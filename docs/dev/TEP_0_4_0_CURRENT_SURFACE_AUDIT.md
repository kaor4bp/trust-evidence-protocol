# TEP 0.4.0 Current Surface Audit

Date: 2026-04-23

Scope: static audit of the current Trust Evidence Protocol plugin surface before the 0.4.0 architectural rebuild.

This document intentionally does not prescribe runtime patches. It captures what exists now, where it conflicts with the 0.4.0 decisions, and the recommended slice-1 implementation boundary.

## Fixed 0.4.0 Decisions

- Target version is `0.4.0`.
- Normal agents must use MCP-only front doors.
- Normal agents must not read raw `~/.tep_context` records and must not use the legacy CLI command zoo.
- Plugin name and skill names stay unchanged.
- CLI remains for development, debugging, migration, and CI. `context_cli.py` may remain as a test/dev wrapper.
- `.codex_context` is no longer a runtime concept.
- `~/.tep_context` is the only primary context root.
- Legacy migration uses `INP-*` with `input_kind=migration_batch`; migration must not fake `RUN-*` provenance.
- Old `GRANT-*` records are preserved for audit but revoked for authorization.
- Preserve canonical record ids where possible.
- New `GRANT.action_kind` enum is exactly `bash|file-write|mcp-write|git|final`.
- Hooks, MCP, and CLI must call shared core services directly.

## Executive Summary

The current plugin is useful but not shaped like the target 0.4.0 system.

The main contradiction is that the product direction says "MCP front doors and graph API", while the current implementation still exposes a large CLI command zoo, has MCP shelling out to that CLI, and lets hooks duplicate command classification and policy checks before shelling out to CLI/runtime scripts.

The second blocker is context-root ambiguity. `.codex_context` is still present in docs, tests, templates, helper names, default help text, and runtime fallback logic. For 0.4.0, this must be reduced to legacy migration fixtures only.

The third blocker is provenance and authorization. `REASON-*` already moved in the right direction, but current GRANT authorization still accepts legacy ledger shapes (`AUTH`, `USE`, `access_granted`, `auth_granted`, `access_used`, `auth_reserved`) and current action kinds are free-form mutation labels, not the 0.4.0 enum.

Slice 1 should not add features. It should create the 0.4.0 contracts, storage layout, migration scaffold, and shared service seams so MCP/hooks/CLI can stop knowing their own policy.

## Current Surface Inventory

### Current CLI Commands

Source: `plugins/trust-evidence-protocol/scripts/context_cli.py`.

| Command or group | Current role | 0.4.0 classification | Recommendation |
|---|---|---:|---|
| `help` | Lists current CLI command categories. | Dev-only | Keep as CLI wrapper help. Do not expose as agent path. |
| `next-step` | Route hint for agent intent. | MCP front-door | Move domain logic into service. MCP calls service directly. CLI wraps service for tests/debug. |
| `lookup` | Main retrieval route; returns facts/code/theory/policy candidates and route data. | MCP front-door | Promote to primary agent path. It must return route branches and next allowed tool calls, not just search output. |
| `brief-context` | Broad context summary. | Drill-down/read-only | Keep behind `next_step`/`lookup`; not a normal first action because it can become a token dump. |
| `search-records`, `claim-graph` | Direct fact search. | Drill-down/read-only, not front-door | Keep for drill-down after `lookup`; remove from normal route menu. |
| `record-detail`, `record-neighborhood`, `linked-records` | Inspect specific records and graph neighborhoods. | Drill-down/read-only | Keep as controlled MCP drill-down. Raw JSON should remain blocked. |
| `guidelines-for`, `show-guidelines`, `show-restrictions` | Policy/guideline retrieval. | Drill-down/read-only | Keep through MCP. `lookup(kind=policy)` should prefer these internally. |
| `curator-pool build/show` | Builds explicit curator work pools. | MCP/front-door for curator role, dev-only for normal agents | Keep, but expose through a curator-specific MCP entry point, not normal agent route. |
| `cleanup-candidates`, `cleanup-archives`, `cleanup-archive`, `cleanup-restore` | Cleanup inspection and archive/restore operations. | Dev-only/migration-only | Keep CLI only until cleanup is a formal 0.4 mechanic. Mutating cleanup must never be normal-agent default. |
| `topic-index build`, `topic-search`, `topic-info`, `topic-conflict-candidates` | Topic prefilter/navigation. | Dev-only build; drill-down read-only search | Keep as backend/navigation services. Normal agents should receive topic hints through `lookup`/map outputs, not call topic tools first. |
| `tap-record`, `telemetry-report` | Activity and usage telemetry. | Dev-only or diagnostic drill-down | Keep. Normal route can use aggregated telemetry internally. |
| `attention-index build`, `attention-map`, `attention-diagram`, `attention-diagram-compare` | Attention/visual-thinking navigation. | Dev-only build; drill-down read-only map | Keep as services behind `lookup` and `curiosity_map`; reduce direct agent menu. |
| `curiosity-map`, `map-brief`, `curiosity-probes`, `probe-inspect`, `probe-chain-draft`, `probe-route`, `probe-pack`, `probe-pack-compare` | Curiosity and map navigation. | Drill-down/read-only | Keep, but consolidate normal entry into one `map_brief`/`curiosity_map` route. Probe tools are secondary drill-down. |
| `logic-index build`, `logic-search`, `logic-graph`, `logic-check`, `logic-conflict-candidates` | Predicate logic navigation/checking. | Dev-only build; drill-down/read-only checks | Keep. 0.4 should treat logic output as mechanical hints, not proof by itself. |
| `init-code-index`, `index-code`, `code-refresh`, `code-entry create/archive-unscoped/attach-unscoped`, `annotate-code`, `link-code`, `assign-code-index` | CIX creation, update, annotation, and linking. | Mutating/dev-only or backend maintenance | Keep as CLI/service operations. Normal agents should use MCP `code_search`/`code_info` and a future controlled annotation route. |
| `code-info`, `code-search`, `code-feedback`, `code-smell-report` | Code navigation, backend feedback, smell report. | Drill-down/read-only, with feedback mutating only through review/apply | Keep through MCP, but route through backend service. `code-feedback --apply` is mutating and should be dev/curator controlled. |
| `build-reasoning-case`, `validate-planning-chain`, `validate-evidence-chain`, `validate-decision`, `augment-chain` | Chain construction/validation. | MCP normal-loop | Move to core chain service. Normal agents should not hand-author low-level chain files unless explicitly in dev mode. |
| `reason-step`, `reason-review`, `reason-current`, `reason-check-grant`, `reason-match-grant` | Append/check REASON/GRANT ledger entries. | MCP normal-loop and hook-internal | Move to reason service. Hooks must call service, not shell out. `reason-check-grant`/`reason-match-grant` are hook internals. |
| `scan-conflicts`, `review-context`, `reindex-context`, `type-graph` | Context integrity and type graph review. | Dev-only/CI | Keep as CLI wrappers around validators/indexers. Normal agents should see summarized blockers through `next_step`. |
| `record-workspace`, `show-workspace`, `set-current-workspace`, `assign-workspace`, `workspace-admission check`, `init-anchor`, `show-anchor`, `validate-anchor` | Workspace and local anchor management. | Workspace front-door only for admission; most dev/migration-only | Keep `workspace_admission` as MCP read-only. Mutating workspace/anchor commands should be controlled setup/dev tools. |
| `record-project`, `show-project`, `set-current-project`, `assign-project`, `assign-task` | Project/task assignment and migration. | Dev/migration-only | Keep CLI. Normal agents should not manually assign records; services should infer scope or ask admission questions. |
| `record-restriction`, `record-guideline`, `record-proposal`, `record-permission` | User/policy/proposal records. | Mutating MCP path needed, low-level CLI dev-only | Keep as service-backed mutations. Normal agents should use higher-level MCP write routes, not raw `record-*`. |
| `configure-runtime`, `backend-status`, `backend-check`, `validate-facts`, `export-rdf` | Settings/backend diagnostics and exports. | Dev-only diagnostics; backend status drill-down | Keep backend status/check through MCP. Settings mutation stays CLI/dev until a clear user-facing settings API exists. |
| `start-task`, `show-task`, `validate-task-decomposition`, `confirm-atomic-task`, `decompose-task`, `task-outcome-check`, `complete-task`, `pause-task`, `resume-task`, `switch-task`, `stop-task`, `task-drift-check`, `review-precedents` | Task lifecycle. | MCP normal-loop, with mutating task commands controlled | Move task lifecycle to service/MCP. `next_step` must force atomic/decomposed readiness. |
| `working-context create/show/check-drift/fork/close` | Agent working context lifecycle. | MCP front-door/drill-down | Keep as service. WCTX should be created/selected by `lookup`/`next_step`, not manually by normal agents. |
| `impact-graph`, `promote-model-to-domain`, `promote-flow-to-domain`, `mark-stale-from-claim`, `rollback-report` | Model/flow promotion and impact review. | Drill-down or curator/dev-only | Keep behind curator/dev route. Promotion must validate supported/user-confirmed theory. |
| `change-strictness`, `request-strictness-change` | Strictness change. | Dev/user-controlled only | Replace direct normal-agent use with explicit settings/user approval workflow. |
| `record-action`, `record-input`, `record-run`, `classify-input`, `input-triage report/link-operational` | Input/action/run capture and triage. | Service/hook-internal; dev-only CLI | Hooks/services should create `INP-*` and `RUN-*`. Normal agents should not manually create runtime provenance. |
| `record-evidence`, `record-support`, `record-source`, `record-claim`, `record-link` | Evidence/source/claim creation and linking. | MCP normal-loop for high-level capture; low-level raw commands dev/migration-only | Keep `record_evidence` as agent-facing MCP. Demote `record-source`, `record-claim`, `record-link` to dev/migration because 0.4 requires mechanical provenance. |
| `show-claim-lifecycle`, `resolve-claim`, `archive-claim`, `restore-claim` | Claim lifecycle. | Curator/dev-only or controlled MCP | Keep but do not expose as normal route unless `lookup`/curator route requires it. |
| `record-plan`, `validate-plan-decomposition`, `confirm-atomic-plan`, `decompose-plan`, `record-debt`, `record-feedback`, `record-model`, `record-flow`, `record-open-question`, `record-artifact` | Plan/debt/feedback/model/flow/open question/artifact records. | Controlled mutating MCP or dev-only low-level | Keep services. Normal agents should write via route-specific tools, not raw record creation. |
| `hypothesis add/list/close/reopen/remove/sync` | Hypothesis index management. | Controlled MCP or dev-only | 0.4 should prefer claims with lifecycle stage plus chain validation. Direct hypothesis index operations should be curator/dev tools. |

### Runtime Gate CLI

Source: `plugins/trust-evidence-protocol/scripts/runtime_gate.py`.

| Command | Current role | 0.4.0 classification | Recommendation |
|---|---|---:|---|
| `hydrate-context`, `show-hydration` | Hydration cache operations. | Hook/dev-only | Move to hydration service. Hooks call service directly. |
| `preflight-task --mode reasoning|planning|edit|action|final` | Action/task/strictness gate. | Hook-internal service | Keep CLI wrapper only for tests/debug. |
| `stop-guard` | Final/autonomous task stop validation. | Hook-internal service | Keep service; final answer gate should use 0.4 `REASON` finalization rules. |
| `confirm-task` | User focus confirmation. | Controlled MCP/task service | Keep but do not leave as ad hoc CLI-only route. |
| `invalidate-hydration` | Marks hydration stale after mutations. | Hook-internal service | Hooks should call service directly. |

## Current MCP Surface

Source: `plugins/trust-evidence-protocol/mcp/tep_server.py`.

Important current fact: the MCP server says it "intentionally delegates all policy and context logic to `context_cli.py`" and calls it through `subprocess.run`. This directly conflicts with the 0.4.0 decision that MCP, hooks, and CLI call shared core services directly.

| MCP tool | Current behavior | Current mutability | 0.4.0 classification | Recommendation |
|---|---|---:|---:|---|
| `next_step` | CLI wrapper around `next-step`. | Read-only | Front-door | Keep as primary front door; return nearest route branches only. |
| `lookup` | CLI wrapper around `lookup`; may create WCTX depending on CLI behavior. | Possibly mutating | Front-door | Keep as primary fact/code/policy/theory route. Make WCTX creation explicit in response. |
| `brief_context` | CLI wrapper broad summary. | Read-only | Drill-down | Keep only as route output, not primary normal path. |
| `search_records`, `claim_graph` | Direct search tools. | Read-only | Drill-down/obsolete as front-door | Keep only after `lookup` route authorizes drill-down. |
| `record_detail`, `linked_records` | Reads specific graph records. | Read-only | Drill-down | Keep. Add telemetry and raw-read replacement messaging. |
| `telemetry_report` | Reads telemetry. | Read-only | Dev/diagnostic drill-down | Keep. |
| `backend_status`, `backend_check` | Backend diagnostics. | Read-only | Drill-down | Keep. Must report selected/available/default backend clearly. |
| `guidelines_for` | Guideline lookup. | Read-only | Drill-down/policy route | Keep. `lookup(kind=policy)` should call this internally. |
| `code_search`, `code_info`, `code_smell_report` | Code index/backend reads. | Read-only | Drill-down/code route | Keep. Route must stay project-scoped by default. |
| `code_feedback` | Reviews backend hits; current docs mention apply workflows. | Mostly read-only via MCP currently | Curator/dev route | Keep read-only; mutating apply path must be separate controlled tool. |
| `cleanup_candidates`, `cleanup_archives` | Cleanup diagnostics. | Read-only | Dev-only | Hide from normal route until cleanup is formalized. |
| `augment_chain` | Enriches an evidence chain JSON file. | Read-only | Normal-loop | Keep but redesign to accept a draft object/id, not force file-centric agent work. |
| `topic_search`, `topic_info`, `topic_conflict_candidates` | Topic prefilter. | Read-only | Navigation drill-down | Keep behind lookup/map. |
| `attention_map`, `attention_diagram`, `attention_diagram_compare` | Attention graph views. | Read-only | Navigation drill-down | Keep as map service outputs. |
| `curiosity_map`, `map_brief`, `curiosity_probes`, `probe_inspect`, `probe_chain_draft`, `probe_route`, `probe_pack`, `probe_pack_compare` | Curiosity and visual-thinking route helpers. | Read-only, except HTML generation writes views via CLI. | Navigation drill-down | Consolidate into fewer normal-agent entry points. HTML generation should be explicit user/view operation. |
| `working_contexts`, `working_context_drift` | WCTX reads/drift check. | Read-only | Front-door support | Keep; `next_step`/`lookup` should call them internally. |
| `workspace_admission` | Checks repo/workspace admission. | Read-only | Front-door support | Keep and make mandatory when cwd/repo is outside current anchor. |
| `logic_search`, `logic_check`, `logic_graph`, `logic_conflict_candidates` | Predicate logic navigation/checking. | Read-only | Drill-down/dev | Keep behind lookup/theory route; not proof by itself. |

Missing MCP tools for the 0.4.0 normal loop:

- `record_evidence`
- `validate_chain`
- `reason_step`
- `reason_review`
- `task_outcome_check`
- `complete_task` or `finalize_task`
- controlled mutating task decomposition tools

## Hook Behavior Audit

Sources: `plugins/trust-evidence-protocol/hooks/codex/*.py`, `plugins/trust-evidence-protocol/hooks/claude/*.py`.

| Hook area | Current behavior | Problem | 0.4.0 action |
|---|---|---|---|
| Context lookup | `hook_common.locate_context()` calls `resolve_context_root()` with legacy fallback behavior from runtime context root code. | `.codex_context` remains discoverable as runtime context. | Use 0.4 context resolver: explicit context, `.tep` anchor, or `~/.tep_context`; no `.codex_context` fallback outside migration. |
| PreToolUse raw claim read guard | Blocks commands that read raw claim JSON unless `TEP_RAW_RECORD_MODE` is set. | Correct direction, but implemented by shell regex in hook. | Move raw-record policy to shared service. Hook only passes tool/cwd/command. |
| PreToolUse protected reasoning write guard | Blocks direct writes to reasoning ledger paths. | Correct direction, but hook owns detection. | Move protected path checks into storage/policy service. |
| PreToolUse mutation classification | `hook_common.py` has regexes and command parsing for mutation kinds such as `write`, `patch`, `edit`, `delete`. | Duplicates policy and does not match 0.4 enum. Has history of false positives around path substrings and redirection. | Replace with service classifier returning `bash|file-write|mcp-write|git|final` plus read-only/mutating flags. |
| PreToolUse preflight | Calls `runtime_gate.py preflight-task --mode action --kind <kind>`. | Shells out and uses old action-kind model. | Hook calls `PreflightService.check_action()` directly. |
| PreToolUse grant check | Calls `context_cli.py reason-check-grant --mode edit --kind <kind> --command ...`. | Shells out; CLI owns authorization. | Hook calls `ReasonService.check_grant()` directly. |
| PostToolUse grant matching | Calls `context_cli.py reason-match-grant`. | Shells out; duplicates PreToolUse matching. | Hook should receive/derive the same command identity and call service once. |
| PostToolUse RUN capture | Calls `context_cli.py record-run`; can capture `all` or `mutating`. | RUN creation is CLI-specific and not guaranteed to enforce 0.4 provenance contracts. | Hook calls `RunService.record_run()`. Mutating bash must produce/link `RUN-*`; read-only capture should be configurable and low-noise. |
| PostToolUse hydration invalidation | Calls `runtime_gate.py invalidate-hydration`. | Shells out. | Hook calls hydration service. |
| Stop hook | Calls `runtime_gate.py stop-guard`. | Shells out; final reasoning rules are split. | Hook calls task/finalization service and checks final `REASON-*` chain. |

## `.codex_context` Coupling

`.codex_context` is still widely referenced. For 0.4.0 it must become a legacy fixture/migration input only.

| Area | Current coupling | 0.4.0 action |
|---|---|---|
| Root `README.md` | Mentions `.codex_context/` alongside `.tep_context/`. | Public docs should describe `~/.tep_context`; `.codex_context` only in migration notes. |
| `plugins/trust-evidence-protocol/README.md` | Describes legacy fallback, `.codex_context/records`, artifacts, indexes, views, settings, hooks, and many command examples. | Rewrite around MCP front doors and `~/.tep_context`. Move old CLI examples to dev/migration appendix. |
| `docs/reference/plugin-commands.md` | Uses explicit `--context .codex_context` throughout. | Reclassify as dev/debug command reference and update examples to `~/.tep_context` or temp fixtures. |
| `docs/dev/TEP_CORE_BASELINE.md`, `docs/dev/TEP_CORE_REWRITE_CONTEXT.md`, `docs/dev/TEP_DEVELOPER_REFERENCE.md` | Baseline/current docs still define `.codex_context` as active layout/fallback. | Mark as historical or update during 0.4 docs pass. |
| `docs/research/TEP_REASONING_RESEARCH.md`, `docs/research/TEP_RESEARCH_MAP.md` | Research examples include `.codex_context` paths. | Treat as historical examples unless rewritten. |
| `plugins/trust-evidence-protocol/templates/codex_context/` | Template directory and README are named for `.codex_context`. | Replace with `templates/tep_context/`; keep old template only for migration tests if needed. |
| `bootstrap_codex_context.py`, `validate_codex_context.py`, `migrate_legacy_context.py` | Script names and help text encode `.codex_context`. | Keep old names as migration/dev compatibility wrappers or rename with deprecation shims. |
| `context_root.py` | `LEGACY_CONTEXT_DIR = ".codex_context"` and resolver checks nearest legacy root. | Remove runtime fallback. Migration tools may call legacy discovery explicitly. |
| `context_cli.py`, `runtime_gate.py`, `context_lib.py` | Docstrings/help mention `.codex_context`; CLI defaults mention legacy fallback. | 0.4 wrappers should point to `~/.tep_context`. |
| Tests | `test_plugin_cli.py`, `test_mcp_server.py`, `test_hooks_runtime.py`, `test_core_services.py`, and harness setup create/use `.codex_context` fixtures. | Rewrite normal tests to temp `.tep_context`; keep explicit legacy migration tests only. |
| Hook tests | Include raw commands touching `.codex_context/runtime/reasoning` and `.codex_context/artifacts`. | Replace with `.tep_context` normal cases plus migration-specific cases. |

## Current REASON and GRANT Shapes

Source: `plugins/trust-evidence-protocol/tep_runtime/reason_ledger.py`.

Current ledger storage is append-only JSONL under runtime reasoning paths. Each entry includes tamper-evidence fields:

- `id`
- `record_type: "reason"`
- `version`
- `created_at`
- `prev_ledger_hash`
- `entry_hash`
- `ledger_hash`
- `seal`
- `pow`

Current accepted id prefixes:

- `REASON`
- `GRANT`
- `AUTH`
- `USE`

Current accepted grant-like entry types:

- `grant`
- `access_granted`
- `auth_granted`

Current use/reservation entry types:

- `access_used`
- `auth_reserved`

Current `REASON` step payload includes:

- `entry_type: "step"`
- `status: "reviewed"` or `draft`
- `workspace_ref`, `project_ref`, `task_ref`
- `parent_refs`
- `branch`
- `intent`
- `mode`
- `action_kind`
- `why`
- `decision_valid`
- `valid_for`
- `blockers`
- `hypothesis_refs`
- `exploration_context_refs`
- `chain_hash`
- `signed_chain`
- `chain_payload`
- `context_fingerprint`

Current `GRANT` payload includes:

- `entry_type: "grant"`
- `status: "active"`
- `grant_type: "exact_command"` or `action_kind`
- `reason_ref`
- `reason_head_hash`
- `workspace_ref`, `project_ref`, `task_ref`
- `mode`
- `action_kind`
- `chain_hash`
- `signed_chain`
- `context_fingerprint`
- `max_runs`
- `issued_at`
- `valid_from`
- `expires_at`
- optional `tool`, `command`, `command_sha256`, `cwd`

0.4.0 consequences:

- Legacy `AUTH`/`USE` prefixes and `access_*`/`auth_*` shapes must remain readable for audit, but must not authorize actions after migration.
- `used`/reservation semantics should not be the proof of legitimacy. Authorization is the append-only `GRANT-*` record plus validity window plus exact action identity plus linked `RUN-*`/protected record.
- `action_kind` must be normalized to `bash|file-write|mcp-write|git|final`.
- `RUN-*` created from protected bash must link to the valid `GRANT-*`.
- Runtime `CLM-*` must transitively reach `RUN-*`; no runtime claim from an unproven command output.

## Mixed Responsibility Areas

| File/area | Mixed responsibilities | Why it matters for 0.4.0 |
|---|---|---|
| `plugins/trust-evidence-protocol/scripts/context_cli.py` | Argparse, text rendering, JSON rendering, record IO, domain validation, mutation orchestration, chain handling, task lifecycle, workspace assignment, backend commands. | Cannot be the core API. It should become a thin dev/test wrapper over services. |
| `plugins/trust-evidence-protocol/scripts/runtime_gate.py` | Hook-facing CLI, policy checks, hydration, stop guard, context resolution, user-facing output. | Hooks should call services directly. Runtime gate can remain a debug wrapper. |
| `plugins/trust-evidence-protocol/mcp/tep_server.py` | MCP schema, MCP routing, cwd/context safety, subprocess CLI adapter, legacy context description. | MCP must become the main API and cannot delegate policy correctness to CLI shellouts. |
| `plugins/trust-evidence-protocol/hooks/codex/hook_common.py` | Plugin discovery, cache/source resolution, context resolution, shell command parsing, mutation classification, raw-record guard, subprocess wrappers. | Hook adapters should be thin and deterministic. Classification/policy belongs in services. |
| `plugins/trust-evidence-protocol/scripts/context_lib.py` | Compatibility re-export/facade for many runtime helpers; docstring still says `.codex_context`. | Useful as a migration seam, but it hides ownership and encourages more CLI coupling. |
| `plugins/trust-evidence-protocol/tep_runtime/search.py` and `retrieval.py` | Text matching, authority scoring, scope filtering, claim lifecycle ranking, navigation-ish broad search. | 0.4 needs an explicit distinction between proof-capable records and navigation hints. |
| Docs/README/skill command sections | User workflow, dev commands, migration commands, and legacy commands are interleaved. | Normal agents need a small route graph, not a manual. |

## Ranking and Proof/Navigation Mixing

Current ranking paths:

- `search.ranked_record_search()` performs generic text scoring over arbitrary record types.
- `search.score_record()` adds simple status and primary flags.
- `search.search_record_matches()` adds claim retrieval tier and fallback/archive penalties only for claims.
- `retrieval.select_records()` ranks typed record candidates and uses `claim_retrieval_tier()` for claims.
- `lookup` composes record search, code search, map/topic/logic-like navigation, and route hints.

Current problem:

- Direct tools like `search_records` and `claim_graph` can make keyword matches feel like evidence.
- Navigation systems such as CIX, topic, attention, curiosity, and logic are exposed as separate tools instead of being clearly labeled route aids.
- `MODEL-*`/`FLOW-*` are not yet mechanically guaranteed to outrank scattered claims only when backed by supported/user-confirmed theory.
- Runtime observation-heavy claims can appear too strong if lookup does not distinguish repeated runtime evidence from theory/user-confirmed mechanics.

0.4.0 target:

- `lookup` is the only normal retrieval front door.
- `lookup` returns separate buckets: `proof_candidates`, `model_flow_context`, `navigation_hints`, `code_hints`, `curiosity_hints`, `required_drilldowns`.
- Proof-capable records must have provenance and authority metadata.
- Navigation hits must be clearly non-proof and must not be accepted in a validated chain without a canonical record/source bridge.

## Minimal 0.4.0 MCP Tool Set

The normal agent surface should be deliberately small.

### Front Doors

| Tool | Mutability | Contract |
|---|---:|---|
| `next_step(intent, task?, cwd)` | Read-only or WCTX-light mutation if explicitly reported | Returns the nearest route branches, current workspace/project/task, blockers, and exactly which tools are allowed next. |
| `lookup(query, reason, kind=auto, cwd, scope=current, mode=general)` | Read-only by default; may create explicit WCTX only if contract says so | Returns proof candidates, model/flow context, navigation hints, chain starter candidates, and next route branches. |

### Normal Loop Tools

| Tool | Mutability | Contract |
|---|---:|---|
| `record_evidence(kind, support, intended_claim?)` | Mutating | Agent supplies file/URL/line/quote, user input ref, command output ref, or artifact ref. Service creates/links `FILE-*`, `ART-*`, `SRC-*`, optional draft `CLM-*`, and CIX links when applicable. |
| `augment_chain(chain_draft)` | Read-only | Mechanically fills missing source quotes, linked refs, CIX links, graph paths, and validation context. |
| `validate_chain(chain, mode, action_kind?)` | Read-only | Accepts/rejects chain. Enforces provenance, no unsupported proof hypotheses, no hypothesis-on-hypothesis proof, runtime-to-RUN reachability, task scope, and model/flow source constraints. |
| `reason_step(chain, intent, mode, action_kind?, why, parent_refs?, branch?)` | Mutating | Appends `REASON-*` step. Rejects duplicate unchanged chains for same task/mode/branch. |
| `reason_review(reason_ref, mode, action_kind, command?, cwd?)` | Mutating | Appends `GRANT-*` when step validates and requested action is allowed. |
| `task_outcome_check(task_ref, outcome)` | Read-only | Tells whether final/done/blocked/user-question is mechanically allowed. |
| `complete_task(task_ref, outcome, reason_ref?)` | Mutating | Finalizes task only after outcome check and final chain requirements. |

### Drill-Down Tools

| Tool | Mutability | Contract |
|---|---:|---|
| `record_detail(record)` | Read-only | Read a specific record through telemetry and source quote limits. |
| `linked_records(record, depth, direction)` | Read-only | Expand local graph around a known record. |
| `guidelines_for(task, domain)` | Read-only | Policy/guideline drill-down. |
| `workspace_admission(repo, cwd)` | Read-only | Classifies external repo access; must not auto-add projects/workspaces. |
| `backend_status`, `backend_check` | Read-only | Shows backend availability and selected scope. |
| `code_search`, `code_info` | Read-only | Code navigation through TEP, not raw backend identity. |
| `map_brief`, `curiosity_map` | Read-only unless `html=true` is explicit | Visual-thinking/navigation. |
| `telemetry_report` | Read-only | Dev/diagnostic route. |

Everything else should be dev/curator/migration-only until it has a route contract.

## Route Graph Behavior

`next_step` and `lookup` must prevent command-menu wandering.

Required response shape:

```json
{
  "contract_version": "0.4",
  "focus": {
    "workspace_ref": "WSP-*",
    "project_ref": "PRJ-* or null",
    "task_ref": "TASK-* or null",
    "wctx_ref": "WCTX-* or null"
  },
  "route": {
    "state": "needs_lookup|needs_evidence|needs_reason|needs_grant|can_act|can_final|blocked",
    "allowed_next_tools": ["lookup", "record_evidence"],
    "blocked_tools": [{"tool": "record_detail", "reason": "lookup first"}],
    "branches": [
      {"label": "inspect facts", "tool": "lookup", "why": "..."},
      {"label": "capture support", "tool": "record_evidence", "why": "..."}
    ]
  },
  "proof_context": {
    "proof_candidates": [],
    "model_flow_context": [],
    "navigation_hints": [],
    "chain_starter": {}
  }
}
```

Rules:

- Normal route output should list only the nearest next tools, not the full plugin command catalog.
- `lookup` should be the default way to find new chain nodes.
- If lookup cannot find new nodes, route may suggest revisiting prior nodes, creating an exploration hypothesis, asking the user, or opening a curator pool.
- Drill-down tools should require a known record id or route hint.
- Raw record access remains blocked outside debug/migration/forensics/plugin-development modes.

## Migration Dry-Run and Apply Checks

### Dry-Run Acceptance Checks

Dry-run must not write to the target context.

Required report:

- Source roots inspected.
- Target `~/.tep_context` path.
- Backup plan path.
- Record counts by type.
- Canonical id collision report.
- Records that lack workspace/project/task scope where required.
- `SRC-*` records without transitive `INP-*`, `FILE-*`, `ART-*`, or `RUN-*` provenance.
- Runtime `CLM-*` records without transitive `RUN-*` provenance.
- Old `GRANT-*`, `AUTH-*`, `USE-*`, `access_granted`, `auth_granted`, `access_used`, and `auth_reserved` records that will be preserved but revoked for authorization.
- Proposed `INP-* input_kind=migration_batch` records.
- Legacy `.codex_context` path references that would remain in record text.
- Records whose ids can be preserved.
- Records that require new ids, with reasons.
- Post-migration validators that would run.

### Apply Acceptance Checks

Apply must:

- Create a backup/archive before writing.
- Preserve canonical ids where possible.
- Create migration `INP-*` records with `input_kind=migration_batch`.
- Link legacy records to migration input without pretending that migration was runtime execution.
- Preserve old GRANT/AUTH/USE ledger entries for audit.
- Revoke old grant shapes for authorization.
- Write a migration report into `~/.tep_context`.
- Remove runtime `.codex_context` fallback from the migrated active context.
- Run post-migration validation:
  - storage schema
  - provenance graph
  - workspace/project/task scope
  - reason ledger integrity
  - old grant revocation
  - lookup route smoke
  - hook preflight smoke through service, not shellout

## Keep/Move/Delete Table

| Surface | Keep | Move | Delete/deprecate |
|---|---|---|---|
| Plugin and skill names | Keep unchanged. | N/A | N/A |
| MCP server | Keep as normal agent API. | Move implementation from CLI subprocess to direct core services. | Deprecate direct exposure of command-zoo equivalents. |
| CLI | Keep for dev/debug/migration/CI. | Move domain logic into services; CLI becomes wrapper. | Delete normal-agent dependency on CLI. |
| Hooks | Keep Codex/Claude adapters. | Move policy/classification/grant/run/hydration to services. | Delete hook-owned duplicate policy and shellouts. |
| `.codex_context` | Keep only as migration fixture/source. | Move normal docs/tests/templates to `~/.tep_context`. | Delete runtime fallback. |
| `context_cli.py` | Keep temporarily. | Split service calls, rendering, argparse, storage. | Delete or freeze low-level normal-agent commands after MCP replacement. |
| `runtime_gate.py` | Keep as dev wrapper. | Move gates to services. | Delete hook dependency on script execution. |
| `record-source`/`record-claim` manual paths | Keep for migration/plugin-dev. | Move normal support capture to `record_evidence`. | Hide from normal route. |
| Search/map/topic/logic tools | Keep as backend services. | Route through `lookup` and map outputs. | Delete direct first-step usage from skill/README. |
| Old GRANT shapes | Keep for audit. | Migrate/revoke for authorization. | Delete as valid authorization inputs. |

## Risk Table

| Risk | Severity | Evidence | Mitigation |
|---|---:|---|---|
| MCP correctness depends on CLI subprocesses. | High | `tep_server.py` delegates policy/context logic to `context_cli.py`. | Build shared core services and make MCP call them directly. |
| Runtime still discovers `.codex_context`. | Critical | `context_root.py` has `LEGACY_CONTEXT_DIR` and fallback discovery. | Remove runtime fallback; migration tools may explicitly read legacy roots. |
| Normal route surface is too large. | High | `context_cli.py` exposes more than 100 command/subcommand paths. | Expose only `next_step`/`lookup` plus normal loop MCP tools to agents. |
| Hooks duplicate and drift from runtime policy. | High | Hook regex classification and shellouts implement their own behavior. | Replace with shared `ActionClassifier` and gate services. |
| GRANT authorization accepts legacy shapes. | High | `LEDGER_ID_PREFIXES` includes `AUTH`/`USE`; grant entry types include `access_granted`/`auth_granted`. | Migration revokes old shapes for authorization while preserving audit. |
| Current action kinds do not match 0.4 enum. | High | Current classifier returns labels such as `write`, `patch`, `edit`, `delete`, `move`, `update`. | Introduce `bash|file-write|mcp-write|git|final` contract and map old labels only in migration/audit. |
| Ranking can mix proof with navigation. | High | Direct search tools and broad ranked search expose keyword hits as candidate facts. | `lookup` must bucket proof candidates separately from navigation hints. |
| Runtime evidence may outrank theory/user-confirmed mechanics. | Medium | Current claim ranking has lifecycle tier but no explicit 0.4 authority formula for repeated runtime vs theory. | Add authority profile to lookup ranking. MODEL/FLOW only from supported/user-confirmed theory. |
| Tests normalize `.codex_context`. | Medium | Many tests create `tmp_path / ".codex_context"`. | Rewrite normal fixtures to `.tep_context`; keep legacy migration tests explicit. |
| Docs teach obsolete paths. | Medium | README and command reference use `.codex_context` examples extensively. | Rewrite public/agent docs after service contracts are implemented. |
| CIX/backend storage scope may confuse agents. | Medium | Backend status/search can disagree when backend marker/runtime path differs. | Keep backend identity behind TEP, report selected backend/scope, and test project/workspace lookup. |
| Local `.env` exists in working tree. | Medium | `find` shows `./.env`; `git ls-files` did not report it in this audit output. | Keep ignored/unpublished; never copy into artifacts or docs. |

## Suggested Milestone Order

1. **0.4 contract freeze**
   - Define `contract_version: "0.4"`.
   - Define canonical MCP request/response dataclasses and exported JSON Schema.
   - Define context root resolution contract: explicit/anchor/`~/.tep_context`; no runtime `.codex_context`.

2. **Storage and migration scaffold**
   - Implement dry-run/apply migration service skeleton.
   - Preserve ids where possible.
   - Create migration `INP-* input_kind=migration_batch`.
   - Preserve old GRANT ledger entries but revoke them for authorization.

3. **Shared core service seam**
   - Extract context resolution, record IO, route response, chain validation, reason/grant, run capture, and action classification into services.
   - Keep CLI wrappers thin.

4. **MCP front-door rebuild**
   - Make MCP call services directly.
   - Expose minimal normal loop tools.
   - Move old direct tools to drill-down/dev-only categories.

5. **Hook rebuild**
   - Hooks call services directly.
   - New action enum.
   - Mutating bash produces/link `RUN-*`.
   - Protected final answer checks final reasoning.

6. **Lookup/ranking rebuild**
   - Split proof candidates from navigation hints.
   - Prefer MODEL/FLOW only when source constraints are satisfied.
   - Add route branches and "new chain node" default behavior.

7. **Docs and tests cleanup**
   - Rewrite normal tests to `.tep_context`.
   - Keep `.codex_context` only in migration fixtures.
   - Replace README/SKILL command catalogs with route graph.

## Slice-1 Implementation Recommendation

Slice 1 should be deliberately boring. It should not chase curiosity maps, CocoIndex integration, z3, or UI output. Those are valuable, but they need a stable core first.

### Slice-1 Scope

1. Add 0.4 contracts and schemas:
   - `ContextRootResolution`
   - `RouteResponse`
   - `LookupResponse`
   - `RecordEvidenceRequest`
   - `ChainDraft`
   - `ChainValidationResult`
   - `ReasonStepRequest`
   - `ReasonReviewRequest`
   - `GrantRecordV04`
   - `MigrationPlan`
   - `MigrationReport`

2. Add storage contract:
   - primary root is `~/.tep_context`
   - local `.tep` anchor points to workspace/project/task focus
   - no `.codex_context` runtime fallback
   - legacy roots are passed only to migration service

3. Add migration scaffold:
   - dry-run report
   - backup plan
   - apply skeleton
   - migration `INP-* input_kind=migration_batch`
   - old grant revocation report
   - id preservation report

4. Add service boundaries without changing behavior yet:
   - `ContextRootService`
   - `RecordStore`
   - `MigrationService`
   - `RouteService`
   - `ChainService`
   - `ReasonLedgerService`
   - `ActionClassifier`
   - `RunCaptureService`

5. Add conformance tests:
   - normal MCP route never exposes full command menu
   - `.codex_context` is not discovered by runtime resolver
   - migration dry-run detects legacy records and old grants
   - old grants are readable but not authorizing
   - new action enum accepts only `bash|file-write|mcp-write|git|final`
   - runtime `SRC-*` requires transitive `INP-*|FILE-*|ART-*|RUN-*`
   - runtime `CLM-*` requires transitive `RUN-*`

### Slice-1 Non-Goals

- No full CLI deletion.
- No full README rewrite before contracts exist.
- No new map/curiosity mechanics.
- No new backend integration.
- No live-agent proof run until the service contracts and migration scaffolding are testable.

### Why This Slice First

The largest current risk is not a missing feature. It is that every surface can make slightly different decisions: CLI, MCP, hooks, tests, and docs all encode behavior. Slice 1 should make one place responsible for contracts and storage. Once that exists, later slices can move behavior behind the shared services without changing the agent-facing model again.
