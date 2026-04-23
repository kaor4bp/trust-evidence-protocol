# TEP 0.4.13 Release Notes

TEP 0.4.13 fixes owner-bound agent hydration so a stale thread binding cannot
masquerade as the current agent.

## Changed

- `current_bound_agent_ref()` now treats `thread_binding` as a cache for the
  current `agent_private_key`, not as an independent source of truth.
- Thread-bound `AGENT-*` is accepted only when the binding fingerprint matches
  the fingerprint derived from the current `agent_private_key`.
- Added a regression test for the stale foreign thread-binding case.

## Rationale

`TASK-*` can be shared across agents, but `AGENT-*` and owner-bound `WCTX-*`
cannot. Before this fix, a thread that had been previously bound by one agent
could cause another agent with a different private key to resolve the wrong
`AGENT-*` during read-only ownership checks. That made some hydration and focus
paths reason from the wrong owner identity even though write paths already
required the correct key-derived binding.

## Migration Notes

No record migration is required. Existing `AGENT-*` and `WCTX-*` records remain
valid; the release tightens runtime ownership resolution only.
