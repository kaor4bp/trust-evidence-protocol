# Persistence And Records Workflow

Use this workflow when deciding whether incoming information, discoveries, rules, actions, plans, debt, models, flows, or critiques should become TEP context records.

## Persistence Pressure

Persist when the information will likely matter to a future agent:

- a reusable user instruction or team convention
- a supported code/runtime/theory fact
- a true historical/resolved claim that should no longer dominate current retrieval
- a contradiction, accepted deviation, or rejected claim
- a current task or project boundary
- a permission or restriction
- a guideline for writing code, tests, reviews, debugging, architecture, or agent behavior
- an executed or intended meaningful action
- an overall model or flow that summarizes multiple claims
- a plan, technical debt item, open question, or stop condition
- a constructive agent proposal with options and risks
- a working-context snapshot needed for handoff, retrospective, local assumptions, or keeping a long task coherent

Do not persist every transient thought.
Persist reconstructable evidence, durable decisions, and useful continuity.

## Write Boundary

Use plugin commands for canonical structured memory:

- write `SRC-*`, `CLM-*`, `PRM-*`, `RST-*`, `GLD-*`, `PRP-*`, `ACT-*`, `TASK-*`, `PRJ-*`, `MODEL-*`, `FLOW-*`, `PLN-*`, `DEBT-*`, and `OPEN-*` through `context_cli.py record-*` or the dedicated lifecycle/task/project commands
- do not write `<context>/records/*.json` directly with shell redirection, `tee`, ad hoc scripts, or manual JSON edits when a command exists
- do not edit `<context>/settings.json`, generated views, indexes, or review files by hand unless there is no plugin command and the user explicitly accepts the risk

Direct file output is acceptable only for raw payloads under `<context>/artifacts/`.
Use this for screenshots, copied logs, JSON snapshots, command output, and other large or binary evidence carriers.
After capturing the payload, create or update a `SRC-*` record that references the artifact before treating it as durable evidence.

Do not use the artifact exception for source code, `/tmp`, arbitrary workspace paths, or canonical records.

Use `<context>/code_index/entries/CIX-*.json` for generated/navigation code map entries.
CIX entries may describe files, directories, globs, symbols, or logical areas, and may carry AST metadata, manual features, annotations, and navigation links.
CIX entries are not truth records and must not be used as proof, source support, claim support, action justification, or evidence-chain nodes.
When a CIX note or link matters for truth, inspect the referenced code and persist an accepted `SRC-*` / `CLM-*` chain.
Use CIX `smell` annotations for local engineering critique on the smallest applicable target.
Smell annotations may guide review/search, but they do not become hard rules until repeated support is recorded through `CLM-*`, `PRP-*`, and optionally `GLD-*`.
If the code changes after the annotation snapshot, treat the smell as stale until rechecked; it may have disappeared or it may still apply.

Use `WCTX-*` working-context records for operational focus, handoff, pinned refs, topic seeds, local assumptions, and concerns.
WCTX records are not truth records and must not be used as proof, claim support, source support, action justification, or decisive evidence-chain nodes.
Fork WCTX records copy-on-write when the working context changes materially, instead of overwriting what a past plan/action depended on.

Use `<context>/topic_index/` only as generated lexical prefilter data.
Topic overlap may suggest which records to compare, but it does not prove contradiction and must not replace structured `comparison` on claims or `scan-conflicts`.

Use `CLM.logic` for optional typed predicate projections of claims.
Every concrete symbol used by an atom must be introduced by a source-backed claim, either in the same `CLM.logic.symbols` block or in an existing claim.
Use `logic_index/` only as generated predicate checking/navigation data.
Predicate conflicts are candidates until the underlying `CLM-*` records are reviewed and status/lifecycle changes are recorded.

## Record Mapping

- User message, file, command output, log, screenshot, document, or artifact -> `SRC-*`
- Normalized factual assertion -> `CLM-*`
- Machine-checkable predicate projection -> `CLM.logic` inside the relevant `CLM-*`
- Authorization -> `PRM-*`
- Negative control constraint -> `RST-*`
- Reusable operational rule -> `GLD-*`
- Agent critique/options/recommendation -> `PRP-*`
- Operational focus/handoff snapshot -> `WCTX-*`
- Code file/folder/glob/symbol/area map -> `CIX-*`
- Local code smell/implementation concern -> CIX `smell` annotation first; `PRP-*` or `GLD-*` only after support/generalization
- Meaningful operation -> `ACT-*`
- Current execution focus -> `TASK-*`
- Context boundary -> `PRJ-*`
- Overall domain/aspect picture -> `MODEL-*`
- End-to-end process understanding -> `FLOW-*`
- Durable intended work -> `PLN-*`
- Durable cleanup/risk -> `DEBT-*`
- Deferred uncertainty -> `OPEN-*`

## Quality Bar

Records should be:

- scoped to global, project, or task when relevant
- source-backed where they assert truth
- short enough to scan
- quoted enough to audit
- linked to related records
- updated, superseded, contested, rejected, completed, or stopped rather than duplicated forever
- resolved, historical, or archived when correct old context should remain searchable but stop steering current work
- explicit about observed file `sha256` when annotations or links depend on a file version

## What Not To Use As Proof

```text
generated view -/-> canonical record
runtime state -/-> proof
backlog item -/-> proof
memory record -/-> proof by existence
task context -/-> proof
permission/restriction/guideline/proposal -/-> truth
CIX/code_index -/-> proof
WCTX/working_context -/-> proof
topic_index -/-> proof
logic_index -/-> proof
logic atom -/-> proof outside its source-backed claim
```

## Guidelines

When the user says how code, tests, reviews, debugging, architecture, or agent behavior should be done:

1. record the user statement or source as `SRC-*`
2. create or update `GLD-*`
3. scope it as global, project, or task
4. mark priority as required, preferred, or optional
5. disclose it before substantial edits and after substantial edits

Do not store reusable coding/test rules as `CLM-*` truth claims unless there is a factual assertion behind them.

## Claim Lifecycle

Use truth `status` for epistemic correctness and `lifecycle.state` for retrieval pressure.

- Keep current usable claims `active`.
- Use `resolve-claim` for claims that were correct but no longer reproduce or no longer describe current behavior.
- Use `archive-claim` for claims that should be explicit-reference/audit/rollback only.
- Use `restore-claim` when an old issue starts reproducing or becomes relevant again.
- Do not lower a corroborated historical fact to tentative just to hide it from the agent.
- Do not delete old claims only because they are noisy; use lifecycle so audit and rollback remain possible.
- Close active `hypotheses.jsonl` entries before resolving or archiving a tentative claim.
- Update or mark stale any `working`/`stable` `MODEL-*` or `FLOW-*` that depends on a claim you move to fallback lifecycle.

## Logic Projection

Use `CLM.logic` when a claim should participate in mechanical conflict checks.
Define:

- `symbols`: typed objects such as `person:alice`, `service:bridge-client-sdk`, or `action:commit`
- `atoms`: predicate applications such as `Student(person:alice)` or `Visible(ui:overlay)=true`
- `rules`: Horn-style rules such as `Student(?x) & Studies(?x, ?s) -> ExpectedPassesExam(?x, ?s)`

Rules:

- Keep `CLM-*` as the truth source; do not create separate atom truth records.
- Do not attach atoms to claims without accepted source support.
- Do not use unknown symbols in atoms.
- Prefer expectation predicates such as `ExpectedPassesExam` over over-strong runtime predicates when a rule describes an oracle or invariant.
- Use `logic-index build`, `logic-search`, and `logic-check` for mechanical lookup/checking only.

## Proposals

When the agent has a constructive opinion:

1. cite relevant `CLM-*`, `GLD-*`, `MODEL-*`, `FLOW-*`, or `OPEN-*`
2. record the position as `PRP-*`
3. include concrete options
4. mark the recommended option explicitly
5. include assumptions, risks, and stop conditions
6. do not use proposal assumptions as proof

## Plans And Debt

Use `PLN-*` for intended future work and prioritization.
Use `DEBT-*` for known cleanup, validator gaps, protocol gaps, or technical risk.
Close, complete, supersede, or reject them when they stop being relevant.

## Working Contexts

Use `WCTX-*` when a task benefits from a durable "what we were looking at" snapshot.
Store pinned record ids, focus paths, topic seeds, local assumptions, concerns, and handoff notes.
Use `working-context fork` for meaningful context changes so later retrospective can reconstruct what changed.
Use `working-context close` when the context should stop steering current work.

## Hypotheses

Hypotheses are tentative `CLM-*` records.
`hypotheses.jsonl` is an index over active tentative claims, not a second source of truth.
Exploration hypotheses may depend on other hypotheses locally, but must not appear as proof in evidence chains.
