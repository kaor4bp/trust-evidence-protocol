"""State-level validation orchestration."""

from __future__ import annotations

from pathlib import Path

from .agent_identity import current_bound_agent_ref, local_agent_owns_working_context
from .code_index import validate_code_index_state
from .core_validators import validate_core_graph
from .errors import ValidationError
from .hypotheses import validate_hypotheses_index
from .logic import validate_logic_state
from .paths import record_path
from .policy import validate_runtime_policy
from .records import load_records
from .reason_ledger import validate_grant_run_lifecycle, validate_reason_ledger_state
from .schemas import validate_record, validate_refs
from .settings import validate_settings_state


def validate_records_state(
    root: Path,
    records: dict[str, dict],
    allowed_freedom: str | None = None,
    mode: str = "full",
) -> list[ValidationError]:
    errors: list[ValidationError] = []
    current_agent_ref = current_bound_agent_ref(root) if mode == "operational" else ""
    for record_id, data in records.items():
        record_type = str(data.get("record_type", "")).strip()
        if mode == "operational":
            if record_type == "agent_identity" and record_id != current_agent_ref:
                continue
            if record_type == "working_context" and (data.get("agent_identity_ref") or data.get("owner_signature")):
                if not local_agent_owns_working_context(root, data):
                    continue
        for message in validate_record(record_id, data):
            errors.append(ValidationError(Path(data["_path"]), message))
    errors.extend(validate_refs(records))
    errors.extend(validate_core_graph(root, records, mode=mode))
    errors.extend(validate_logic_state(root, records))
    errors.extend(validate_code_index_state(root, records))
    errors.extend(validate_settings_state(root, records))
    errors.extend(validate_hypotheses_index(root, records))
    errors.extend(validate_reason_ledger_state(root))
    errors.extend(validate_grant_run_lifecycle(root, records))
    errors.extend(validate_runtime_policy(root, records, allowed_freedom=allowed_freedom))
    return errors


def collect_validation_errors(
    root: Path,
    allowed_freedom: str | None = None,
    mode: str = "full",
) -> tuple[dict[str, dict], list[ValidationError]]:
    records, errors = load_records(root)
    errors.extend(validate_records_state(root, records, allowed_freedom=allowed_freedom, mode=mode))
    return records, errors


def validate_candidate_record(
    root: Path,
    records: dict[str, dict],
    payload: dict,
    allowed_freedom: str | None = None,
) -> tuple[dict, list[ValidationError]]:
    record_id = str(payload.get("id", "")).strip()
    record_type = str(payload.get("record_type", "")).strip()
    candidate = dict(payload)
    candidate["_folder"] = record_type
    candidate["_path"] = record_path(root, record_type, record_id)

    errors: list[ValidationError] = []
    if record_id in records:
        errors.append(ValidationError(Path(candidate["_path"]), f"duplicate id: {record_id}"))

    for message in validate_record(record_id, candidate):
        errors.append(ValidationError(Path(candidate["_path"]), message))

    merged = dict(records)
    merged[record_id] = candidate
    errors.extend(validate_records_state(root, merged, allowed_freedom=allowed_freedom))
    return candidate, errors
