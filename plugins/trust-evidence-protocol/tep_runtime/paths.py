from __future__ import annotations

from pathlib import Path


def settings_path(root: Path) -> Path:
    return root / "settings.json"


def runtime_dir(root: Path) -> Path:
    return root / "runtime"


def hydration_state_path(root: Path) -> Path:
    return runtime_dir(root) / "hydration.json"


def chain_permits_dir(root: Path) -> Path:
    return runtime_dir(root) / "chain_permits"


def hypotheses_index_path(root: Path) -> Path:
    return root / "hypotheses.jsonl"


def record_path(root: Path, record_type: str, record_id: str) -> Path:
    return root / "records" / record_type / f"{record_id}.json"


def code_index_entries_root(root: Path) -> Path:
    return root / "code_index" / "entries"


def code_index_entry_path(root: Path, entry_id: str) -> Path:
    return code_index_entries_root(root) / f"{entry_id}.json"
