"""Project record payload helpers."""

from __future__ import annotations

from .notes import append_note


def build_project_payload(
    record_id: str,
    timestamp: str,
    project_key: str,
    title: str,
    status: str,
    root_refs: list[str],
    related_project_refs: list[str],
    tags: list[str],
    note: str,
) -> dict:
    return {
        "id": record_id,
        "record_type": "project",
        "scope": project_key.strip(),
        "project_key": project_key.strip(),
        "title": title.strip(),
        "status": status,
        "root_refs": root_refs,
        "related_project_refs": related_project_refs,
        "created_at": timestamp,
        "updated_at": timestamp,
        "tags": tags,
        "note": note.strip(),
    }


def assign_project_payload(record_payload: dict, timestamp: str, project_ref: str, note: str | None) -> dict:
    payload = dict(record_payload)
    payload["project_refs"] = sorted({*payload.get("project_refs", []), project_ref})
    payload["note"] = append_note(
        str(payload.get("note", "")),
        note or f"[{timestamp}] assigned to project {project_ref}",
    )
    if "updated_at" in payload:
        payload["updated_at"] = timestamp
    return payload
