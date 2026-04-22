#!/usr/bin/env python3
"""Claude Code PreToolUse guard for obvious Bash mutations."""

from __future__ import annotations

import json
from hook_common import (
    active_permission_context,
    hook_mode,
    hooks_enabled,
    append_raw_claim_read_event,
    command_reads_raw_claims,
    command_scope_violation,
    infer_action_kind,
    load_payload,
    locate_context,
    protected_reasoning_write_violation,
    raw_claim_read_allowed,
    run_runtime_gate,
    TEP_ICON,
)


def emit_denial(reason: str, *, permission_context: str | None = None) -> None:
    hook_output: dict[str, object] = {
        "hookEventName": "PreToolUse",
        "permissionDecision": "deny",
        "permissionDecisionReason": reason,
    }
    if permission_context:
        hook_output["additionalContext"] = permission_context
    payload = {
        "systemMessage": f"{TEP_ICON} {reason}",
        "hookSpecificOutput": hook_output,
    }
    print(json.dumps(payload))


def main() -> int:
    payload = load_payload()
    cwd = payload.get("cwd")
    context_root = locate_context(cwd)
    if context_root is None:
        return 0
    if not hooks_enabled(context_root):
        return 0

    mode = hook_mode(context_root, "pre_tool_use_guard")
    if mode == "off":
        return 0

    command = str(payload.get("tool_input", {}).get("command", "")).strip()
    reason_violation = protected_reasoning_write_violation(context_root, command, cwd=cwd)
    if reason_violation:
        emit_denial(reason_violation)
        return 0
    if command_reads_raw_claims(command):
        allowed_mode = raw_claim_read_allowed(command)
        if not allowed_mode:
            append_raw_claim_read_event(context_root, command, cwd=cwd, blocked=True)
            emit_denial(
                "Raw TEP claim JSON reads are blocked in normal mode; use record-detail, claim-graph, linked-records, lookup, or map-brief. "
                "For debug/migration/forensics/plugin-dev, prefix the command with TEP_RAW_RECORD_MODE=<mode>."
            )
            return 0
        append_raw_claim_read_event(context_root, command, cwd=cwd)
    action_kind = infer_action_kind(command, context_root)
    if not action_kind:
        return 0

    scope_violation = command_scope_violation(context_root, command, cwd=cwd)
    if scope_violation:
        emit_denial(scope_violation)
        return 0

    result = run_runtime_gate(
        "--context",
        str(context_root),
        "preflight-task",
        "--mode",
        "action",
        "--kind",
        action_kind,
        cwd=cwd,
    )
    if result.returncode == 0:
        return 0

    message = (result.stdout or result.stderr or "").strip()
    if not message:
        message = f"Bash mutation blocked: action kind {action_kind!r} failed preflight."
    permission_context = active_permission_context(context_root, action_kind, cwd=cwd)
    if mode == "warn":
        print(
            json.dumps(
                {
                    "systemMessage": f"{TEP_ICON} {message.splitlines()[0]}",
                    "hookSpecificOutput": {
                        "hookEventName": "PreToolUse",
                        "additionalContext": permission_context,
                    },
                }
            )
        )
        return 0
    emit_denial(message.splitlines()[0], permission_context=permission_context)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
