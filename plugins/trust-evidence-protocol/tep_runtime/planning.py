from __future__ import annotations


def build_plan_payload(
    record_id: str,
    timestamp: str,
    scope: str,
    title: str,
    priority: str,
    status: str,
    justified_by: list[str],
    steps: list[str],
    success_criteria: list[str],
    blocked_by: list[str],
    project_refs: list[str],
    task_refs: list[str],
    tags: list[str],
    note: str,
) -> dict:
    return {
        "id": record_id,
        "record_type": "plan",
        "scope": scope.strip(),
        "title": title.strip(),
        "status": status,
        "priority": priority,
        "justified_by": justified_by,
        "steps": steps,
        "success_criteria": success_criteria,
        "blocked_by": blocked_by,
        "project_refs": project_refs,
        "task_refs": task_refs,
        "created_at": timestamp,
        "updated_at": timestamp,
        "tags": tags,
        "note": note.strip(),
    }


def build_debt_payload(
    record_id: str,
    timestamp: str,
    scope: str,
    title: str,
    priority: str,
    status: str,
    evidence_refs: list[str],
    plan_refs: list[str],
    project_refs: list[str],
    task_refs: list[str],
    tags: list[str],
    note: str,
) -> dict:
    return {
        "id": record_id,
        "record_type": "debt",
        "scope": scope.strip(),
        "title": title.strip(),
        "status": status,
        "priority": priority,
        "evidence_refs": evidence_refs,
        "plan_refs": plan_refs,
        "project_refs": project_refs,
        "task_refs": task_refs,
        "created_at": timestamp,
        "updated_at": timestamp,
        "tags": tags,
        "note": note.strip(),
    }
