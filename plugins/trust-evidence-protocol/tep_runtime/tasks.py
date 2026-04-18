"""Task record payload and lifecycle mutation helpers."""

from __future__ import annotations

from .notes import append_note
from .scopes import record_belongs_to_project
from .search import concise, score_record
from .topic_index import task_terms


def build_task_payload(
    record_id: str,
    timestamp: str,
    scope: str,
    title: str,
    task_type: str,
    description: str | None,
    related_claim_refs: list[str],
    related_model_refs: list[str],
    related_flow_refs: list[str],
    open_question_refs: list[str],
    plan_refs: list[str],
    debt_refs: list[str],
    action_refs: list[str],
    project_refs: list[str],
    tags: list[str],
    note: str,
) -> dict:
    return {
        "id": record_id,
        "record_type": "task",
        "scope": scope.strip(),
        "title": title.strip(),
        "description": (description or "").strip(),
        "status": "active",
        "task_type": task_type.strip() or "general",
        "related_claim_refs": related_claim_refs,
        "related_model_refs": related_model_refs,
        "related_flow_refs": related_flow_refs,
        "open_question_refs": open_question_refs,
        "plan_refs": plan_refs,
        "debt_refs": debt_refs,
        "action_refs": action_refs,
        "project_refs": project_refs,
        "restriction_refs": [],
        "created_at": timestamp,
        "updated_at": timestamp,
        "tags": tags,
        "note": note.strip(),
    }


def task_summary_line(task: dict) -> str:
    task_type = str(task.get("task_type", "general")).strip() or "general"
    return (
        f"`{task.get('id')}` status=`{task.get('status')}` type=`{task_type}` scope=`{task.get('scope')}` "
        f"title=\"{concise(task.get('title', ''), 160)}\""
    )


def task_identity_text(task: dict | None) -> str:
    if not task:
        return ""
    fields = [
        str(task.get("scope", "")),
        str(task.get("title", "")),
        str(task.get("description", "")),
        str(task.get("task_type", "")),
        " ".join(str(tag) for tag in task.get("tags", [])),
    ]
    return " ".join(fields)


def task_related_counts(task: dict) -> str:
    parts = []
    for key in ("plan_refs", "debt_refs", "action_refs", "open_question_refs", "related_claim_refs"):
        values = task.get(key, [])
        if values:
            parts.append(f"{key}={len(values)}")
    return ", ".join(parts) if parts else "no linked records"


def build_task_drift_payload(
    task_ref: str,
    task: dict | None,
    intent: str,
    task_type: str | None,
) -> dict:
    if not task_ref:
        return {
            "exit_code": 0,
            "alignment": "unknown",
            "recommendation": "start-task or ask the user before substantial work",
        }
    if not task or task.get("record_type") != "task":
        return {
            "exit_code": 1,
            "alignment": "unknown",
            "reason": f"missing task record {task_ref}",
        }
    if str(task.get("status", "")).strip() != "active":
        return {
            "exit_code": 0,
            "alignment": "unknown",
            "current_task": task_ref,
            "status": task.get("status", ""),
            "recommendation": "resume-task or start a new task before substantial work",
        }

    intent_terms = task_terms(intent)
    task_terms_set = task_terms(task_identity_text(task))
    overlap = sorted(intent_terms & task_terms_set)
    current_type = str(task.get("task_type", "general")).strip() or "general"
    if task_type and task_type != current_type:
        alignment = "drifted"
        recommendation = "pause/switch current task before continuing"
    elif len(overlap) >= 2:
        alignment = "aligned"
        recommendation = "continue"
    elif len(overlap) == 1:
        alignment = "adjacent"
        recommendation = "continue only if this is supporting work; otherwise pause/switch task"
    else:
        alignment = "drifted"
        recommendation = "pause/switch current task or ask the user"
    return {
        "exit_code": 0,
        "alignment": alignment,
        "current_task": task_ref,
        "current_type": current_type,
        "title": task.get("title", ""),
        "intent_type": task_type,
        "overlap": overlap,
        "recommendation": recommendation,
    }


def task_drift_text_lines(payload: dict) -> list[str]:
    lines = [f"alignment={payload.get('alignment', 'unknown')}"]
    if payload.get("reason"):
        lines.append(f"reason={payload['reason']}")
        return lines
    if payload.get("current_task") and payload.get("status") is not None:
        lines.append(f"current_task={payload['current_task']} status={payload.get('status', '')}")
        lines.append(f"recommendation={payload.get('recommendation', '')}")
        return lines
    if payload.get("current_task"):
        lines.append(
            f"current_task={payload['current_task']} type={payload.get('current_type', 'general')} "
            f"title={payload.get('title', '')}"
        )
        if payload.get("intent_type"):
            lines.append(f"intent_type={payload['intent_type']}")
        overlap = payload.get("overlap", [])
        lines.append(f"overlap_terms={','.join(overlap) if overlap else 'none'}")
    lines.append(f"recommendation={payload.get('recommendation', '')}")
    return lines


def select_precedent_tasks(
    records: dict[str, dict],
    current_ref: str,
    resolved_type: str,
    search_text: str,
    project_ref: str | None,
    query: str | None,
    limit: int,
) -> list[dict]:
    terms = task_terms(search_text)
    ranked = []
    for task in records.values():
        if task.get("record_type") != "task":
            continue
        if task.get("id") == current_ref:
            continue
        if str(task.get("task_type", "general")).strip() != resolved_type:
            continue
        if not record_belongs_to_project(task, project_ref):
            continue
        score = score_record(task, terms)
        if query and score <= 0:
            continue
        timestamp = str(task.get("updated_at") or task.get("created_at") or "")
        ranked.append((score, timestamp, task))
    return [task for _, _, task in sorted(ranked, key=lambda item: (item[0], item[1]), reverse=True)[:limit]]


def build_precedent_review_payload(
    current_task: dict | None,
    resolved_type: str,
    query: str | None,
    tasks: list[dict],
) -> dict:
    return {
        "current_task": current_task,
        "resolved_type": resolved_type or "general",
        "query": query,
        "tasks": tasks,
    }


def precedent_review_text_lines(payload: dict) -> list[str]:
    lines = ["# Precedent Review"]
    current_task = payload.get("current_task")
    if current_task:
        lines.append(f"Current task: {task_summary_line(current_task)}")
    lines.append(f"task_type=`{payload.get('resolved_type', 'general')}`")
    if payload.get("query"):
        lines.append(f"query=\"{payload['query']}\"")
    lines.extend(["", "## Similar Tasks"])
    tasks = payload.get("tasks", [])
    if not tasks:
        lines.append("- none found")
        return lines
    for task in tasks:
        lines.append(f"- {task_summary_line(task)}")
        lines.append(f"  linked: {task_related_counts(task)}")
        note = str(task.get("note", "")).strip()
        if note:
            lines.append(f"  note: {concise(note, 220)}")
    lines.extend(
        [
            "",
            "## Recommended Move",
            "- Inspect linked `PLN-*`, `DEBT-*`, `ACT-*`, `PRP-*`, and `OPEN-*` before repeating the same task type.",
            "- If a prior assumption changed, create or update claims/models/flows before acting.",
        ]
    )
    return lines


def assign_task_payload(record_payload: dict, timestamp: str, task_ref: str, note: str | None) -> dict:
    payload = dict(record_payload)
    payload["task_refs"] = sorted({*payload.get("task_refs", []), task_ref})
    payload["note"] = append_note(
        str(payload.get("note", "")),
        note or f"[{timestamp}] assigned to task {task_ref}",
    )
    if "updated_at" in payload:
        payload["updated_at"] = timestamp
    return payload


def finish_task_payload(task_payload: dict, timestamp: str, final_status: str, note: str | None) -> dict:
    payload = dict(task_payload)
    payload["status"] = final_status
    payload["updated_at"] = timestamp
    payload[f"{final_status}_at"] = timestamp
    if note:
        payload["note"] = append_note(str(payload.get("note", "")), f"[{timestamp}] {note.strip()}")
    return payload


def resume_task_payload(task_payload: dict, timestamp: str, note: str | None) -> dict:
    payload = dict(task_payload)
    payload["status"] = "active"
    payload["updated_at"] = timestamp
    payload["resumed_at"] = timestamp
    if note:
        payload["note"] = append_note(str(payload.get("note", "")), f"[{timestamp}] {note.strip()}")
    return payload


def pause_task_for_switch_payload(
    task_payload: dict,
    timestamp: str,
    target_task_ref: str,
    note: str | None,
) -> dict:
    payload = dict(task_payload)
    payload["status"] = "paused"
    payload["updated_at"] = timestamp
    payload["paused_at"] = timestamp
    switch_note = f"paused by switch-task to {target_task_ref}"
    if note:
        switch_note = f"{switch_note}: {note.strip()}"
    payload["note"] = append_note(str(payload.get("note", "")), f"[{timestamp}] {switch_note}")
    return payload
