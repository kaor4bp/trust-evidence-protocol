"""Restriction record payload and scope helpers."""

from __future__ import annotations


def resolve_restriction_scope(
    applies_to: str,
    project_refs: list[str],
    task_refs: list[str],
    current_project: str | None,
    current_task: str | None,
) -> tuple[list[str], list[str]]:
    resolved_project_refs = project_refs
    resolved_task_refs = task_refs
    if applies_to == "project" and not resolved_project_refs and current_project:
        resolved_project_refs = [current_project]
    if applies_to == "task" and not resolved_task_refs and current_task:
        resolved_task_refs = [current_task]
    return resolved_project_refs, resolved_task_refs


def build_restriction_payload(
    record_id: str,
    timestamp: str,
    scope: str,
    title: str,
    applies_to: str,
    severity: str,
    rules: list[str],
    project_refs: list[str],
    task_refs: list[str],
    related_claim_refs: list[str],
    supersedes_refs: list[str],
    imposed_by: str,
    imposed_at: str | None,
    tags: list[str],
    note: str,
) -> dict:
    return {
        "id": record_id,
        "record_type": "restriction",
        "scope": scope.strip(),
        "title": title.strip(),
        "status": "active",
        "applies_to": applies_to,
        "severity": severity,
        "rules": rules,
        "project_refs": project_refs,
        "task_refs": task_refs,
        "related_claim_refs": related_claim_refs,
        "supersedes_refs": supersedes_refs,
        "imposed_by": imposed_by.strip(),
        "imposed_at": (imposed_at or timestamp).strip(),
        "created_at": timestamp,
        "updated_at": timestamp,
        "tags": tags,
        "note": note.strip(),
    }
