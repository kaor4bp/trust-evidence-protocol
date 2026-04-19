# Anti-NIH Tooling Round

Last reviewed: 2026-04-19.

This document exists to prevent TEP from rebuilding mature tooling by accident.
TEP should own evidence semantics, scoped records, proof boundaries, workflow
guardrails, and agent-facing context routes. It should integrate existing tools
for parsing, indexing, validation, extraction, and reasoning whenever they can
serve as bounded backends.

Rule:

```text
Before implementing a new analyzer, parser, graph algorithm, extractor, or
validator inside TEP, check this document and prefer an adapter/spike unless
the feature is required for the no-dependency baseline.
```

## Ownership Boundary

TEP owns:

- canonical record types: `SRC-*`, `CLM-*`, `GLD-*`, `PRM-*`, `RST-*`,
  `PRP-*`, `TASK-*`, `WCTX-*`, `MODEL-*`, `FLOW-*`, `PLN-*`, `DEBT-*`, and
  generated/navigation `CIX-*`
- durable provenance and source critique
- claim status and lifecycle semantics
- scoped workspace/project/task policy
- proof-chain validity rules
- hydration, preflight, and agent route guidance
- "navigation output is not proof" enforcement
- telemetry over access patterns and raw-record reads

External tools may provide:

- code parsing, code search, symbol lookup, references, impact candidates
- fact extraction candidates
- entity resolution candidates
- graph constraints and validation reports
- rule-based derivation and dependency closure
- SMT consistency checks
- pattern/static-analysis findings
- vector or graph retrieval candidates

External tool output must be labeled as one of:

- `navigation_candidate`
- `extraction_candidate`
- `validation_candidate`
- `conflict_candidate`
- `derived_candidate`
- `smell_candidate`

It must not become `SRC-*` support, `CLM-*` support, action justification, or
permission by itself.

## Adapter Interface Pattern

Every optional backend should fit this shape:

```text
Backend.status(root, settings) -> availability, version, freshness, warnings
Backend.refresh(root, paths, settings) -> refresh diagnostics
Backend.query(request, settings) -> bounded candidates with provenance to the tool run
Backend.explain(candidate, settings) -> compact reason, source refs, confidence caveats
```

Adapter rules:

- default to disabled or `builtin`
- fail softly with a setup hint
- expose deterministic fake backends for unit tests
- record telemetry separately from raw file reads and MCP/CLI TEP lookups
- keep output bounded by explicit limits
- never mutate canonical records directly
- import into TEP only through normal TEP commands
- keep settings workspace/project-scoped where backend behavior can differ

## Code Intelligence

Current TEP baseline:

- Python `ast` extraction
- JS/TS regex extraction
- Markdown heading/link/code-block outline extraction
- `CIX-*` entries with manual links, annotations, smells, freshness, and
  protocol semantics

Do not expand this baseline into a full code-intelligence engine unless the
feature is small, deterministic, and required without dependencies.

### Preferred Integration Candidates

| Tool | Use Instead Of Writing | Best TEP Role | Notes |
| --- | --- | --- | --- |
| [Serena](https://github.com/oraios/serena) | LSP-backed symbol search, references, semantic navigation, agent-facing code tools | `code_intelligence.serena` backend | Strong first spike. MCP-native and uses language servers or JetBrains backend. |
| [CocoIndex code indexing](https://cocoindex.io/docs/examples/code_index) / [cocoindex-code](https://github.com/cocoindex-io/cocoindex-code) | Tree-sitter chunking, semantic/vector code search, incremental indexing | `code_intelligence.cocoindex` backend | Good for token reduction and semantic search. Keep CIX as TEP-owned projection. |
| [Codebase-Memory MCP](https://arxiv.org/abs/2603.27277) | Persistent Tree-sitter code graph, call chains, impact/community discovery | `code_intelligence.graph` backend | Promising for curiosity/attention maps; treat as experimental until stability is proven. |
| [Semgrep](https://github.com/semgrep/semgrep) / [OpenGrep](https://github.com/opengrep/opengrep) | Pattern-based static analysis, security smells, convention checks | `static_analysis.patterns` backend | Feed `CIX` smell candidates or `PRP-*` proposals, not proof. |
| [CodeQL](https://codeql.github.com/docs/index.html) | Deep static/security/data-flow queries | `static_analysis.codeql` backend | Heavy optional backend, not baseline. |
| [Universal Ctags](https://github.com/universal-ctags/ctags) | Cheap multi-language symbol extraction | `code_intelligence.ctags` fallback | Useful fallback when LSP/Tree-sitter backends are unavailable. |

### Decision

Use TEP's builtin analyzers only as the light mode.

First integration priority:

1. Serena for LSP-backed semantic code navigation.
2. CocoIndex for semantic/vector code retrieval and incremental indexing.
3. Semgrep/OpenGrep for guideline/smell candidates.
4. Codebase-Memory for graph/curiosity/impact experiments.
5. CodeQL for heavyweight security/data-flow checks.

## Fact Storage And Validation

Current TEP baseline:

- JSON canonical records
- strict validation
- source-backed `CLM-*`
- optional `CLM.logic`
- comparison blocks
- generated `logic_index`, `topic_index`, and review reports

Do not build a full semantic-web engine or Datalog engine directly into TEP.
Build projections/adapters.

### Preferred Integration Candidates

| Tool | Use Instead Of Writing | Best TEP Role | Notes |
| --- | --- | --- | --- |
| [RDFLib](https://github.com/RDFLib/rdflib) + [pySHACL](https://github.com/RDFLib/pySHACL) | RDF graph model, SHACL validation, shape reports | `fact_validation.rdf_shacl` backend | Best first fact-layer integration. Python-native and deterministic. |
| [Apache Jena SHACL](https://jena.apache.org/documentation/shacl/) / [Jena inference](https://jena.apache.org/documentation/inference/index.html) | Heavier RDF validation and reasoning | `fact_validation.jena` backend | Consider only when Python stack is insufficient. |
| [Eclipse RDF4J SHACL](https://rdf4j.org/documentation/programming/shacl/) | Java RDF/SHACL storage and validation | `fact_validation.rdf4j` backend | Alternative to Jena in Java deployments. |
| [Neo4j neosemantics](https://neo4j.com/labs/neosemantics-rdf/) | RDF/SHACL over Neo4j graph DB | `graph_store.neo4j_n10s` backend | Useful for graph exploration, but not a TEP baseline dependency. |

### Decision

Use RDF/SHACL as a validation projection:

```text
TEP records -> RDF quads -> SHACL shapes -> validation report -> TEP review candidates
```

Do not replace `CLM-*` with RDF triples. TEP needs scoped provenance, source
critique, lifecycle, and proof boundary semantics that RDF triples alone do not
carry.

## Rule-Based Derivation And Dependency Closure

TEP needs mechanical help for:

- "which records support this conclusion?"
- "what breaks if this claim is rejected/resolved/archived?"
- "which contradictions are indirect?"
- "which open questions block plans/actions?"
- "which facts are reachable through model/flow/domain links?"

### Preferred Integration Candidates

| Tool | Use Instead Of Writing | Best TEP Role | Notes |
| --- | --- | --- | --- |
| [Soufflé Datalog](https://souffle-lang.github.io/facts) | Datalog fact/rule evaluation, closure, dependency-style derivation | `derivation.datalog` backend | Best fit for relational closure and explainable rule outputs. |
| [Z3](https://github.com/Z3Prover/z3) | SMT consistency checks over typed predicates, booleans, numerics, functional constraints | `consistency.smt` backend | Already aligned with `CLM.logic`; use for bounded consistency checks, not broad graph traversal. |
| [clingo / ASP](https://potassco.org/clingo/) | Answer-set reasoning over alternatives and constraints | `reasoning.asp` experimental backend | Interesting for competing hypotheses, but likely heavier than needed initially. |

### Decision

Use Datalog for graph/dependency closure and Z3 for bounded consistency.
Do not force one solver to do both jobs.

Recommended near-term split:

```text
CLM.logic atoms/rules -> Z3 for local consistency
record/link projections -> Datalog for reachability and dependency closure
```

## Information Extraction From Text

TEP should not require the agent to manually extract every entity, relation, or
candidate claim from raw input when mechanical pre-extraction can reduce token
use.

### Preferred Integration Candidates

| Tool | Use Instead Of Writing | Best TEP Role | Notes |
| --- | --- | --- | --- |
| [GLiNER2](https://github.com/fastino-ai/GLiNER2) | Schema-based entity, relation, classification, and structured extraction | `extraction.gliner2` backend | Good candidate for `INP-*` / `SRC-*` pre-classification. |
| [GLiNER](https://github.com/urchade/GLiNER) | Zero-shot named entity recognition and relation extraction | `extraction.gliner` backend | Lighter entity extraction option. |
| [Stanford OpenIE](https://www-nlp.stanford.edu/software/openie.shtml) | Open relation triples from natural language | `extraction.openie` backend | Useful for candidate triples, but needs review and canonicalization. |
| [spaCy EntityLinker](https://spacy.io/api/entitylinker) | Mention-to-knowledge-base linking | `entity_linking.spacy` backend | Requires a configured KB; useful after TEP has entity vocabulary. |

### Decision

Extraction tools create candidates only:

```text
raw input/source -> extraction candidates -> agent/user review -> SRC/CLM records
```

No extraction backend may silently create supported claims.

## Entity Resolution And Duplicate Detection

TEP will accumulate repeated claims, source mentions, project names, symbols,
services, and user concepts. Duplicate detection should be mechanical where
possible, but merge decisions must remain governed.

### Preferred Integration Candidates

| Tool | Use Instead Of Writing | Best TEP Role | Notes |
| --- | --- | --- | --- |
| [Splink](https://github.com/moj-analytical-services/splink) | Probabilistic record linkage at scale | `entity_resolution.splink` backend | Good for batch duplicate review and explainable match probabilities. |
| [dedupe](https://github.com/dedupeio/dedupe) | ML-backed fuzzy matching, deduplication, entity resolution | `entity_resolution.dedupe` backend | Good Python library for structured records. |
| [Python Record Linkage Toolkit](https://github.com/J535D165/recordlinkage) | Modular record linkage and duplicate detection | `entity_resolution.recordlinkage` backend | Useful deterministic/feature-based baseline. |

### Decision

Entity-resolution output should create review candidates:

```text
possible_duplicate_refs
possibly_same_entity_refs
merge_proposal
do_not_merge_evidence
```

It must not auto-merge canonical records without explicit TEP mutation commands
and review policy.

## Retrieval, Topic, And Attention Maps

Current TEP baseline:

- lexical topic index
- attention map
- curiosity probes
- telemetry over lookups and raw-record reads

Do not build a full vector database or graph database into the baseline.

Candidate integrations:

- SQLite FTS5 for local lexical retrieval if the current JSON scans become too
  slow.
- `sqlite-vec`, LanceDB, Chroma, or Qdrant for optional vector retrieval.
- NetworkX or igraph for local graph metrics if current custom graph code grows.
- DuckDB for analytical scans over records, telemetry, and generated indexes.

Decision:

Use simple JSON/SQLite in baseline. Add vector/graph stores only as optional
analysis backends with explicit settings and telemetry.

## Provenance Verification

TEP's core value depends on whether claims are actually supported by their
quoted sources.

Relevant external reference:

- [ProVe: Automated Provenance Verification of Knowledge Graphs against Textual Sources](https://arxiv.org/abs/2210.14846)

ProVe-style flow:

```text
triple/claim -> verbalization -> source sentence selection -> claim verification
```

Decision:

Do not implement a full ProVe clone now. Use it as a design reference for a
future `provenance_verification` backend:

```text
CLM + SRC quote/artifact -> support/weakening/unsupported candidate report
```

## Testing Requirements For Backends

Every backend integration needs tests before being enabled by default:

- fake backend unit tests
- missing dependency graceful-failure tests
- settings scoping tests
- telemetry event tests
- proof-boundary tests showing backend output cannot support claims directly
- live Docker or local integration tests when the dependency is installed
- migration tests if backend output is imported into existing records/indexes

## Implementation Priorities

Recommended order:

1. Add generic backend settings and status reporting.
2. Add `pySHACL` projection spike for fact validation.
3. Add Serena read-only code navigation spike.
4. Add CocoIndex semantic search spike.
5. Add Datalog projection spike for dependency closure.
6. Add GLiNER2 extraction spike for input/source candidate classification.
7. Add Splink/dedupe duplicate review spike.
8. Add Semgrep/OpenGrep smell/guideline enforcement spike.

This order prioritizes deterministic validation and token reduction before
heavier ML or graph infrastructure.

## Hard No-Go Rules

- Do not introduce a mandatory heavyweight dependency into baseline TEP.
- Do not make external tool output proof.
- Do not let external tools write canonical records directly.
- Do not hide backend failures from the agent; report availability and fallback.
- Do not add a custom parser/extractor/solver without checking this document.
- Do not duplicate a mature tool unless the TEP baseline needs a small,
  deterministic, no-dependency fallback.

