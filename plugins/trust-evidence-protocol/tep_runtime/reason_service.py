"""Reason ledger service wrappers shared by CLI and MCP adapters."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .hypotheses import active_hypothesis_entry_by_claim
from .reason_ledger import (
    create_claim_step,
    create_reason_step,
    grant_reason_access,
    reason_access_text_lines,
    validate_reason_ledger,
)
from .reasoning import (
    decision_validation_text_lines,
    decision_validation_payload,
    evidence_chain_report_lines,
    validate_evidence_chain_payload,
)


def reason_step_service(
    root: Path,
    records: dict[str, dict],
    *,
    chain_payload: dict[str, Any] | None = None,
    claim_ref: str | None = None,
    prev_claim_ref: str | None = None,
    relation_claim_ref: str | None = None,
    prev_step_ref: str | None = None,
    wctx_ref: str | None = None,
    intent: str,
    mode: str,
    action_kind: str | None,
    why: str,
    parent_refs: list[str] | None = None,
    branch: str = "main",
    icon: str = "TEP",
) -> tuple[dict[str, Any] | None, str | None]:
    """Validate a public chain or CLM transition and append one ledger step."""

    if claim_ref:
        return create_claim_step(
            root,
            records,
            claim_ref=claim_ref,
            prev_claim_ref=prev_claim_ref,
            relation_claim_ref=relation_claim_ref,
            prev_step_ref=prev_step_ref,
            wctx_ref=wctx_ref,
            intent=intent,
            mode=mode,
            action_kind=action_kind,
            reason=why,
            branch=branch,
        )
    if not isinstance(chain_payload, dict):
        return None, "chain_payload must be an object"
    hypothesis_entries = active_hypothesis_entry_by_claim(root, records)
    validation = validate_evidence_chain_payload(records, hypothesis_entries, chain_payload)
    if validation.errors:
        return None, "\n".join(evidence_chain_report_lines(validation, chain_payload, icon))
    decision = decision_validation_payload(records, hypothesis_entries, chain_payload, mode)
    if not decision.get("decision_chain_valid", decision.get("decision_valid")):
        return None, "\n".join(decision_validation_text_lines(decision, icon))
    return create_reason_step(
        root,
        chain_payload=chain_payload,
        decision_payload=decision,
        intent=intent,
        mode=mode,
        action_kind=action_kind,
        why=why,
        parent_refs=parent_refs or [],
        branch=branch,
    )


def reason_review_service(
    root: Path,
    *,
    reason_ref: str,
    mode: str,
    action_kind: str | None,
    grant: bool,
    ttl_seconds: int | None,
    command: str | None,
    cwd: str | Path | None,
    tool: str = "bash",
) -> tuple[dict[str, Any] | None, str | None]:
    """Review a STEP-* and optionally create a GRANT-* entry."""

    validation = validate_reason_ledger(root)
    if not validation["ok"]:
        return None, "Reason ledger tampered or invalid:\n" + "\n".join(
            f"- {error}" for error in validation["errors"]
        )
    reason = next((entry for entry in validation["entries"] if str(entry.get("id", "")).strip() == reason_ref), None)
    if not reason:
        return None, f"missing reason {reason_ref}"
    if not grant:
        return {"reason": reason}, None
    access, error = grant_reason_access(
        root,
        reason_ref=reason_ref,
        mode=mode,
        action_kind=action_kind,
        ttl_seconds=ttl_seconds,
        command=command,
        cwd=cwd,
        tool=tool,
    )
    if error:
        return None, error
    return {"reason": reason, "grant": access}, None


def reason_step_text(reason: dict[str, Any], mode: str, action_kind: str | None) -> str:
    if reason.get("entry_type") == "claim_step":
        return (
            f"Recorded claim step {reason['id']} claim={reason.get('claim_ref')} "
            f"prev={reason.get('prev_claim_ref') or 'none'} mode={mode} kind={(action_kind or '') or 'none'}"
        )
    return f"Recorded reason {reason['id']} status={reason.get('status')} mode={mode} kind={(action_kind or '') or 'none'}"


def reason_review_text(payload: dict[str, Any], reason_ref: str, grant: bool) -> str:
    if not grant:
        return f"Reason {reason_ref} reviewed; grant=false"
    access = payload.get("grant")
    if not isinstance(access, dict):
        return json.dumps(payload, indent=2, ensure_ascii=False)
    lines = [f"Granted reason authorization {access['id']} for reason {reason_ref}"]
    lines.extend(reason_access_text_lines(access))
    return "\n".join(lines)
