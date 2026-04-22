# TEP 0.4.0 Implementation Decisions

This document records accepted implementation decisions for the 0.4.0
architectural rebuild. It is a planning lock: if implementation discovers a
conflict, update this document and the normative contract before changing code.

## Product Boundary

- Target version is `0.4.0`.
- The rebuild is an architectural reassembly of the core mechanics, not a
  compatibility refactor of the current command surface.
- Keep the plugin name, display identity, and skill names stable.
- The old CLI command zoo is not public API for normal agents.
- `context_cli.py` may remain as a test, development, debugging, migration, and
  CI wrapper over shared services.

## Agent API

- Normal agents use MCP-only front doors.
- MCP tools may mutate canonical context, but only through shared core services
  and validators.
- The normal front doors are `next_step` and `lookup`.
- Drill-down tools such as `record_detail`, `linked_records`, `claim_graph`,
  `code_search`, and map tools are available only through returned route
  branches.
- Drill-down tools should accept a lightweight `route_token`, `lookup_ref`, or
  `map_session_ref` so conformance can verify that the agent followed the route.
- MCP, hooks, and CLI adapters must call the same core services directly. The
  CLI must not be the internal policy engine.

## Context Root And Raw Access

- `~/.tep_context` is the only primary runtime context root.
- `.codex_context` is no longer a runtime concept.
- Legacy `.codex_context` data may appear only as an explicit migration input or
  fixture.
- Normal agents must not read or write raw `~/.tep_context` records.
- Raw access to records is hard-blocked in normal hooks for reads and writes.
- Debugging, migration, forensics, and plugin development may use explicit raw
  access modes such as `TEP_RAW_RECORD_MODE=migration|forensics|plugin-dev`.
  These accesses must be visible to telemetry or audit output.

## Migration

- Migration is staged: dry-run, backup, migration report, apply, validate,
  post-review.
- `migrate_context dry-run` can be exposed through MCP.
- `migrate_context apply` is a privileged migration operation. It should remain
  CLI/dev-only or require an explicit user-confirmed migration grant before MCP
  can apply it.
- Legacy provenance must not be faked.
- Legacy records that need graph-v2 provenance get `INP-*` records with
  `input_kind=migration_batch`.
- Prefer one migration `INP-*` per migrated legacy file or logical batch.
- Preserve canonical record ids where possible.
- New ids are expected for migration provenance wrappers.
- Old `GRANT-*` records are preserved for audit but revoked for authorization.

## Authorization

- New `GRANT.action_kind` enum is exactly:

```text
bash|file-write|mcp-write|git|final
```

- Old grant shapes and old action-kind labels are not accepted for 0.4.0
  authorization.
- Final autonomous completion requires `REASON-* mode=final`.
- Strict autonomous finalization may require `GRANT-* mode=final`; ordinary
  non-autonomous answers should not become grant ceremony unless settings demand
  it.

## Curiosity Map

- Curiosity map is a navigation-only cognitive fact map.
- It exists to give agents a bounded mental picture of the fact space without
  exposing raw records.
- The map shows anchor facts, neglected relevant facts, bridge facts, tension
  facts, tap smell, and inquiry pressure.
- Map sessions are persisted in `WCTX-*` as operational state, not truth.
- Map tools do not create `OPEN-*`, `DEBT-*`, `PRP-*`, or truth records
  automatically.
- Map drill-down returns proof routes. It does not produce proof.
- HTML visualization is optional for 0.4.0; MCP navigation and compact
  text/JSON projections come first.
