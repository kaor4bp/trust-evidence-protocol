# Plugin Commands Workflow

Use plugin commands when available instead of manually editing canonical records.
Write raw payload files directly only under `<context>/artifacts/`; write canonical records through `context_cli.py` commands.

When operating in normal live mode, omit `--context` and let the runtime resolve
`TEP_CONTEXT_ROOT`, nearest `.tep.context_root`, `~/.tep_context`, or legacy `.codex_context`.
The examples below keep explicit `--context .codex_context` for fixture,
migration, and debugging clarity; do not treat that as a requirement to prefer
repo-local memory over the unified global context.

## MCP Bounded Lookup

When the plugin MCP server is available, prefer MCP for lookup-heavy work and keep CLI for mutation:

- `brief_context`: equivalent to compact `brief-context --task "..."`; pass `detail=full` only when the expanded brief is needed
- `next_step`: equivalent to `next-step --intent ...`; use it as the first route branch when unsure what to do next, follow its compact action graph before re-reading the protocol, and request `format=json` when a tool needs structured `route_graph` data
- `lookup`: equivalent to `lookup --query "..." --reason ...`; reason is mandatory, lookup may auto-create a lightweight `WCTX-*`, and output is navigation only
- `lookup` returns `next_allowed_commands`, `route_graph`, `evidence_profile`, and `output_contract`; follow these fields before broadening the search
- `search_records`: equivalent to `search-records --query "..."`; drill-down after `lookup` in normal work
- `claim_graph`: equivalent to `claim-graph --query "..."`; drill-down after `lookup`, returns current matching `CLM-*` anchors plus compact linked records/edges without reading raw claim JSON
- `record_detail`: equivalent to `record-detail --record ID`; use before citing proof
- `linked_records`: equivalent to `linked-records --record ID`; use for graph expansion after a selected candidate
- `guidelines_for`: equivalent to `guidelines-for --task "..."`
- `code_search`: equivalent to `code-search`; optional semantic `query` is proxied through TEP-managed backends such as CocoIndex; `scope=workspace` is an explicit broader glance
- `code_feedback`: equivalent to read-only `code-feedback`; use CLI apply mode for reviewed CIX-to-record links
- `code_smell_report`: equivalent to `code-smell-report`
- `code_info`: equivalent to `code-info`
- `cleanup_candidates`: equivalent to `cleanup-candidates`
- `topic_search`: equivalent to `topic-search`
- `topic_info`: equivalent to `topic-info`
- `topic_conflict_candidates`: equivalent to `topic-conflict-candidates`
- `attention_map`: equivalent to `attention-map`; defaults to current `.tep` focus
- `attention_diagram`: equivalent to `attention-diagram`; renders a Mermaid cluster/link map, defaulting to compact labels
- `attention_diagram_compare`: equivalent to `attention-diagram-compare`; compares compact/full diagram metrics
- `curiosity_map`: equivalent to `curiosity-map`; renders a visual-thinking map with heat, cold zones, bridges, candidate probes, and volume control
- `telemetry_report`: equivalent to `telemetry-report`; reports MCP/CLI/hook lookup telemetry and raw claim read counts
- `curiosity_probes`: equivalent to `curiosity-probes`; defaults to current `.tep` focus
- `probe_inspect`: equivalent to `probe-inspect`; expands one generated probe into canonical inspection context
- `probe_chain_draft`: equivalent to `probe-chain-draft`; generates a non-proof evidence-chain draft from one probe
- `probe_route`: equivalent to `probe-route`; generates ordered next inspection commands and expansion hints for one probe
- `probe_pack`: equivalent to `probe-pack`; compactly bundles top probes with inspection summaries and draft validation
- `probe_pack_compare`: equivalent to `probe-pack-compare`; compares compact/full metrics before requesting expanded context
- `working_contexts`: equivalent to `working-context show`
- `working_context_drift`: equivalent to `working-context check-drift`
- `workspace_admission`: equivalent to `workspace-admission check`
- `logic_search`: equivalent to `logic-search`
- `logic_check`: equivalent to `logic-check`
- `logic_conflict_candidates`: equivalent to `logic-conflict-candidates`

MCP lookup is bounded and does not replace canonical records. Most MCP tools are read-only; `lookup` may auto-create a lightweight `WCTX-*` operational context so agent focus stays explicit.
When a tool supports `cwd`, pass the active workdir so MCP resolves the nearest `.tep` anchor and uses the same workspace/project focus as hooks and CLI.
Before citing a fact or rule, use `claim_graph`, `record_detail`, `linked_records`, or the equivalent CLI command to obtain the record id and quote.
Do not read raw `records/claim/*.json` directly during normal reasoning; hooks block normal Bash reads. Use compact MCP/CLI projections first, and use `TEP_RAW_RECORD_MODE=debug|migration|forensics|plugin-dev` only for explicit escape-hatch work.
Use CLI commands for all record creation, updates, strictness changes, task changes, code-index mutation, lifecycle changes, and review regeneration.

## Runtime Gate

```bash
python3 plugins/trust-evidence-protocol/scripts/runtime_gate.py --context .codex_context hydrate-context
python3 plugins/trust-evidence-protocol/scripts/runtime_gate.py --context .codex_context show-hydration
python3 plugins/trust-evidence-protocol/scripts/runtime_gate.py --context .codex_context confirm-task --task TASK-* --note "user confirmed focus"
python3 plugins/trust-evidence-protocol/scripts/runtime_gate.py --context .codex_context preflight-task --mode reasoning
python3 plugins/trust-evidence-protocol/scripts/runtime_gate.py --context .codex_context preflight-task --mode planning
python3 plugins/trust-evidence-protocol/scripts/runtime_gate.py --context .codex_context preflight-task --mode edit
python3 plugins/trust-evidence-protocol/scripts/runtime_gate.py --context .codex_context preflight-task --mode action --kind edit
python3 plugins/trust-evidence-protocol/scripts/runtime_gate.py --context .codex_context invalidate-hydration --reason "..."
```

## Review And Retrieval

```bash
python3 plugins/trust-evidence-protocol/scripts/context_cli.py --context .codex_context help modes
python3 plugins/trust-evidence-protocol/scripts/context_cli.py --context .codex_context review-context
python3 plugins/trust-evidence-protocol/scripts/context_cli.py --context .codex_context reindex-context
python3 plugins/trust-evidence-protocol/scripts/context_cli.py --context .codex_context scan-conflicts
python3 plugins/trust-evidence-protocol/scripts/context_cli.py --context .codex_context brief-context --task "..."
python3 plugins/trust-evidence-protocol/scripts/context_cli.py --context .codex_context brief-context --task "..." --detail full
python3 plugins/trust-evidence-protocol/scripts/context_cli.py --context .codex_context lookup --query "..." --reason orientation --kind auto --format json
python3 plugins/trust-evidence-protocol/scripts/context_cli.py --context .codex_context next-step --intent plan --task "..."
python3 plugins/trust-evidence-protocol/scripts/context_cli.py --context .codex_context next-step --intent plan --task "..." --format json
python3 plugins/trust-evidence-protocol/scripts/context_cli.py --context .codex_context task-outcome-check --task TASK-* --outcome done --format json
python3 plugins/trust-evidence-protocol/scripts/context_cli.py --context .codex_context search-records --query "..."
python3 plugins/trust-evidence-protocol/scripts/context_cli.py --context .codex_context claim-graph --query "..." --format json
python3 plugins/trust-evidence-protocol/scripts/context_cli.py --context .codex_context record-detail --record CLM-*
python3 plugins/trust-evidence-protocol/scripts/context_cli.py --context .codex_context record-neighborhood --record CLM-* --depth 2
python3 plugins/trust-evidence-protocol/scripts/context_cli.py --context .codex_context linked-records --record CLM-* --direction both --depth 1
python3 plugins/trust-evidence-protocol/scripts/context_cli.py --context .codex_context guidelines-for --task "..." --domain code
python3 plugins/trust-evidence-protocol/scripts/context_cli.py --context .codex_context cleanup-candidates
python3 plugins/trust-evidence-protocol/scripts/context_cli.py --context .codex_context cleanup-archives
python3 plugins/trust-evidence-protocol/scripts/context_cli.py --context .codex_context cleanup-archives --archive ARC-*
python3 plugins/trust-evidence-protocol/scripts/context_cli.py --context .codex_context cleanup-archive --dry-run
python3 plugins/trust-evidence-protocol/scripts/context_cli.py --context .codex_context cleanup-archive --apply
python3 plugins/trust-evidence-protocol/scripts/context_cli.py --context .codex_context cleanup-restore --archive ARC-* --dry-run
python3 plugins/trust-evidence-protocol/scripts/context_cli.py --context .codex_context cleanup-restore --archive ARC-* --apply
python3 plugins/trust-evidence-protocol/scripts/context_cli.py --context .codex_context topic-search --query "..."
python3 plugins/trust-evidence-protocol/scripts/context_cli.py --context .codex_context topic-info --record CLM-*
python3 plugins/trust-evidence-protocol/scripts/context_cli.py --context .codex_context topic-conflict-candidates
python3 plugins/trust-evidence-protocol/scripts/context_cli.py --context .codex_context tap-record --record CLM-* --kind cited --intent support
python3 plugins/trust-evidence-protocol/scripts/context_cli.py --context .codex_context telemetry-report --format json
python3 plugins/trust-evidence-protocol/scripts/context_cli.py --context .codex_context backend-status --format json
python3 plugins/trust-evidence-protocol/scripts/context_cli.py --context .codex_context backend-check --backend derivation.datalog --format json
python3 plugins/trust-evidence-protocol/scripts/context_cli.py --context .codex_context validate-facts --backend rdf_shacl --format json
python3 plugins/trust-evidence-protocol/scripts/context_cli.py --context .codex_context export-rdf --format turtle --output /tmp/tep.ttl
python3 plugins/trust-evidence-protocol/scripts/context_cli.py --context .codex_context attention-index build
python3 plugins/trust-evidence-protocol/scripts/context_cli.py --context .codex_context attention-map --scope current
python3 plugins/trust-evidence-protocol/scripts/context_cli.py --context .codex_context attention-diagram --scope current --limit 8 --detail compact
python3 plugins/trust-evidence-protocol/scripts/context_cli.py --context .codex_context attention-diagram-compare --scope current --limit 8
python3 plugins/trust-evidence-protocol/scripts/context_cli.py --context .codex_context curiosity-map --scope current --volume compact
python3 plugins/trust-evidence-protocol/scripts/context_cli.py --context .codex_context curiosity-probes --budget 5 --scope current
python3 plugins/trust-evidence-protocol/scripts/context_cli.py --context .codex_context probe-inspect --index 1 --scope current
python3 plugins/trust-evidence-protocol/scripts/context_cli.py --context .codex_context probe-chain-draft --index 1 --scope current --format json
python3 plugins/trust-evidence-protocol/scripts/context_cli.py --context .codex_context probe-route --index 1 --scope current
python3 plugins/trust-evidence-protocol/scripts/context_cli.py --context .codex_context probe-pack --budget 3 --scope current --detail compact
python3 plugins/trust-evidence-protocol/scripts/context_cli.py --context .codex_context probe-pack-compare --budget 3 --scope current
python3 plugins/trust-evidence-protocol/scripts/context_cli.py --context .codex_context logic-search --predicate PredicateName
python3 plugins/trust-evidence-protocol/scripts/context_cli.py --context .codex_context logic-check
python3 plugins/trust-evidence-protocol/scripts/context_cli.py --context .codex_context logic-conflict-candidates
python3 plugins/trust-evidence-protocol/scripts/context_cli.py --context .codex_context build-reasoning-case --task "..."
python3 plugins/trust-evidence-protocol/scripts/context_cli.py --context .codex_context augment-chain --file evidence-chain.json --format json
python3 plugins/trust-evidence-protocol/scripts/context_cli.py --context .codex_context validate-evidence-chain --file evidence-chain.json
python3 plugins/trust-evidence-protocol/scripts/context_cli.py --context .codex_context validate-decision --mode planning --chain evidence-chain.json
python3 plugins/trust-evidence-protocol/scripts/context_cli.py --context .codex_context validate-decision --mode edit --kind write --chain evidence-chain.json --emit-permit
python3 plugins/trust-evidence-protocol/scripts/context_cli.py --context .codex_context validate-decision --mode model --chain evidence-chain.json --emit-permit
python3 plugins/trust-evidence-protocol/scripts/context_cli.py --context .codex_context validate-decision --mode flow --chain evidence-chain.json --emit-permit
python3 plugins/trust-evidence-protocol/scripts/context_cli.py --context .codex_context validate-decision --mode final --chain evidence-chain.json --emit-permit
python3 plugins/trust-evidence-protocol/scripts/context_cli.py --context .codex_context working-context check-drift --task "..."
python3 plugins/trust-evidence-protocol/scripts/context_cli.py --context .codex_context workspace-admission check --repo /abs/repo --format json
```

Use `record-detail` after search when you need the exact record id, source quote, and direct links for a public reasoning checkpoint.
Use `record-neighborhood` before changing or dismissing records with unknown dependents.
Use `guidelines-for` before sizeable code/test edits and show the selected `GLD-*` ids plus short rule quotes.
Use `cleanup-candidates` only as a read-only triage report; do not treat it as permission to delete or archive records.
Use `cleanup-archives` to find restorable `ARC-*` bundles before asking the user to remember an archive id.
Use `cleanup-archive --dry-run` to inspect a planned archive manifest before any `zip` is written.
Use `cleanup-archive --apply` only to write a restorable archive; it must not delete originals.
Use `cleanup-restore --dry-run` before restore; `--apply` restores missing files only and must not overwrite conflicts.
Use `topic-search` only as a lexical prefilter, then inspect canonical records before citing facts.
Use `topic-conflict-candidates` only to find records worth structured comparison; it does not replace `scan-conflicts`.
Use `tap-record` to record non-proof activity when a record was retrieved, opened, cited, decisive, updated, challenged, or contradicted.
Use `telemetry-report` to inspect non-proof lookup telemetry, including whether agents are using MCP/CLI compact views or reading raw claim files; inspect anomaly `recommended_tools` and `next_action` before manually interpreting counters or expanding raw records.
Use `backend-status` and `backend-check` to inspect optional helper availability before relying on external fact-validation, code-intelligence, or derivation backends.
Backend status is diagnostic/navigation data only; it is not proof and does not replace canonical `SRC-*` or `CLM-*` support.
Use `validate-facts` to get backend-produced validation candidates over canonical records.
Validation candidates are not proof, do not support claims, and should be followed by `record-detail` / source inspection before changing records.
Use `export-rdf` only as a backend projection for validation/debugging; it is not canonical storage and must not be cited as proof.
Use `attention-map` and `curiosity-probes` to reduce token-heavy context exploration by asking the runtime for cold zones and bounded inspection questions.
Use `attention-diagram` when a Mermaid cluster/link map is a cheaper orientation aid than reading several textual reports.
Use `attention-diagram --detail full` only when compact node labels are not enough.
Use `attention-diagram-compare` to compare compact/full diagram payload cost mechanically before requesting full labels.
Use `curiosity-map --volume compact|normal|wide` when the agent needs one visual orientation view with heat, cold zones, bridges, curiosity prompts, and next inspection commands.
They default to `--scope current`, using the current workspace/project/task from settings or `.tep`; use `--scope all` only for deliberate cross-scope triage.
Probe `score` and `explanation` fields are mechanical ranking hints for what to inspect first, not evidence confidence.
Use `probe-inspect` to mechanically fetch record summaries, source quotes, direct link status, and suggested follow-up commands for a selected probe.
Use `probe-chain-draft` to mechanically assemble a draft evidence chain from a selected probe, then run normal validation/augmentation before presenting proof.
Use `probe-route` after choosing a probe when you want the runtime to compose next inspection commands plus diagram/full-pack expansion hints.
Use `record-link` after a probe has been inspected and a real source-backed relationship should be persisted; never use the probe score itself as support.
Use `probe-pack` when the agent needs a compact first pass over several top probes without manually composing multiple lookup commands.
Use `probe-pack --detail full` only when the compact pack shows a probe worth expanding with source quotes and full chain draft payload.
Use `probe-pack.metrics` to compare payload size and omitted fields mechanically; metrics are not proof.
Use `probe-pack-compare` to compare compact/full payload cost mechanically before requesting full detail; comparison output is not proof.
Do not use attention output as proof; follow up with `record-detail`, `linked-records`, sources, and normal claims.
Use `logic-search` / `logic-check` only as predicate prefilters over `CLM.logic`; they do not replace `CLM-*` and `SRC-*`.
Use `build-reasoning-case` before non-trivial actions or recommendations that span several facts, models, or flows.
Use `augment-chain` when you already have record refs but need the plugin to fill quotes, source refs, and validation output mechanically.
Use `validate-evidence-chain` before asking permission, recording a mutating `ACT-*`, or presenting a user-facing proof chain.
Use `validate-decision` after evidence-chain validation when deciding whether that chain is sufficient for planning, permission, edit, model, flow, proposal, final, curiosity, or debugging mode.
Use `validate-decision --emit-permit --mode edit --kind <action-kind>` before evidence-authorized mutating Bash; the PreToolUse hook requires a fresh time-limited chain permit for the current workspace/project/task/fingerprint.
Use the same permit before write-API commitments in `evidence-authorized`: mutating `record-action` checks a matching edit permit and chain hash; working/stable/contested `record-model` and `record-flow` check `mode=model` or `mode=flow` permits.
Use `validate-decision --emit-permit --mode final` before marking an autonomous task `done`; Stop/final guards reject `done` without a fresh final permit.
Use `telemetry-report --format json` to inspect permit pressure counters such as `permit_missing_count`, `permit_expired_count`, `permit_issued_count`, and `permit_used_count`.
Use `task-outcome-check` before declaring an autonomous task `done`, `blocked`, or `user-question`; the Stop hook uses the same check, so a marker without linked obligations can still be rejected.
If a chain uses `role=hypothesis`, first record it as `CLM-* status=tentative` and add it with `hypothesis add`; proof modes still must not rely on hypothesis nodes.
Do not stack proof hypotheses. A `role=hypothesis` node must be directly anchored by a fact or observation edge, and a hypothesis cannot be used as truth support for another hypothesis.
Use `working-context check-drift` when the user changes topic, task type, or repository; switch/fork/create `WCTX-*` before persisting task-local conclusions under the wrong focus.
Use `workspace-admission check` before attaching or analyzing an unknown checkout; if it requires a decision, ask whether to create a new workspace, add a project to the current workspace, or inspect read-only without persistence.

## Mechanical Evidence Writes

Use `record-support` as the default write API when new support should become a durable source-backed claim.
It creates the needed graph records mechanically: `FILE-*` for file metadata, `RUN-*` for command executions, `SRC-*` for source support, optional `CLM-*` for the thought, and `INP-*` back-links through `derived_record_refs`.
`record-evidence` is the compatibility form with the same graph-v2 behavior and more knobs.

```bash
python3 plugins/trust-evidence-protocol/scripts/context_cli.py --context .codex_context record-support \
  --scope smartpick.cache \
  --kind user-confirmation \
  --input INP-* \
  --quote "User confirmed SmartPick cache refresh happens only at startup." \
  --thought "SmartPick cache refresh happens only at application startup." \
  --claim-status supported \
  --note "classified captured user input into source-backed theory claim"

python3 plugins/trust-evidence-protocol/scripts/context_cli.py --context .codex_context record-support \
  --scope tests.cache \
  --kind command-output \
  --command "uv run pytest tests/unit/test_cache.py -q" \
  --quote "1 passed" \
  --thought "The focused cache unit test passed." \
  --claim-status supported \
  --note "focused test evidence"

python3 plugins/trust-evidence-protocol/scripts/context_cli.py --context .codex_context record-support \
  --scope code.cache \
  --kind file-line \
  --path src/cache.py \
  --line 42 \
  --quote "def refresh_cache():" \
  --thought "src/cache.py defines refresh_cache." \
  --claim-status supported \
  --note "file-line code evidence"
```

Use separate `record-source` and `record-claim` only for advanced comparison, logic predicates, source-only staging, migration, or debugging.

## Runtime Configuration

```bash
python3 plugins/trust-evidence-protocol/scripts/context_cli.py --context .codex_context configure-runtime --show
python3 plugins/trust-evidence-protocol/scripts/context_cli.py --context .codex_context configure-runtime --backend-preset minimal
python3 plugins/trust-evidence-protocol/scripts/context_cli.py --context .codex_context configure-runtime --backend-preset recommended
python3 plugins/trust-evidence-protocol/scripts/context_cli.py --context .codex_context configure-runtime --hook-verbosity quiet --hook-run-capture mutating --context-budget hydration=compact
python3 plugins/trust-evidence-protocol/scripts/context_cli.py --context .codex_context configure-runtime --input-capture user_prompts=metadata-only --input-capture session_linking=false
python3 plugins/trust-evidence-protocol/scripts/context_cli.py --context .codex_context configure-runtime --analysis logic_solver.backend=z3 --analysis logic_solver.install_policy=ask
python3 plugins/trust-evidence-protocol/scripts/context_cli.py --context .codex_context configure-runtime --analysis topic_prefilter.backend=nmf --analysis topic_prefilter.missing_dependency=warn
python3 plugins/trust-evidence-protocol/scripts/context_cli.py --context .codex_context configure-runtime --backend derivation.backend=datalog --backend derivation.datalog.enabled=true --backend derivation.datalog.mode=fake
python3 plugins/trust-evidence-protocol/scripts/context_cli.py --context .codex_context configure-runtime --backend fact_validation.backend=rdf_shacl --backend fact_validation.rdf_shacl.enabled=true --backend fact_validation.rdf_shacl.mode=fake
python3 plugins/trust-evidence-protocol/scripts/context_cli.py --context .codex_context configure-runtime --backend code_intelligence.cocoindex.default_scope=project --backend code_intelligence.cocoindex.storage_root='<context>/backends/cocoindex'
```

Use `hooks.verbosity=quiet` to reduce routine hook chatter while preserving stale/conflict/blocking messages.
Use `hooks.run_capture=off|mutating|all` to control automatic PostToolUse `RUN-*` capture; default `mutating` avoids turning every read-only `rg/ls/sed` into canonical context churn.
Use `context_budget` as policy for compact/normal/debug output; do not treat compact output as permission to omit decisive ids.
Use `input_capture` as policy for prompt provenance; `INP-*` records are not proof until classified into `SRC-*`, `CLM-*`, `GLD-*`, `TASK-*`, or another appropriate record.
Do not call an `INP-*` a remembered fact/rule. Use `review/inputs.md` to find unclassified inputs, then create/link the derived canonical records before final response.
Use `analysis` as policy for optional helpers such as Z3 and NMF; it is not proof and not permission to silently install dependencies.
Use `backends` as policy for optional external adapters such as RDF/SHACL, Serena, CocoIndex, and Datalog-style derivation; missing dependencies must degrade to status diagnostics instead of crashing normal TEP commands.
Keep CocoIndex behind TEP `code-search`; default to project scope and use workspace scope only as a deliberate outward glance.

## Local Anchors

```bash
python3 plugins/trust-evidence-protocol/scripts/context_cli.py --context ~/.tep_context init-anchor --directory . --workspace WSP-* --project PRJ-* --allowed-freedom proof-only
python3 plugins/trust-evidence-protocol/scripts/context_cli.py show-anchor
python3 plugins/trust-evidence-protocol/scripts/context_cli.py --context ~/.tep_context validate-anchor
```

Use `.tep` as a workdir-local anchor when one global `~/.tep_context` contains several workspaces or projects.
The anchor stores `context_root`, `workspace_ref`, optional `project_ref`, and local display/budget settings.
It is not canonical memory and must not contain facts, records, permissions, restrictions, guidelines, or proposals.
Local `allowed_freedom` can only lower the effective strictness; it cannot raise `proof-only` to a more permissive mode.
Hooks use the Codex payload cwd when available, so anchored workdirs keep their own workspace/project focus even when the plugin code lives elsewhere.

## Code Index

```bash
python3 plugins/trust-evidence-protocol/scripts/context_cli.py --context .codex_context init-code-index --root .
python3 plugins/trust-evidence-protocol/scripts/context_cli.py --context .codex_context index-code --root . --include "src/**/*.py" --include "tests/**/*.py"
python3 plugins/trust-evidence-protocol/scripts/context_cli.py --context .codex_context code-refresh --root . --path "tests/**/*.py"
python3 plugins/trust-evidence-protocol/scripts/context_cli.py --context .codex_context code-info --path tests/unit/test_example.py --fields target,imports,symbols,features,freshness
python3 plugins/trust-evidence-protocol/scripts/context_cli.py --context .codex_context code-search --import pytest --fields target,imports,features --limit 20
python3 plugins/trust-evidence-protocol/scripts/context_cli.py --context .codex_context code-search --query "prompt choice backend" --fields target --limit 8
python3 plugins/trust-evidence-protocol/scripts/context_cli.py --context .codex_context code-search --scope workspace --query "shared client behavior" --fields target --limit 8
python3 plugins/trust-evidence-protocol/scripts/context_cli.py --context .codex_context code-search --query "prompt choice backend" --link-candidate CLM-* --fields target --format json
python3 plugins/trust-evidence-protocol/scripts/context_cli.py --context .codex_context code-feedback --query "prompt choice backend" --link-candidate CLM-* --format json
python3 plugins/trust-evidence-protocol/scripts/context_cli.py --context .codex_context code-feedback --apply --entry CIX-* --link-candidate CLM-* --note "reviewed backend hit links this claim to this code area"
python3 plugins/trust-evidence-protocol/scripts/context_cli.py --context .codex_context code-search --annotation-kind smell --annotation-category mixed-responsibility --fields target,annotations
python3 plugins/trust-evidence-protocol/scripts/context_cli.py --context .codex_context code-smell-report --category mixed-responsibility
python3 plugins/trust-evidence-protocol/scripts/context_cli.py --context .codex_context code-entry create --target-kind directory --path tests/e2e --summary "E2E tests" --note "manual code area"
python3 plugins/trust-evidence-protocol/scripts/context_cli.py --context .codex_context annotate-code --entry CIX-* --kind agent-note --note "..."
python3 plugins/trust-evidence-protocol/scripts/context_cli.py --context .codex_context annotate-code --entry CIX-* --kind smell --category mixed-responsibility --severity medium --suggestion "..." --note "..."
python3 plugins/trust-evidence-protocol/scripts/context_cli.py --context .codex_context link-code --entry CIX-* --guideline GLD-* --note "guideline applies here"
python3 plugins/trust-evidence-protocol/scripts/context_cli.py --context .codex_context assign-code-index --record PLN-* --entry CIX-* --note "plan affects this code area"
```

Treat `CIX-*` as navigation/scope/impact only.
Do not use CIX entries as proof, claim support, source support, action justification, or evidence-chain nodes.
Backend hits may include `cix_candidates`, `index_suggestion`, and `link_suggestions`.
Apply a suggested CIX-to-record link with `link-code` only after inspecting the code hit and verifying that the relationship is useful.
Use `code-feedback` when you want a dedicated review/apply loop for backend hits.
Read the code or cite a `SRC-*` before making truth claims about behavior or compliance.
Use smell annotations as local critique/search signals, not hard rules.
When a smell repeats and has support, create a `PRP-*` for options or a `GLD-*` through normal guideline recording; do not auto-promote smells.
Agents should attach smells to the smallest applicable CIX target, preferring symbol over file and file over directory/area.
Critical smell annotations require a supporting `CLM-*`.

## Workspaces, Projects, And Tasks

```bash
python3 plugins/trust-evidence-protocol/scripts/context_cli.py --context .codex_context record-workspace --workspace-key "..." --title "..." --root-ref /abs/project --note "..."
python3 plugins/trust-evidence-protocol/scripts/context_cli.py --context .codex_context show-workspace
python3 plugins/trust-evidence-protocol/scripts/context_cli.py --context .codex_context set-current-workspace --workspace WSP-*
python3 plugins/trust-evidence-protocol/scripts/context_cli.py --context .codex_context assign-workspace --workspace WSP-* --all-unassigned
python3 plugins/trust-evidence-protocol/scripts/context_cli.py --context .codex_context assign-workspace --workspace WSP-* --records-file /tmp/record-ids.txt
python3 plugins/trust-evidence-protocol/scripts/context_cli.py --context .codex_context record-project --project-key "..." --title "..." --root-ref SRC-* --note "..."
python3 plugins/trust-evidence-protocol/scripts/context_cli.py --context .codex_context show-project
python3 plugins/trust-evidence-protocol/scripts/context_cli.py --context .codex_context set-current-project --project PRJ-*
python3 plugins/trust-evidence-protocol/scripts/context_cli.py --context .codex_context start-task --type investigation --scope "..." --title "..." --note "..."
python3 plugins/trust-evidence-protocol/scripts/context_cli.py --context .codex_context show-task
python3 plugins/trust-evidence-protocol/scripts/context_cli.py --context .codex_context task-drift-check --intent "..." --type implementation
python3 plugins/trust-evidence-protocol/scripts/context_cli.py --context .codex_context review-precedents --task-type investigation --query "..."
python3 plugins/trust-evidence-protocol/scripts/context_cli.py --context .codex_context pause-task --note "..."
python3 plugins/trust-evidence-protocol/scripts/context_cli.py --context .codex_context resume-task --task TASK-* --note "..."
python3 plugins/trust-evidence-protocol/scripts/context_cli.py --context .codex_context switch-task --task TASK-* --note "..."
python3 plugins/trust-evidence-protocol/scripts/context_cli.py --context .codex_context complete-task
python3 plugins/trust-evidence-protocol/scripts/context_cli.py --context .codex_context stop-task
```

Use `WSP-*` as the memory boundary first. A record can lack a precise `PRJ-*`, but new records should inherit the current workspace when one is set.
Use `task-drift-check` when intended work may no longer match the current `TASK-*`.
If the work is adjacent, note or expand the task context.
If it is drifted, pause/switch/start a task instead of silently continuing.
Use `review-precedents` before substantial repeated task types to inspect prior tasks, linked plans, debt, actions, and open questions.

## Working Context

```bash
python3 plugins/trust-evidence-protocol/scripts/context_cli.py --context .codex_context working-context create --scope "..." --title "..." --pin CLM-* --topic-seed CLM-* --note "..."
python3 plugins/trust-evidence-protocol/scripts/context_cli.py --context .codex_context working-context show
python3 plugins/trust-evidence-protocol/scripts/context_cli.py --context .codex_context working-context fork --context WCTX-* --add-pin CLM-* --add-topic-term "..." --note "..."
python3 plugins/trust-evidence-protocol/scripts/context_cli.py --context .codex_context working-context close --context WCTX-* --note "..."
```

Use `WCTX-*` for operational focus, pinned refs, local assumptions, concerns, and handoff.
Working contexts are not proof and must not replace `CLM-*` plus `SRC-*`.
Use `fork` for copy-on-write changes so plans/actions can later be tied to the context that existed at the time.

## Topic Index

```bash
python3 plugins/trust-evidence-protocol/scripts/context_cli.py --context .codex_context topic-index build --method lexical
python3 plugins/trust-evidence-protocol/scripts/context_cli.py --context .codex_context topic-search --query "gateway retry" --type claim
python3 plugins/trust-evidence-protocol/scripts/context_cli.py --context .codex_context topic-info --record CLM-*
python3 plugins/trust-evidence-protocol/scripts/context_cli.py --context .codex_context topic-conflict-candidates
```

`topic_index/` is generated navigation data.
It is useful for narrowing broad searches and finding records worth comparing, but topic overlap is not a contradiction and not proof.

## Logic Index

```bash
python3 plugins/trust-evidence-protocol/scripts/context_cli.py --context .codex_context logic-index build
python3 plugins/trust-evidence-protocol/scripts/context_cli.py --context .codex_context logic-search --predicate Student
python3 plugins/trust-evidence-protocol/scripts/context_cli.py --context .codex_context logic-search --symbol person:alice
python3 plugins/trust-evidence-protocol/scripts/context_cli.py --context .codex_context logic-graph --symbol person:alice
python3 plugins/trust-evidence-protocol/scripts/context_cli.py --context .codex_context logic-graph --smells
python3 plugins/trust-evidence-protocol/scripts/context_cli.py --context .codex_context logic-check
python3 plugins/trust-evidence-protocol/scripts/context_cli.py --context .codex_context logic-check --solver z3 --closure rules --format json
python3 plugins/trust-evidence-protocol/scripts/context_cli.py --context .codex_context logic-conflict-candidates
```

Use `CLM.logic` for typed symbols, atoms, and Horn-style rules attached to source-backed claims.
`logic_index/` is generated checking/navigation data.
Predicate candidates are not proof and must be resolved by reviewing/updating the underlying `CLM-*` records.
Before adding a new `CLM.logic.symbols` entry, use `logic-graph` or MCP `logic_graph` to search existing symbols/predicates and avoid duplicate vocabulary.
New `--logic-symbol` entries must include `symbol|kind|meaning[|note]`; `meaning` explains the semantic object the agent needs.
If `analysis.logic_solver.backend` requests an optional solver such as `z3`, respect `missing_dependency` and `install_policy` instead of silently changing the environment.
Use Z3 reports as claim-level contradiction candidates only.
When Z3 returns `unsat`, inspect the reported `CLM-*`, logic refs, derived atoms, and underlying `SRC-*` records before changing claim status or lifecycle.

## Control And Guidance

```bash
python3 plugins/trust-evidence-protocol/scripts/context_cli.py --context .codex_context record-permission --scope "..." --applies-to task --grant "..." --note "..."
python3 plugins/trust-evidence-protocol/scripts/context_cli.py --context .codex_context record-restriction --scope "..." --title "..." --applies-to task --severity warning --rule "..." --note "..."
python3 plugins/trust-evidence-protocol/scripts/context_cli.py --context .codex_context record-guideline --scope "..." --domain code --applies-to project --priority preferred --rule "..." --source SRC-* --note "..."
python3 plugins/trust-evidence-protocol/scripts/context_cli.py --context .codex_context show-restrictions
python3 plugins/trust-evidence-protocol/scripts/context_cli.py --context .codex_context show-guidelines
python3 plugins/trust-evidence-protocol/scripts/context_cli.py --context .codex_context request-strictness-change evidence-authorized --reason "..."
python3 plugins/trust-evidence-protocol/scripts/context_cli.py --context .codex_context record-source --scope strictness.approval --source-kind theory --critique-status accepted --origin-kind user --origin-ref "user approval" --quote "TEP-APPROVE REQ-*" --note "strictness approval"
python3 plugins/trust-evidence-protocol/scripts/context_cli.py --context .codex_context change-strictness evidence-authorized --request REQ-* --approval-source SRC-*
```

Do not run `change-strictness` upward from a permission alone.
The user approval source must quote the exact `TEP-APPROVE REQ-*` line printed by `request-strictness-change`.
Lowering strictness back to `proof-only` can be done directly.

## Records

```bash
python3 plugins/trust-evidence-protocol/scripts/context_cli.py --context .codex_context record-input --scope "..." --input-kind user_prompt --origin-kind user --origin-ref "chat-turn" --text "..." --note "..."
python3 plugins/trust-evidence-protocol/scripts/context_cli.py --context .codex_context classify-input --input INP-* --derived-record SRC-* --note "classified prompt"
python3 plugins/trust-evidence-protocol/scripts/context_cli.py --context .codex_context input-triage report --task TASK-*
python3 plugins/trust-evidence-protocol/scripts/context_cli.py --context .codex_context input-triage link-operational --task TASK-* --input INP-* --note "operational prompt"
python3 plugins/trust-evidence-protocol/scripts/context_cli.py --context .codex_context record-support --scope "..." --kind command-output --command "..." --quote "..." --thought "..." --claim-status tentative --note "..."
python3 plugins/trust-evidence-protocol/scripts/context_cli.py --context .codex_context record-run --command "uv run pytest -q" --exit-code 0 --stdout-quote "passed" --note "hook/API captured run"
python3 plugins/trust-evidence-protocol/scripts/context_cli.py --context .codex_context record-claim --scope "..." --statement "Alice studies algebra." --plane runtime --status supported --source SRC-* --logic-symbol "person:alice|entity" --logic-symbol "subject:algebra|concept" --logic-atom "Studies|person:alice,subject:algebra|affirmed" --note "..."
python3 plugins/trust-evidence-protocol/scripts/context_cli.py --context .codex_context show-claim-lifecycle --claim CLM-*
python3 plugins/trust-evidence-protocol/scripts/context_cli.py --context .codex_context resolve-claim --claim CLM-* --resolved-by-claim CLM-* --note "..."
python3 plugins/trust-evidence-protocol/scripts/context_cli.py --context .codex_context archive-claim --claim CLM-* --note "..."
python3 plugins/trust-evidence-protocol/scripts/context_cli.py --context .codex_context restore-claim --claim CLM-* --note "..."
python3 plugins/trust-evidence-protocol/scripts/context_cli.py --context .codex_context record-action --kind edit --scope "..." --justify CLM-* --safety-class guarded --status executed --evidence-chain evidence-chain.json --note "..."
python3 plugins/trust-evidence-protocol/scripts/context_cli.py --context .codex_context record-plan --scope "..." --title "..." --priority medium --justify CLM-* --step "..." --success "..." --note "..."
python3 plugins/trust-evidence-protocol/scripts/context_cli.py --context .codex_context record-debt --scope "..." --title "..." --priority medium --evidence CLM-* --note "..."
python3 plugins/trust-evidence-protocol/scripts/context_cli.py --context .codex_context record-feedback --scope "tep.plugin" --kind false-positive --surface hook --severity high --title "..." --actual "..." --expected "..." --repro "..." --suggestion "..."
python3 plugins/trust-evidence-protocol/scripts/context_cli.py --context .codex_context record-model --knowledge-class domain --domain "..." --scope "..." --aspect "..." --summary "..." --claim CLM-* --note "..."
python3 plugins/trust-evidence-protocol/scripts/context_cli.py --context .codex_context record-flow --knowledge-class domain --domain "..." --scope "..." --summary "..." --model MODEL-* --note "..."
python3 plugins/trust-evidence-protocol/scripts/context_cli.py --context .codex_context record-open-question --domain "..." --scope "..." --aspect "..." --question "..." --note "..."
python3 plugins/trust-evidence-protocol/scripts/context_cli.py --context .codex_context record-proposal --scope "..." --subject "..." --position "..." --proposal "title|why|tradeoff|recommended" --claim CLM-* --note "..."
```

Use `resolve-claim` before repeated old facts become attention noise.
Use `archive-claim` only when default retrieval should stop seeing the claim.
Use `show-claim-lifecycle` before restoring old context into active use.
Use `record-feedback` when the plugin, hook, MCP server, skill, docs, reasoning
workflow, code index, or context merge causes agent-visible friction. It creates
a feedback `SRC-*` and an open `DEBT-*`; it is not proof by itself.

## Hypotheses

```bash
python3 plugins/trust-evidence-protocol/scripts/context_cli.py --context .codex_context hypothesis list
python3 plugins/trust-evidence-protocol/scripts/context_cli.py --context .codex_context hypothesis add --claim CLM-* --note "..."
python3 plugins/trust-evidence-protocol/scripts/context_cli.py --context .codex_context validate-decision --mode planning --chain evidence-chain.json
python3 plugins/trust-evidence-protocol/scripts/context_cli.py --context .codex_context hypothesis close --claim CLM-* --status confirmed --note "..."
python3 plugins/trust-evidence-protocol/scripts/context_cli.py --context .codex_context hypothesis remove --claim CLM-* --note "..."
```

## If Commands Are Missing

If plugin commands are unavailable:

- follow the same semantics manually
- do not invent record ids unless writing records
- state that mechanical validation was unavailable
- keep public ids, quotes, and support edges explicit
