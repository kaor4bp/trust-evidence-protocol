# TEP 0.4.0 MAP Records

Status: design note for 0.4.0 implementation.

This document fixes the intended semantics of `MAP-*` records after the
curiosity-map discussion.

## Decision

`MAP-*` is a canonical navigation record for one cognitive map cell.

One `MAP-*` record has exactly one abstraction level:

- `L1`: evidence patch
- `L2`: abstraction or mechanism cell
- `L3`: task situation or strategy cell

`MAP-*` is never a full project map and never a container with embedded
`L1/L2/L3` sections. Larger maps are graphs of many `MAP-*` cells connected by
`up_refs`, `down_refs`, `adjacent_map_refs`, and other typed map links.

## Why

The runtime needs to help agents build a compact cognitive picture without
forcing them to read raw facts. The current attention/curiosity map is useful as
navigation, but it is still close to record-level graph exploration. `MAP-*`
adds a persistent middle layer:

```text
proof/support records -> MAP-L1 -> MAP-L2 -> MAP-L3 -> route/strategy
```

This keeps the map scalable:

- many small `MAP-L1` cells near evidence
- fewer `MAP-L2` cells for patterns and mechanisms
- still fewer `MAP-L3` cells for current task meaning and strategy

## Non-Goals

- `MAP-*` is not proof.
- `MAP-*` is not a substitute for `CLM-*`, `MODEL-*`, or `FLOW-*`.
- `MAP-*` does not create truth automatically.
- `MAP-*` should not hold large raw record sets.
- `MAP-*` should not duplicate the full attention index or HTML graph payload.

## Relationship To Other Records

```text
INP/FILE/ART/RUN -> SRC -> CLM(object)
many CLM(object) -> CLM(meta_aggregated)
CLM/MODEL/FLOW/CIX -> MAP-L1/L2/L3 navigation cells
MAP cells -> lookup/map route hints
```

Rules:

- `CLM-*` remains the atomic truth assertion.
- `CLM-* plane=meta claim_kind=meta_aggregate` is the preferred bridge when
  many object-level facts need to be summarized for map use.
- `MODEL-*` and `FLOW-*` remain confirmed integrated domain knowledge.
- `MAP-*` may point to `MODEL-*`/`FLOW-*` as anchors, but must not pretend to be
  confirmed model/flow knowledge.
- `WCTX-*` may keep active map session state and selected `MAP-*` refs.
- `REASON-*` may cite a `MAP-*` only as navigation context. Proof routes must
  drill down to proof-capable records.

## Common MAP Schema Shape

All levels share these fields:

```json
{
  "id": "MAP-*",
  "record_type": "map",
  "contract_version": "0.4",
  "record_version": 1,
  "level": "L1|L2|L3",
  "map_kind": "...",
  "status": "active|stale|archived",
  "summary": "...",
  "scope_refs": {
    "workspace_refs": ["WSP-*"],
    "project_refs": ["PRJ-*"],
    "task_refs": ["TASK-*"],
    "wctx_refs": ["WCTX-*"]
  },
  "anchor_refs": [],
  "derived_from_refs": [],
  "source_set_fingerprint": "sha256:...",
  "up_refs": [],
  "down_refs": [],
  "adjacent_map_refs": [],
  "contradicts_map_refs": [],
  "refines_map_refs": [],
  "supersedes_refs": [],
  "tension_refs": [],
  "unknown_links": [],
  "proof_routes": [],
  "signals": {
    "tap_smell": {
      "score": 0.0,
      "half_life_days": 7.0,
      "last_updated_at": "..."
    },
    "neglect_pressure": {"score": 0.0},
    "inquiry_pressure": {"score": 0.0},
    "promotion_pressure": {"score": 0.0},
    "staleness_pressure": {"score": 0.0},
    "conflict_pressure": {"score": 0.0}
  },
  "map_is_proof": false,
  "generated_by": "lookup|curiosity_map|curator|agent_request|map_refresh",
  "generated_at": "...",
  "updated_at": "...",
  "stale_policy": "anchor_changed|source_set_changed|time_window_expired|manual"
}
```

Field rules:

- `contract_version` identifies the public record contract. New 0.4 MAP cells
  must use `contract_version=0.4`.
- `record_version` identifies the concrete record shape for migration. New MAP
  cells start at `record_version=1`.
- `level` is required and must be exactly one of `L1`, `L2`, or `L3`.
- `map_is_proof` must be `false`.
- `anchor_refs` are the most important records for understanding this cell.
- `derived_from_refs` explain how this cell was constructed.
- `source_set_fingerprint` is computed from the semantic source set used to
  create the cell. It is the primary refresh/staleness comparison key.
- `up_refs` point to higher-abstraction map cells.
- `down_refs` point to lower-abstraction map cells.
- `adjacent_map_refs` point to same-level neighboring cells.
- `refines_map_refs` point to older or broader cells that remain useful.
- `supersedes_refs` point to older cells replaced by a newer semantic cell.
- `unknown_links` are structured candidate/missing/rejected/unknown link
  objects. Do not encode free-form `candidate:A->B` strings.
- `proof_routes` are instructions for drilling down to proof-capable records.
  They are not proof by themselves.
- `signals` are activity and pressure values. They may be updated in place when
  the cell meaning has not changed.
- Runtime-created cells should also mirror active `workspace_refs`,
  `project_refs`, and `task_refs` at top level when those refs exist. This keeps
  shared durable-record validators and focus search aligned with `scope_refs`.

`unknown_links` entries should use this shape:

```json
{
  "id": "ULINK-*",
  "from_ref": "CLM-*",
  "to_ref": "MODEL-*",
  "link_kind": "candidate|missing|rejected|unknown",
  "status": "candidate|dismissed|deferred|confirmed",
  "source_signal": "probe|bridge|topic|curator|agent",
  "why_suggested": "..."
}
```

`scope_refs` must be present. Runtime-created cells should default missing
workspace/project/task/WCTX lists to empty arrays before validation.

## L1 Evidence Patch

Purpose: compact navigation cell close to evidence and claims.

Typical anchors:

- `CLM-*`
- `CLM-* plane=meta`
- `SRC-*`
- `RUN-*`
- `FILE-*`
- `ART-*`
- `CIX-*` when the cell is code-adjacent navigation

Allowed derived sources:

- record links
- lookup output
- topic/attention/code index hints
- `CLM(meta_aggregated)`

Example:

```json
{
  "id": "MAP-20260423-l1abc123",
  "record_type": "map",
  "contract_version": "0.4",
  "record_version": 1,
  "level": "L1",
  "map_kind": "evidence_patch",
  "summary": "Runtime and claim evidence around SmartPick entity visibility.",
  "anchor_refs": ["CLM-...", "CLM-meta-...", "SRC-...", "RUN-..."],
  "up_refs": ["MAP-20260423-l2abc123"],
  "proof_routes": [
    {
      "route_kind": "claim_support",
      "route_refs": ["CLM-...", "SRC-...", "RUN-..."],
      "required_drilldown": true
    }
  ],
  "map_is_proof": false
}
```

L1 validation:

- L1 may anchor directly to proof-capable records.
- L1 may include CIX/backend/navigation anchors, but proof routes cannot end at
  CIX/backend/navigation records.
- L1 should use `CLM(meta_aggregated)` instead of listing many similar object
  claims.

## L2 Abstraction Or Mechanism Cell

Purpose: local abstraction over one or more L1 cells.

Typical anchors:

- `MAP-* level=L1`
- `CLM(meta_aggregated)`
- `MODEL-*`
- `FLOW-*`
- high-value `CLM-*` when the abstraction is still tentative

Typical map kinds:

- `mechanism_cell`
- `pattern_cell`
- `workflow_cell`
- `code_area_cell`
- `risk_cell`
- `policy_cell`
- `open_frontier_cell`

Example:

```json
{
  "id": "MAP-20260423-l2abc123",
  "record_type": "map",
  "contract_version": "0.4",
  "record_version": 1,
  "level": "L2",
  "map_kind": "mechanism_cell",
  "summary": "Fresh entities may not be reliably visible until sync/cache boundaries are crossed.",
  "derived_from_refs": ["MAP-20260423-l1abc123", "CLM-meta-...", "MODEL-..."],
  "down_refs": ["MAP-20260423-l1abc123"],
  "up_refs": ["MAP-20260423-l3abc123"],
  "tension_refs": ["CLM-..."],
  "unknown_links": [
    {
      "id": "ULINK-...",
      "from_ref": "CLM-...",
      "to_ref": "MODEL-...",
      "link_kind": "candidate",
      "status": "candidate",
      "source_signal": "probe",
      "why_suggested": "Facility and Program visibility claims share a cold topic and no established direct link."
    }
  ],
  "map_is_proof": false
}
```

L2 validation:

- L2 must have at least one `down_refs` entry or at least one
  `CLM(meta_aggregated)`/`MODEL-*`/`FLOW-*` anchor.
- L2 must label tentative abstractions as navigation, not theory.
- L2 cannot promote itself to `MODEL-*` or `FLOW-*`; promotion requires the
  normal MODEL/FLOW gate.

## L3 Task Situation Or Strategy Cell

Purpose: local meaning for the current task, plan, or working context.

Typical anchors:

- `MAP-* level=L2`
- `TASK-*`
- `WCTX-*`
- `PLAN-*`
- `REASON-*`
- `OPEN-*`
- `PRP-*`

Typical map kinds:

- `task_situation`
- `debugging_strategy`
- `implementation_strategy`
- `curator_strategy`
- `retrospective_cell`
- `decision_pressure_cell`

Example:

```json
{
  "id": "MAP-20260423-l3abc123",
  "record_type": "map",
  "contract_version": "0.4",
  "record_version": 1,
  "level": "L3",
  "map_kind": "task_situation",
  "summary": "Tests should avoid assuming immediate SmartPick visibility for freshly created entities.",
  "derived_from_refs": ["MAP-20260423-l2abc123", "TASK-...", "WCTX-..."],
  "down_refs": ["MAP-20260423-l2abc123"],
  "signals": {
    "next_moves": [
      {
        "kind": "record_evidence",
        "target_refs": ["CLM-..."],
        "why": "Confirm whether the observed visibility behavior still holds."
      },
      {
        "kind": "ask_user",
        "target_refs": ["OPEN-..."],
        "why": "User confirmation is needed before promoting this to MODEL/FLOW."
      }
    ]
  },
  "proof_routes": [
    {
      "route_kind": "task_decision_support",
      "route_refs": ["MAP-20260423-l2abc123", "MAP-20260423-l1abc123", "CLM-meta-...", "CLM-...", "SRC-..."],
      "required_drilldown": true
    }
  ],
  "map_is_proof": false
}
```

L3 validation:

- L3 must be scoped to a task, plan, WCTX, or explicit retrospective context.
- L3 should not anchor directly to large object-level claim sets; use L2/L1 or
  `CLM(meta_aggregated)`.
- L3 may recommend next moves, but executing them still requires normal route,
  chain, REASON, and GRANT rules.

## Link Semantics

Typed map links are navigation links:

- `up_refs`: lower level to higher level.
- `down_refs`: higher level to lower level.
- `adjacent_map_refs`: same-level neighborhood.
- `contradicts_map_refs`: map cells whose summaries or implications are in
  tension.
- `refines_map_refs`: newer or narrower map cells that refine an older/broader
  map cell.

Validation should enforce level direction:

```text
L1 up_refs -> L2 or L3
L2 down_refs -> L1
L2 up_refs -> L3
L3 down_refs -> L2 or L1
adjacent_map_refs -> same level preferred; cross-level allowed only with reason
```

`up_refs` and `down_refs` should be reciprocal when both cells already exist.
Validation may warn instead of failing when a partial refresh creates one side
first.

## Lookup Behavior

`lookup` may return `MAP-*` cells as navigation context.

Rules:

- `MAP-L3` is useful for current task orientation.
- `MAP-L2` is useful for theory/mechanism lookup.
- `MAP-L1` is useful for proof-route discovery.
- Lookup should not return many raw `MAP-L1` cells when a `MAP-L2` or
  `CLM(meta_aggregated)` already summarizes them.
- Current implementation ranks active `L2` cells with `down_refs` above covered
  `L1` cells and includes `up_refs`, `down_refs`, and `covered_by_map_refs` in
  `lookup.map_navigation.cells`.
- `map_drilldown` expands a selected `L2`/`L3` cell through bounded `down_refs`
  and returns the lower-level `proof_routes` with `source_map_ref`,
  `via_map_refs`, and `expanded_from_map_ref` metadata.
- If the current `REASON-*` branch exists, lookup should prefer map cells that
  add new chain nodes or expose unresolved tensions.

Example lookup ordering:

```text
MODEL/FLOW integrated theory
MAP-L3 current task situation
MAP-L2 mechanism/pattern cells
CLM(meta_aggregated)
MAP-L1 evidence patches
object-level CLM drill-down candidates
navigation-only CIX/backend/topic hits
```

`lookup` should prefer existing `MAP-*` cells over regenerating a large map
view. `curiosity_map` and attention output are signal sources; durable MAP cells
are the preferred navigation memory.

## Proof Behavior

`MAP-*` must not be accepted as a proof node in an evidence chain.

Allowed:

```text
MAP-* -> proof_routes -> CLM/SRC/RUN/INP/FILE/ART
```

For higher-level cells:

```text
MAP-L2/L3 -> down_refs -> MAP-L1/L2 -> proof_routes -> CLM/SRC/RUN/INP/FILE/ART
```

The expanded route is still navigation. `route_is_proof=false` must remain true
until `record_detail`, `augment_chain`, and `validate_chain` produce a valid
proof-capable chain.

Not allowed:

```text
MAP-* -> final conclusion
MAP-* -> MODEL/FLOW promotion support
MAP-* -> GRANT justification without chain drill-down
```

`MAP-*` may appear in `REASON-*` as navigation context if the reason step also
contains proof-capable chain nodes or explicitly states that it is exploratory.

## Curiosity And Pressure Signals

`MAP-*` cells may include navigation signals:

- `tap_smell`: repeated access suggests fixation or missing abstraction.
- `neglect_pressure`: relevant but rarely inspected cell.
- `inquiry_pressure`: unresolved hypotheses, candidate links, or high-value
  unknowns.
- `promotion_pressure`: many scattered facts suggest a needed
  `CLM(meta_aggregated)`, `MODEL-*`, or `FLOW-*`.
- `staleness_pressure`: important anchors may be outdated.
- `conflict_pressure`: nearby cells or claims are contradictory.

Signals are not proof. They rank inspection order and route suggestions.

Signal updates are not semantic updates. `tap_smell`, `neglect_pressure`,
`inquiry_pressure`, `promotion_pressure`, `staleness_pressure`, and
`conflict_pressure` may be updated in place when the cell summary, anchors, and
proof routes still describe the same meaning.

`tap_smell` should decay over time. Recent repeated taps strengthen it; time,
changed task context, or promotion into a compact `MODEL-*`/`FLOW-*` anchor lets
it fade. A hot fact is not automatically a smell: smell is high when repeated
access looks like fixation, missing integration, or reuse without extending the
reasoning branch.

## Creation And Refresh

`MAP-*` cells are durable navigation records. The runtime should not regenerate
the whole cognitive map on every view. It should create and refresh small cells.

`map_refresh` is an explicit mutating runtime operation for 0.4.0. It may be
called from MCP after `lookup`/`map_open` shows stale or missing map coverage,
but normal read-only map views must not silently mutate records.

Current implementation status:

- `tep_runtime.map_refresh` materializes `L1 evidence_patch` cells from
  bounded curiosity prompts.
- CLI exposes this as `map-refresh`; `--dry-run` plans the same mutations
  without writing records.
- MCP exposes `map_refresh` as a direct core-service tool, not a CLI shell-out.
- `map_refresh` returns navigation-only `refresh_triggers` before mutation.
  These triggers tell the agent why refresh is warranted without treating the
  trigger list as proof.
- Matching active cells with the same level, map kind, scope, anchors, and
  source-set fingerprint are updated in place for signals/timestamps.
- Matching active cells with the same anchor key but changed source fingerprint
  are marked `stale`; the new cell links them through `supersedes_refs` and
  `refines_map_refs`.
- Stale-cell triggers create explicit `mark_map_stale` planned actions for
  terminal anchors and source-set fingerprint mismatches. Dry-run shows the
  same stale mutations that apply would perform.
- Existing active `L1/evidence_patch` cells with a shared non-terminal
  `CLM-*`, `MODEL-*`, or `FLOW-*` source can materialize a bounded
  `L2/mechanism_cell`. The L2 cell uses the shared source as `anchor_refs`,
  the source L1 cells as `down_refs`, and updates those L1 cells with `up_refs`.
- `map_view` exposes `hierarchy.up_cells` and `hierarchy.down_cells` so an agent
  can move between abstraction and evidence without treating either as proof.
- The generated `curiosity-map`, `attention-map`, HTML map, and `map-brief`
  remain read-only navigation views.

Refresh flow:

1. Read attention/curiosity/topic/code/telemetry signals as sensor input.
2. Propose candidate `MAP-*` cells with level, map kind, anchors, proof routes,
   and a `source_set_fingerprint`.
3. Find an existing active cell with compatible level, map kind, scope, and
   source set.
4. Update in place only for activity/pressure signals and timestamps.
5. Create a new cell when anchors, source set, proof routes, level, map kind, or
   semantic summary materially changes.
6. Link new semantic cells to older cells through `refines_map_refs` and/or
   `supersedes_refs`.
7. Mark old cells `stale` when they should be retained but de-ranked.

Refresh triggers:

- uncovered map-worthy `CLM-*` records appear. In the implemented 0.4 detector,
  map-worthy claim kinds are empty/default, `factual`, `implied`, and
  `statistical`, and unsupported speculative claim kinds are excluded.
- a covered map-worthy `CLM-*` has a newer `recorded_at`/`updated_at` than the
  active map cell that covers it.
- uncovered or newer active `MODEL-*` or `FLOW-*` records appear. Current
  implemented statuses are `working` and `stable`.
- any anchor record is archived/rejected/superseded/stale, or a `CLM-*` anchor
  moves into lifecycle `archived`, `resolved`, or `historical`. The trigger
  reason is `map_has_terminal_anchor` with per-anchor reasons.
- source set fingerprint changes. The trigger reason is
  `source_set_fingerprint_changed` and reports the expected and actual
  fingerprints.
- linked `CLM(meta_aggregated)` becomes stale.
- current task/WCTX is closed or forked
- explicit user, curator, or agent request

Shared vs personal state:

- `MAP-*` records are shared canonical navigation cells.
- The agent's current position, inspected/dismissed/deferred candidates, and
  allowed map moves live in an owner-bound `WCTX-*` map session.
- Current implementation stores the default personal session at
  `WCTX.map_sessions.default` and returns it as `WCTX-*#map-session`.
- `map_sessions` is covered by the WCTX owner signature so map position,
  visited cells, and checkpoints cannot be silently changed without detection.
- Reusing another agent's WCTX session requires the normal fork/adopt flow; it
  must not silently transfer personal map state.

## Lifecycle

`MAP-*` records may be:

- `active`: usable navigation cell.
- `stale`: retained but de-ranked because anchors or source set changed.
- `archived`: retained for retrospective only.

Staleness triggers:

- any anchor record is archived/rejected/superseded/stale, or a `CLM-*` anchor
  moves into lifecycle `archived`, `resolved`, or `historical`
- source set fingerprint changes
- linked `CLM(meta_aggregated)` becomes stale
- map-relevant `CLM-*`, `MODEL-*`, or `FLOW-*` records appear or change near the
  cell's anchors
- current task/WCTX is closed
- explicit user or curator decision

Map refresh should normally create a new `MAP-*` and link it through
`refines_map_refs` or `supersedes_refs` rather than mutating the old cell in
place. In-place updates are reserved for pressure/activity signal changes that
do not alter the cell's meaning.

## Implementation Notes For 0.4.0

Slice order:

1. Define `MAP-*` schema and validators. Done for `record_version=1`.
2. Add record loading/search support for `record_type=map`. Done.
3. Add lookup support for returning existing `MAP-*` cells. Done through the
   navigation-only `lookup.map_navigation` block and map route hints.
4. Add explicit `map_refresh` service for materializing and updating `L1` cells
   from current attention/curiosity output. Done for bounded `evidence_patch`
   cells.
5. Add map session state in owner-bound `WCTX-*` plus read-only/mutating
   `map_open`/`map_view`/`map_move`/`map_drilldown`/`map_checkpoint` behavior.
   Done for the default owner-bound WCTX session: `map_open`, `map_move`, and
   `map_checkpoint` mutate WCTX session state; `map_view` and `map_drilldown`
   are read-only navigation.
6. Add `L2` creation from `MAP-L1`, `CLM(meta_aggregated)`, MODEL/FLOW, and
   tensions.
7. Add `L3` creation from `MAP-L2`, TASK, WCTX, PLAN, REASON, OPEN, and PRP.
8. Add HTML/visual projection only after MCP/text projections are stable.

Do not start with a full visual map. Start with small, typed `MAP-*` cells that
make lookup cheaper and reasoning more structured.
