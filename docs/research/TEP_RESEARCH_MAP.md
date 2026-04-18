# TEP Research Map

This document maps external methods, algorithms, and tools that can support future TEP development.

The goal is pragmatic: reduce agent token pressure and improve mechanical checking without letting generated analysis replace canonical evidence.

For deeper academic tracks around heuristic reasoning, source corroboration,
formal slices, argumentation, and belief revision, see
`docs/research/TEP_ACADEMIC_RESEARCH_PLAN.md`.

## Adoption Rule

Every optional backend must fit this rule:

```text
external method -> candidate/navigation signal -> canonical record review -> durable action
```

No solver, topic model, vector index, static analyzer, or classifier can directly change claim truth status.

## Formal Logic And SMT

### Z3

Z3 is a practical SMT solver candidate for optional consistency checks.

Useful for TEP:

- boolean contradictions
- exact functional-value conflicts
- typed symbolic constraints
- simple implications
- unsat-core extraction mapped back to `CLM-*`
- bounded consistency snapshots

Not suitable as the whole truth model:

- natural language claims still need source interpretation
- missing predicates can hide contradictions
- over-broad symbols create false pressure
- SMT snapshots can become hard to explain if unconstrained

Recommended use:

- keep structural checks as baseline
- add Z3 as optional backend behind settings
- limit symbol/rule counts
- use timeouts
- report claim ids and logic refs in unsat cores
- require user/source review before status changes

References:

- Z3 project and Python API: https://github.com/Z3Prover/z3
- Z3 Python API documentation: https://z3prover.github.io/api/html/namespacez3py.html
- SMT-LIB standard and benchmark ecosystem: https://smt-lib.org/

### SMT-LIB

SMT-LIB is useful as an interchange/reference format.

Potential use:

- export a TEP logic snapshot for debugging
- preserve solver-independent test fixtures
- compare Z3 behavior against other SMT solvers later

Do not expose raw SMT-LIB as the primary authoring format for agents. Agents should author source-backed claim logic, and the plugin should project it.

## Datalog And Deductive Databases

Datalog is a strong candidate for graph-like closure:

- transitive dependencies
- model/flow reachability
- impact graph expansion
- stale propagation
- permission/restriction scope
- code-index relationship closure
- derived candidate links

Souffle is especially relevant because it is designed for Datalog static-analysis workloads and separates facts from programs.

Recommended use:

- keep Datalog optional
- start with generated fact files from canonical records
- use it for navigation/impact, not truth status
- prefer Datalog over SMT for recursive graph queries

References:

- Souffle Datalog documentation: https://souffle-lang.github.io/
- Souffle execution and fact input model: https://souffle-lang.github.io/execute
- pyDatalog reference for a Python-embedded option: https://sites.google.com/site/pydatalog/reference

## Graph Algorithms

TEP is naturally graph-shaped:

- records are nodes
- refs are typed edges
- project/task scopes are filters
- fallback lifecycle changes affect reachable support
- rollback and impact reports are graph traversals

NetworkX is useful for early implementation:

- connected components
- reachability
- shortest paths
- centrality/importance hints
- cycle detection
- dependency impact

Recommended use:

- use simple local graph construction first
- keep outputs explainable as record ids and edge fields
- avoid graph metrics as proof

Reference:

- NetworkX algorithms: https://networkx.org/documentation/stable/reference/algorithms/index.html

## Retrieval And Search

### Lexical Search

Baseline TEP should keep cheap lexical search.

Useful methods:

- exact id lookup
- keyword search over selected fields
- TF-IDF
- BM25
- field-weighted scoring

Lexical search is strong for record ids, file paths, symbols, function names, exact user phrases, and technical terms.

References:

- scikit-learn text feature extraction and TF-IDF: https://scikit-learn.org/stable/modules/feature_extraction.html
- Elasticsearch BM25 reference: https://www.elastic.co/guide/en/elasticsearch/reference/current/index-modules-similarity.html

### Dense And Hybrid Retrieval

Dense vector search may help with paraphrases and conceptual similarity, but it can miss exact identifiers.

TEP should prefer hybrid retrieval when semantic search is introduced:

- lexical prefilter for ids and exact terms
- vector retrieval for paraphrases
- optional reranking
- canonical record inspection before citation

Recommended use:

- begin with lexical/topic search
- introduce embeddings only behind settings
- cache embeddings by record hash
- expose candidate ids, scores, and method
- never cite vector similarity as proof

Reference:

- Sentence-BERT paper: https://arxiv.org/abs/1908.10084

## Topic Modeling And Statistical Prefilters

Topic methods can group records and reduce broad-search token cost.

Candidate methods:

- TF-IDF terms for cheap lexical topics
- NMF for additive, often interpretable topics
- LDA for probabilistic topic mixtures
- clustering over sparse or dense vectors

TEP use cases:

- topic neighborhoods for records
- candidate contradiction pairs
- cleanup clusters
- duplicate-like claims
- guideline applicability hints
- model/flow grouping suggestions

Recommended use:

- keep lexical as default
- add NMF as optional backend first
- make rebuild manual or explicit
- store model metadata and corpus fingerprint
- label results as generated prefilter data

References:

- scikit-learn NMF/LDA topic extraction example: https://scikit-learn.org/stable/auto_examples/applications/plot_topics_extraction_with_nmf_lda.html
- scikit-learn LatentDirichletAllocation API: https://scikit-learn.org/stable/modules/generated/sklearn.decomposition.LatentDirichletAllocation.html

## Attention Maps, Tap Decay, And Curiosity Signals

Topic grouping becomes more useful when combined with lightweight activity
telemetry.

TEP should eventually support an attention map over records and generated topic
clusters:

- records are canonical inputs
- topic clusters are generated navigation groups
- low-dimensional coordinates are visualization/navigation hints
- tap events describe how agents used or inspected records
- decay makes old activity fade unless refreshed by current work

A tap is not evidence. It is an activity event such as:

- retrieved
- opened
- cited
- decisive
- updated
- challenged
- contradicted

Different tap kinds should feed different attention layers. A single "hotness"
score would blur too many meanings.

Useful derived layers:

- support heat: records repeatedly used as support
- conflict heat: records repeatedly challenged or contradicted
- uncertainty heat: records repeatedly inspected without resolution
- edit heat: records connected to recent code/test changes
- stale heat: important records whose support has not been refreshed recently
- cold-zone signal: semantically relevant clusters with unexpectedly low tap
  activity
- bridge signal: reasoning chains whose linked records cross cluster boundaries

Recommended conceptual formula:

```text
tap_score(record, layer) =
  sum(weight(kind, intent, layer) * exp(-age / half_life(layer)))
```

This should be computed from an append-only tap log or generated activity
summary, not by mutating canonical `CLM-*` truth fields.

The most important research direction is not merely "show hot clusters".
The system should also make the agent curious about:

- relevant clusters that are rarely tapped
- old but high-impact records whose activity has decayed
- clusters that have many nearby claims but few current sources
- reasoning chains that unexpectedly move from one cluster to another
- cross-cluster bridges that might indicate hidden dependencies, scope drift,
  missing model/flow links, or a useful abstraction boundary

This matters because a naive heat map creates a rich-get-richer failure mode:
the agent repeatedly reads already-hot records and neglects cold but relevant
areas.

Mitigation:

- mix hot records with cold semantically-near records during retrieval
- surface "why is this zone cold?" candidates in curiosity reports
- surface "why did this chain cross clusters?" candidates in reasoning review
- keep coordinates and clusters rebuildable from canonical records
- never treat tap frequency, cluster membership, or coordinate distance as proof

Controlled presentation can also induce useful curiosity.
The agent does not always need the whole map at once.
A generated attention view may intentionally show a bounded viewport plus
frontier cues:

- visible clusters relevant to the current task
- collapsed neighboring clusters
- cold-but-near zones
- unexplained gaps where an expected link is not established
- cross-cluster bridge candidates
- explicit "expand here" prompts

This is an attention-budget mechanism, not a dark pattern.
The view must disclose when it is partial and must never hide active
restrictions, conflicts, safety-relevant records, or proof needed for a
commitment.

Attention maps should also distinguish link states:

- `established`: a canonical record asserts or uses the link with source support
- `candidate`: generated similarity, topic overlap, code-index relation, or
  reasoning-chain bridge suggests a link worth checking
- `expected_missing`: a model, flow, task, or cluster shape suggests a link
  should exist, but no supported link is currently known
- `tested_absent`: a bounded search or inspection found no link under an
  explicit scope, time, corpus fingerprint, and method
- `rejected`: a previous candidate link was checked and weakened or rejected by
  canonical support
- `unknown`: no relation is known and no absence check has been performed

`expected_missing` and `unknown` are not evidence of absence.
`tested_absent` is only bounded evidence about a specific search method and
scope; it is not a universal proof that no relationship exists.

The attention map may also run bounded stochastic curiosity probes.
When a reasoning path crosses several clusters, the system can sample claim
pairs or small claim paths that are:

- near enough by topic, code, model, flow, or reasoning-chain context to be
  plausible
- separated enough to avoid obvious duplicate lookup
- not already `established`
- not already `rejected`
- not covered by a fresh compatible `tested_absent` result
- relevant to the current task, an active model/flow, or a reusable domain gap

The point is to imitate curiosity by asking the agent to check whether a
relationship exists.
The probe must be framed as a question, not as a suspicion:

```text
Check whether CLM-A and CLM-B are related.
Known state: no established link; no fresh tested_absent result.
Acceptable outcomes: established, candidate, tested_absent, rejected, unknown.
```

This can discover hidden bridges without forcing all-pairs comparison.
It also teaches the agent that the absence of link information is itself an
object of review, while preserving the rule that missing evidence is not
evidence of absence.

Recommended constraints:

- use a per-task probe budget
- make stochastic sampling seedable and reproducible
- mix deterministic high-value probes with a small random exploration fraction
- prefer cheap first checks before source-heavy investigation
- record the reason for each probe and the generated link state after review
- demote or suppress repeatedly unproductive probe regions
- never let a sampled pair become evidence until canonical records support the
  resulting relationship or absence claim

Potential generated storage:

```text
.codex_context/attention_index/records.json
.codex_context/attention_index/clusters.json
.codex_context/attention_index/bridges.json
.codex_context/attention_index/cold_zones.json
.codex_context/attention_index/link_states.json
.codex_context/attention_index/probes.json
.codex_context/activity/taps.jsonl
```

Potential commands:

- `tap-record --record CLM-* --kind cited --intent support`
- `attention-map --scope current-task`
- `hot-zones --scope current-project`
- `cold-zones --scope current-task`
- `cluster-bridges --record CLM-*`
- `link-gaps --scope current-task`
- `curiosity-probes --scope current-task --budget N`
- `records-near --record CLM-* --method topic|hybrid`

All outputs are candidate/navigation data.
They may guide search, curiosity, cleanup, model review, and flow review.
They must not promote claims, resolve contradictions, or justify actions without
canonical record inspection.

## Natural Language Inference

NLI can be useful for contradiction candidate prefiltering over prose claims.

Potential value:

- detect likely entailment/contradiction between two claim statements
- find unsupported paraphrase duplicates
- flag claims that should receive structured `comparison` or `CLM.logic`

Risks:

- false positives on domain-specific language
- weak temporal/scope handling
- brittle behavior on code/test details
- difficult audit trail if the model is opaque

Recommended use:

- optional candidate scorer only
- require canonical source inspection
- store model/version and input refs if results are persisted
- never let NLI directly change claim status

Reference:

- NLI contradiction detection background example: https://arxiv.org/abs/2210.10434

## Code Intelligence

### Python AST

Python `ast` is the best first layer for Python files.

Useful metadata:

- imports
- classes
- functions
- decorators
- call-like references
- docstrings
- line spans

It is cheap, dependency-free, and deterministic.

### Tree-sitter

Tree-sitter is a strong future parser layer for multi-language code indexing.

Useful for TEP:

- language-agnostic concrete syntax trees
- incremental parsing
- symbol/code-part indexing
- smaller CIX targets for functions/classes
- broader language coverage than Python `ast`

References:

- Tree-sitter project: https://github.com/tree-sitter/tree-sitter
- Tree-sitter documentation: https://tree-sitter.github.io/tree-sitter/

### Semgrep

Semgrep is useful for pattern-based rules and local smells.

Potential TEP use:

- executable guideline checks
- code smell annotations
- risky pattern detection
- review scope generation

References:

- Semgrep docs: https://semgrep.dev/docs/
- Semgrep rule running docs: https://semgrep.dev/docs/running-rules/

### CodeQL

CodeQL is a heavier reference for semantic code databases and queryable code facts.

Potential TEP use:

- future deep static-analysis backend
- reference design for "code as data"
- query metadata and result documentation practices

Risks:

- heavy setup
- licensing/usage constraints depending on project context
- overkill for baseline plugin operation

References:

- CodeQL documentation: https://codeql.github.com/docs/
- CodeQL overview: https://codeql.github.com/docs/codeql-overview/about-codeql/

## Provenance, Knowledge Graphs, RDF, And OWL

TEP overlaps with provenance and knowledge-graph systems, but it should stay smaller and more operational.

Useful ideas:

- typed nodes and edges
- explicit provenance
- lifecycle and versioning
- schema validation
- graph traversal
- ontology-like symbol discipline

Risks:

- RDF/OWL can add heavy abstraction before TEP needs it
- formal ontologies can distract from source-backed operational memory
- agent workflows need simple commands more than general semantic-web power

Recommended use:

- borrow provenance and typed-edge ideas
- do not migrate canonical storage to RDF/OWL in the near term
- keep JSON records as the human-auditable source of truth

References:

- W3C RDF/OWL recommendations overview: https://www.w3.org/news/2004/rdf-and-owl-are-w3c-recommendations/
- OWL guide: https://www.w3.org/TR/owl-guide/

## Cleanup Research Direction

Cleanup should combine deterministic checks and optional ranking.

Deterministic signals:

- broken refs
- fallback claim used by active model/flow/action
- stale CIX sha256
- duplicate ids
- active hypothesis with resolved claim
- old task still active
- completed plan still in backlog
- debt with no evidence refs

Statistical/heuristic signals:

- near-duplicate claims
- noisy high-degree records
- repeated stale topics
- old claims frequently retrieved but never used
- guideline conflicts
- orphan proposals

Cleanup should first report candidates. Mutation should be explicit and auditable.

## Academic Research Tracks

If deeper research is needed, split it by component:

- reasoning discipline for coding agents
- formal model construction from natural-language facts
- contradiction detection over source-backed claims
- hybrid retrieval for persistent agent memory
- code knowledge graphs through Tree-sitter/MCP
- provenance and lifecycle design for agent memory
- cleanup/staleness ranking for persistent context stores

Each track should produce:

- problem statement
- candidate algorithms
- failure modes
- TEP applicability
- testable MVP
- reasons not to adopt
