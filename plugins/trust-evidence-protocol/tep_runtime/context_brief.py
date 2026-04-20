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


def workspace_detail_lines(workspace: dict) -> list[str]:
    lines = [
        f"- `{workspace.get('id')}` status=`{workspace.get('status')}` "
        f"key=`{workspace.get('workspace_key')}` title=\"{workspace.get('title', '')}\""
    ]
    context_root = str(workspace.get("context_root", "")).strip()
    if context_root:
        lines.append(f"  context_root: {context_root}")
    for key in ("root_refs", "project_refs"):
        values = workspace.get(key, [])
        if values:
            lines.append(f"  {key}: {values}")
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
    workspace_ref: str,
    project_ref: str,
    limit: int,
) -> dict:
    task_ref = current_ref or None
    project_filter = project_ref or None
    current_task = records.get(current_ref) if current_ref else None
    current_workspace = records.get(workspace_ref) if workspace_ref else None
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
        "current_workspace": current_workspace,
        "current_project": current_project,
        "workspace_ref": workspace_ref,
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


def _compact_claim_line(record: dict) -> str:
    return (
        f"`{record.get('id')}` {record.get('status')}/{record.get('plane')}: "
        f"{concise(record.get('statement', ''), 110)}"
    )


def _compact_model_line(model: dict) -> str:
    return f"`{model.get('id')}` {model.get('status')} {model.get('domain')}/{model.get('aspect')}: {concise(model.get('summary', ''), 100)}"


def _compact_flow_line(flow: dict) -> str:
    return f"`{flow.get('id')}` {flow.get('status')} {flow.get('domain')}: {concise(flow.get('summary', ''), 100)}"


def _append_compact_items(lines: list[str], label: str, items: list[str], empty: str = "none") -> None:
    if items:
        lines.append(f"- {label}: " + "; ".join(items))
    else:
        lines.append(f"- {label}: {empty}")


def compact_context_brief_text_lines(payload: dict, icon: str) -> list[str]:
    limit = min(int(payload.get("limit", 8)), 3)
    lines = [f"# {icon} Context Brief (compact)", ""]
    current_workspace = payload.get("current_workspace")
    current_project = payload.get("current_project")
    current_task = payload.get("current_task")
    if current_workspace:
        lines.append(
            f"- workspace: `{current_workspace.get('id')}` key=`{current_workspace.get('workspace_key')}` "
            f"status=`{current_workspace.get('status')}`"
        )
    if current_project:
        lines.append(
            f"- project: `{current_project.get('id')}` key=`{current_project.get('project_key')}` "
            f"status=`{current_project.get('status')}`"
        )
    if current_task:
        lines.append(
            f"- task: `{current_task.get('id')}` type=`{current_task.get('task_type', 'general')}` "
            f"scope=`{current_task.get('scope')}` status=`{current_task.get('status')}`"
        )
    lines.append(f"- requested: {concise(payload.get('task', ''), 160)}")
    project_ref = payload.get("project_ref", "")
    if project_ref:
        lines.append(f"- project filter: `{project_ref}`")

    lines.extend(["", "## Evidence"])
    _append_compact_items(lines, "models", [_compact_model_line(model) for model in payload.get("models", [])[:limit]])
    _append_compact_items(lines, "flows", [_compact_flow_line(flow) for flow in payload.get("flows", [])[:limit]])
    _append_compact_items(
        lines,
        "facts",
        [_compact_claim_line(record) for record in payload.get("active_facts", [])[:limit]],
        "none; gather sources before decisive claims",
    )
    fallback_facts = payload.get("fallback_facts", [])
    if fallback_facts:
        _append_compact_items(lines, "fallback facts", [_compact_claim_line(record) for record in fallback_facts[:limit]])

    lines.extend(["", "## Controls"])
    _append_compact_items(
        lines,
        "permissions",
        [
            f"`{permission.get('id')}` {permission.get('applies_to') or 'global'}: {concise('; '.join(str(grant) for grant in permission.get('grants', [])), 90)}"
            for permission in payload.get("permissions", [])[:limit]
        ],
    )
    _append_compact_items(
        lines,
        "guidelines",
        [
            f"`{guideline.get('id')}` {guideline.get('priority')}: {concise(guideline.get('rule', ''), 100)}"
            for guideline in payload.get("guidelines", [])[:limit]
        ],
        "none active",
    )
    _append_compact_items(
        lines,
        "restrictions",
        [
            f"`{restriction.get('id')}` {restriction.get('severity')}: {concise(restriction.get('title', ''), 100)}"
            for restriction in payload.get("restrictions", [])[:limit]
        ],
        "none active",
    )

    followups: list[str] = []
    for label, key, formatter in (
        (
            "hypotheses",
            "hypotheses",
            lambda item: f"`{item.get('claim_ref')}` {concise(item.get('_claim', {}).get('statement', item.get('note', '')), 90)}",
        ),
        ("questions", "open_questions", lambda item: f"`{item.get('id')}` {concise(item.get('question', ''), 90)}"),
        ("proposals", "proposals", lambda item: f"`{item.get('id')}` {concise(item.get('position', ''), 90)}"),
        ("plans", "plans", lambda item: f"`{item.get('id')}` {item.get('priority')}: {concise(item.get('title', ''), 80)}"),
        ("debt", "debts", lambda item: f"`{item.get('id')}` {item.get('priority')}: {concise(item.get('title', ''), 80)}"),
    ):
        items = payload.get(key, [])
        if items:
            followups.append(f"{label}: " + "; ".join(formatter(item) for item in items[:3]))
    if followups:
        lines.extend(["", "## Follow-ups"])
        lines.extend(f"- {item}" for item in followups)

    lines.extend(
        [
            "",
            "## Reasoning",
            "- Use `record_detail`, `linked_records`, or `brief-context --detail full` before citing detailed proof.",
            "- Publish a compact Evidence Chain / Reasoning Checkpoint before planning, permission, persistence, or edits.",
        ]
    )
    return lines


def context_brief_text_lines(payload: dict, icon: str, detail: str = "compact") -> list[str]:
    if detail == "compact":
        return compact_context_brief_text_lines(payload, icon)

    limit = int(payload.get("limit", 8))
    lines = [f"# {icon} Context Brief", ""]
    current_workspace = payload.get("current_workspace")
    current_project = payload.get("current_project")
    current_task = payload.get("current_task")
    if current_workspace:
        lines.append("## Current Workspace")
        lines.extend(workspace_detail_lines(current_workspace))
        lines.append("")
    if current_project:
        lines.append("## Current Project")
        lines.extend(project_detail_lines(current_project))
        lines.append("")
    if current_task:
        lines.append("## Current Task")
        lines.extend(task_detail_lines(current_task))
        lines.append("")
    lines.extend([f"- requested: {concise(payload.get('task', ''), 260)}", ""])
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
