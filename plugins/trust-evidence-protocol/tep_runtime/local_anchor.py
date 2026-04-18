"""Local .tep anchor parsing.

The anchor is a workdir-local selector for the global TEP store. It is not
canonical memory and must not contain records.
"""

from __future__ import annotations

import json
from pathlib import Path

from .ids import PROJECT_ID_PATTERN, WORKSPACE_ID_PATTERN

ANCHOR_FILENAME = ".tep"


def find_anchor_path(start: str | Path | None, *, stop: Path | None = None) -> Path | None:
    if start is None:
        current = Path.cwd().resolve()
    else:
        current = Path(start).expanduser().resolve()
    if current.is_file():
        current = current.parent

    stop_root = stop.expanduser().resolve() if stop is not None else None
    for candidate_dir in [current, *current.parents]:
        candidate = candidate_dir / ANCHOR_FILENAME
        if candidate.is_file():
            return candidate.resolve()
        if stop_root is not None and candidate_dir == stop_root:
            break
    return None


def load_anchor(path: str | Path) -> dict:
    anchor_path = Path(path).expanduser().resolve()
    try:
        data = json.loads(anchor_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(data, dict):
        return {}
    data["_path"] = anchor_path
    return data


def find_anchor(start: str | Path | None, *, stop: Path | None = None) -> dict:
    path = find_anchor_path(start, stop=stop)
    if path is None:
        return {}
    return load_anchor(path)


def anchor_context_root(anchor: dict) -> Path | None:
    raw = str(anchor.get("context_root") or "").strip()
    if not raw:
        return None
    return Path(raw).expanduser().resolve()


def anchor_applies_to_context(anchor: dict, root: str | Path) -> bool:
    context_root = anchor_context_root(anchor)
    if context_root is None:
        return False
    return context_root == Path(root).expanduser().resolve()


def anchor_workspace_ref(anchor: dict) -> str:
    ref = str(anchor.get("workspace_ref") or "").strip()
    return ref if WORKSPACE_ID_PATTERN.match(ref) else ""


def anchor_project_ref(anchor: dict) -> str:
    ref = str(anchor.get("project_ref") or "").strip()
    return ref if PROJECT_ID_PATTERN.match(ref) else ""


def anchor_settings(anchor: dict) -> dict:
    settings = anchor.get("settings")
    return settings if isinstance(settings, dict) else {}
