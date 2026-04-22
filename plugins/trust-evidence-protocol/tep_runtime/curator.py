"""Curator pool records for bounded knowledge-curation agents."""

from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from typing import Any

from .claims import claim_is_fallback
from .search import concise, public_record_summary, record_search_timestamp, record_summary, score_record
from .validation import safe_list

CURATOR_POOL_KINDS = {"health", "duplicates", "conflicts", "modeling", "flow", "staleness"}
CURATOR_POOL_STATUSES = {"active", "closed", "stale"}
CURATOR_ALLOWED_ACTIONS = [
    "ask-user-clarifying-questions",
    "propose-links",
    "propose-lifecycle-changes",
    "record-user-supported-theory-claims",
    "draft-working-models",
    "draft-working-flows",
    "record-open-questions",
    "record-proposals",
]
CURATOR_FORBIDDEN_ACTIONS = [
    "run-runtime-commands",
    "edit-project-code",
    "change-current-task-or-workspace",
    "change-allowed-freedom",
    "create-runtime-claims-without-run-provenance",
    "read-raw-records-outside-pool",
]


def record_digest(record: dict) -> str:
    public = {key: value for key, value in record.items() if not str(key).startswith("_")}
    payload = json.dumps(public, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def scoped_to_workspace(records: dict[str, dict], record: dict, workspace_ref: str) -> bool:
    if record.get("id") == workspace_ref:
        return True
    if workspace_ref in safe_list(record, "workspace_refs"):
        return True
    workspace = records.get(workspace_ref, {})
    workspace_projects = set(safe_list(workspace, "project_refs"))
    return bool(workspace_projects and workspace_projects.intersection(safe_list(record, "project_refs")))


def curator_record_in_scope(
    records: dict[str, dict],
    record: dict,
    workspace_ref: str,
    project_ref: str | None,
    task_ref: str | None,
) -> bool:
    if not scoped_to_workspace(records, record, workspace_ref):
        return False
    if project_ref:
        if record.get("id") == project_ref:
            return True
        if project_ref not in safe_list(record, "project_refs"):
            return False
    if task_ref:
        if record.get("id") == task_ref:
            return True
        task_refs = safe_list(record, "task_refs")
        if task_refs and task_ref not in task_refs:
            return False
    return True


def curator_summary(record: dict) -> dict[str, Any]:
    summary = public_record_summary(record)
    summary["curator_candidate_is_proof"] = False
    return summary


def hot_record_counts(access_events: list[dict], scoped_ids: set[str]) -> Counter:
    counts: Counter = Counter()
    for event in access_events:
        for ref in safe_list(event, "record_refs"):
            if ref in scoped_ids:
                counts[ref] += 1
    return counts


def normalized_statement(record: dict) -> str:
    value = str(record.get("statement") or record.get("summary") or record.get("question") or "").strip().lower()
    return " ".join(value.split())


def duplicate_groups(scoped_records: list[dict]) -> list[dict]:
    grouped: dict[str, list[str]] = defaultdict(list)
    for record in scoped_records:
        if record.get("record_type") != "claim":
            continue
        key = normalized_statement(record)
        if key:
            grouped[key].append(str(record.get("id", "")))
    return [
        {"kind": "exact-statement", "record_refs": sorted(refs), "candidate_is_proof": False}
        for _, refs in sorted(grouped.items())
        if len(refs) > 1
    ]


def inactive_task_wctx(records: dict[str, dict], scoped_records: list[dict]) -> list[dict]:
    findings = []
    for record in scoped_records:
        if record.get("record_type") != "working_context" or str(record.get("status", "")).strip() != "active":
            continue
        inactive_refs = []
        for task_ref in safe_list(record, "task_refs"):
            task = records.get(task_ref, {})
            if task.get("record_type") == "task" and str(task.get("status", "")).strip() != "active":
                inactive_refs.append(task_ref)
        if inactive_refs:
            findings.append(
                {
                    "record_ref": record.get("id"),
                    "task_refs": inactive_refs,
                    "candidate_is_proof": False,
                    "suggestion": "close or fork this WCTX before reusing it as active focus",
                }
            )
    return findings


def weak_model_flow_records(scoped_records: list[dict]) -> list[dict]:
    findings = []
    for record in scoped_records:
        record_type = record.get("record_type")
        status = str(record.get("status", "")).strip()
        if record_type == "model" and status in {"working", "stable"} and not safe_list(record, "claim_refs"):
            findings.append({"record_ref": record.get("id"), "reason": "model has no claim_refs", "candidate_is_proof": False})
        if record_type == "flow" and status in {"working", "stable"} and not safe_list(record, "model_refs"):
            findings.append({"record_ref": record.get("id"), "reason": "flow has no model_refs", "candidate_is_proof": False})
    return findings


def contradiction_records(scoped_records: list[dict]) -> list[dict]:
    findings = []
    for record in scoped_records:
        if record.get("record_type") == "claim" and safe_list(record, "contradiction_refs"):
            findings.append(
                {
                    "record_ref": record.get("id"),
                    "contradiction_refs": safe_list(record, "contradiction_refs"),
                    "candidate_is_proof": False,
                }
            )
    return findings


def stale_candidates(scoped_records: list[dict]) -> list[dict]:
    findings = []
    for record in scoped_records:
        record_type = record.get("record_type")
        status = str(record.get("status", "")).strip()
        if record_type == "claim" and (claim_is_fallback(record) or status in {"contested", "rejected"}):
            findings.append(
                {
                    "record_ref": record.get("id"),
                    "status": status,
                    "summary": record_summary(record),
                    "candidate_is_proof": False,
                }
            )
    return findings


def candidate_reason(record: dict, hot_counts: Counter, review_kind: str) -> str:
    record_id = str(record.get("id", ""))
    if hot_counts.get(record_id):
        return f"hot-record:{hot_counts[record_id]}"
    record_type = str(record.get("record_type", ""))
    if review_kind == "modeling" and record_type in {"claim", "model", "open_question"}:
        return "modeling-context"
    if review_kind == "flow" and record_type in {"claim", "model", "flow", "open_question"}:
        return "flow-context"
    if review_kind == "conflicts" and (safe_list(record, "contradiction_refs") or str(record.get("status", "")) == "contested"):
        return "conflict-context"
    if review_kind == "staleness" and record_type in {"claim", "model", "flow"}:
        return "staleness-context"
    return "scope-context"


def select_curator_candidates(
    scoped_records: list[dict],
    terms: set[str],
    review_kind: str,
    hot_counts: Counter,
    limit: int,
) -> list[dict]:
    scored = []
    for record in scoped_records:
        record_type = str(record.get("record_type", ""))
        if record_type in {"workspace", "project", "task"}:
            continue
        score = 0
        if terms:
            score += score_record(record, terms)
        score += min(hot_counts.get(str(record.get("id", "")), 0), 10)
        if review_kind == "modeling" and record_type in {"claim", "model", "open_question"}:
            score += 3
        elif review_kind == "flow" and record_type in {"claim", "model", "flow", "open_question"}:
            score += 3
        elif review_kind == "duplicates" and record_type == "claim":
            score += 3
        elif review_kind == "conflicts" and (safe_list(record, "contradiction_refs") or str(record.get("status", "")) == "contested"):
            score += 4
        elif review_kind == "staleness" and record_type in {"claim", "model", "flow"}:
            score += 2
        elif review_kind == "health":
            score += 1
        if score <= 0:
            continue
        scored.append((score, record_search_timestamp(record), str(record.get("id", "")), record))
    selected = sorted(scored, key=lambda item: (item[0], item[1], item[2]), reverse=True)[: max(1, limit)]
    return [
        {
            **curator_summary(record),
            "candidate_reason": candidate_reason(record, hot_counts, review_kind),
        }
        for _, _, _, record in selected
    ]


def curator_source_quotes(records: dict[str, dict], candidate_refs: list[str], limit: int = 8) -> list[dict]:
    quotes = []
    for record_ref in candidate_refs:
        record = records.get(record_ref, {})
        for source_ref in safe_list(record, "source_refs"):
            source = records.get(source_ref, {})
            if source.get("record_type") != "source":
                continue
            quotes.append(
                {
                    "record_ref": record_ref,
                    "source_ref": source_ref,
                    "source_kind": source.get("source_kind", ""),
                    "critique_status": source.get("critique_status", ""),
                    "quote": concise(str(source.get("quote", "")), 220),
                    "quote_is_proof": False,
                }
            )
            if len(quotes) >= limit:
                return quotes
    return quotes


def candidate_edges(records: dict[str, dict], candidate_refs: list[str]) -> list[dict]:
    candidate_set = set(candidate_refs)
    edges = []
    for record_ref in candidate_refs:
        record = records.get(record_ref, {})
        for key in ("source_refs", "support_refs", "contradiction_refs", "claim_refs", "model_refs", "flow_refs", "open_question_refs"):
            for target in safe_list(record, key):
                if target in candidate_set:
                    edges.append({"from": record_ref, "to": target, "field": key, "edge_is_proof": False})
    return edges


def curator_recommended_questions(review_kind: str, categories: dict[str, list]) -> list[str]:
    questions = []
    if categories.get("duplicate_candidates"):
        questions.append("Which duplicate candidates describe the same durable fact, and which should stay separate?")
    if categories.get("conflict_candidates"):
        questions.append("Which conflicting claims reflect accepted system drift versus an actual contradiction?")
    if categories.get("stale_candidates"):
        questions.append("Which stale or fallback-only facts should be demoted, superseded, or preserved for history?")
    if review_kind in {"modeling", "flow"}:
        questions.append("Which supported theory claims should be promoted into MODEL/FLOW records?")
    if categories.get("inactive_task_wctx"):
        questions.append("Which active WCTX records tied to inactive tasks should be closed or forked?")
    return questions


def build_curator_pool_payload(
    *,
    records: dict[str, dict],
    access_events: list[dict],
    record_id: str,
    timestamp: str,
    workspace_ref: str,
    project_ref: str | None,
    task_ref: str | None,
    review_kind: str,
    query: str,
    limit: int,
    note: str,
) -> dict:
    workspace = records[workspace_ref]
    scoped_records = [
        record
        for record in records.values()
        if curator_record_in_scope(records, record, workspace_ref, project_ref, task_ref)
    ]
    scoped_ids = {str(record.get("id", "")) for record in scoped_records}
    terms = {term for term in query.lower().split() if len(term) >= 3}
    hot_counts = hot_record_counts(access_events, scoped_ids)
    candidates = select_curator_candidates(scoped_records, terms, review_kind, hot_counts, limit)
    candidate_refs = [str(item.get("id", "")) for item in candidates if str(item.get("id", ""))]
    categories = {
        "hot_records": [
            {"record_ref": ref, "access_count": count, "candidate_is_proof": False}
            for ref, count in hot_counts.most_common(10)
        ],
        "duplicate_candidates": duplicate_groups(scoped_records),
        "conflict_candidates": contradiction_records(scoped_records),
        "inactive_task_wctx": inactive_task_wctx(records, scoped_records),
        "weak_model_flow_records": weak_model_flow_records(scoped_records),
        "stale_candidates": stale_candidates(scoped_records),
    }
    existing_models = [curator_summary(record) for record in scoped_records if record.get("record_type") == "model"]
    existing_flows = [curator_summary(record) for record in scoped_records if record.get("record_type") == "flow"]
    title_parts = [review_kind, str(workspace.get("workspace_key") or workspace.get("title") or workspace_ref)]
    if project_ref:
        title_parts.append(project_ref)
    if task_ref:
        title_parts.append(task_ref)
    return {
        "id": record_id,
        "record_type": "curator_pool",
        "scope": f"curator.{review_kind}",
        "title": " / ".join(title_parts),
        "status": "active",
        "review_kind": review_kind,
        "query": query,
        "snapshot_at": timestamp,
        "created_at": timestamp,
        "updated_at": timestamp,
        "workspace_ref": workspace_ref,
        "project_ref": project_ref or "",
        "task_ref": task_ref or "",
        "workspace_refs": [workspace_ref],
        "project_refs": [project_ref] if project_ref else [],
        "task_refs": [task_ref] if task_ref else [],
        "selection": {
            "limit": limit,
            "scoped_record_count": len(scoped_records),
            "pool_is_proof": False,
        },
        "candidate_record_refs": candidate_refs,
        "candidate_records": candidates,
        "candidate_edges": candidate_edges(records, candidate_refs),
        "record_fingerprints": [
            {
                "record_ref": record_ref,
                "sha256": record_digest(records[record_ref]),
                "record_type": records[record_ref].get("record_type", ""),
                "updated_at": record_search_timestamp(records[record_ref]),
            }
            for record_ref in candidate_refs
            if record_ref in records
        ],
        "source_quotes": curator_source_quotes(records, candidate_refs),
        "existing_model_refs": [str(item.get("id", "")) for item in existing_models],
        "existing_models": existing_models,
        "existing_flow_refs": [str(item.get("id", "")) for item in existing_flows],
        "existing_flows": existing_flows,
        "categories": categories,
        "recommended_questions": curator_recommended_questions(review_kind, categories),
        "allowed_curator_actions": CURATOR_ALLOWED_ACTIONS,
        "forbidden_actions": CURATOR_FORBIDDEN_ACTIONS,
        "pool_is_proof": False,
        "note": note.strip() or "Curator pool snapshot. Not proof and not authorization.",
    }


def curator_pool_text_lines(pool: dict) -> list[str]:
    lines = [
        "# Curator Pool",
        "",
        "Mode: bounded knowledge-curation snapshot. Not proof and not authorization.",
        f"id: `{pool.get('id')}` status: `{pool.get('status')}` kind: `{pool.get('review_kind')}`",
        f"workspace: `{pool.get('workspace_ref')}` project: `{pool.get('project_ref')}` task: `{pool.get('task_ref')}`",
        f"snapshot_at: `{pool.get('snapshot_at')}` candidates: `{len(pool.get('candidate_records', []))}`",
        "",
        "## Candidate Records",
    ]
    for item in pool.get("candidate_records", [])[:12]:
        lines.append(
            f"- `{item.get('id')}` type=`{item.get('record_type')}` status=`{item.get('status')}` "
            f"reason=`{item.get('candidate_reason')}`: {item.get('summary')}"
        )
    if not pool.get("candidate_records"):
        lines.append("- none")
    lines.extend(["", "## Recommended Questions"])
    for question in pool.get("recommended_questions", []):
        lines.append(f"- {question}")
    if not pool.get("recommended_questions"):
        lines.append("- none")
    lines.extend(["", "## Forbidden Actions"])
    for action in pool.get("forbidden_actions", []):
        lines.append(f"- {action}")
    return lines
