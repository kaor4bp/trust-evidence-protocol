from __future__ import annotations

import fnmatch
import hashlib
import json
import re
import secrets
import subprocess
from datetime import datetime
from pathlib import Path

from tep_runtime.code_ast import analyze_js_like, analyze_markdown, analyze_python, empty_analysis
from tep_runtime.errors import ValidationError
from tep_runtime.hydration import invalidate_hydration_state
from tep_runtime.ids import CODE_INDEX_ID_PATTERN
from tep_runtime.ids import now_timestamp
from tep_runtime.io import write_json_file, write_text_file
from tep_runtime.paths import code_index_entry_path
from tep_runtime.records import load_code_index_entries
from tep_runtime.search import concise
from tep_runtime.validation import CONFIDENCE_LEVELS, ensure_string_list, safe_list


CODE_INDEX_TARGET_KINDS = {"file", "directory", "glob", "symbol", "area"}
CODE_INDEX_STATUSES = {"active", "missing", "superseded", "archived"}
CODE_INDEX_TARGET_STATES = {"present", "missing", "unknown"}
CODE_INDEX_ANNOTATION_KINDS = {"agent-note", "review-note", "TODO", "rationale", "risk", "smell"}
CODE_INDEX_ANNOTATION_STATUSES = {"active", "stale", "superseded", "invalid", "rejected"}
CODE_SMELL_CATEGORIES = {
    "mixed-responsibility",
    "hidden-side-effect",
    "implicit-contract",
    "brittle-selector",
    "overbroad-abstraction",
    "leaky-compatibility",
    "test-coupled-implementation",
    "unverified-runtime-assumption",
    "stateful-helper",
    "poor-error-boundary",
}
CODE_SMELL_SEVERITIES = {"low", "medium", "high", "critical"}
CODE_INDEX_ALLOWED_RECORD_TYPES = {
    "guideline",
    "proposal",
    "plan",
    "debt",
    "open_question",
    "model",
    "flow",
    "action",
    "task",
    "working_context",
}
CODE_INDEX_LINK_KEYS = {
    "guideline_refs": "guideline",
    "claim_refs": "claim",
    "model_refs": "model",
    "flow_refs": "flow",
    "source_refs": "source",
    "plan_refs": "plan",
    "debt_refs": "debt",
    "open_question_refs": "open_question",
    "working_context_refs": "working_context",
}
CODE_INDEX_LANGUAGES = {
    ".py": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".sh": "shell",
    ".bash": "shell",
    ".zsh": "shell",
    ".md": "markdown",
    ".json": "json",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".toml": "toml",
}
DEFAULT_CODE_INDEX_PATTERNS = [
    "**/*.py",
    "**/*.js",
    "**/*.jsx",
    "**/*.ts",
    "**/*.tsx",
    "**/*.sh",
    "**/*.md",
    "**/*.json",
    "**/*.yaml",
    "**/*.yml",
    "**/*.toml",
]
DEFAULT_CODE_INDEX_EXCLUDES = [
    ".git/**",
    ".codex_context/**",
    ".codex/**/__pycache__/**",
    "**/__pycache__/**",
    ".venv/**",
    "venv/**",
    "node_modules/**",
    "dist/**",
    "build/**",
    ".mypy_cache/**",
    ".pytest_cache/**",
]
CODE_SEARCH_FIELD_ORDER = [
    "target",
    "summary",
    "language",
    "code_kind",
    "imports",
    "symbols",
    "features",
    "links",
    "annotations",
    "freshness",
    "hash",
]


def next_code_index_id(entries: dict[str, dict]) -> str:
    today = now_timestamp()[:10].replace("-", "")
    for _ in range(32):
        candidate = f"CIX-{today}-{secrets.token_hex(4)}"
        if candidate not in entries:
            return candidate
    raise RuntimeError(f"could not allocate collision-free code index id for CIX-{today}")


def build_manual_code_index_entry(
    entry_id: str,
    timestamp: str,
    target_kind: str,
    path: str | None,
    name: str | None,
    symbol_name: str | None,
    summary: str,
    manual_features: list[str],
    note: str,
) -> dict:
    target = {"kind": target_kind}
    if path:
        target["path"] = path.strip()
    if name:
        target["name"] = name.strip()
    if symbol_name:
        target["symbol_name"] = symbol_name.strip()
    return {
        "id": entry_id,
        "record_type": "code_index_entry",
        "status": "active",
        "target": target,
        "target_state": "unknown" if target_kind in {"glob", "symbol", "area"} else "present",
        "language": "",
        "code_kind": target_kind,
        "summary": summary.strip(),
        "metadata": {},
        "detected_features": [],
        "manual_features": manual_features,
        "manual_links": {},
        "annotations": [],
        "links": [],
        "child_entry_refs": [],
        "related_entry_refs": [],
        "supersedes_refs": [],
        "created_at": timestamp,
        "updated_at": timestamp,
        "note": note.strip(),
    }


def code_index_rel_path(root_path: Path, path: Path) -> str:
    resolved_root = root_path.resolve()
    resolved_path = path.resolve()
    try:
        return resolved_path.relative_to(resolved_root).as_posix()
    except ValueError:
        return resolved_path.as_posix()


def code_index_language(path: Path) -> str:
    return CODE_INDEX_LANGUAGES.get(path.suffix.lower(), "unknown")


def code_index_kind(path: Path, text: str | None = None) -> str:
    lowered = path.as_posix().lower()
    name = path.name.lower()
    if "/test/" in lowered or "/tests/" in lowered or name.startswith("test_") or name.endswith("_test.py") or ".test." in name or ".spec." in name:
        return "test"
    if "/docs/" in lowered or path.suffix.lower() in {".md"}:
        return "docs"
    if path.suffix.lower() in {".json", ".yaml", ".yml", ".toml"}:
        return "config"
    if "/generated/" in lowered or name.endswith(".generated.ts") or name.endswith(".generated.py"):
        return "generated"
    return "source"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_text_sample(path: Path, max_bytes: int) -> tuple[str, bool]:
    data = path.read_bytes()
    truncated = len(data) > max_bytes
    if truncated:
        data = data[:max_bytes]
    try:
        return data.decode("utf-8"), truncated
    except UnicodeDecodeError:
        return data.decode("utf-8", errors="replace"), truncated


def detect_code_features(path: Path, language: str, code_kind: str, text: str, analysis: dict) -> list[str]:
    features: set[str] = set()
    lowered = text.lower()
    imports = set(analysis.get("imports", []))
    if code_kind == "test":
        features.add("tests")
    if "pytest" in imports or "pytest" in lowered:
        features.add("pytest")
    if "unittest" in imports:
        features.add("unittest")
    if "playwright" in lowered:
        features.add("playwright")
    if "fixture" in lowered or any("fixture" in item for item in analysis.get("decorators", [])):
        features.add("fixtures")
    if "assert " in text or "expect(" in text or "assert." in lowered:
        features.add("assertions")
    if "locator" in lowered:
        features.add("locator")
    if "screenshot" in lowered:
        features.add("screenshot")
    if "subprocess" in imports or "subprocess" in lowered:
        features.add("subprocess")
    if "requests" in imports or "httpx" in imports or "fetch(" in lowered:
        features.add("network")
    if "open(" in text or "write_text" in lowered or "write_bytes" in lowered:
        features.add("filesystem-write")
    if "run_json_agent" in text or "agent" in path.as_posix().lower():
        features.add("agent-call")
    if "page" in path.as_posix().lower() or "pageobject" in lowered or "page object" in lowered:
        features.add("page-object")
    if language in {"json", "yaml", "toml"}:
        features.add("config")
    if language == "markdown":
        features.add("markdown")
        if analysis.get("headings"):
            features.add("outline")
        if analysis.get("links"):
            features.add("links")
        if analysis.get("code_blocks"):
            features.add("code-blocks")
    return sorted(features)


def analyze_code_file(root_path: Path, path: Path, max_bytes: int) -> dict:
    stat = path.stat()
    text, truncated = read_text_sample(path, max_bytes)
    language = code_index_language(path)
    code_kind = code_index_kind(path, text)
    if language == "python":
        analysis = analyze_python(text)
    elif language in {"javascript", "typescript"}:
        analysis = analyze_js_like(text)
    elif language == "markdown":
        analysis = analyze_markdown(text)
    else:
        analysis = empty_analysis()
    features = detect_code_features(path, language, code_kind, text, analysis)
    rel_path = code_index_rel_path(root_path, path)
    return {
        "target": {"kind": "file", "path": rel_path},
        "target_state": "present",
        "language": language,
        "code_kind": code_kind,
        "metadata": {
            "sha256": sha256_file(path),
            "size_bytes": stat.st_size,
            "mtime": datetime.fromtimestamp(stat.st_mtime).astimezone().isoformat(timespec="seconds"),
            "imports": analysis.get("imports", []),
            "classes": analysis.get("classes", []),
            "functions": analysis.get("functions", []),
            "tests": analysis.get("tests", []),
            "decorators": analysis.get("decorators", []),
            "headings": analysis.get("headings", []),
            "links": analysis.get("links", []),
            "code_blocks": analysis.get("code_blocks", []),
            "parse_error": analysis.get("parse_error", ""),
            "truncated": truncated,
        },
        "detected_features": features,
    }


def public_code_index_entry(entry: dict) -> dict:
    return {key: value for key, value in entry.items() if not str(key).startswith("_")}


def code_index_entry_for_file(
    root: Path,
    entries: dict[str, dict],
    root_path: Path,
    path: Path,
    max_bytes: int,
    *,
    workspace_ref: str = "",
    project_ref: str = "",
) -> tuple[dict, bool]:
    now = now_timestamp()
    rel_path = code_index_rel_path(root_path, path)
    existing_for_path = [
        entry
        for entry in entries.values()
        if isinstance(entry.get("target"), dict)
        and entry["target"].get("kind") == "file"
        and entry["target"].get("path") == rel_path
        and entry.get("status") not in {"superseded", "archived"}
        and (str(entry.get("project_ref", "")).strip() == project_ref if project_ref else True)
        and (str(entry.get("workspace_ref", "")).strip() == workspace_ref if workspace_ref else True)
    ]
    active = next((entry for entry in existing_for_path if entry.get("target_state") == "present"), None)
    missing = next((entry for entry in existing_for_path if entry.get("target_state") == "missing"), None)
    detected = analyze_code_file(root_path, path, max_bytes)
    if active:
        payload = public_code_index_entry(active)
        payload.update(detected)
        if workspace_ref:
            payload["workspace_ref"] = workspace_ref
        if project_ref:
            payload["project_ref"] = project_ref
        payload["updated_at"] = now
        return payload, False
    entry_id = next_code_index_id(entries)
    payload = {
        "id": entry_id,
        "record_type": "code_index_entry",
        "status": "active",
        "summary": f"{detected['code_kind']} {rel_path}",
        "manual_features": [],
        "manual_links": {},
        "annotations": [],
        "links": [],
        "child_entry_refs": [],
        "related_entry_refs": [missing["id"]] if missing else [],
        "supersedes_refs": [missing["id"]] if missing else [],
        "created_at": now,
        "updated_at": now,
        "note": "generated by code index",
        **detected,
    }
    if workspace_ref:
        payload["workspace_ref"] = workspace_ref
    if project_ref:
        payload["project_ref"] = project_ref
    return payload, True


def code_index_path_matches(path: str, patterns: list[str]) -> bool:
    if not patterns:
        return True
    return any(fnmatch.fnmatch(path, pattern) for pattern in patterns)


def code_index_excluded(path: str, patterns: list[str]) -> bool:
    return any(fnmatch.fnmatch(path, pattern) for pattern in patterns)


def discover_files(root_path: Path, includes: list[str], excludes: list[str], git_tracked: bool, max_files: int) -> list[Path]:
    patterns = includes or DEFAULT_CODE_INDEX_PATTERNS
    exclude_patterns = DEFAULT_CODE_INDEX_EXCLUDES + excludes
    files: list[Path] = []
    if git_tracked:
        result = subprocess.run(
            ["git", "-C", str(root_path), "ls-files"],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            raise RuntimeError("git ls-files failed; run inside a git worktree or use index-code with --include")
        candidates = [root_path / line.strip() for line in result.stdout.splitlines() if line.strip()]
    else:
        candidates = [path for path in root_path.rglob("*") if path.is_file()]
    for path in candidates:
        if not path.is_file():
            continue
        rel = code_index_rel_path(root_path, path)
        if code_index_excluded(rel, exclude_patterns):
            continue
        if not code_index_path_matches(rel, patterns):
            continue
        files.append(path)
        if len(files) > max_files:
            raise RuntimeError(f"too many files for code indexing ({len(files)} > {max_files}); narrow --include or raise --max-files")
    return sorted(files)


def write_code_index_views(root: Path, entries: dict[str, dict]) -> None:
    index_root = root / "code_index"
    by_path = {}
    by_ref: dict[str, list[str]] = {}
    for entry_id, entry in sorted(entries.items()):
        target = entry.get("target", {})
        if isinstance(target, dict) and target.get("path"):
            by_path.setdefault(str(target.get("path")), []).append(entry_id)
        for ref_key, refs in (entry.get("manual_links") or {}).items():
            if isinstance(refs, list):
                for ref in refs:
                    by_ref.setdefault(str(ref), []).append(entry_id)
        for link in entry.get("links", []) if isinstance(entry.get("links", []), list) else []:
            if isinstance(link, dict) and str(link.get("status", "active")) == "active" and link.get("ref"):
                by_ref.setdefault(str(link.get("ref")), []).append(entry_id)
    write_json_file(index_root / "by_path.json", {key: sorted(value) for key, value in sorted(by_path.items())})
    write_json_file(index_root / "by_ref.json", {key: sorted(set(value)) for key, value in sorted(by_ref.items())})
    counts: dict[str, int] = {}
    for entry in entries.values():
        counts[str(entry.get("status", ""))] = counts.get(str(entry.get("status", "")), 0) + 1
    lines = [
        "# Code Index Summary\n",
        "\n",
        "This view is generated from `.codex_context/code_index/entries/CIX-*.json`.\n",
        "CIX entries are navigation/scope/impact objects, not proof.\n",
        "\n",
        "Counts:\n",
    ]
    for status, count in sorted(counts.items()):
        lines.append(f"- `{status or 'unknown'}`: {count}\n")
    write_text_file(index_root / "summary.md", "".join(lines))


def persist_code_index_entries(root: Path, entries: dict[str, dict], changed: list[dict], reason: str) -> int:
    for entry in changed:
        write_json_file(code_index_entry_path(root, entry["id"]), public_code_index_entry(entry))
        entries[entry["id"]] = dict(entry)
    write_code_index_views(root, entries)
    invalidate_hydration_state(root, reason)
    print(reason)
    return 0


def resolve_code_entry(entries: dict[str, dict], entry_ref: str | None, path: str | None) -> dict | None:
    if entry_ref:
        return entries.get(entry_ref)
    if path:
        matches = [
            entry
            for entry in entries.values()
            if isinstance(entry.get("target"), dict)
            and entry["target"].get("path") == path
            and entry.get("status") not in {"superseded", "archived"}
        ]
        return sorted(matches, key=lambda item: str(item.get("updated_at", "")), reverse=True)[0] if matches else None
    return None


def code_entry_freshness(repo_root: Path, entry: dict) -> dict:
    target = entry.get("target", {})
    if not isinstance(target, dict) or target.get("kind") != "file":
        return {"stale": False, "target_state": entry.get("target_state", "unknown")}
    rel = str(target.get("path", ""))
    path = repo_root / rel
    if not path.exists():
        return {"stale": entry.get("target_state") == "present", "target_state": "missing"}
    current_hash = sha256_file(path)
    stored_hash = str((entry.get("metadata") or {}).get("sha256", ""))
    return {"stale": bool(stored_hash and current_hash != stored_hash), "target_state": "present", "current_sha256": current_hash}


def code_entry_current_target_sha(repo_root: Path, entry: dict) -> str | None:
    target = entry.get("target", {})
    if not isinstance(target, dict):
        return None
    rel = str(target.get("path", "")).strip()
    if not rel:
        return None
    path = repo_root / rel
    if not path.exists() or not path.is_file():
        return None
    return sha256_file(path)


def code_annotation_is_stale(repo_root: Path, entry: dict, annotation: dict) -> bool:
    observed = str(annotation.get("observed_sha256", "") or "").strip()
    if not observed:
        return False
    current = code_entry_current_target_sha(repo_root, entry)
    return current is not None and current != observed


def code_annotation_matches(
    repo_root: Path,
    entry: dict,
    annotation: dict,
    annotation_kind: str | None,
    annotation_categories: list[str],
    annotation_status: str | None,
    include_stale_annotations: bool,
) -> bool:
    if not isinstance(annotation, dict):
        return False
    if annotation_kind and str(annotation.get("kind", "")).strip() != annotation_kind:
        return False
    status = str(annotation.get("status", "active")).strip() or "active"
    if annotation_status and status != annotation_status:
        return False
    if not annotation_status and status != "active":
        return False
    if annotation_categories:
        categories = {str(item).strip() for item in annotation.get("categories", []) if str(item).strip()}
        if not set(annotation_categories).issubset(categories):
            return False
    if not include_stale_annotations and code_annotation_is_stale(repo_root, entry, annotation):
        return False
    return True


def code_entry_matching_annotations(
    repo_root: Path,
    entry: dict,
    annotation_kind: str | None,
    annotation_categories: list[str],
    annotation_status: str | None,
    include_stale_annotations: bool,
) -> list[dict]:
    return [
        annotation
        for annotation in entry.get("annotations", [])
        if code_annotation_matches(
            repo_root,
            entry,
            annotation,
            annotation_kind,
            annotation_categories,
            annotation_status,
            include_stale_annotations,
        )
    ]


def project_code_entry(entry: dict, fields: list[str], repo_root: Path) -> dict:
    metadata = entry.get("metadata") or {}
    result = {"id": entry.get("id"), "status": entry.get("status")}
    for field in fields:
        if field == "target":
            result["target"] = entry.get("target", {})
        elif field == "summary":
            result["summary"] = entry.get("summary", "")
        elif field == "language":
            result["language"] = entry.get("language", "")
        elif field == "code_kind":
            result["code_kind"] = entry.get("code_kind", "")
        elif field == "imports":
            result["imports"] = metadata.get("imports", [])
        elif field == "symbols":
            result["symbols"] = {
                "classes": metadata.get("classes", []),
                "functions": metadata.get("functions", []),
                "tests": metadata.get("tests", []),
                "headings": metadata.get("headings", []),
                "code_blocks": metadata.get("code_blocks", []),
            }
        elif field == "features":
            result["features"] = {"detected": entry.get("detected_features", []), "manual": entry.get("manual_features", [])}
        elif field == "links":
            result["links"] = {"manual_links": entry.get("manual_links", {}), "links": entry.get("links", [])}
        elif field == "annotations":
            result["annotations"] = entry.get("annotations", [])
        elif field == "freshness":
            result["freshness"] = code_entry_freshness(repo_root, entry)
        elif field == "hash":
            result["hash"] = {"sha256": metadata.get("sha256", ""), "mtime": metadata.get("mtime", ""), "size_bytes": metadata.get("size_bytes", "")}
    return result


def code_entries_text_lines(entries: list[dict], fields: list[str], repo_root: Path) -> list[str]:
    lines = ["# Code Index Results", ""]
    for entry in entries:
        projected = project_code_entry(entry, fields, repo_root)
        target = projected.get("target", {})
        target_display = target.get("path") or target.get("name") or target.get("symbol_name") or "<unknown>"
        freshness = projected.get("freshness", {})
        stale = f" stale={freshness.get('stale')}" if "freshness" in projected else ""
        lines.append(f"- `{entry.get('id')}` status=`{entry.get('status')}` target=`{target_display}`{stale}")
        for field, value in projected.items():
            if field in {"id", "status", "target", "freshness"}:
                continue
            lines.append(f"  {field}: {concise(json.dumps(value, ensure_ascii=False), 260)}")
    return lines


def parse_code_fields(value: str | None) -> list[str]:
    if not value:
        return ["target", "summary", "features", "freshness"]
    fields = [item.strip() for item in value.split(",") if item.strip()]
    invalid = [field for field in fields if field not in CODE_SEARCH_FIELD_ORDER]
    if invalid:
        raise ValueError(f"invalid field(s): {', '.join(invalid)}")
    return fields


def code_target_rank(entry: dict) -> int:
    target = entry.get("target", {})
    kind = str(target.get("kind", "") if isinstance(target, dict) else "")
    return {"symbol": 0, "file": 1, "directory": 2, "glob": 3, "area": 3}.get(kind, 9)


def code_smell_rows(
    repo_root: Path,
    entries: dict[str, dict],
    categories: list[str],
    severities: list[str],
    include_stale: bool,
) -> list[dict]:
    severity_rank = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    rows = []
    for entry in entries.values():
        if str(entry.get("status", "")) not in {"active", "missing"}:
            continue
        for annotation in entry.get("annotations", []):
            status = str(annotation.get("status", "active")).strip() or "active"
            if status not in {"active", "stale"}:
                continue
            if str(annotation.get("kind", "")).strip() != "smell":
                continue
            if categories and not set(categories).issubset(set(annotation.get("categories", []))):
                continue
            severity = str(annotation.get("severity", "medium")).strip() or "medium"
            if severities and severity not in severities:
                continue
            stale = status == "stale" or code_annotation_is_stale(repo_root, entry, annotation)
            if stale and not include_stale:
                continue
            rows.append(
                {
                    "entry": project_code_entry(entry, ["target", "summary", "freshness"], repo_root),
                    "annotation": annotation,
                    "stale": stale,
                    "target_rank": code_target_rank(entry),
                    "severity_rank": severity_rank.get(severity, 9),
                }
            )
    return sorted(
        rows,
        key=lambda row: (
            row["target_rank"],
            row["severity_rank"],
            str(row["entry"].get("target", {}).get("path", "")),
            str(row["annotation"].get("id", "")),
        ),
    )


def code_smell_report_payload(rows: list[dict], categories: list[str], severities: list[str], include_stale: bool) -> dict:
    return {
        "include_stale": include_stale,
        "category_filter": categories,
        "severity_filter": severities,
        "results": [
            {
                "entry": {key: value for key, value in row["entry"].items() if key != "freshness"},
                "freshness": row["entry"].get("freshness", {}),
                "annotation": row["annotation"],
                "stale": row["stale"],
            }
            for row in rows
        ],
    }


def code_smell_report_text_lines(rows: list[dict]) -> list[str]:
    lines = [
        "# Code Smell Report",
        "",
        "Mode: read-only. CIX smell annotations are navigation/critique, not proof or hard rules.",
        "",
    ]
    if not rows:
        lines.append("- no active code smell annotations found")
        return lines

    for row in rows:
        entry = row["entry"]
        annotation = row["annotation"]
        target = entry.get("target", {})
        target_display = target.get("qualified_name") or target.get("symbol_name") or target.get("path") or target.get("name") or "<unknown>"
        stale_suffix = " stale=true" if row["stale"] else ""
        lines.append(
            f"- `{entry.get('id')}` target=`{target_display}` "
            f"severity=`{annotation.get('severity', 'medium')}` categories={annotation.get('categories', [])}{stale_suffix}: "
            f"{concise(str(annotation.get('text', '')), 220)}"
        )
        suggestions = annotation.get("suggestions", [])
        if suggestions:
            lines.append(f"  suggestions: {concise(json.dumps(suggestions, ensure_ascii=False), 220)}")
        refs = []
        for key in ("claim_refs", "source_refs", "proposal_refs"):
            if annotation.get(key):
                refs.append(f"{key}={annotation[key]}")
        if refs:
            lines.append(f"  refs: {' '.join(refs)}")
    return lines


def annotation_snapshot(entry: dict) -> dict:
    metadata = entry.get("metadata") or {}
    payload = {
        "observed_sha256": metadata.get("sha256"),
        "observed_mtime": metadata.get("mtime"),
        "observed_target_state": entry.get("target_state", "unknown"),
        "observed_at": now_timestamp(),
    }
    target = entry.get("target", {})
    if isinstance(target, dict) and target.get("start_line") and target.get("end_line"):
        payload["observed_range"] = {
            "start_line": target.get("start_line"),
            "end_line": target.get("end_line"),
        }
    return payload


def normalize_smell_categories(categories: list[str]) -> tuple[list[str], str | None]:
    result = []
    for raw_category in categories:
        category = raw_category.strip()
        if not category:
            continue
        if category in CODE_SMELL_CATEGORIES or re.match(r"^custom:[a-z0-9][a-z0-9-]{1,63}$", category):
            result.append(category)
        else:
            return [], f"invalid smell category: {category}"
    if not result:
        return [], "smell annotations require at least one --category"
    return sorted(set(result)), None


def validate_code_index_entry(
    entry_id: str,
    entry: dict,
    records: dict[str, dict],
    entries: dict[str, dict],
) -> list[ValidationError]:
    path = Path(entry.get("_path", code_index_entry_path(Path("."), entry_id)))
    errors: list[ValidationError] = []
    if path.stem != entry_id:
        errors.append(ValidationError(path, "filename must match code index id"))
    if not CODE_INDEX_ID_PATTERN.match(entry_id):
        errors.append(ValidationError(path, "code index id must be CIX-YYYYMMDD-xxxxxxxx"))
    if str(entry.get("record_type", "")).strip() != "code_index_entry":
        errors.append(ValidationError(path, "record_type must be code_index_entry"))
    status = str(entry.get("status", "")).strip()
    if status not in CODE_INDEX_STATUSES:
        errors.append(ValidationError(path, "status must be active, missing, superseded, or archived"))
    target_state = str(entry.get("target_state", "")).strip()
    if target_state not in CODE_INDEX_TARGET_STATES:
        errors.append(ValidationError(path, "target_state must be present, missing, or unknown"))
    target = entry.get("target", {})
    if not isinstance(target, dict):
        errors.append(ValidationError(path, "target must be an object"))
        target = {}
    target_kind = str(target.get("kind", "")).strip()
    if target_kind not in CODE_INDEX_TARGET_KINDS:
        errors.append(ValidationError(path, "target.kind must be file, directory, glob, symbol, or area"))
    if target_kind in {"file", "directory", "glob"} and not str(target.get("path", "")).strip():
        errors.append(ValidationError(path, f"target.kind={target_kind} requires target.path"))
    if target_kind == "symbol" and (
        not str(target.get("path", "")).strip() or not str(target.get("symbol_name", "")).strip()
    ):
        errors.append(ValidationError(path, "target.kind=symbol requires target.path and target.symbol_name"))
    if target_kind == "area" and not str(target.get("name", "")).strip():
        errors.append(ValidationError(path, "target.kind=area requires target.name"))
    for key in ("detected_features", "manual_features", "child_entry_refs", "related_entry_refs", "supersedes_refs"):
        try:
            ensure_string_list(entry, key)
        except ValueError as exc:
            errors.append(ValidationError(path, str(exc)))
    for key in ("child_entry_refs", "related_entry_refs", "supersedes_refs"):
        for ref in safe_list(entry, key):
            if ref not in entries:
                errors.append(ValidationError(path, f"missing code index ref in {key}: {ref}"))
    manual_links = entry.get("manual_links", {})
    if manual_links in ("", None):
        manual_links = {}
    if not isinstance(manual_links, dict):
        errors.append(ValidationError(path, "manual_links must be an object"))
        manual_links = {}
    for key, expected_type in CODE_INDEX_LINK_KEYS.items():
        refs = manual_links.get(key, [])
        if refs in ("", None):
            refs = []
        if not isinstance(refs, list):
            errors.append(ValidationError(path, f"manual_links.{key} must be a list"))
            continue
        for ref in refs:
            ref = str(ref)
            if ref not in records:
                errors.append(ValidationError(path, f"manual_links.{key} missing ref: {ref}"))
            elif records[ref].get("record_type") != expected_type:
                errors.append(ValidationError(path, f"manual_links.{key} ref {ref} must reference {expected_type}"))
    annotations = entry.get("annotations", [])
    if annotations in ("", None):
        annotations = []
    if not isinstance(annotations, list):
        errors.append(ValidationError(path, "annotations must be a list"))
    else:
        seen_annotation_ids: set[str] = set()
        for annotation in annotations:
            if not isinstance(annotation, dict):
                errors.append(ValidationError(path, "annotation entries must be objects"))
                continue
            annotation_id = str(annotation.get("id", "")).strip()
            if not annotation_id:
                errors.append(ValidationError(path, "annotation.id is required"))
            elif annotation_id in seen_annotation_ids:
                errors.append(ValidationError(path, f"duplicate annotation id: {annotation_id}"))
            seen_annotation_ids.add(annotation_id)
            annotation_kind = str(annotation.get("kind", "")).strip()
            if annotation_kind not in CODE_INDEX_ANNOTATION_KINDS:
                errors.append(ValidationError(path, "annotation.kind is invalid"))
            if str(annotation.get("status", "active")).strip() not in CODE_INDEX_ANNOTATION_STATUSES:
                errors.append(ValidationError(path, "annotation.status must be active, stale, superseded, invalid, or rejected"))
            if not str(annotation.get("text", "")).strip():
                errors.append(ValidationError(path, "annotation.text is required"))
            confidence = str(annotation.get("confidence", "")).strip()
            if confidence and confidence not in CONFIDENCE_LEVELS:
                errors.append(ValidationError(path, "annotation.confidence is invalid"))
            for ref_key, expected_type in {
                "source_refs": "source",
                "claim_refs": "claim",
                "proposal_refs": "proposal",
            }.items():
                refs = annotation.get(ref_key, [])
                if refs in ("", None):
                    refs = []
                if not isinstance(refs, list):
                    errors.append(ValidationError(path, f"annotation.{ref_key} must be a list"))
                    continue
                for ref in refs:
                    ref = str(ref)
                    if ref not in records:
                        errors.append(ValidationError(path, f"annotation.{ref_key} missing ref: {ref}"))
                    elif records[ref].get("record_type") != expected_type:
                        errors.append(ValidationError(path, f"annotation.{ref_key} ref {ref} must reference {expected_type}"))
            suggestions = annotation.get("suggestions", [])
            if suggestions in ("", None):
                suggestions = []
            if not isinstance(suggestions, list):
                errors.append(ValidationError(path, "annotation.suggestions must be a list"))
            elif any(not str(item).strip() for item in suggestions):
                errors.append(ValidationError(path, "annotation.suggestions entries must be non-empty strings"))
            if annotation_kind == "smell":
                categories = annotation.get("categories", [])
                if not isinstance(categories, list) or not categories:
                    errors.append(ValidationError(path, "smell annotation.categories must be a non-empty list"))
                    categories = []
                for category in categories:
                    category_value = str(category).strip()
                    if category_value in CODE_SMELL_CATEGORIES:
                        continue
                    if re.match(r"^custom:[a-z0-9][a-z0-9-]{1,63}$", category_value):
                        continue
                    errors.append(ValidationError(path, f"invalid smell category: {category_value}"))
                severity = str(annotation.get("severity", "")).strip()
                if severity not in CODE_SMELL_SEVERITIES:
                    errors.append(ValidationError(path, "smell annotation.severity must be low, medium, high, or critical"))
                if severity == "critical" and not annotation.get("claim_refs"):
                    errors.append(ValidationError(path, "critical smell annotation requires at least one claim_ref"))
    links = entry.get("links", [])
    if links in ("", None):
        links = []
    if not isinstance(links, list):
        errors.append(ValidationError(path, "links must be a list"))
    else:
        seen_link_ids: set[str] = set()
        for link in links:
            if not isinstance(link, dict):
                errors.append(ValidationError(path, "link entries must be objects"))
                continue
            link_id = str(link.get("id", "")).strip()
            if not link_id:
                errors.append(ValidationError(path, "link.id is required"))
            elif link_id in seen_link_ids:
                errors.append(ValidationError(path, f"duplicate link id: {link_id}"))
            seen_link_ids.add(link_id)
            if str(link.get("status", "active")).strip() not in {"active", "superseded", "invalid"}:
                errors.append(ValidationError(path, "link.status must be active, superseded, or invalid"))
            ref_key = str(link.get("ref_key", "")).strip()
            ref = str(link.get("ref", "")).strip()
            expected_type = CODE_INDEX_LINK_KEYS.get(ref_key)
            if not expected_type:
                errors.append(ValidationError(path, "link.ref_key is invalid"))
            elif ref not in records:
                errors.append(ValidationError(path, f"link missing ref: {ref}"))
            elif records[ref].get("record_type") != expected_type:
                errors.append(ValidationError(path, f"link ref {ref} must reference {expected_type}"))
    return errors


def validate_code_index_state(root: Path, records: dict[str, dict]) -> list[ValidationError]:
    entries, errors = load_code_index_entries(root)
    for entry_id, entry in entries.items():
        errors.extend(validate_code_index_entry(entry_id, entry, records, entries))
    for record_id, data in records.items():
        path = Path(data["_path"])
        if data.get("record_type") == "working_context":
            for ref in safe_list(data, "pinned_refs"):
                ref = str(ref)
                if ref.startswith("CIX-") and ref not in entries:
                    errors.append(ValidationError(path, f"missing pinned code index ref: {ref}"))
        code_index_refs = data.get("code_index_refs")
        if code_index_refs in (None, ""):
            continue
        if data.get("record_type") not in CODE_INDEX_ALLOWED_RECORD_TYPES:
            errors.append(ValidationError(path, "code_index_refs are not allowed for this record_type"))
            continue
        if not isinstance(code_index_refs, list):
            errors.append(ValidationError(path, "code_index_refs must be a list"))
            continue
        for ref in code_index_refs:
            ref = str(ref)
            if ref not in entries:
                errors.append(ValidationError(path, f"missing code_index_ref: {ref}"))
    return errors
