# Codex Context

This directory stores durable, reconstructable project memory for the Trust Evidence Protocol.

## Canonical Layers

- `records/` contains the only canonical structured records
- `artifacts/` contains canonical referenced payloads such as logs, JSON snapshots, copied outputs, or screenshots
  - artifact refs may be root-relative (`artifacts/...`) or record-relative (`../../artifacts/...`)

## Non-Canonical Layer

- `review/` contains generated diagnostics only
- `review/attention.md` is a generated navigation view only
- `review/resolved.md` is a generated lifecycle/navigation view only
- `topic_index/` contains generated lexical prefilter data only
- `logic_index/` contains generated predicate checking/navigation data only
- `runtime/` contains generated hydration state only
- `archives/` contains restorable cleanup zip archives and sidecar manifests only
- `settings.json` contains runtime policy only
  - `input_capture` controls prompt/session capture
  - `artifact_policy` controls reference-vs-copy behavior for large inputs
  - `cleanup` controls archive/delete staging and stale thresholds

Cleanup archives are reversible by command, not by manual unzip. Use
`cleanup-archives` to find an `ARC-*`, then run
`cleanup-restore --archive ARC-* --dry-run` first; `--apply` restores missing
files only after manifest hash verification and refuses conflicting overwrites.

## Hard Rules

- one file = one record
- filename must equal record `id`
- records must be canonical JSON objects
- new 0.4 records use `contract_version` for the public contract and
  `record_version` for the concrete record shape
- canonical data must not be stored in aggregate ledgers
- claims must cite explicit `source_refs`
- claims that should participate in automatic contradiction scans must define a structured `comparison` object
- claim `status` is truth state; claim `lifecycle.state` is retrieval/attention state
- `resolved` and `historical` claims remain searchable but are fallback-only
- `archived` claims are explicit-reference/audit material and must not appear in normal task context
- records should use `workspace_refs` for memory boundaries, `project_refs` for project boundaries, and `task_refs` for task-local scope
- reusable coding, testing, review, debugging, architecture, or agent-behavior rules belong in `GLD-*` guideline records
- constructive agent critique and solution options belong in `PRP-*` proposal records
- proposal assumptions may guide discussion, but must not be used as proof in evidence chains
- fresh unlinked `INP-*` input records are not cleanup garbage; archive them only after `settings.cleanup.orphan_input_stale_after_days`
- working context, topic overlap, and generated views may guide lookup, but must not be used as proof
- `MAP-*` records are durable navigation cells only; drill down through
  `proof_routes` before using proof-capable records
- `CLM.logic` atoms/rules are projections of claims; generated `logic_index/` output must not be used as proof
- `accepted-deviation` steps in flows require an explicit user-backed anchor; scoped permission may authorize action, but it does not prove truth
- memory records do not become proof by virtue of being persisted
- generated files in `review/` must not be manually edited
- generated attention/brief views must be used for navigation, not proof
- plugin-mediated writes are serialized through `runtime/write.lock`
- records and generated files are written through atomic same-directory replace

## Layout

```text
.tep_context/
  README.md
  index.md
  backlog.md
  records/
    agent_identity/
    workspace/
    project/
    input/
    file/
    run/
    source/
    claim/
    permission/
    restriction/
    guideline/
    proposal/
    action/
    task/
    working_context/
    map/
    curator_pool/
    plan/
    debt/
    model/
    flow/
    open_question/
  artifacts/
  archives/
  hypotheses.jsonl
  topic_index/
  logic_index/
  review/
    attention.md
    resolved.md
  runtime/
```

## Record IDs

Use these prefixes with date plus random suffix:

- `INP-YYYYMMDD-xxxxxxxx`
- `FILE-YYYYMMDD-xxxxxxxx`
- `RUN-YYYYMMDD-xxxxxxxx`
- `SRC-YYYYMMDD-xxxxxxxx`
- `CLM-YYYYMMDD-xxxxxxxx`
- `PRM-YYYYMMDD-xxxxxxxx`
- `RST-YYYYMMDD-xxxxxxxx`
- `GLD-YYYYMMDD-xxxxxxxx`
- `PRP-YYYYMMDD-xxxxxxxx`
- `ACT-YYYYMMDD-xxxxxxxx`
- `PRJ-YYYYMMDD-xxxxxxxx`
- `TASK-YYYYMMDD-xxxxxxxx`
- `WCTX-YYYYMMDD-xxxxxxxx`
- `MAP-YYYYMMDD-xxxxxxxx`
- `CURP-YYYYMMDD-xxxxxxxx`
- `PLN-YYYYMMDD-xxxxxxxx`
- `DEBT-YYYYMMDD-xxxxxxxx`
- `MODEL-YYYYMMDD-xxxxxxxx`
- `FLOW-YYYYMMDD-xxxxxxxx`
- `OPEN-YYYYMMDD-xxxxxxxx`

The suffix is 8 lowercase hex characters generated independently per record.
Legacy sequential ids such as `CLM-YYYYMMDD-NNNN` remain valid for existing contexts, but new records should not use sequential allocation.

## Record Templates

Use the templates bundled with the plugin:

- `templates/codex_context/input.json`
- `templates/codex_context/map.json`
- `templates/codex_context/source.json`
- `templates/codex_context/claim.json`
- `templates/codex_context/permission.json`
- `templates/codex_context/restriction.json`
- `templates/codex_context/guideline.json`
- `templates/codex_context/proposal.json`
- `templates/codex_context/action.json`
- `templates/codex_context/project.json`
- `templates/codex_context/task.json`
- `templates/codex_context/working_context.json`
- `templates/codex_context/curator_pool.json`
- `templates/codex_context/plan.json`
- `templates/codex_context/debt.json`
- `templates/codex_context/model.json`
- `templates/codex_context/flow.json`
- `templates/codex_context/open_question.json`

## Settings

`.tep_context/settings.json` is the policy layer, not a canonical fact record.

It currently stores:

- `allowed_freedom`
- `current_workspace_ref`
- `current_project_ref`
- `current_task_ref`
- repo-local Codex hook modes under `hooks`
- token/output budget preferences under `context_budget`
- optional analysis backend policy under `analysis`

Default hook modes:

- `hooks.enabled = true`
- `hooks.session_start_hydrate = "on"`
- `hooks.user_prompt_notice = "remind"`
- `hooks.pre_tool_use_guard = "enforce"`
- `hooks.post_tool_use_review = "invalidate"`
- `hooks.stop_guard = "enforce"`
- `hooks.verbosity = "normal"`

Context budget defaults:

- `context_budget.hydration = "normal"`
- `context_budget.brief = "normal"`
- `context_budget.quotes = "normal"`
- `context_budget.guidelines = "normal"`
- `context_budget.record_details = "on-demand"`

Default analysis backend policy:

- `analysis.logic_solver.backend = "structural"` with optional `z3`
- `analysis.logic_solver.mode = "candidate"`
- `analysis.logic_solver.install_policy = "ask"`
- `analysis.topic_prefilter.backend = "lexical"` with optional `nmf`
- `analysis.topic_prefilter.rebuild = "manual"`
- `analysis.topic_prefilter.install_policy = "ask"`

The `analysis` block controls optional mechanical helpers.
It does not prove facts, does not install dependencies by itself, and must not let generated indexes replace canonical records.

Logic vocabulary pressure:

- `logic_index/variable_graph.json` is generated symbol/predicate/rule-variable graph data, not proof
- `logic_index/vocabulary_smells.md` reports orphan symbols, duplicate-like symbols, single-use predicates, and weak/generic rule variables
- new logic symbols should include a `meaning` field explaining what semantic object they represent

## Additional Layers

- `model` records capture the current evidence-backed picture for one `scope + aspect`
- `flow` records capture integrated process understanding with `preconditions` and `oracle`
- `open_question` records capture deferred uncertainty without interrupting the user
- `task` records capture execution focus and `task_type`; they do not prove claims or grant permission
- `working_context` records capture operational focus, pinned refs, local assumptions, concerns, and handoff context; they do not prove claims or grant permission
- `guideline` records capture reusable operational rules; they guide work but do not prove truth
- `proposal` records capture constructive agent position, critique, concrete options, and stop conditions; they do not prove truth or grant permission
- `workspace` records capture memory boundaries; records should link to them with `workspace_refs`
- `project` records capture optional narrower boundaries inside a workspace; records may link to them with `project_refs`
- `restriction` records capture global, project, or task-scoped constraints; they do not prove truth
- `permission` records may be global, project-scoped, or task-scoped through `applies_to`, `project_refs`, and `task_refs`
- `hypotheses.jsonl` is an index of active tentative `CLM-*` records, not a second source of truth
- `topic_index/` is a generated lexical prefilter over records, not a second source of truth
- `logic_index/` is a generated predicate projection over `CLM.logic`, not a second source of truth

## Comparable Claims

Narrative claims may use only `statement`.

Claims that should be scanned for contradictions should also define:

- `comparison.key`: normalized identity of the compared fact
- `comparison.subject`: what the fact is about
- `comparison.aspect`: which property is being asserted
- `comparison.comparator`: currently `exact` or `boolean`
- `comparison.value`: scalar comparable value
- `comparison.polarity`: `affirmed` or `denied`
- `comparison.context_scope`: optional narrower comparison scope

## Auxiliary Taxonomy

The plugin may attach auxiliary classification fields to `source` and `claim` records.

These fields do not replace:

- `source_kind`
- `critique_status`
- `claim.status`
- `allowed_freedom`

Use them as review metadata, not as proof mechanics.

`source` may additionally define:

- `confidence`: `high | moderate | low`
- `red_flags`: short labels such as `out-of-context`, `circular-sourcing`, `urgency-framing`

`claim` may additionally define:

- `claim_kind`: `factual | implied | statistical | opinion | prediction | unfalsifiable`
- `confidence`: `high | moderate | low`
- `red_flags`: short labels such as `implied-claim`, `needs-origin-trace`, `numbers-without-baseline`
- `lifecycle.state`: `active | resolved | historical | archived`
- `lifecycle.attention`: `normal | low | fallback-only | explicit-only`
- `lifecycle.resolved_by_claim_refs` / `lifecycle.resolved_by_action_refs`: optional anchors explaining why an active claim became fallback-only
- `lifecycle.reactivation_conditions`: conditions that should make a fallback claim relevant again
- `logic.symbols`: typed symbol introductions such as `person:alice`
- `logic.atoms`: predicate atoms such as `Student(person:alice)`
- `logic.rules`: Horn-style rules such as `Student(?x) -> ExpectedPassesExam(?x)`

Compatibility rule:

- `opinion`, `prediction`, and `unfalsifiable` claims should remain `tentative` until rewritten as checkable factual claims
- resolved/historical claims may still be true historical facts; do not change `status` just to reduce retrieval priority
- new actions, active hypotheses, and working/stable models or flows must not use lifecycle fallback claims as current support

## Plans And Debt

`plan` and `debt` are canonical record types, not aggregate ledgers.

- `plan` is for persistent, evidence-backed intended work
- `debt` is for persistent, evidence-backed known liabilities
- both require explicit `priority`
- generated `backlog.md` shows only active items and excludes terminal statuses
