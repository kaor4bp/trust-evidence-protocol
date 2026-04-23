# TEP Data Model

This document defines the canonical data model for the Trust Evidence Protocol runtime plugin.

It is normative for refactoring. Current code may be reorganized, but the data semantics below must remain stable unless a migration is explicitly designed.

## Storage Boundary

Canonical storage:

- `.tep_context/records/`
- `.tep_context/artifacts/`
- `.tep_context/archives/`

Policy storage:

- `.tep_context/settings.json`

Generated navigation storage:

- `.tep_context/index.md`
- `.tep_context/backlog.md`
- `.tep_context/review/`
- `.tep_context/topic_index/`
- `.tep_context/logic_index/`
- `.tep_context/code_index/`
- `.tep_context/runtime/`
- `.tep_context/hypotheses.jsonl`

Generated storage is rebuildable and must not become canonical proof.

Legacy `.codex_context` roots are migration inputs. They remain readable for
migration and tests, but new 0.4 documentation and tooling should describe
`.tep_context` as the primary context root.

## Record Identity

Each canonical record is one JSON object in one file.

Rules:

- filename equals record `id`
- directory matches `record_type`
- new ids use `PREFIX-YYYYMMDD-xxxxxxxx`
- suffix is eight lowercase random hex characters
- legacy sequential ids remain readable but must not be generated for new records

Canonical record prefixes:

- `INP-*`: captured input
- `FILE-*`: source file metadata
- `ART-*`: TEP-owned artifact metadata or payload manifest
- `SRC-*`: source
- `CLM-*`: claim
- `PRM-*`: permission
- `RST-*`: restriction
- `GLD-*`: guideline
- `PRP-*`: proposal
- `ACT-*`: action
- `PRJ-*`: project
- `TASK-*`: task
- `WCTX-*`: working context
- `PLN-*`: plan
- `DEBT-*`: debt
- `MODEL-*`: model
- `FLOW-*`: flow
- `OPEN-*`: open question
- `MAP-*`: durable cognitive map cell, navigation only

Runtime/control ids:

- `REASON-*`: append-only task-local reasoning ledger entry
- `GRANT-*`: append-only authorization entry derived from a reason step
- `RUN-*`: command execution trace

Generated/navigation ids:

- `CIX-*`: generated code-index entry, not canonical truth
- `TEL-*`: telemetry event id, not canonical truth
- `CURP-*`: bounded curator work pool id, not canonical truth

## Record Versioning

New 0.4 records separate two version concepts:

- `contract_version`: public runtime contract, currently `"0.4"`.
- `record_version`: concrete JSON record shape, currently `1`.

`schema_version` is reserved for generated metadata and anchors that already
use numeric schema versions. New canonical records must not use
`schema_version` as the 0.4 contract marker.

Legacy records without `record_version` remain readable so migrations can run
in stages. New 0.4 record shapes with strict ownership or navigation semantics
must include both `contract_version` and `record_version`; this currently
includes `AGENT-*`, owner-bound `WCTX-*`, and `MAP-*`. Migration code should
branch on these fields and backfill or wrap legacy records only through
explicit migration provenance.

Record-shape changes are handled by the schema migration chain. Each schema
change has one dedicated module under `tep_runtime/schema_migrations/`, and
apply is all-or-nothing after post-migration validation. Root migration and
schema migration are separate operations.

## Local Agent Identity

`AGENT-*` is public local-agent metadata. It stores the agent name,
`hmac-sha256` key algorithm, `local-agent` scope, and `sha256:` key
fingerprint. It must not store private key material.

The corresponding HMAC key is runtime-private state under
`.tep_context/runtime/agent_identity/`. Owner-bound `WCTX-*` records store an
`owner_signature` over the canonical WCTX focus payload plus the public
`AGENT-*` reference and fingerprint. Runtime validators recompute the signed
payload hash for every signed WCTX, and verify the HMAC when the local runtime
secret owns that WCTX. Another agent may inspect that WCTX as navigation
context, but must create a signed fork/adopted WCTX before using it as current
focus.

## Core Semantics

Truth has one canonical record type: `claim`.

Terms such as fact, evidence, hypothesis, and observation are roles or lifecycle stages of `CLM-*`, not separate truth stores.

Mapping:

- hypothesis: `CLM-*` with `status=tentative`
- fact: `CLM-*` with `status=supported`
- evidence: `CLM-*` with `status=corroborated`
- observation: runtime-plane `CLM-*`, usually tentative or supported

Only source-backed `CLM-*` records can be decisive proof candidates.

## Input Records

`INP-*` records preserve raw prompt-level provenance before classification.

They represent:

- user prompts
- referenced files or attachments
- copied prompt artifacts
- tool payloads that should remain linked to later records

Required semantics:

- `input_kind`: `user_prompt`, `file_reference`, `attachment`, or `tool_payload`
- `captured_at`
- `origin.kind` and `origin.ref`
- `text` and/or artifact refs
- optional `session_ref`
- optional `derived_record_refs` for records produced from the input

`INP-*` records are not proof. They can explain where later `SRC-*`, `CLM-*`,
`GLD-*`, `PRP-*`, `TASK-*`, or project records came from, but reasoning must
still cite classified canonical records.

Runtime mechanics:

- `record-input` creates `INP-*` records through the normal record write path.
- UserPromptSubmit hook capture may create `INP-*` records automatically according to `settings.input_capture`.
- `metadata-only` prompt capture preserves prompt/session provenance while replacing raw prompt text with an explicit placeholder.
- Hook capture should rehydrate immediately after a successful write so prompt provenance does not make the next agent turn stale by itself.

## File Records

`FILE-*` records preserve metadata about original local or remote files.

They represent:

- local source files
- user-referenced files
- remote documents by URL
- deleted or moved files whose metadata still matters

Required semantics:

- original path or URL
- workspace/project scope when known
- observed sha256/mtime/size when local content was available
- optional linked artifact refs
- optional code-index refs

`FILE-*` records are provenance metadata. They are not proof without a linked
`SRC-*` quote.

## Artifact Records

`ART-*` records or manifests represent TEP-owned payloads.

They may point to:

- copied file snapshots
- generated screenshots/log extracts
- downloaded URL content
- archived prompt attachments

Required semantics:

- artifact path under `.tep_context/artifacts/` or archive manifest path
- media/type metadata when known
- source file/input/run refs when known
- retention policy metadata when relevant

`ART-*` records are storage/provenance. They are not proof without a linked
`SRC-*` quote.

## Source Records

`SRC-*` records preserve provenance.

They represent:

- user messages
- code excerpts
- command output
- logs
- screenshots
- documents
- artifacts
- memory records under audit

Required semantics:

- `source_kind`: `theory`, `code`, `runtime`, or `memory`
- `critique_status`: `accepted`, `audited`, or `unresolved`
- `origin.kind` and `origin.ref`
- quote and/or artifact refs sufficient for audit
- independence group when corroboration matters

`SRC-*` records carry information. They are not normalized assertions by themselves; claims perform that normalization.

## Claim Records

`CLM-*` records are normalized assertions extracted from sources.

Important fields:

- `plane`: `theory`, `code`, `runtime`, or `meta`
- `status`: truth state
- `claim_kind`: factual/implied/statistical/opinion/prediction/unfalsifiable
  or a plugin-generated `meta_*` kind
- `confidence`: high/moderate/low
- `statement`: human-readable assertion
- `source_refs`: accepted source support
- `support_refs`: additional claim support
- `contradiction_refs`: known conflicting claims
- `comparison`: optional structured comparable fact
- `logic`: optional typed predicate projection
- `meta`: optional plugin-generated corpus summary block when `plane=meta`
- `lifecycle`: retrieval/attention state

Truth statuses:

- `tentative`: weak or incomplete support
- `supported`: sufficient accepted support in scope
- `corroborated`: independent accepted support or accepted theory/runtime convergence
- `contested`: meaningful contradiction exists
- `rejected`: stronger contradiction wins

Lifecycle states:

- `active`: normal retrieval and reasoning candidate
- `resolved`: true or useful historically, no longer current, fallback-only
- `historical`: historical context, fallback-only
- `archived`: explicit-reference/audit/rollback only

Do not conflate `status` and `lifecycle.state`.

## Meta Claims

`CLM-* plane=meta` records are plugin-generated claims about the TEP corpus.
They do not assert product behavior directly. They assert that the TEP context
contains a distribution, conflict, gap, or other corpus-level signal over
underlying records.

Required 0.4.0 meta claim kinds:

- `meta_aggregate`: summarizes a related set of claims/runs/sources and their
  distribution.
- `meta_conflict`: records that the corpus contains conflicting or tensioned
  claims under comparable scope.
- `meta_gap`: records a missing relation, support path, or confirmed fact that
  matters for reasoning.

Planned future meta claim kinds:

- `meta_duplicate`
- `meta_staleness`
- `meta_evidence_quality`
- `meta_hotspot`
- `meta_regression_candidate`
- `meta_cluster`
- `meta_coverage`

The `meta` block should include:

- `source_query`
- `source_record_count`
- `source_record_refs_sample`
- `representative_refs`
- `outlier_refs`
- `source_set_fingerprint`
- `generated_by`
- `generated_at`
- `stale_policy`

Rules:

- Agents request meta claims through runtime/curator routes instead of writing
  them by hand.
- Meta claims can be `supported` when their corpus aggregation is mechanically
  reproducible.
- Meta claims are compact lookup entry points and chain summaries.
- Meta claims prove only corpus-level statements unless the chain also cites
  underlying object-level `CLM-*`/`SRC-*`/`RUN-*`.
- Meta claims are superseded or marked stale when the source set fingerprint
  changes; they are not silently rewritten.

## Comparison Blocks

Use `comparison` when a claim should participate in structured contradiction scans.

Fields:

- `key`: normalized identity of the compared fact
- `subject`: entity or object being compared
- `aspect`: property being asserted
- `comparator`: `exact` or `boolean`
- `value`: scalar comparable value
- `polarity`: `affirmed` or `denied`
- `context_scope`: optional narrower scope

The scanner should compare only compatible claims with the same normalized key and compatible context.

## Logic Projection

`CLM.logic` is an optional machine-checkable projection inside a source-backed claim.

It may include:

- `symbols`: typed objects introduced by the claim
- `atoms`: predicate applications over introduced symbols
- `rules`: Horn-style rules

Rules:

- logic projection does not create truth outside the parent claim
- every concrete symbol used by an atom must be introduced by a source-backed claim
- symbols should carry a `meaning` or `note` explaining the semantic object
- rule variables should be specific enough to avoid meaningless graph pressure
- generated `logic_index/` output is candidate/navigation data only

Z3 or any other solver may identify inconsistent formal snapshots, but claim status changes require source review.

## Control Records

Control records guide action but do not prove truth.

### Permission

`PRM-*` records represent bounded authorization.

Scope may be global, project, or task.

Permission can authorize an action. It cannot prove a claim.

### Restriction

`RST-*` records represent negative constraints.

They may be hard or soft, global/project/task scoped, and user/system imposed.

Restrictions can block action. They cannot prove a claim.

### Guideline

`GLD-*` records represent reusable operational rules.

Domains:

- code
- tests
- review
- debugging
- architecture
- agent-behavior

Guidelines should be source-backed and disclosed before/after substantial edits. They guide work but do not prove behavior.

## Agent Critique Records

`PRP-*` records capture constructive agent critique.

They may include:

- position
- cited claim/guideline/model/flow/open-question refs
- assumptions
- concerns
- concrete proposals
- recommended option
- risks
- stop conditions

Proposal assumptions are not proof.

## Operational Records

### Workspace

`WSP-*` records define operational memory boundaries.

One workspace can contain multiple projects. A record may not have a precise
project, especially after migration or when a user prompt spans several
repositories, but new records should link to the current workspace through
`workspace_refs` when `settings.json.current_workspace_ref` is set.

Workspace records do not prove truth.

### Project

`PRJ-*` records define context boundaries.

They prevent records about different repositories, domains, or products inside a
workspace from leaking into each other.

### Task

`TASK-*` records define execution focus.

They may contain task type, `execution_mode=manual|autonomous`, related claims/models/flows/open questions, plans/debt/actions, and restrictions.
Autonomous tasks are a runtime continuation contract: the agent should only stop when the task is done, blocked, or waiting for a user answer.

Tasks do not prove truth or grant permission.

### Working Context

`WCTX-*` records capture local focus and handoff:

- pinned refs
- focus paths
- topic seeds
- local assumptions
- concerns
- parent/superseded contexts

Working contexts are copy-on-write when materially changed. They do not prove truth.

## Understanding Records

### Model

`MODEL-*` records summarize the evidence-backed picture for one domain/aspect.

They are strictly derivative from claims.

Model classes:

- investigation-local
- domain knowledge

Investigation models should be promoted, superseded, or marked stale when they become broader domain knowledge or stop reflecting current claims.

### Flow

`FLOW-*` records describe end-to-end process understanding across models and claims.

They may include:

- model refs
- steps
- preconditions
- oracle
- expected/observed tensions
- open questions
- accepted deviations

Flow should normally remain integrated. Contradictions inside a flow are often useful signals, not a reason to split the flow prematurely.

## Continuity Records

### Plan

`PLN-*` records represent durable intended work.

They require title, status, priority, justification, steps, and success criteria.

### Debt

`DEBT-*` records represent durable liabilities:

- technical debt
- validator gaps
- protocol gaps
- test gaps
- cleanup/risk items

Debt should be closed, superseded, rejected, or resolved when no longer relevant.

### Open Question

`OPEN-*` records preserve deferred uncertainty.

They are especially important in autonomous mode, where the agent should keep working safely and return with a list of unresolved concerns.

## Action Records

`ACT-*` records represent meaningful intended or executed operations.

They should include kind, safety class, status, justification refs, project/task refs, timestamps, and note.

Mutating action policy is governed by `allowed_freedom`, restrictions, permissions, and hook classification.

## Run Records

`RUN-*` records preserve command execution traces.

Required semantics:

- workspace/project/task refs when known
- optional grant ref
- cwd
- command and command hash
- timestamps
- exit status
- selected output quotes

Runtime claims derived from command output must transitively reach a `RUN-*`
through `SRC-*`.

## Code Index Entries

`CIX-*` entries are generated/navigation code-map records.

They may target file, directory, glob, symbol, or logical area.

They may store:

- language
- imports
- symbols/classes/functions
- AST metadata
- manual features
- annotations
- smell annotations
- links to canonical records
- observed file sha256/mtime
- freshness state

CIX entries must not be used as proof, source support, claim support, or action justification. Read code or create `SRC-*`/`CLM-*` before making truth claims.

## Hypothesis Index

`hypotheses.jsonl` is an index over active tentative `CLM-*` records.

It exists to make active hypotheses visible and closable. It is not a second truth store.

Closing a hypothesis means updating the underlying claim status/lifecycle and removing or marking the index entry.

## Generated Topic Index

`topic_index/` groups records by lexical/statistical similarity.

Allowed use:

- prefilter broad searches
- find similar records
- propose contradiction-review candidates
- guide cleanup

Forbidden use:

- proof
- contradiction declaration
- claim support
- action justification

## Generated Attention Index

`attention_index/` may combine topic clusters, tap activity, lookup telemetry,
decayed activity scores, partial map views, cold-zone candidates, bridge
candidates, and generated link-state summaries.

Allowed use:

- choose what records or clusters to inspect next
- surface rarely tapped relevant zones
- surface cross-cluster reasoning-chain transitions
- surface expected but unestablished links
- propose bounded curiosity probes over uncertain cross-cluster relationships
- report bounded no-link observations for review
- manage context budget with partial map views
- render compact, normal, or wide visual-thinking maps that combine heat, cold zones, bridges, and curiosity prompts

Forbidden use:

- proof
- claim support
- action justification
- hiding active restrictions, conflicts, or commitment-critical proof
- treating absent generated edges as evidence of absence

Generated link states should be explicit:

- `established`: supported by canonical records
- `candidate`: generated signal worth checking
- `expected_missing`: expected by model/flow/task shape but not established
- `tested_absent`: bounded search/inspection found no link under recorded scope
- `rejected`: checked candidate weakened by canonical support
- `unknown`: no relation known and no absence check performed

Only `tested_absent` can support an absence-oriented claim, and only when backed
by a `SRC-*`/`CLM-*` pair that records scope, corpus or time boundary, and
method.

Curiosity probes are generated questions over records or clusters.
They should preserve:

- sampled record refs or cluster refs
- sampling method and seed
- reason for the probe
- task/model/flow scope
- budget group
- current link state before review
- resulting link state after review, if checked

A probe result is navigation metadata until backed by canonical records.

## Reason Authorization Ledger

`runtime/reasoning/agents/AGENT-*/reasons.jsonl` is an append-only runtime
ledger for justified reasoning by one local agent identity. Protected actions
are one consumer of that ledger, not the ledger's only purpose.

Ledger entries are not canonical truth records. They are runtime control
evidence:

- `REASON-*`: task-scoped reasoning step with the validated chain snapshot,
  parent links, branch label, intent, mode, action kind, and the agent's `why`.
- `GRANT-*`: reviewed one-shot authorization bound to mode, action kind, task
  scope, context fingerprint, expiry, and optionally exact command hash plus cwd.

The ledger is not a free-form record store. The append-only ledger validator
accepts current `REASON-*` and `GRANT-*` entries, plus legacy `AUTH/USE` entries
for old contexts. Current entries must carry the same `agent_identity_ref` as
their enclosing ledger path. `REASON-*` chain snapshots may cite only supported
evidence chain roles: `fact`, `observation`, `hypothesis`, `exploration_context`,
`permission`, `requested_permission`, `restriction`, `guideline`, `proposal`,
`task`, `working_context`, `project`, `model`, `flow`, and `open_question`.
Generated/backend/navigation ids such as `CIX-*`, `BCK-*`, `backend:*`, or
`topic_index:*` cannot be proof nodes.

`REASON-*` entries form a task-local DAG. A new step without explicit parents
continues from the latest step for the current task; explicit `parent_refs` and
`branch` create forks for alternative interpretations or rollback paths. A
reason step cannot parent across another `TASK-*`.
Same-mode continuation cannot duplicate the direct parent chain hash on the
same branch; the agent must extend the evidence chain or fork a named
alternative branch. This keeps the ledger as reasoning progression, not a
reusable permit token.

Final answers for an active task must be backed by a reviewed
`REASON-* mode=final` entry with the current task node and context fingerprint.
Autonomous `done` completion is stricter: it also needs a fresh
`GRANT-* mode=final`. Interrupted work or ordinary continuation can resume from
the latest non-final `REASON-*` without fabricating a final step.

For protected Bash, the intended path is:

```text
REASON-* -> GRANT-* -> RUN-* -> SRC-* -> CLM-*
```

New ledger entries include a hash-chain seal and weak proof-of-work metadata.
This makes accidental/manual rewriting cheap to detect and bulk rewriting more
expensive, but it is not a sandbox boundary against a process that can directly
modify all runtime files.

## Access Telemetry

`activity/access.jsonl` is append-only lookup telemetry.

Access events include:

- `accessed_at`
- `channel`: `cli`, `mcp`, `hook`, or another adapter name
- `tool`: lookup surface, such as `claim-graph`, `record-detail`, or `bash`
- `access_kind`: semantic lookup type, such as `claim_graph`, `record_detail`, or `raw_claim_read`
- `record_refs`: records exposed by the lookup when known
- `raw_path_count`: count of raw record-storage path references detected by hooks
- `access_is_proof: false`

Access telemetry may feed generated attention heatmaps and raw-read reports.
It must not support claims, permissions, restrictions, or evidence chains.

## Generated Logic Index

`logic_index/` indexes `CLM.logic` symbols, atoms, predicates, and rules.

Allowed use:

- predicate lookup
- symbol reuse
- vocabulary pressure reports
- candidate consistency checks
- candidate unsat-core reports

Forbidden use:

- proof outside parent claims
- automatic claim status changes
- source support

## Retrieval Priority

Default lookup order for truth-bearing claims:

1. active `corroborated`
2. active `supported`
3. active `contested` / `rejected` for conflict awareness
4. active `tentative` for exploration
5. resolved/historical fallback claims when active records do not answer
6. archived claims only by explicit id, audit, rollback, or user request

Generated views should reflect this priority.
Normal agent lookup should use compact projections such as MCP `claim_graph` or
CLI `claim-graph` before opening raw `records/claim/*.json` files. Raw claim
files are an escape hatch for debugging, migration, and missing tool coverage,
not the primary reasoning interface.

## Link Semantics

Common link fields:

- `input_refs`
- `source_refs`
- `support_refs`
- `contradiction_refs`
- `claim_refs`
- `guideline_refs`
- `model_refs`
- `flow_refs`
- `open_question_refs`
- `plan_refs`
- `debt_refs`
- `action_refs`
- `workspace_refs`
- `project_refs`
- `task_refs`
- `supersedes_refs`
- `promoted_from_refs`
- `resolved_by_claim_refs`
- `resolved_by_action_refs`
- `code_index_refs`
- `derived_record_refs`

Only claim/source links participate in proof. Most other links are scope, guidance, impact, or continuity.

## Cleanup Semantics

Cleanup is not deletion-first.

Preferred cleanup operations:

- resolve old-but-true claims
- archive audit-only claims
- reject false claims
- close stale hypotheses
- supersede old models/flows/proposals/guidelines
- complete or cancel plans
- close debt when addressed
- refresh stale CIX annotations

Input capture has stricter retention than ordinary orphan cleanup:

- `INP-*` records store captured user input or prompt-level provenance for later
  classification.
- an `INP-*` with no incoming links is not immediately archiveable
- orphan `INP-*` records become archive candidates only after the effective
  `settings.cleanup.orphan_input_stale_after_days` threshold
- stale orphan `INP-*` records should be archived to a restorable `zip` manifest
  before deletion is considered
- if an `INP-*` is later classified into `SRC-*`, `CLM-*`, `GLD-*`, `PRP-*`, or
  task/project records, those links reset its cleanup status

Archive-first cleanup should preserve:

- archive id
- zip archive path
- sidecar manifest path
- original record ids and paths
- sha256 for every archived payload
- reason codes
- context fingerprint or generation timestamp
- restore instructions

Restore is a separate explicit command stage:

- `cleanup-archives` lists available `ARC-*` bundles and can show one archive
  manifest without mutating context
- `cleanup-restore --dry-run` reads the archive manifest and reports per-item
  status without writing files
- `cleanup-restore --apply` restores only missing files whose zip entry matches
  the manifest `sha256`
- existing files are safe only when their current hash equals the archived hash
- conflicting existing files must not be overwritten by restore

Deletion is for malformed, duplicate, or explicitly discarded records when audit
history is not useful, and only after archival/grace policy allows it.

## Migration Requirements

Any data-model change must define:

- old shape
- new shape
- migration command
- validation rule
- backwards compatibility rule
- test coverage
- documentation update

Do not silently change semantics in implementation only.
