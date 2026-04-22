#!/usr/bin/env python3
"""Claude Code PostToolUse review for obvious Bash mutations."""

from __future__ import annotations

import json

from hook_common import (
    TEP_ICON,
    hook_mode,
    hooks_enabled,
    infer_action_kind,
    load_payload,
    locate_context,
    run_context_cli,
    run_runtime_gate,
)


def emit_warning(reason: str, *, hydration_marked_stale: bool) -> None:
    additional_context = (
        "A mutating Bash command completed. Re-run runtime_gate.py hydrate-context "
        "before relying on persistent project facts, planning, or further mutation decisions."
    )
    if hydration_marked_stale:
        additional_context = (
            "A mutating Bash command completed and TEP context hydration was marked stale. "
            "Re-run runtime_gate.py hydrate-context before relying on persistent project facts, "
            "planning, or further mutation decisions."
        )
    payload = {
        "systemMessage": f"{TEP_ICON} {reason}",
        "hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "additionalContext": additional_context,
        },
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

    mode = hook_mode(context_root, "post_tool_use_review")
    if mode == "off":
        return 0

    command = str(payload.get("tool_input", {}).get("command", "")).strip()
    action_kind = infer_action_kind(command, context_root)
    capture_mode = hook_mode(context_root, "run_capture")
    if command and (capture_mode == "all" or (capture_mode == "mutating" and action_kind)):
        exit_code = payload.get("tool_response", {}).get("exit_code")
        run_args = [
            "--context",
            str(context_root),
            "record-run",
            "--command",
            command,
            "--cwd",
            str(cwd or ""),
            "--note",
            "Bash execution captured by PostToolUse hook",
        ]
        if isinstance(exit_code, int):
            run_args.extend(["--exit-code", str(exit_code)])
        run_context_cli(*run_args, cwd=cwd)
    if not action_kind:
        return 0

    if mode == "notify":
        emit_warning(
            f"Mutating Bash command completed ({action_kind}); review whether re-hydration is needed.",
            hydration_marked_stale=False,
        )
        return 0

    result = run_runtime_gate(
        "--context",
        str(context_root),
        "invalidate-hydration",
        "--reason",
        f"mutating Bash command completed ({action_kind}): {command[:120]}",
        cwd=cwd,
    )
    if result.returncode != 0:
        return 0

    emit_warning(
        f"Hydration marked stale after mutating Bash command ({action_kind}).",
        hydration_marked_stale=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
