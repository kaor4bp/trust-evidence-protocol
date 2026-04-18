from __future__ import annotations

from .notes import append_note


def build_flow_step(
    step_id: str,
    label: str,
    status: str,
    claim_refs: list[str],
    next_steps: list[str],
    open_question_refs: list[str],
    accepted_deviation_refs: list[str],
) -> dict:
    payload = {
        "id": step_id.strip(),
        "label": label.strip(),
        "status": status,
        "claim_refs": claim_refs,
        "next_steps": next_steps,
    }
    if open_question_refs:
        payload["open_question_refs"] = open_question_refs
    if accepted_deviation_refs:
        payload["accepted_deviation_refs"] = accepted_deviation_refs
    return payload


def build_flow_preconditions(
    claim_refs: list[str],
    hypothesis_refs: list[str],
    note: str | None,
) -> dict:
    payload = {
        "claim_refs": claim_refs,
        "hypothesis_refs": hypothesis_refs,
    }
    if note:
        payload["note"] = note.strip()
    return payload


def build_flow_oracle(
    success_claim_refs: list[str],
    failure_claim_refs: list[str],
    hypothesis_refs: list[str],
    note: str | None,
) -> dict:
    payload = {
        "success_claim_refs": success_claim_refs,
        "failure_claim_refs": failure_claim_refs,
        "hypothesis_refs": hypothesis_refs,
    }
    if note:
        payload["note"] = note.strip()
    return payload


def build_flow_payload(
    record_id: str,
    timestamp: str,
    knowledge_class: str,
    domain: str,
    scope: str,
    status: str,
    is_primary: bool,
    summary: str,
    model_refs: list[str],
    open_question_refs: list[str],
    preconditions: dict,
    oracle: dict,
    steps: list[dict],
    supersedes_refs: list[str],
    promoted_from_refs: list[str],
    project_refs: list[str],
    task_refs: list[str],
    note: str,
) -> dict:
    return {
        "id": record_id,
        "record_type": "flow",
        "knowledge_class": knowledge_class,
        "domain": domain.strip(),
        "scope": scope.strip(),
        "status": status,
        "is_primary": is_primary,
        "summary": summary.strip(),
        "model_refs": model_refs,
        "open_question_refs": open_question_refs,
        "preconditions": preconditions,
        "oracle": oracle,
        "steps": steps,
        "supersedes_refs": supersedes_refs,
        "promoted_from_refs": promoted_from_refs,
        "project_refs": project_refs,
        "task_refs": task_refs,
        "updated_at": timestamp,
        "note": note.strip(),
    }


def promote_flow_to_domain_payloads(
    source_payload: dict,
    timestamp: str,
    source_flow_ref: str,
    promoted_flow_id: str,
    note: str | None,
) -> tuple[dict, dict]:
    source_update = dict(source_payload)
    source_update["status"] = "superseded"
    source_update["is_primary"] = False
    source_update["updated_at"] = timestamp
    source_update["note"] = append_note(
        str(source_update.get("note", "")),
        f"[{timestamp}] superseded by domain promotion from {source_flow_ref}",
    )

    promoted = dict(source_payload)
    promoted["id"] = promoted_flow_id
    promoted["knowledge_class"] = "domain"
    promoted["status"] = "stable"
    promoted["updated_at"] = timestamp
    promoted["promoted_from_refs"] = sorted({*promoted.get("promoted_from_refs", []), source_flow_ref})
    promoted["note"] = append_note(
        str(promoted.get("note", "")),
        note or f"[{timestamp}] promoted to domain knowledge from {source_flow_ref}",
    )
    return source_update, promoted
