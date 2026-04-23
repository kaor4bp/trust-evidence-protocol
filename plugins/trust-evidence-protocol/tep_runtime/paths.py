from __future__ import annotations

import re
from pathlib import Path


def settings_path(root: Path) -> Path:
    return root / "settings.json"


def runtime_dir(root: Path) -> Path:
    return root / "runtime"


def hydration_state_path(root: Path) -> Path:
    return runtime_dir(root) / "hydration.json"


def reasoning_runtime_dir(root: Path) -> Path:
    return runtime_dir(root) / "reasoning"


def _safe_agent_ref(agent_ref: str) -> str:
    value = str(agent_ref or "").strip()
    if not value:
        raise ValueError("agent_ref is required for an agent-scoped reasoning ledger path")
    return re.sub(r"[^A-Za-z0-9_.-]", "_", value)


def agent_reasoning_runtime_dir(root: Path, agent_ref: str) -> Path:
    return reasoning_runtime_dir(root) / "agents" / _safe_agent_ref(agent_ref)


def legacy_reasons_ledger_path(root: Path) -> Path:
    return reasoning_runtime_dir(root) / "reasons.jsonl"


def legacy_reasoning_seal_path(root: Path) -> Path:
    return reasoning_runtime_dir(root) / "seal.json"


def reasons_ledger_path(root: Path, agent_ref: str | None = None) -> Path:
    if agent_ref:
        return agent_reasoning_runtime_dir(root, agent_ref) / "reasons.jsonl"
    return legacy_reasons_ledger_path(root)


def reasoning_seal_path(root: Path, agent_ref: str | None = None) -> Path:
    if agent_ref:
        return agent_reasoning_runtime_dir(root, agent_ref) / "seal.json"
    return legacy_reasoning_seal_path(root)


def hypotheses_index_path(root: Path) -> Path:
    return root / "hypotheses.jsonl"


def record_path(root: Path, record_type: str, record_id: str) -> Path:
    return root / "records" / record_type / f"{record_id}.json"


def code_index_entries_root(root: Path) -> Path:
    return root / "code_index" / "entries"


def code_index_entry_path(root: Path, entry_id: str) -> Path:
    return code_index_entries_root(root) / f"{entry_id}.json"
