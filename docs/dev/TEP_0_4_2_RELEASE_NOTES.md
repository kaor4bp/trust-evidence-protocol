# TEP 0.4.2 Release Notes

Status: local plugin line after the 0.4.1 per-agent identity split.

0.4.2 makes the semantic reasoning chain explicit: the main chain is made of
`CLM-*` records, and edges between claims are themselves `CLM-*` records with
`claim_kind=relation`. The runtime ledger now records `STEP-*` claim-step
entries over that graph instead of treating `REASON-*` as the semantic object.

## Changes

- Bumped package, Codex plugin manifest, Claude plugin manifest, and MCP server
  version to `0.4.2`.
- Added `claim_kind=relation` with a structured `relation` object:
  `kind`, `subject_ref|subject_refs`, and `object_ref|object_refs`.
- Relation kinds are directional. Current proof-capable kinds are `supports`,
  `causes`, `depends_on`, `implies`, and `refines`; `co_relevant` is navigation
  only.
- Relation CLM records cannot carry `scope_refs`. They are general facts, not
  local ledger scope.
- Active single-subject relation claims are deduplicated strictly. A second
  active relation with the same subject and kind must either be represented by
  one merged relation claim or the old relation must be archived first.
- Added `STEP-*` `entry_type=claim_step` ledger entries. A claim step stores
  `prev_step_ref`, `prev_claim_ref`, `claim_ref`, `relation_claim_ref`, `wctx_ref`,
  `task_ref`, `mode`, and the human `reason` text.
- The ledger file remains one append-only hash chain per agent identity. `STEP-*`
  is the semantic entry type; `reason` is only the explanation field.
- `reason-step` and MCP `reason_step` now accept claim-step fields while keeping
  the command/tool name as the public compatibility wrapper.
- Claim-step validation blocks sudden fact jumps: continuing a chain requires a
  relation CLM that connects the previous claim to the next claim.
- Claim-step validation rejects proof/action modes over tentative claims or
  navigation-only relations, and uncertain modes allow at most one tentative hop.

## Compatibility

The public `reason-step` command and `reason_step` MCP tool names remain for
compatibility, but new agent-facing usage should pass `claim_ref` and
`relation_claim_ref` and expect a `STEP-*` id. Legacy evidence-chain payloads
still validate through the old path for existing tests and transition tooling,
but they are not the preferred 0.4.2 reasoning model.
