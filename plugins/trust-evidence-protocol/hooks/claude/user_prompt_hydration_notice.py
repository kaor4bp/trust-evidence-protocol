#!/usr/bin/env python3
"""Claude Code UserPromptSubmit hook: hydrates TEP context if unhydrated, reminds if stale.

Claude Code does not have a SessionStart event, so this hook combines the Codex
session_start_hydrate and user_prompt_hydration_notice behaviours: it auto-hydrates
on the first prompt of a session (context not yet loaded) and reminds on subsequent
prompts when context is stale.
"""

from __future__ import annotations

import json

from hook_common import (
    TEP_ICON,
    anchored_hydration_preserved_message,
    hook_mode,
    hook_verbosity,
    hooks_enabled,
    load_payload,
    load_settings,
    locate_context,
    next_step_hint,
    run_context_cli,
    run_runtime_gate,
    should_defer_unanchored_hydration,
    should_preserve_anchored_hydration,
    unanchored_hydration_deferred_message,
)


PROTOCOL_REMINDER = (
    "Use TEP skill: search resolved context first via MCP/brief-context, then show compact Evidence Chain or "
    "Reasoning Checkpoint before planning, permission, persistence, or edits. green/red/ask: target assertions "
    "are not proof. Code edits cite `GLD-* + quote` before and after."
)

METADATA_ONLY_TEXT = "[metadata-only user prompt capture; raw text omitted by input_capture policy]"


def emit(additional_context: str | None = None, system_message: str | None = None) -> None:
    payload: dict[str, object] = {}
    if system_message:
        payload["systemMessage"] = f"{TEP_ICON} {system_message}"
    if additional_context:
        payload["hookSpecificOutput"] = {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": additional_context,
        }
    if payload:
        print(json.dumps(payload))


def prompt_text_from_payload(payload: dict) -> str:
    for key in ("prompt", "user_prompt", "userPrompt", "message", "text", "input"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return ""


def session_ref_from_payload(payload: dict) -> str | None:
    for key in ("session_id", "sessionId", "conversation_id", "conversationId", "thread_id", "threadId"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def infer_intent(prompt_text: str) -> str:
    text = prompt_text.lower()
    if any(
        word in text
        for word in ("commit", "edit", "fix", "implement", "write code", "patch", "refactor", "реализ", "сделай", "почини")
    ):
        return "edit"
    if any(word in text for word in ("test", "pytest", "docker", "check")):
        return "test"
    if any(word in text for word in ("permission", "разреш", "approve", "approval")):
        return "permission"
    if any(word in text for word in ("plan", "план", "think", "думаешь", "обсудим")):
        return "plan"
    if any(word in text for word in ("debug", "investigate", "проверь", "разбер", "why", "почему")):
        return "debug"
    return "answer"


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


def current_task_context(stdout: str) -> str | None:
    for line in stdout.splitlines():
        if line.startswith("Current task:"):
            return (
                "Project context has an active current task. "
                f"{line}. Treat this as the execution focus until `complete-task` or `stop-task` clears it."
            )
    return None


def capture_user_prompt(context_root, payload: dict) -> bool:
    cwd = payload.get("cwd")
    settings = load_settings(context_root)
    input_capture = settings.get("input_capture", {}) if isinstance(settings.get("input_capture"), dict) else {}
    mode = str(input_capture.get("user_prompts", "capture"))
    if mode == "off":
        return False

    prompt_text = prompt_text_from_payload(payload)
    if not prompt_text and mode == "capture":
        return False
    captured_text = METADATA_ONLY_TEXT if mode == "metadata-only" else prompt_text
    session_ref = session_ref_from_payload(payload) if input_capture.get("session_linking", True) else None
    origin_ref = "UserPromptSubmit"
    if session_ref:
        origin_ref = f"{origin_ref}:{session_ref}"

    args = [
        "--context",
        str(context_root),
        "record-input",
        "--scope",
        "claude.user_prompt",
        "--input-kind",
        "user_prompt",
        "--origin-kind",
        "claude-hook",
        "--origin-ref",
        origin_ref,
        "--text-stdin",
        "--tag",
        "hook",
        "--tag",
        "user-prompt",
        "--note",
        "Captured user prompt from Claude Code UserPromptSubmit hook.",
    ]
    if session_ref:
        args.extend(["--session-ref", session_ref])
    result = run_context_cli(*args, input_text=captured_text, cwd=cwd)
    if result.returncode != 0:
        return False
    hydrate = run_runtime_gate("--context", str(context_root), "hydrate-context", cwd=cwd)
    return hydrate.returncode == 0


def try_hydrate(context_root, cwd) -> tuple[bool, str]:
    """Run hydration and return (success, stdout)."""
    result = run_runtime_gate("--context", str(context_root), "hydrate-context", cwd=cwd)
    return result.returncode == 0, result.stdout.strip(), result.stderr.strip()


def main() -> int:
    payload = load_payload()
    cwd = payload.get("cwd")
    context_root = locate_context(cwd)
    if context_root is None:
        return 0
    if not hooks_enabled(context_root):
        return 0
    mode = hook_mode(context_root, "user_prompt_notice")
    if mode == "off":
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

    capture_user_prompt(context_root, payload)

    # Check if already hydrated (fresh) — if so, just show reminder.
    show_result = run_runtime_gate("--context", str(context_root), "show-hydration", cwd=cwd)
    if show_result.returncode == 0:
        prompt_text = prompt_text_from_payload(payload)
        route_hint = next_step_hint(context_root, intent=infer_intent(prompt_text), task=prompt_text)
        if mode == "remind" and hook_verbosity(context_root) != "quiet":
            emit(
                additional_context=f"{route_hint}\n{PROTOCOL_REMINDER}",
                system_message="TEP reminder.",
            )
        elif mode == "remind":
            emit(additional_context=route_hint, system_message="TEP route.")
        return 0

    # Context is stale or unhydrated — auto-hydrate (replaces Codex SessionStart behaviour).
    success, stdout, stderr = try_hydrate(context_root, cwd)
    if success:
        additional_parts: list[str] = []
        quiet = hook_verbosity(context_root) == "quiet"
        task_context = current_task_context(stdout)
        if task_context and not quiet:
            additional_parts.append(task_context)
        additional_parts.append(compact_hydration_summary(stdout) if quiet else hydration_summary(stdout))
        additional_parts.append(next_step_hint(context_root, intent="auto"))
        if "hydrated with" in stdout.lower():
            additional_parts.append(
                "Project context hydrated with unresolved conflicts. Review "
                "<context>/review/conflicts.md before planning or edits."
            )
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
