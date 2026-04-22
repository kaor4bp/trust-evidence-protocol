# Telemetry, Cleanup, And Token Pressure

## Responsibility

This mechanic keeps the system usable as records grow.

## Telemetry

Telemetry should detect whether TEP is helping or annoying agents.

Signals include raw claim reads, repeated hot record reads, lookup reason
distribution, MCP vs CLI usage, backend readiness, missing WCTX/task focus,
missing reason chains, grant misses, chain validation failures, and unresolved
INP.

Telemetry should return recommended compact tools, not just counters.

## Cleanup

Cleanup should be staged:

```text
candidate -> archive -> delete
```

Rules:

- resolved/historical/stale claims rank below active records
- old resolved bug claims should not dominate lookup
- stale facts are fallback context, not primary proof
- unreferenced `INP-*` is not archived immediately; age threshold is settings
  controlled
- archive before delete
- cleanup keeps enough provenance to explain why a record was hidden or removed

## Token Pressure

Primary strategy is mechanical substitution, not truncation.

Move route choice, chain starter/extension, chain augmentation, guideline
selection, linked record retrieval, backend code search, map summaries, and
telemetry anomaly hints out of the LLM.

Context budget settings can compact output, but should not be the main design.

## Coherence Notes

- MODEL/FLOW promotion is a token-pressure tool.
- Curiosity map cold/hot zones use telemetry.
- Cleanup affects lookup ranking and must not erase proof-critical provenance.

## Known Gaps

- Archive restore semantics need definition.
- Raw-read telemetry depends on hook coverage; MCP-only reads need equivalent
  accounting.
- Token savings should be measured with before/after live-agent runs.

