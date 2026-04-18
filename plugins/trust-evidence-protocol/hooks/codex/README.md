# Codex Hook Adapters

This folder contains Codex hook adapters wired through `.codex/hooks.json` in
the repository where the plugin is being tested.

Runtime modes are read from project policy in:

- `<context>/settings.json`

Supported hook settings:

- `hooks.enabled`: `true | false`
- `hooks.session_start_hydrate`: `off | on`
- `hooks.user_prompt_notice`: `off | on`
- `hooks.pre_tool_use_guard`: `off | warn | enforce`
- `hooks.post_tool_use_review`: `off | notify | invalidate`

Human-facing hook `systemMessage` values use the `🛡️` TEP marker.
Do not add the marker to canonical records or machine-readable ids.

Current adapters:

- `session_start_hydrate.py`
  - runs `plugins/trust-evidence-protocol/scripts/runtime_gate.py hydrate-context`
  - activates for the resolved TEP context root, preferring `~/.tep_context`
- `user_prompt_hydration_notice.py`
  - runs `plugins/trust-evidence-protocol/scripts/runtime_gate.py show-hydration`
  - injects developer context when hydration is stale or missing
- `pre_tool_use_guard.py`
  - runs on Codex `PreToolUse` for `Bash`
  - detects only obvious mutating shell commands
  - delegates final decision to `runtime_gate.py preflight-task`
- `post_tool_use_review.py`
  - runs on Codex `PostToolUse` for `Bash`
  - can warn or mark hydration stale after obvious mutating shell commands complete
  - injects a warning to re-run hydration before relying on project facts

These are intentionally conservative:

- no automatic `Stop` continuation loops
- `PreToolUse` only covers obvious Bash mutations
- `PostToolUse` cannot undo completed side effects
- no claim of complete enforcement across non-Bash tools
