# First Integration Stack

Last reviewed: 2026-04-19.

This document defines the first practical backend-integration round after the
anti-NIH tooling review.

Goal:

```text
Reduce agent token waste and custom analyzer growth while preserving TEP's
evidence semantics, scoped records, proof boundaries, and no-dependency
baseline.
```

Non-goals for this round:

- no mandatory heavyweight dependencies
- no replacement of canonical TEP JSON records
- no external tool writes to `records/`
- no auto-supporting `CLM-*` from backend output
- no full vector database or graph database migration
- no large rewrite of existing CIX/CLM storage

## Stack Summary

First round stack:

| Layer | First Backend | Purpose | Status In Round |
| --- | --- | --- | --- |
| Backend framework | Builtin adapter interface | Shared status/query/telemetry/fallback contracts | implemented first slice |
| Fact validation | RDFLib + pySHACL | Validate TEP record graph projections and constraints | fake RDF/SHACL-shaped slice + RDF export started |
| Code navigation | Serena MCP | LSP-backed symbol/references/navigation lookup | spike |
| Semantic code search | CocoIndex / cocoindex-code | Tree-sitter chunks, embeddings, incremental code search | spike after Serena |
| Dependency closure | Builtin projection + Datalog-shaped interface | Prepare for Soufflé without hard dependency | design + fake backend |
| Consistency checking | Existing Z3 policy | Keep bounded `CLM.logic` consistency checks | refine only |
| Extraction | GLiNER2 | Candidate extraction from input/source text | defer to round 2 unless fact validation is stable |
| Entity resolution | Splink or dedupe | Duplicate candidate review | defer to round 2 |
| Pattern analysis | Semgrep/OpenGrep | Smell/guideline candidates | defer to round 2 |

## Baseline Dependency Policy

Baseline TEP remains dependency-light:

- Python standard library for core runtime
- current builtin parsers for light CIX metadata
- optional dependencies installed only for specific backend tests or local use

The plugin must work when no optional backend is installed.

Every backend must expose:

```text
available: true|false
version: string|unknown
mode: disabled|fake|local|docker|mcp|cli
freshness: fresh|stale|unknown
warnings: []
setup_hint: string
```

## Round 1 Work Packages

### WP1: Backend Registry And Settings

Implement a small backend registry before integrating any specific tool.

Settings shape:

```json
{
  "backends": {
    "fact_validation": {
      "backend": "builtin",
      "rdf_shacl": {
        "enabled": false,
        "mode": "local",
        "strict": false
      }
    },
    "code_intelligence": {
      "backend": "builtin",
      "serena": {
        "enabled": false,
        "mode": "mcp",
        "max_results": 12
      },
      "cocoindex": {
        "enabled": false,
        "mode": "cli",
        "max_results": 8,
        "import_into_cix": false
      }
    },
    "derivation": {
      "backend": "builtin",
      "datalog": {
        "enabled": false,
        "mode": "fake"
      }
    }
  }
}
```

Commands:

```text
backend-status [--format text|json]
backend-check --backend <name> [--format text|json]
```

Success criteria:

- missing backend never crashes normal TEP commands
- status output is compact enough for hydration/help
- settings can be scoped by workspace/project through existing settings policy
- telemetry records backend status/query events

Tests:

- default settings select builtin/fake-only behavior
- missing executable/MCP endpoint returns unavailable with setup hint
- backend status is deterministic in unit tests
- backend telemetry does not count as proof

### WP2: RDFLib + pySHACL Fact Validation Spike

Purpose:

```text
Use mature RDF/SHACL validation to check TEP graph projections without replacing
CLM/SRC records.
```

Projection:

```text
SRC-* -> tep:Source
CLM-* -> tep:Claim
CLM.source_refs -> tep:supportedBy
CLM.contradiction_refs -> tep:contradicts
workspace/project/task refs -> tep:scopedTo
record_type -> rdf:type
status/lifecycle -> datatype properties
```

Initial SHACL checks:

- every supported/corroborated `CLM-*` has at least one source ref
- every `CLM.logic.symbol` has `meaning`
- no `corroborated` claim has unresolved `contradiction_refs`
- no proof chain uses `CIX-*`, `GLD-*`, `PRP-*`, `TASK-*`, `WCTX-*`, or generated views as proof
- every current record with workspace support has a valid workspace ref

Commands:

```text
validate-facts --backend rdf-shacl [--format text|json]
export-rdf --format turtle|jsonld --output <path>
```

Current command spelling uses the settings id `rdf_shacl`:

```text
validate-facts --backend rdf_shacl [--format text|json]
```

Output:

```text
validation_candidate
record_ref
shape_ref
message
severity
source_refs
```

Success criteria:

- pySHACL missing -> clear setup hint, no hard failure in baseline
- fake SHACL backend can produce deterministic violations
- real pySHACL backend validates a tiny fixture
- validation report is never treated as claim support

Why first:

- deterministic
- directly improves fact-layer quality
- low risk
- Python-native

### WP3: Serena Read-Only Code Navigation Spike

Purpose:

```text
Give agents IDE-like navigation without teaching TEP to implement LSP.
```

Scope:

- read-only symbol lookup
- read-only references lookup
- read-only file/symbol overview
- no Serena editing tools in round 1

Commands:

```text
code-backend-search --backend serena --query <text> --fields target,symbols,refs
code-backend-info --backend serena --path <path> --symbol <name>
```

Output:

```text
navigation_candidate
path
symbol
range
kind
backend_confidence
backend_reason
```

TEP behavior:

- map candidates to existing `CIX-*` by path when possible
- optionally suggest `code-refresh` for stale/missing CIX
- never use Serena output as proof
- require source/code read before truth claims

Success criteria:

- fake Serena backend supports unit tests
- unavailable MCP endpoint fails softly
- live test can run only when Serena is configured
- telemetry distinguishes Serena lookup from raw file reads
- no write/edit tools exposed by TEP adapter

Why before CocoIndex:

- LSP navigation is more precise for symbols/references
- directly reduces raw file reading
- MCP-native interaction matches agent workflow

### WP4: CocoIndex Semantic Search Spike

Purpose:

```text
Use CocoIndex for semantic/vector code search and incremental code indexing,
without replacing CIX.
```

Scope:

- query CocoIndex/cocoindex-code for semantic code candidates
- optionally surface chunk path/range/summary
- do not import embeddings or vector data into TEP
- do not require CocoIndex for baseline `code-search`

Commands:

```text
code-backend-search --backend cocoindex --query <text> --fields target,summary,score
code-backend-status --backend cocoindex
```

Output:

```text
navigation_candidate
path
range
summary
score
chunk_id
```

Success criteria:

- fake CocoIndex backend unit tests
- missing CLI/daemon returns setup hint
- live Docker/local test gated by environment
- results can be correlated with CIX path refs
- semantic result cannot appear in proof chain

Why after Serena:

- semantic search is useful but ranking may be embedding/model dependent
- LSP/symbol navigation is easier to make deterministic

### WP5: Datalog-Shaped Dependency Closure Interface

Purpose:

```text
Prepare for Soufflé without making it a hard dependency.
```

Round 1 does not need real Soufflé execution. It needs a projection and fake
backend contract.

Relations:

```text
record(id, type, status, lifecycle)
supports(claim, source)
contradicts(claim_a, claim_b)
links(record_a, record_b, kind)
scoped_to(record, workspace_or_project_or_task)
blocks(question, plan_or_action)
depends_on(record_a, record_b)
```

Candidate outputs:

```text
derived_candidate
dependency_chain
blocked_action_candidate
indirect_conflict_candidate
stale_support_candidate
```

Commands:

```text
derive-context --backend builtin|datalog --query support-closure --record <ID>
derive-context --backend builtin|datalog --query blocked-actions
```

Success criteria:

- fake backend returns deterministic chains
- output chains cite canonical record ids
- output is not proof without inspecting records
- future Soufflé adapter can consume exported `.facts`

Why not real Soufflé yet:

- dependency closure schema must stabilize first
- we already have Z3 for bounded logic consistency
- no need to introduce another solver until the interface is proven useful

## What We Explicitly Defer

### GLiNER2 Extraction

Defer until fact validation is stable.

Reason:

- extraction will increase candidate volume
- without strong validation/review, it can make context noisier
- useful in round 2 for `INP-*` classification and source pre-processing

### Splink / dedupe Entity Resolution

Defer until duplicate records become a measurable pain.

Reason:

- entity resolution needs labeled examples or tuning
- premature merge suggestions can be dangerous
- cleanup/archive lifecycle should stabilize first

### Semgrep / OpenGrep

Defer until CIX smell lifecycle and guideline selection are stable enough.

Reason:

- pattern findings are useful but noisy
- they should feed `CIX` smell annotations and `PRP-*`, not block coding
- better after code backend telemetry shows where agents over-read code

### Codebase-Memory MCP

Defer to experiment after Serena/CocoIndex.

Reason:

- high potential for attention/curiosity maps
- newer and broader than first-round needs
- should be compared against our own attention/probe outputs

## Round 1 Test Matrix

Required tests:

| Area | Unit | CLI | MCP/Live | Docker |
| --- | --- | --- | --- | --- |
| backend registry | required | required | not needed | not needed |
| pySHACL fake | required | required | not needed | not needed |
| pySHACL real | optional dependency | required when installed | not needed | optional |
| Serena fake | required | required | not needed | not needed |
| Serena real | not required | optional | gated live | optional |
| CocoIndex fake | required | required | not needed | not needed |
| CocoIndex real | not required | optional | gated live | optional |
| Datalog fake | required | required | not needed | not needed |

Live-agent tests should verify:

- agent checks `backend-status` before relying on a backend
- agent treats backend results as candidates
- agent reads/cites canonical source before proof claims
- telemetry records backend lookups
- missing backend does not derail task completion

## Round 1 Definition Of Done

Round 1 is complete when:

- `backend-status` exists and is documented
- `validate-facts --backend rdf-shacl` works with fake and real pySHACL when installed
- Serena read-only adapter exists behind settings and fake tests
- CocoIndex semantic-search adapter exists behind settings and fake tests
- Datalog-shaped projection exists with fake closure tests
- all backend outputs are rejected by evidence-chain validation as direct proof
- telemetry distinguishes backend lookups from raw reads
- public docs mention optional backend policy at a high level
- developer docs include setup and test commands

## Recommended Implementation Order

1. Backend registry, settings schema, status command, telemetry event type.
2. Fake backend framework and proof-boundary tests.
3. RDF projection + fake SHACL validation.
4. Optional real pySHACL integration and fixture test.
5. Serena fake adapter and read-only command surface.
6. CocoIndex fake adapter and semantic-search command surface.
7. Datalog projection/export and fake closure query.
8. Gated live tests for configured real backends.
9. Documentation update and migration notes.

This sequence keeps the core stable while creating clear seams for external
tools.
