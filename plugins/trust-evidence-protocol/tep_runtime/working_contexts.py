"""Working-context payload, mutation, and display helpers."""

from __future__ import annotations

from .notes import append_note
from .search import concise


def parse_working_context_assumption(raw: str) -> dict:
    parts = [part.strip() for part in raw.split("|")]
    if not parts or not parts[0]:
        raise ValueError("--assumption must start with text")
    mode = parts[1] if len(parts) >= 2 and parts[1] else "exploration-only"
    if mode not in {"exploration-only", "supported", "deprecated"}:
        raise ValueError("--assumption mode must be exploration-only, supported, or deprecated")
    support_refs = [item.strip() for item in parts[2].split(",") if item.strip()] if len(parts) >= 3 else []
    return {
        "text": parts[0],
        "mode": mode,
        "support_refs": support_refs,
    }


def parse_working_context_assumptions(values: list[str]) -> list[dict]:
    return [parse_working_context_assumption(value) for value in values]


def add_remove_values(existing: list[str], additions: list[str], removals: list[str]) -> list[str]:
    values = [str(item).strip() for item in existing if str(item).strip()]
    for addition in additions:
        item = str(addition).strip()
        if item and item not in values:
            values.append(item)
    remove_set = {str(item).strip() for item in removals if str(item).strip()}
    return [item for item in values if item not in remove_set]


def working_context_summary_line(context: dict) -> str:
    return (
        f"`{context.get('id')}` status=`{context.get('status')}` kind=`{context.get('context_kind')}` "
        f"title=\"{concise(context.get('title', ''), 160)}\""
    )


def working_context_detail_lines(context: dict) -> list[str]:
    lines = [f"- {working_context_summary_line(context)}"]
    for key in (
        "pinned_refs",
        "focus_paths",
        "topic_terms",
        "topic_seed_refs",
        "project_refs",
        "task_refs",
        "supersedes_refs",
    ):
        values = context.get(key, [])
        if values:
            lines.append(f"  {key}: {values}")
    parent_ref = str(context.get("parent_context_ref", "")).strip()
    if parent_ref:
        lines.append(f"  parent_context_ref: {parent_ref}")
    assumptions = context.get("assumptions", [])
    if assumptions:
        lines.append("  assumptions:")
        for assumption in assumptions:
            if isinstance(assumption, dict):
                support = assumption.get("support_refs", [])
                suffix = f" support_refs={support}" if support else ""
                lines.append(f"    - mode={assumption.get('mode', 'exploration-only')}: {assumption.get('text', '')}{suffix}")
    concerns = context.get("concerns", [])
    if concerns:
        lines.append(f"  concerns: {concerns}")
    note = str(context.get("note", "")).strip()
    if note:
        lines.append(f"  note: {concise(note, 260)}")
    return lines


def working_context_show_payload(contexts: list[dict]) -> dict:
    return {
        "working_context_is_proof": False,
        "contexts": contexts,
    }


def build_working_context_payload(
    record_id: str,
    timestamp: str,
    scope: str,
    title: str,
    context_kind: str,
    pinned_refs: list[str],
    focus_paths: list[str],
    topic_terms: list[str],
    topic_seed_refs: list[str],
    assumptions: list[dict],
    concerns: list[str],
    project_refs: list[str],
    task_refs: list[str],
    tags: list[str],
    note: str,
) -> dict:
    return {
        "id": record_id,
        "record_type": "working_context",
        "scope": scope.strip(),
        "title": title.strip(),
        "status": "active",
        "context_kind": context_kind,
        "pinned_refs": pinned_refs,
        "focus_paths": focus_paths,
        "topic_terms": topic_terms,
        "topic_seed_refs": topic_seed_refs,
        "assumptions": assumptions,
        "concerns": concerns,
        "parent_context_ref": "",
        "supersedes_refs": [],
        "project_refs": project_refs,
        "task_refs": task_refs,
        "created_at": timestamp,
        "updated_at": timestamp,
        "tags": tags,
        "note": note.strip(),
    }


def fork_working_context_payload(
    source_payload: dict,
    record_id: str,
    timestamp: str,
    context_ref: str,
    title: str | None,
    context_kind: str | None,
    add_pinned_refs: list[str],
    remove_pinned_refs: list[str],
    add_focus_paths: list[str],
    remove_focus_paths: list[str],
    add_topic_terms: list[str],
    remove_topic_terms: list[str],
    add_topic_seed_refs: list[str],
    remove_topic_seed_refs: list[str],
    added_assumptions: list[dict],
    add_concerns: list[str],
    inferred_topic_terms: list[str],
    project_refs: list[str],
    task_refs: list[str],
    tags: list[str],
    note: str,
) -> dict:
    payload = dict(source_payload)
    payload["id"] = record_id
    payload["status"] = "active"
    payload["title"] = (title or str(payload.get("title", ""))).strip()
    payload["context_kind"] = context_kind or str(payload.get("context_kind", "general")).strip() or "general"
    payload["pinned_refs"] = add_remove_values(payload.get("pinned_refs", []), add_pinned_refs, remove_pinned_refs)
    payload["focus_paths"] = add_remove_values(payload.get("focus_paths", []), add_focus_paths, remove_focus_paths)
    payload["topic_terms"] = add_remove_values(payload.get("topic_terms", []), add_topic_terms, remove_topic_terms)
    payload["topic_seed_refs"] = add_remove_values(payload.get("topic_seed_refs", []), add_topic_seed_refs, remove_topic_seed_refs)
    if not payload["topic_terms"]:
        payload["topic_terms"] = inferred_topic_terms
    payload["assumptions"] = list(payload.get("assumptions", [])) + added_assumptions
    payload["concerns"] = add_remove_values(payload.get("concerns", []), add_concerns, [])
    payload["parent_context_ref"] = context_ref
    payload["supersedes_refs"] = sorted({*payload.get("supersedes_refs", []), context_ref})
    if project_refs:
        payload["project_refs"] = project_refs
    if task_refs:
        payload["task_refs"] = task_refs
    if tags:
        payload["tags"] = sorted({*payload.get("tags", []), *tags})
    payload["created_at"] = timestamp
    payload["updated_at"] = timestamp
    payload["note"] = append_note(str(payload.get("note", "")), note.strip())
    return payload


def close_working_context_payload(context_payload: dict, timestamp: str, status: str, note: str | None) -> dict:
    payload = dict(context_payload)
    payload["status"] = status
    payload["updated_at"] = timestamp
    payload["closed_at"] = timestamp
    if note:
        payload["note"] = append_note(str(payload.get("note", "")), f"[{timestamp}] {note.strip()}")
    return payload
