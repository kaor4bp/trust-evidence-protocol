# TEP 0.4.1 Release Notes

Status: local plugin line after the 0.4.0 rebuild.

0.4.1 separates agent identity from the shared `.tep_context` runtime root.
Each agent must invent a private per-agent key and reuse it for owner-bound
mutations.

## Changes

- Bumped package, Codex plugin manifest, Claude plugin manifest, and MCP server
  version to `0.4.1`.
- Replaced the shared `runtime/agent_identity/local_agent_key.json` write path
  with key-fingerprint-scoped private state:
  `runtime/agent_identity/agents/<key_fingerprint_hash>.json`.
- Added MCP `agent_private_key` input for owner-bound and mutating tools:
  `lookup`, `record_evidence`, `reason_step`, `reason_review`, `map_refresh`,
  `map_open`, `map_view`, `map_move`, `map_drilldown`, `map_checkpoint`, and
  `schema_migration_apply`.
- Missing private key now blocks WCTX/REASON/GRANT owner-bound mutations with
  `agent_identity_required`.
- Reason grant validation now requires the current per-agent identity and
  rejects grants from another agent's ledger.

## Compatibility

This is an intentional tightening, not a legacy compatibility layer. Existing
shared local identity files are not accepted as current-agent ownership proof.
