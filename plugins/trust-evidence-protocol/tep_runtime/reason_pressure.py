"""Claim-step ledger briefing and pressure helpers for agent routes."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from .hydration import compute_context_fingerprint
from .reason_ledger import current_reasoning_agent_ref, grant_use_count, latest_reason_step, validate_reason_ledger
from .retrieval import active_permissions_for
from .scopes import current_project_ref, current_task_ref, current_workspace_ref


INTENT_REASON_MODE = {
    "answer": "final",
    "answering": "final",
    "plan": "planning",
    "planning": "planning",
    "edit": "edit",
    "editing": "edit",
    "test": "test",
    "persist": "planning",
    "permission": "permission",
    "debug": "debugging",
    "debugging": "debugging",
    "after-mutation": "debugging",
    "curiosity": "curiosity",
    "migration": "planning",
    "orientation": "planning",
    "retrospective": "planning",
    "auto": "planning",
}


def reason_mode_for_intent(intent: str, fallback: str = "planning") -> str:
    return INTENT_REASON_MODE.get((intent or "").strip(), fallback)


def _record_time(record: dict[str, Any]) -> str:
    for key in ("created_at", "recorded_at", "started_at", "updated_at", "completed_at"):
        value = str(record.get(key, "")).strip()
        if value:
            return value
    return ""


def _short_record(record: dict[str, Any]) -> dict[str, str]:
    return {
        "id": str(record.get("id", "")).strip(),
        "record_type": str(record.get("record_type", "")).strip(),
        "scope": str(record.get("scope", "")).strip(),
        "status": str(record.get("status", "")).strip(),
        "summary": str(
            record.get("summary")
            or record.get("title")
            or record.get("statement")
            or record.get("command")
            or record.get("note")
            or ""
        ).strip()[:240],
        "time": _record_time(record),
    }


def _parse_time(value: str) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.astimezone()
    return parsed


def _permission_label(permission: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(permission.get("id", "")).strip(),
        "status": str(permission.get("status", "")).strip(),
        "scope": str(permission.get("scope", "")).strip(),
        "applies_to": str(permission.get("applies_to", "")).strip(),
        "grants": [str(item).strip() for item in permission.get("grants", []) if str(item).strip()][:6],
        "summary": str(permission.get("summary") or permission.get("title") or permission.get("note") or "").strip()[:240],
    }


def _grant_is_scope_current(grant: dict[str, Any], *, workspace_ref: str, project_ref: str, task_ref: str, fingerprint: str) -> bool:
    return (
        str(grant.get("workspace_ref", "")).strip() == workspace_ref
        and str(grant.get("project_ref", "")).strip() == project_ref
        and str(grant.get("task_ref", "")).strip() == task_ref
        and str(grant.get("context_fingerprint", "")).strip() == fingerprint
    )


def _grant_is_time_current(grant: dict[str, Any]) -> bool:
    expires_at = _parse_time(str(grant.get("expires_at", "")).strip())
    return expires_at is not None and expires_at >= datetime.now().astimezone()


def _current_grant_label(root: Path, grant: dict[str, Any]) -> dict[str, Any]:
    grant_ref = str(grant.get("id", "")).strip()
    max_runs = int(grant.get("max_runs", grant.get("max_uses", 1)) or 1)
    use_count = grant_use_count(root, grant_ref)
    return {
        "id": grant_ref,
        "mode": str(grant.get("mode", "")).strip(),
        "action_kind": str(grant.get("action_kind", "")).strip() or "*",
        "grant_type": str(grant.get("grant_type", "")).strip() or "action_kind",
        "reason_ref": str(grant.get("reason_ref", "")).strip(),
        "claim_ref": str(grant.get("claim_ref", "")).strip(),
        "relation_claim_ref": str(grant.get("relation_claim_ref", "")).strip(),
        "command_bound": bool(str(grant.get("command_sha256", "")).strip()),
        "expires_at": str(grant.get("expires_at", "")).strip(),
        "remaining_runs": max(0, max_runs - use_count) if max_runs > 0 else -1,
    }


def build_permission_snapshot(root: Path, records: dict[str, dict], entries: list[dict[str, Any]], *, limit: int = 5) -> dict[str, Any]:
    """Return a compact, non-authoritative summary of currently visible rights."""

    workspace_ref = current_workspace_ref(root)
    project_ref = current_project_ref(root)
    task_ref = current_task_ref(root)
    fingerprint = compute_context_fingerprint(root)
    agent_ref = current_reasoning_agent_ref(root, create=False)
    active_permissions = active_permissions_for(records, set(), project_ref or None, task_ref or None, limit)
    grants = [
        entry
        for entry in entries
        if str(entry.get("entry_type", "")).strip() == "grant"
        and str(entry.get("status", "")).strip() == "active"
        and (not agent_ref or str(entry.get("agent_identity_ref", "")).strip() == agent_ref)
        and _grant_is_scope_current(
            entry,
            workspace_ref=workspace_ref,
            project_ref=project_ref,
            task_ref=task_ref,
            fingerprint=fingerprint,
        )
        and _grant_is_time_current(entry)
    ]
    current_grants = [
        label
        for label in (_current_grant_label(root, grant) for grant in reversed(grants))
        if int(label.get("remaining_runs", 0)) != 0
    ][:limit]
    return {
        "snapshot_is_authorization": False,
        "always_allowed": ["next_step", "lookup"],
        "agent_identity_ref": agent_ref,
        "active_permission_refs": [_permission_label(permission) for permission in active_permissions],
        "current_grants": current_grants,
        "default_denied": [
            "protected writes without reviewed STEP-* and GRANT-*",
            "mutating bash without command-bound GRANT-*",
            "autonomous done without fresh final STEP-* and GRANT-*",
        ],
        "check_at_use": "Use reason-review/reason-check-grant or the runtime hook for authoritative authorization.",
    }


def build_start_briefing(root: Path, records: dict[str, dict], *, intent: str = "auto", limit: int = 5) -> dict[str, Any]:
    """Return a compact, non-proof briefing over current reasoning state."""

    validation = validate_reason_ledger(root)
    task_ref = current_task_ref(root)
    entries = validation.get("entries", []) if validation.get("ok") else []
    task_steps = [
        entry
        for entry in entries
        if str(entry.get("entry_type", "")).strip() == "claim_step"
        and (not task_ref or str(entry.get("task_ref", "")).strip() == task_ref)
    ]
    current = latest_reason_step(entries, task_ref) if validation.get("ok") else None
    branches: dict[str, dict[str, Any]] = {}
    for step in task_steps:
        branch = str(step.get("branch") or "main").strip() or "main"
        slot = branches.setdefault(branch, {"branch": branch, "step_count": 0, "latest_step_ref": "", "latest_mode": "", "latest_why": ""})
        slot["step_count"] += 1
        slot["latest_step_ref"] = str(step.get("id", "")).strip()
        slot["latest_mode"] = str(step.get("mode", "")).strip()
        slot["latest_why"] = str(step.get("why") or step.get("reason") or "").strip()

    scoped_records = [
        record
        for record in records.values()
        if str(record.get("record_type", "")).strip() in {"action", "run"}
        and (not task_ref or task_ref in record.get("task_refs", []))
    ]
    recent_actions = [_short_record(record) for record in sorted(scoped_records, key=_record_time)[-limit:]]
    expected_mode = reason_mode_for_intent(intent)
    checks = [
        "confirm current task and WCTX still match the user request",
        "confirm the current STEP branch still matches the next intent",
    ]
    if not current:
        checks.append("create the first STEP-* claim step before substantial work")
    elif str(current.get("mode", "")).strip() != expected_mode:
        checks.append(f"extend or fork STEP-* for mode={expected_mode}")

    return {
        "briefing_is_proof": False,
        "ledger_ok": bool(validation.get("ok")),
        "ledger_errors": validation.get("errors", []),
        "task_ref": task_ref or "",
        "expected_step_mode": expected_mode,
        "current_step_ref": str(current.get("id", "")).strip() if isinstance(current, dict) else "",
        "current_branch": str(current.get("branch", "main")).strip() if isinstance(current, dict) else "",
        "current_mode": str(current.get("mode", "")).strip() if isinstance(current, dict) else "",
        "current_why": str(current.get("why", "")).strip() if isinstance(current, dict) else "",
        "recent_steps": [
            {
                "ref": str(step.get("id", "")).strip(),
                "mode": str(step.get("mode", "")).strip(),
                "branch": str(step.get("branch", "main")).strip() or "main",
                "parent_refs": [str(ref).strip() for ref in step.get("parent_refs", []) if str(ref).strip()],
                "prev_step_ref": str(step.get("prev_step_ref", "")).strip(),
                "claim_ref": str(step.get("claim_ref", "")).strip(),
                "relation_claim_ref": str(step.get("relation_claim_ref", "")).strip(),
                "why": str(step.get("why") or step.get("reason") or "").strip(),
                "created_at": str(step.get("created_at", "")).strip(),
            }
            for step in task_steps[-limit:]
        ],
        "branches": sorted(branches.values(), key=lambda item: str(item.get("branch", ""))),
        "recent_actions": recent_actions,
        "permission_snapshot": build_permission_snapshot(root, records, entries, limit=limit),
        "checks": checks,
    }


def build_reason_pressure(
    root: Path,
    records: dict[str, dict],
    *,
    intent: str = "auto",
    chain_starter: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return route pressure that makes STEP-* the easiest next step."""

    briefing = build_start_briefing(root, records, intent=intent)
    expected_mode = str(briefing.get("expected_step_mode") or reason_mode_for_intent(intent))
    current_step_ref = str(briefing.get("current_step_ref") or "")
    current_mode = str(briefing.get("current_mode") or "")
    validation_preview = (
        chain_starter.get("validation_preview", {})
        if isinstance(chain_starter, dict) and isinstance(chain_starter.get("validation_preview"), dict)
        else {}
    )
    chain_ready = bool(validation_preview.get("justification_valid") or validation_preview.get("decision_chain_valid") or validation_preview.get("ok"))
    reasons: list[str] = []
    level = "none"
    recommended_tool = ""
    recommended_mode = expected_mode

    if not briefing.get("ledger_ok"):
        level = "blocked"
        reasons.append("claim-step ledger is invalid or tampered")
        recommended_tool = "reason-current"
    elif not current_step_ref:
        level = "high" if intent in {"plan", "edit", "test", "final", "answer", "permission"} else "medium"
        reasons.append("current task has no STEP-* claim step")
        recommended_tool = "reason_step" if chain_ready else "lookup"
    elif current_mode != expected_mode and intent in {"plan", "edit", "test", "answer", "permission"}:
        level = "medium"
        reasons.append(f"current STEP-* mode is {current_mode or 'none'}, expected {expected_mode}")
        recommended_tool = "reason_step" if chain_ready else "lookup"
    else:
        level = "low"
        reasons.append("current STEP-* exists; extend it through relation CLM when observations or direction change")
        recommended_tool = "lookup"

    if chain_ready:
        reasons.append("lookup candidates can seed the next claim step")

    return {
        "pressure_is_proof": False,
        "level": level,
        "reasons": reasons,
        "recommended_tool": recommended_tool,
        "recommended_mode": recommended_mode,
        "chain_starter_ready": chain_ready,
        "next_action": (
            f"reason_step mode={recommended_mode} using claim_ref and relation_claim_ref"
            if recommended_tool == "reason_step"
            else "run lookup to find CLM candidates for the next STEP-*"
            if recommended_tool == "lookup"
            else "inspect reason-current and repair the ledger"
        ),
    }
