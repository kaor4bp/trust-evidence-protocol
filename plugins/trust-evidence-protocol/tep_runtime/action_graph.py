"""Token-light next-step routing for TEP agents."""

from __future__ import annotations

from pathlib import Path

from .hydration import compute_context_fingerprint, load_hydration_state
from .retrieval import active_guidelines_for
from .scopes import active_restrictions_for, current_project_ref, current_task_ref, current_workspace_ref
from .search import concise
from .settings import load_effective_settings


NEXT_STEP_INTENTS = {"auto", "answer", "plan", "edit", "test", "persist", "permission", "debug", "after-mutation"}
VALID_HYDRATION_STATUSES = {"hydrated", "hydrated-with-conflicts"}


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
    routes = {
        "answer": ("answering", [f"brief-context{task_arg}", "record-detail / linked-records before citing proof"]),
        "plan": ("planning", [f"brief-context{task_arg}", "publish Reasoning Checkpoint", "validate-planning-chain if chain is explicit"]),
        "edit": ("editing", [f"guidelines-for{task_arg}", "build/validate evidence chain", "preflight-task --mode edit"]),
        "test": ("testing", [f"brief-context{task_arg}", "record-source for meaningful test output", "hydrate-context after mutation"]),
        "persist": ("persisting", ["classify input/source first", "record-* through context_cli", "hydrate-context"]),
        "permission": ("permission", ["build-reasoning-case", "cite CLM/GLD/PRM ids + quotes", "request explicit approval if needed"]),
        "debug": ("debugging", ["show-hydration", "review-context", "scan-conflicts / reindex-context if needed"]),
        "after-mutation": ("after mutation", ["hydrate-context", "record-source/claim/action if meaningful", "show-hydration"]),
    }
    return routes.get(intent, ("general", [f"brief-context{task_arg}", "choose answer|plan|edit|test|persist|permission|debug route"]))


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
    if active_restrictions and intent in {"edit", "test", "persist", "permission"}:
        forced.append("show-restrictions")
    if intent == "edit" and not active_guidelines:
        forced.append("guidelines-for")

    route_label, route_steps = _intent_route(intent, task)
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
        "forced_first": forced,
        "route_steps": route_steps,
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

    forced = payload.get("forced_first") or []
    if forced:
        lines.append("- first: " + " -> ".join(str(item) for item in forced))
    else:
        route_steps = [str(item) for item in payload.get("route_steps", [])]
        lines.append("- route: " + " -> ".join(route_steps))

    if detail == "full":
        lines.extend(
            [
                f"- controls: restrictions={payload.get('restriction_count')} guidelines={payload.get('guideline_count')}",
                f"- task text: {concise(payload.get('task', ''), 180) or 'none'}",
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
    return (
        f"TEP route: intent={payload.get('intent')} | fresh={payload.get('hydration_fresh')} "
        f"| freedom={payload.get('allowed_freedom')} | next={route}"
    )
