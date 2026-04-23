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
  validation, agent identity, owner-bound `WCTX`, `REASON`,
  chain-ledger entries, `GRANT`, `RUN`, migration reports, and map sessions.
- Introduce `contract_version: "0.4"` while documenting any temporary
  compatibility field such as `api_contract_version`.
- Introduce canonical `record_version` for new 0.4 record shapes so migrations
  can branch on concrete record format without confusing it with generated
  `schema_version` metadata.

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

Progress:

- `next_step` MCP now calls `tep_runtime.action_graph` directly instead of
  shelling out to `context_cli.py`.
- `lookup` MCP and CLI now share `tep_runtime.lookup_service`; the MCP adapter
  no longer shells out for the lookup front door.
- `migration_dry_run` MCP already uses the migration service directly.
- `record_version=1` is the current canonical record-shape marker. Legacy
  records without `record_version` remain readable, while new 0.4-only records
  such as `MAP-*` must carry both `contract_version` and `record_version`.

## Milestone 3: Core Validators

Implement validators in this order:

1. Workspace focus: durable work requires explicit workspace focus.
2. WCTX ownership: active focus requires a valid owner signature and matching
   local `AGENT-*`; non-owner agents must fork/adopt instead of reusing WCTX.
3. Provenance graph: new `SRC-*` requires `INP-*`, `FILE-*`, `ART-*`, or
   `RUN-*`.
4. Runtime claim: runtime `CLM-*` requires transitive `RUN-*`.
5. Chain roles: meta, navigation, and control records cannot become
   object-level proof.
6. REASON progression: same-branch continuation cannot reuse the parent chain.
7. Chain ledger integrity: `prev_ledger_hash`, `entry_hash`, `ledger_hash`,
   HMAC seal, `chain_hash`, signed chain summary, and PoW validate for every
   version-2 ledger entry.
8. GRANT/RUN lifecycle: protected action requires a valid grant and mutating
   bash records or links `RUN-*`.
9. MODEL/FLOW authority: no tentative, runtime-only, or meta-only decisive
   support.

Exit criteria:

- Validators are importable services, not CLI subprocess behavior.
- Hook and MCP checks can call the same functions.

Progress:

- Added `tep_runtime.core_validators` as the shared graph-level validation
  service for 0.4/graph-v2 records.
- Enforced source provenance, runtime-claim RUN reachability, owner-bound WCTX,
  and MODEL/FLOW authority without forcing legacy records through migration
  prematurely.
- Added optional `AGENT-*` record loading so WCTX ownership validation can
  resolve local agent identities while old contexts remain readable.
- Added active focus validation as a shared preflight service for current
  workspace/project/task status and compatibility. It is intentionally not a
  whole-state invariant because lifecycle commands can briefly keep stale focus
  while switching or completing tasks.
- Connected active focus validation to mutating runtime preflight so `edit` and
  mutating `action` gates reject stale or incompatible workspace/project/task
  focus before decomposition or grant checks.
- Connected reason ledger integrity to state validation through a read-only
  preflight path. `validate_reason_ledger()` keeps the existing write-path
  behavior by default, while shared validation checks `prev_ledger_hash`,
  `entry_hash`, seal, `ledger_hash`, `chain_hash`, and PoW without creating
  `runtime/reasoning/seal.json` for empty contexts.
- Added GRANT/RUN lifecycle validation as a shared service. Durable `RUN-*` and
  protected records that cite `grant_ref` must point to a current v2 `GRANT-*`,
  match grant scope/action/command bindings, and respect `max_runs`.
- Marked `records/curator_pool` as an optional backfill-safe directory so older
  contexts do not break MCP front doors before their first `CURP-*` pool exists.

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
map_refresh
```

- Keep direct search, record detail, code search, linked records, telemetry, and
  map inspection as drill-down tools requiring route/session context.
- Keep CLI for development, migration, debugging, and CI only.

Exit criteria:

- The skill can describe the MCP route without listing a command zoo.
- Normal-agent conformance tests show use of `next_step`/`lookup` before
  drill-down.

Progress:

- `reason_step` and `reason_review` now share `tep_runtime.reason_service`
  between CLI and MCP. The MCP handlers append and review the reason ledger
  directly, including PoW/HMAC ledger validation, without shelling out to the
  development CLI.
- Added MCP conformance coverage that monkeypatches CLI execution to fail and
  still proves `next_step`, `lookup`, `reason_step`, and `reason_review` work
  through direct service calls.
- `augment_chain` and `validate_chain` now share `tep_runtime.chain_service`.
  MCP enrichment/validation reads chain files and returns structured results
  directly instead of shelling out to the development CLI. The CLI keeps the
  compatibility command name `validate-evidence-chain`; normal-agent MCP uses
  the 0.4-facing `validate_chain` name.
- `record_evidence` now uses `tep_runtime.evidence_service` from both CLI and
  MCP. The MCP handler takes the write lock and creates FILE/RUN/SRC plus
  optional CLM records directly, preserving the normal provenance graph without
  exposing low-level `record-source` / `record-claim` as the agent-facing path.
- `task_outcome_check` now uses `tep_runtime.task_outcome_service` from both
  CLI and MCP. The MCP handler performs the read-only mechanical finalization
  gate directly, while the CLI keeps the compatibility `task-outcome-check`
  command for development, hooks, and CI.

## Milestone 5: Hooks And Protected Actions

Goals:

- Replace shell-out policy checks with direct service calls.
- Hard-block raw `~/.tep_context` record reads and writes in normal mode.
- Generate or load the current agent key through the runtime service; never ask
  normal agents to read/write key material or raw WCTX files.
- Block active use of a WCTX signed by a different agent identity and return a
  fork/adopt repair route.
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
- Represent durable cognitive memory as shared `MAP-*` records where one record
  is one cell at one abstraction level.
- Persist agent-specific map session state in owner-bound `WCTX-*`.
- Keep `curiosity-map`/attention output as generated sensor views; use explicit
  `map_refresh` to create or update durable `MAP-*` cells.
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
- Refresh map cells when map-relevant `CLM-*` records appear, when
  `MODEL-*`/`FLOW-*` records are created or changed, or when source-set
  fingerprints/staleness triggers change.
- Update pressure/activity signals in place; create a new `MAP-*` with
  `refines_map_refs`/`supersedes_refs` when cell meaning changes materially.

Exit criteria:

- Map MCP tools return bounded views and allowed moves, not full raw graph dumps.
- Every curiosity candidate includes `why_suggested`, expected value, and proof
  route.
- Dismissed/deferred/inspected map candidates are remembered in WCTX session
  state.
- `map_refresh` is the only normal map operation that mutates durable `MAP-*`
  records.

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
