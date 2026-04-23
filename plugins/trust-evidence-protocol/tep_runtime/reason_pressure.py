"""Reason-ledge briefing and pressure helpers for agent routes."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .reason_ledger import latest_reason_step, validate_reason_ledger
from .scopes import current_task_ref


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


def build_start_briefing(root: Path, records: dict[str, dict], *, intent: str = "auto", limit: int = 5) -> dict[str, Any]:
    """Return a compact, non-proof briefing over current reasoning state."""

    validation = validate_reason_ledger(root)
    task_ref = current_task_ref(root)
    entries = validation.get("entries", []) if validation.get("ok") else []
    task_steps = [
        entry
        for entry in entries
        if str(entry.get("entry_type", "")).strip() == "step"
        and (not task_ref or str(entry.get("task_ref", "")).strip() == task_ref)
    ]
    current = latest_reason_step(entries, task_ref) if validation.get("ok") else None
    branches: dict[str, dict[str, Any]] = {}
    for step in task_steps:
        branch = str(step.get("branch") or "main").strip() or "main"
        slot = branches.setdefault(branch, {"branch": branch, "step_count": 0, "latest_reason_ref": "", "latest_mode": "", "latest_why": ""})
        slot["step_count"] += 1
        slot["latest_reason_ref"] = str(step.get("id", "")).strip()
        slot["latest_mode"] = str(step.get("mode", "")).strip()
        slot["latest_why"] = str(step.get("why", "")).strip()

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
        "confirm the current REASON branch still matches the next intent",
    ]
    if not current:
        checks.append("create the first REASON-* step before substantial work")
    elif str(current.get("mode", "")).strip() != expected_mode:
        checks.append(f"extend or fork REASON-* for mode={expected_mode}")

    return {
        "briefing_is_proof": False,
        "ledger_ok": bool(validation.get("ok")),
        "ledger_errors": validation.get("errors", []),
        "task_ref": task_ref or "",
        "expected_reason_mode": expected_mode,
        "current_reason_ref": str(current.get("id", "")).strip() if isinstance(current, dict) else "",
        "current_branch": str(current.get("branch", "main")).strip() if isinstance(current, dict) else "",
        "current_mode": str(current.get("mode", "")).strip() if isinstance(current, dict) else "",
        "current_why": str(current.get("why", "")).strip() if isinstance(current, dict) else "",
        "recent_steps": [
            {
                "ref": str(step.get("id", "")).strip(),
                "mode": str(step.get("mode", "")).strip(),
                "branch": str(step.get("branch", "main")).strip() or "main",
                "parent_refs": [str(ref).strip() for ref in step.get("parent_refs", []) if str(ref).strip()],
                "why": str(step.get("why", "")).strip(),
                "created_at": str(step.get("created_at", "")).strip(),
            }
            for step in task_steps[-limit:]
        ],
        "branches": sorted(branches.values(), key=lambda item: str(item.get("branch", ""))),
        "recent_actions": recent_actions,
        "checks": checks,
    }


def build_reason_pressure(
    root: Path,
    records: dict[str, dict],
    *,
    intent: str = "auto",
    chain_starter: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return route pressure that makes REASON-* the easiest next step."""

    briefing = build_start_briefing(root, records, intent=intent)
    expected_mode = str(briefing.get("expected_reason_mode") or reason_mode_for_intent(intent))
    current_reason_ref = str(briefing.get("current_reason_ref") or "")
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
        reasons.append("reason ledger is invalid or tampered")
        recommended_tool = "reason-current"
    elif not current_reason_ref:
        level = "high" if intent in {"plan", "edit", "test", "final", "answer", "permission"} else "medium"
        reasons.append("current task has no REASON-* step")
        recommended_tool = "reason_step" if chain_ready else "lookup"
    elif current_mode != expected_mode and intent in {"plan", "edit", "test", "answer", "permission"}:
        level = "medium"
        reasons.append(f"current REASON-* mode is {current_mode or 'none'}, expected {expected_mode}")
        recommended_tool = "reason_step" if chain_ready else "lookup"
    else:
        level = "low"
        reasons.append("current REASON-* exists; extend it when observations or direction change")
        recommended_tool = "lookup"

    if chain_ready:
        reasons.append("lookup chain_starter is ready for reason_step")

    return {
        "pressure_is_proof": False,
        "level": level,
        "reasons": reasons,
        "recommended_tool": recommended_tool,
        "recommended_mode": recommended_mode,
        "chain_starter_ready": chain_ready,
        "next_action": (
            f"reason_step mode={recommended_mode} using lookup.chain_starter"
            if recommended_tool == "reason_step"
            else "run lookup to build a chain_starter for the next REASON-*"
            if recommended_tool == "lookup"
            else "inspect reason-current and repair the ledger"
        ),
    }
