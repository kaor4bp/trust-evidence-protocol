# TEP Core Baseline

This document characterizes the current TEP runtime surface before the stable
core rebuild starts moving implementation code.

The goal is not to freeze weak design. The goal is to know what exists, what is
canonical, what is generated, and which behavior must be migrated deliberately if
the rebuild breaks it.

## Scope

This is Slice 1 of the stable-core rebuild.

It covers:

- CLI command surface
- runtime gate surface
- canonical record templates
- generated output layout
- current source-code concentration
- deterministic validation and test gates

It does not implement the new core modules.

## Rebuild Stance

Treat this as plugin rebuild, not cosmetic refactoring.

Breaking changes are allowed during beta, but only when the change improves the
core contract and has an explicit migration or compatibility story.

Do not preserve current structure just because it exists. Preserve semantics,
data safety, and operator expectations.

## Current Entrypoints

### Plugin Manifest

Source: `plugins/trust-evidence-protocol/.codex-plugin/plugin.json`

Current public identity:

- plugin name: `trust-evidence-protocol`
- version: `0.1.29`
- Codex UI display name: `TEP Runtime`
- skills path: `./skills/`
- MCP declaration: `./.mcp.json`
- default prompt reminds agents to use TEP before changes or decisions

### Main CLI

Source: `plugins/trust-evidence-protocol/scripts/context_cli.py`

Current shape:

- 76 top-level commands
- 13 nested subcommands
- mutation policy is hard-coded through `MUTATING_COMMANDS` and nested mutation
  sets
- parsing and dispatch live in the same file as most command behavior

The CLI currently owns too much behavior. During the rebuild it should become a
thin adapter over importable core services.

### Runtime Gate CLI

Source: `plugins/trust-evidence-protocol/scripts/runtime_gate.py`

Commands:

- `hydrate-context`
- `show-hydration`
- `preflight-task`
- `invalidate-hydration`

This is the hook-facing policy surface. It should keep using the same core
validation/settings/policy services as the main CLI after extraction.

### Strict Validator

Source: `plugins/trust-evidence-protocol/scripts/validate_codex_context.py`

Current surface:

```text
validate_codex_context.py [target]
```

This is a strict layout and record validator. The rebuild must preserve a simple
standalone validation command even if internals move.

### MCP Server

Source: `plugins/trust-evidence-protocol/mcp/tep_server.py`

Current contract:

- stdio MCP server
- read-only lookup tools
- no mutating record writes
- uses `.mcp.json` command `python3 mcp/tep_server.py`

MCP visibility/debugging is important but not part of the first core extraction
slice.

### Hook Adapters

Source: `plugins/trust-evidence-protocol/hooks/codex/`

Current adapters:

- `session_start_hydrate.py`
- `user_prompt_hydration_notice.py`
- `pre_tool_use_guard.py`
- `post_tool_use_review.py`

Current hook settings live in `.codex_context/settings.json` under `hooks.*`.
The adapters are intentionally conservative and do not claim complete
enforcement across every Codex tool.

## CLI Command Groups

### Core Review And Context Lookup

- `help`
- `review-context`
- `reindex-context`
- `brief-context`
- `search-records`
- `record-detail`
- `record-neighborhood`
- `guidelines-for`
- `cleanup-candidates`

### Generated Topic And Logic Navigation

- `topic-index build`
- `topic-search`
- `topic-info`
- `topic-conflict-candidates`
- `logic-index build`
- `logic-search`
- `logic-graph`
- `logic-check`
- `logic-conflict-candidates`

Generated topic and logic outputs are navigation only. They must never become
proof during the rebuild.

### Code Index Navigation

- `init-code-index`
- `index-code`
- `code-refresh`
- `code-info`
- `code-search`
- `code-smell-report`
- `code-entry create`
- `annotate-code`
- `link-code`
- `assign-code-index`

`CIX-*` remains navigation/scope/impact data, not claim support.

### Reasoning And Conflict Workflows

- `build-reasoning-case`
- `augment-chain`
- `validate-planning-chain`
- `validate-evidence-chain`
- `scan-conflicts`
- `impact-graph`
- `linked-records`
- `rollback-report`

`validate-planning-chain` is currently a deprecated alias for
`validate-evidence-chain`.

### Project, Task, And Working Context

- `record-project`
- `show-project`
- `set-current-project`
- `assign-project`
- `assign-task`
- `start-task`
- `show-task`
- `complete-task`
- `pause-task`
- `resume-task`
- `switch-task`
- `stop-task`
- `task-drift-check`
- `review-precedents`
- `working-context create`
- `working-context show`
- `working-context fork`
- `working-context close`

These commands define operational focus, not truth.

### Control And Guidance

- `record-restriction`
- `show-restrictions`
- `record-guideline`
- `show-guidelines`
- `record-proposal`
- `configure-runtime`
- `change-strictness`
- `request-strictness-change`
- `record-permission`

Permissions, restrictions, guidelines, proposals, and runtime settings guide
action. They do not prove factual claims.

### Canonical Record Writes

- `record-action`
- `record-evidence`
- `record-source`
- `record-claim`
- `record-plan`
- `record-debt`
- `record-feedback`
- `record-model`
- `record-flow`
- `record-open-question`
- `record-artifact`

These are the main write surface for durable context.

### Claim Lifecycle

- `show-claim-lifecycle`
- `resolve-claim`
- `archive-claim`
- `restore-claim`
- `promote-model-to-domain`
- `promote-flow-to-domain`
- `mark-stale-from-claim`

The rebuild must preserve the separation between truth status and retrieval
lifecycle.

### Hypothesis Index

- `hypothesis add`
- `hypothesis list`
- `hypothesis close`
- `hypothesis reopen`
- `hypothesis remove`
- `hypothesis sync`

`hypotheses.jsonl` is an index over tentative `CLM-*` records, not a second truth
store.

## Mutating Command Baseline

Top-level mutating commands currently include:

```text
annotate-code
archive-claim
assign-code-index
assign-project
assign-task
change-strictness
code-entry
code-refresh
complete-task
configure-runtime
index-code
init-code-index
link-code
mark-stale-from-claim
pause-task
promote-flow-to-domain
promote-model-to-domain
record-action
record-artifact
record-claim
record-debt
record-evidence
record-feedback
record-flow
record-guideline
record-model
record-open-question
record-permission
record-plan
record-project
record-proposal
record-restriction
record-source
reindex-context
request-strictness-change
resolve-claim
restore-claim
resume-task
review-context
scan-conflicts
set-current-project
start-task
stop-task
switch-task
```

Nested mutating commands:

- `hypothesis add|close|reopen|remove|sync`
- `topic-index build`
- `logic-index build`
- `working-context create|fork|close`

The rebuild should move mutation classification out of the monolithic CLI and
into a shared command registry or policy service so hooks, CLI, and docs cannot
drift independently.

## Canonical Record Templates

Current templates live in `plugins/trust-evidence-protocol/templates/codex_context/`.

| Template | Primary role | Important fields |
| --- | --- | --- |
| `source.json` | provenance carrier | `source_kind`, `critique_status`, `origin`, `quote`, `artifact_refs`, `confidence` |
| `claim.json` | only truth record | `plane`, `status`, `statement`, `source_refs`, `support_refs`, `contradiction_refs`, `lifecycle`, `comparison`, `logic` |
| `permission.json` | positive authorization | `applies_to`, `grants`, `granted_by`, `granted_at` |
| `restriction.json` | negative/control constraint | `applies_to`, `rules`, `severity`, `status`, `related_claim_refs` |
| `guideline.json` | operational rule | `domain`, `applies_to`, `priority`, `rule`, `source_refs`, `related_claim_refs` |
| `proposal.json` | constructive critique/options | `position`, `proposals`, `risks`, `stop_conditions`, `claim_refs`, `model_refs`, `flow_refs` |
| `action.json` | intended/executed operation | `kind`, `status`, `safety_class`, `justified_by`, `planned_at` |
| `project.json` | project boundary | `project_key`, `root_refs`, `related_project_refs`, `status` |
| `task.json` | execution focus | `task_type`, `status`, `plan_refs`, `debt_refs`, `related_claim_refs` |
| `working_context.json` | operational handoff/focus | `context_kind`, `pinned_refs`, `focus_paths`, `assumptions`, `concerns` |
| `plan.json` | intended future work | `priority`, `status`, `justified_by`, `steps`, `success_criteria` |
| `debt.json` | persistent liability | `priority`, `status`, `evidence_refs`, `plan_refs` |
| `model.json` | evidence-backed domain picture | `domain`, `aspect`, `claim_refs`, `hypothesis_refs`, `status`, `knowledge_class` |
| `flow.json` | end-to-end behavior picture | `domain`, `model_refs`, `preconditions`, `steps`, `oracle`, `status` |
| `open_question.json` | unresolved uncertainty | `domain`, `aspect`, `question`, `related_claim_refs`, `resolved_by_claim_refs` |

Migration tests must cover any schema tightening or field rename for these
templates.

## Generated Output Baseline

Current generated/navigation outputs include:

```text
.codex_context/index.md
.codex_context/backlog.md
.codex_context/review/attention.md
.codex_context/review/broken.md
.codex_context/review/conflicts.md
.codex_context/review/flows.md
.codex_context/review/hypotheses.md
.codex_context/review/models.md
.codex_context/review/resolved.md
.codex_context/review/stale.md
.codex_context/topic_index/by_record.json
.codex_context/topic_index/by_topic.json
.codex_context/topic_index/conflict_candidates.md
.codex_context/topic_index/records.json
.codex_context/topic_index/summary.md
.codex_context/topic_index/topics.json
.codex_context/logic_index/atoms.json
.codex_context/logic_index/by_predicate.json
.codex_context/logic_index/by_symbol.json
.codex_context/logic_index/conflict_candidates.md
.codex_context/logic_index/rules.json
.codex_context/logic_index/summary.md
.codex_context/logic_index/symbols.json
.codex_context/logic_index/variable_graph.json
.codex_context/logic_index/vocabulary_smells.md
.codex_context/code_index/by_path.json
.codex_context/code_index/by_ref.json
.codex_context/code_index/summary.md
.codex_context/runtime/hydration.json
```

These outputs are rebuildable navigation/policy artifacts. They must not become
canonical proof in the new core.

## Current Source Concentration

Current measured implementation shape:

| File | Lines | Functions | Classes |
| --- | ---: | ---: | ---: |
| `scripts/context_cli.py` | 8905 | 242 | 0 |
| `scripts/context_lib.py` | 3327 | 92 | 1 |
| `scripts/runtime_gate.py` | 385 | 15 | 0 |
| `mcp/tep_server.py` | 776 | 32 | 0 |

This validates the rebuild direction: the CLI and shared library are too large
to remain the long-term core boundary.

## Baseline Gates

Run these before and after core movement:

```bash
python3 plugins/trust-evidence-protocol/scripts/context_cli.py --context .codex_context review-context
python3 plugins/trust-evidence-protocol/scripts/context_cli.py --context .codex_context reindex-context
python3 plugins/trust-evidence-protocol/scripts/validate_codex_context.py .codex_context
python3 plugins/trust-evidence-protocol/scripts/runtime_gate.py --context .codex_context hydrate-context
uv run pytest -q \
  tests/trust_evidence_protocol/test_plugin_cli.py \
  tests/trust_evidence_protocol/test_hooks_runtime.py \
  tests/trust_evidence_protocol/test_mcp_server.py
```

The full Docker live-agent suite is intentionally not part of this inner-loop
gate. It remains an explicit user-triggered conformance pass before publication.

## Known Baseline Smells

- CLI parser and dispatch are not a registry.
- Mutating command policy is duplicated as string constants instead of command
  metadata.
- Many tests still exercise behavior through subprocess CLI calls instead of
  direct core services.
- Validation behavior is concentrated in `context_lib.py`.
- MCP and hooks are adapters over the current script layout, not over a stable
  core API.

These smells should be reduced by the rebuild, not merely moved into new files.

## Next Slice

Slice 2 should extract the lowest-risk pure services first:

- path resolution
- ID allocation
- record path/load/save/list
- settings load/save
- reference/link helpers
- small validation helpers

Success for Slice 2:

- extracted services have direct unit tests
- current CLI behavior remains available or has a deliberate migration note
- baseline gates pass
- no new feature semantics are added during extraction
