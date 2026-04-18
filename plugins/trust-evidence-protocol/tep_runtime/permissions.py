"""Permission record payload and scope helpers."""

from __future__ import annotations


def resolve_permission_scope(
    applies_to: str | None,
    project_refs: list[str],
    task_refs: list[str],
    current_project: str | None,
    current_task: str | None,
) -> tuple[str, list[str], list[str]]:
    resolved_project_refs = project_refs
    resolved_task_refs = task_refs
    if applies_to == "project" and not resolved_project_refs and current_project:
        resolved_project_refs = [current_project]
    if applies_to == "task" and not resolved_task_refs and current_task:
        resolved_task_refs = [current_task]
    resolved_applies_to = applies_to or (
        "task" if resolved_task_refs else "project" if resolved_project_refs else "global"
    )
    return resolved_applies_to, resolved_project_refs, resolved_task_refs


def build_permission_payload(
    record_id: str,
    timestamp: str,
    scope: str,
    applies_to: str,
    granted_by: str,
    grants: list[str],
    project_refs: list[str],
    task_refs: list[str],
    granted_at: str | None,
    tags: list[str],
    note: str,
) -> dict:
    return {
        "id": record_id,
        "record_type": "permission",
        "scope": scope.strip(),
        "applies_to": applies_to,
        "granted_by": granted_by.strip(),
        "granted_at": (granted_at or timestamp).strip(),
        "grants": grants,
        "project_refs": project_refs,
        "task_refs": task_refs,
        "tags": tags,
        "note": note.strip(),
    }
