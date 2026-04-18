#!/usr/bin/env python3
"""Codex hook that hydrates the resolved TEP context on session start."""

from __future__ import annotations

import json

from hook_common import TEP_ICON, hook_mode, hook_verbosity, hooks_enabled, load_payload, locate_context, run_runtime_gate


PROTOCOL_REMINDER = (
    "Use the Trust Evidence Protocol skill: search the resolved TEP context first, cite `CLM-*`/`GLD-*` ids with "
    "short quotes for planning, permission, persistence, and substantial edits, keep detailed lookup in MCP/brief-context, "
    "and never make green/red/ask decisions by deriving unknown values from target assertions or user pressure."
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
                "Current task:",
                "Active restrictions:",
                "Active guidelines:",
            )
        ):
            lines.append(line)
    if not lines:
        lines.append("Project context hydrated. No current task/project summary was emitted.")
    lines.append(PROTOCOL_REMINDER)
    return "\n".join(lines)


def compact_hydration_summary(stdout: str) -> str:
    lines = [
        line
        for line in stdout.splitlines()
        if line.startswith(("Current project:", "Current task:", "Active restrictions:", "Active guidelines:"))
    ]
    if not lines:
        lines.append("Project context hydrated.")
    return "\n".join(lines)


def main() -> int:
    payload = load_payload()
    context_root = locate_context(payload.get("cwd"))
    if context_root is None:
        return 0
    if not hooks_enabled(context_root):
        return 0
    if hook_mode(context_root, "session_start_hydrate") == "off":
        return 0

    result = run_runtime_gate("--context", str(context_root), "hydrate-context")
    stdout = result.stdout.strip()
    stderr = result.stderr.strip()

    if result.returncode == 0:
        additional_parts: list[str] = []
        quiet = hook_verbosity(context_root) == "quiet"
        task_context = current_task_context(stdout)
        if task_context and not quiet:
            additional_parts.append(task_context)
        additional_parts.append(compact_hydration_summary(stdout) if quiet else hydration_summary(stdout))
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
