#!/usr/bin/env python3
"""Repo-local Codex hook that reminds Codex when .codex_context hydration is stale."""

from __future__ import annotations

import json

from hook_common import TEP_ICON, hook_mode, hook_verbosity, hooks_enabled, load_payload, locate_context, run_runtime_gate


PROTOCOL_REMINDER = (
    "Use the Trust Evidence Protocol skill. Search `.codex_context` first via MCP/brief-context, then show "
    "compact public Evidence Chain or Reasoning Checkpoint panels when planning, asking permission, persisting, "
    "or editing. For green/red/ask decisions, target assertions and user pressure are not proof; unanchored "
    "targets require `ask` when available or `red` when not. For substantial code edits, cite applicable "
    "`GLD-* + quote` before edits and `Guidelines used:` after."
)


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
            "project facts, planning, or edits, refresh .codex_context with "
            "trust-evidence-protocol runtime_gate.py --context .codex_context hydrate-context."
        ),
        system_message="Context hydration is stale.",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
