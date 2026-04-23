"""Reason ledger service wrappers shared by CLI and MCP adapters."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .reason_ledger import (
    create_claim_step,
    grant_reason_access,
    reason_access_text_lines,
    validate_reason_ledger,
)


def reason_step_service(
    root: Path,
    records: dict[str, dict],
    *,
    claim_ref: str | None = None,
    prev_claim_ref: str | None = None,
    relation_claim_ref: str | None = None,
    prev_step_ref: str | None = None,
    wctx_ref: str | None = None,
    intent: str,
    mode: str,
    action_kind: str | None,
    why: str,
    branch: str = "main",
) -> tuple[dict[str, Any] | None, str | None]:
    """Validate a CLM transition and append one STEP-* claim-step ledger entry."""

    if not claim_ref:
        return None, "reason-step requires --claim CLM-*; evidence-chain based ledger steps were removed in 0.4.7"
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
    return (
        f"Recorded claim step {reason['id']} claim={reason.get('claim_ref')} "
        f"prev={reason.get('prev_claim_ref') or 'none'} mode={mode} kind={(action_kind or '') or 'none'}"
    )


def reason_review_text(payload: dict[str, Any], reason_ref: str, grant: bool) -> str:
    if not grant:
        return f"Reason {reason_ref} reviewed; grant=false"
    access = payload.get("grant")
    if not isinstance(access, dict):
        return json.dumps(payload, indent=2, ensure_ascii=False)
    lines = [f"Granted reason authorization {access['id']} for reason {reason_ref}"]
    lines.extend(reason_access_text_lines(access))
    return "\n".join(lines)
