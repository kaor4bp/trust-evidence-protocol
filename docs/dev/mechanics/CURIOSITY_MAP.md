# Curiosity Map And Visual Thinking

## Responsibility

This mechanic gives agents compact spatial/topological navigation over TEP
records.

Maps are not proof. They help choose inspection order.

## Map Graph

The canonical generated graph shape is `tep.map_graph.v1`.

It should expose nodes, edges, clusters, cluster layers, probes, relation
weights, and topology analysis.

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

## Views

Agents should normally use compact map views such as `map-brief`,
`curiosity-map` compact, `probe-pack`, and attention diagram/map.

HTML visualization should use the same map graph object and support navigation,
cluster grouping, filtering, and stable layout.

## Coherence Notes

- Lookup can use map output as navigation but must still validate proof chains.
- Curator can use map probes to select record pools.
- Telemetry heat feeds activity layer.

## Known Gaps

- Candidate link generation needs quality controls to avoid curiosity noise.
- The formula for heat/tap decay should be documented and testable.
- HTML map usability should be regression-tested enough to avoid unstable
  force-layout behavior returning.

