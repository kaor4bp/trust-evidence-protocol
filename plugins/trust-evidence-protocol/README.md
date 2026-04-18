# TEP Runtime Plugin

This plugin appears in Codex UI as `TEP Runtime`.
It is the storage, runtime, and guardrail layer for the `trust-evidence-protocol` skill.
The skill defines reasoning discipline; the plugin provides commands, validation, hydration, generated views, hook guardrails, and read-only MCP lookup where Codex can enforce them.

Responsibilities:

- resolve a TEP context root, targeting global `~/.tep_context` with legacy `.codex_context` fallback
- honor workdir-local `.tep` anchor files that select the global context root plus current workspace/project focus
- bootstrap a strict context layout
- provide canonical JSON record templates
- validate persistent-memory records before hydration or review
- scan structured comparable claims for contradictions among known claims
- manage claim lifecycle so true historical/resolved claims stay searchable without dominating current task context
- keep persistent plan/debt records and generate an active prioritization view
- keep constructive `PRP-*` agent proposals with cited context, options, risks, and stop conditions
- keep agent plugin feedback as `SRC-*` plus `DEBT-*` through `record-feedback`
- keep `WCTX-*` working-context snapshots for focus, handoff, assumptions, and retrospective
- build generated lexical `topic_index/` data for search prefiltering and candidate review
- build generated predicate `logic_index/` data from `CLM.logic` for symbol, atom, rule, and conflict-candidate checks
- capture `INP-*` user-prompt provenance through the UserPromptSubmit hook when enabled by `input_capture`
- push agents to preserve reusable discoveries, rules, actions, plans, debt, questions, models, flows, and proposals as records

Non-responsibilities:

- redefining epistemic rules from the skill
- treating memory as proof
- storing canonical data in generated views or ledgers

Current implementation:

- `templates/codex_context/` contains the canonical `.codex_context` README and JSON record templates
- `scripts/bootstrap_codex_context.py` creates the strict storage layout
- `scripts/validate_codex_context.py` validates record files and reference integrity
- `scripts/context_cli.py` exposes explicit operational commands
- `mcp/tep_server.py` exposes read-only context lookup tools over MCP stdio
- `.mcp.json` declares the local MCP server for clients that support plugin MCP discovery
- `skills/trust-evidence-protocol/SKILL.md` contains only core semantics and workflow routing
- `skills/trust-evidence-protocol/workflows/` contains task-specific operating procedures

Runtime hook output is intentionally compact by default. Detailed context should be pulled through MCP tools such as `brief_context`, `search_records`, `guidelines_for`, `code_search`, and `code_info`.
Human-facing TEP Runtime output uses the `🛡️` marker so plugin messages are easy to distinguish from normal agent prose.
Machine-readable JSON fields and canonical records do not rely on the marker.

Skill workflow files:

- `workflows/information-lookup.md`: what to do when searching, answering, investigating, or reconciling facts
- `workflows/before-action.md`: what to do before planning, editing, mutating, persisting, or asking permission
- `workflows/after-action.md`: what to do after edits, tests, commands, discoveries, or completed work
- `workflows/persistence-and-records.md`: when and how to persist information into canonical records
- `workflows/plugin-commands.md`: command reference for hydration, review, strictness, records, projects, tasks, and hypotheses

The preferred live context root is `~/.tep_context`.
Legacy repo-local `.codex_context` roots remain supported for migration and tests.

Local workdirs may contain a `.tep` JSON anchor.
The anchor is local configuration, not canonical memory and not proof.
It lets one global context hold multiple workspaces/projects while each checkout still resolves the right focus:

- `context_root`: canonical context root, usually `~/.tep_context`
- `workspace_ref`: active `WSP-*` memory boundary for this workdir
- `project_ref`: optional active `PRJ-*` focus inside the workspace
- `settings`: local hook/context-budget preferences and optional `allowed_freedom`

Local `.tep.settings.allowed_freedom` can only keep or lower the effective freedom.
It cannot raise a workspace from `proof-only` to `evidence-authorized` or `implementation-choice`; escalation still goes through canonical strictness requests and approvals.

Context-root resolution order is:

1. explicit `--context`
2. `TEP_CONTEXT_ROOT`
3. nearest `.tep.context_root`
4. global `~/.tep_context`
5. nearest legacy `.codex_context`
6. global `~/.tep_context` fallback

The only canonical storage layer is:

- `.codex_context/records/`
- `.codex_context/artifacts/`

Canonical records are stored as one JSON object per file.

Generated navigation layer:

- `.codex_context/code_index/entries/CIX-*.json`
  - code map entries for files, directories, globs, symbols, and logical areas
  - stores AST/regex/outline metadata, manual features, annotations, and navigation links
  - may be rebuilt or refreshed at any time
  - not a source of truth and not proof
- `.codex_context/topic_index/*.json`
  - generated lexical topic maps over canonical records
  - helps search, grouping, context assembly, and contradiction-candidate prefiltering
  - may be rebuilt at any time
  - not a source of truth and not proof
- `.codex_context/logic_index/*.json`
  - generated predicate projection over optional `CLM.logic` blocks
  - indexes typed symbols, atoms, rules, predicates, and symbol usage
  - helps mechanical conflict-candidate detection without asking an agent to reason over prose
  - may be rebuilt at any time
  - not a source of truth and not proof
- `.codex_context/attention_index/*.json`
  - generated attention map over topic clusters, record taps, cold zones, bridges, and curiosity probes
  - helps an agent choose what to inspect next without reading the whole context
  - may be rebuilt at any time
  - not a source of truth and not proof
- `.codex_context/activity/taps.jsonl`
  - append-only activity signals such as retrieved, opened, cited, decisive, updated, challenged, or contradicted
  - not evidence, not proof, and not claim support

Additional transient index:

- `.codex_context/hypotheses.jsonl`
  - index of active tentative `CLM-*` records
  - not a second source of truth

`review/` is generated diagnostics, not a source of truth.
`review/attention.md` is a generated navigation view, not a source of truth.
`review/resolved.md` is a generated lifecycle/navigation view for fallback historical and archived claims, not a source of truth.

`backlog.md` is a generated working view, not a source of truth.

`runtime/` is generated runtime bookkeeping, not a source of truth.

`.codex_context/settings.json` is the policy layer for:

- `allowed_freedom`
- `current_workspace_ref`
- `current_project_ref`
- `current_task_ref`
- repo-local Codex hook modes
- `context_budget` preferences for compact/normal/debug output
- `input_capture` policy for prompt/session capture
- `artifact_policy` for when referenced files are copied or only linked
- `cleanup` staging and retention thresholds
- optional `analysis` backend policy for logic solving and topic prefiltering

`.tep` is intentionally excluded from canonical storage.
Do not use it to store records, claims, user facts, permissions, restrictions, or guidelines.

Tick-tock development should target `~/.tep_context`: use the current plugin to
develop the next plugin version, merge local context into the unified context,
then switch agents to the next version. Agents should record plugin bugs,
friction, false positives, false negatives, docs gaps, and migration issues with
`record-feedback` so maintainers can process them through normal debt/search
workflows.

Default retention/capture policy:

- `input_capture.user_prompts = "capture"`
- `input_capture.file_mentions = "reference-only"`
- `artifact_policy.copy_mode = "reference-only"`
- `artifact_policy.max_copy_bytes = 1048576`
- `cleanup.mode = "report-only"`
- `cleanup.archive_format = "zip"`
- `cleanup.orphan_input_stale_after_days = 30`
- `cleanup.orphan_record_stale_after_days = 90`
- `cleanup.orphan_artifact_stale_after_days = 30`
- `cleanup.delete_after_archive_days = 180`

`INP-*` prompt records must not be archived just because they have no incoming
links. They become cleanup candidates only after the effective
`cleanup.orphan_input_stale_after_days` threshold. Fresh unlinked prompts are
still useful because an agent may classify them into claims, guidelines,
projects, tasks, proposals, or open questions later.

Default analysis policy:

- `analysis.logic_solver.enabled = true`
- `analysis.logic_solver.backend = "structural"`
- `analysis.logic_solver.optional_backends = ["z3"]`
- `analysis.logic_solver.missing_dependency = "warn"`
- `analysis.logic_solver.install_policy = "ask"`
- `analysis.logic_solver.mode = "candidate"`
- `analysis.logic_solver.timeout_ms = 2000`
- `analysis.logic_solver.max_symbols = 500`
- `analysis.logic_solver.max_rules = 100`
- `analysis.logic_solver.use_unsat_core = true`
- `analysis.topic_prefilter.enabled = true`
- `analysis.topic_prefilter.backend = "lexical"`
- `analysis.topic_prefilter.optional_backends = ["nmf"]`
- `analysis.topic_prefilter.missing_dependency = "warn"`
- `analysis.topic_prefilter.install_policy = "ask"`
- `analysis.topic_prefilter.rebuild = "manual"`
- `analysis.topic_prefilter.max_records = 5000`

`analysis` is policy, not proof and not a dependency installer.
The baseline runtime must work with structural logic checks and lexical topic prefiltering.
Optional backends such as `z3` and `nmf` may be enabled per project, but missing dependencies should warn or error according to settings instead of silently installing packages.
When `install_policy = "ask"`, the agent may propose the install command and record the action only after user approval.

Prompt capture mechanics:

- `record-input` creates canonical `INP-*` provenance records.
- UserPromptSubmit hook capture follows `settings.input_capture.user_prompts`.
- `capture` stores the prompt text in the `INP-*` record.
- `metadata-only` stores a placeholder and prompt/session metadata without raw text.
- `off` disables prompt capture.
- The hook rehydrates after a successful capture so prompt provenance does not leave the next agent turn mechanically stale.

## Agent Operating Path

When an agent needs to answer a question, plan, ask for permission, or edit code, it should search existing context first.

Use this order:

1. Run or inspect hydration: current workspace, current project, current task, current task type, active restrictions, active guidelines, active permissions, conflicts.
2. Read `review/attention.md` or run `brief-context --task "..."` as navigation only.
3. Check active `WCTX-*` working contexts for pinned refs, focus paths, assumptions, and concerns.
4. Use `topic-search` or `topic_info` as a prefilter when keyword search is too broad, then inspect canonical records.
5. Use `logic-search` / `logic-check` when claims have `CLM.logic` atoms or rules, then inspect canonical records.
6. Check relevant canonical `MODEL-*` and `FLOW-*` records for the current project/task.
7. Check canonical `CLM-*` records in trust order: active `corroborated`, then active `supported`, then active `contested/rejected` for conflict awareness, then active `tentative` for exploration.
8. Check active `GLD-*` guidelines for coding, testing, review, debugging, architecture, and agent-behavior rules.
9. Check active `PRP-*` proposals for agent critique, recommended options, risks, and stop conditions.
10. Check the `SRC-*` records behind decisive claims and guidelines, preferring accepted independent sources.
11. Use resolved/historical `CLM-*` claims only as fallback context when active records do not answer the task.
12. Use archived `CLM-*` claims only by explicit id, audit, rollback, or user request.
13. Check `OPEN-*`, `PLN-*`, and `DEBT-*` for unresolved questions and continuity.
14. If the intended work changes task type, run `task-drift-check`; pause/switch/start tasks instead of silently working in the wrong task context.
15. For substantial repeated work modes, run `review-precedents` to inspect past `TASK-*` records with the same `task_type`.
16. Only then inspect code/runtime/docs or ask the user for missing support.

Important boundary:

- `CLM-*` is the only canonical truth record.
- `GLD-*` records are operational rules; they guide action but do not prove truth.
- `PRP-*` records are constructive agent proposals; they guide critique/options but do not prove truth or grant permission.
- `TASK-*` records carry `task_type` and execution focus; they guide continuity and precedent review but do not prove truth.
- `WCTX-*` records carry operational focus, pinned refs, local assumptions, and handoff context; they do not prove truth.
- `CIX-*` code-index entries are navigation/scope/impact objects; they can guide where to look but do not prove behavior, compliance, or correctness.
- `topic_index/` is generated lexical prefiltering; it can suggest records to compare but cannot declare contradictions.
- `CLM.logic` is an optional machine-checkable projection of a claim; it does not create truth outside the claim.
- `logic_index/` is generated predicate checking/navigation data; it can suggest conflicts but cannot change claim status.
- `fact`, `evidence`, `hypothesis`, and `observation` are roles or lifecycle stages of `CLM-*`.
- Generated views such as `review/attention.md`, `index.md`, `backlog.md`, and `brief-context` output are navigation, not proof.
- Proof must resolve to canonical `CLM-*` records and their accepted `SRC-*` support.

Why this matters for the agent:

- Confirming or falsifying a claim makes future lookup cheaper.
- Promoting a claim from `tentative` to `supported` or `corroborated` reduces repeated investigation.
- Marking stale, contested, rejected, superseded, resolved, historical, or archived records prevents future agents from following bad shortcuts.
- Updating models and flows after claim changes gives the next agent a higher-level map instead of a flat record search.
- Recording reusable guidelines keeps coding/test/review rules available to future agents.
- Recording actions, plans, debt, open questions, and proposals keeps continuity instead of leaving it in chat.

Persistence rule:

- If a future agent would need the information to avoid rediscovery, avoid repeating a mistake, follow a rule, continue a plan, or understand a decision, write or update canonical records.
- If the information is transient, redundant, or abandoned, keep it ephemeral and do not pollute the store.
- If the information is large, copy it as an artifact and cite it from records.

Write boundary:

- Canonical records under `.codex_context/records/` must be created or updated through plugin commands such as `record-source`, `record-claim`, `record-guideline`, `record-action`, `resolve-claim`, or `archive-claim`.
- Captured prompt provenance should use `record-input`; an `INP-*` is not proof until later classified into `SRC-*`, `CLM-*`, `GLD-*`, `TASK-*`, or another appropriate record.
- Do not write `.codex_context/records/*.json`, indexes, settings, or generated views with shell redirection, `tee`, ad hoc scripts, or manual JSON edits when a plugin command exists.
- Diagnostic payloads may be written directly only under `.codex_context/artifacts/`; this is for screenshots, logs, copied command output, and similar raw material.
- After writing a raw artifact, create or update a `SRC-*` record with `record-source --artifact-ref artifacts/...` when the artifact should support future reasoning.
- The artifact-write exception does not grant permission to write source files, `/tmp`, arbitrary workspace paths, or canonical records.
- CIX entries may point to canonical records, and some canonical records may point to CIX entries with `code_index_refs`, but those links are scope/navigation only.
- Do not use `CIX-*` as `CLM-*` support, `SRC-*` support, or `ACT-*` justification.

## MCP Interface

The plugin includes a minimal stdio MCP server declared in `.mcp.json`.

MCP is intentionally read-only in this plugin version. It is a faster context lookup surface, not a second mutation API.

Exposed tools:

- `brief_context`: task-oriented context brief
- `search_records`: keyword search across canonical records
- `record_detail`: one record with source quotes and direct links
- `linked_records`: graph expansion around one record
- `guidelines_for`: scoped active guidelines for a task
- `code_search`: CIX navigation search
- `code_smell_report`: read-only CIX smell annotation report
- `code_info`: one CIX entry/path projection
- `cleanup_candidates`: read-only stale/noise triage
- `cleanup_archives`: read-only `ARC-*` archive catalog/detail lookup
- `augment_chain`: read-only evidence-chain quote/source/validation enrichment
- `topic_search`: generated lexical topic search
- `topic_info`: generated topic terms and similar records for one record
- `topic_conflict_candidates`: generated lexical overlap candidates for review
- `attention_map`: generated attention-map clusters and cold zones; defaults to current `.tep` workspace/project/task focus
- `curiosity_probes`: generated bounded curiosity questions; defaults to current `.tep` workspace/project/task focus
- `probe_inspect`: generated probe context with canonical record summaries, source quotes, direct link status, and follow-up commands
- `probe_chain_draft`: generated evidence-chain skeleton for one probe; validates/augments the draft but does not make it proof
- `probe_pack`: compact generated bundle of top probes, inspection summaries, and chain-draft validation
- `working_contexts`: read-only `WCTX-*` working-context lookup
- `logic_search`: generated predicate atom/rule search
- `logic_check`: read-only predicate consistency summary
- `logic_graph`: generated symbol/predicate/rule-variable graph and vocabulary-smell lookup
- `logic_conflict_candidates`: predicate-level conflict candidates

Rules:

- Prefer MCP read-only tools when available for lookup-heavy work.
- Pass `cwd` when the caller knows the active workdir so MCP can resolve the nearest `.tep` anchor instead of the MCP server's own cwd.
- For attention tools, use default `scope=current` during normal work; use `scope=all` only for cross-workspace/project triage.
- Curiosity probe `score` and `explanation` fields are mechanical navigation hints, not confidence or proof.
- Use `probe_inspect` after choosing a curiosity probe so the runtime, not the agent, expands the pair into canonical inspection context.
- Use `probe_chain_draft` when you need a mechanically assembled proof skeleton from a selected probe, then validate and revise before user-facing proof.
- Use `probe_pack` when you need a compact first pass over top probes without manually chaining several lookup tools.
- Fall back to `context_cli.py` commands when MCP is unavailable or when mutation is needed.
- Do not expose mutating commands through MCP until authorization, hook, and audit behavior is explicitly designed.
- MCP results are navigation unless they include canonical `CLM-*`, `SRC-*`, `GLD-*`, or other record ids with enough detail to cite.
- Before citing a fact, use `record_detail` or `linked_records` to obtain the canonical id and source quote.

## Explicit Commands

Use:

```bash
python3 plugins/trust-evidence-protocol/scripts/context_cli.py --context .codex_context <command>
```

Commands:

- `help [modes|commands|records|workflows|all]`
  - compact human-facing overview of TEP Runtime modes and commands

- `configure-runtime`
  - shows or updates `hooks.verbosity`
  - shows or updates `context_budget`
  - shows or updates optional `analysis` backend policy
  - useful examples:
    - `configure-runtime --show`
    - `configure-runtime --hook-verbosity quiet --context-budget hydration=compact`
    - `configure-runtime --analysis logic_solver.backend=z3 --analysis logic_solver.install_policy=ask`
    - `configure-runtime --analysis topic_prefilter.backend=nmf --analysis topic_prefilter.missing_dependency=warn`

- `review-context`
  - checks structural correctness
  - checks source-backed claim/action chains
  - regenerates `review/broken.md`, `review/stale.md`, `review/conflicts.md`
  - regenerates `review/attention.md`
  - regenerates `backlog.md`
  - regenerates `index.md`
  - returns non-zero only for structural validation errors; structured claim conflicts are reported without aborting the command

- `reindex-context`
  - regenerates `index.md`
  - regenerates `backlog.md`
  - regenerates `review/attention.md`
  - regenerates generated review files
  - reports missing canonical record directories or unresolved refs
  - returns non-zero only for structural validation errors; structured claim conflicts are reported without aborting the command

- `scan-conflicts`
  - scans only `supported` and `corroborated` claims
  - ignores fallback-only resolved/historical/archived claims when building current contradiction blockers
  - uses the optional `comparison` block on claims instead of free-text matching
  - groups claims by normalized `comparison.key` and optional `comparison.context_scope`
  - compares only compatible structured values
  - writes `review/conflicts.md`
  - returns zero when conflicts are found; use `preflight-task --mode planning` for blocking policy

- `record-guideline`
  - creates a `GLD-*` operational rule for `code`, `tests`, `review`, `debugging`, `architecture`, or `agent-behavior`
  - requires accepted `SRC-*` support for the user instruction, doc, or other source behind the rule
  - supports `applies_to=global|project|task` and `priority=required|preferred|optional`
  - keeps style/test/code conventions separate from truth-bearing `CLM-*` records

- `show-guidelines`
  - shows active guidelines for the current project/task, or all guidelines with `--all`
  - supports `--domain code|tests|review|debugging|architecture|agent-behavior`

- `record-proposal`
  - creates a `PRP-*` constructive proposal record for the agent's position, critique, and solution options
  - requires `--subject`, `--position`, at least one `--proposal "title|why|tradeoff1;tradeoff2|recommended"`, and cited context via claim/guideline/model/flow/open-question refs
  - attaches the current project and current task automatically when explicit refs are omitted
  - may include lightweight `--assumption`, `--concern`, `--risk`, and `--stop-condition`
  - proposal assumptions are not truth support and cannot be used as proof in evidence chains

- `brief-context --task "..."`
  - prints a task-oriented reasoning brief from the current `.codex_context`
  - surfaces relevant primary `MODEL-*` / `FLOW-*`, candidate claims, fallback historical claims, active hypotheses, open questions, applicable permissions, active guidelines, active restrictions, active proposals, plans, and debt
  - filters relevance sections by `settings.json.current_project_ref` when a current project is set
  - excludes records tied to another `TASK-*` through `task_refs`
  - is read-only and fails if the context is structurally invalid

- `search-records --query "..." [--type claim] [--include-fallback] [--include-archived] [--format text|json]`
  - searches canonical records by keyword and returns ranked candidate ids
  - respects current project and task filters by default
  - excludes lifecycle fallback and archived claims by default so current facts rank first
  - use `--include-fallback` for historical fallback matches and `--include-archived` for explicit audit search
  - use `linked-records --record ID` after search to expand the graph around a selected result

- `record-detail --record ID [--format text|json]`
  - shows one canonical record, its lifecycle/status, source quotes, and direct incoming/outgoing links
  - use this after `search-records` when the agent needs the exact quote and id before citing a record

- `record-neighborhood --record ID [--depth N] [--format text|json]`
  - shows a record plus linked records by graph distance
  - use this when deciding whether a claim, guideline, model, flow, plan, or debt item is safe to modify or ignore

- `linked-records --record ID [--direction incoming|outgoing|both] [--depth N] [--format text|json]`
  - shows linked canonical records for any record id, not only claims
  - outgoing links are records referenced by the anchor
  - incoming links are records that reference the anchor
  - prints the fields that create each edge, such as `source_refs`, `claim_refs`, `resolved_by_claim_refs`, or nested flow fields
  - use `--format json` when another tool or agent needs structured graph data

- `guidelines-for --task "..." [--domain code|tests|review|debugging|architecture|agent-behavior] [--format text|json]`
  - selects active scoped `GLD-*` rules that apply to a concrete task
  - respects current project and task filters by default
  - before sizeable code/test edits, the agent should show the selected guideline ids plus short quotes/rules

- `topic-index build --method lexical`
  - rebuilds `.codex_context/topic_index/records.json`, `topics.json`, `by_record.json`, `by_topic.json`, and reports
  - writes `topic_index/conflict_candidates.md` as a review prefilter
  - does not create facts, claims, or contradictions

- `topic-search --query "..."`
  - searches generated lexical topic metadata
  - use it when canonical keyword search is too broad or when assembling context cheaply
  - follow up with `record-detail` / `linked-records` before citing anything

- `topic-info --record ID`
  - shows generated topic terms and similar records for one canonical record

- `topic-conflict-candidates`
  - shows lexical overlap candidates that may deserve structured comparison
  - candidate output is not proof and does not replace `scan-conflicts`

- `logic-index build`
  - rebuilds `.codex_context/logic_index/atoms.json`, `symbols.json`, `rules.json`, `by_predicate.json`, `by_symbol.json`, `variable_graph.json`, and reports
  - validates that factual atoms reference introduced typed symbols through source-backed `CLM-*` records
  - writes `logic_index/conflict_candidates.md` as a predicate-level review prefilter
  - writes `logic_index/vocabulary_smells.md` as a generated pressure report for orphan symbols, duplicate-like symbols, single-use predicates, and weak/generic rule variables
  - does not create facts, claims, or contradictions

- `logic-search --predicate P [--symbol ns:id] [--claim CLM-*]`
  - searches generated predicate atoms and rules
  - use after broad record/topic search when the relevant facts have `CLM.logic`
  - follow up with `record-detail` / `linked-records` before citing anything

- `logic-graph [--symbol ns:id] [--predicate P] [--smells]`
  - reads generated symbol, predicate, rule-variable, component, and smell metadata
  - use before adding new `CLM.logic.symbols` or predicates to reuse existing vocabulary where possible
  - output is pressure/navigation data, not proof

- `logic-check`
  - read-only predicate consistency check over current `CLM.logic` blocks
  - reports atom/symbol/rule counts and predicate-level candidates
  - accepts `--solver structural|z3|auto`
  - accepts `--closure direct|rules|system`
  - `z3` is optional and reports `available=false` when `z3-solver` is missing
  - Z3 candidates include claim-level `unsat_core` data so agents can inspect the exact `CLM-*` records and logic refs that participate in an inconsistent formal snapshot
  - Z3 output remains candidate/navigation data, not proof; inspect underlying `SRC-*` before changing claim status

- `logic-conflict-candidates`
  - reports same predicate/args/context candidates with opposite polarity or conflicting functional values
  - candidate output is not proof and does not replace claim lifecycle/status decisions

- `working-context create|fork|show|close`
  - manages `WCTX-*` operational context snapshots
  - `create` stores pinned refs, focus paths, topic seeds, local assumptions, and concerns
  - `fork` creates a copy-on-write replacement instead of mutating the old context
  - `show` is read-only and suitable for handoff or retrospective
  - `close` ends a context when it should stop guiding current work

- `cleanup-candidates [--format text|json]`
  - read-only report for stale or noisy records that may be safe to resolve, archive, refresh, or remove later
  - never edits records automatically; cleanup remains a deliberate separate action
  - reports lifecycle attention mismatches, working/stable model or flow dependencies on fallback claims, active hypotheses pointing at fallback claims, and stale orphan `INP-*` inputs

- `cleanup-archives [--archive ARC-*] [--format text|json]`
  - read-only catalog of cleanup archives
  - without `--archive`, lists available `ARC-*` archives and invalid archive entries without failing the whole report
  - with `--archive`, shows the manifest items needed before `cleanup-restore`

- `cleanup-archive --dry-run [--format text|json]`
  - builds a read-only archive manifest plan for archivable cleanup candidates
  - currently includes stale orphan `INP-*` records
  - does not write a zip, mutate records, or delete files

- `cleanup-archive --apply [--format text|json]`
  - writes `.codex_context/archives/ARC-*.zip` plus `.manifest.json`
  - includes `manifest.json` and the original record paths inside the zip
  - does not mutate canonical records and does not delete archived originals

- `cleanup-restore --archive ARC-* --dry-run [--format text|json]`
  - reads a cleanup archive manifest and reports per-item restore status
  - marks files as `restore-ready`, `already-present`, `target-conflict`, `sha256-mismatch`, or `missing-archive-entry`
  - does not write files

- `cleanup-restore --archive ARC-* --apply [--format text|json]`
  - restores only missing files whose archive entry matches the recorded `sha256`
  - skips `already-present` files when the current file matches the archive hash
  - refuses to overwrite conflicting existing files

- `init-code-index --root .`
  - initializes generated `CIX-*` code-index entries from `git ls-files`
  - indexes Python with AST metadata, JS/TS with lightweight import/symbol regexes, and Markdown with heading/link/code-block outline metadata
  - writes `.codex_context/code_index/entries/`, `by_path.json`, `by_ref.json`, and `summary.md`
  - defaults to tracked files only; use `--include-untracked` deliberately
  - bounded by `--max-files` and `--max-bytes-per-file`

- `index-code --root . --include "src/**/*.py" --include "tests/**/*.py"`
  - indexes a scoped file set into `CIX-*` entries
  - preserves manual annotations, manual features, and manual links on refresh
  - excludes common cache/build directories by default

- `code-refresh --root . --path "tests/**/*.py"`
  - refreshes existing CIX metadata for matching paths
  - marks missing files as `status=missing`
  - when a missing path reappears, creates a new `CIX-*` and links it to the old entry with `supersedes_refs`

- `code-info --path <path> --fields target,imports,symbols,features,freshness`
  - shows one CIX entry with explicit projection fields
  - use `--entry CIX-*` when path is ambiguous or historical

- `code-search`
  - searches CIX entries by path, language, code kind, import, symbol, feature, linked ref, or stale state
  - can filter annotations with `--annotation-kind smell` and `--annotation-category ...`
  - returns only requested projection fields and defaults to a small limit
  - hides missing, superseded, and archived entries unless explicitly requested
  - code search is navigation only; read files or create `SRC-*` support before making truth claims

- `code-smell-report [--category ...] [--severity low|medium|high|critical] [--include-stale] [--format text|json]`
  - read-only report of active CIX `smell` annotations
  - hides stale smell annotations by default when their observed file `sha256` no longer matches the current file
  - `--include-stale` shows smells that may have disappeared or changed after code edits
  - smells are critique/navigation only; they are not proof, restrictions, permissions, or hard guidelines
  - promote repeated supported smells manually through `PRP-*` proposals and `GLD-*` guidelines only when support is sufficient

- `code-entry create`
  - creates manual CIX entries for directories, globs, symbols, or logical areas
  - use this for areas like "SmartPick prompt UI" or "E2E tests folder" that AST cannot infer

- `annotate-code`
  - adds `agent-note`, `review-note`, `TODO`, `rationale`, `risk`, or `smell` annotations to a CIX entry
  - annotations store observed `sha256`, `mtime`, and target state so agents can see whether a note may be stale
  - annotations are navigation, not proof
  - `smell` annotations require one or more `--category` values and may include multiple categories
  - supported categories are `mixed-responsibility`, `hidden-side-effect`, `implicit-contract`, `brittle-selector`, `overbroad-abstraction`, `leaky-compatibility`, `test-coupled-implementation`, `unverified-runtime-assumption`, `stateful-helper`, and `poor-error-boundary`
  - custom smell categories must use `custom:<kebab-name>`
  - `--severity critical` requires at least one `--claim CLM-*` support ref
  - use `--suggestion` for local refactor ideas; use `PRP-*` for expanded constructive critique/options

- `link-code`
  - links a CIX entry to canonical records for navigation and impact
  - supports guideline, claim, model, flow, source, plan, debt, and open-question refs
  - links store observed file snapshot metadata

- `assign-code-index --record <ID> --entry CIX-*`
  - adds `code_index_refs` to allowed records: guideline, proposal, plan, debt, open_question, model, flow, action, and task
  - rejected for claim, source, permission, restriction, and project records
  - does not make CIX a proof source

- `show-claim-lifecycle --claim CLM-*`
  - shows lifecycle state, attention state, resolution anchors, reactivation conditions, and history
  - is read-only and safe for audits

- `resolve-claim --claim CLM-* --note "..."`
  - marks a true-but-no-longer-current claim as `lifecycle.state=resolved` and `attention=fallback-only`
  - accepts optional `--resolved-by-claim CLM-*`, `--resolved-by-action ACT-*`, and `--reactivate-when "..."`
  - keeps truth `status` unchanged; use this for facts that were correct historically but should no longer dominate current lookup
  - fails if an active hypothesis index entry, current action, or working/stable model/flow would still treat the fallback claim as current support

- `archive-claim --claim CLM-* --note "..."`
  - marks a claim as `lifecycle.state=archived` and `attention=explicit-only`
  - removes it from normal task retrieval while preserving it for explicit refs, audits, and rollback analysis

- `restore-claim --claim CLM-* --note "..."`
  - returns a fallback/archived claim to `lifecycle.state=active` and `attention=normal`
  - use this when a resolved issue starts reproducing again or an archived claim becomes relevant
  - clears current lifecycle resolution fields while preserving lifecycle history

- `review/attention.md`
  - generated by hydration, review, reindex, and record-writing commands
  - shows current project/task, recent claims/models/flows, active restrictions, guidelines, proposals, permissions, hypotheses, plans/debt, open questions, and fallback historical claims
  - documents lookup priority from active `corroborated` to active `tentative`, then fallback historical claims
  - is navigation only; canonical support must still come from `records/` and referenced sources

- `review/resolved.md`
  - generated by hydration, review, reindex, and record-writing commands
  - lists fallback historical claims and archived explicit-only claims
  - is navigation only; canonical support must still come from `records/` and referenced sources

- `build-reasoning-case --task "..." [--claim CLM-*] [--model MODEL-*] [--flow FLOW-*]`
  - expands selected models/flows/claims into an audit-friendly `Claim -> Source quote` chain
  - flags tentative claims as hypothesis-stage support
  - flags lifecycle fallback/archived claims as background/audit context that must be restored or re-supported before decisive use
  - warns when selected models/flows are inactive, stale, contested, or superseded
  - is read-only and intended before non-trivial conclusions or actions

- `augment-chain --file evidence-chain.json [--format text|json]`
  - read-only enrichment for compact agent-supplied evidence chains
  - fills missing node quotes from canonical records when a matching statement/rule/summary exists
  - attaches public record metadata and source quotes so the agent does not have to rediscover them manually
  - runs the same mechanical validation as `validate-evidence-chain`
  - does not weaken proof rules; unresolved blockers still return non-zero

- `validate-evidence-chain --file evidence-chain.json`
  - validates an agent-supplied evidence chain instead of inventing one
  - expects nodes shaped as `role + ref + quote`, e.g. `fact CLM-*: "..." -> observation CLM-*: "..."`
  - treats `fact` as a role for `CLM-* status=supported|corroborated`, not as a separate record type
  - prints a `User-Facing Chain` that includes the entity id for every node
  - checks that refs exist, roles match record types/statuses, and quotes appear in the referenced record or its source quotes
  - supports `requested_permission` nodes for user-facing permission requests before a `PRM-*` exists
  - supports `exploration_context` nodes for local hypotheses that motivate safe probes but are not proof
  - supports `restriction`, `guideline`, `proposal`, and `project` nodes as context/control/guidance/critique, not proof
  - blocks permission/restriction/guideline/proposal-as-truth edges, project/task/exploration-as-proof edges, and chains without at least one fact node
  - `validate-planning-chain` remains as a compatibility alias

Reasoning checkpoint disclosure:

- Before long analysis, multi-tool investigation, plan-changing tool batches, permission requests, or substantial edits, the agent should show a compact `Reasoning Checkpoint`.
- A checkpoint is not hidden chain-of-thought and is not proof. It is a public status panel with goal, anchors, current inference, next safe action, and concern.
- If relevant records already exist, the checkpoint should cite `CLM-*`, `GLD-*`, `MODEL-*`, `FLOW-*`, or `PRP-*` ids.
- A checkpoint does not replace a mechanically valid `Evidence Chain`.

Recommended format:

```text
Reasoning Checkpoint:
- Goal: ...
- Anchors: CLM-... / GLD-... / none yet
- Current inference: ...
- Next safe action: ...
- Concern: ...
```

Guideline disclosure for code edits:

- Before planning substantial code edits, the agent should list applicable `GLD-*` ids with short quotes.
- After substantial code edits, the agent should summarize the `GLD-*` ids and quotes it actually used.
- If no guideline applies, the agent should say `Guidelines: none found`.
- `required` guideline conflicts should stop the edit or trigger a user question; `preferred` guideline conflicts require a scoped explanation.

- `record-workspace --workspace-key ... --title ... --root-ref ... --note ...`
  - creates a canonical `WSP-*` workspace memory-boundary record
  - a workspace groups one or more project records under one TEP context root
  - workspace records do not prove claims

- `set-current-workspace --workspace WSP-*`
  - stores the default active workspace boundary in `<context>/settings.json.current_workspace_ref`
  - causes new canonical records to inherit `workspace_refs` automatically
  - hydration and session-start hooks show the current workspace explicitly

- `init-anchor --directory . --workspace WSP-* [--project PRJ-*]`
  - writes a local `.tep` anchor that selects context root plus workdir-specific workspace/project focus
  - `.tep` is local configuration, not canonical memory and not proof
  - local `allowed_freedom` can only keep or lower effective strictness

- `show-anchor` / `validate-anchor`
  - inspect and validate the nearest local `.tep` anchor

- `set-current-workspace --clear`
  - clears the current workspace boundary

- `show-workspace [--all]`
  - prints the current workspace boundary, or all workspace records with `--all`

- `assign-workspace --workspace WSP-* --record <ID>`
  - attaches an existing record to a workspace via `workspace_refs`

- `assign-workspace --workspace WSP-* --records-file <path>`
  - attaches a newline-separated set of existing record ids to a workspace for explicit migration

- `assign-workspace --workspace WSP-* --all-unassigned`
  - migrates legacy records that have no `workspace_refs` without guessing their `project_refs`

- `record-project --project-key ... --title ... --root-ref ... --note ...`
  - creates a canonical `PRJ-*` project boundary record
  - project records separate mixed domains inside one workspace
  - project records do not prove claims

- `set-current-project --project PRJ-*`
  - stores the default active project boundary in `<context>/settings.json.current_project_ref`
  - causes `brief-context` and `build-reasoning-case` to filter relevance sections by `project_refs`

- `set-current-project --clear`
  - clears the current project boundary

- `show-project [--all]`
  - prints the current project boundary, or all project records with `--all`

- `assign-project --project PRJ-* --record <ID>`
  - attaches an existing record to a project via `project_refs`
  - supports gradual migration of mixed legacy contexts

- `assign-task --task TASK-* --record <ID>`
  - attaches an existing record to a task via `task_refs`
  - marks claims, permissions, plans, or other records as local to one execution focus

- `record-restriction --scope ... --title ... --applies-to global|project|task --rule ... --note ...`
  - creates a canonical `RST-*` restriction record
  - restrictions can be global, project-scoped, or task-scoped
  - `--applies-to project` defaults to the current project when no `--project` is supplied
  - `--applies-to task` defaults to the current task when no `--task` is supplied
  - restrictions are control records; they do not prove truth
  - `--severity hard|warning` lets agents distinguish blocking constraints from warnings

- `show-restrictions [--all]`
  - prints active restrictions for the current project/task, or all restrictions with `--all`

- `start-task --scope ... --title ... --note ... [--project PRJ-*]`
  - creates a canonical `TASK-*` record
  - stores the active execution focus in `.codex_context/settings.json.current_task_ref`
  - attaches the current project automatically when `settings.json.current_project_ref` is set
  - refuses to replace an already active current task; use `complete-task` or `stop-task` first
  - refreshes generated views and marks hydration stale

- `show-task [--all]`
  - prints the current task focus, or all task records with `--all`

- `complete-task [--task TASK-*] [--note ...]`
  - marks the selected or current task `completed`
  - clears `current_task_ref` when it points at that task

- `stop-task [--task TASK-*] [--note ...]`
  - marks the selected or current task `stopped`
  - clears `current_task_ref` when it points at that task

- `record-source`
  - creates a canonical `SRC-*` record
  - requires explicit `source_kind`, `critique_status`, `origin.kind`, `origin.ref`, and `note`
  - requires either `quote` or `artifact_refs`
  - attaches the current project automatically when `settings.json.current_project_ref` is set
  - accepts `--project PRJ-*` and `--task TASK-*` for explicit local scoping
  - defaults `captured_at` to now and auto-generates `independence_group` if omitted
  - refuses to write into an already invalid `.codex_context`
  - refreshes `index.md`, `backlog.md`, and generated review files

- `record-input`
  - creates a canonical `INP-*` provenance record for prompts, referenced files, attachments, or tool payloads
  - requires explicit `input_kind`, `origin.kind`, `origin.ref`, `scope`, and `note`
  - requires prompt `text` or `artifact_refs`
  - accepts `--text-stdin` for hook capture without passing large prompts as command arguments
  - can link to a session with `--session-ref` and to later classified records with `--derived-record`
  - attaches the current project/current task automatically unless explicit refs are supplied
  - refreshes generated views and marks hydration stale unless a hook rehydrates immediately after capture

- `record-claim`
  - creates a canonical `CLM-*` record
  - requires explicit `plane`, `statement`, at least one `source_ref`, and `note`
  - defaults `status` to `tentative`
  - accepts optional `claim_kind`, `confidence`, `red_flags`, and structured `comparison`
  - attaches the current project automatically when `settings.json.current_project_ref` is set
  - accepts `--project PRJ-*` and `--task TASK-*` for explicit local scoping
  - refuses to write into an already invalid `.codex_context`
  - refreshes `index.md`, `backlog.md`, and generated review files

- `record-plan`
  - creates a canonical `PLN-*` record
  - requires explicit `priority`, `justified_by`, `steps`, `success_criteria`, and `note`
  - attaches the current project automatically and accepts explicit `--project` / `--task`
  - refuses to write into an already invalid `.codex_context`
  - refreshes `index.md`, `backlog.md`, and generated review files

- `record-debt`
  - creates a canonical `DEBT-*` record
  - requires explicit `priority`, `evidence_refs`, and `note`
  - can link scheduled debt to `PLN-*` via `--plan-ref`
  - attaches the current project automatically and accepts explicit `--project` / `--task`
  - refuses to write into an already invalid `.codex_context`
  - refreshes `index.md`, `backlog.md`, and generated review files

- `change-strictness <proof-only|evidence-authorized|implementation-choice>`
  - validates the current context against the requested strictness before writing `.codex_context/settings.json`
  - updates the generated `index.md` and `backlog.md`
  - stores the current runtime `allowed_freedom` for the context
  - in `proof-only`, new mutating durable actions are rejected
  - `evidence-authorized` allows bounded safe/guarded mutation with active task, fresh conflict-free hydration, and valid `--evidence-chain`
  - escalation to any higher strictness requires a pending `request-strictness-change` request and a user `SRC-*` quote containing `TEP-APPROVE REQ-*`
  - escalation to `implementation-choice` additionally requires `--permission PRM-*` with an explicit user-backed `allowed_freedom`/strictness grant
  - returning to `proof-only` or otherwise lowering strictness does not require approval
  - approval requests are one-shot; after successful escalation the request is marked `used`

- `request-strictness-change <evidence-authorized|implementation-choice> --reason "..."`
  - creates a pending strictness approval request in `.codex_context/strictness_requests.jsonl`
  - prints the exact user reply the agent must ask for: `TEP-APPROVE REQ-*`
  - does not change `allowed_freedom` by itself
  - for `implementation-choice`, still requires `--permission PRM-*`

- `record-permission`
  - creates a canonical `PRM-*` record
  - requires explicit `scope`, at least one `grant`, and `note`
  - accepts `--applies-to global|project|task`
  - `--applies-to project` defaults to the current project when no `--project` is supplied
  - `--applies-to task` defaults to the current task when no `--task` is supplied
  - defaults `granted_by` to `user` and `granted_at` to now
  - refreshes `index.md`, `backlog.md`, and generated review files

- `record-action`
  - creates a canonical `ACT-*` record
  - requires explicit `kind`, `scope`, at least one `justified_by`, and `note`
  - requires explicit `safety_class`: `safe | guarded | unsafe`
  - in `evidence-authorized`, mutating actions require `--evidence-chain`
  - defaults `planned_at` or `executed_at` based on action status
  - attaches the current project automatically and accepts explicit `--project` / `--task`
  - is validated against the current strictness
  - refreshes `index.md`, `backlog.md`, and generated review files

- `record-model`
  - creates a canonical `MODEL-*` record
  - represents an evidence-backed picture for one `scope + aspect`
  - remains strictly derivative from `claim_refs`
  - attaches the current project automatically and accepts explicit `--project` / `--task`

- `record-flow`
  - creates a canonical `FLOW-*` record
  - represents one integrated flow with `preconditions`, `oracle`, and step-level status
  - binds the flow to `model_refs`
  - attaches the current project automatically and accepts explicit `--project` / `--task`

- `record-open-question`
  - creates a canonical `OPEN-*` record
  - stores deferred uncertainty without interrupting the user
  - attaches the current project automatically and accepts explicit `--project` / `--task`

- `record-artifact --path <file>`
  - copies a payload file into `.codex_context/artifacts/`
  - preserves the payload as the canonical artifact, without creating a separate record type
  - prints a root-relative artifact ref such as `artifacts/ART-YYYYMMDD-xxxxxxxx__name.txt`
  - can be used before `record-source` when you need to ingest logs, snapshots, or outputs first

- `impact-graph --claim CLM-*`
  - shows direct and transitive dependencies of a claim across canonical records
  - includes `used_by` and `rollback_refs` hints from `hypotheses.jsonl`

- `rollback-report --claim CLM-*`
  - prints the direct and transitive review surface for an invalidated claim
  - highlights `model/flow` records that would be stale candidates
  - does not mutate canonical records

- `mark-stale-from-claim --claim CLM-*`
  - marks dependent non-superseded `MODEL-*` and `FLOW-*` records as `stale`
  - does not touch actions, plans, debt, or open questions
  - is intentionally conservative and explicit

- `promote-model-to-domain --model MODEL-*`
  - clones a stable investigation model into a new `domain` model
  - marks the source investigation model as `superseded`
  - records the trail via `promoted_from_refs`

- `promote-flow-to-domain --flow FLOW-*`
  - clones a stable investigation flow into a new `domain` flow
  - marks the source investigation flow as `superseded`
  - records the trail via `promoted_from_refs`

- `hypothesis add`
  - adds an active hypothesis index entry for a tentative `CLM-*`
  - refuses non-tentative claims

- `hypothesis list`
  - lists hypothesis index entries, optionally filtered by status

- `hypothesis close`
  - changes an active hypothesis entry to `confirmed`, `falsified`, or `abandoned`

- `hypothesis reopen`
  - reopens a previously closed hypothesis entry
  - requires the referenced claim to remain `tentative`

- `hypothesis remove`
  - removes a hypothesis entry entirely

- `hypothesis sync`
  - removes index entries that no longer match tentative claims
  - `--drop-closed` also drops non-active entries

## Comparable Claim Shape

Not every claim must be fully structured.

Use a `comparison` object only when the claim should participate in automatic contradiction scans. The current minimal comparable shape is:

- `comparison.key`
- `comparison.subject`
- `comparison.aspect`
- `comparison.comparator`: `exact` or `boolean`
- `comparison.value`
- `comparison.polarity`: `affirmed` or `denied`
- optional `comparison.context_scope`

## Plans And Debt

The plugin now supports two additional canonical record types:

- `plan`: evidence-backed intended work with `priority`, `steps`, and `success_criteria`
- `debt`: evidence-backed known liability with `priority` and `evidence_refs`

Current prioritization behavior:

- active plans are `proposed`, `active`, `blocked`
- active debt is `open`, `accepted`, `scheduled`
- terminal items are preserved as canonical records but excluded from generated `backlog.md`
- backlog ordering prefers higher priority before lower priority

## Captured Inputs

`input` stores raw prompt-level provenance as `INP-*`.

- canonical input records live in `records/input/INP-*.json`
- input records are not proof and cannot support truth directly
- use `derived_record_refs` to record canonical records produced from the input
- use `input_refs` on other records when the input itself must remain traceable
- fresh orphan `INP-*` records are retained until `settings.cleanup.orphan_input_stale_after_days`
- stale orphan `INP-*` records should be archived before deletion is considered

## Tasks

`task` is an explicit runtime focus layer.

- canonical task records live in `records/task/TASK-*.json`
- the current task pointer lives in `settings.json.current_task_ref`
- task records have `task_type`, such as `investigation`, `implementation`, `review`, `debugging`, `refactor`, `migration`, `test-writing`, `release`, or `general`
- task records may be `active`, `paused`, `completed`, or `stopped`
- hydration prints the current task when the pointer is set
- the session-start hook injects the current task into agent context when present
- `TASK-*` can be cited in evidence chains as `role=task`, but cannot support truth claims
- use `task-drift-check` before substantial work that may not match the current task
- use `pause-task`, `resume-task`, or `switch-task` instead of silently continuing in the wrong task context
- use `review-precedents` before repeating a substantial task type to inspect similar past tasks and linked plans/debt/actions/open questions

## Projects And Restrictions

`workspace` is an explicit memory boundary.

- canonical workspace records live in `records/workspace/WSP-*.json`
- records should link to workspaces through `workspace_refs`
- `settings.json.current_workspace_ref` selects the default workspace boundary
- local `.tep.workspace_ref` may select a workdir-specific workspace boundary over the same global context
- hydration and session-start hook output must show the current workspace when one is set
- new canonical records automatically inherit the current workspace
- legacy records can be migrated safely with `assign-workspace --all-unassigned` or `assign-workspace --records-file`; this does not guess project ownership

`project` is an optional narrower context boundary inside a workspace.

- canonical project records live in `records/project/PRJ-*.json`
- records can link to projects through `project_refs`
- `settings.json.current_project_ref` selects the default project boundary
- local `.tep.project_ref` may select a workdir-specific project inside the anchored workspace
- current project filtering intentionally excludes unassigned records from relevance sections
- new source/claim/model/flow/plan/debt/action/open-question records automatically inherit the current project
- unassigned legacy records remain valid and can be migrated gradually with `assign-project`

`restriction` is the negative counterpart to permission.

- canonical restriction records live in `records/restriction/RST-*.json`
- restrictions may apply to `global`, `project`, or `task`
- restrictions are surfaced during hydration, preflight, and context briefs
- restrictions constrain what the agent may do or assume, but do not prove claims

`permission` records may also be global, project-scoped, or task-scoped through `applies_to`, `project_refs`, and `task_refs`.
Task-scoped permissions and claims are hidden from other active tasks by relevance filtering.

## Models, Flows, and Questions

Additional `v1` layers:

- `model`
  - derivative picture over claims for one `scope + aspect`
- `flow`
  - integrated process understanding with `preconditions` and `oracle`
- `open_question`
  - lightweight deferred uncertainty for later user review
- `hypotheses.jsonl`
  - active index of tentative `CLM-*` hypotheses and their dependency hints
  - supports `mode=durable|exploration`
  - supports `based_on_hypotheses` only for `mode=exploration`

Promotion and rollback skeleton:

- promotion from `investigation` to `domain` creates a new canonical record instead of mutating the old one in place
- the source investigation record is marked `superseded`
- the promoted record keeps a `promoted_from_refs` trail
- rollback remains explicit: `rollback-report` shows impact first, `mark-stale-from-claim` performs only conservative stale marking

Hypothesis lifecycle:

- `record-claim --status tentative` creates the tentative claim itself
- `hypothesis add` places that claim in the active hypothesis index
- `hypothesis add --mode exploration --based-on-hypothesis CLM-*` is allowed for local exploration, but those entries are not valid as proof in `validate-evidence-chain`
- stronger evidence should promote or reject the underlying `CLM-*`
- once the claim is no longer tentative, `hypothesis sync` removes the stale index entry

## Auxiliary Taxonomy

Borrowed from the fact-check workflow, but kept compatible with the protocol:

- `claim_kind` classifies the kind of assertion
- `confidence` calibrates current assessment strength
- `red_flags` stores manipulation/provenance concerns

These fields are additive. They do not replace:

- `source_kind`
- `critique_status`
- `claim.status`
- `allowed_freedom`

Current claim taxonomy:

- `factual`
- `implied`
- `statistical`
- `opinion`
- `prediction`
- `unfalsifiable`

Compatibility rule:

- `opinion`, `prediction`, and `unfalsifiable` claims must remain `tentative` until re-expressed as checkable factual claims

## Strictness Semantics

Current enforcement is intentionally conservative:

- `proof-only` rejects new mutating durable actions such as `edit`, `write`, `create`, `delete`, `rename`, `move`, `refactor`, `patch`, and `update`
- `evidence-authorized` allows bounded safe/guarded mutating actions without a new manual permission only when preflight is fresh/conflict-free, a current task is active, no hard restriction blocks the scope, and `record-action` validates a supplied evidence chain
- `implementation-choice` allows those actions, but only on top of the existing claim-justification rules
- Returning to `proof-only` must not invalidate historical `ACT-*` records that were recorded while higher freedom was active
- Agents must not self-escalate to any higher strictness. Escalation requires a pending `REQ-*` strictness request plus a user `SRC-*` quote containing `TEP-APPROVE REQ-*`
- Escalation to `implementation-choice` additionally requires an explicit `PRM-*` grant naming `allowed_freedom` or strictness

This does not yet prove that an implementation choice is semantically safe. It only makes the strictness switch operative instead of metadata-only.

## Runtime Gate

The plugin now includes a hook-ready runtime gate in:

- `scripts/runtime_gate.py`
- `hooks/hydrate_context.sh`
- `hooks/preflight_task.sh`

Available runtime commands:

- `hydrate-context`
  - validates the context
  - refreshes generated reports/views
  - writes `runtime/hydration.json`
  - marks the store as `hydrated`, `hydrated-with-conflicts`, or `blocked`

- `show-hydration`
  - shows the current hydration state and whether it still matches the current fingerprint

- `preflight-task --mode reasoning|planning|edit|action [--kind ...]`
  - requires current hydration before project-claim work
  - blocks planning while hydration conflicts remain unresolved
  - blocks mutating actions in `proof-only`
  - in `evidence-authorized`, allows mutating action preflight only with active task and no active hard restrictions; `record-action` still requires `--evidence-chain`

- `invalidate-hydration --reason "..."`
  - marks the current hydration state as stale after an external mutation
  - intended for hook adapters and other runtime integrations

Current lifecycle:

1. run `hydrate-context`
2. run `preflight-task` before project-claim reasoning/planning/editing
3. after any `record-*` write or strictness change, hydration becomes `stale`
4. hydrate again before the next project-claim task

Official Codex hook integration now exists in this repo via:

- `.codex/hooks.json`
- `.codex/hooks/session_start_hydrate.py`
- `.codex/hooks/user_prompt_hydration_notice.py`
- `.codex/hooks/pre_tool_use_guard.py`
- `.codex/hooks/post_tool_use_review.py`

Current behavior is intentionally conservative:

- `SessionStart` hydrates the resolved TEP context root, preferring `~/.tep_context`, and injects the active context summary plus protocol obligations
- `UserPromptSubmit` injects a warning when hydration is stale or missing; in `remind` mode it also injects a compact evidence-chain/guideline-disclosure reminder while hydration is fresh
- `PreToolUse` inspects `Bash` commands for obvious mutating intent and denies them when runtime preflight fails
- `PostToolUse` marks hydration stale after obvious mutating `Bash` commands complete and injects a re-hydration warning
- no automatic `Stop` continuation loop is configured

Write safety:

- Mutating plugin commands take an inter-process lock at `<context>/runtime/write.lock`.
- Generated markdown, JSON records, JSONL indexes, settings, and hydration state are written through same-directory temporary files followed by atomic replace.
- Read-only commands do not take the write lock.
- The lock protects plugin-mediated writes only; manual edits outside plugin commands can still race with agents.

Chat-native protocol panels:

- Plugins do not inject arbitrary custom chat UI, so agents render protocol state as stable markdown panels.
- Before substantial planning, permission requests, persistence, or edits, render an `Evidence Chain` panel with `id + quote` nodes.
- Before long analysis or tool-heavy investigation, render a compact `Reasoning Checkpoint` panel.
- Before substantial code edits, render a `Guidelines` panel with applicable `GLD-* + quote` entries.
- After substantial code edits, render `Guidelines used:` with the used `GLD-* + quote` entries.
- These panels are user-visible proof surfaces and should be mechanically checkable with `validate-evidence-chain` where possible.

Important limit:

- official Codex hooks still do not provide complete enforcement across non-Bash tools, and `PreToolUse` currently only sees `Bash`, so this remains a strong guardrail rather than a total boundary

Hook modes are configured in `.codex_context/settings.json` under:

```json
{
  "allowed_freedom": "proof-only",
  "hooks": {
    "enabled": true,
    "session_start_hydrate": "on",
    "user_prompt_notice": "remind",
    "pre_tool_use_guard": "enforce",
    "post_tool_use_review": "invalidate"
  }
}
```

Debugging-oriented values:

- `session_start_hydrate`: `off | on`
- `user_prompt_notice`: `off | on | remind`

Mode meanings:

- `on`: warn only when hydration is stale or missing
- `remind`: warn when stale and remind the agent on every prompt to show public Evidence Chain and `GLD-* + quote` guideline disclosure before substantial code edits
- `remind` also reminds the agent to show public `Reasoning Checkpoint` panels before long analysis or tool-heavy work
- `pre_tool_use_guard`: `off | warn | enforce`
- `post_tool_use_review`: `off | notify | invalidate`
