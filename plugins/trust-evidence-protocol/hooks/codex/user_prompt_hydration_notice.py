#!/usr/bin/env python3
"""Codex hook that reminds Codex when TEP context hydration is stale."""

from __future__ import annotations

import json

from hook_common import (
    TEP_ICON,
    hook_mode,
    hook_verbosity,
    hooks_enabled,
    load_payload,
    load_settings,
    locate_context,
    run_context_cli,
    run_runtime_gate,
)


PROTOCOL_REMINDER = (
    "Use the Trust Evidence Protocol skill. Search the resolved TEP context first via MCP/brief-context, then show "
    "compact public Evidence Chain or Reasoning Checkpoint panels when planning, asking permission, persisting, "
    "or editing. For green/red/ask decisions, target assertions and user pressure are not proof; unanchored "
    "targets require `ask` when available or `red` when not. For substantial code edits, cite applicable "
    "`GLD-* + quote` before edits and `Guidelines used:` after."
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


def capture_user_prompt(context_root, payload: dict) -> bool:
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
        "codex.user_prompt",
        "--input-kind",
        "user_prompt",
        "--origin-kind",
        "codex-hook",
        "--origin-ref",
        origin_ref,
        "--text-stdin",
        "--tag",
        "hook",
        "--tag",
        "user-prompt",
        "--note",
        "Captured user prompt from Codex UserPromptSubmit hook.",
    ]
    if session_ref:
        args.extend(["--session-ref", session_ref])
    result = run_context_cli(*args, input_text=captured_text)
    if result.returncode != 0:
        return False
    hydrate = run_runtime_gate("--context", str(context_root), "hydrate-context")
    return hydrate.returncode == 0


def main() -> int:
    payload = load_payload()
    context_root = locate_context(payload.get("cwd"))
    if context_root is None:
        return 0
    if not hooks_enabled(context_root):
        return 0
    mode = hook_mode(context_root, "user_prompt_notice")
    if mode == "off":
        return 0
    capture_user_prompt(context_root, payload)

    result = run_runtime_gate("--context", str(context_root), "show-hydration")
    if result.returncode == 0:
        if mode == "remind" and hook_verbosity(context_root) != "quiet":
            emit(
                additional_context=PROTOCOL_REMINDER,
                system_message="Trust Evidence Protocol reminder.",
            )
        return 0

    emit(
        additional_context=(
            "Project context is stale or unhydrated. Before relying on persistent "
            "project facts, planning, or edits, refresh the resolved TEP context with "
            "trust-evidence-protocol runtime_gate.py hydrate-context."
        ),
        system_message="Context hydration is stale.",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
