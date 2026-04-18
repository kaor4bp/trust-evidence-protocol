"""Reasoning-case selection, diagnostics, and text rendering helpers."""

from __future__ import annotations

from .claims import claim_is_fallback
from .display import (
    claim_line,
    guideline_summary_line,
    project_summary_line,
    restriction_summary_line,
    source_line,
)
from .hypotheses import collect_claim_refs_from_models_flows
from .retrieval import active_guidelines_for, active_permissions_for, select_records
from .scopes import active_restrictions_for, record_belongs_to_project, record_belongs_to_task
from .search import concise
from .tasks import task_summary_line
from .topic_index import task_terms


def _explicit_records_in_scope(
    records: dict[str, dict],
    refs: list[str],
    project_ref: str | None,
    task_ref: str | None,
) -> list[dict]:
    return [
        records[ref]
        for ref in refs
        if ref in records
        and record_belongs_to_project(records[ref], project_ref)
        and record_belongs_to_task(records[ref], task_ref)
    ]


def _claim_items(records: dict[str, dict], claims: list[dict], limit: int) -> tuple[list[dict], list[str], list[str], list[str]]:
    items = []
    unsupported = []
    tentative = []
    lifecycle_fallback = []
    for claim in claims[:limit]:
        source_records = []
        source_refs = claim.get("source_refs", [])
        if not source_refs:
            unsupported.append(claim.get("id"))
        if claim.get("status") == "tentative":
            tentative.append(claim.get("id"))
        if claim_is_fallback(claim):
            lifecycle_fallback.append(claim.get("id"))
        for source_ref in source_refs:
            source = records.get(source_ref)
            if source and source.get("record_type") == "source":
                source_records.append(source)
            else:
                unsupported.append(claim.get("id"))
        items.append({"claim": claim, "sources": source_records})
    return items, unsupported, tentative, lifecycle_fallback


def _open_question_items(records: dict[str, dict], models: list[dict], flows: list[dict]) -> list[dict]:
    open_refs = set()
    for model in models:
        open_refs.update(model.get("open_question_refs", []))
    for flow in flows:
        open_refs.update(flow.get("open_question_refs", []))
        for step in flow.get("steps", []):
            if isinstance(step, dict):
                open_refs.update(step.get("open_question_refs", []))
    return [{"ref": ref, "record": records.get(ref, {})} for ref in sorted(open_refs)]


def build_reasoning_case_payload(
    records: dict[str, dict],
    task: str,
    claim_refs: list[str],
    model_refs: list[str],
    flow_refs: list[str],
    current_ref: str,
    project_ref: str,
    limit: int,
) -> dict:
    project_filter = project_ref or None
    task_filter = current_ref or None
    current_task = records.get(current_ref) if current_ref else None
    current_project = records.get(project_ref) if project_ref else None
    terms = task_terms(task)

    models = _explicit_records_in_scope(records, model_refs, project_filter, task_filter) or select_records(
        records,
        "model",
        terms,
        3,
        explicit_refs=set(model_refs),
        project_ref=project_filter,
        task_ref=task_filter,
    )
    flows = _explicit_records_in_scope(records, flow_refs, project_filter, task_filter) or select_records(
        records,
        "flow",
        terms,
        3,
        explicit_refs=set(flow_refs),
        project_ref=project_filter,
        task_ref=task_filter,
    )

    derived_claim_refs = collect_claim_refs_from_models_flows(models, flows)
    derived_claim_refs.update(claim_refs)
    claims = [
        records[ref]
        for ref in sorted(derived_claim_refs)
        if ref in records
        and records[ref].get("record_type") == "claim"
        and record_belongs_to_project(records[ref], project_filter)
        and record_belongs_to_task(records[ref], task_filter)
    ]
    if not claims:
        claims = select_records(records, "claim", terms, limit, project_ref=project_filter, task_ref=task_filter)

    claim_items, unsupported, tentative, lifecycle_fallback = _claim_items(records, claims, limit)
    inactive_context = [
        str(item.get("id"))
        for item in [*models, *flows]
        if str(item.get("status", "")).strip() in {"superseded", "stale", "contested"}
    ]
    return {
        "task": task,
        "terms": terms,
        "current_task": current_task,
        "current_project": current_project,
        "project_ref": project_ref,
        "models": models,
        "flows": flows,
        "claim_items": claim_items,
        "open_questions": _open_question_items(records, models, flows),
        "permissions": active_permissions_for(records, terms, project_filter, task_filter, limit),
        "guidelines": active_guidelines_for(records, terms, project_filter, task_filter, limit),
        "restrictions": active_restrictions_for(records, project_filter, task_filter),
        "unsupported": unsupported,
        "tentative": tentative,
        "lifecycle_fallback": lifecycle_fallback,
        "inactive_context": inactive_context,
    }


def _append_model_lines(lines: list[str], models: list[dict]) -> None:
    lines.append("## Models")
    if not models:
        lines.append("- none")
        return
    for model in models:
        lines.append(
            f"- `{model.get('id')}` status=`{model.get('status')}` scope=`{model.get('scope')}`: "
            f"{concise(model.get('summary', ''), 260)}"
        )


def _append_flow_lines(lines: list[str], flows: list[dict]) -> None:
    lines.extend(["", "## Flows"])
    if not flows:
        lines.append("- none")
        return
    for flow in flows:
        lines.append(
            f"- `{flow.get('id')}` status=`{flow.get('status')}` scope=`{flow.get('scope')}`: "
            f"{concise(flow.get('summary', ''), 260)}"
        )


def reasoning_case_text_lines(payload: dict) -> list[str]:
    lines = ["# Reasoning Case", ""]
    current_project = payload.get("current_project")
    current_task = payload.get("current_task")
    project_ref = payload.get("project_ref", "")
    if current_project:
        lines.append(f"Current Project: {project_summary_line(current_project)}")
    if current_task:
        lines.append(f"Current Task: {task_summary_line(current_task)}")
    lines.extend([f"Requested Task: {payload.get('task', '')}", ""])
    if project_ref:
        lines.extend([f"Project filter: `{project_ref}`", ""])

    _append_model_lines(lines, payload.get("models", []))
    _append_flow_lines(lines, payload.get("flows", []))

    lines.extend(["", "## Fact/Hypothesis Chain"])
    claim_items = payload.get("claim_items", [])
    if not claim_items:
        lines.append("- none")
    for item in claim_items:
        lines.append(claim_line(item.get("claim", {})))
        for source in item.get("sources", []):
            lines.append(source_line(source))

    lines.extend(["", "## Open Questions"])
    open_questions = payload.get("open_questions", [])
    if not open_questions:
        lines.append("- none")
    for item in open_questions:
        question = item.get("record", {})
        lines.append(
            f"- `{item.get('ref')}` status=`{question.get('status', '')}`: "
            f"{concise(question.get('question', ''), 220)}"
        )

    lines.extend(["", "## Applicable Permissions"])
    permissions = payload.get("permissions", [])
    if not permissions:
        lines.append("- none")
    for permission in permissions:
        applies_to = str(permission.get("applies_to", "")).strip() or "global"
        lines.append(
            f"- `{permission.get('id')}` applies_to=`{applies_to}` scope=`{permission.get('scope')}` "
            f"grants={permission.get('grants', [])}"
        )

    lines.extend(["", "## Applicable Guidelines"])
    guidelines = payload.get("guidelines", [])
    if not guidelines:
        lines.append("- none")
    for guideline in guidelines:
        lines.append(f"- {guideline_summary_line(guideline)}")

    lines.extend(["", "## Active Restrictions"])
    restrictions = payload.get("restrictions", [])
    if not restrictions:
        lines.append("- none active for current project/task")
    for restriction in restrictions:
        lines.append(f"- {restriction_summary_line(restriction)} rules={restriction.get('rules', [])}")

    lines.extend(["", "## Chain Check"])
    inactive_context = payload.get("inactive_context", [])
    unsupported = payload.get("unsupported", [])
    tentative = payload.get("tentative", [])
    lifecycle_fallback = payload.get("lifecycle_fallback", [])
    if inactive_context:
        lines.append(f"- WARNING: selected inactive model/flow records: {', '.join(sorted(inactive_context))}")
    if unsupported:
        lines.append(f"- BLOCKER: unsupported or missing source refs in claims: {', '.join(sorted(set(unsupported)))}")
    else:
        lines.append("- every listed claim has source refs")
    if tentative:
        lines.append(f"- WARNING: tentative claims used as hypotheses: {', '.join(sorted(set(tentative)))}")
    else:
        lines.append("- no tentative claims in the selected chain")
    if lifecycle_fallback:
        lines.append(
            "- WARNING: lifecycle fallback/archived claims are background or audit context only; "
            f"restore or re-support before decisive use: {', '.join(sorted(set(lifecycle_fallback)))}"
        )
    if not payload.get("models", []):
        lines.append("- WARNING: no model selected; if this reasoning spans multiple facts, create/update `MODEL-*`")
    if not payload.get("flows", []) and any(
        term in {"flow", "path", "setup", "pipeline", "integration"} for term in payload.get("terms", set())
    ):
        lines.append("- WARNING: task looks flow-shaped but no `FLOW-*` was selected")

    lines.extend(["", "## Next Safe Move"])
    if unsupported:
        lines.append("- gather/record sources before acting")
    elif tentative:
        lines.append("- only safe/guarded exploratory action; do not promote conclusions without more support")
    elif lifecycle_fallback:
        lines.append("- proceed only from active claims; restore or re-support fallback claims before using them as proof")
    else:
        lines.append("- action may proceed if strictness and permissions allow it; record `ACT-*` for durable changes")
    return lines
