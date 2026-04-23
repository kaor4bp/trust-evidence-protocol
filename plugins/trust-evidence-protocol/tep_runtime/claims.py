"""Claim lifecycle, attention, and retrieval helpers."""

from __future__ import annotations

from datetime import datetime

from .notes import append_note


def build_claim_payload(
    record_id: str,
    timestamp: str,
    scope: str,
    plane: str,
    status: str,
    statement: str,
    source_refs: list[str],
    support_refs: list[str],
    contradiction_refs: list[str],
    derived_from: list[str],
    claim_kind: str | None,
    confidence: str | None,
    comparison: dict | None,
    relation: dict | None,
    logic: dict | None,
    recorded_at: str | None,
    project_refs: list[str],
    task_refs: list[str],
    tags: list[str],
    red_flags: list[str],
    note: str,
) -> dict:
    payload = {
        "id": record_id,
        "record_type": "claim",
        "plane": plane,
        "status": status,
        "scope": scope.strip(),
        "statement": statement.strip(),
        "source_refs": source_refs,
        "support_refs": support_refs,
        "contradiction_refs": contradiction_refs,
        "derived_from": derived_from,
        "project_refs": project_refs,
        "task_refs": task_refs,
        "recorded_at": (recorded_at or timestamp).strip(),
        "tags": tags,
        "red_flags": red_flags,
        "note": note.strip(),
    }
    if claim_kind:
        payload["claim_kind"] = claim_kind
    if confidence:
        payload["confidence"] = confidence
    if comparison:
        payload["comparison"] = comparison
    if relation:
        payload["relation"] = relation
    if logic:
        payload["logic"] = logic
    return payload


def parse_timestamp(value: str) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def claim_lifecycle(data: dict) -> dict:
    lifecycle = data.get("lifecycle")
    if isinstance(lifecycle, dict):
        return lifecycle
    return {}


def claim_lifecycle_state(data: dict) -> str:
    state = str(claim_lifecycle(data).get("state", "")).strip()
    return state or "active"


def claim_attention(data: dict) -> str:
    lifecycle = claim_lifecycle(data)
    attention = str(lifecycle.get("attention", "")).strip()
    if attention:
        return attention
    state = claim_lifecycle_state(data)
    if state == "active":
        return "normal"
    if state in {"resolved", "historical"}:
        return "fallback-only"
    return "explicit-only"


def claim_is_fallback(data: dict) -> bool:
    return data.get("record_type") == "claim" and (
        claim_lifecycle_state(data) in {"resolved", "historical", "archived"}
        or claim_attention(data) in {"fallback-only", "explicit-only"}
    )


def claim_is_archived(data: dict) -> bool:
    return data.get("record_type") == "claim" and (
        claim_lifecycle_state(data) == "archived" or claim_attention(data) == "explicit-only"
    )


def claim_retrieval_tier(data: dict, explicit_refs: set[str] | None = None) -> int:
    record_id = str(data.get("id", "")).strip()
    if explicit_refs and record_id in explicit_refs:
        return 4
    if data.get("record_type") != "claim":
        return 2
    attention = claim_attention(data)
    state = claim_lifecycle_state(data)
    if state == "active" and attention == "normal":
        return 3
    if state == "active" and attention == "low":
        return 2
    if state in {"resolved", "historical"} or attention == "fallback-only":
        return 1
    return 0


def action_reference_timestamp(data: dict) -> datetime | None:
    for key in ("executed_at", "planned_at", "updated_at", "created_at"):
        timestamp = parse_timestamp(str(data.get(key, "")).strip())
        if timestamp is not None:
            return timestamp
    return None


def claim_lifecycle_transition_timestamp(data: dict) -> datetime | None:
    lifecycle = claim_lifecycle(data)
    timestamps = [
        parse_timestamp(str(lifecycle.get(key, "")).strip())
        for key in ("resolved_at", "archived_at", "historical_at")
    ]
    present = [timestamp for timestamp in timestamps if timestamp is not None]
    if not present:
        return None
    return min(present)


def claim_blocks_current_action(data: dict, action: dict) -> bool:
    if not claim_is_fallback(data):
        return False
    action_time = action_reference_timestamp(action)
    transition_time = claim_lifecycle_transition_timestamp(data)
    if action_time is None or transition_time is None:
        return True
    try:
        return action_time >= transition_time
    except TypeError:
        return True


def build_claim_lifecycle_history_entry(
    state: str,
    attention: str,
    timestamp: str,
    note: str,
    details: dict | None = None,
) -> dict:
    entry = {
        "state": state,
        "attention": attention,
        "at": timestamp,
        "note": note.strip(),
    }
    for key, value in (details or {}).items():
        if value:
            entry[key] = value
    return entry


def mutate_claim_lifecycle_payload(
    claim_payload: dict,
    timestamp: str,
    state: str,
    attention: str,
    note: str,
    current_project_ref: str | None = None,
    resolved_by_claim_refs: list[str] | None = None,
    resolved_by_action_refs: list[str] | None = None,
    reactivation_conditions: list[str] | None = None,
) -> dict:
    payload = dict(claim_payload)
    lifecycle = dict(claim_lifecycle(payload))
    lifecycle["state"] = state
    lifecycle["attention"] = attention
    lifecycle["reason"] = note.strip()
    history_details: dict = {}
    if state == "resolved":
        lifecycle["resolved_at"] = timestamp
        lifecycle["resolved_by_claim_refs"] = resolved_by_claim_refs or []
        lifecycle["resolved_by_action_refs"] = resolved_by_action_refs or []
        if reactivation_conditions:
            lifecycle["reactivation_conditions"] = reactivation_conditions
        history_details = {
            "resolved_by_claim_refs": lifecycle.get("resolved_by_claim_refs", []),
            "resolved_by_action_refs": lifecycle.get("resolved_by_action_refs", []),
            "reactivation_conditions": lifecycle.get("reactivation_conditions", []),
        }
    elif state == "archived":
        lifecycle["archived_at"] = timestamp
        history_details = {
            "resolved_by_claim_refs": lifecycle.get("resolved_by_claim_refs", []),
            "resolved_by_action_refs": lifecycle.get("resolved_by_action_refs", []),
        }
    elif state == "active":
        lifecycle["restored_at"] = timestamp
        for key in (
            "resolved_at",
            "archived_at",
            "historical_at",
            "resolved_by_claim_refs",
            "resolved_by_action_refs",
            "reactivation_conditions",
        ):
            lifecycle.pop(key, None)
    history = lifecycle.get("history", [])
    if not isinstance(history, list):
        history = []
    else:
        history = list(history)
    history.append(build_claim_lifecycle_history_entry(state, attention, timestamp, note, details=history_details))
    lifecycle["history"] = history
    payload["lifecycle"] = lifecycle
    if current_project_ref and not payload.get("project_refs"):
        payload["project_refs"] = [current_project_ref]
    payload["updated_at"] = timestamp
    payload["note"] = append_note(
        str(payload.get("note", "")),
        f"[{timestamp}] lifecycle={state}/{attention}: {note.strip()}",
    )
    return payload
