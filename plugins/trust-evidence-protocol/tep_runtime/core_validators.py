"""TEP 0.4 graph-level validators shared by adapters and hooks."""

from __future__ import annotations

from pathlib import Path

from .claims import claim_is_fallback
from .errors import ValidationError
from .scopes import current_workspace_ref
from .validation import safe_list


def _path(record: dict) -> Path:
    value = record.get("_path")
    return value if isinstance(value, Path) else Path(str(value or "."))


def _is_v04(record: dict) -> bool:
    return str(record.get("contract_version", "")).strip() == "0.4"


def _has_tag(record: dict, tag: str) -> bool:
    return tag in {str(item).strip() for item in record.get("tags", [])}


def _requires_v04_graph(record: dict) -> bool:
    return _is_v04(record) or _has_tag(record, "graph-v2")


def _source_provenance_refs(source: dict) -> list[str]:
    refs: list[str] = []
    refs.extend(safe_list(source, "input_refs"))
    refs.extend(safe_list(source, "file_refs"))
    refs.extend(safe_list(source, "run_refs"))
    refs.extend(safe_list(source, "artifact_refs"))
    return [ref for ref in refs if str(ref).strip()]


def _source_has_run(records: dict[str, dict], source_ref: str) -> bool:
    source = records.get(source_ref)
    return bool(source and source.get("record_type") == "source" and safe_list(source, "run_refs"))


def validate_workspace_focus(root: Path, records: dict[str, dict]) -> list[ValidationError]:
    """Durable non-workspace records require workspace scope in 0.4 records."""

    errors: list[ValidationError] = []
    current_workspace = current_workspace_ref(root)
    for record in records.values():
        if not _is_v04(record):
            continue
        record_type = str(record.get("record_type", "")).strip()
        if record_type in {"workspace", "agent_identity"}:
            continue
        workspace_refs = safe_list(record, "workspace_refs")
        workspace_ref = str(record.get("workspace_ref", "")).strip()
        if not workspace_refs and not workspace_ref and not current_workspace:
            errors.append(ValidationError(_path(record), "0.4 durable record requires explicit workspace focus"))
    return errors


def validate_wctx_ownership(records: dict[str, dict]) -> list[ValidationError]:
    """Owner-bound WCTX records must match a valid local AGENT-* identity."""

    errors: list[ValidationError] = []
    for record in records.values():
        if record.get("record_type") != "working_context":
            continue
        if not (_is_v04(record) or record.get("agent_identity_ref") or record.get("owner_signature")):
            continue
        agent_ref = str(record.get("agent_identity_ref", "")).strip()
        fingerprint = str(record.get("agent_key_fingerprint", "")).strip()
        signature = record.get("owner_signature")
        if not agent_ref.startswith("AGENT-"):
            errors.append(ValidationError(_path(record), "0.4 WCTX requires agent_identity_ref"))
            continue
        agent = records.get(agent_ref)
        if not agent or agent.get("record_type") != "agent_identity":
            errors.append(ValidationError(_path(record), f"WCTX agent_identity_ref {agent_ref} must reference an agent_identity record"))
            continue
        if str(agent.get("status", "")).strip() != "active":
            errors.append(ValidationError(_path(record), f"WCTX agent_identity_ref {agent_ref} must reference an active agent_identity"))
        if fingerprint != str(agent.get("key_fingerprint", "")).strip():
            errors.append(ValidationError(_path(record), "WCTX agent_key_fingerprint must match agent_identity key_fingerprint"))
        if str(record.get("ownership_mode", "")).strip() != "owner-only":
            errors.append(ValidationError(_path(record), "0.4 WCTX ownership_mode must be owner-only"))
        if str(record.get("handoff_policy", "")).strip() != "fork-required":
            errors.append(ValidationError(_path(record), "0.4 WCTX handoff_policy must be fork-required"))
        if not isinstance(signature, dict):
            errors.append(ValidationError(_path(record), "0.4 WCTX requires owner_signature object"))
            continue
        if str(signature.get("algorithm", "")).strip() != "hmac-sha256":
            errors.append(ValidationError(_path(record), "WCTX owner_signature.algorithm must be hmac-sha256"))
        if not str(signature.get("signed_payload_hash", "")).strip().startswith("sha256:"):
            errors.append(ValidationError(_path(record), "WCTX owner_signature.signed_payload_hash must start with sha256:"))
        if not str(signature.get("signature", "")).strip().startswith("hmac-sha256:"):
            errors.append(ValidationError(_path(record), "WCTX owner_signature.signature must start with hmac-sha256:"))
    return errors


def validate_provenance_graph(records: dict[str, dict]) -> list[ValidationError]:
    """0.4/graph-v2 sources and runtime claims must have mechanical provenance."""

    errors: list[ValidationError] = []
    for record in records.values():
        if record.get("record_type") == "source" and _requires_v04_graph(record):
            if not _source_provenance_refs(record):
                errors.append(ValidationError(_path(record), "0.4 source requires INP/FILE/RUN/ART provenance"))

        if record.get("record_type") != "claim" or not _requires_v04_graph(record):
            continue
        if str(record.get("plane", "")).strip() != "runtime":
            continue
        source_refs = safe_list(record, "source_refs")
        if not any(_source_has_run(records, ref) for ref in source_refs):
            errors.append(ValidationError(_path(record), "0.4 runtime claim requires source transitively linked to RUN-*"))
    return errors


def _claim_is_supported_theory(records: dict[str, dict], ref: str) -> bool:
    claim = records.get(ref)
    if not claim or claim.get("record_type") != "claim":
        return False
    if str(claim.get("plane", "")).strip() != "theory":
        return False
    if str(claim.get("status", "")).strip() not in {"supported", "corroborated"}:
        return False
    if claim_is_fallback(claim):
        return False
    return True


def validate_model_flow_authority(records: dict[str, dict]) -> list[ValidationError]:
    """0.4 MODEL/FLOW authority cannot come from tentative/runtime-only/meta-only support."""

    errors: list[ValidationError] = []
    for record in records.values():
        record_type = record.get("record_type")
        if record_type == "model" and _is_v04(record):
            bad_refs = [ref for ref in safe_list(record, "claim_refs") if not _claim_is_supported_theory(records, ref)]
            if bad_refs:
                errors.append(ValidationError(_path(record), f"0.4 MODEL requires supported theory claim_refs: {', '.join(bad_refs)}"))

        if record_type == "flow" and _is_v04(record):
            for model_ref in safe_list(record, "model_refs"):
                model = records.get(model_ref)
                if not model or model.get("record_type") != "model":
                    continue
                if _is_v04(model):
                    continue
                errors.append(ValidationError(_path(record), f"0.4 FLOW model_ref {model_ref} must reference a 0.4 MODEL"))
            for step in record.get("steps", []) if isinstance(record.get("steps"), list) else []:
                if not isinstance(step, dict):
                    continue
                bad_refs = [ref for ref in step.get("claim_refs", []) if not _claim_is_supported_theory(records, str(ref))]
                if bad_refs:
                    errors.append(ValidationError(_path(record), f"0.4 FLOW step requires supported theory claim_refs: {', '.join(bad_refs)}"))
    return errors


def validate_core_graph(root: Path, records: dict[str, dict]) -> list[ValidationError]:
    errors: list[ValidationError] = []
    errors.extend(validate_workspace_focus(root, records))
    errors.extend(validate_wctx_ownership(records))
    errors.extend(validate_provenance_graph(records))
    errors.extend(validate_model_flow_authority(records))
    return errors
