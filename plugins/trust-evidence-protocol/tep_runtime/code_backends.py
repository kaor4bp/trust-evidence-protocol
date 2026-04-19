"""Optional code-intelligence backend adapters.

Backend output is navigation only. TEP remains the agent-facing boundary and
normalizes external tool output before it reaches MCP/CLI callers.
"""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

from .backends import backend_status_payload, select_backend_status
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


def cocoindex_search_payload(
    context_root: Path,
    repo_root: Path,
    *,
    query: str,
    language: str | None = None,
    path_patterns: list[str] | None = None,
    limit: int = 8,
) -> dict[str, Any]:
    settings = load_settings(context_root)
    code_settings = settings.get("backends", {}).get("code_intelligence", {})
    coco_settings = code_settings.get("cocoindex", {}) if isinstance(code_settings, dict) else {}
    enabled = bool(coco_settings.get("enabled"))
    mode = str(coco_settings.get("mode") or "cli")
    backend_limit = int(coco_settings.get("max_results") or limit)
    effective_limit = max(1, min(limit, backend_limit, 100))
    status_matches = select_backend_status(backend_status_payload(context_root), "code_intelligence.cocoindex")
    status = status_matches[0] if status_matches else {}

    payload: dict[str, Any] = {
        "backend": "cocoindex",
        "query": query,
        "mode": mode,
        "enabled": enabled,
        "available": bool(status.get("available")),
        "backend_output_is_proof": BACKEND_OUTPUT_IS_PROOF,
        "warnings": list(status.get("warnings") or []),
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

    args = [command, "search", query, "--limit", str(effective_limit)]
    if language:
        args.extend(["--lang", language])
    for pattern in path_patterns or []:
        if pattern:
            args.extend(["--path", pattern])
            break
    try:
        result = subprocess.run(
            args,
            cwd=repo_root,
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


def cocoindex_search_text_lines(payload: dict[str, Any]) -> list[str]:
    status = "available" if payload.get("available") else "unavailable"
    lines = [
        f"Backend: cocoindex ({status}, mode={payload.get('mode', 'unknown')}, proof=false)",
        f"Query: {payload.get('query', '')}",
    ]
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
    return lines
