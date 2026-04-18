"""Generated review, index, attention, and backlog views."""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

from .claims import (
    claim_attention,
    claim_is_archived,
    claim_is_fallback,
    claim_lifecycle_state,
    claim_retrieval_tier,
    parse_timestamp,
)
from .hypotheses import load_hypotheses_index
from .io import write_text_file
from .links import dependency_refs_for_record
from .records import RECORD_DIRS
from .reports import rel_display, write_report
from .settings import load_settings
from .validation import safe_list

ACTIVE_PLAN_STATUSES = {"proposed", "active", "blocked"}
ACTIVE_DEBT_STATUSES = {"open", "accepted", "scheduled"}
TERMINAL_PLAN_STATUSES = {"completed", "abandoned"}
TERMINAL_DEBT_STATUSES = {"resolved", "invalid", "wont-fix"}
PRIORITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}


def write_stale_report(root: Path, records: dict[str, dict], stale_days: int = 30) -> None:
    threshold = datetime.now().astimezone() - timedelta(days=stale_days)
    lines: list[str] = []
    for _, data in sorted(records.items()):
        timestamp = parse_timestamp(str(data.get("captured_at") or data.get("recorded_at") or ""))
        if timestamp and timestamp < threshold:
            lines.append(
                f"- `{rel_display(root, Path(data['_path']))}`: stale timestamp {timestamp.isoformat(timespec='seconds')}\n"
            )
    write_report(
        root / "review" / "stale.md",
        "Generated Stale Review",
        "Generated stale-record diagnostics. Do not treat this file as a source of truth.",
        lines,
    )


def write_models_report(root: Path, records: dict[str, dict]) -> None:
    primary_by_scope: dict[tuple[str, str], list[str]] = {}
    lines: list[str] = []
    for _, data in sorted(records.items()):
        if data.get("record_type") != "model":
            continue
        scope = str(data.get("scope", "")).strip()
        aspect = str(data.get("aspect", "")).strip()
        if data.get("is_primary") is True:
            primary_by_scope.setdefault((scope, aspect), []).append(str(data.get("id", "")).strip())
        if str(data.get("status", "")).strip() == "stable" and safe_list(data, "hypothesis_refs"):
            lines.append(
                f"- `{rel_display(root, Path(data['_path']))}`: stable model must not rely on hypothesis_refs\n"
            )
    for (scope, aspect), ids in sorted(primary_by_scope.items()):
        if len(ids) > 1:
            lines.append(f"- multiple primary models for scope=`{scope}` aspect=`{aspect}`: {', '.join(ids)}\n")
    write_report(
        root / "review" / "models.md",
        "Generated Model Review",
        "Generated diagnostics for model records. Do not treat this file as a source of truth.",
        lines,
    )


def write_flows_report(root: Path, records: dict[str, dict]) -> None:
    primary_by_scope: dict[str, list[str]] = {}
    lines: list[str] = []
    for _, data in sorted(records.items()):
        if data.get("record_type") != "flow":
            continue
        scope = str(data.get("scope", "")).strip()
        if data.get("is_primary") is True:
            primary_by_scope.setdefault(scope, []).append(str(data.get("id", "")).strip())
        oracle = data.get("oracle", {})
        if str(data.get("status", "")).strip() in {"working", "stable"}:
            if not isinstance(oracle, dict) or (
                not safe_list(oracle, "success_claim_refs") and not safe_list(oracle, "failure_claim_refs")
            ):
                lines.append(f"- `{rel_display(root, Path(data['_path']))}`: working/stable flow missing usable oracle\n")
        for step in data.get("steps", []) if isinstance(data.get("steps"), list) else []:
            if not isinstance(step, dict):
                continue
            if str(step.get("status", "")).strip() == "contradicted":
                lines.append(
                    f"- `{rel_display(root, Path(data['_path']))}` step `{step.get('id', '')}`: contradicted and needs review\n"
                )
    for scope, ids in sorted(primary_by_scope.items()):
        if len(ids) > 1:
            lines.append(f"- multiple primary flows for scope=`{scope}`: {', '.join(ids)}\n")
    write_report(
        root / "review" / "flows.md",
        "Generated Flow Review",
        "Generated diagnostics for flow records. Do not treat this file as a source of truth.",
        lines,
    )


def write_hypotheses_report(root: Path, records: dict[str, dict]) -> None:
    entries, parse_errors = load_hypotheses_index(root)
    lines = [f"- `{rel_display(root, error.path)}`: {error.message}\n" for error in parse_errors]
    active_by_scope: dict[str, list[str]] = {}
    for entry in entries:
        claim_ref = str(entry.get("claim_ref", "")).strip()
        if not claim_ref:
            continue
        scope = str(entry.get("scope", "")).strip()
        status = str(entry.get("status", "")).strip()
        if status == "active":
            active_by_scope.setdefault(scope or "<missing-scope>", []).append(claim_ref)
            mode = str(entry.get("mode", "durable")).strip() or "durable"
            based_on_hypotheses = entry.get("based_on_hypotheses", [])
            if mode == "exploration":
                suffix = f" based_on={', '.join(based_on_hypotheses)}" if based_on_hypotheses else ""
                lines.append(f"- exploration hypothesis `{claim_ref}` is local-only and not valid as proof{suffix}\n")
            claim = records.get(claim_ref)
            if claim and str(claim.get("status", "")).strip() != "tentative":
                lines.append(
                    f"- `hypotheses.jsonl` claim `{claim_ref}` is indexed as active but claim status is `{claim.get('status', '')}`\n"
                )
    for scope, ids in sorted(active_by_scope.items()):
        if len(ids) > 5:
            lines.append(f"- scope=`{scope}` has {len(ids)} active hypotheses: {', '.join(ids)}\n")
    write_report(
        root / "review" / "hypotheses.md",
        "Generated Hypothesis Review",
        "Generated diagnostics for hypothesis index entries. Do not treat this file as a source of truth.",
        lines,
    )


def record_updated_at(data: dict) -> str:
    for key in ("updated_at", "recorded_at", "captured_at", "created_at", "granted_at", "planned_at", "executed_at"):
        value = str(data.get(key, "")).strip()
        if value:
            return value
    return ""


def record_attention_label(data: dict) -> str:
    record_type = str(data.get("record_type", "")).strip()
    if record_type == "claim":
        return str(data.get("statement", "")).strip()
    if record_type in {"model", "flow"}:
        return str(data.get("summary", "")).strip()
    if record_type in {"task", "working_context", "plan", "debt", "restriction", "project"}:
        return str(data.get("title", "")).strip()
    if record_type == "proposal":
        subject = str(data.get("subject", "")).strip()
        position = str(data.get("position", "")).strip()
        if subject and position:
            return f"{subject}: {position}"
        return subject or position
    if record_type == "open_question":
        return str(data.get("question", "")).strip()
    if record_type == "permission":
        grants = safe_list(data, "grants")
        return "; ".join(grants)
    if record_type == "source":
        return str(data.get("quote", "")).strip() or ", ".join(safe_list(data, "artifact_refs"))
    if record_type == "action":
        return str(data.get("kind", "")).strip()
    return ""


def attention_line(root: Path, data: dict) -> str:
    path = rel_display(root, Path(data["_path"]))
    status = str(data.get("status", data.get("critique_status", ""))).strip()
    status_part = f" status=`{status}`" if status else ""
    lifecycle_part = ""
    if data.get("record_type") == "claim":
        state = claim_lifecycle_state(data)
        attention = claim_attention(data)
        if state != "active" or attention != "normal":
            lifecycle_part = f" lifecycle=`{state}` attention=`{attention}`"
    project_refs = safe_list(data, "project_refs")
    task_refs = safe_list(data, "task_refs")
    scope_parts = []
    if project_refs:
        scope_parts.append(f"project_refs={','.join(project_refs)}")
    if task_refs:
        scope_parts.append(f"task_refs={','.join(task_refs)}")
    scope_suffix = f" {' '.join(scope_parts)}" if scope_parts else ""
    label = record_attention_label(data)
    label_suffix = f" — {label}" if label else ""
    return (
        f"- `{data.get('id')}` [{path}] type=`{data.get('record_type')}`{status_part}{lifecycle_part}"
        f" updated=`{record_updated_at(data) or 'unknown'}`{scope_suffix}{label_suffix}\n"
    )


def recent_records(records: dict[str, dict], record_types: set[str], limit: int) -> list[dict]:
    candidates = [
        data
        for data in records.values()
        if str(data.get("record_type", "")).strip() in record_types
        and str(data.get("status", "")).strip()
        not in TERMINAL_PLAN_STATUSES | TERMINAL_DEBT_STATUSES | {"superseded", "rejected", "abandoned"}
        and not claim_is_fallback(data)
    ]
    return sorted(candidates, key=lambda item: (record_updated_at(item), str(item.get("id", ""))), reverse=True)[:limit]


def fallback_claims(records: dict[str, dict], limit: int) -> list[dict]:
    candidates = [
        data
        for data in records.values()
        if data.get("record_type") == "claim"
        and claim_is_fallback(data)
        and not claim_is_archived(data)
        and str(data.get("status", "")).strip() != "rejected"
    ]
    return sorted(
        candidates,
        key=lambda item: (claim_retrieval_tier(item), record_updated_at(item), str(item.get("id", ""))),
        reverse=True,
    )[:limit]


def write_attention_report(root: Path, records: dict[str, dict], limit: int = 12) -> None:
    settings = load_settings(root)
    current_project_ref = str(settings.get("current_project_ref") or "").strip()
    current_task_ref = str(settings.get("current_task_ref") or "").strip()

    lines = [
        "This file is generated as an attention/navigation view. Do not treat it as a source of truth.\n",
        "\n",
        f"- current_project_ref: `{current_project_ref or 'none'}`\n",
        f"- current_task_ref: `{current_task_ref or 'none'}`\n",
        "\n",
        "Trust order for lookup: active `corroborated` -> active `supported` -> active `contested/rejected` for conflict awareness -> active `tentative` for exploration -> resolved/historical fallback only -> archived explicit refs only.\n",
        "\n",
        "## Current Focus\n",
        "\n",
    ]

    focus_ids = [ref for ref in (current_project_ref, current_task_ref) if ref and ref in records]
    if focus_ids:
        for record_id in focus_ids:
            lines.append(attention_line(root, records[record_id]))
    else:
        lines.append("- none\n")

    active_restrictions = [
        data
        for data in records.values()
        if data.get("record_type") == "restriction" and str(data.get("status", "")).strip() == "active"
    ]
    active_guidelines = [
        data
        for data in records.values()
        if data.get("record_type") == "guideline" and str(data.get("status", "")).strip() == "active"
    ]
    active_permissions = [data for data in records.values() if data.get("record_type") == "permission"]
    active_hypotheses = [
        data
        for data in records.values()
        if data.get("record_type") == "claim"
        and str(data.get("status", "")).strip() == "tentative"
        and not claim_is_fallback(data)
    ]
    active_proposals = [
        data
        for data in records.values()
        if data.get("record_type") == "proposal" and str(data.get("status", "")).strip() == "active"
    ]

    sections = [
        (
            "Active Restrictions",
            sorted(active_restrictions, key=lambda item: (record_updated_at(item), str(item.get("id", ""))), reverse=True)[
                :limit
            ],
        ),
        (
            "Active Guidelines",
            sorted(active_guidelines, key=lambda item: (record_updated_at(item), str(item.get("id", ""))), reverse=True)[
                :limit
            ],
        ),
        (
            "Active Proposals",
            sorted(active_proposals, key=lambda item: (record_updated_at(item), str(item.get("id", ""))), reverse=True)[
                :limit
            ],
        ),
        ("Recent Claims", recent_records(records, {"claim"}, limit)),
        ("Recent Models And Flows", recent_records(records, {"model", "flow"}, limit)),
        ("Recent Working Contexts", recent_records(records, {"working_context"}, limit)),
        ("Recent Plans And Debt", recent_records(records, {"plan", "debt"}, limit)),
        ("Open Questions", recent_records(records, {"open_question"}, limit)),
        (
            "Recent Permissions",
            sorted(active_permissions, key=lambda item: (record_updated_at(item), str(item.get("id", ""))), reverse=True)[
                :limit
            ],
        ),
        (
            "Tentative Claims",
            sorted(active_hypotheses, key=lambda item: (record_updated_at(item), str(item.get("id", ""))), reverse=True)[
                :limit
            ],
        ),
        ("Fallback Historical Claims", fallback_claims(records, limit)),
    ]

    for title, items in sections:
        lines.extend(["\n", f"## {title}\n", "\n"])
        if items:
            for item in items:
                lines.append(attention_line(root, item))
        else:
            lines.append("- none\n")

    write_text_file(root / "review" / "attention.md", "".join(lines))


def write_resolved_report(root: Path, records: dict[str, dict], limit: int = 50) -> None:
    fallback_items = fallback_claims(records, limit)
    archived_items = [
        data
        for data in records.values()
        if data.get("record_type") == "claim"
        and claim_is_archived(data)
        and str(data.get("status", "")).strip() != "rejected"
    ]
    archived_items = sorted(
        archived_items,
        key=lambda item: (record_updated_at(item), str(item.get("id", ""))),
        reverse=True,
    )[:limit]

    lines = [
        "This file is generated as a lifecycle/navigation view. Do not treat it as a source of truth.\n",
        "\n",
        "Resolved and historical claims remain searchable, but normal lookup should use them only after active claims, models, and flows fail to answer the task.\n",
        "Archived claims are explicit-reference/audit material and must not be used as default task context.\n",
        "\n",
        "## Fallback Historical Claims\n",
        "\n",
    ]
    if fallback_items:
        for item in fallback_items:
            lines.append(attention_line(root, item))
    else:
        lines.append("- none\n")

    lines.extend(["\n", "## Archived Explicit-Only Claims\n", "\n"])
    if archived_items:
        for item in archived_items:
            lines.append(attention_line(root, item))
    else:
        lines.append("- none\n")

    write_text_file(root / "review" / "resolved.md", "".join(lines))


def collect_dependency_impact(root: Path, records: dict[str, dict], anchor_ref: str) -> dict[str, list[str]]:
    reverse_edges: dict[str, set[str]] = {}
    for record_id, data in records.items():
        for ref in dependency_refs_for_record(data):
            reverse_edges.setdefault(ref, set()).add(record_id)

    hypothesis_entries, _ = load_hypotheses_index(root)
    hypothesis_users: set[str] = set()
    for entry in hypothesis_entries:
        if str(entry.get("claim_ref", "")).strip() != anchor_ref:
            continue
        used_by = entry.get("used_by", {})
        if isinstance(used_by, dict):
            for values in used_by.values():
                if isinstance(values, list):
                    hypothesis_users.update(str(item).strip() for item in values if str(item).strip())
        rollback_refs = entry.get("rollback_refs", [])
        if isinstance(rollback_refs, list):
            hypothesis_users.update(str(item).strip() for item in rollback_refs if str(item).strip())

    direct = sorted(reverse_edges.get(anchor_ref, set()) | hypothesis_users)
    transitively_seen: set[str] = set(direct)
    frontier = list(direct)
    while frontier:
        current = frontier.pop()
        for dependent in reverse_edges.get(current, set()):
            if dependent in transitively_seen:
                continue
            transitively_seen.add(dependent)
            frontier.append(dependent)

    direct_by_type: dict[str, list[str]] = {}
    transitive_only_by_type: dict[str, list[str]] = {}
    for record_id in direct:
        record = records.get(record_id)
        record_type = str(record.get("record_type", "external")).strip() if record else "external"
        direct_by_type.setdefault(record_type, []).append(record_id)
    for record_id in sorted(transitively_seen):
        if record_id in direct:
            continue
        record = records.get(record_id)
        record_type = str(record.get("record_type", "external")).strip() if record else "external"
        transitive_only_by_type.setdefault(record_type, []).append(record_id)

    return {
        "direct": direct,
        "transitive": sorted(transitively_seen),
        "direct_by_type": {key: sorted(value) for key, value in direct_by_type.items()},
        "transitive_only_by_type": {key: sorted(value) for key, value in transitive_only_by_type.items()},
    }


def backlog_sort_key(data: dict) -> tuple[int, int, str, str]:
    priority = str(data.get("priority", "")).strip()
    status = str(data.get("status", "")).strip()
    status_order = 0
    if data.get("record_type") == "plan":
        status_order = {"active": 0, "proposed": 1, "blocked": 2}.get(status, 9)
    elif data.get("record_type") == "debt":
        status_order = {"open": 0, "scheduled": 1, "accepted": 2}.get(status, 9)
    title = str(data.get("title", "")).strip().lower()
    return (PRIORITY_ORDER.get(priority, 99), status_order, title, str(data.get("id", "")))


def write_backlog(root: Path, records: dict[str, dict]) -> None:
    active_plans: list[dict] = []
    active_debts: list[dict] = []
    for _, data in sorted(records.items()):
        record_type = str(data.get("record_type", "")).strip()
        status = str(data.get("status", "")).strip()
        if record_type == "plan" and status in ACTIVE_PLAN_STATUSES:
            active_plans.append(data)
        if record_type == "debt" and status in ACTIVE_DEBT_STATUSES:
            active_debts.append(data)

    active_plans.sort(key=backlog_sort_key)
    active_debts.sort(key=backlog_sort_key)

    lines = [
        "# Active Backlog\n",
        "\n",
        "This view is generated from canonical plan/debt records.\n",
        "\n",
        "Excluded from active backlog:\n",
        "- plans with statuses `completed`, `abandoned`\n",
        "- debt with statuses `resolved`, `invalid`, `wont-fix`\n",
        "\n",
        "## Plans\n",
        "\n",
    ]
    if not active_plans:
        lines.append("- none\n")
    else:
        for data in active_plans:
            path = rel_display(root, Path(data["_path"]))
            blocked = ""
            blocked_refs = safe_list(data, "blocked_by")
            if blocked_refs:
                blocked = f" blocked_by={','.join(blocked_refs)}"
            lines.append(
                f"- `{data['id']}` priority=`{data.get('priority', '')}` status=`{data.get('status', '')}`"
                f" [{path}] title=\"{data.get('title', '')}\"{blocked}\n"
            )
    lines.extend(["\n", "## Debt\n", "\n"])
    if not active_debts:
        lines.append("- none\n")
    else:
        for data in active_debts:
            path = rel_display(root, Path(data["_path"]))
            plan_refs = safe_list(data, "plan_refs")
            plan_suffix = f" plan_refs={','.join(plan_refs)}" if plan_refs else ""
            lines.append(
                f"- `{data['id']}` priority=`{data.get('priority', '')}` status=`{data.get('status', '')}`"
                f" [{path}] title=\"{data.get('title', '')}\"{plan_suffix}\n"
            )
    write_text_file(root / "backlog.md", "".join(lines))


def build_index(root: Path, records: dict[str, dict]) -> None:
    counts = {kind: 0 for kind in RECORD_DIRS}
    groups: dict[str, list[tuple[str, str, str]]] = {kind: [] for kind in RECORD_DIRS}
    for record_id, data in sorted(records.items()):
        record_type = str(data.get("record_type", ""))
        if record_type not in counts:
            continue
        counts[record_type] += 1
        summary = ""
        if record_type == "project":
            summary = f"{data.get('status', '')} | {data.get('project_key', '')} | {data.get('title', '')}"
        elif record_type == "source":
            summary = str(data.get("source_kind", ""))
            confidence = str(data.get("confidence", "")).strip()
            if confidence:
                summary = f"{summary} | {confidence}"
        elif record_type == "claim":
            comparison = data.get("comparison")
            claim_key = ""
            if isinstance(comparison, dict):
                claim_key = str(comparison.get("key", "")).strip()
            claim_kind = str(data.get("claim_kind", "")).strip()
            confidence = str(data.get("confidence", "")).strip()
            lifecycle_state = claim_lifecycle_state(data)
            attention = claim_attention(data)
            label = claim_key or data.get("statement", "")
            prefix_parts = [str(data.get("status", "")).strip()]
            if claim_kind:
                prefix_parts.append(claim_kind)
            if confidence:
                prefix_parts.append(confidence)
            if lifecycle_state != "active" or attention != "normal":
                prefix_parts.append(f"lifecycle={lifecycle_state}")
                prefix_parts.append(f"attention={attention}")
            summary = f"{' | '.join(part for part in prefix_parts if part)} | {label}"
        elif record_type == "permission":
            applies_to = str(data.get("applies_to", "global")).strip() or "global"
            summary = f"{applies_to} | {data.get('granted_by', '')}"
        elif record_type == "restriction":
            summary = f"{data.get('status', '')} | {data.get('applies_to', '')} | {data.get('severity', '')} | {data.get('title', '')}"
        elif record_type == "guideline":
            summary = f"{data.get('status', '')} | {data.get('domain', '')} | {data.get('applies_to', '')} | {data.get('priority', '')} | {data.get('rule', '')}"
        elif record_type == "proposal":
            summary = f"{data.get('status', '')} | {data.get('confidence', '')} | {data.get('subject', '')}"
        elif record_type == "action":
            summary = f"{data.get('status', '')} | {data.get('kind', '')}"
        elif record_type == "task":
            summary = f"{data.get('status', '')} | {data.get('title', '')}"
        elif record_type == "plan":
            summary = f"{data.get('status', '')} | {data.get('priority', '')} | {data.get('title', '')}"
        elif record_type == "debt":
            summary = f"{data.get('status', '')} | {data.get('priority', '')} | {data.get('title', '')}"
        elif record_type == "model":
            summary = (
                f"{data.get('status', '')} | {data.get('knowledge_class', '')} | "
                f"{data.get('aspect', '')} | primary={data.get('is_primary', False)}"
            )
        elif record_type == "flow":
            summary = (
                f"{data.get('status', '')} | {data.get('knowledge_class', '')} | "
                f"primary={data.get('is_primary', False)}"
            )
        elif record_type == "open_question":
            summary = f"{data.get('status', '')} | {data.get('question', '')}"
        groups[record_type].append((record_id, str(data.get("scope", "")), summary))

    settings = load_settings(root)
    lines = [
        "# Codex Context Index\n",
        "\n",
        "This index is generated from canonical records.\n",
        "\n",
        "Canonical layers:\n",
        "- `records/`\n",
        "- `artifacts/`\n",
        "\n",
        "Generated working views:\n",
        "- `backlog.md`\n",
        "\n",
        "Generated review views:\n",
        "- `review/models.md`\n",
        "- `review/flows.md`\n",
        "- `review/hypotheses.md`\n",
        "- `review/resolved.md`\n",
        "- `review/attention.md`\n",
        "\n",
        f"Current strictness: `{settings.get('allowed_freedom', 'proof-only')}`\n",
        f"Current project: `{settings.get('current_project_ref') or 'none'}`\n",
        f"Current task: `{settings.get('current_task_ref') or 'none'}`\n",
        "\n",
        "Counts:\n",
    ]
    for record_type in (
        "project",
        "source",
        "claim",
        "permission",
        "restriction",
        "guideline",
        "proposal",
        "action",
        "task",
        "plan",
        "debt",
        "model",
        "flow",
        "open_question",
    ):
        lines.append(f"- `{record_type}`: {counts[record_type]}\n")
    entries, _ = load_hypotheses_index(root)
    active_hypotheses = sum(1 for entry in entries if str(entry.get("status", "")).strip() == "active")
    lines.append(f"- `active_hypotheses`: {active_hypotheses}\n")
    lines.append("\n")
    for record_type in (
        "project",
        "source",
        "claim",
        "permission",
        "restriction",
        "guideline",
        "proposal",
        "action",
        "task",
        "plan",
        "debt",
        "model",
        "flow",
        "open_question",
    ):
        lines.append(f"## {record_type.title()} Records\n\n")
        if not groups[record_type]:
            lines.append("- none\n\n")
            continue
        for record_id, scope, summary in groups[record_type]:
            path = root / "records" / record_type / f"{record_id}.json"
            rel = rel_display(root, path)
            suffix = f" — {summary}" if summary else ""
            lines.append(f"- `{record_id}` [{rel}] scope=`{scope}`{suffix}\n")
        lines.append("\n")
    write_text_file(root / "index.md", "".join(lines))
