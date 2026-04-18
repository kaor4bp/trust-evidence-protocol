"""Guideline record payload and scope helpers."""

from __future__ import annotations


def resolve_guideline_scope(
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


def build_guideline_payload(
    record_id: str,
    timestamp: str,
    scope: str,
    domain: str,
    applies_to: str,
    priority: str,
    rule: str,
    source_refs: list[str],
    project_refs: list[str],
    task_refs: list[str],
    related_claim_refs: list[str],
    conflict_refs: list[str],
    supersedes_refs: list[str],
    examples: list[str],
    rationale: str | None,
    tags: list[str],
    note: str,
) -> dict:
    return {
        "id": record_id,
        "record_type": "guideline",
        "scope": scope.strip(),
        "domain": domain,
        "status": "active",
        "applies_to": applies_to,
        "priority": priority,
        "rule": rule.strip(),
        "rationale": (rationale or "").strip(),
        "source_refs": source_refs,
        "project_refs": project_refs,
        "task_refs": task_refs,
        "related_claim_refs": related_claim_refs,
        "conflict_refs": conflict_refs,
        "supersedes_refs": supersedes_refs,
        "examples": examples,
        "created_at": timestamp,
        "updated_at": timestamp,
        "tags": tags,
        "note": note.strip(),
    }
