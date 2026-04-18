"""Workspace record payload helpers."""

from __future__ import annotations

from .notes import append_note


def build_workspace_payload(
    record_id: str,
    timestamp: str,
    workspace_key: str,
    title: str,
    status: str,
    context_root: str,
    root_refs: list[str],
    project_refs: list[str],
    tags: list[str],
    note: str,
) -> dict:
    return {
        "id": record_id,
        "record_type": "workspace",
        "scope": workspace_key.strip(),
        "workspace_key": workspace_key.strip(),
        "title": title.strip(),
        "status": status,
        "context_root": context_root.strip(),
        "root_refs": root_refs,
        "project_refs": project_refs,
        "created_at": timestamp,
        "updated_at": timestamp,
        "tags": tags,
        "note": note.strip(),
    }


def assign_workspace_payload(record_payload: dict, timestamp: str, workspace_ref: str, note: str | None) -> dict:
    payload = dict(record_payload)
    payload["workspace_refs"] = sorted({*payload.get("workspace_refs", []), workspace_ref})
    payload["note"] = append_note(
        str(payload.get("note", "")),
        note or f"[{timestamp}] assigned to workspace {workspace_ref}",
    )
    if "updated_at" in payload:
        payload["updated_at"] = timestamp
    return payload
