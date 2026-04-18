"""Open-question record payload helpers."""

from __future__ import annotations


def build_open_question_payload(
    record_id: str,
    timestamp: str,
    domain: str,
    scope: str,
    aspect: str,
    status: str,
    question: str,
    related_claim_refs: list[str],
    related_model_refs: list[str],
    related_flow_refs: list[str],
    resolved_by_claim_refs: list[str],
    project_refs: list[str],
    task_refs: list[str],
    note: str,
) -> dict:
    return {
        "id": record_id,
        "record_type": "open_question",
        "domain": domain.strip(),
        "scope": scope.strip(),
        "aspect": aspect.strip(),
        "status": status,
        "question": question.strip(),
        "related_claim_refs": related_claim_refs,
        "related_model_refs": related_model_refs,
        "related_flow_refs": related_flow_refs,
        "resolved_by_claim_refs": resolved_by_claim_refs,
        "project_refs": project_refs,
        "task_refs": task_refs,
        "created_at": timestamp,
        "note": note.strip(),
    }
