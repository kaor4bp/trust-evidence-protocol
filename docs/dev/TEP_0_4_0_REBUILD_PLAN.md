# TEP 0.4.0 Rebuild Plan

This plan turns the 0.4.0 contracts into implementation slices. It assumes the
decisions in `TEP_0_4_0_IMPLEMENTATION_DECISIONS.md`.

## Strategy

Build one clean core service layer and route all adapters through it:

```text
MCP -> service -> structured result
hooks -> service -> structured result
CLI -> service -> renderer / exit code
```

Do not build a parallel v04 runtime. Replace the current runtime shape in
place, while preserving plugin identity and using tests/migration reports to
protect canonical data.

## Milestone 1: Contracts And Schemas

Goals:

- Define dataclass-style internal contracts and exported JSON Schemas.
- Lock response shapes for `next_step`, `lookup`, evidence capture, chain
  validation, `REASON`, chain-ledger entries, `GRANT`, `RUN`, migration
  reports, and map sessions.
- Introduce `contract_version: "0.4"` while documenting any temporary
  compatibility field such as `api_contract_version`.

Exit criteria:

- Schemas exist and can validate representative fixtures.
- MCP front-door responses expose route branches instead of a full command menu.
- Drill-down requests can carry `route_token`, `lookup_ref`, or
  `map_session_ref`.

## Milestone 2: Storage, Context Root, And Migration

Goals:

- Make `~/.tep_context` the only primary runtime root.
- Remove runtime `.codex_context` fallback.
- Keep legacy input discovery only inside explicit migration code.
- Implement migration dry-run, backup, report, apply, validate, and post-review.
- Create `INP-* input_kind=migration_batch` records for legacy provenance.
- Revoke legacy grants for authorization while preserving audit history.

Exit criteria:

- Normal services never select `.codex_context`.
- Raw context reads/writes are blocked for normal agents.
- Migration reports list preserved ids, new provenance wrappers, revoked grants,
  and unresolved records.

## Milestone 3: Core Validators

Implement validators in this order:

1. Workspace focus: durable work requires explicit workspace focus.
2. Provenance graph: new `SRC-*` requires `INP-*`, `FILE-*`, `ART-*`, or
   `RUN-*`.
3. Runtime claim: runtime `CLM-*` requires transitive `RUN-*`.
4. Chain roles: meta, navigation, and control records cannot become
   object-level proof.
5. REASON progression: same-branch continuation cannot reuse the parent chain.
6. Chain ledger integrity: `prev_ledger_hash`, `entry_hash`, `ledger_hash`,
   HMAC seal, `chain_hash`, signed chain summary, and PoW validate for every
   version-2 ledger entry.
7. GRANT/RUN lifecycle: protected action requires a valid grant and mutating
   bash records or links `RUN-*`.
8. MODEL/FLOW authority: no tentative, runtime-only, or meta-only decisive
   support.

Exit criteria:

- Validators are importable services, not CLI subprocess behavior.
- Hook and MCP checks can call the same functions.

## Milestone 4: MCP-Only Agent Route

Goals:

- Expose a small normal-agent MCP surface:

```text
next_step
lookup
record_evidence
augment_chain
validate_chain
reason_step
reason_review
task_outcome_check
backend_status
map_open
map_view
map_move
map_drilldown
map_checkpoint
```

- Keep direct search, record detail, code search, linked records, telemetry, and
  map inspection as drill-down tools requiring route/session context.
- Keep CLI for development, migration, debugging, and CI only.

Exit criteria:

- The skill can describe the MCP route without listing a command zoo.
- Normal-agent conformance tests show use of `next_step`/`lookup` before
  drill-down.

## Milestone 5: Hooks And Protected Actions

Goals:

- Replace shell-out policy checks with direct service calls.
- Hard-block raw `~/.tep_context` record reads and writes in normal mode.
- Classify protected effects separately from action kind:

```text
action_kind: bash|file-write|mcp-write|git|final
effect: read|write|network|process|unknown
```

- Capture mutating bash as `RUN-*`; avoid read-only command noise unless output
  is used as evidence or settings request it.
- Enforce final autonomous completion with final `REASON-*`.

Exit criteria:

- Hooks do not duplicate CLI policy.
- Grant checks and RUN capture use shared services.

## Milestone 6: Cognitive Curiosity Map

Goals:

- Treat curiosity map as a navigable cognitive fact map.
- Persist map session state in `WCTX-*`.
- Surface:
  - anchor facts
  - ignored but relevant facts
  - bridge facts
  - tension facts
  - tap smell
  - neglect pressure
  - inquiry pressure
  - promotion pressure
- Use generated/meta `CLM-*` summaries when they exist, while requiring
  object-level drill-down for proof.

Exit criteria:

- Map MCP tools return bounded views and allowed moves, not full raw graph dumps.
- Every curiosity candidate includes `why_suggested`, expected value, and proof
  route.
- Dismissed/deferred/inspected map candidates are remembered in WCTX session
  state.

## Milestone 7: Feature Recovery And Conformance

Recover broader features after the core is stable:

- MODEL/FLOW promotion helpers
- telemetry and hot-record feedback
- curator pools and curator apply
- backend/code integration polish
- optional HTML map visualization
- live-agent smoke suite

Exit criteria:

- Deterministic tests pass.
- Migration fixtures pass.
- Live-agent smoke verifies MCP front-door behavior, not model intelligence.
