from __future__ import annotations


def build_action_payload(
    record_id: str,
    timestamp: str,
    kind: str,
    scope: str,
    justified_by: list[str],
    safety_class: str,
    status: str,
    planned_at: str | None,
    executed_at: str | None,
    project_refs: list[str],
    task_refs: list[str],
    tags: list[str],
    note: str,
) -> dict:
    payload = {
        "id": record_id,
        "record_type": "action",
        "kind": kind.strip(),
        "scope": scope.strip(),
        "justified_by": justified_by,
        "safety_class": safety_class,
        "status": status,
        "project_refs": project_refs,
        "task_refs": task_refs,
        "tags": tags,
        "note": note.strip(),
    }
    if planned_at:
        payload["planned_at"] = planned_at.strip()
    elif status != "executed":
        payload["planned_at"] = timestamp
    if executed_at:
        payload["executed_at"] = executed_at.strip()
    elif status == "executed":
        payload["executed_at"] = timestamp
    return payload
