# Curiosity Map And Visual Thinking

## Responsibility

This mechanic gives agents compact spatial/topological navigation over TEP
records. For 0.4.0, curiosity map is a cognitive fact map: it gives the agent a
bounded mental picture of the current fact space without exposing raw context
files.

Maps are not proof. They help choose inspection order.

## Map Graph

The canonical generated graph shape is `tep.map_graph.v1`.

It should expose nodes, edges, clusters, cluster layers, probes, relation
weights, and topology analysis.

`tep.map_graph.v1` is a sensor/projection layer, not durable map memory. The
0.4.0 durable memory layer is `MAP-*`: one canonical navigation record for one
cognitive map cell at one abstraction level. `curiosity-map` may propose or
rank cells, but `map_refresh` materializes and updates them.

## Clusters

Cluster layers should stay explicit:

- topic: lexical/statistical similarity
- topology: established record links
- scope: workspace/project/task/WCTX
- code: CIX package/module/function/class grouping
- activity: heat/decay
- probe: candidate, missing, rejected, and unknown links

Topology clusters should be based on established links, not candidate links.

## Curiosity Signals

Useful probes come from cold zones, bridge pressure, repeated access to hot
records, candidate links with no confirmed absence, contradictions between
expected and observed flow, and topology islands that should maybe connect.

Absence of evidence is not evidence of absence. The map should represent known
missing/rejected links separately from unknown links.

0.4.0 map views should separate these signal classes:

- `anchor_facts`: primary facts or integrated MODEL/FLOW records relevant to the
  current task.
- `ignored_but_relevant`: connected facts with low recent use, low tap history,
  or no presence in the current REASON branch.
- `bridge_facts`: facts connecting the current zone to another topology, topic,
  code, or scope zone.
- `tension_facts`: stale, resolved, runtime, tentative, conflict, gap, or
  hypothesis signals that may change the interpretation.
- `tap_smell`: decaying repeated-access pressure. Many recent taps strengthen
  the smell; time and changed context let it fade.
- `neglect_pressure`: a cold connected fact may deserve inspection because it
  has been ignored despite graph relevance.
- `inquiry_pressure`: a fact has many hypotheses, tentative branches, unresolved
  probes, dismissed probes, or aggregate/meta claims around it.
- `promotion_pressure`: a hot supported fact or fact cluster may deserve
  MODEL/FLOW promotion instead of repeated rediscovery.

`tap_smell` is not simple popularity. A frequently used fact can be healthy if
it is the right compact MODEL/FLOW anchor. Smell rises when repeated access
looks like fixation, missing integration, or reuse of the same facts in new
reasoning without extension.

Generated `CLM-* plane=meta` aggregate claims can summarize hypothesis clouds or
repeated probes around a fact. They are map summaries and route hints. They do
not become object-level proof without drill-down into underlying support.

Every curiosity candidate should explain `why_suggested`, expected value, and
the proof route needed before the agent may rely on it.

## Durable MAP Cells

`MAP-*` cells should be created and refreshed incrementally rather than
regenerating a whole project map for every view.

Levels:

- `MAP-L1`: evidence patch near CLM/SRC/RUN/FILE/ART/CIX anchors.
- `MAP-L2`: mechanism, pattern, risk, policy, workflow, or code-area cell over
  L1 cells, meta CLM, MODEL, and FLOW anchors.
- `MAP-L3`: task situation or strategy cell over L2 cells, TASK, WCTX, PLAN,
  REASON, OPEN, and PRP anchors.

`MAP-*` records are shared navigation cells. Agent-specific position, inspected
candidates, dismissed candidates, deferred candidates, and allowed moves belong
in an owner-bound `WCTX-*` map session.

`map_refresh` is explicit and mutating in 0.4.0. It should update pressure and
activity signals in place when a cell meaning is unchanged. It should create a
new `MAP-*` when anchors, source set, proof routes, level, map kind, or semantic
summary materially changes, linking the new cell to older ones with
`refines_map_refs` or `supersedes_refs`.

Refresh is triggered by stale anchors, source-set fingerprint changes, new
map-relevant CLM records, new or changed MODEL/FLOW records, task/WCTX closure
or fork, and explicit user/curator/agent request.

## Map Sessions

Agent map navigation should be session-based:

```text
map_open -> map_view -> map_move -> map_drilldown -> map_checkpoint

optional explicit mutation:
map_refresh
```

The session state belongs in `WCTX-*`, not truth records. It may track:

- current zone
- suggested candidates
- inspected candidates
- candidates used in a chain
- dismissed candidates
- deferred candidates
- reason refs or aggregate refs sampled for inquiry pressure

Dismissed and deferred candidates are navigation memory. They do not create
`OPEN-*`, `DEBT-*`, `PRP-*`, or truth records automatically. A candidate can
return later only when new evidence, a new bridge, a new task, or changed tap
smell makes the route valuable again.

`map_open`, `map_view`, `map_move`, `map_drilldown`, and `map_checkpoint` are
session/view operations. `map_refresh` is the only normal map operation in this
loop that mutates durable `MAP-*` records.

## Views

Agents should normally use bounded MCP map sessions and compact map views such
as `map-brief`, `curiosity-map` compact, `probe-pack`, and attention
diagram/map. The agent should move through allowed map moves, not read the full
graph dump.

HTML visualization is optional for 0.4.0. If implemented, it should use the same
map graph object and support navigation, cluster grouping, filtering, and stable
layout.

## Coherence Notes

- Lookup can use map output as navigation but must still validate proof chains.
- Curator can use map probes to select record pools.
- Telemetry heat feeds activity layer.
- Map drill-down returns lookup/record-detail/chain routes, not proof.
- Candidate links do not form topology clusters.
- Map sessions may persist into WCTX so the next agent can continue from the
  same zone.

## Known Gaps

- Candidate link generation needs quality controls to avoid curiosity noise.
- The formula for heat/tap decay should be documented and testable.
- Tap smell and neglect pressure need default half-life values and deterministic
  tests.
- HTML map usability, if implemented, should be regression-tested enough to
  avoid unstable force-layout behavior returning.
