# TEP Developer Reference

This document is the normative development reference for the Trust Evidence Protocol runtime plugin.

It describes what the plugin must do, which problems it solves, which contracts must survive refactoring, and how future components should fit into the system. It is not a line-by-line description of the current implementation.

For record fields and relationships, see `docs/TEP_DATA_MODEL.md`.
For pragmatic backend options, see `docs/TEP_RESEARCH_MAP.md`.
For deeper reasoning research tracks, see `docs/TEP_ACADEMIC_RESEARCH_PLAN.md`.
For the detailed reasoning synthesis behind explanatory chains and reconciliation,
see `docs/TEP_REASONING_RESEARCH.md`.
For bounded planning, deferral, and curiosity-driven hypothesis verification, see
`docs/TEP_PLANNING_CURIOSITY_RESEARCH.md`.
For the first stable-core rewrite phase, breaking-change policy, migration
expectations, and implementation gates, see
`docs/TEP_CORE_REWRITE_CONTEXT.md`.
For the current pre-rebuild runtime surface, see
`docs/TEP_CORE_BASELINE.md`.

## Purpose

TEP exists to give a coding agent persistent, auditable project memory without letting memory become unchecked belief.

The plugin must help the agent:

- classify incoming information before using it
- turn source material into source-backed claims
- distinguish truth, authorization, restrictions, guidelines, tasks, proposals, and operational context
- retrieve known facts before rediscovering them
- build user-visible evidence chains for conclusions, plans, permission requests, and significant actions
- preserve reusable discoveries, rules, plans, debt, questions, models, flows, code map entries, and critique
- demote obsolete-but-true claims without deleting audit history
- detect candidate conflicts mechanically before asking the agent to reason over all prose records
- reduce token pressure by moving lookup, indexing, validation, and consistency checks into deterministic tools

## Reasoning Principle

TEP should not remove heuristic reasoning, abstraction, critique, or hypothesis
generation from the agent.

The governing rule is:

```text
heuristic reasoning is allowed
unsupported commitment is not allowed
```

The agent may form a rich exploratory view of the problem. Before using that view
for a plan, edit, permission request, final answer, claim promotion, model update,
flow update, or task completion, it must reconcile the view with canonical facts.

The reconciliation pass should separate:

- supported facts
- contradicted facts
- fallback-only historical context
- hypothesis-only elements
- abstractions and interpretations
- open questions
- the subset safe to commit to

This keeps the agent free to think, but prevents unsupported interpretations from
becoming action justifications.

TEP should also distinguish two user-visible chain types:

- `Evidence Chain`: proof-oriented and suitable for commitment.
- `Explanatory Chain`: exploration-oriented and suitable for fact-compatible
  candidate narratives that may contain marked hypotheses.

An explanatory chain can be valid even when it is not proven. Its validity comes
from consistency with known facts, explicit hypothesis marking, temporal/order
plausibility, and clear confirmers or defeaters. It becomes actionable only after
reconciliation.

## Planning And Curiosity Principle

TEP should distinguish bounded partial progress from lazy superficial coverage.

For large tasks, the agent may choose a coherent slice and defer the rest if it:

- states the selected scope
- records deferred work in `PLN-*`, `DEBT-*`, `OPEN-*`, or `WCTX-*`
- explains why the slice is the best next move
- defines resume conditions
- does not claim full completion

TEP should also create inquiry pressure around useful hypotheses.

Every important hypothesis should expose:

- possible confirmers
- possible defeaters
- cheapest safe observation
- whether the user is the right oracle
- downstream reasoning value if confirmed

The agent should verify high-value hypotheses when doing so is cheap and safe,
because confirmed hypotheses become facts and enable deeper evidence-backed
chains.

Curiosity should also use generated attention signals when they exist.
Rarely tapped but semantically relevant clusters, decayed high-impact records,
and reasoning chains that cross cluster boundaries should become inquiry
candidates.
This prevents retrieval from collapsing into already-hot records and helps the
agent notice blind spots, hidden dependencies, missing model/flow links, and
possible task drift.
Tap counts, topic clusters, and coordinates are navigation only; they do not
prove truth.
Partial attention-map views may be used to manage context budget and induce
useful curiosity, but they must disclose that the view is partial and must not
hide restrictions, conflicts, or proof needed for commitment.
Generated link gaps should distinguish unknown, expected-missing, candidate,
established, tested-absent, and rejected links.
Absence of a generated edge is not evidence of absence; bounded evidence of
absence requires an explicit source-backed claim.
The runtime may propose bounded stochastic curiosity probes across clusters
when no fresh established/rejected/tested-absent state answers whether a
relationship exists.
Such probes should be budgeted, reproducible, and framed as relation checks, not
as evidence.

## Problems Solved

### Agent Memory Is Not Proof

Agents may remember user instructions, runtime observations, and previous conclusions, but raw memory is not enough to justify future action.

TEP solves this by requiring:

- `SRC-*` records for provenance
- `CLM-*` records for normalized truth assertions
- explicit status and lifecycle
- source quotes or artifact refs
- evidence-chain validation before decisive use

### Flat Facts Do Not Form Understanding

A flat list of claims is searchable but weak for planning.

TEP solves this with derivative records:

- `MODEL-*` for an evidence-backed picture of one domain/aspect
- `FLOW-*` for end-to-end behavior across models and claims
- `WCTX-*` for local operational focus and handoff
- `PRP-*` for constructive agent critique and options
- `PLN-*`, `DEBT-*`, and `OPEN-*` for continuity

These records guide attention but do not prove truth by themselves.

### Old True Claims Can Poison Retrieval

A claim may have been correct when recorded but no longer describe current behavior.

TEP solves this with claim lifecycle:

- `active`: normal retrieval candidate
- `resolved`: true historically, fallback-only
- `historical`: background historical context, fallback-only
- `archived`: explicit-reference/audit only

Truth `status` and retrieval `lifecycle.state` are separate. Do not weaken a true claim just to hide it from the agent.

### Free-Text Contradiction Search Does Not Scale

Comparing every prose claim against every other prose claim is expensive and fragile.

TEP solves this with layered mechanical prefilters:

- structured `comparison` blocks on claims for exact/boolean contradiction scans
- optional `CLM.logic` predicate projections for typed logic checks
- generated `topic_index/` for lexical grouping and candidate review
- generated `logic_index/` for predicate/symbol/rule lookup
- optional future ML/statistical prefilters for broader candidate retrieval

All generated indexes are navigation only. Conflict candidates must be resolved by inspecting canonical `CLM-*` and `SRC-*` records.

### Code Understanding Costs Too Many Tokens

Agents repeatedly use grep and file reads to rebuild the same code map.

TEP solves this with `CIX-*` code-index entries:

- files, directories, globs, symbols, or logical areas
- AST or lightweight metadata
- imports, symbols, features, manual notes, smell annotations
- links to records for navigation and impact analysis
- observed file hashes so notes can become stale

`CIX-*` is not proof. It tells the agent where to inspect and what might matter.

### User Instructions Need Durable Operational Form

User instructions about how to write code, tests, reviews, debugging, or architecture should not disappear into chat history.

TEP solves this with `GLD-*` guideline records:

- source-backed
- scoped as global, project, or task
- priority `required`, `preferred`, or `optional`
- disclosed before and after substantial code/test edits

Guidelines guide action but do not prove factual claims.

## System Layers

TEP has four conceptual layers.

### 1. Canonical Memory

Canonical memory is stored under the resolved TEP context root, usually
`~/.tep_context` for the global agent memory target or legacy `.codex_context`
during migration.
Canonical records live in `records/`; raw durable artifacts live in
`artifacts/`; cleanup archive bundles live in `archives/`.

Only canonical records and artifacts can be durable sources for future reasoning.
`INP-*` records are canonical provenance for captured input, but they are not
classified proof until a `SRC-*`/`CLM-*`/`GLD-*`/other appropriate record is
created from them.

The live TEP context root is operational memory and should not be committed to a
project repository.
Repositories may contain templates, fixtures, sanitized exports, and docs, but
not the working `records/`, generated indexes, runtime state, task focus, or
agent telemetry.

### 2. Generated Navigation

Generated files are rebuildable and not canonical:

- `index.md`
- `backlog.md`
- `review/*.md`
- `topic_index/*`
- `logic_index/*`
- `code_index/*`
- `runtime/*`

Generated navigation may guide lookup, but proof must resolve to canonical records.

### 3. Runtime Policy

`settings.json` under the resolved TEP context root is runtime policy, not
truth.

It controls:

- current project/task focus
- `allowed_freedom`
- hook modes
- context budget
- input capture behavior
- artifact copy/reference policy
- cleanup staging and retention thresholds
- optional analysis backends such as Z3 or NMF

The global-context architecture must not use one process-wide task focus for
all workspaces.
Runtime focus needs workspace/session scoping so parallel agents and projects do
not overwrite each other's active task.

Context-root discovery order:

1. explicit `--context`
2. `TEP_CONTEXT_ROOT`
3. existing `~/.tep_context`
4. legacy `.codex_context` found from the current workspace upward
5. future default `~/.tep_context`

If both global and legacy contexts exist, global context wins unless an explicit
`--context` is supplied.
Migration tools should copy/import legacy repo-local contexts into the global
store with project refs instead of silently merging them.

Settings need layered scope, not ad hoc mutation. Effective runtime policy should
resolve in this order:

1. plugin defaults
2. global context defaults
3. workspace override by normalized workspace root
4. project override by `PRJ-*`
5. task/session override for short-lived focus

The runtime should expose an explain command that prints the effective value and
the layer that supplied each key. Settings are policy and must not become proof.

### 4. Agent Discipline

The skill defines the reasoning discipline. The plugin can enforce some boundaries through commands, validation, hydration, hooks, and MCP lookup, but it cannot replace agent judgment.

The agent must still:

- search the resolved TEP context first
- disclose evidence chains and reasoning checkpoints when required
- keep proof and navigation separate
- ask the user when policy or facts require it
- record durable outcomes

## Core Functional Contracts

### Bootstrap

The plugin must create a strict `.codex_context` layout with one directory per canonical record type, one JSON object per record file, generated directories for review/runtime/topic/logic/code indexes, settings with safe defaults, and templates explaining the layout.

### Validation

Validation must check:

- record id and filename consistency
- required fields
- record type and prefix consistency
- reference integrity
- claim source backing
- lifecycle/status consistency
- action and permission chains
- generated/index directory assumptions

Validation should fail on structural corruption. Structured conflict reports should not make the whole review flow unusable unless the calling policy explicitly treats conflicts as blockers.

### Hydration

Hydration must assemble compact operational context:

- current project
- current task
- conflicts and review warnings
- active restrictions
- active guidelines
- active permissions
- active proposals
- plans, debt, and open questions
- current/fallback claim attention
- available lookup commands

Hydration must motivate the agent to search and link records, not just print a mechanical banner.

### Context Lookup

Lookup tools must favor precision and explicit projections:

- `brief_context` for task-oriented summaries
- `search_records` before raw file search
- `record_detail` before citing a record
- `linked_records` for impact and context expansion
- `guidelines_for` before sizeable edits
- `code_search` / `code_info` for code navigation
- `topic_search` / `topic_info` for lexical prefiltering
- `logic_search` / `logic_check` for predicate prefiltering
- `cleanup_candidates` for stale/noisy records

Lookup results are not new truth. They are access paths into canonical records.

### Evidence Chains

The plugin must support user-visible evidence chains shaped as:

```text
fact CLM-...: "quote" -> observation CLM-...: "quote" -> requested_permission ...
```

The chain validator must check:

- referenced records exist
- roles match record types and claim statuses
- quotes appear in the record or source quotes
- proof nodes resolve to source-backed claims
- guidelines, permissions, restrictions, projects, tasks, proposals, WCTX, CIX, topic indexes, and logic indexes are not used as truth
- tentative/exploration hypotheses are not used as decisive proof

`augment-chain` is the read-only helper for compact chains. It may fill missing
quotes from canonical record statements/rules/summaries and attach source
quotes, but it must still run the same validation and must not create proof from
generated metadata.

Evidence chains are both a user explanation format and a mechanical guardrail.

### Hooks

Hooks are guardrails, not a complete security boundary.

They should:

- hydrate at session start or user prompt time according to settings
- remind the agent to use the skill and context lookup
- classify shell/tool actions before execution
- block or warn according to `allowed_freedom`, restrictions, and action kind
- invalidate hydration after mutating operations
- avoid false positives for read-only commands
- avoid noisy repetitive output in normal mode

Hook behavior must be configurable through `.codex_context/settings.json`.

### MCP

MCP tools are read-only in the current contract.

They should expose fast lookup surfaces over canonical records and generated navigation indexes. They must not become a second mutation API until authorization, audit, locking, and hook behavior are designed.

### Persistence

The plugin must persist durable information when future agents would otherwise rediscover the same fact, repeat a mistake, miss a user rule, lose task continuity, forget a permission or restriction, overlook a known risk, miss an open question, or ignore a useful model, flow, or proposal.

The plugin must also avoid memory pollution. Transient thoughts should remain ephemeral.

## Refactor Invariants

Refactoring must preserve these contracts:

- `CLM-*` remains the only canonical truth record type.
- `SRC-*` remains the provenance carrier for claims.
- Generated views and indexes remain navigation only.
- `MODEL-*` and `FLOW-*` remain derivative from claims.
- `GLD-*`, `PRP-*`, `PRM-*`, `RST-*`, `TASK-*`, `WCTX-*`, and `CIX-*` must not become proof.
- Claim truth `status` and retrieval `lifecycle.state` remain separate.
- Resolved/historical claims remain searchable but fallback-only.
- `hypotheses.jsonl` remains an index over tentative `CLM-*`, not a truth store.
- Optional Z3, NMF, embeddings, or other ML backends must never be required for baseline operation.
- Optional analysis outputs must remain candidates until canonical records are reviewed.
- Commands, JSON shapes, hook payloads, and MCP tool names must not change without an explicit migration plan and tests.
- Canonical writes must go through plugin commands where commands exist.
- File writes must be atomic and serialized where the plugin owns the store.

## Test Strategy

TEP uses three test layers.

### Deterministic Runtime Tests

These are the main regression layer.

They should cover:

- record creation and validation
- source-backed claim rules
- lifecycle transitions
- strictness/action policy
- hooks classification
- MCP read-only lookup
- topic and logic index generation
- code-index metadata and stale annotations
- cleanup candidate reports

### Coverage Runs

Coverage is used to reveal blind spots in plugin Python code.

Coverage should improve by extracting pure modules from subprocess-only CLI paths. The target is not a vanity percentage; the target is testable domain logic.

### Live-Agent Docker Tests

Live-agent tests run real `codex exec` inside Docker with isolated `CODEX_HOME`.

They are conformance checks for skill behavior, not the primary regression base. They may be slower and nondeterministic. Failures should be triaged against the expected behavior, not blindly fixed by weakening the skill.

## Refactor Direction

The current implementation should be decomposed incrementally.

Preferred module boundaries:

- `records`: id generation, paths, atomic IO, locking
- `validation`: schemas, reference integrity, lifecycle/action checks
- `settings`: runtime policy and defaults
- `reports`: generated attention, backlog, review summaries
- `search`: keyword search, linked records, relevance ranking
- `code_index`: CIX metadata, AST extraction, annotations, impact links
- `topic_index`: lexical and optional NMF prefilters
- `logic_index`: predicate projection, symbol graph, structural conflicts
- `logic_z3`: optional SMT checks and unsat-core projection
- `cleanup`: stale/noisy record triage and deliberate lifecycle operations
- `cli_commands`: thin command handlers over importable domain services

Refactor order should be:

1. lock down public command behavior with tests
2. extract pure functions with direct unit tests
3. keep CLI wrappers thin
4. keep MCP read-only and backed by the same runtime APIs
5. preserve hooks as adapters over shared policy functions

## Future Development Areas

### Cleanup

Cleanup must be conservative.

Near-term cleanup should be read-only triage:

- stale source or claim candidates
- active claims that should be fallback-only
- orphan records
- duplicate-like claims
- active hypotheses that no longer have current support
- models/flows depending on fallback claims
- stale CIX annotations by file hash

Mutation should require explicit commands: resolve, archive, restore, supersede, close, reject, and refresh.

Archive/delete cleanup must be staged:

1. report candidates without mutation
2. build an archive plan with reasons, refs, paths, and hashes
3. write a `zip` archive plus sidecar manifest
4. list archives by `ARC-*` id so restore does not depend on user memory
5. restore only from manifest-verified archive entries and never overwrite a
   conflicting existing file
6. keep a tombstone or archive index entry so explicit lookup and restore remain possible
7. delete raw files only after an additional configured grace period

`INP-*` captured user input records have an extra safety rule. Lack of incoming
links is not enough to archive them. An unreferenced input record becomes an
archive candidate only after `settings.cleanup.orphan_input_stale_after_days`.
That threshold must be configurable per effective settings layer. This keeps
fresh user prompts available for classification and linkage without forcing the
agent to immediately turn every prompt into canonical records.

Artifacts copied from user input or tool output follow artifact retention, not
input retention, unless an `INP-*` or `SRC-*` still references them. Deletion
should be rare and audit-oriented.

### Formal Logic And Z3

Formal checks should start narrow:

- symbol registry and meaning pressure
- same predicate/args/context polarity conflicts
- functional predicate value conflicts
- simple Horn-style rule closure
- optional Z3 consistency snapshots
- claim-level unsat-core reporting

Z3 must not decide truth. It should identify which claims make a formal snapshot inconsistent so the agent can inspect the underlying sources.

### Datalog And Graph Reasoning

Datalog is useful for recursive relationships and impact analysis:

- dependencies
- transitive links
- flow/model reachability
- code impact
- stale propagation
- permission/restriction scope

It may be a better fit than SMT for graph-like closure queries.

### ML And Statistical Prefilters

ML/statistical methods should reduce agent token work, not replace proof.

Potential uses:

- topic grouping over records
- attention maps over records and topic clusters
- tap decay and cold-zone detection
- cross-cluster bridge detection for reasoning-chain review
- controlled partial map reveal for context budgeting and curiosity
- generated link-state/gap detection with explicit absence semantics
- bounded stochastic curiosity probes over uncertain cross-cluster relations
- contradiction candidate prefiltering
- duplicate-like record detection
- cleanup prioritization
- relevant guideline selection
- code smell clustering
- hybrid retrieval over text and structured records

Outputs must be labeled candidate/navigation data.

### Code Intelligence

Code intelligence should progress from cheap to heavy:

1. Python `ast` and lightweight regex metadata
2. Tree-sitter for broader language parsing
3. Semgrep-style pattern rules for local smells and conventions
4. LSP/Jedi-style symbol resolution where available
5. CodeQL-like database/query workflows for deeper static analysis when justified

TEP should not require heavyweight code-analysis dependencies for baseline use.

## Documentation Contract

When changing TEP semantics, update:

- this developer reference
- `docs/TEP_DATA_MODEL.md` if record semantics changed
- `docs/TEP_RESEARCH_MAP.md` if backend direction changed
- plugin `README.md` if user-facing commands changed
- skill workflow files if agent behavior changed
- tests that prove the contract

Do not let implementation drift ahead of the normative docs.
