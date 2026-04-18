"""Shared helpers for model/flow knowledge records."""

from __future__ import annotations

from .notes import append_note


KNOWLEDGE_RECORD_TYPES = {"model", "flow"}
STALE_TERMINAL_STATUSES = {"stale", "superseded"}


def stale_knowledge_target_ids(records: dict[str, dict], candidate_ids: list[str]) -> list[str]:
    return [
        record_id
        for record_id in candidate_ids
        if record_id in records
        and records[record_id].get("record_type") in KNOWLEDGE_RECORD_TYPES
        and str(records[record_id].get("status", "")).strip() not in STALE_TERMINAL_STATUSES
    ]


def public_knowledge_record_payload(data: dict) -> dict:
    return {key: value for key, value in data.items() if not str(key).startswith("_")}


def mark_knowledge_records_stale_payloads(
    records: dict[str, dict],
    target_ids: list[str],
    timestamp: str,
    claim_ref: str,
    note: str | None,
) -> dict[str, dict]:
    updates: dict[str, dict] = {}
    for record_id in target_ids:
        payload = public_knowledge_record_payload(records[record_id])
        payload["status"] = "stale"
        payload["updated_at"] = timestamp
        payload["note"] = append_note(
            str(payload.get("note", "")),
            note or f"[{timestamp}] marked stale from weakened claim {claim_ref}",
        )
        updates[record_id] = payload
    return updates
