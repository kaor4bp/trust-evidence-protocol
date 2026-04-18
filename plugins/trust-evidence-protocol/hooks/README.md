# Hook Entry Points

This folder contains stable wrapper entry points for runtime integration.

They are not auto-discovered directly by Codex. Official Codex hooks are configured
through `hooks.json`, for example:

- `.codex/hooks.json` in the repository where the plugin is being tested

Current wrappers:

- `hydrate_context.sh`
  - calls `scripts/runtime_gate.py hydrate-context`
- `preflight_task.sh`
  - calls `scripts/runtime_gate.py preflight-task`

Use these wrappers from hook adapters or any external runner that needs a stable path.

Canonical Codex hook adapter templates are stored in `hooks/codex/`.
Copy them to a repository-local `.codex/hooks/` folder together with a matching
`.codex/hooks.json` when testing Codex hook behavior in a project.

The adapter command classifier is intentionally conservative. In particular,
`patch` is treated as mutating only when it is the shell command for a command
segment, not when `patch` appears inside a read-only file path such as
`patches/fix.patch`.

File output is allowed without strictness escalation only when every detected
output target is inside the canonical `.codex_context/artifacts/` store. This
keeps screenshots, copied logs, and other diagnostic payloads cheap to capture
while still blocking ordinary writes to source files, `/tmp`, or arbitrary
workspace paths under `proof-only`.
