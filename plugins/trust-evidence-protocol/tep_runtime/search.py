"""Deterministic record text, scoring, and summary helpers."""

from __future__ import annotations

import json

from .claims import claim_is_archived, claim_is_fallback, claim_retrieval_tier
from .scopes import record_belongs_to_project, record_belongs_to_task


def record_search_text(data: dict) -> str:
    fields = (
        "id",
        "record_type",
        "domain",
        "scope",
        "aspect",
        "summary",
        "text",
        "input_kind",
        "session_ref",
        "statement",
        "question",
        "rule",
        "rationale",
        "subject",
        "position",
        "priority",
        "title",
        "task_type",
        "note",
        "status",
        "knowledge_class",
    )
    parts = [str(data.get(key, "")) for key in fields]
    parts.extend(str(item) for item in data.get("tags", []) if item)
    parts.extend(str(item) for item in data.get("examples", []) if item)
    for option in data.get("proposals", []):
        if isinstance(option, dict):
            parts.extend(str(option.get(key, "")) for key in ("title", "why"))
            parts.extend(str(item) for item in option.get("tradeoffs", []) if item)
    for key in ("assumptions", "concerns", "risks", "stop_conditions"):
        for item in data.get(key, []):
            if isinstance(item, dict):
                parts.extend(str(item.get(nested_key, "")) for nested_key in ("text", "mode"))
                parts.extend(str(ref) for ref in item.get("support_refs", []) if ref)
            elif item:
                parts.append(str(item))
    for key in ("context_kind", "parent_context_ref"):
        parts.append(str(data.get(key, "")))
    for key in ("focus_paths", "topic_terms", "topic_seed_refs", "pinned_refs"):
        parts.extend(str(item) for item in data.get(key, []) if item)
    if isinstance(data.get("comparison"), dict):
        parts.extend(str(value) for value in data["comparison"].values())
    if isinstance(data.get("logic"), dict):
        parts.append(json.dumps(data["logic"], ensure_ascii=False, sort_keys=True))
    return " ".join(parts).lower()


def score_record(data: dict, terms: set[str], explicit_refs: set[str] | None = None) -> int:
    if explicit_refs and data.get("id") in explicit_refs:
        return 100
    haystack = record_search_text(data)
    score = sum(1 for term in terms if term in haystack)
    if data.get("is_primary"):
        score += 2
    if data.get("status") in {"working", "stable", "supported", "corroborated", "open"}:
        score += 1
    if data.get("status") in {"superseded", "rejected"}:
        score -= 3
    return score


def search_record_matches(data: dict, terms: set[str]) -> tuple[int, list[str]]:
    haystack = record_search_text(data)
    matched = sorted(term for term in terms if term in haystack)
    if not matched:
        return 0, []
    score = score_record(data, terms)
    if data.get("record_type") == "claim":
        score += claim_retrieval_tier(data)
        if claim_is_archived(data):
            score -= 4
        elif claim_is_fallback(data):
            score -= 2
    return score, matched


def record_search_timestamp(data: dict) -> str:
    return str(
        data.get("updated_at")
        or data.get("recorded_at")
        or data.get("captured_at")
        or data.get("created_at")
        or ""
    )


def ranked_record_search(
    records: dict[str, dict],
    terms: set[str],
    limit: int,
    record_types: list[str],
    project_ref: str | None,
    task_ref: str | None,
    include_fallback: bool,
    include_archived: bool,
) -> list[dict]:
    allowed_types = {item.strip() for item in record_types if item.strip()}
    ranked = []
    for record_id, data in records.items():
        record_type = str(data.get("record_type", "")).strip()
        if allowed_types and record_type not in allowed_types:
            continue
        if not record_belongs_to_project(data, project_ref):
            continue
        if not record_belongs_to_task(data, task_ref):
            continue
        if record_type == "claim":
            if claim_is_archived(data) and not include_archived:
                continue
            if claim_is_fallback(data) and not include_fallback and not claim_is_archived(data):
                continue
        score, matched = search_record_matches(data, terms)
        if score <= 0:
            continue
        ranked.append(
            {
                "score": score,
                "timestamp": record_search_timestamp(data),
                "id": record_id,
                "record": data,
                "matched_terms": matched,
            }
        )

    return sorted(ranked, key=lambda item: (item["score"], item["timestamp"], item["id"]), reverse=True)[:limit]


def concise(value: str, limit: int = 180) -> str:
    text = " ".join(str(value).split())
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "..."


def record_summary(data: dict) -> str:
    record_type = str(data.get("record_type", "")).strip()
    if record_type == "claim":
        return concise(str(data.get("statement", "")), 180)
    if record_type == "input":
        return concise(str(data.get("text", "")) or ", ".join(data.get("artifact_refs", [])), 180)
    if record_type == "source":
        return concise(str(data.get("quote", "")) or ", ".join(data.get("artifact_refs", [])), 180)
    if record_type == "guideline":
        return concise(str(data.get("rule", "")), 180)
    if record_type == "proposal":
        return concise(str(data.get("subject", "")) or str(data.get("position", "")), 180)
    if record_type == "model":
        return concise(str(data.get("summary", "")), 180)
    if record_type == "flow":
        return concise(str(data.get("summary", "")), 180)
    if record_type == "open_question":
        return concise(str(data.get("question", "")), 180)
    return concise(str(data.get("title", "")) or str(data.get("scope", "")) or str(data.get("note", "")), 180)


def public_record_summary(data: dict) -> dict:
    return {
        "id": data.get("id"),
        "record_type": data.get("record_type"),
        "scope": data.get("scope", ""),
        "status": data.get("status", data.get("critique_status", "")),
        "summary": record_summary(data),
    }
