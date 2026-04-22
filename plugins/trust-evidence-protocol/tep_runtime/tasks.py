"""Task record payload and lifecycle mutation helpers."""

from __future__ import annotations

from .notes import append_note
from .scopes import record_belongs_to_project
from .search import concise, score_record
from .topic_index import task_terms
from .validation import safe_list


TASK_OUTCOME_MARKER = "TEP TASK OUTCOME:"
TASK_TERMINAL_OUTCOMES = {"done", "blocked", "user-question"}
TASK_OBLIGATION_TYPES = {"open_question", "plan", "debt", "action"}
TASK_OBLIGATION_REF_FIELDS = {
    "open_question": "open_question_refs",
    "plan": "plan_refs",
    "debt": "debt_refs",
    "action": "action_refs",
}
TASK_BLOCKING_STATUSES = {
    "open_question": {"open"},
    "plan": {"proposed", "active", "blocked"},
    "debt": {"open", "accepted", "scheduled"},
    "action": {"planned"},
}


def build_task_payload(
    record_id: str,
    timestamp: str,
    scope: str,
    title: str,
    task_type: str,
    execution_mode: str,
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
        "execution_mode": execution_mode.strip() or "manual",
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
    execution_mode = str(task.get("execution_mode", "manual")).strip() or "manual"
    return (
        f"`{task.get('id')}` status=`{task.get('status')}` type=`{task_type}` mode=`{execution_mode}` scope=`{task.get('scope')}` "
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


def task_outcome_from_message(message: str) -> str:
    for line in message.splitlines():
        stripped = line.strip()
        if stripped.lower().startswith(TASK_OUTCOME_MARKER.lower()):
            value = stripped[len(TASK_OUTCOME_MARKER) :].strip().lower()
            return value.split()[0].strip("`.,;:") if value else ""
    return ""


def task_linked_obligations(records: dict[str, dict], task_ref: str) -> list[dict]:
    task = records.get(task_ref, {})
    refs_by_type: dict[str, set[str]] = {
        record_type: set(safe_list(task, field))
        for record_type, field in TASK_OBLIGATION_REF_FIELDS.items()
    }
    linked: list[dict] = []
    for record_id, record in records.items():
        record_type = str(record.get("record_type", "")).strip()
        if record_type not in TASK_OBLIGATION_TYPES:
            continue
        via_task_field = record_id in refs_by_type.get(record_type, set())
        via_record_task_ref = task_ref in safe_list(record, "task_refs")
        if via_task_field or via_record_task_ref:
            linked.append(
                {
                    "id": record_id,
                    "record_type": record_type,
                    "status": str(record.get("status", "")).strip(),
                    "title": str(record.get("title") or record.get("question") or record.get("scope") or "").strip(),
                    "blocking": str(record.get("status", "")).strip() in TASK_BLOCKING_STATUSES[record_type],
                    "linked_by": sorted(
                        item
                        for item, present in (
                            ("task_field", via_task_field),
                            ("record_task_refs", via_record_task_ref),
                        )
                        if present
                    ),
                }
            )
    return sorted(linked, key=lambda item: (item["record_type"], item["id"]))


def task_outcome_check_payload(records: dict[str, dict], task_ref: str, outcome: str) -> dict:
    task = records.get(task_ref)
    outcome = outcome.strip().lower()
    errors: list[str] = []
    warnings: list[str] = []
    if not task or task.get("record_type") != "task":
        return {
            "task_ref": task_ref,
            "outcome": outcome,
            "accepted": False,
            "errors": [f"missing task record {task_ref}"],
            "warnings": [],
            "obligations": [],
            "next_allowed_commands": ["show-task --all", "start-task ..."],
        }
    if outcome not in TASK_TERMINAL_OUTCOMES:
        errors.append(
            "outcome must be one of: " + ", ".join(sorted(TASK_TERMINAL_OUTCOMES))
        )

    obligations = task_linked_obligations(records, task_ref)
    blocking = [item for item in obligations if item["blocking"]]
    blocking_open_questions = [item for item in blocking if item["record_type"] == "open_question"]
    blocking_plans = [item for item in blocking if item["record_type"] == "plan"]
    blocking_debt = [item for item in blocking if item["record_type"] == "debt"]
    blocking_actions = [item for item in blocking if item["record_type"] == "action"]

    if outcome == "done" and blocking:
        errors.append("done requires no linked open obligations")
    if outcome == "blocked" and not (blocking_open_questions or blocking_plans or blocking_debt or blocking_actions):
        errors.append("blocked requires a linked open question, blocked/active plan, unresolved debt, or planned action")
    if outcome == "user-question" and not blocking_open_questions:
        errors.append("user-question requires a linked OPEN-* record with status=open")
    if outcome in {"blocked", "user-question"} and not str(task.get("note", "")).strip():
        warnings.append("task note is empty; include a blocker/question summary when finishing")

    if outcome == "done":
        next_allowed = ["complete-task --task " + task_ref]
    elif outcome == "blocked":
        next_allowed = [
            "pause-task --task " + task_ref,
            "record-open-question ...",
            "record-plan ...",
            "record-debt ...",
            "record-action ...",
        ]
    elif outcome == "user-question":
        next_allowed = ["pause-task --task " + task_ref, "record-open-question ..."]
    else:
        next_allowed = ["task-outcome-check --task " + task_ref + " --outcome done|blocked|user-question"]

    return {
        "task_ref": task_ref,
        "task_status": str(task.get("status", "")).strip(),
        "task_execution_mode": str(task.get("execution_mode", "manual")).strip() or "manual",
        "outcome": outcome,
        "accepted": not errors,
        "errors": errors,
        "warnings": warnings,
        "obligations": obligations,
        "blocking_obligations": blocking,
        "next_allowed_commands": next_allowed,
        "outcome_contract": {
            "done": "All linked obligations must be closed, resolved, completed, abandoned, invalid, or wont-fix.",
            "blocked": "At least one linked OPEN/PLN/DEBT/ACT record must explain the blocker.",
            "user-question": "At least one linked open OPEN-* question must state what the user must answer.",
        },
    }


def task_outcome_check_text_lines(payload: dict) -> list[str]:
    lines = [
        "# Task Outcome Check",
        "",
        f"task: `{payload.get('task_ref')}` outcome: `{payload.get('outcome')}` accepted: `{payload.get('accepted')}`",
        f"status: `{payload.get('task_status', '')}` mode: `{payload.get('task_execution_mode', '')}`",
        "",
        "## Obligations",
    ]
    obligations = payload.get("obligations") or []
    if obligations:
        for item in obligations:
            marker = "blocking" if item.get("blocking") else "closed"
            title = concise(item.get("title", ""), 120)
            lines.append(
                f"- `{item.get('id')}` type=`{item.get('record_type')}` status=`{item.get('status')}` {marker}: {title}"
            )
    else:
        lines.append("- none")
    if payload.get("errors"):
        lines.extend(["", "## Errors"])
        for error in payload.get("errors", []):
            lines.append(f"- {error}")
    if payload.get("warnings"):
        lines.extend(["", "## Warnings"])
        for warning in payload.get("warnings", []):
            lines.append(f"- {warning}")
    lines.extend(["", "## Next Allowed Commands"])
    for command in payload.get("next_allowed_commands", []):
        lines.append(f"- `{command}`")
    return lines


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
