from __future__ import annotations

from pathlib import Path

from .errors import ValidationError
from .io import parse_json_file
from .paths import code_index_entries_root


RECORD_DIRS = {
    "agent_identity": "agent_identity",
    "workspace": "workspace",
    "project": "project",
    "input": "input",
    "file": "file",
    "run": "run",
    "source": "source",
    "claim": "claim",
    "permission": "permission",
    "restriction": "restriction",
    "guideline": "guideline",
    "proposal": "proposal",
    "action": "action",
    "task": "task",
    "working_context": "working_context",
    "curator_pool": "curator_pool",
    "plan": "plan",
    "debt": "debt",
    "model": "model",
    "flow": "flow",
    "open_question": "open_question",
}

OPTIONAL_RECORD_DIRS = {"agent_identity", "curator_pool"}

RECORD_TYPE_TO_PREFIX = {
    "agent_identity": "AGENT-",
    "workspace": "WSP-",
    "project": "PRJ-",
    "input": "INP-",
    "file": "FILE-",
    "run": "RUN-",
    "source": "SRC-",
    "claim": "CLM-",
    "permission": "PRM-",
    "restriction": "RST-",
    "guideline": "GLD-",
    "proposal": "PRP-",
    "action": "ACT-",
    "task": "TASK-",
    "working_context": "WCTX-",
    "curator_pool": "CURP-",
    "plan": "PLN-",
    "debt": "DEBT-",
    "model": "MODEL-",
    "flow": "FLOW-",
    "open_question": "OPEN-",
}


def load_code_index_entries(root: Path) -> tuple[dict[str, dict], list[ValidationError]]:
    entries: dict[str, dict] = {}
    errors: list[ValidationError] = []
    entries_root = code_index_entries_root(root)
    if not entries_root.exists():
        return entries, []
    for path in sorted(entries_root.glob("*.json")):
        try:
            data = parse_json_file(path)
        except Exception as exc:  # noqa: BLE001
            errors.append(ValidationError(path, str(exc)))
            continue
        entry_id = str(data.get("id", "")).strip()
        if not entry_id:
            errors.append(ValidationError(path, "missing id"))
            continue
        if entry_id in entries:
            errors.append(ValidationError(path, f"duplicate code index id: {entry_id}"))
            continue
        data["_path"] = path
        entries[entry_id] = data
    return entries, errors


def load_records(root: Path) -> tuple[dict[str, dict], list[ValidationError]]:
    records: dict[str, dict] = {}
    errors: list[ValidationError] = []
    for directory in RECORD_DIRS:
        folder = root / "records" / directory
        if not folder.exists():
            if directory not in OPTIONAL_RECORD_DIRS:
                errors.append(ValidationError(folder, "missing record directory"))
            continue
        for path in sorted(folder.glob("*.json")):
            try:
                data = parse_json_file(path)
            except Exception as exc:  # noqa: BLE001
                errors.append(ValidationError(path, str(exc)))
                continue
            record_id = str(data.get("id", "")).strip()
            if not record_id:
                errors.append(ValidationError(path, "missing id"))
                continue
            if record_id in records:
                errors.append(ValidationError(path, f"duplicate id: {record_id}"))
                continue
            data["_path"] = path
            data["_folder"] = directory
            records[record_id] = data
    return records, errors
