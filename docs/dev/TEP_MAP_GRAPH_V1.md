# TEP Map Graph v1

`TEP Map Graph v1` is the canonical generated graph shape behind attention and
curiosity map views.

It is not canonical memory and it is not proof. Canonical truth remains
`SRC-* -> CLM-*`. Map graph output is a navigation artifact that helps agents
choose what to inspect next.

## Design Goals

- Keep one typed graph contract for agent, HTML, Mermaid, DOT/GraphML export,
  and future NetworkX-style algorithms.
- Keep visual views as projections, not data sources.
- Make cluster layers explicit so semantic/topic clustering and graph-topology
  clustering do not get confused.
- Let agents reason about dense islands, bridges, cold zones, candidate links,
  and missing links without reading raw record files.

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
    "access_count": 1
  },
  "not_proof": true
}
```

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

Agents should not read the full map graph unless needed. Prefer compact views:

- cluster layers
- dense topology components
- established bridges
- candidate probes
- cold zones
- recommended next commands

The graph helps choose inspection order. It does not justify conclusions,
actions, or permission requests.
