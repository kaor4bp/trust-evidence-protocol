"""Scope-aware canonical record retrieval helpers."""

from __future__ import annotations

from .claims import claim_is_archived, claim_is_fallback, claim_retrieval_tier
from .scopes import guideline_applies, permission_applies, record_belongs_to_project, record_belongs_to_task
from .search import score_record


EXCLUDED_RETRIEVAL_STATUSES = {"superseded", "rejected", "abandoned", "invalid", "wont-fix"}
EXCLUDED_FALLBACK_STATUSES = {"rejected", "abandoned", "invalid", "wont-fix"}


def select_records(
    records: dict[str, dict],
    record_type: str,
    terms: set[str],
    limit: int,
    explicit_refs: set[str] | None = None,
    project_ref: str | None = None,
    task_ref: str | None = None,
) -> list[dict]:
    explicit_refs = explicit_refs or set()
    candidates = [
        data
        for data in records.values()
        if data.get("record_type") == record_type
        and (data.get("id") in explicit_refs or data.get("status") not in EXCLUDED_RETRIEVAL_STATUSES)
        and (data.get("id") in explicit_refs or record_belongs_to_project(data, project_ref))
        and (data.get("id") in explicit_refs or record_belongs_to_task(data, task_ref))
        and not (record_type == "claim" and claim_is_fallback(data) and data.get("id") not in explicit_refs)
    ]
    ranked = []
    for data in candidates:
        score = score_record(data, terms, explicit_refs=explicit_refs)
        if score <= 0:
            continue
        timestamp = str(data.get("updated_at") or data.get("recorded_at") or "")
        if record_type == "claim":
            ranked.append((claim_retrieval_tier(data, explicit_refs=explicit_refs), score, timestamp, data))
        else:
            ranked.append((0, score, timestamp, data))
    selected = [
        data
        for _, _, _, data in sorted(ranked, key=lambda item: (item[0], item[1], item[2]), reverse=True)
    ]
    return selected[:limit]


def select_fallback_claims(
    records: dict[str, dict],
    terms: set[str],
    limit: int,
    project_ref: str | None = None,
    task_ref: str | None = None,
) -> list[dict]:
    ranked = []
    for data in records.values():
        if data.get("record_type") != "claim":
            continue
        if not claim_is_fallback(data) or claim_is_archived(data):
            continue
        if data.get("status") in EXCLUDED_FALLBACK_STATUSES:
            continue
        if not record_belongs_to_project(data, project_ref) or not record_belongs_to_task(data, task_ref):
            continue
        score = score_record(data, terms)
        if score <= 0:
            continue
        timestamp = str(data.get("updated_at") or data.get("recorded_at") or "")
        ranked.append((score, timestamp, data))
    return [data for _, _, data in sorted(ranked, key=lambda item: (item[0], item[1]), reverse=True)][:limit]


def active_permissions_for(
    records: dict[str, dict],
    terms: set[str],
    project_ref: str | None,
    task_ref: str | None,
    limit: int,
) -> list[dict]:
    candidates = [
        permission
        for permission in records.values()
        if permission.get("record_type") == "permission"
        and permission_applies(permission, project_ref, task_ref)
    ]
    ranked = [
        (
            100 if task_ref and task_ref in permission.get("task_refs", []) else score_record(permission, terms),
            str(permission.get("granted_at", "")),
            permission,
        )
        for permission in candidates
    ]
    selected = [
        permission
        for score, _, permission in sorted(ranked, key=lambda item: (item[0], item[1]), reverse=True)
        if score > 0
        or (
            str(permission.get("applies_to", "")).strip()
            or ("task" if permission.get("task_refs") else "project" if permission.get("project_refs") else "global")
        )
        in {"global", "project", "task"}
    ]
    return selected[:limit]


def active_guidelines_for(
    records: dict[str, dict],
    terms: set[str],
    project_ref: str | None,
    task_ref: str | None,
    limit: int,
) -> list[dict]:
    priority_order = {"required": 0, "preferred": 1, "optional": 2}
    candidates = [
        guideline
        for guideline in records.values()
        if guideline.get("record_type") == "guideline" and guideline_applies(guideline, project_ref, task_ref)
    ]
    ranked = [
        (
            100 if task_ref and task_ref in guideline.get("task_refs", []) else score_record(guideline, terms),
            -priority_order.get(str(guideline.get("priority", "")).strip(), 9),
            str(guideline.get("updated_at", "")),
            guideline,
        )
        for guideline in candidates
    ]
    selected = [
        guideline
        for score, _, _, guideline in sorted(ranked, key=lambda item: (item[0], item[1], item[2]), reverse=True)
        if score > 0 or str(guideline.get("applies_to", "")).strip() in {"global", "project", "task"}
    ]
    return selected[:limit]
