# TEP Map Graph v1

`TEP Map Graph v1` is the canonical generated graph shape behind attention and
curiosity map views.

It is not canonical memory and it is not proof. Canonical truth remains
`SRC-* -> CLM-*`. Map graph output is a navigation artifact that helps agents
choose what to inspect next.

For TEP 0.4.0, durable cognitive map memory is represented by `MAP-*` records,
not by this generated graph payload. A `MAP-*` record is one shared navigation
cell at exactly one abstraction level. `tep.map_graph.v1` remains the generated
projection used by `curiosity-map`, `map-brief`, HTML, export, and algorithms.

## Design Goals

- Keep one typed graph contract for agent, HTML, Mermaid, DOT/GraphML export,
  and future NetworkX-style algorithms.
- Keep visual views as projections, not data sources.
- Make cluster layers explicit so semantic/topic clustering and graph-topology
  clustering do not get confused.
- Let agents reason about dense islands, bridges, cold zones, candidate links,
  and missing links without reading raw record files.
- Support cognitive fact-map sessions that surface anchor facts, neglected
  relevant facts, tap smell, and inquiry pressure without turning map output
  into proof.

## Current Shape

Curiosity map payloads expose:

```json
{
  "map_graph_version": "tep.map_graph.v1",
  "map_graph": {
    "format": "tep.map_graph.v1",
    "graph_is_proof": false,
    "nodes": [],
    "edges": [],
    "clusters": [],
    "cluster_layers": [],
    "probes": [],
    "relation_weights": {}
  }
}
```

## Nodes

Nodes are selected TEP records projected into a small LLM-readable shape.

```json
{
  "id": "CLM-...",
  "kind": "claim",
  "label": "CLM-...",
  "summary": "short public summary",
  "status": "supported",
  "topic_ref": "topic-0001",
  "scores": {
    "heat": 0.62,
    "tap_count": 2,
    "access_count": 1,
    "tap_smell": 0.1,
    "neglect_pressure": 0.0,
    "inquiry_pressure": 0.0,
    "promotion_pressure": 0.0
  },
  "signals": {
    "anchor_fact": true,
    "ignored_but_relevant": false,
    "bridge_fact": false,
    "tension_fact": false
  },
  "why_suggested": "short route-oriented explanation",
  "not_proof": true
}
```

Scores are navigation signals:

- `tap_smell`: repeated access with decay; high values suggest fixation,
  repeated reuse, or missing MODEL/FLOW integration.
- `neglect_pressure`: graph-relevant but rarely used facts.
- `inquiry_pressure`: hypothesis clouds, tentative branches, unresolved probes,
  dismissed probes, or aggregate/meta claims around the fact.
- `promotion_pressure`: supported hot facts that may deserve MODEL/FLOW
  promotion.

Map nodes may include aggregate/meta claim references that summarize inquiry
pressure. These summaries are route hints. They do not prove object-level
truth.

## Edges

Edges are typed projections of canonical record references.

```json
{
  "id": "MEDGE-0001",
  "from": "CLM-...",
  "to": "SRC-...",
  "relation": "cites",
  "status": "established",
  "weight": 0.7,
  "fields": ["source_refs"],
  "not_proof": true
}
```

Initial relation weights:

```json
{
  "supports": 1.0,
  "contradicts": 1.0,
  "derived_from": 0.9,
  "depends_on": 0.8,
  "implemented_by": 0.75,
  "cites": 0.7,
  "same_topic": 0.35,
  "mentions": 0.2,
  "candidate_link": 0.1,
  "no_known_link": 0.0,
  "rejected_link": -0.2
}
```

`candidate_link` must not glue established topology clusters. It is a curiosity
signal only.

## Cluster Layers

Map graph clustering is multi-layer. A node may belong to multiple clusters.

Current layers:

- `topic`: lexical topic-index membership.
- `topology`: connected components over established weighted record links.

Planned layers:

- `scope`: workspace/project/task/WCTX grouping.
- `code`: CIX package/module/function/class grouping.
- `activity`: heat/decay and repeated-access grouping.
- `probe`: candidate, rejected, unknown, and explicitly absent link areas.
- `inquiry`: hypothesis clouds, tentative branches, and repeated/dismissed
  probes around a fact.

## Topology Clusters

Topology clusters answer: "Which records are actually tightly connected by
TEP graph links?"

They are not semantic similarity clusters. A topology cluster may include
records with different text topics if the records are connected through
canonical references.

Current implementation:

- algorithm: `connected_components`
- includes relations: `supports`, `contradicts`, `derived_from`, `depends_on`,
  `implemented_by`, `cites`
- excludes relations: `candidate_link`, `no_known_link`, `rejected_link`
- minimum weight: `0.35`

Example:

```json
{
  "id": "MCL-topology-001",
  "kind": "topology",
  "label": "Topology component 1",
  "algorithm": "connected_components",
  "status": "generated",
  "node_refs": ["CLM-...", "SRC-..."],
  "edge_refs": ["MEDGE-0001"],
  "scores": {
    "density": 0.66,
    "heat": 1.2,
    "bridge_score": 0.0
  },
  "boundary": {
    "internal_edge_refs": ["MEDGE-0001"],
    "external_edge_refs": [],
    "bridge_node_refs": [],
    "orphan_node_refs": []
  },
  "not_proof": true
}
```

## Agent View

Agents should not read the full map graph unless needed. Prefer `map-brief`,
which is a compact projection over `tep.map_graph.v1`.

- cluster layers
- dense topology components
- established bridges
- candidate probes
- cold zones
- anchor facts
- ignored but relevant facts
- tap smell and neglect pressure
- inquiry pressure
- recommended next commands

The graph helps choose inspection order. It does not justify conclusions,
actions, or permission requests.

0.4.0 map navigation should be session-based:

```text
map_open -> map_view -> map_move -> map_drilldown -> map_checkpoint
```

Map session state is stored in `WCTX-*` operational context. A session may track
the current zone, allowed moves, suggested candidates, inspected candidates,
chain-used candidates, dismissed candidates, deferred candidates, and sampled
`REASON-*` or aggregate `CLM-*` refs used to explain inquiry pressure.

`MAP-*` records are shared; the WCTX session is personal to the owning agent.
Another agent must fork/adopt WCTX before reusing personal map position or
checkpoint state.

`map_refresh` is the explicit mutating operation that materializes or updates
durable `MAP-*` cells from map graph, attention, topic, code, telemetry, and
curiosity signals. Read-only map views should not silently create or rewrite
`MAP-*` records.

Refresh should update pressure/activity signals in place when the cell meaning
is unchanged. It should create a new `MAP-*` when anchors, source set, proof
routes, level, map kind, or summary changes materially. New map-relevant
`CLM-*` records and new or changed `MODEL-*`/`FLOW-*` records are refresh
triggers.

`map_drilldown` returns navigation routes toward proof-capable records, such as
`lookup`, `record_detail`, `linked_records`, `augment_chain`, and
`validate_chain`. For higher-level `MAP-*` cells it may unfold bounded
`down_refs` to lower-level map cells before reaching proof-capable records. It
does not return proof.

`map-brief` currently reports:

- topology islands
- bridge pressure from bridge nodes and bridge edges
- candidate probes
- cold zones
- recommended inspection commands

`curiosity-map --html` renders from this same `map_graph` object. The HTML
view must treat `map_graph.nodes`, `map_graph.edges`, `map_graph.clusters`, and
`map_graph.topology_analysis` as the source for topology, bridge, and probe
controls instead of deriving a separate visual model from legacy fields.

`record-link` feedback claims produce generated `related` map edges between the
two reviewed support claims. These edges make resolved curiosity links visible
in topology islands while preserving the proof boundary: the generated map edge
is navigation-only and points back to the source-backed link claim.

Use `curiosity-map --format json` only when a caller needs the full typed graph
payload for visualization, export, or algorithm debugging.
