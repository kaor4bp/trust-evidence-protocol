"""Context-root discovery for global TEP memory with legacy fallback."""

from __future__ import annotations

import os
from pathlib import Path

TEP_CONTEXT_ENV = "TEP_CONTEXT_ROOT"
GLOBAL_CONTEXT_DIR = ".tep_context"
LEGACY_CONTEXT_DIR = ".codex_context"


def normalize_context_root(path: str | Path) -> Path:
    return Path(path).expanduser().resolve()


def global_context_root(home: Path | None = None) -> Path:
    base = home if home is not None else Path.home()
    return (base / GLOBAL_CONTEXT_DIR).expanduser().resolve()


def env_context_root() -> Path | None:
    raw = os.environ.get(TEP_CONTEXT_ENV, "").strip()
    if not raw:
        return None
    return normalize_context_root(raw)


def find_legacy_context_root(start: str | Path | None, *, stop: Path | None = None) -> Path | None:
    if start is None:
        current = Path.cwd().resolve()
    else:
        current = normalize_context_root(start)
    if current.is_file():
        current = current.parent

    stop_root = stop.expanduser().resolve() if stop is not None else None
    for candidate_dir in [current, *current.parents]:
        candidate = candidate_dir / LEGACY_CONTEXT_DIR
        if candidate.is_dir():
            return candidate.resolve()
        if stop_root is not None and candidate_dir == stop_root:
            break
    return None


def resolve_context_root(
    explicit: str | Path | None = None,
    *,
    start: str | Path | None = None,
    stop: Path | None = None,
    require_exists: bool = False,
) -> Path | None:
    candidates: list[Path] = []

    if explicit:
        candidates.append(normalize_context_root(explicit))
    else:
        env_root = env_context_root()
        if env_root is not None:
            candidates.append(env_root)

        global_root = global_context_root()
        if global_root.is_dir():
            candidates.append(global_root)

        legacy_root = find_legacy_context_root(start, stop=stop)
        if legacy_root is not None:
            candidates.append(legacy_root)

        candidates.append(global_root)

    for candidate in candidates:
        if not require_exists or candidate.is_dir():
            return candidate
    return None
