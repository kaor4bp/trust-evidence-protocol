#!/usr/bin/env python3
"""Codex hook that hydrates the resolved TEP context on session start."""

from __future__ import annotations

import json

from hook_common import (
    TEP_ICON,
    anchored_hydration_preserved_message,
    hook_mode,
    hook_verbosity,
    hooks_enabled,
    load_payload,
    locate_context,
    next_step_hint,
    run_runtime_gate,
    should_defer_unanchored_hydration,
    should_preserve_anchored_hydration,
    unanchored_hydration_deferred_message,
)


PROTOCOL_REMINDER = (
    "Use TEP skill: search resolved context first, cite `CLM-*`/`GLD-* + quote` for planning, permission, "
    "persistence, and substantial edits, and never derive green/red/ask values from target assertions."
)


def emit(additional_context: str | None = None, system_message: str | None = None) -> None:
    payload: dict[str, object] = {}
    if system_message:
        payload["systemMessage"] = f"{TEP_ICON} {system_message}"
    if additional_context:
        payload["hookSpecificOutput"] = {
            "hookEventName": "SessionStart",
            "additionalContext": additional_context,
        }
    if payload:
        print(json.dumps(payload))


def current_task_context(stdout: str) -> str | None:
    for line in stdout.splitlines():
        if line.startswith("Current task:"):
            return (
                "Project context has an active current task. "
                f"{line}. Treat this as the execution focus until `complete-task` or `stop-task` clears it."
            )
    return None


def hydration_summary(stdout: str) -> str:
    lines = []
    for line in stdout.splitlines():
        if line.startswith(
            (
                "Current project:",
                "Current workspace:",
                "Current task:",
                "Active restrictions:",
                "Active guidelines:",
            )
        ):
            lines.append(line)
    if not lines:
        lines.append("Project context hydrated. No current task/project/workspace summary was emitted.")
    lines.append(PROTOCOL_REMINDER)
    return "\n".join(lines)


def compact_hydration_summary(stdout: str) -> str:
    lines = [
        line
        for line in stdout.splitlines()
        if line.startswith(("Current workspace:", "Current project:", "Current task:", "Active restrictions:", "Active guidelines:"))
    ]
    if not lines:
        lines.append("Project context hydrated.")
    return "\n".join(lines)


def main() -> int:
    payload = load_payload()
    cwd = payload.get("cwd")
    context_root = locate_context(cwd)
    if context_root is None:
        return 0
    if not hooks_enabled(context_root):
        return 0
    if hook_mode(context_root, "session_start_hydrate") == "off":
        return 0
    if should_preserve_anchored_hydration(context_root, cwd):
        emit(
            additional_context=anchored_hydration_preserved_message(context_root),
            system_message="Anchored context preserved.",
        )
        return 0
    if should_defer_unanchored_hydration(context_root, cwd):
        emit(
            additional_context=unanchored_hydration_deferred_message(context_root),
            system_message="Explicit TEP anchor required.",
        )
        return 0

    result = run_runtime_gate("--context", str(context_root), "hydrate-context", cwd=cwd)
    stdout = result.stdout.strip()
    stderr = result.stderr.strip()

    if result.returncode == 0:
        additional_parts: list[str] = []
        quiet = hook_verbosity(context_root) == "quiet"
        task_context = current_task_context(stdout)
        if task_context and not quiet:
            additional_parts.append(task_context)
        additional_parts.append(compact_hydration_summary(stdout) if quiet else hydration_summary(stdout))
        additional_parts.append(next_step_hint(context_root, intent="auto"))
        if "hydrated with" in stdout.lower():
            additional_parts.append(
                (
                    "Project context hydrated with unresolved conflicts. Review "
                    "<context>/review/conflicts.md before planning or edits."
                )
            )
        if additional_parts:
            emit(
                additional_context="\n".join(additional_parts),
                system_message="Context hydrated with conflicts."
                if "hydrated with" in stdout.lower()
                else "Context hydrated."
                if quiet
                else "Context hydrated with current task.",
            )
        return 0

    detail = stderr or stdout or "Hydration blocked."
    emit(
        additional_context=(
            "Project context hydration failed. Review <context>/review/broken.md "
            "before relying on persistent project facts."
        ),
        system_message=detail.splitlines()[0],
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
