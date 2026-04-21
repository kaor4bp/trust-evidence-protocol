#!/usr/bin/env python3
"""Runtime hydration and preflight gates for the trust-evidence-protocol plugin."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from context_lib import (
    RECORD_DIRS,
    build_index,
    collect_validation_errors,
    compute_context_fingerprint,
    context_write_lock,
    hydration_state_path,
    invalidate_hydration_state,
    is_mutating_action_kind,
    load_effective_settings,
    load_hydration_state,
    now_timestamp,
    resolve_context_root,
    unclassified_input_items,
    write_backlog,
    write_conflicts_report,
    write_flows_report,
    write_hydration_state,
    write_hypotheses_report,
    write_attention_report,
    write_models_report,
    write_resolved_report,
    write_stale_report,
    write_validation_report,
)


FULL_CLI_COMMANDS = {
    "help",
    "tep-help",
    "review-context",
    "reindex-context",
    "brief-context",
    "next-step",
    "search-records",
    "record-detail",
    "scan-conflicts",
    "guidelines-for",
    "linked-records",
}


def raw_runtime_command(argv: list[str]) -> str | None:
    """Return the positional runtime command before argparse emits a long error."""
    index = 1
    while index < len(argv):
        arg = argv[index]
        if arg == "--context":
            index += 2
            continue
        if arg.startswith("--context="):
            index += 1
            continue
        if arg.startswith("-"):
            index += 1
            continue
        return arg
    return None


VALID_HYDRATION_STATUSES = {"hydrated", "hydrated-with-conflicts"}
TEP_ICON = "🛡️"


def active_workspace_summaries_for_guard(records: dict[str, dict]) -> list[dict]:
    return sorted(
        [
            record
            for record in records.values()
            if record.get("record_type") == "workspace" and str(record.get("status", "")).strip() == "active"
        ],
        key=lambda item: str(item.get("id", "")),
    )


def print_unanchored_hydration_block(workspaces: list[dict]) -> None:
    print(
        "Explicit TEP workspace anchor required: refusing to hydrate from an unanchored cwd "
        "while active workspaces exist."
    )
    print("Run hydrate-context from the intended workdir with a .tep anchor that declares workspace_ref.")
    if workspaces:
        print("Active workspaces:")
        for workspace in workspaces[:8]:
            print(f"- {workspace.get('id')} | {workspace.get('workspace_key', '')}")


def print_errors(errors) -> None:
    for error in errors:
        print(f"{error.path}: {error.message}")


def refresh_generated_outputs(root: Path, records: dict[str, dict]) -> list[str]:
    write_stale_report(root, records)
    conflict_lines = write_conflicts_report(root, records)
    write_models_report(root, records)
    write_flows_report(root, records)
    write_hypotheses_report(root, records)
    write_resolved_report(root, records)
    write_attention_report(root, records)
    build_index(root, records)
    write_backlog(root, records)
    return conflict_lines


def summarize_counts(records: dict[str, dict]) -> dict[str, int]:
    counts = {record_type: 0 for record_type in RECORD_DIRS}
    for data in records.values():
        record_type = str(data.get("record_type", "")).strip()
        if record_type in counts:
            counts[record_type] += 1
    return counts


def current_task_summary(root: Path, records: dict[str, dict]) -> dict | None:
    current_task_ref = str(load_effective_settings(root).get("current_task_ref") or "").strip()
    if not current_task_ref:
        return None
    task = records.get(current_task_ref)
    if not task or task.get("record_type") != "task":
        return {"id": current_task_ref, "status": "missing", "title": "", "scope": ""}
    return {
        "id": current_task_ref,
        "status": str(task.get("status", "")).strip(),
        "scope": str(task.get("scope", "")).strip(),
        "task_type": str(task.get("task_type", "general")).strip() or "general",
        "title": str(task.get("title", "")).strip(),
    }


def current_project_summary(root: Path, records: dict[str, dict]) -> dict | None:
    current_project_ref = str(load_effective_settings(root).get("current_project_ref") or "").strip()
    if not current_project_ref:
        return None
    project = records.get(current_project_ref)
    if not project or project.get("record_type") != "project":
        return {"id": current_project_ref, "status": "missing", "project_key": "", "title": ""}
    return {
        "id": current_project_ref,
        "status": str(project.get("status", "")).strip(),
        "project_key": str(project.get("project_key", "")).strip(),
        "title": str(project.get("title", "")).strip(),
    }


def current_workspace_summary(root: Path, records: dict[str, dict]) -> dict | None:
    current_workspace_ref = str(load_effective_settings(root).get("current_workspace_ref") or "").strip()
    if not current_workspace_ref:
        return None
    workspace = records.get(current_workspace_ref)
    if not workspace or workspace.get("record_type") != "workspace":
        return {"id": current_workspace_ref, "status": "missing", "workspace_key": "", "title": ""}
    return {
        "id": current_workspace_ref,
        "status": str(workspace.get("status", "")).strip(),
        "workspace_key": str(workspace.get("workspace_key", "")).strip(),
        "title": str(workspace.get("title", "")).strip(),
    }


def active_restriction_summaries(records: dict[str, dict], project_ref: str | None, task_ref: str | None) -> list[dict]:
    restrictions: list[dict] = []
    for restriction in records.values():
        if restriction.get("record_type") != "restriction":
            continue
        if str(restriction.get("status", "")).strip() != "active":
            continue
        applies_to = str(restriction.get("applies_to", "")).strip()
        if applies_to == "global":
            matched = True
        elif applies_to == "project":
            matched = bool(project_ref and project_ref in restriction.get("project_refs", []))
        elif applies_to == "task":
            matched = bool(task_ref and task_ref in restriction.get("task_refs", []))
        else:
            matched = False
        if matched:
            restrictions.append(
                {
                    "id": str(restriction.get("id", "")).strip(),
                    "applies_to": applies_to,
                    "severity": str(restriction.get("severity", "")).strip(),
                    "title": str(restriction.get("title", "")).strip(),
                }
            )
    return sorted(restrictions, key=lambda item: (item["severity"], item["id"]))


def active_guideline_summaries(records: dict[str, dict], project_ref: str | None, task_ref: str | None) -> list[dict]:
    guidelines: list[dict] = []
    for guideline in records.values():
        if guideline.get("record_type") != "guideline":
            continue
        if str(guideline.get("status", "")).strip() != "active":
            continue
        applies_to = str(guideline.get("applies_to", "")).strip()
        if applies_to == "global":
            matched = True
        elif applies_to == "project":
            matched = bool(project_ref and project_ref in guideline.get("project_refs", []))
        elif applies_to == "task":
            matched = bool(task_ref and task_ref in guideline.get("task_refs", []))
        else:
            matched = False
        if matched:
            guidelines.append(
                {
                    "id": str(guideline.get("id", "")).strip(),
                    "domain": str(guideline.get("domain", "")).strip(),
                    "applies_to": applies_to,
                    "priority": str(guideline.get("priority", "")).strip(),
                    "rule": str(guideline.get("rule", "")).strip(),
                }
            )
    priority_order = {"required": 0, "preferred": 1, "optional": 2}
    return sorted(guidelines, key=lambda item: (priority_order.get(item["priority"], 9), item["id"]))


def render_current_task(task: dict) -> str:
    title = str(task.get("title", "")).strip()
    title_suffix = f" | {title}" if title else ""
    return (
        f"Current task: {task.get('id')} | status={task.get('status', '')} "
        f"| type={task.get('task_type', 'general')} | scope={task.get('scope', '')}{title_suffix}"
    )


def render_current_project(project: dict) -> str:
    title = str(project.get("title", "")).strip()
    title_suffix = f" | {title}" if title else ""
    return (
        f"Current project: {project.get('id')} | status={project.get('status', '')} "
        f"| key={project.get('project_key', '')}{title_suffix}"
    )


def render_current_workspace(workspace: dict) -> str:
    title = str(workspace.get("title", "")).strip()
    title_suffix = f" | {title}" if title else ""
    return (
        f"Current workspace: {workspace.get('id')} | status={workspace.get('status', '')} "
        f"| key={workspace.get('workspace_key', '')}{title_suffix}"
    )


def cmd_hydrate_context(root: Path, *, allow_unanchored: bool = False) -> int:
    records, errors = collect_validation_errors(root)
    settings = load_effective_settings(root)
    active_workspaces = active_workspace_summaries_for_guard(records)
    if active_workspaces and (
        not str(settings.get("anchor_path") or "").strip()
        or not str(settings.get("current_workspace_ref") or "").strip()
    ):
        print_unanchored_hydration_block(active_workspaces)
        return 1

    write_validation_report(root, errors)
    conflict_lines = refresh_generated_outputs(root, records)

    fingerprint = compute_context_fingerprint(root)
    current_task = current_task_summary(root, records)
    current_workspace = current_workspace_summary(root, records)
    current_project = current_project_summary(root, records)
    restrictions = active_restriction_summaries(
        records,
        current_project["id"] if current_project else None,
        current_task["id"] if current_task else None,
    )
    guidelines = active_guideline_summaries(
        records,
        current_project["id"] if current_project else None,
        current_task["id"] if current_task else None,
    )
    state = {
        "status": "blocked" if errors else ("hydrated-with-conflicts" if conflict_lines else "hydrated"),
        "hydrated_at": now_timestamp(),
        "fingerprint": fingerprint,
        "allowed_freedom": settings.get("allowed_freedom", "proof-only"),
        "anchor_path": settings.get("anchor_path", ""),
        "current_workspace": current_workspace,
        "current_project": current_project,
        "current_task": current_task,
        "active_restrictions": restrictions,
        "active_guidelines": guidelines,
        "record_counts": summarize_counts(records),
        "conflict_count": len(conflict_lines),
        "error_count": len(errors),
    }
    write_hydration_state(root, state)

    if errors:
        print_errors(errors)
        print(f"{hydration_state_path(root)}: hydration blocked by validation errors")
        return 1
    if current_workspace:
        print(render_current_workspace(current_workspace))
    if current_project:
        print(render_current_project(current_project))
    if current_task:
        print(render_current_task(current_task))
    if restrictions:
        print(f"Active restrictions: {len(restrictions)} ({', '.join(item['id'] for item in restrictions)})")
    if guidelines:
        print(f"Active guidelines: {len(guidelines)} ({', '.join(item['id'] for item in guidelines)})")
    if conflict_lines:
        print(f"{hydration_state_path(root)}: hydrated with {len(conflict_lines)} conflict issue(s)")
        return 0
    print(f"{TEP_ICON} Hydrated context: {root}")
    return 0


def cmd_show_hydration(root: Path) -> int:
    state = load_hydration_state(root)
    current_fingerprint = compute_context_fingerprint(root)
    stored_fingerprint = str(state.get("fingerprint", ""))
    settings = load_effective_settings(root)
    mismatches: list[tuple[str, str, str]] = []
    for key, settings_key in (
        ("current_workspace", "current_workspace_ref"),
        ("current_project", "current_project_ref"),
        ("current_task", "current_task_ref"),
    ):
        snapshot = state.get(key)
        snapshot_ref = str(snapshot.get("id", "")).strip() if isinstance(snapshot, dict) else ""
        effective_ref = str(settings.get(settings_key) or "").strip()
        if snapshot_ref != effective_ref:
            mismatches.append((key, snapshot_ref or "none", effective_ref or "none"))
    is_current = (
        stored_fingerprint == current_fingerprint
        and state.get("status") in VALID_HYDRATION_STATUSES
        and not mismatches
    )

    print(f"hydration_status={state.get('status', 'unhydrated')}")
    print(f"hydrated_at={state.get('hydrated_at', '')}")
    print(f"allowed_freedom={settings.get('allowed_freedom', 'proof-only')}")
    if settings.get("allowed_freedom_source"):
        print(f"allowed_freedom_source={settings.get('allowed_freedom_source')}")
    if settings.get("anchor_path"):
        print(f"anchor_path={settings.get('anchor_path')}")
    current_workspace = state.get("current_workspace")
    if isinstance(current_workspace, dict) and current_workspace.get("id"):
        print(
            "current_workspace="
            f"{current_workspace.get('id')} status={current_workspace.get('status', '')} "
            f"key={current_workspace.get('workspace_key', '')} title={current_workspace.get('title', '')}"
        )
    current_project = state.get("current_project")
    if isinstance(current_project, dict) and current_project.get("id"):
        print(
            "current_project="
            f"{current_project.get('id')} status={current_project.get('status', '')} "
            f"key={current_project.get('project_key', '')} title={current_project.get('title', '')}"
        )
    current_task = state.get("current_task")
    if isinstance(current_task, dict) and current_task.get("id"):
        print(
            "current_task="
            f"{current_task.get('id')} status={current_task.get('status', '')} "
            f"type={current_task.get('task_type', 'general')} scope={current_task.get('scope', '')} "
            f"title={current_task.get('title', '')}"
        )
    active_restrictions = state.get("active_restrictions")
    if isinstance(active_restrictions, list):
        print(f"active_restrictions={len(active_restrictions)}")
    active_guidelines = state.get("active_guidelines")
    if isinstance(active_guidelines, list):
        print(f"active_guidelines={len(active_guidelines)}")
    print(f"state_file={hydration_state_path(root)}")
    print(f"fingerprint_current={is_current}")
    if mismatches:
        print("snapshot_mismatch=" + ",".join(key for key, _, _ in mismatches))
        for key, snapshot_ref, effective_ref in mismatches:
            print(f"snapshot_{key}={snapshot_ref}")
            print(f"effective_{key}={effective_ref}")
        print("action=run hydrate-context")
    if state.get("conflict_count") is not None:
        print(f"conflict_count={state.get('conflict_count')}")
    if state.get("error_count") is not None:
        print(f"error_count={state.get('error_count')}")
    return 0 if is_current else 1


def cmd_preflight_task(root: Path, mode: str, kind: str | None) -> int:
    state = load_hydration_state(root)
    current_fingerprint = compute_context_fingerprint(root)
    stored_fingerprint = str(state.get("fingerprint", ""))
    status = str(state.get("status", "unhydrated")).strip()

    if status not in VALID_HYDRATION_STATUSES or stored_fingerprint != current_fingerprint:
        print(
            f"Hydration required before {mode}. Run: "
            f"python3 plugins/trust-evidence-protocol/scripts/runtime_gate.py --context {root} hydrate-context"
        )
        return 1

    strictness = load_effective_settings(root).get("allowed_freedom", "proof-only")
    active_restrictions = state.get("active_restrictions", [])
    current_task = state.get("current_task")

    if mode in {"planning", "edit", "action", "final"}:
        confirmed_task = state.get("confirmed_task")
        current_task_id = (
            str(current_task.get("id", "")).strip()
            if isinstance(current_task, dict)
            else ""
        )
        confirmed_task_id = (
            str(confirmed_task.get("id", "")).strip()
            if isinstance(confirmed_task, dict)
            else ""
        )
        confirmed_fingerprint = (
            str(confirmed_task.get("fingerprint", "")).strip()
            if isinstance(confirmed_task, dict)
            else ""
        )
        if current_task_id and (
            confirmed_task_id != current_task_id
            or confirmed_fingerprint != current_fingerprint
        ):
            print(
                "Current TASK-* is not confirmed for this hydrated context. "
                "Ask the user whether this is the intended task, then run:"
            )
            print(
                f"python3 plugins/trust-evidence-protocol/scripts/runtime_gate.py "
                f"--context {root} confirm-task --task {current_task_id}"
            )
            print(render_current_task(current_task))
            return 1

    if mode == "final":
        records, errors = collect_validation_errors(root)
        if errors:
            print_errors(errors)
            return 1
        unresolved_inputs = unclassified_input_items(records)
        if unresolved_inputs:
            print(
                "Final response blocked: unresolved INP-* provenance requires at least one "
                "derived_record_refs or incoming input_refs link."
            )
            print("Classify inputs with: context_cli.py classify-input --input INP-* --derived-record REF")
            for item in unresolved_inputs[:12]:
                print(f"- {item['id']}: {item['summary']}")
            if len(unresolved_inputs) > 12:
                print(f"... {len(unresolved_inputs) - 12} more unresolved INP-*")
            return 1

    if status == "hydrated-with-conflicts" and mode == "planning":
        print("Planning is blocked while hydrated conflicts remain unresolved. Review review/conflicts.md first.")
        return 1

    action_kind = ""
    if mode == "edit":
        action_kind = "edit"
    if mode == "action":
        action_kind = (kind or "").strip()
        if not action_kind:
            print("preflight-task --mode action requires --kind")
            return 1

    if action_kind and is_mutating_action_kind(action_kind) and strictness == "proof-only":
        print(f"Mutating action kind {action_kind!r} requires implementation-choice strictness")
        return 1
    if action_kind and is_mutating_action_kind(action_kind) and strictness == "evidence-authorized":
        if not isinstance(current_task, dict) or not current_task.get("id"):
            print("Mutating action in evidence-authorized mode requires an active TASK-*")
            return 1
        hard_restrictions = [
            item
            for item in active_restrictions
            if isinstance(item, dict) and str(item.get("severity", "")).strip() == "hard"
        ]
        if hard_restrictions:
            print(
                "Mutating action in evidence-authorized mode is blocked by hard restriction(s): "
                + ", ".join(str(item.get("id", "")) for item in hard_restrictions)
            )
            return 1
        print("Evidence-authorized preflight passed; record-action still requires --evidence-chain.")

    if status == "hydrated-with-conflicts":
        print(f"Preflight passed with conflicts present for {mode}; proceed only with conflict-aware reasoning.")
        if active_restrictions:
            print(f"Active restrictions present: {', '.join(str(item.get('id', '')) for item in active_restrictions if isinstance(item, dict))}")
        return 0

    print(f"Preflight passed for {mode}")
    if active_restrictions:
        print(f"Active restrictions present: {', '.join(str(item.get('id', '')) for item in active_restrictions if isinstance(item, dict))}")
    return 0


def cmd_confirm_task(root: Path, task_ref: str, note: str | None) -> int:
    state = load_hydration_state(root)
    current_fingerprint = compute_context_fingerprint(root)
    stored_fingerprint = str(state.get("fingerprint", ""))
    status = str(state.get("status", "unhydrated")).strip()
    if status not in VALID_HYDRATION_STATUSES or stored_fingerprint != current_fingerprint:
        print("Hydrate the context before confirming the current TASK-*.")
        return 1
    current_task = state.get("current_task")
    if not isinstance(current_task, dict) or not current_task.get("id"):
        print("No current TASK-* is active in hydration state.")
        return 1
    current_task_id = str(current_task.get("id", "")).strip()
    if task_ref != current_task_id:
        print(f"Cannot confirm {task_ref}: current hydrated task is {current_task_id}")
        return 1
    state = dict(state)
    state["confirmed_task"] = {
        "id": current_task_id,
        "fingerprint": current_fingerprint,
        "confirmed_at": now_timestamp(),
        "note": (note or "").strip(),
    }
    write_hydration_state(root, state)
    print(f"Confirmed current task {current_task_id}")
    print(render_current_task(current_task))
    return 0


def cmd_invalidate_hydration(root: Path, reason: str) -> int:
    invalidate_hydration_state(root, reason=reason)
    print(f"{hydration_state_path(root)}: marked stale ({reason})")
    return 0


def parse_args() -> argparse.Namespace:
    command = raw_runtime_command(sys.argv)
    if command in FULL_CLI_COMMANDS:
        print(
            "runtime_gate.py only handles hook gates: "
            "hydrate-context, show-hydration, preflight-task, confirm-task, invalidate-hydration.\n"
            f"For `{command}`, use scripts/context_cli.py --context <context> {command}",
            file=sys.stderr,
        )
        raise SystemExit(2)
    parser = argparse.ArgumentParser(description="Hydration and runtime preflight gates.")
    parser.add_argument(
        "--context",
        default=None,
        help="Path to TEP context root. Defaults to TEP_CONTEXT_ROOT, ~/.tep_context, or legacy ./.codex_context.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    hydrate = subparsers.add_parser("hydrate-context", help="Validate and mark the context as hydrated.")
    hydrate.add_argument(
        "--allow-unanchored",
        action="store_true",
        help="Deprecated compatibility flag. Active workspaces still require a .tep workspace anchor.",
    )
    subparsers.add_parser("show-hydration", help="Show hydration status and currentness.")

    preflight = subparsers.add_parser(
        "preflight-task",
        help="Check whether the current context is hydrated and compatible with the task mode.",
    )
    preflight.add_argument("--mode", required=True, choices=["reasoning", "planning", "edit", "action", "final"])
    preflight.add_argument("--kind")

    confirm_task = subparsers.add_parser(
        "confirm-task",
        help="Confirm that the hydrated current TASK-* is the intended work focus.",
    )
    confirm_task.add_argument("--task", dest="task_ref", required=True)
    confirm_task.add_argument("--note")

    invalidate = subparsers.add_parser(
        "invalidate-hydration",
        help="Mark hydration state stale after an external mutation.",
    )
    invalidate.add_argument("--reason", required=True)

    return parser.parse_args()


def main() -> None:
    args = parse_args()
    root = resolve_context_root(args.context, start=Path.cwd())
    if root is None:
        print("Could not resolve TEP context root")
        raise SystemExit(1)
    if args.command == "hydrate-context":
        try:
            with context_write_lock(root):
                raise SystemExit(cmd_hydrate_context(root, allow_unanchored=args.allow_unanchored))
        except TimeoutError as exc:
            print(exc)
            raise SystemExit(1)
    if args.command == "show-hydration":
        raise SystemExit(cmd_show_hydration(root))
    if args.command == "preflight-task":
        raise SystemExit(cmd_preflight_task(root, mode=args.mode, kind=args.kind))
    if args.command == "confirm-task":
        try:
            with context_write_lock(root):
                raise SystemExit(cmd_confirm_task(root, task_ref=args.task_ref, note=args.note))
        except TimeoutError as exc:
            print(exc)
            raise SystemExit(1)
    if args.command == "invalidate-hydration":
        try:
            with context_write_lock(root):
                raise SystemExit(cmd_invalidate_hydration(root, reason=args.reason))
        except TimeoutError as exc:
            print(exc)
            raise SystemExit(1)
    raise SystemExit(2)


if __name__ == "__main__":
    main()
