"""Token-light next-step routing for TEP agents."""

from __future__ import annotations

from pathlib import Path

from .core_validators import validate_active_focus
from .hydration import compute_context_fingerprint, load_hydration_state
from .reason_pressure import build_reason_pressure, build_start_briefing
from .reason_ledger import validate_reason_access
from .retrieval import active_guidelines_for
from .scopes import active_restrictions_for, current_project_ref, current_task_ref, current_workspace_ref
from .search import concise
from .settings import load_effective_settings
from .tasks import validate_task_decomposition_payload


NEXT_STEP_INTENTS = {"auto", "answer", "plan", "edit", "test", "persist", "permission", "debug", "after-mutation"}
VALID_HYDRATION_STATUSES = {"hydrated", "hydrated-with-conflicts"}
GRANT_REQUIRED_FREEDOMS = {"evidence-authorized", "implementation-choice"}


def _record_summary(records: dict[str, dict], record_ref: str, key_field: str) -> dict:
    record = records.get(record_ref, {})
    return {
        "id": record_ref,
        "status": str(record.get("status", "missing" if record_ref else "")).strip(),
        "key": str(record.get(key_field, "")).strip(),
        "title": str(record.get("title", "")).strip(),
    }


def _hydration_is_fresh(root: Path, state: dict) -> bool:
    return (
        str(state.get("status", "")).strip() in VALID_HYDRATION_STATUSES
        and str(state.get("fingerprint", "")) == compute_context_fingerprint(root)
    )


def _intent_route(intent: str, task: str) -> tuple[str, list[str]]:
    task_arg = f' --task "{task}"' if task else ' --task "..."'
    query_arg = f' --query "{task}"' if task else ' --query "..."'
    routes = {
        "answer": ("answering", [f"lookup{query_arg} --reason answering --kind auto --format json", f"brief-context{task_arg}", "record-detail / linked-records before citing proof"]),
        "plan": ("planning", [f"lookup{query_arg} --reason planning --kind auto --format json", "validate-task-decomposition --task TASK-*", f"brief-context{task_arg}", "record/reuse relation CLM", "reason-step --mode planning --claim CLM-*"]),
        "edit": ("editing", ["validate-task-decomposition --task TASK-*", f"lookup{query_arg} --reason editing --kind auto --format json", f"guidelines-for{task_arg}", "record/reuse proof-capable relation CLM", "reason-step --mode edit --claim CLM-*", "preflight-task --mode edit"]),
        "test": ("testing", [f"lookup{query_arg} --reason debugging --kind auto --format json", f"brief-context{task_arg}", "record/reuse proof-capable relation CLM", "reason-step --mode test --claim CLM-*", "record-evidence for meaningful test output", "hydrate-context after mutation"]),
        "persist": ("persisting", [f"lookup{query_arg} --reason migration --kind auto --format json", "classify input/source first", "record-evidence or record-* through context_cli", "hydrate-context"]),
        "permission": ("permission", [f"lookup{query_arg} --reason permission --kind policy --format json", "build-reasoning-case", "cite CLM/GLD/PRM ids + quotes", "request explicit approval if needed"]),
        "debug": ("debugging", ["show-hydration", f"lookup{query_arg} --reason debugging --kind auto --format json", "review-context", "scan-conflicts / reindex-context if needed"]),
        "after-mutation": ("after mutation", ["hydrate-context", f"lookup{query_arg} --reason debugging --kind auto --format json", "record-evidence/action if meaningful", "show-hydration"]),
    }
    return routes.get(intent, ("general", [f"brief-context{task_arg}", "choose answer|plan|edit|test|persist|permission|debug route"]))


def _route_graph(intent: str) -> dict:
    branch_sets = {
        "auto": [
            {"if": "need facts", "then": "answer"},
            {"if": "need intended work", "then": "plan"},
            {"if": "need mutation", "then": "edit|test"},
            {"if": "need durable memory", "then": "persist"},
            {"if": "blocked", "then": "permission|debug"},
        ],
        "answer": [
            {"if": "record answers", "then": "record-detail|linked-records"},
            {"if": "record missing", "then": "search_records|investigate"},
            {"if": "answer reusable", "then": "persist"},
        ],
        "plan": [
            {"if": "task needs decomposition", "then": "confirm-atomic-task|decompose-task"},
            {"if": "no current valid STEP", "then": "lookup -> record/reuse relation CLM -> reason-step --claim"},
            {"if": "legacy proof chain explicit", "then": "validate-evidence-chain"},
            {"if": "scope/task drift", "then": "task-drift-check|switch-task"},
            {"if": "permission needed", "then": "permission"},
        ],
        "edit": [
            {"if": "current task is parent/invalid", "then": "switch to leaf task|decompose-task"},
            {"if": "guidelines missing", "then": "guidelines-for"},
            {"if": "proof gap", "then": "record support and relation CLM"},
            {"if": "no current valid STEP", "then": "lookup -> relation CLM -> reason-step --claim"},
            {"if": "grant missing", "then": "reason-step --claim|reason-review --grant"},
            {"if": "blocked by policy", "then": "permission|debug"},
            {"if": "edited", "then": "after-mutation"},
        ],
        "test": [
            {"if": "no current test STEP", "then": "lookup -> relation CLM -> reason-step --mode test --claim"},
            {"if": "test output meaningful", "then": "record-evidence"},
            {"if": "failure unexplained", "then": "debug"},
            {"if": "state changed", "then": "after-mutation"},
        ],
        "persist": [
            {"if": "raw input", "then": "record-input|record-evidence"},
            {"if": "truth claim", "then": "record-evidence"},
            {"if": "work remains", "then": "record-plan|record-debt|record-open-question"},
        ],
        "permission": [
            {"if": "proof sufficient", "then": "cite ids+quotes"},
            {"if": "proof insufficient", "then": "ask|debug"},
            {"if": "approval received", "then": "edit|test"},
        ],
        "debug": [
            {"if": "hydration stale", "then": "hydrate-context"},
            {"if": "records invalid", "then": "review-context|reindex-context"},
            {"if": "runtime unknown", "then": "safe probe"},
        ],
        "after-mutation": [
            {"if": "test/log supports fact", "then": "record-evidence"},
            {"if": "follow-up work remains", "then": "record-plan|record-debt"},
            {"if": "context changed", "then": "hydrate-context"},
        ],
    }
    return {
        "graph_version": 1,
        "branches": branch_sets.get(intent, branch_sets["auto"]),
        "stop_conditions": [
            "hydration stale/errors/conflicts before decisive action",
            "missing source-backed proof for truth claim",
            "missing valid STEP/claim relation before GRANT/final",
            "restriction or permission gap blocks requested scope",
        ],
    }


def build_next_step_payload(records: dict[str, dict], root: Path, intent: str = "auto", task: str = "") -> dict:
    intent = intent if intent in NEXT_STEP_INTENTS else "auto"
    task = task.strip()
    settings = load_effective_settings(root)
    hydration = load_hydration_state(root)
    workspace_ref = current_workspace_ref(root)
    project_ref = current_project_ref(root)
    task_ref = current_task_ref(root)
    active_restrictions = active_restrictions_for(records, project_ref or None, task_ref or None)
    active_guidelines = active_guidelines_for(records, [], project_ref or None, task_ref or None, 5)
    active_focus_errors = validate_active_focus(root, records)
    fresh = _hydration_is_fresh(root, hydration)
    conflict_count = int(hydration.get("conflict_count") or 0)
    error_count = int(hydration.get("error_count") or 0)

    forced: list[str] = []
    if not fresh:
        forced.append("hydrate-context")
    if error_count:
        forced.append("review-context")
    if conflict_count:
        forced.append("scan-conflicts")
    if active_focus_errors and intent in {"edit", "test", "persist", "permission"}:
        forced.append("resolve-active-focus")
    if active_restrictions and intent in {"edit", "test", "persist", "permission"}:
        forced.append("show-restrictions")
    task_decomposition = None
    if task_ref:
        task_decomposition = validate_task_decomposition_payload(records, task_ref)
        if intent in {"plan", "edit", "test", "persist", "permission"} and not task_decomposition.get("accepted"):
            forced.append("validate-task-decomposition")
        if intent in {"edit", "test"} and task_decomposition.get("status") != "atomic":
            forced.append("switch-to-atomic-leaf-task")
    if intent == "edit" and not active_guidelines:
        forced.append("guidelines-for")

    route_label, route_steps = _intent_route(intent, task)
    route_steps = list(route_steps)
    start_briefing = build_start_briefing(root, records, intent=intent)
    reason_pressure = build_reason_pressure(root, records, intent=intent)
    grant_status = {
        "required": False,
        "mode": "",
        "action_kind": "",
        "ok": None,
        "reason": "",
        "command": "",
    }
    if intent == "edit" and str(settings.get("allowed_freedom", "proof-only")) in GRANT_REQUIRED_FREEDOMS:
        grant_check = validate_reason_access(root, mode="edit", action_kind=None)
        grant_status = {
            "required": True,
            "mode": "edit",
            "action_kind": "<action-kind>",
            "ok": bool(grant_check.get("ok")),
            "reason": str(grant_check.get("reason") or ""),
            "command": "reason-review --reason STEP-* --mode edit --kind <action-kind> --grant",
        }
        grant_step = grant_status["command"]
        if grant_step not in route_steps:
            insert_at = max(0, len(route_steps) - 1)
            route_steps.insert(insert_at, grant_step)
    return {
        "intent": intent,
        "route_label": route_label,
        "task": task,
        "hydration_status": str(hydration.get("status", "unhydrated")),
        "hydration_fresh": fresh,
        "conflict_count": conflict_count,
        "error_count": error_count,
        "allowed_freedom": str(settings.get("allowed_freedom", "proof-only")),
        "workspace": _record_summary(records, workspace_ref, "workspace_key") if workspace_ref else None,
        "project": _record_summary(records, project_ref, "project_key") if project_ref else None,
        "current_task": _record_summary(records, task_ref, "scope") if task_ref else None,
        "restriction_count": len(active_restrictions),
        "guideline_count": len(active_guidelines),
        "task_decomposition": task_decomposition,
        "active_focus": {
            "ok": not active_focus_errors,
            "errors": [error.message for error in active_focus_errors],
        },
        "forced_first": forced,
        "route_steps": route_steps,
        "route_graph": _route_graph(intent),
        "start_briefing": start_briefing,
        "reason_pressure": reason_pressure,
        "grant": grant_status,
        "api_contract": {
            "contract_version": 1,
            "normal_entrypoint": "lookup",
            "route_graph_required": True,
            "drill_down_tools": ["brief-context", "search-records", "claim-graph", "record-detail", "linked-records"],
            "proof_rule": "Navigation output is not proof; cite canonical records with quotes before decisions.",
            "chain_rule": "Before STEP/GRANT/final, advance through connected CLM records; relation CLM records are the semantic edges.",
            "reason_rule": "Treat STEP-* as the agent's task/WCTX cursor: start by checking the briefing, then extend or fork the ledger when intent, evidence, tests, or direction change.",
            "rights_rule": "Briefing includes a non-authoritative rights snapshot, but the agent must still start with a personal agent_private_key; even next_step/lookup may require identity checks before routing. Protected actions still require runtime grant validation at use time.",
            "grant_rule": "Mutating protected actions in evidence-authorized or implementation-choice require a fresh one-shot GRANT-* bound to current workspace/project/task/fingerprint.",
            "write_rule": "Use record-support/record-evidence so FILE/RUN/SRC/CLM links are built mechanically; low-level record-source/record-claim are for plugin-dev or migration.",
            "task_rule": "Mutating work belongs on a valid atomic leaf TASK-*; parent tasks are orchestration only.",
        },
        "note": "Navigation only. This route is not proof; cite records with quotes before decisions.",
    }


def next_step_text_lines(payload: dict, icon: str, detail: str = "compact") -> list[str]:
    lines = [f"# {icon} TEP Next Step", ""]
    current = [
        f"hydration={payload.get('hydration_status')} fresh={payload.get('hydration_fresh')}",
        f"conflicts={payload.get('conflict_count')} errors={payload.get('error_count')}",
        f"freedom={payload.get('allowed_freedom')}",
    ]
    workspace = payload.get("workspace") or {}
    project = payload.get("project") or {}
    task = payload.get("current_task") or {}
    if workspace.get("id"):
        current.append(f"workspace={workspace.get('id')}")
    if project.get("id"):
        current.append(f"project={project.get('id')}")
    if task.get("id"):
        current.append(f"task={task.get('id')}")
    lines.append("- current: " + " | ".join(current))
    lines.append(f"- intent: {payload.get('intent')} ({payload.get('route_label')})")
    briefing = payload.get("start_briefing") or {}
    current_step = briefing.get("current_step_ref") or "none"
    current_branch = briefing.get("current_branch") or "none"
    lines.append(
        f"- briefing: step=`{current_step}` mode=`{briefing.get('current_mode') or 'none'}` "
        f"branch=`{current_branch}` recent_steps=`{len(briefing.get('recent_steps') or [])}` "
        f"recent_actions=`{len(briefing.get('recent_actions') or [])}`"
    )
    permission_snapshot = briefing.get("permission_snapshot") or {}
    always_allowed = ", ".join(str(item) for item in (permission_snapshot.get("always_allowed") or [])[:4])
    current_grants = permission_snapshot.get("current_grants") or []
    active_permissions = permission_snapshot.get("active_permission_refs") or []
    agent_ref = permission_snapshot.get("agent_identity_ref") or "none"
    lines.append(
        f"- rights: always=`{always_allowed or 'none'}` grants=`{len(current_grants)}` "
        f"permissions=`{len(active_permissions)}` agent=`{agent_ref}`"
    )
    pressure = payload.get("reason_pressure") or {}
    if pressure:
        reasons = "; ".join(str(item) for item in (pressure.get("reasons") or [])[:2])
        lines.append(
            f"- reason-pressure: {pressure.get('level')} mode=`{pressure.get('recommended_mode')}` "
            f"next=`{pressure.get('recommended_tool')}` {reasons}"
        )

    forced = payload.get("forced_first") or []
    if forced:
        lines.append("- first: " + " -> ".join(str(item) for item in forced))
    else:
        route_steps = [str(item) for item in payload.get("route_steps", [])]
        lines.append("- route: " + " -> ".join(route_steps))
    graph = payload.get("route_graph") or {}
    branches = graph.get("branches") or []
    if branches:
        compact_branches = [
            f"{branch.get('if')}=>{branch.get('then')}"
            for branch in branches[:5]
            if isinstance(branch, dict)
        ]
        lines.append("- graph: " + " | ".join(compact_branches))
    grant = payload.get("grant") or {}
    if grant.get("required"):
        state = "ok" if grant.get("ok") else f"missing ({grant.get('reason')})"
        lines.append(f"- grant: {state}; run `{grant.get('command')}`")
    decomposition = payload.get("task_decomposition") or {}
    if decomposition:
        lines.append(
            f"- task-decomposition: status={decomposition.get('status')} accepted={decomposition.get('accepted')}"
        )

    if detail == "full":
        lines.extend(
            [
                f"- controls: restrictions={payload.get('restriction_count')} guidelines={payload.get('guideline_count')}",
                f"- task text: {concise(payload.get('task', ''), 180) or 'none'}",
                "- briefing-checks: " + " | ".join(str(item) for item in briefing.get("checks", [])),
                "- rights-detail: "
                + " | ".join(
                    [
                        str(permission_snapshot.get("check_at_use") or "runtime authorization is authoritative"),
                        "default-denied="
                        + ", ".join(str(item) for item in (permission_snapshot.get("default_denied") or [])[:3]),
                    ]
                ),
                "- stop: " + " | ".join(str(item) for item in graph.get("stop_conditions", [])),
                f"- note: {payload.get('note')}",
            ]
        )
    else:
        lines.append("- proof: use record_detail/linked_records before citing facts")
    return lines


def next_step_inline(payload: dict) -> str:
    forced = payload.get("forced_first") or []
    if forced:
        route = " -> ".join(str(item) for item in forced)
    else:
        route = " -> ".join(str(item) for item in payload.get("route_steps", [])[:2])
    branches = (payload.get("route_graph") or {}).get("branches") or []
    compact_graph = "; ".join(
        f"{branch.get('if')}=>{branch.get('then')}"
        for branch in branches[:3]
        if isinstance(branch, dict)
    )
    graph_part = f" | graph={compact_graph}" if compact_graph else ""
    pressure = payload.get("reason_pressure") or {}
    pressure_part = (
        f" | reason_pressure={pressure.get('level')}:{pressure.get('recommended_tool')}"
        if pressure
        else ""
    )
    return (
        f"TEP route: intent={payload.get('intent')} | fresh={payload.get('hydration_fresh')} "
        f"| freedom={payload.get('allowed_freedom')} | next={route}{graph_part}{pressure_part}"
    )
