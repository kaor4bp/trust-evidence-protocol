# TEP And CocoIndex Integration Research

Last reviewed: 2026-04-19.

## Question

TEP already has `CIX-*` code-index entries with lightweight AST/text metadata.
CocoIndex and `cocoindex-code` also provide AST-based codebase indexing and
agent-facing retrieval. The architectural question is whether TEP should keep
building its own parser/indexing features or integrate with CocoIndex.

## External Findings

CocoIndex is a data transformation framework for AI context pipelines. Its
public positioning is incremental processing: declare transformation logic and
let the engine keep target stores synchronized with changed source data and
changed pipeline code.

Sources:

- [CocoIndex homepage](https://cocoindex.io/) describes incremental processing,
  codebase sources, persistent pipeline control, lineage, metrics, and target
  stores.
- [Real-time Codebase Indexing](https://cocoindex.io/examples/code_index)
  describes reading local code files, deriving language from extension,
  splitting code into semantic chunks with Tree-sitter, generating embeddings,
  storing vectors, and querying by similarity.
- [cocoindex-code](https://github.com/cocoindex-io/cocoindex-code) is a
  separate AST-based semantic code search tool with CLI/MCP integration,
  Docker setup, local or cloud embeddings, and multi-language support.
- [cocoindex-code PyPI](https://pypi.org/project/cocoindex-code/) describes it
  as an AST-based semantic code search tool for coding agents, with CLI and MCP
  integration.

Relevant capabilities:

- incremental indexing and update handling
- Tree-sitter semantic chunking
- embeddings and vector retrieval
- CLI and MCP surfaces for coding agents
- Docker-friendly deployment
- broad language coverage, including Python, JS/TS, Rust, Go, Java, C/C++,
  Markdown, JSON, YAML, TOML, SQL, shell, and others
- local SentenceTransformers embeddings or cloud embeddings through LiteLLM

## Current TEP Overlap

TEP currently overlaps with CocoIndex in the narrow area of code context
extraction and lookup:

- `init-code-index`, `index-code`, and `code-refresh`
- `CIX-*` entries for files, directories, symbols, globs, and logical areas
- Python AST metadata extraction
- JS/TS lightweight regex extraction
- Markdown heading/link/code-block outline extraction
- path/language/import/symbol/feature search

This overlap is real, but incomplete. TEP's CIX layer is not just a code search
index.

## Non-Overlapping TEP Semantics

TEP CIX entries carry protocol-specific semantics that CocoIndex should not own:

- `CIX-*` IDs and lifecycle states: `active`, `missing`, `superseded`,
  `archived`
- file hash and freshness checks for stale annotations
- manual features and agent notes
- local smell annotations with severity/category/status
- links to `GLD-*`, `CLM-*`, `MODEL-*`, `FLOW-*`, `PLN-*`, `DEBT-*`, `WCTX-*`,
  `TASK-*`, and `ACT-*`
- impact/navigation links from canonical records back into code areas
- explicit rule that CIX is navigation only and never proof
- validation that prevents CIX from becoming claim support, source support, or
  action justification

These semantics are central to TEP. Replacing CIX with CocoIndex would lose the
evidence boundary unless TEP reintroduced it on top.

## Recommended Boundary

Use CocoIndex as an optional external code-intelligence backend, not as the
canonical TEP code index.

Recommended split:

- TEP owns canonical/navigation records: `CIX-*`, links, annotations, smell
  lifecycle, freshness, and proof boundaries.
- CocoIndex owns heavy code retrieval: Tree-sitter chunking, embeddings,
  semantic search, incremental refresh, and broad language parsing.
- A TEP adapter imports or references CocoIndex results into CIX-compatible
  projections when useful.
- CocoIndex search results remain navigation candidates until the agent reads
  code or records an accepted `SRC-*`/`CLM-*` chain.

This keeps TEP lightweight by default while avoiding duplicate investment in
multi-language AST parsing and semantic code search.

## Integration Options

### Option A: Keep Current Baseline

Keep Python `ast`, JS/TS regex, and Markdown outline extraction in TEP.

Use when:

- TEP must work without external services, Docker, embeddings, or databases.
- Tests need deterministic parser output.
- The agent only needs cheap path/import/symbol filtering.

Cost:

- Language coverage stays shallow.
- Agents still need grep/file reads for semantic search.
- TEP risks slowly rebuilding a weaker CocoIndex.

### Option B: Add Optional CocoIndex Lookup

Add settings for an optional `cocoindex-code` command/MCP endpoint. TEP
continues writing CIX entries, but `code-search` can optionally include
CocoIndex semantic candidates.

Use when:

- The user has installed CocoIndex or runs the Docker container.
- The agent needs semantic code retrieval.
- We want immediate token savings without changing CIX schema.

Cost:

- Requires settings, dependency checks, and error-tolerant fallback.
- Search ranking becomes partly embedding/model dependent.
- Results must be labeled as navigation candidates, not proof.

### Option C: CocoIndex-Backed CIX Refresh

Use CocoIndex output as a source for richer CIX metadata:

- semantic chunks
- chunk locations
- symbol/chunk summaries
- language-specific chunk types
- optional embedding search ids

TEP would store stable pointers and small summaries, not raw vector payloads.

Use when:

- We need CIX to guide impact analysis across large repos.
- We want agents to traverse code maps without reading many files.
- CocoIndex output is stable enough for reproducible tests.

Cost:

- More adapter code.
- Schema migration for CIX metadata.
- Need careful stale/hash semantics when CocoIndex and Git state diverge.

### Option D: Replace TEP AST Parsers

Remove most internal AST extraction and delegate to CocoIndex.

This is not recommended now. It would make baseline TEP depend on a heavier
runtime and would conflate code retrieval with TEP's evidence/navigation model.

## Proposed Near-Term Plan

1. Keep TEP's current lightweight parser package as the no-dependency baseline.
2. Add a settings section such as:

   ```json
   {
     "code_intelligence": {
       "backend": "builtin",
       "cocoindex": {
         "enabled": false,
         "command": "ccc",
         "mode": "cli",
         "max_results": 8,
         "import_into_cix": false
       }
     }
   }
   ```

3. Add a small adapter interface:

   ```text
   CodeSearchBackend.search(query, root, limit) -> navigation candidates
   CodeSearchBackend.status(root) -> availability/freshness diagnostics
   CodeSearchBackend.refresh(root, paths) -> optional refresh result
   ```

4. Add tests with a fake CocoIndex backend first. Do not require real
   CocoIndex in unit tests.
5. Add Docker live-agent tests later that verify a real `cocoindex-code`
   container can answer a semantic query and that TEP labels the result as
   navigation-only.
6. Only after the adapter is stable, consider importing CocoIndex chunk metadata
   into CIX entries.

## Test Strategy

Minimum tests before integration:

- settings default keeps backend `builtin`
- missing CocoIndex executable fails softly and suggests setup
- fake CocoIndex search results are returned as navigation candidates
- fake results cannot be used as evidence-chain proof
- CIX annotations remain local and survive builtin refresh
- CocoIndex candidates can link to CIX entries by path/range when available
- telemetry records CocoIndex lookup use separately from raw file reads

Live tests after optional integration:

- Docker `cocoindex-code` can index a small fixture repo
- TEP adapter can call the configured CLI/MCP endpoint
- agent uses CocoIndex candidate to choose which file to inspect
- agent still reads/cites code before making truth claims

## Decision

Do not replace CIX with CocoIndex.

Do integrate CocoIndex as an optional code-intelligence backend once the TEP core
is stable enough for a narrow adapter. The first integration should focus on
semantic search and token reduction, not on replacing TEP record semantics.

