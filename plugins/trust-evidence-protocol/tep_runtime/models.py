"""Model record payload helpers."""

from __future__ import annotations

from .notes import append_note


def build_model_payload(
    record_id: str,
    timestamp: str,
    knowledge_class: str,
    domain: str,
    scope: str,
    aspect: str,
    status: str,
    is_primary: bool,
    summary: str,
    claim_refs: list[str],
    open_question_refs: list[str],
    hypothesis_refs: list[str],
    related_model_refs: list[str],
    supersedes_refs: list[str],
    promoted_from_refs: list[str],
    project_refs: list[str],
    task_refs: list[str],
    note: str,
) -> dict:
    return {
        "id": record_id,
        "record_type": "model",
        "knowledge_class": knowledge_class,
        "domain": domain.strip(),
        "scope": scope.strip(),
        "aspect": aspect.strip(),
        "status": status,
        "is_primary": is_primary,
        "summary": summary.strip(),
        "claim_refs": claim_refs,
        "open_question_refs": open_question_refs,
        "hypothesis_refs": hypothesis_refs,
        "related_model_refs": related_model_refs,
        "supersedes_refs": supersedes_refs,
        "promoted_from_refs": promoted_from_refs,
        "project_refs": project_refs,
        "task_refs": task_refs,
        "updated_at": timestamp,
        "note": note.strip(),
    }


def promote_model_to_domain_payloads(
    source_payload: dict,
    timestamp: str,
    source_model_ref: str,
    promoted_model_id: str,
    note: str | None,
) -> tuple[dict, dict]:
    source_update = dict(source_payload)
    source_update["status"] = "superseded"
    source_update["is_primary"] = False
    source_update["updated_at"] = timestamp
    source_update["note"] = append_note(
        str(source_update.get("note", "")),
        f"[{timestamp}] superseded by domain promotion from {source_model_ref}",
    )

    promoted = dict(source_payload)
    promoted["id"] = promoted_model_id
    promoted["knowledge_class"] = "domain"
    promoted["status"] = "stable"
    promoted["updated_at"] = timestamp
    promoted["promoted_from_refs"] = sorted({*promoted.get("promoted_from_refs", []), source_model_ref})
    promoted["note"] = append_note(
        str(promoted.get("note", "")),
        note or f"[{timestamp}] promoted to domain knowledge from {source_model_ref}",
    )
    return source_update, promoted
