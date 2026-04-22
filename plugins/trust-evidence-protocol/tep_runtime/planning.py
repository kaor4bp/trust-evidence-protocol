from __future__ import annotations


PLAN_DECOMPOSITION_STATUSES = {"atomic", "decomposed"}


def build_plan_payload(
    record_id: str,
    timestamp: str,
    scope: str,
    title: str,
    priority: str,
    status: str,
    justified_by: list[str],
    steps: list[str],
    success_criteria: list[str],
    blocked_by: list[str],
    project_refs: list[str],
    task_refs: list[str],
    tags: list[str],
    note: str,
    decomposition: dict | None = None,
    parent_plan_refs: list[str] | None = None,
) -> dict:
    payload = {
        "id": record_id,
        "record_type": "plan",
        "scope": scope.strip(),
        "title": title.strip(),
        "status": status,
        "priority": priority,
        "justified_by": justified_by,
        "steps": steps,
        "success_criteria": success_criteria,
        "blocked_by": blocked_by,
        "project_refs": project_refs,
        "task_refs": task_refs,
        "created_at": timestamp,
        "updated_at": timestamp,
        "tags": tags,
        "note": note.strip(),
    }
    if decomposition:
        payload["decomposition"] = decomposition
    if parent_plan_refs:
        payload["parent_plan_refs"] = parent_plan_refs
    return payload


def build_atomic_plan_decomposition(*, task_ref: str | None = None) -> dict:
    return {
        "status": "atomic",
        "one_pass": True,
        "task_ref": (task_ref or "").strip(),
    }


def build_decomposed_plan_decomposition(
    *,
    subplan_refs: list[str],
    task_refs: list[str] | None = None,
) -> dict:
    return {
        "status": "decomposed",
        "subplan_refs": [ref.strip() for ref in subplan_refs if ref.strip()],
        "task_refs": [ref.strip() for ref in (task_refs or []) if ref.strip()],
    }


def apply_atomic_plan_decomposition(
    plan: dict,
    *,
    timestamp: str,
    task_ref: str | None = None,
    note: str | None = None,
) -> dict:
    payload = dict(plan)
    payload["decomposition"] = build_atomic_plan_decomposition(task_ref=task_ref)
    payload["updated_at"] = timestamp
    if note and note.strip():
        previous = str(payload.get("note", "")).strip()
        payload["note"] = f"{previous}\n{timestamp}: {note.strip()}" if previous else note.strip()
    return payload


def apply_decomposed_plan_decomposition(
    plan: dict,
    *,
    timestamp: str,
    subplan_refs: list[str],
    task_refs: list[str] | None = None,
    note: str | None = None,
) -> dict:
    payload = dict(plan)
    payload["decomposition"] = build_decomposed_plan_decomposition(
        subplan_refs=subplan_refs,
        task_refs=task_refs,
    )
    payload["updated_at"] = timestamp
    if note and note.strip():
        previous = str(payload.get("note", "")).strip()
        payload["note"] = f"{previous}\n{timestamp}: {note.strip()}" if previous else note.strip()
    return payload


def validate_plan_decomposition_payload(
    records: dict[str, dict],
    plan_ref: str,
    *,
    _seen: set[str] | None = None,
) -> dict:
    plan = records.get(plan_ref)
    errors: list[str] = []
    warnings: list[str] = []
    children: list[dict] = []
    if not plan or plan.get("record_type") != "plan":
        return {
            "plan_ref": plan_ref,
            "accepted": False,
            "status": "missing",
            "errors": [f"missing plan record {plan_ref}"],
            "warnings": [],
            "children": [],
        }
    decomposition = plan.get("decomposition")
    if not isinstance(decomposition, dict):
        return {
            "plan_ref": plan_ref,
            "accepted": False,
            "status": "needs-decomposition",
            "errors": ["plan requires atomic or decomposed decomposition before execution"],
            "warnings": [],
            "children": [],
        }
    mode = str(decomposition.get("status", "")).strip()
    if mode not in PLAN_DECOMPOSITION_STATUSES:
        errors.append("decomposition.status must be atomic or decomposed")
    if mode == "atomic":
        if decomposition.get("one_pass") is not True:
            errors.append("atomic plan requires one_pass=true")
        if not [str(item).strip() for item in plan.get("steps", []) if str(item).strip()]:
            errors.append("atomic plan requires existing steps")
        if not [str(item).strip() for item in plan.get("success_criteria", []) if str(item).strip()]:
            errors.append("atomic plan requires existing success_criteria")
        task_ref = str(decomposition.get("task_ref", "")).strip()
        if task_ref:
            task = records.get(task_ref)
            if not task or task.get("record_type") != "task":
                errors.append(f"{task_ref} is not a task")
    if mode == "decomposed":
        subplan_refs = decomposition.get("subplan_refs", [])
        if not isinstance(subplan_refs, list) or not [str(ref).strip() for ref in subplan_refs]:
            errors.append("decomposed plan requires non-empty subplan_refs")
            subplan_refs = []
        seen = set(_seen or set())
        if plan_ref in seen:
            errors.append(f"plan decomposition cycle at {plan_ref}")
        seen.add(plan_ref)
        for child_ref in [str(ref).strip() for ref in subplan_refs if str(ref).strip()]:
            child = records.get(child_ref)
            if not child or child.get("record_type") != "plan":
                errors.append(f"{child_ref} is not a plan")
                continue
            if plan_ref not in [str(ref).strip() for ref in child.get("parent_plan_refs", [])]:
                errors.append(f"{child_ref} must link back via parent_plan_refs")
            child_payload = validate_plan_decomposition_payload(records, child_ref, _seen=seen)
            children.append(child_payload)
            if not child_payload.get("accepted"):
                errors.append(f"{child_ref} decomposition invalid")
    return {
        "plan_ref": plan_ref,
        "accepted": not errors,
        "status": mode or "invalid",
        "errors": errors,
        "warnings": warnings,
        "children": children,
        "next_allowed_commands": (
            ["confirm-atomic-plan --plan " + plan_ref, "decompose-plan --plan " + plan_ref]
            if errors
            else ["execute atomic plan" if mode == "atomic" else "work through child plans/tasks"]
        ),
    }


def plan_decomposition_text_lines(payload: dict) -> list[str]:
    lines = [
        "# Plan Decomposition Check",
        "",
        f"plan: `{payload.get('plan_ref')}` status: `{payload.get('status')}` accepted={payload.get('accepted')}",
    ]
    if payload.get("errors"):
        lines.extend(["", "## Errors"])
        for error in payload.get("errors", []):
            lines.append(f"- {error}")
    if payload.get("warnings"):
        lines.extend(["", "## Warnings"])
        for warning in payload.get("warnings", []):
            lines.append(f"- {warning}")
    children = payload.get("children") or []
    if children:
        lines.extend(["", "## Children"])
        for child in children:
            lines.append(
                f"- `{child.get('plan_ref')}` status=`{child.get('status')}` accepted={child.get('accepted')}"
            )
    lines.extend(["", "## Next Allowed Commands"])
    for command in payload.get("next_allowed_commands", []):
        lines.append(f"- `{command}`")
    return lines


def build_debt_payload(
    record_id: str,
    timestamp: str,
    scope: str,
    title: str,
    priority: str,
    status: str,
    evidence_refs: list[str],
    plan_refs: list[str],
    project_refs: list[str],
    task_refs: list[str],
    tags: list[str],
    note: str,
) -> dict:
    return {
        "id": record_id,
        "record_type": "debt",
        "scope": scope.strip(),
        "title": title.strip(),
        "status": status,
        "priority": priority,
        "evidence_refs": evidence_refs,
        "plan_refs": plan_refs,
        "project_refs": project_refs,
        "task_refs": task_refs,
        "created_at": timestamp,
        "updated_at": timestamp,
        "tags": tags,
        "note": note.strip(),
    }
