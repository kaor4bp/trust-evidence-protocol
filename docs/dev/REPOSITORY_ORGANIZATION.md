# Repository Organization

This repository is now managed as a plugin-first Codex development workspace.

## Current Boundaries

- `plugins/trust-evidence-protocol/` is the source of truth for the TEP plugin.
- `plugins/trust-evidence-protocol/skills/trust-evidence-protocol/` is the only TEP skill package.
- `trust-evidence-protocol/` at repository root is intentionally removed to avoid duplicate skill sources.
- Live TEP memory is moving toward one global `~/.tep_context` selected through
  `TEP_CONTEXT_ROOT` or resolver discovery; repo-local `.codex_context/` remains
  a legacy development context during migration.
- Live `.tep_context/` and `.codex_context/` directories are ignored by git.
  Commit sanitized fixtures, templates, docs, or exports instead of working
  memory.
- `tests/trust_evidence_protocol/test_plugin_cli.py`, `test_hooks_runtime.py`, and `test_mcp_server.py` are deterministic plugin-runtime tests.
- The remaining `tests/trust_evidence_protocol/test_*.py` files that use `codex_harness.py` are live-agent conformance tests.

## Test Layers

Use three layers instead of treating all tests as equivalent:

1. Deterministic runtime tests.
   These validate Python CLI/runtime/hooks/MCP behavior and should run before every commit.

2. Coverage run.
   These use `coverage[toml]` with subprocess patching and `coverage combine`.
   They measure plugin Python surface, not model behavior.

3. Live-agent Docker tests.
   These run real `codex exec` inside Docker with isolated `CODEX_HOME` and `OPENAI_API_KEY` from `.env`.
   They are intentionally slower and can be nondeterministic, so failures need triage rather than blind refactor.

## Target Code Layout

The current plugin works, but `context_cli.py` and `context_lib.py` are too large.
Refactor incrementally, preserving CLI behavior.

Recommended target structure:

```text
plugins/trust-evidence-protocol/
  scripts/
    context_cli.py          # thin argparse + dispatch only
    runtime_gate.py         # hook-facing runtime gates
  tep_runtime/
    actions.py              # ACT payload helpers
    claims.py               # CLM lifecycle and payload helpers
    records.py              # record IO, ids, locks
    schemas.py              # canonical record constants and record/ref validation
    validation.py           # shared schema helper primitives
    working_contexts.py     # WCTX payload, fork, close, assumptions, and display
    state_validation.py      # state-level validation orchestration
    settings.py             # runtime settings and settings-state validation
    policy.py               # runtime policy helpers shared by CLI/hooks
    reasoning.py            # evidence-chain validation, proof-role checks, reports
    reasoning_case.py       # build-reasoning-case selection, diagnostics, rendering
    reports.py              # generated report rendering primitives
    generated_views.py      # generated review, attention, backlog, and index views
    knowledge.py            # shared MODEL/FLOW lifecycle helpers
    rollback.py             # impact/rollback report payload and rendering helpers
    context_brief.py        # brief-context/detail selection and text rendering
    cleanup.py              # read-only cleanup candidate diagnostics
    flows.py                # FLOW payload and promotion helpers
    guidelines.py           # GLD scope resolution and payload helpers
    models.py               # MODEL payload and promotion helpers
    notes.py                # shared note formatting helpers
    open_questions.py       # OPEN payload helpers
    planning.py             # PLN/DEBT payload helpers
    permissions.py          # PRM scope resolution and payload helpers
    projects.py             # PRJ payload and assignment mutation helpers
    proposals.py            # proposal parsing and display helpers
    restrictions.py         # RST scope resolution and payload helpers
    cli_common.py           # shared CLI persistence, display, and mutation-policy helpers
    display.py              # deterministic public record summary line renderers
    search.py               # record search text, ranking, and summaries
    sources.py              # SRC payload helpers
    inputs.py               # INP prompt/input provenance payload helpers
    tasks.py                # TASK payload, lifecycle, drift, and precedent helpers
    retrieval.py            # scope-aware record selection and fallback lookup
    hypotheses.py           # hypothesis index IO, mutation, validation, and lookup
    code_index.py           # CIX metadata, AST extraction, code annotations/rendering
    topic_index.py          # lexical/NMF prefilter
    logic.py                # CLM.logic parsing, validation, and symbol checks
    logic_index.py          # predicate projection and structural checks
    logic_check.py          # logic-check solver settings and report rendering
    logic_z3.py             # optional Z3 backend
    code_ast/               # per-language code metadata analyzers used by CIX
    cli_commands/           # small command handlers grouped by domain
  mcp/
    tep_server.py           # read-only MCP adapter over runtime APIs
  hooks/
    codex/                  # Codex hook adapters only
```

Current rebuild status:

- `tep_runtime/` exists and owns the first extracted pure services.
- Action payload and timestamp helpers now live in `tep_runtime/actions.py`
  behind the compatibility facade.
- `tep_runtime/context_root.py` owns TEP context-root discovery for explicit
  `--context`, `TEP_CONTEXT_ROOT`, global `~/.tep_context`, and legacy
  `.codex_context` fallback.
- Runtime settings normalization, persistence, strictness approval request
  IO/checks, and settings-state validation now live in
  `tep_runtime/settings.py` behind the compatibility facade.
- Runtime policy helpers shared by CLI and hook gates now live in
  `tep_runtime/policy.py` behind the compatibility facade.
- Canonical record type/status constants, artifact reference checks,
  per-record schema validation, and typed reference validation now live in
  `tep_runtime/schemas.py` behind the compatibility facade.
- State-level validation orchestration now lives in
  `tep_runtime/state_validation.py` behind the compatibility facade.
- Hydration state and context fingerprinting now live in `tep_runtime/hydration.py`
  behind the `context_lib.py` compatibility facade.
- Generated report rendering primitives and validation-report writing now live
  in `tep_runtime/reports.py` behind the compatibility facade.
- Generated stale/model/flow/hypothesis, attention, resolved, backlog,
  dependency-impact, and index views now live in `tep_runtime/generated_views.py`
  behind the compatibility facade.
- Shared CLI display, generated-output refresh, candidate/mutated-record
  persistence, payload normalization, and command write-lock policy helpers now
  live in `tep_runtime/cli_common.py`.
- Public record summary line renderers for projects, restrictions, guidelines,
  claims, and sources now live in `tep_runtime/display.py` behind the
  compatibility facade.
- Shared schema helper primitives for list/object normalization, optional
  confidence, and optional red-flag validation now live in
  `tep_runtime/validation.py` behind the compatibility facade.
- Working-context assumption parsing, payload construction, fork mutation,
  close mutation, summary/detail rendering, and show payload helpers now live
  in `tep_runtime/working_contexts.py` behind the compatibility facade.
- Code-index constants, smell taxonomies, CIX entry construction, generated
  code-index views, entry
  freshness/projection, search/smell result rendering, smell report payloads,
  entry persistence, CIX entry validation, and state-level code-index reference
  validation now live in `tep_runtime/code_index.py` behind the compatibility
  facade.
- Per-language AST/text metadata extraction now lives under
  `tep_runtime/code_ast/` and is re-exported by `tep_runtime/code_index.py` for
  compatibility. The current package covers Python AST extraction, JS/TS-like
  regex extraction, and Markdown heading/link/code-block outline extraction.
- CLM.logic constants, CLI logic spec parsing, atom/rule/schema validation,
  symbol extraction, and state-level symbol introduction validation now live in
  `tep_runtime/logic.py` behind the compatibility facade.
- Generated CLM.logic index payloads/reports, predicate conflict candidates,
  vocabulary graph construction, rule-variable analysis, and vocabulary smell
  pressure reports now live in `tep_runtime/logic_index.py` behind the
  compatibility facade.
- Logic-check solver selection, solver settings lookup, structural result
  payloads, structural text rendering, and Z3 text rendering now live in
  `tep_runtime/logic_check.py` behind the compatibility facade.
- Claim comparison CLI payload construction, constants/schema checks,
  comparison signatures, generated conflict-line collection, and conflict
  report writing now live in `tep_runtime/conflicts.py` behind the
  compatibility facade.
- Claim lifecycle, lifecycle mutation payloads, attention, retrieval-tier, and
  fallback action-blocking helpers plus claim payload helpers now live in
  `tep_runtime/claims.py` behind the compatibility facade.
- Read-only cleanup candidate diagnostics for stale lifecycle attention,
  fallback dependencies, and active hypothesis pointers now live in
  `tep_runtime/cleanup.py` behind the compatibility facade.
- Flow step, precondition, oracle, full payload, and domain promotion helpers
  now live in `tep_runtime/flows.py` behind the compatibility facade.
- Guideline scope resolution and payload helpers now live in
  `tep_runtime/guidelines.py` behind the compatibility facade.
- Model payload and domain promotion helpers now live in
  `tep_runtime/models.py` behind the compatibility facade.
- Shared note formatting helpers now live in `tep_runtime/notes.py`.
- Open-question payload helpers now live in `tep_runtime/open_questions.py`
  behind the compatibility facade.
- Plan and debt payload helpers now live in `tep_runtime/planning.py` behind
  the compatibility facade.
- Permission scope resolution and payload helpers now live in
  `tep_runtime/permissions.py` behind the compatibility facade.
- Project payload and assignment mutation helpers now live in
  `tep_runtime/projects.py` behind the compatibility facade.
- Proposal option parsing, proposal payload construction, and proposal summary
  formatting now live in `tep_runtime/proposals.py` behind the compatibility
  facade.
- Restriction scope resolution and payload helpers now live in
  `tep_runtime/restrictions.py` behind the compatibility facade.
- Record dependency-reference, link-edge, linked-record graph payload,
  record-detail payload, and record-detail text rendering helpers now live in
  `tep_runtime/links.py` behind the compatibility facade.
- Project/task scope resolution and permission/restriction/guideline
  applicability helpers now live in `tep_runtime/scopes.py` behind the
  compatibility facade.
- Deterministic record search text, scoring, scoped ranked record search,
  concise formatting, and public summary helpers now live in
  `tep_runtime/search.py` behind the compatibility facade.
- Source payload and default independence-group helpers now live in
  `tep_runtime/sources.py` behind the compatibility facade.
- Input provenance payload helpers now live in `tep_runtime/inputs.py` behind
  the compatibility facade.
- Task payload construction, pure lifecycle mutation, drift-check payloads, and
  precedent-review selection/rendering helpers now live in
  `tep_runtime/tasks.py` behind the compatibility facade.
- Scope-aware record selection, explicit-reference retrieval, fallback claim
  lookup, and active permission/guideline selection now live in
  `tep_runtime/retrieval.py` behind the compatibility facade.
- Lexical task terms, generated topic-index payloads/reports, topic-search
  matching, topic-conflict prefilter candidates, and working-context topic
  inference now live in `tep_runtime/topic_index.py` behind the compatibility
  facade.
- Hypothesis index IO, entry mutation helpers, semantic validation, model/flow
  claim reference collection, active hypothesis selection, and evidence-chain
  hypothesis lookup now live in `tep_runtime/hypotheses.py` behind the
  compatibility facade.
- Shared MODEL/FLOW stale-target selection and stale payload helpers now live
  in `tep_runtime/knowledge.py` behind the compatibility facade.
- Impact graph and rollback report payload construction and text rendering
  helpers now live in `tep_runtime/rollback.py` behind the compatibility
  facade.
- Evidence-chain quote normalization and matching helpers now live in
  `tep_runtime/evidence.py` behind the compatibility facade.
- Evidence-chain node/edge validation, role constraints, lifecycle proof
  blocking, support-edge checks, and validation-report rendering now live in
  `tep_runtime/reasoning.py` behind the compatibility facade.
- Reasoning-case record selection, chain diagnostics, and text rendering now
  live in `tep_runtime/reasoning_case.py` behind the compatibility facade.
- Task-oriented context brief record selection, context-brief text rendering,
  and shared project/restriction/guideline/task detail renderers now live in
  `tep_runtime/context_brief.py` behind the compatibility facade.
- `scripts/context_lib.py` is now a compatibility facade that re-exports
  runtime helpers for existing scripts.
- `scripts/context_cli.py` is still the monolithic parser/dispatcher and has not
  been converted to a command registry yet.

## Rebuild Rules

- Do not rewrite the plugin in one pass.
- Extract pure modules first, then move CLI handlers.
- Preserve command names, JSON schemas, hook payloads, and MCP tool names unless explicitly planned.
- Add direct unit tests for extracted modules before moving behavior that is currently only covered through subprocess CLI tests.
- Keep live-agent tests as conformance checks, not as the primary regression signal.

## Normative References

Use these documents as the rebuild contract:

- `docs/dev/TEP_DEVELOPER_REFERENCE.md` defines plugin responsibilities, system layers, functional contracts, rebuild invariants, and future development areas.
- `docs/reference/TEP_DATA_MODEL.md` defines canonical record semantics, lifecycle, links, generated indexes, cleanup, and migration rules.
- `docs/research/TEP_RESEARCH_MAP.md` maps external algorithms/tools to safe TEP adoption paths.
- `docs/research/TEP_ACADEMIC_RESEARCH_PLAN.md` defines deeper research tracks for heuristic reasoning, corroboration, formal slices, argumentation, and belief revision.
- `docs/research/TEP_REASONING_RESEARCH.md` contains the detailed academic synthesis for explanatory chains, candidate narratives, and fact reconciliation.
- `docs/research/TEP_PLANNING_CURIOSITY_RESEARCH.md` contains the detailed synthesis for bounded planning, legitimate deferral, curiosity, and hypothesis verification pressure.
- `docs/dev/TEP_CORE_REWRITE_CONTEXT.md` is the working contract for the first stable-core rebuild phase, including breaking-change, migration, module, and test gates.
- `docs/dev/TEP_CORE_BASELINE.md` characterizes the current CLI, runtime gates, record templates, generated outputs, and source concentration before the core rebuild moves implementation code.

When implementation and documentation disagree, treat it as a design drift issue.
Do not silently change record semantics, command contracts, hook policy, or MCP behavior without updating the normative docs and tests.

## Commit Discipline

Before each commit:

```bash
uv run pytest -q \
  tests/trust_evidence_protocol/test_core_services.py \
  tests/trust_evidence_protocol/test_plugin_cli.py \
  tests/trust_evidence_protocol/test_hooks_runtime.py \
  tests/trust_evidence_protocol/test_mcp_server.py
```

For coverage:

```bash
COVERAGE_FILE=/tmp/tep.coverage uv run --extra test coverage run -m pytest -q \
  tests/trust_evidence_protocol/test_core_services.py \
  tests/trust_evidence_protocol/test_plugin_cli.py \
  tests/trust_evidence_protocol/test_hooks_runtime.py \
  tests/trust_evidence_protocol/test_mcp_server.py
COVERAGE_FILE=/tmp/tep.coverage uv run --extra test coverage combine
COVERAGE_FILE=/tmp/tep.coverage uv run --extra test coverage report -m
```
