# TEP 0.4.3 Release Notes

Status: local plugin line after the 0.4.2 claim-step ledger.

0.4.3 tightens claim-step relation coherence. A `STEP-*` chain can no longer
contain an inverse proof-capable relation of the same kind, such as
`CLM-A depends_on CLM-B` followed by `CLM-B depends_on CLM-A`.

## Changes

- Bumped package, Codex plugin manifest, Claude plugin manifest, and MCP server
  version to `0.4.3`.
- Added chain-local inverse relation detection for `STEP-* entry_type=claim_step`.
- The append path rejects inverse relation attempts and returns the existing
  relation CLM, existing STEP, candidate relation CLM, and a suggested new-chain
  command shape for the agent.
- State validation now checks existing per-agent ledgers for inverse relation
  violations across `prev_step_ref` lineage.

## Compatibility

This is a validator tightening. Existing valid 0.4.2 claim-step chains remain
valid. Chains that relied on reciprocal proof-capable relations inside one
branch must be split into separate `STEP-*` chains or represented by an explicit
higher-level CLM relation.
