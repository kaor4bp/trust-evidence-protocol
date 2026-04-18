# TEP Core Rewrite Working Context

This document is the local working contract for the first rebuild phase of the
Trust Evidence Protocol plugin.

It is intentionally practical. It describes what the next implementation slices
must preserve, what may break during beta, which migrations are required, and
which work is explicitly deferred.

Read "rebuild" literally. This is not a cosmetic refactor. The plugin may change
shape substantially, but the core data and reasoning contracts must stay
auditable or be migrated deliberately.

For the current pre-rebuild surface, see `docs/dev/TEP_CORE_BASELINE.md`.

## User Decisions

The rebuild is allowed to make breaking changes while TEP is still in beta.
Breaking now is better than preserving weak contracts, but every breaking change
must include a migration path for existing `.codex_context` data.

The priority order is:

1. stable core
2. cleaner architecture and testable module seams
3. feature implementation
4. MCP polish and visibility
5. full live-agent conformance pass before publication

The next public release should accumulate several internal iterations instead of
publishing after every small slice.

Docker live-agent tests may be used for experiments and debugging, but the full
live-agent suite is not part of the normal inner-loop gate. The user will decide
when to run the full live pass.

## Evidence Base

The rebuild is justified by existing records:

- `MODEL-20260418-8294c4f3`: TEP is a runtime where canonical records prove,
  generated indexes navigate, and CLI/hooks/MCP enforce or accelerate.
- `CLM-20260418-7e124690`: the refactor should use the normative developer
  reference, data model spec, and research map as contracts.
- `CLM-20260418-e1492e59`: `context_cli.py` and `context_lib.py` are
  over-concentrated and hard to test.
- `CLM-20260418-0afba8ad`: deterministic runtime/CLI/hooks/MCP tests pass.
- `CLM-20260418-c707d6d2`: coverage reporting works for the deterministic
  Python plugin surface.
- `PRP-20260418-c4814d41`: extract pure domain modules first instead of doing a
  wholesale rewrite.

## Core Definition

The TEP core is the smallest runtime layer that makes the resolved TEP context
root safe, auditable, and reusable.
The target live root is one global `~/.tep_context`; legacy repo-local
`.codex_context` remains a migration fallback.

Core responsibilities:

- canonical record storage and ID generation
- schema validation and semantic validation
- record links and referential integrity
- settings and runtime policy loading
- context-root discovery and legacy fallback
- generated navigation indexes and review reports
- deterministic search over canonical records and generated indexes
- migration framework for breaking data or command changes
- thin CLI entrypoints over importable services
- hook gates that use the same services as CLI
- read-only MCP adapters over the same services

The core must not depend on LLM judgment. LLM-facing workflows may use the core,
but the core must remain deterministic where practical.

## Non-Core For First Iteration

These are important, but should not block the first core rewrite slice:

- full MCP visibility/debugging in Codex app
- Z3/Datalog/ML/NMF backends
- code-part index expansion beyond current CIX behavior
- new explanatory-chain runtime implementation
- new curiosity runtime commands
- UI customization
- full live-agent conformance suite

The rebuild should keep extension points for these areas, but not implement them
as part of the first architectural slice.

## Contracts That Must Survive

Canonical semantics must survive every rebuild slice:

- `SRC-*` carries provenance.
- `CLM-*` is the only truth record type.
- `PRM-*`, `RST-*`, `GLD-*`, `PRP-*`, `TASK-*`, `WCTX-*`, `PLN-*`, `DEBT-*`,
  `MODEL-*`, `FLOW-*`, and CIX records guide action or navigation but do not
  prove truth by themselves.
- generated indexes and review views are navigation only.
- `.codex_context/settings.json` is runtime policy, not truth.
- context validation must reject broken references and invalid state
  combinations.
- records must be written through plugin commands/services when available.

Behavioral contracts:

- `review-context`, `reindex-context`, `validate`, and hydration must remain
  deterministic gates.
- hook classification must avoid known false positives on read-only commands.
- records and indexes must remain safe under repeated reindexing.
- lifecycle fallback records must stay searchable without dominating current
  retrieval.
- command failures should identify the bad record or policy decision instead of
  failing as an opaque flow error.

## Allowed Breaking Changes

Breaking changes are allowed when they improve the core contract.

Allowed examples:

- command arguments may be renamed or grouped if compatibility shims or migration
  notes exist
- generated index formats may change because they are rebuildable
- record schemas may tighten if a migration updates old records
- settings format may change if a migration preserves equivalent policy
- internal module paths may change freely

Not allowed without explicit migration and tests:

- changing the meaning of record types
- weakening provenance requirements
- turning generated views into proof
- dropping existing canonical records
- changing lifecycle semantics silently
- breaking existing `.codex_context` directories without a repair command

## Migration Requirements

Every breaking data change must provide:

- a migration script or command
- dry-run output
- backup or rollback guidance
- a human-readable migration report
- tests over at least one old-context fixture
- post-migration `review-context` and `reindex-context` success

Migration should prefer explicit commands such as:

```text
context_cli.py migrate-context --from <version> --to <version> --dry-run
context_cli.py migrate-context --from <version> --to <version> --apply
```

If command names change, the old command should either remain as a shim for one
beta cycle or fail with a precise replacement message.

## Target Module Shape

The first rebuild phase should move behavior toward importable modules:

```text
plugins/trust-evidence-protocol/
  tep_runtime/
    actions.py
    claims.py
    ids.py
    paths.py
    records.py
    schemas.py
    validation.py
    working_contexts.py
    settings.py
    links.py
    migrations.py
    reports.py
    display.py
    generated_views.py
    knowledge.py
    rollback.py
    context_brief.py
    flows.py
    guidelines.py
    models.py
    notes.py
    open_questions.py
    planning.py
    permissions.py
    projects.py
    restrictions.py
    search.py
    sources.py
    tasks.py
    policy.py
    logic.py
    logic_index.py
    logic_check.py
    logic_z3.py
    reasoning_case.py
    cli/
      registry.py
      commands_*.py
```

`context_cli.py` should become a thin adapter:

- parse arguments
- call a registered command handler
- print command result
- return an exit code

It should not contain domain validation, record mutation logic, report
generation, or hook policy.

`context_lib.py` should be split by domain responsibility. It may remain as a
temporary compatibility facade while imports are migrated.

## First Rebuild Slices

### Slice 0: Working Contract

Create this document and link it from the normative docs.

Success:

- future agents can inspect one document to understand the first rebuild phase
- breaking-change policy and migration expectations are explicit

### Slice 1: Baseline Characterization

Map current command behavior, record schemas, and report outputs before moving
code.

Success:

- command matrix exists
- deterministic baseline tests still pass
- current context validates and hydrates
- no behavior changes yet

### Slice 2: Pure Core Extraction

Extract low-risk pure modules first:

- IDs
- path resolution
- record load/save/list
- link traversal
- settings load/save
- validation helpers

Success:

- direct unit tests cover extracted modules
- subprocess CLI tests still pass
- `context_cli.py` and `context_lib.py` shrink without behavior change

Current first extraction:

- `tep_runtime/context_root.py`: global `~/.tep_context`, `TEP_CONTEXT_ROOT`,
  explicit `--context`, and legacy `.codex_context` discovery
- `tep_runtime/actions.py`: action payload and planned/executed timestamp
  helpers
- `tep_runtime/claims.py`: claim lifecycle, retrieval, fallback-action checks,
  and claim payload helpers
- `tep_runtime/errors.py`: shared `ValidationError`
- `tep_runtime/paths.py`: context path helpers
- `tep_runtime/io.py`: JSON/text atomic writes and context write lock
- `tep_runtime/ids.py`: timestamp and random-suffix id allocation
- `tep_runtime/sources.py`: source payload and default independence-group
  helpers
- `tep_runtime/tasks.py`: task payload construction, pure lifecycle mutation,
  drift-check payload/rendering, and precedent-review selection/rendering
  helpers
- `tep_runtime/settings.py`: runtime settings normalization/load/save,
  strictness approval request IO/checks, and semantic settings-state validation
- `tep_runtime/policy.py`: runtime policy helpers shared by CLI and hook gates,
  including action-kind mutation classification
- `tep_runtime/records.py`: record and code-index entry loading
- `tep_runtime/schemas.py`: canonical record type/status constants, artifact
  reference checks, per-record schema validation, and typed reference validation
- `tep_runtime/state_validation.py`: state-level validation orchestration over
  record schemas, refs, logic, code index, settings, hypotheses, and runtime
  policy
- `tep_runtime/cli_common.py`: shared CLI display, generated-output refresh,
  candidate/mutated-record persistence, payload normalization, and command
  write-lock policy helpers
- `tep_runtime/hydration.py`: hydration state, context fingerprinting, and
  invalidation helpers
- `tep_runtime/reports.py`: generated report rendering primitives and
  validation-report writing
- `tep_runtime/display.py`: public record summary line renderers for project,
  restriction, guideline, claim, and source records
- `tep_runtime/generated_views.py`: generated stale/model/flow/hypothesis,
  attention, resolved, backlog, dependency-impact, and index views
- `tep_runtime/validation.py`: shared schema helper primitives for list/object
  normalization, optional confidence, and optional red-flag validation
- `tep_runtime/working_contexts.py`: working-context assumption parsing,
  payload construction, fork mutation, close mutation, summary/detail
  rendering, and show payload helpers
- `tep_runtime/code_index.py`: CIX constants, smell taxonomies, AST/text
  metadata extraction, manual entry payload construction, generated code-index
  views, entry freshness/projection, smell row selection, entry persistence,
  search/smell result rendering, smell report payloads, entry validation, and
  state-level code-index reference validation
- `tep_runtime/logic.py`: CLM.logic constants, CLI logic spec parsing,
  atom/rule/schema validation, symbol extraction, and state-level symbol
  introduction validation
- `tep_runtime/logic_index.py`: generated CLM.logic index payloads/reports,
  predicate conflict candidates, vocabulary graph construction, variable
  analysis, and vocabulary smell pressure reports
- `tep_runtime/logic_check.py`: logic-check solver selection, solver settings
  lookup, structural result payload/text rendering, and Z3 text rendering
- `tep_runtime/conflicts.py`: claim comparison CLI payload construction,
  constants/schema checks, comparison signatures, generated conflict-line
  collection, and conflict report writing
- `tep_runtime/claims.py`: claim lifecycle, lifecycle mutation payloads,
  attention, retrieval tier, fallback action-blocking helpers, and claim payload
  helpers
- `tep_runtime/cleanup.py`: read-only cleanup candidate diagnostics for stale
  lifecycle attention, fallback dependencies, and active hypothesis pointers
- `tep_runtime/flows.py`: flow step, precondition, oracle, full payload, and
  domain promotion helpers
- `tep_runtime/guidelines.py`: guideline scope resolution and payload helpers
- `tep_runtime/models.py`: model payload and domain promotion helpers
- `tep_runtime/notes.py`: shared note formatting helpers
- `tep_runtime/open_questions.py`: open-question payload helpers
- `tep_runtime/planning.py`: plan and debt payload helpers
- `tep_runtime/permissions.py`: permission scope resolution and payload helpers
- `tep_runtime/projects.py`: project payload and assignment mutation helpers
- `tep_runtime/proposals.py`: proposal option parsing, proposal payload
  construction, and proposal summary formatting
- `tep_runtime/restrictions.py`: restriction scope resolution and payload
  helpers
- `tep_runtime/links.py`: dependency reference extraction, reference field-path
  lookup, canonical link-edge construction, linked-record graph payloads, and
  record-detail payload/text rendering
- `tep_runtime/scopes.py`: current project/task refs, write-scope defaults,
  record relevance filters, and permission/restriction/guideline applicability
- `tep_runtime/search.py`: deterministic record search text, scoring, scoped
  ranked record search, concise formatting, and public summary helpers
- `tep_runtime/retrieval.py`: scope-aware record selection, explicit-ref
  retrieval, lifecycle fallback-claim selection, and active permission/guideline
  selection
- `tep_runtime/topic_index.py`: lexical task terms, topic tokenization,
  generated topic-index payloads/reports, topic-search matching, topic-conflict
  prefilter candidates, and working-context topic inference
- `tep_runtime/hypotheses.py`: `hypotheses.jsonl` load/save, entry mutation
  helpers, semantic validation, model/flow claim reference collection, active
  hypothesis selection, and evidence-chain hypothesis lookup
- `tep_runtime/knowledge.py`: shared MODEL/FLOW stale-target selection and
  stale payload construction helpers
- `tep_runtime/rollback.py`: impact graph and rollback report payload
  construction and text rendering helpers
- `tep_runtime/context_brief.py`: `brief-context` record selection, text
  rendering, and shared project/restriction/guideline/task detail renderers
- `tep_runtime/evidence.py`: quote normalization, quote item joining, and
  evidence-chain quote matching against records and their source quotes
- `tep_runtime/reasoning.py`: pure evidence-chain node/edge validation, role
  constraints, lifecycle proof blocking, proof/support edge checks, and
  validation-report rendering
- `tep_runtime/reasoning_case.py`: `build-reasoning-case` record selection,
  diagnostics, and text rendering
- `context_lib.py` remains a compatibility facade for existing CLI, hooks, MCP,
  and migration scripts
- direct tests live in `tests/trust_evidence_protocol/test_core_services.py`

### Slice 3: Validation And Migration Core

Separate schema validation, semantic validation, and migrations.

Success:

- validation can be unit-tested without invoking the CLI
- migration dry-run/apply shape is defined
- old fixture contexts can be validated or migrated

### Slice 4: CLI Command Registry

Move command handlers behind a registry and reduce dispatch branching.

Success:

- command names remain discoverable
- command implementations are small and grouped by domain
- error messages stay precise

### Slice 5: Hook And MCP Adapters

Make hooks and MCP call the same core services instead of duplicating policy.

Success:

- hook behavior remains covered by deterministic tests
- MCP remains read-only
- adapter failures explain missing runtime capability separately from bad data

## Inner-Loop Gates

Before each implementation slice is considered complete:

```bash
python3 plugins/trust-evidence-protocol/scripts/context_cli.py --context .codex_context review-context
python3 plugins/trust-evidence-protocol/scripts/context_cli.py --context .codex_context reindex-context
python3 plugins/trust-evidence-protocol/scripts/validate_codex_context.py .codex_context
python3 plugins/trust-evidence-protocol/scripts/runtime_gate.py --context .codex_context hydrate-context
uv run pytest -q \
  tests/trust_evidence_protocol/test_core_services.py \
  tests/trust_evidence_protocol/test_plugin_cli.py \
  tests/trust_evidence_protocol/test_hooks_runtime.py \
  tests/trust_evidence_protocol/test_mcp_server.py
```

Coverage should run after meaningful extraction:

```bash
COVERAGE_FILE=/tmp/tep.coverage uv run --extra test coverage run -m pytest -q \
  tests/trust_evidence_protocol/test_core_services.py \
  tests/trust_evidence_protocol/test_plugin_cli.py \
  tests/trust_evidence_protocol/test_hooks_runtime.py \
  tests/trust_evidence_protocol/test_mcp_server.py
COVERAGE_FILE=/tmp/tep.coverage uv run --extra test coverage combine
COVERAGE_FILE=/tmp/tep.coverage uv run --extra test coverage report -m
```

Docker live-agent tests are optional during development and user-triggered before
publication.

## Documentation Gates

When a rebuild slice changes behavior, update the relevant docs in the same
slice:

- `docs/dev/TEP_DEVELOPER_REFERENCE.md` for normative behavior
- `docs/reference/TEP_DATA_MODEL.md` for record semantics and schema changes
- `docs/dev/REPOSITORY_ORGANIZATION.md` for module/test layout
- plugin `README.md` for operator-facing commands
- skill docs only when agent-facing reasoning requirements change

Do not hide behavior changes in implementation-only commits.

## Working Context Rules

During the rebuild:

- record durable decisions as `CLM-*`, `PRP-*`, `PLN-*`, or `DEBT-*`
- use `WCTX-*` when switching between architecture, tests, migration, MCP, and
  live-agent work
- record major implementation actions as `ACT-*`
- record deferrals instead of leaving TODOs only in prose
- prefer narrow slices with explicit success criteria
- avoid implementing new feature semantics while extracting core modules unless
  the slice explicitly targets that feature

## Exit Criteria For Stable Core Phase

The stable core phase is complete when:

- core services are importable without CLI subprocesses
- CLI is mostly adapter and command registry
- validation is unit-testable directly
- migration framework exists for breaking schema/settings changes
- deterministic tests pass
- coverage remains usable and improves over the current baseline
- current repository `.codex_context` migrates or validates cleanly
- docs describe the actual core contract
- a later feature slice can implement explanatory chains or curiosity commands
  without adding more monolithic CLI logic

## Current Recommendation

Use the next internal version line as a larger beta rebuild release, likely
`0.2.0`, and do not publish until several core slices are complete.

The first implementation move should be Slice 1: characterize current command
behavior and establish direct tests around the first pure modules to extract.
