# Lookup And Chain Extension

## Responsibility

Lookup is the default read path. It should keep agents away from raw records and
guide them toward proof-capable next steps.

## Default Route

Normal agent read flow:

```text
lookup(query, reason, kind)
-> returned route commands
-> compact graph/detail drill-down
-> chain starter or extension
```

Lookup output should include primary tool, next allowed commands, route graph,
output contract, evidence profile, navigation-only `map_navigation`, chain
starter or extension, fallback route, and proof boundary reminders.

## Chain Extension Mode

When a current `STEP-*` exists, lookup should default to extension mode:

- inspect the current claim-step chain
- exclude refs already present in that chain
- search for records that can become connected CLM successors
- include current task node when useful
- report excluded count and new candidate count
- return fallback when no new proof-capable node exists

Fallback should not simply reuse the old chain. It should say:

- review existing nodes
- find a new quote or relation
- record an open question
- record a fact-compatible hypothesis
- fork a named reasoning branch if pursuing an alternative

## Proof Boundary

Lookup is navigation. It can propose chain nodes but cannot prove anything.

Backend hits, CIX, `MAP-*` cells, topic hits, and generated summaries should be
kept out of proof nodes unless converted into canonical records through support
capture. `MAP-*` cells may appear under `map_navigation`; they must not appear
as `chain_starter.nodes`.

## API Requirements

- Lookup must require a reason.
- Lookup should auto-create WCTX only when workspace focus is explicit.
- Lookup should expose backend status when a route depends on a backend.
- Lookup should return compact summaries, not full raw record payloads.
- Lookup should prefer MODEL/FLOW for integrated picture, then active CLM graph,
  then drill-down detail.

## Coherence Notes

- Evidence chain validation consumes lookup chain drafts.
- REASON progression depends on lookup being able to provide new nodes.
- Telemetry should reveal whether agents bypass lookup.

## Known Gaps

- Ranking "new useful node" needs more than text search. It should consider
  chain role, topic cluster, topology bridge, recency, trust, and conflict
  pressure.
- Lookup fallback should be tested against cases where no new fact exists but a
  useful hypothesis can be formed.
