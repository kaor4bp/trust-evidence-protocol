"""Optional code-intelligence backend adapters.

Backend output is navigation only. TEP remains the agent-facing boundary and
normalizes external tool output before it reaches MCP/CLI callers.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

from .backends import backend_status_payload, select_backend_status
from .code_index import code_entry_freshness
from .settings import load_settings


BACKEND_OUTPUT_IS_PROOF = False
_CCC_RESULT_RE = re.compile(r"^--- Result (?P<rank>\d+) \(score: (?P<score>[0-9.]+)\) ---$")
_CCC_FILE_RE = re.compile(
    r"^File: (?P<path>.*?):(?P<start>\d+)(?:-(?P<end>\d+))? \[(?P<language>[^\]]+)\]$"
)


def _cocoindex_command() -> str | None:
    for command in ("ccc", "cocoindex-code", "cocoindex"):
        path = shutil.which(command)
        if path:
            return path
    return None


def _compact_snippet(lines: list[str], *, max_chars: int = 700) -> str:
    snippet = "\n".join(line.rstrip() for line in lines).strip()
    if len(snippet) <= max_chars:
        return snippet
    return snippet[: max_chars - 3].rstrip() + "..."


def parse_cocoindex_search_output(stdout: str) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    snippet_lines: list[str] = []

    def flush() -> None:
        nonlocal current, snippet_lines
        if current is not None:
            current["snippet"] = _compact_snippet(snippet_lines)
            results.append(current)
        current = None
        snippet_lines = []

    for raw_line in stdout.splitlines():
        line = raw_line.rstrip()
        result_match = _CCC_RESULT_RE.match(line)
        if result_match:
            flush()
            current = {
                "rank": int(result_match.group("rank")),
                "score": float(result_match.group("score")),
                "backend": "cocoindex",
                "backend_output_is_proof": BACKEND_OUTPUT_IS_PROOF,
            }
            continue
        file_match = _CCC_FILE_RE.match(line)
        if file_match and current is not None:
            current["target"] = {
                "path": file_match.group("path"),
                "line_start": int(file_match.group("start")),
                "line_end": int(file_match.group("end") or file_match.group("start")),
            }
            current["language"] = file_match.group("language")
            continue
        if current is not None:
            snippet_lines.append(line)
    flush()
    return results


def resolve_cocoindex_storage_dir(
    context_root: Path,
    *,
    scope: str,
    workspace_ref: str | None,
    project_ref: str | None,
    storage_root: str | None,
) -> Path | None:
    """Return the scoped CocoIndex DB directory controlled by TEP settings."""

    root_value = (storage_root or "<context>/backends/cocoindex").strip()
    if root_value.startswith("<context>"):
        base = context_root / root_value.removeprefix("<context>").lstrip("/")
    else:
        base = Path(root_value).expanduser()
        if not base.is_absolute():
            base = context_root / base
    if scope == "project":
        return base / "projects" / project_ref / ".cocoindex_code" if project_ref else None
    if scope == "workspace":
        return base / "workspaces" / workspace_ref / ".cocoindex_code" if workspace_ref else None
    return None


def cocoindex_search_payload(
    context_root: Path,
    repo_root: Path,
    *,
    query: str,
    language: str | None = None,
    path_patterns: list[str] | None = None,
    limit: int = 8,
    scope: str | None = None,
    workspace_ref: str | None = None,
    project_ref: str | None = None,
) -> dict[str, Any]:
    settings = load_settings(context_root)
    code_settings = settings.get("backends", {}).get("code_intelligence", {})
    coco_settings = code_settings.get("cocoindex", {}) if isinstance(code_settings, dict) else {}
    enabled = bool(coco_settings.get("enabled"))
    mode = str(coco_settings.get("mode") or "cli")
    effective_scope = scope or str(coco_settings.get("default_scope") or "project")
    backend_limit = int(coco_settings.get("max_results") or limit)
    effective_limit = max(1, min(limit, backend_limit, 100))
    storage_dir = resolve_cocoindex_storage_dir(
        context_root,
        scope=effective_scope,
        workspace_ref=workspace_ref,
        project_ref=project_ref,
        storage_root=str(coco_settings.get("storage_root") or "<context>/backends/cocoindex"),
    )
    status_matches = select_backend_status(backend_status_payload(context_root), "code_intelligence.cocoindex")
    status = status_matches[0] if status_matches else {}

    payload: dict[str, Any] = {
        "backend": "cocoindex",
        "query": query,
        "mode": mode,
        "scope": effective_scope,
        "enabled": enabled,
        "available": bool(status.get("available")),
        "backend_output_is_proof": BACKEND_OUTPUT_IS_PROOF,
        "warnings": list(status.get("warnings") or []),
        "storage": {
            "repo_root": str(repo_root),
            "workspace_ref": workspace_ref or "",
            "project_ref": project_ref or "",
            "scoped_db_dir": str(storage_dir) if storage_dir else "",
            "db_path_mapping": f"{repo_root}={storage_dir}" if storage_dir else "",
        },
        "results": [],
    }
    if not query.strip():
        payload["warnings"].append("empty backend query")
        return payload
    if not enabled:
        payload["warnings"].append("backends.code_intelligence.cocoindex.enabled is false")
        return payload
    if mode not in {"cli", "mcp"}:
        payload["warnings"].append(f"unsupported cocoindex mode for TEP proxy: {mode}")
        return payload
    command = _cocoindex_command()
    if command is None:
        payload["available"] = False
        payload["warnings"].append("CocoIndex command was not found on PATH")
        return payload
    if effective_scope == "project" and not project_ref:
        payload["warnings"].append("project-scoped CocoIndex search has no current project ref")
    if effective_scope == "workspace" and not workspace_ref:
        payload["warnings"].append("workspace-scoped CocoIndex search has no current workspace ref")

    args = [command, "search", query, "--limit", str(effective_limit)]
    if language:
        args.extend(["--lang", language])
    for pattern in path_patterns or []:
        if pattern:
            args.extend(["--path", pattern])
            break
    try:
        env = None
        if storage_dir:
            env = {
                **os.environ,
                "COCOINDEX_CODE_DB_PATH_MAPPING": f"{repo_root}={storage_dir}",
            }
        result = subprocess.run(
            args,
            cwd=repo_root,
            env=env,
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
    except subprocess.TimeoutExpired:
        payload["available"] = False
        payload["warnings"].append("CocoIndex search timed out")
        return payload
    payload["returncode"] = result.returncode
    if result.returncode != 0:
        payload["warnings"].append((result.stderr or result.stdout or "CocoIndex search failed").strip())
        return payload
    payload["results"] = parse_cocoindex_search_output(result.stdout)[:effective_limit]
    return payload


def enrich_backend_results_with_cix(
    payload: dict[str, Any],
    entries: dict[str, dict],
    repo_root: Path,
    *,
    link_candidates: dict[str, list[str]] | None = None,
) -> dict[str, Any]:
    """Attach matching CIX candidates and link suggestions to backend hits."""

    by_path: dict[str, list[dict]] = {}
    for entry in entries.values():
        target = entry.get("target") if isinstance(entry.get("target"), dict) else {}
        path = str(target.get("path", "")).strip()
        if not path or str(entry.get("status", "")) in {"superseded", "archived"}:
            continue
        by_path.setdefault(path, []).append(entry)

    for result in payload.get("results") or []:
        if not isinstance(result, dict):
            continue
        target = result.get("target") if isinstance(result.get("target"), dict) else {}
        path = str(target.get("path", "")).strip()
        candidates = []
        for entry in sorted(by_path.get(path, []), key=lambda item: str(item.get("updated_at", "")), reverse=True):
            candidates.append(
                {
                    "id": entry.get("id"),
                    "status": entry.get("status"),
                    "target": entry.get("target", {}),
                    "freshness": code_entry_freshness(repo_root, entry),
                }
            )
        result["cix_candidates"] = candidates
        if path and not candidates:
            result["index_suggestion"] = {
                "command": f"index-code --root <repo-root> --include {path}",
                "suggestion_is_proof": BACKEND_OUTPUT_IS_PROOF,
                "reason": "backend hit path is not represented by a CIX entry yet",
            }
        suggestions = []
        if candidates and link_candidates:
            entry_id = str(candidates[0].get("id") or "")
            for ref_key, refs in sorted(link_candidates.items()):
                for ref in refs:
                    suggestions.append(
                        {
                            "entry": entry_id,
                            "ref_key": ref_key,
                            "ref": ref,
                            "command": f"link-code --entry {entry_id} --{ref_key.removesuffix('_refs').replace('_', '-')} {ref} --note <why-this-backend-hit-is-relevant>",
                            "suggestion_is_proof": BACKEND_OUTPUT_IS_PROOF,
                        }
                    )
        if suggestions:
            result["link_suggestions"] = suggestions
    return payload


def cocoindex_search_text_lines(payload: dict[str, Any]) -> list[str]:
    status = "available" if payload.get("available") else "unavailable"
    lines = [
        f"Backend: cocoindex ({status}, mode={payload.get('mode', 'unknown')}, proof=false)",
        f"Scope: {payload.get('scope', 'project')}",
        f"Query: {payload.get('query', '')}",
    ]
    storage = payload.get("storage") if isinstance(payload.get("storage"), dict) else {}
    if storage.get("scoped_db_dir"):
        lines.append(f"Scoped DB: {storage.get('scoped_db_dir')}")
    for warning in payload.get("warnings") or []:
        lines.append(f"Warning: {warning}")
    for item in payload.get("results") or []:
        target = item.get("target") or {}
        location = target.get("path", "")
        if target.get("line_start"):
            location = f"{location}:{target.get('line_start')}-{target.get('line_end')}"
        lines.append(f"- #{item.get('rank')} score={item.get('score')} {location} [{item.get('language', '')}]")
        snippet = str(item.get("snippet") or "").strip()
        if snippet:
            first_line = snippet.splitlines()[0]
            lines.append(f"  snippet: {first_line[:180]}")
        cix_candidates = item.get("cix_candidates") or []
        if cix_candidates:
            lines.append("  cix_candidates: " + ", ".join(str(candidate.get("id")) for candidate in cix_candidates))
        index_suggestion = item.get("index_suggestion")
        if isinstance(index_suggestion, dict):
            lines.append(f"  index_suggestion: {index_suggestion.get('command')}")
        for suggestion in item.get("link_suggestions") or []:
            lines.append(f"  link_suggestion: {suggestion.get('command')}")
    return lines
