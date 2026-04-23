# TEP 0.4.16 Release Notes

## Summary

`0.4.16` is a stabilization release focused on removing agent-facing blockers in
identity bootstrap, write gating, lookup working-context reporting,
reason-ledger validation, and live-agent decision/help-output drift.

## What Changed

- Identity-bound MCP tools now require explicit `agent_private_key` in the tool
  schema, and startup hooks bootstrap that requirement before routing the agent
  into TEP front doors.
- CLI and MCP front doors treat missing `agent_private_key` as an explicit agent
  contract failure instead of surfacing misleading downstream `WCTX-*` errors.
- `current_bound_agent_ref()` no longer accepts stale foreign thread bindings
  unless the bound key fingerprint matches the current `agent_private_key`.
- Mutating writes such as `start-task` no longer get blocked by unrelated
  integrity/signature errors on non-active `WCTX-*` records.
- Read-only reason-ledger validation now discovers per-agent ledgers even when a
  current agent key is not loaded, while still ignoring foreign ledgers when the
  current local agent is known.
- Lookup now keeps reporting when the active `WCTX-*` was originally
  auto-created, even on subsequent calls that reuse that same auto-created
  context.
- `review-context` now emits both `Review OK:` and `Reviewed context:` success
  markers so older CLI callers and newer live-plugin conformance checks stay
  compatible.
- `help commands` now lists `record-evidence` explicitly, so runtime help and
  live-plugin conformance cover the same write route that the CLI already
  exposes.
- The TEP skill and Codex live harness now pin down bounded-subset,
  non-blocking-irrelevant-variable, negative-gating, and proof-only-vs-
  implementation-choice behavior so the live agent stops oscillating between
  `ask`, `green`, and mislabeled freedom levels in fact-determined cases.

## Verification

- `pytest -q tests/trust_evidence_protocol`
- `pytest -m live_agent tests/trust_evidence_protocol -q`
- `./scripts/install-local-plugin.sh`

## Notes

- Final verification for this release completed with `211 passed, 40 deselected`
  in the non-live suite and `40 passed, 210 deselected` in the live-agent suite.
