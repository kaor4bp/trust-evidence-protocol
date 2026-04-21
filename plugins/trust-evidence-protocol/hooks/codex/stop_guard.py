#!/usr/bin/env python3
"""Codex Stop hook: keep autonomous TASK-* work from ending without an outcome."""

from __future__ import annotations

import json

from hook_common import TEP_ICON, hook_mode, hooks_enabled, load_payload, locate_context, run_runtime_gate


def last_assistant_message(payload: dict) -> str:
    for key in (
        "last_assistant_message",
        "assistant_message",
        "last_response",
        "response",
        "message",
        "text",
        "transcript",
    ):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return ""


def stop_hook_active(payload: dict) -> bool:
    return bool(payload.get("stop_hook_active") or payload.get("stopHookActive"))


def emit_block(reason: str) -> None:
    print(
        json.dumps(
            {
                "decision": "block",
                "reason": reason,
                "systemMessage": f"{TEP_ICON} Autonomous task stop blocked.",
                "hookSpecificOutput": {
                    "hookEventName": "Stop",
                    "additionalContext": reason,
                },
            }
        )
    )


def emit_warning(reason: str) -> None:
    print(
        json.dumps(
            {
                "systemMessage": f"{TEP_ICON} Autonomous task stop warning.",
                "hookSpecificOutput": {
                    "hookEventName": "Stop",
                    "additionalContext": reason,
                },
            }
        )
    )


def main() -> int:
    payload = load_payload()
    cwd = payload.get("cwd")
    context_root = locate_context(cwd)
    if context_root is None or not hooks_enabled(context_root):
        return 0
    mode = hook_mode(context_root, "stop_guard")
    if mode == "off":
        return 0

    args = ["--context", str(context_root), "stop-guard", "--last-assistant-message-stdin"]
    if stop_hook_active(payload):
        args.append("--stop-hook-active")
    result = run_runtime_gate(*args, input_text=last_assistant_message(payload), cwd=cwd)
    if result.returncode == 0:
        return 0

    reason = (result.stdout or result.stderr or "").strip()
    if not reason:
        reason = "Autonomous task stop guard blocked an unclassified final response."
    if mode == "warn":
        emit_warning(reason)
    else:
        emit_block(reason)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
