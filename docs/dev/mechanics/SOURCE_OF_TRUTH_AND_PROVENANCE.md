# Source Of Truth And Provenance

## Responsibility

This mechanic defines what can become durable knowledge and how every durable
claim is tied back to a concrete support surface.

TEP must keep a hard distinction between canonical records and generated
navigation. Generated views may guide inspection, but they must not become proof
without a canonical support path.

## Canonical Direction

```text
INP / FILE / ART / RUN -> SRC -> CLM -> MODEL / FLOW
```

Operational records such as `TASK-*`, `WCTX-*`, `GLD-*`, `RST-*`, `PRP-*`,
`PLN-*`, and `DEBT-*` can control work. They do not prove factual claims.

Navigation records or artifacts such as `CIX-*`, backend hits, topic index
matches, map nodes, and telemetry hints can suggest where to inspect. They are
not truth.

## Record Roles

- `INP-*`: captured or metadata-only user/agent input. It proves the input was
  received, not that its content is true.
- `FILE-*`: metadata for an original file or external file reference.
- `ART-*`: copied or generated artifact payload. It may outlive the original
  file.
- `RUN-*`: command execution trace with command, cwd, exit status, and captured
  output.
- `SRC-*`: source quote derived from one or more provenance surfaces.
- `CLM-*`: the only atomic truth-claim record.
- `MODEL-*` and `FLOW-*`: derived integrated views over claims.

## API Requirements

- Manual `record-source` / `record-claim` should remain possible for migration
  and plugin development, but normal agents should use support-capture APIs.
- Support-capture APIs should let the agent provide path/line/URL/command/input
  and quote; runtime creates or links `FILE-*`, `ART-*`, `RUN-*`, `SRC-*`, and
  optional draft `CLM-*`.
- `SRC-*` without at least one provenance surface should be invalid after
  graph-v2 migration.
- Runtime-plane `CLM-*` should transitively reach `RUN-*`.
- `FILE-*` should try to create an `ART-*` snapshot where configured size/type
  policy allows it.
- If `FILE-*` maps to `CIX-*`, generated chain augmentation may add CIX links
  as navigation metadata, not proof.

## Agent Contract

The agent should not create truth directly. It provides support surfaces and
candidate statements; runtime decides whether the graph is valid.

## Coherence Notes

- `INP-*` classification and cleanup depend on this mechanic.
- Evidence-chain quote validation depends on `SRC-*` and source quote fields.
- MODEL/FLOW promotion depends on CLM status and support plane.

## Known Gaps

- `ART-*` and `FILE-*` boundaries need a stable reference schema for external
  files that cannot be copied.
- Existing legacy `SRC-*` may lack graph-v2 provenance and need migration or a
  compatibility flag.
- Runtime claim transitive `RUN-*` enforcement must be implemented without
  making historical data unreadable.

