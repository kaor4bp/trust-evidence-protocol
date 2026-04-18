"""Task-oriented context brief selection and text rendering helpers."""

from __future__ import annotations

from pathlib import Path

from .claims import claim_is_archived, claim_is_fallback
from .display import claim_line, guideline_summary_line, project_summary_line, restriction_summary_line
from .hypotheses import active_hypotheses_for, collect_claim_refs_from_models_flows
from .proposals import proposal_summary_line
from .retrieval import active_guidelines_for, active_permissions_for, select_fallback_claims, select_records
from .scopes import active_restrictions_for
from .search import concise
from .tasks import task_summary_line
from .topic_index import task_terms


def project_detail_lines(project: dict) -> list[str]:
    lines = [f"- {project_summary_line(project)}"]
    root_refs = project.get("root_refs", [])
    if root_refs:
        lines.append(f"  root_refs: {root_refs}")
    return lines


def task_detail_lines(task: dict) -> list[str]:
    lines = [f"- {task_summary_line(task)}"]
    description = str(task.get("description", "")).strip()
    if description:
        lines.append(f"  description: {concise(description, 260)}")
    for key in (
        "related_claim_refs",
        "related_model_refs",
        "related_flow_refs",
        "open_question_refs",
        "plan_refs",
        "debt_refs",
        "action_refs",
        "project_refs",
        "restriction_refs",
    ):
        values = task.get(key, [])
        if values:
            lines.append(f"  {key}: {values}")
    return lines


def guideline_detail_lines(guideline: dict) -> list[str]:
    lines = [f"- {guideline_summary_line(guideline)}"]
    rationale = str(guideline.get("rationale", "")).strip()
    if rationale:
        lines.append(f"  rationale: {concise(rationale, 260)}")
    examples = guideline.get("examples", [])
    if examples:
        lines.append(f"  examples: {examples}")
    for key in ("project_refs", "task_refs", "source_refs", "related_claim_refs"):
        values = guideline.get(key, [])
        if values:
            lines.append(f"  {key}: {values}")
    return lines


def restriction_detail_lines(restriction: dict) -> list[str]:
    lines = [f"- {restriction_summary_line(restriction)}"]
    rules = restriction.get("rules", [])
    if rules:
        lines.append(f"  rules: {rules}")
    for key in ("project_refs", "task_refs", "related_claim_refs"):
        values = restriction.get(key, [])
        if values:
            lines.append(f"  {key}: {values}")
    return lines


def _dedupe_claims(claims: list[dict]) -> list[dict]:
    deduped = []
    seen = set()
    for claim in claims:
        claim_id = claim.get("id")
        if claim_id not in seen:
            deduped.append(claim)
            seen.add(claim_id)
    return deduped


def build_context_brief_payload(
    records: dict[str, dict],
    root: Path,
    task: str,
    current_ref: str,
    project_ref: str,
    limit: int,
) -> dict:
    task_ref = current_ref or None
    project_filter = project_ref or None
    current_task = records.get(current_ref) if current_ref else None
    current_project = records.get(project_ref) if project_ref else None
    terms = task_terms(task)
    models = select_records(records, "model", terms, limit, project_ref=project_filter, task_ref=task_ref)
    flows = select_records(records, "flow", terms, limit, project_ref=project_filter, task_ref=task_ref)
    model_flow_claim_refs = collect_claim_refs_from_models_flows(models, flows)
    facts = [records[ref] for ref in sorted(model_flow_claim_refs) if ref in records]
    facts.extend(select_records(records, "claim", terms, limit, project_ref=project_filter, task_ref=task_ref))
    fallback_matches = select_fallback_claims(records, terms, limit, project_ref=project_filter, task_ref=task_ref)
    deduped_facts = _dedupe_claims(facts)
    fallback_facts = [claim for claim in deduped_facts if claim_is_fallback(claim) and not claim_is_archived(claim)]
    fallback_seen = {claim.get("id") for claim in fallback_facts}
    for claim in fallback_matches:
        if claim.get("id") not in fallback_seen:
            fallback_facts.append(claim)
            fallback_seen.add(claim.get("id"))
    return {
        "task": task,
        "current_task": current_task,
        "current_project": current_project,
        "project_ref": project_ref,
        "models": models,
        "flows": flows,
        "active_facts": [claim for claim in deduped_facts if not claim_is_fallback(claim)],
        "fallback_facts": fallback_facts,
        "hypotheses": active_hypotheses_for(
            records,
            root,
            terms,
            model_flow_claim_refs,
            project_ref=project_filter,
            task_ref=task_ref,
        ),
        "open_questions": select_records(
            records, "open_question", terms, limit, project_ref=project_filter, task_ref=task_ref
        ),
        "permissions": active_permissions_for(records, terms, project_filter, task_ref, limit),
        "guidelines": active_guidelines_for(records, terms, project_filter, task_ref, limit),
        "restrictions": active_restrictions_for(records, project_filter, task_ref),
        "proposals": select_records(records, "proposal", terms, limit, project_ref=project_filter, task_ref=task_ref),
        "plans": select_records(records, "plan", terms, limit, project_ref=project_filter, task_ref=task_ref),
        "debts": select_records(records, "debt", terms, limit, project_ref=project_filter, task_ref=task_ref),
        "limit": limit,
    }


def _append_model_lines(lines: list[str], models: list[dict]) -> None:
    lines.append("## Primary/Relevant Models")
    if not models:
        lines.append("- none found; if the task uses several claims in one scope, create or update `MODEL-*` after fact gathering")
        return
    for model in models:
        lines.append(
            f"- `{model.get('id')}` status=`{model.get('status')}` domain=`{model.get('domain')}` "
            f"scope=`{model.get('scope')}` aspect=`{model.get('aspect')}` primary={model.get('is_primary', False)}"
        )
        lines.append(f"  summary: {concise(model.get('summary', ''), 260)}")


def _append_flow_lines(lines: list[str], flows: list[dict]) -> None:
    lines.extend(["", "## Primary/Relevant Flows"])
    if not flows:
        lines.append("- none found; if the task changes an end-to-end path, create or update `FLOW-*`")
        return
    for flow in flows:
        lines.append(
            f"- `{flow.get('id')}` status=`{flow.get('status')}` domain=`{flow.get('domain')}` "
            f"scope=`{flow.get('scope')}` primary={flow.get('is_primary', False)}"
        )
        lines.append(f"  summary: {concise(flow.get('summary', ''), 260)}")


def _append_record_list(lines: list[str], title: str, records: list[dict], empty: str, limit: int) -> None:
    lines.extend(["", title])
    if not records:
        lines.append(empty)
        return
    for record in records[:limit]:
        lines.append(claim_line(record))


def context_brief_text_lines(payload: dict, icon: str) -> list[str]:
    limit = int(payload.get("limit", 8))
    lines = [f"# {icon} Context Brief", ""]
    current_project = payload.get("current_project")
    current_task = payload.get("current_task")
    if current_project:
        lines.append("## Current Project")
        lines.extend(project_detail_lines(current_project))
        lines.append("")
    if current_task:
        lines.append("## Current Task")
        lines.extend(task_detail_lines(current_task))
        lines.append("")
    lines.extend([f"Requested Task: {payload.get('task', '')}", ""])
    project_ref = payload.get("project_ref", "")
    if project_ref:
        lines.extend([f"Project filter: `{project_ref}`. Unassigned records are excluded from relevance sections.", ""])

    _append_model_lines(lines, payload.get("models", []))
    _append_flow_lines(lines, payload.get("flows", []))
    _append_record_list(
        lines,
        "## Candidate Facts",
        payload.get("active_facts", []),
        "- none found; gather sources before making decisive claims",
        limit,
    )
    _append_record_list(
        lines,
        "## Fallback Historical Facts",
        payload.get("fallback_facts", []),
        "- none; resolved/historical claims are fallback-only and archived claims require explicit refs",
        limit,
    )

    lines.extend(["", "## Active Hypotheses"])
    hypotheses = payload.get("hypotheses", [])
    if not hypotheses:
        lines.append("- none")
    for entry in hypotheses[:limit]:
        claim = entry.get("_claim", {})
        scope = entry.get("scope", claim.get("scope", ""))
        lines.append(f"- `{entry.get('claim_ref')}` scope=`{scope}`: {concise(claim.get('statement', entry.get('note', '')), 220)}")

    lines.extend(["", "## Open Questions"])
    open_questions = payload.get("open_questions", [])
    if not open_questions:
        lines.append("- none")
    for question in open_questions:
        lines.append(f"- `{question.get('id')}` status=`{question.get('status')}`: {concise(question.get('question', ''), 220)}")

    lines.extend(["", "## Scoped Permissions"])
    permissions = payload.get("permissions", [])
    if not permissions:
        lines.append("- none found for this task")
    for permission in permissions:
        applies_to = str(permission.get("applies_to", "")).strip() or "global"
        lines.append(
            f"- `{permission.get('id')}` applies_to=`{applies_to}` scope=`{permission.get('scope')}` "
            f"granted_by=`{permission.get('granted_by')}` grants={permission.get('grants', [])}"
        )

    lines.extend(["", "## Active Guidelines"])
    guidelines = payload.get("guidelines", [])
    if not guidelines:
        lines.append("- none active for current project/task")
    for guideline in guidelines:
        lines.extend(guideline_detail_lines(guideline))

    lines.extend(["", "## Active Restrictions"])
    restrictions = payload.get("restrictions", [])
    if not restrictions:
        lines.append("- none active for current project/task")
    for restriction in restrictions[:limit]:
        lines.extend(restriction_detail_lines(restriction))

    lines.extend(["", "## Active Proposals"])
    proposals = payload.get("proposals", [])
    if not proposals:
        lines.append("- none; create `PRP-*` when the agent has a constructive alternative or critique")
    for proposal in proposals:
        lines.append(f"- {proposal_summary_line(proposal)}")
        lines.append(f"  position: {concise(proposal.get('position', ''), 260)}")
        assumptions = proposal.get("assumptions", [])
        if assumptions:
            lines.append(f"  assumptions: {assumptions}")

    lines.extend(["", "## Plans / Debt"])
    for label, items in (("Plans", payload.get("plans", [])), ("Debt", payload.get("debts", []))):
        lines.append(f"### {label}")
        if not items:
            lines.append("- none")
            continue
        for item in items:
            lines.append(
                f"- `{item.get('id')}` status=`{item.get('status')}` "
                f"priority=`{item.get('priority')}`: {concise(item.get('title', ''), 180)}"
            )
    lines.extend(
        [
            "",
            "## Required Reasoning Move",
            "- If analysis will be long or tool-heavy, publish a compact `Reasoning Checkpoint` before continuing.",
            "- Before non-trivial action, run `build-reasoning-case` with the decisive claim/model/flow ids.",
            "- If the brief has facts but no model/flow for the scope, update the context after the next supported observation.",
        ]
    )
    return lines
