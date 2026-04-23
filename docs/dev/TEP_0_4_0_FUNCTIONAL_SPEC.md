# TEP 0.4.0 Functional Specification

This document is normative for the 0.4.0 rebuild.

Its job is to close logical gaps in the mechanics documents. If this document
conflicts with exploratory notes, this document wins. If the implementation
needs behavior not specified here, update this document before or with the code.

## 1. System Contract

TEP 0.4.0 is an MCP-first evidence and action-control runtime for agents.
The normal agent-facing API is MCP. CLI remains for development, debugging,
migration, and CI wrappers over the same core services.

The runtime must:

- keep workspace focus explicit
- route agents through `next-step` and `lookup`
- keep retrieval/navigation separate from proof
- mechanically capture provenance
- validate public evidence chains
- require task-local REASON progression for planning/action/final boundaries
- authorize protected actions through GRANT
- capture command provenance through RUN
- prioritize integrated MODEL/FLOW knowledge over scattered raw claims
- expose repair routes for every blocking response
- route normal agents through MCP front doors instead of a command zoo
- hard-block normal raw reads and writes of `~/.tep_context`

The runtime must not:

- rely on agents reading long skill manuals
- fall back to global current task/workspace for normal work
- treat generated views, CIX, backend hits, maps, or telemetry as proof
- allow new `SRC-*` without INP/FILE/ART/RUN provenance
- allow runtime CLM without transitive RUN provenance
- allow MODEL/FLOW promotion from runtime-only or tentative support
- make cleanup/archive a required 0.4.0 mechanic
- treat the old CLI command surface as public normal-agent API
- use `.codex_context` as a runtime fallback

Normal agents must not inspect or edit raw `~/.tep_context` records. Explicit
debugging, migration, forensics, and plugin-development modes may bypass this
only with an auditable raw-access mode.

## 2. Canonical Record Graph

### 2.1 Required Truth Graph

New truth-bearing records must satisfy this path:

```text
INP-* / FILE-* / ART-* / RUN-* -> SRC-* -> CLM-* -> MODEL-* / FLOW-*
```

Rules:

- `SRC-*` is invalid for new records unless it has at least one provenance
  surface: `INP-*`, `FILE-*`, `ART-*`, or `RUN-*`.
- `CLM-*` is the only atomic truth assertion type.
- `MODEL-*` and `FLOW-*` are derived integrated views over `CLM-*`.
- `CIX-*`, maps, telemetry, topic indexes, and backend hits are navigation.
- Navigation records may be linked for context but cannot be proof nodes.

### 2.2 Operational Graph

Operational records must satisfy this path:

```text
WSP-* -> PRJ-* -> TASK-* -> PLN-* / DEBT-* / ACT-* / OPEN-*
WSP-* -> AGENT-* -> WCTX-*
TASK-* -> WCTX-* -> REASON-* -> GRANT-* -> RUN-* / protected record
```

Rules:

- Every durable record must have `workspace_refs`, except explicitly marked
  legacy migration records.
- `project_refs` are optional only for genuinely cross-project records.
- `AGENT-*` is versioned local agent identity metadata; private key material is
  not a public record.
- `WCTX-*` is a versioned owner-bound agent working context, not truth.
- `REASON-*` belongs to one task focus and cannot parent across tasks.

### 2.3 Provenance Surfaces

`INP-*`: captured user input, prompt metadata, attachment reference, or tool
payload.

`FILE-*`: metadata about an original local or remote file. It may outlive the
original file.

`ART-*`: TEP-owned copied artifact, snapshot, generated file, or archived
payload.

`RUN-*`: command execution trace, including command, cwd, timestamps, exit
status, quoted output, and linked GRANT when protected.

Decision:

- `FILE-*` is metadata.
- `ART-*` is payload/file storage.
- For file evidence, runtime must create `FILE-*` and must create `ART-*`
  when settings allow copying/snapshotting.
- For command evidence, runtime must create/link `RUN-*`.

## 3. Authority And Ranking

### 3.1 Claim Authority Classes

Each `CLM-*` gets an authority class derived from source plane, status,
lifecycle, and support graph.

Highest to lowest normal lookup priority:

1. `integrated_theory`: current `MODEL-*`/`FLOW-*` built from supported or
   corroborated user-confirmed/theory CLM.
2. `confirmed_theory_claim`: current supported/corroborated theory CLM with
   user confirmation or accepted source support.
3. `meta_corpus_claim`: current plugin-generated meta CLM that summarizes the
   TEP corpus, such as aggregate/conflict/gap claims.
4. `code_claim`: current supported/corroborated code-plane CLM from FILE/SRC
   evidence.
5. `runtime_observation`: current runtime CLM with transitive RUN provenance.
6. `tentative_hypothesis`: tentative CLM compatible with known facts.
7. `resolved_or_historical`: resolved/historical CLM, fallback only.
8. `navigation_hit`: CIX/backend/map/topic result, never proof.

Rules:

- Runtime observations can corroborate that a behavior happened.
- Runtime observations alone cannot define durable system theory.
- A bug observation with many RUN confirmations still ranks below a supported
  theory claim for MODEL/FLOW promotion.
- Multiple independent runtime observations may increase retrieval relevance,
  but not promotion authority.
- Meta corpus claims can rank above scattered object-level runtime claims as
  compact entry points, but they prove only facts about the TEP corpus unless
  the chain drills down into underlying object-level support.

### 3.2 Plugin-Generated Meta Claims

`CLM-* plane=meta` records are plugin-generated claims about the TEP corpus.
They do not assert product behavior directly. They assert that the TEP context
contains a cluster, distribution, conflict, gap, or quality signal over
underlying records.

Required fields:

```json
{
  "plane": "meta",
  "claim_kind": "meta_aggregate|meta_conflict|meta_gap|...",
  "statement": "...",
  "meta": {
    "source_query": "...",
    "source_record_count": 0,
    "source_record_refs_sample": [],
    "representative_refs": [],
    "outlier_refs": [],
    "source_set_fingerprint": "...",
    "generated_by": "lookup|curator|aggregate-records|review-context",
    "generated_at": "...",
    "stale_policy": "source_set_changed|time_window_expired|manual"
  }
}
```

Rules:

- Agents should not hand-write meta claims; they request a runtime/curator
  route that creates them.
- Meta claims may be `supported` when the aggregation over the corpus is
  mechanically reproducible.
- Meta claims are high-value lookup entry points and chain summaries.
- Meta claims are not decisive proof of object-level truth without underlying
  `CLM-*`/`SRC-*`/`RUN-*` drill-down.
- Meta claims are not silently updated. If the source set changes, the old
  claim becomes `stale_candidate` or is superseded by a new meta claim.
- High link count alone must not make a stale or broad meta claim dominate
  lookup.

Required 0.4.0 meta claim kinds:

- `meta_aggregate`: summarizes a related set of claims/runs/sources and their
  distribution, for example pass/fail counts for repeated test runs.
- `meta_conflict`: records that the corpus contains conflicting or tensioned
  claims under comparable scope.
- `meta_gap`: records a missing relation, missing support, or missing confirmed
  fact that matters for reasoning.

Planned future meta claim kinds:

- `meta_duplicate`: likely duplicate claims that should be merged, superseded,
  or de-ranked.
- `meta_staleness`: lifecycle suspicion that a claim/model/flow is stale.
- `meta_evidence_quality`: summary of support independence, plane mix, and
  source quality.
- `meta_hotspot`: repeated access or token-pressure hotspot that should be
  promoted into MODEL/FLOW or another compact structure.
- `meta_regression_candidate`: similarity between new symptoms and resolved or
  historical claims without assuming same-bug identity.
- `meta_cluster`: durable summary of a topic/graph cluster when generated maps
  are insufficient.
- `meta_coverage`: summary of which parts of a domain/task have enough facts
  and which remain under-covered.

### 3.3 MODEL/FLOW Promotion Gate

MODEL/FLOW creation or update requires:

- at least one supported/corroborated theory CLM
- no tentative hypothesis in decisive support
- no runtime-only decisive support
- no meta-only decisive support for object-level theory
- no unresolved contradiction unless explicitly modeled as a known conflict
- workspace/project/domain scope
- source quote coverage through linked CLM/SRC

Rejected promotion must return repair routes:

- ask user to confirm theory
- record missing source evidence
- split runtime observation from theory claim
- drill down from meta claim into object-level support
- mark as PRP/proposal instead of MODEL/FLOW

### 3.4 Historical And Resolved Ranking

Resolved/historical claims are not forgotten.

They must:

- be excluded from first-page normal lookup unless directly queried
- appear in a `historical_fallback` section after active records
- carry explicit `lifecycle.state`
- include `why_fallback` in lookup output

Regression route:

- If active/runtime symptoms overlap a resolved bug claim, lookup must return a
  `regression_suspicion` branch.
- The branch must include at least two hypotheses:
  `same_issue_regressed` and `new_issue_with_similar_symptoms`.
- The agent must not conclude same-bug identity without new support.

Cleanup/archive policy is future work. 0.4.0 only needs ranking and labels.

## 4. Workspace, Project, And Focus

### 4.1 No Global Fallback

Normal commands must require explicit workspace focus from one of:

- local `.tep` anchor
- explicit command argument
- curator pool scope
- migration command scope

The primary context root is `~/.tep_context`. Legacy `.codex_context` data is
not a runtime fallback and may only be used as an explicit migration input.

If no workspace is available, return:

```json
{
  "blocked": true,
  "reason": "missing_workspace_focus",
  "repair": [
    {"command": "workspace-admission", "why": "choose or create workspace"},
    {"command": "inspect-readonly", "why": "read without durable writes"}
  ]
}
```

Global context can exist as storage, but not as an implicit current focus.

### 4.2 Foreign Repository Admission

If `cwd` or a referenced path is outside known project roots, runtime must not
silently attach it.

Required repair choices:

- create new workspace
- add project to current workspace
- inspect read-only without durable records

Durable writes for a foreign repo are blocked until admission is resolved.

### 4.3 WCTX Requirement

Lookup must have a WCTX.

Rules:

- If workspace is explicit and no suitable WCTX exists, lookup may auto-create
  a task-local WCTX for the current `AGENT-*`.
- If workspace is missing, WCTX auto-create is blocked.
- WCTX records should be frequent and cheap; they are agent-local working memory
  and may be superseded.
- WCTX records are owner-only. A different agent may inspect them as handoff
  context, but must create a signed fork/adopted WCTX before using that focus.
- WCTX owner signatures cover the canonical focus payload used by `next_step`,
  lookup, map sessions, and protected-action checks.
- WCTX cannot prove facts.

## 5. Lookup Contract

### 5.1 Purpose

`lookup` is the default read path for facts, code, theory, policy, research,
map context, and chain extension.

Direct raw record reads are allowed only for:

- plugin/runtime development
- migration/repair
- forensics after lookup drill-down
- explicit user request

### 5.2 Required Inputs

```json
{
  "query": "...",
  "reason": "orientation|planning|answering|permission|editing|debugging|retrospective|curiosity|migration",
  "kind": "auto|facts|code|theory|policy|research",
  "mode": "general|research|theory|code",
  "cwd": "...",
  "workspace_ref": "optional WSP-*",
  "project_ref": "optional PRJ-*",
  "task_ref": "optional TASK-*",
  "current_reason_ref": "optional REASON-*"
}
```

### 5.3 Required Output

```json
{
  "contract_version": "0.4",
  "lookup_is_proof": false,
  "focus": {
    "workspace_ref": "WSP-*",
    "project_ref": "PRJ-*|null",
    "task_ref": "TASK-*|null",
    "wctx_ref": "WCTX-*"
  },
  "ranked_context": [],
  "chain_candidates": [],
  "route_graph": {},
  "curiosity": {},
  "telemetry": {
    "event_ref": "TEL-*|null",
    "raw_records_returned": 0
  },
  "repair": []
}
```

### 5.4 Ranking Formula

Implementations may tune numeric weights, but the ordering constraints are
mandatory.

Base weights:

- current MODEL/FLOW: `100`
- current confirmed/theory CLM: `80`
- current meta corpus CLM: `75`
- current code CLM: `70`
- current runtime CLM with RUN: `55`
- tentative compatible CLM: `35`
- resolved/historical CLM: `15`
- CIX/backend/map hit: `10`

Adjustments:

- same workspace: `+20`
- same project: `+15`
- current task/WCTX link: `+15`
- exact query/topic match: `+10`
- linked from current REASON branch as unused extension: `+10`
- unresolved contradiction: `-30` and mark `contested`
- stale lifecycle: cap final score at `25`
- archived lifecycle: cap final score at `5`, explicit drill-down only

Constraints:

- CIX/backend/map hits cannot outrank proof-capable records in fact lookup.
- Meta claims can outrank many scattered runtime observations for orientation,
  but cannot satisfy object-level proof without drill-down.
- Runtime CLM cannot outrank confirmed theory for theory/model lookup.
- Resolved/historical cannot appear before active records unless regression
  route applies.

### 5.5 Chain Extension Mode

If `current_reason_ref` exists, lookup must:

- load current REASON chain refs
- avoid returning the same refs as primary chain candidates
- prefer unused support, contrasting facts, open questions, or compatible
  hypotheses
- if no new candidate exists, return fallback branches:
  `fork_reason`, `record_hypothesis`, `ask_open_question`, `retrospective`

This prevents reusable-permit behavior.

## 6. Evidence Capture Contract

### 6.1 Agent Input

Agent supplies support, not record internals.

```json
{
  "kind": "file-line|url|command-output|user-input|artifact",
  "quote": "...",
  "claim_text": "optional",
  "path": "optional",
  "line_start": 1,
  "line_end": 1,
  "url": "optional",
  "command": "optional",
  "input_ref": "optional INP-*",
  "artifact_ref": "optional ART-*"
}
```

### 6.2 Runtime Output

```json
{
  "created_refs": {
    "input_ref": "INP-*|null",
    "file_ref": "FILE-*|null",
    "artifact_ref": "ART-*|null",
    "run_ref": "RUN-*|null",
    "source_ref": "SRC-*",
    "claim_ref": "CLM-*|null"
  },
  "links": [
    {"from": "FILE-*", "to": "ART-*", "relation": "snapshot"},
    {"from": "SRC-*", "to": "FILE-*", "relation": "provenance"}
  ],
  "repair": []
}
```

### 6.3 Validation Rules

- Missing quote blocks source creation unless metadata-only capture is
  explicitly allowed.
- File-line evidence verifies path existence and quote/range when local file is
  available.
- URL evidence stores URL metadata and may copy content to ART when allowed.
- Command output evidence requires RUN.
- User-input evidence requires INP.
- Claim creation is optional; source creation is mandatory after accepted
  evidence capture.

## 7. Evidence Chain Validation

### 7.1 Roles

Allowed node roles:

- `fact`
- `observation`
- `hypothesis`
- `exploration_context`
- `permission`
- `requested_permission`
- `observation_summary`
- `conflict_summary`
- `gap_summary`
- `quality_summary`
- `restriction`
- `guideline`
- `proposal`
- `task`
- `working_context`
- `project`
- `model`
- `flow`
- `open_question`

### 7.2 Modes

`proof`: no unsupported hypothesis or exploration context.

`planning`: facts plus compatible hypotheses allowed.

`proposal`: facts plus compatible hypotheses and critique allowed.

`permission`: must cite permission/restriction/task facts and intended action.

`final`: must cite the chain supporting the user-facing conclusion, or explicitly
state that the answer is exploratory.

`debug`: runtime observations and hypotheses allowed, but durable conclusions
must remain tentative.

Meta chain roles:

- `observation_summary` may cite `meta_aggregate`.
- `conflict_summary` may cite `meta_conflict`.
- `gap_summary` may cite `meta_gap`.
- `quality_summary` may cite future `meta_evidence_quality`.
- Summary roles are valid for orientation, planning, debugging, proposal, and
  permission context.
- Summary roles do not satisfy object-level proof unless the chain also cites
  representative underlying `CLM-*`/`SRC-*`/`RUN-*` records.

### 7.3 Validation Error Taxonomy

Errors:

- `missing_quote`
- `quote_mismatch`
- `unknown_ref`
- `navigation_used_as_proof`
- `control_used_as_truth`
- `hypothesis_used_as_proof`
- `hypothesis_on_hypothesis`
- `runtime_without_run`
- `model_flow_authority_violation`
- `meta_claim_used_as_object_proof`
- `workspace_scope_mismatch`
- `task_scope_mismatch`
- `contradiction_unhandled`
- `duplicate_reason_chain`

Warnings:

- `legacy_source_without_surface`
- `resolved_claim_used`
- `stale_claim_used`
- `low_independence_support`
- `weak_hypothesis_compatibility_check`

Every error must include a repair suggestion.

### 7.4 Hypothesis Compatibility

0.4.0 does not need a complete theorem prover.

It must implement a conservative compatibility check:

- reject direct `comparison` contradictions with active supported facts
- reject use of a hypothesis as proof for another hypothesis
- reject theory built on a staleness hypothesis unless staleness has support
- mark predicate/logic conflicts as candidate conflicts
- allow multiple competing hypotheses when all fit known facts

The output must distinguish:

- `compatible_hypothesis`
- `competing_hypothesis`
- `contradicted_hypothesis`
- `untested_exploration_hypothesis`

## 8. REASON, GRANT, RUN

### 8.1 REASON Record

Required fields:

```json
{
  "id": "REASON-*",
  "workspace_ref": "WSP-*",
  "project_ref": "PRJ-*|null",
  "task_ref": "TASK-*",
  "wctx_ref": "WCTX-*",
  "agent_identity_ref": "AGENT-*",
  "parent_reason_ref": "REASON-*|null",
  "branch": "main",
  "mode": "planning|edit|test|debug|permission|final",
  "intent": "...",
  "chain": {},
  "chain_hash": "...",
  "previous_seal": "...",
  "seal": "...",
  "pow": {"difficulty": 0, "nonce": "..."},
  "created_at": "..."
}
```

Rules:

- append-only JSONL ledger
- direct file writes blocked by hooks
- validator verifies hash chain and parent existence
- validator rejects WCTX/agent identity mismatch
- same-mode direct continuation on same branch must change chain hash
- forks may parent any earlier REASON in the same task

### 8.2 GRANT Record

Required fields:

```json
{
  "id": "GRANT-*",
  "reason_ref": "REASON-*",
  "workspace_ref": "WSP-*",
  "project_ref": "PRJ-*|null",
  "task_ref": "TASK-*",
  "wctx_ref": "WCTX-*",
  "agent_identity_ref": "AGENT-*",
  "mode": "edit|test|permission|final",
  "action_kind": "bash|file-write|mcp-write|git|final",
  "cwd": "...",
  "command_hash": "optional",
  "valid_from": "...",
  "valid_until": "...",
  "context_fingerprint": "..."
}
```

Rules:

- GRANT is not mutable and has no `used` flag.
- Use is inferred from linked RUN/protected record timestamps.
- GRANT is valid only when the current WCTX owner matches `agent_identity_ref`.
- Protected action must occur inside the grant window.
- Final response may require final GRANT in autonomous mode.

### 8.3 RUN Record

Required fields:

```json
{
  "id": "RUN-*",
  "workspace_ref": "WSP-*",
  "project_ref": "PRJ-*|null",
  "task_ref": "TASK-*|null",
  "grant_ref": "GRANT-*|null",
  "cwd": "...",
  "command": "...",
  "command_hash": "...",
  "started_at": "...",
  "finished_at": "...",
  "exit_code": 0,
  "output_quotes": []
}
```

Rules:

- Mutating shell commands must produce RUN when hooks can observe the command.
- Read-only shell commands may produce RUN when their output supports a CLM.
- Runtime CLM must transitively reach RUN.

## 9. Task, Plan, Debt, And Retrospective

### 9.1 Task Validity

TASK states:

- `draft`
- `atomic`
- `decomposed`
- `active`
- `blocked`
- `done`
- `cancelled`

Rules:

- Active work requires `atomic` or `decomposed`.
- `decomposed` requires at least one subtask or subplan.
- Subtasks must be one-iteration sized.
- Parent task cannot be `done` while blocking child task/plan/debt/open question
  remains active.

### 9.2 Plan And Debt

PLN required semantics:

- task/workspace/project refs
- goal
- status
- ordered steps or linked subtasks
- blockers

DEBT required semantics:

- task/workspace/project refs
- reason
- impact
- priority
- exclusion condition
- owner or follow-up route

Rules:

- Agents may defer work only by creating linked PLAN/DEBT/OPEN records.
- Deferral without linked record is invalid for autonomous `done`.

### 9.3 Retrospective

When task type changes, `next-step` should offer retrospective lookup for prior
same-type tasks in the workspace.

Retrospective is navigation. It can suggest useful prior REASON/PLAN/DEBT/MODEL
records but cannot prove current facts.

## 10. Curator Mode

Curator is an organizational mode for fact maintenance.

Input is a bounded pool, not raw global browsing:

```json
{
  "pool_ref": "CURP-*",
  "workspace_ref": "WSP-*",
  "project_refs": [],
  "record_refs": [],
  "purpose": "deduplicate|contradictions|model-update|flow-update|stale-review",
  "max_items": 50
}
```

Curator may:

- identify duplicates
- identify contradiction candidates
- propose MODEL/FLOW updates
- ask user questions
- propose lifecycle changes
- propose source/claim repairs

Curator may not:

- browse raw global records outside its pool
- mutate truth records without normal write contracts
- use backend/map output as proof

Pool construction:

- starts from lookup/topic/telemetry/map candidates
- capped by settings
- includes why each item is in the pool
- supports paging

## 11. Backend Scope

Backend index layers:

- project: default
- workspace: optional when cross-project context is needed
- global: rare, explicit, never default

Rules:

- `backend-status` must report selected backend and readiness per scope.
- A backend can be `installed` but not `search_ready`.
- Search cannot report ready only because storage exists.
- Project search must not require repo pollution unless settings explicitly
  allow markers/symlinks.
- Workspace search must be requested through route graph, not hidden fallback.
- Backend hits are navigation and must be linkable into CIX/CLM/MODEL/FLOW only
  through review/write contracts.

## 12. Curiosity And Map

Curiosity map is navigation for agent attention and visual thinking. It is a
cognitive fact map: a bounded map session that shows the agent support anchors,
ignored-but-relevant facts, bridges, tensions, and inquiry pressure without
exposing raw records.

It must expose:

- clusters
- bridge candidates
- cold zones
- hot zones
- anchor facts
- ignored but relevant facts
- bridge facts
- tension facts
- tap smell with decay
- neglect pressure for cold connected facts
- inquiry pressure around facts with many hypotheses or tentative branches
- promotion pressure for hot facts that should become MODEL/FLOW candidates
- missing-link probes
- mode filter: `general`, `research`, `theory`, `code`
- volume setting: `compact`, `normal`, `wide`

Rules:

- Map data is never proof.
- Missing link does not prove absence of relation.
- The map may induce curiosity by showing bounded probes, not by dumping raw
  records.
- The map must distinguish established links from candidate, rejected, missing,
  and unknown links.
- Candidate links must not glue topology clusters.
- Map sessions are operational state and may be persisted in `WCTX-*`.
- Map tools do not automatically create truth, task, debt, proposal, or open
  question records.
- Map drill-down returns proof routes such as lookup, record detail, chain
  augmentation, and validation. It is not proof.
- HTML map is optional for 0.4.0; MCP text/JSON map navigation is the required
  agent-facing route data.

## 13. Telemetry

Minimum telemetry counters:

- lookup calls by reason/kind/mode
- raw record read attempts
- missing workspace/WCTX/focus events
- reason validation failures
- duplicate reason-chain rejections
- grant misses and grant successes
- runtime CLM without RUN rejections
- MODEL/FLOW promotion rejections
- backend readiness failures
- hot record repeated reads
- lookup fallback to resolved/historical records

Acceptance targets for 0.4 smoke tests:

- normal fact work uses lookup before record-detail
- raw CLM reads are zero unless test explicitly exercises escape hatch
- protected action without GRANT is blocked
- final autonomous answer without final REASON is blocked
- repeated hot-record reads produce MODEL/FLOW suggestion or telemetry warning

## 14. Error And Repair Contract

All blocking responses must include:

```json
{
  "blocked": true,
  "reason": "machine_readable_reason",
  "message": "short human-readable explanation",
  "repair": [
    {
      "command": "next command or tool",
      "why": "why this fixes the block",
      "required_inputs": {}
    }
  ]
}
```

Rules:

- No dead-end block when safe lookup/reason/repair exists.
- Repair route should be shorter than the policy explanation.
- Hook messages should be concise and route-oriented.

## 15. Required Test Matrix

Deterministic tests:

- missing workspace blocks durable work
- foreign repo requires admission
- lookup creates/requires WCTX when workspace explicit
- lookup ranking obeys authority constraints
- chain extension avoids already-used refs
- new SRC without provenance surface rejected
- runtime CLM without RUN rejected
- MODEL/FLOW from tentative/runtime-only rejected
- MODEL/FLOW from meta-only decisive support rejected
- meta claim used as object-level proof rejected unless underlying support is
  present
- hypothesis-on-hypothesis rejected in proof mode
- same-branch duplicate REASON rejected
- protected mutation without GRANT rejected
- resolved bug plus new symptom creates regression branch
- backend status reports search readiness, not just storage existence

Live-agent tests:

- agent follows route graph for a small coding task
- agent records competing hypotheses for underdetermined reasoning task
- agent asks/records open question when chain has a gap
- agent uses retrospective route for same-type task
- agent does not read raw CLM in normal fact lookup
- agent finalizes autonomous task only after final REASON

## 16. Closed Logical Gaps

This spec closes the previously open gaps as follows:

- Runtime claim authority: closed by authority classes and ranking constraints.
- SRC graph-v2: closed by required provenance surfaces and legacy-only warning.
- Hypothesis compatibility: closed by conservative comparison/logic checks and
  explicit compatibility classes.
- Planning gate pressure: closed by `lookup -> reason-step -> preflight` route
  and repair contract.
- Curator pool: closed by bounded pool input and allowed outputs.
- Backend scope: closed by project/workspace/global readiness policy.
- Historical context: closed by fallback ranking and regression branch.
- Token pressure: closed by telemetry counters and acceptance targets.

Remaining future work is implementation depth, not unresolved system logic.
