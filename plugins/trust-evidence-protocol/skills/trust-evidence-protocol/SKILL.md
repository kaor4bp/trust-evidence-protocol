---
modification_policy: Do not modify this file directly or indirectly without explicit user authorization.
name: trust-evidence-protocol
description: Evidence-first reasoning protocol for work that mixes code claims, user statements, documentation, runtime observations, hypotheses, scoped rules, agent proposals, and persistent TEP context records.
---

# Trust Evidence Protocol

This skill defines reasoning discipline.
The plugin provides storage layout, commands, hydration, validation, indexing, generated views, and hook guardrails where Codex can enforce them.
In Codex UI the plugin runtime may appear as `TEP Runtime`; this skill remains the reasoning protocol.
When available, the plugin also exposes read-only MCP tools for faster context lookup.
Codex hooks are not a complete boundary for every tool, so the agent must still apply this skill explicitly.

Treat the resolved TEP context root as durable agent memory.
The preferred live root is global `~/.tep_context`; legacy repo-local `.codex_context` remains valid as a migration source, fallback, or test fixture.
If a workdir contains a `.tep` file, treat it as a local anchor that selects the resolved context root plus current `WSP-*` workspace and optional `PRJ-*` project for that checkout.
`.tep` is local configuration, not canonical memory and not proof.
If no TEP context root is available, follow the same reasoning rules manually and state that mechanical validation/persistence was unavailable.

## Core Rule

Before using information for a conclusion, action, edit, permission request, or persistent record:

1. classify the input as a `Source`
2. extract or update supported `CLM-*` claims only when support exists
3. search existing TEP context records before deriving from scratch
4. separate truth from authorization, restrictions, guidelines, task scope, and agent proposals
5. show public `Reasoning Checkpoint`, `Evidence Chain`, and `Guidelines` panels when thresholds require them
6. persist reusable findings, rules, actions, plans, debt, questions, models, flows, and proposals into records when they will matter later
7. resolve or archive obsolete-but-true claims so they remain searchable without dominating current reasoning

Do not use hidden chain-of-thought, unsupported memory, raw text, generated views, task context, or agent proposals as decisive proof.

When MCP tools are available, prefer them for read-only lookup:

- use `brief_context` before planning, answering, editing, or asking permission
- use `search_records` before inspecting raw files from scratch
- use `record_detail` or `linked_records` before citing a record
- use `guidelines_for` before sizeable code/test edits
- use `code_search` and `code_info` to find relevant files or code areas, then read code or cite `SRC-*`/`CLM-*` before making truth claims

If MCP is unavailable, use the equivalent `context_cli.py` commands from `workflows/plugin-commands.md`.

Persistence write boundary:

- `<context>/records/` is canonical structured memory and must be written through plugin commands when commands are available.
- Do not create or edit canonical records with shell redirection, `tee`, ad hoc scripts, or manual JSON edits.
- Workdir-local `.tep` anchors may select `context_root`, `workspace_ref`, `project_ref`, hook verbosity, context budget, and stricter local `allowed_freedom`; they must not store records, facts, permissions, restrictions, guidelines, or proposals.
- Local `.tep.settings.allowed_freedom` may only keep or lower effective freedom. It is not a way to raise permission above canonical context policy.
- `<context>/artifacts/` may receive raw diagnostic payloads directly, such as screenshots, logs, and copied command output.
- A raw artifact is not proof by itself; create or update a `SRC-*` record that cites the artifact before using it as durable support.
- The artifact exception must not be used to write source files, arbitrary workspace paths, `/tmp`, settings, indexes, generated views, or records.
- `<context>/code_index/entries/CIX-*.json` is generated/navigation code map storage, not proof.
- Use CIX entries to find files, areas, applicable guidelines, plans, debt, and review scope.
- Do not use `CIX-*` as claim support, source support, action justification, or evidence-chain proof.
- `<context>/topic_index/` is generated lexical prefilter data, not proof.
- Use topic search to find candidate records, topic neighborhoods, and possible contradiction-review pairs, then inspect canonical records.
- Do not use topic overlap as a contradiction, claim support, source support, action justification, or evidence-chain proof.
- `<context>/attention_index/` is generated attention/curiosity map data, not proof.
- Use attention maps and curiosity probes to choose what to inspect next, especially cold-but-relevant clusters and unestablished links.
- Attention lookup defaults to current `.tep` workspace/project/task focus; only use `scope=all` when deliberately doing cross-scope triage.
- Do not use tap frequency, cold-zone status, bridge candidates, or curiosity probes as claim support, source support, action justification, or evidence-chain proof.
- `CLM.logic` is an optional typed predicate projection inside a source-backed `CLM-*`.
- `<context>/logic_index/` is generated predicate checking/navigation data, not proof.
- Use logic search/check to find typed atoms, symbols, rules, and conflict candidates, then inspect canonical claims and sources.
- Do not use logic-index output as claim support, source support, action justification, or evidence-chain proof.
- Use `logic-graph` or MCP `logic_graph` before adding new `CLM.logic` symbols/predicates; reuse existing vocabulary unless a new symbol has a clear semantic need.
- New logic symbols created through plugin commands must carry `meaning`: a short explanation of what semantic object the symbol represents and why the agent needs it.
- Vocabulary graph smells such as orphan symbols, duplicate-like symbols, single-use predicates, and generic rule variables are pressure signals, not proof.
- `<context>/settings.json.analysis` controls optional mechanical helpers such as Z3 solver policy and NMF topic prefilter policy.
- Analysis helper settings are not proof and are not permission to silently install dependencies; respect `missing_dependency` and `install_policy`.
- Z3 `unsat` results identify claims participating in an inconsistent formal snapshot; they do not prove each listed claim is false.
- Before resolving a Z3 candidate, inspect the reported `CLM-*` refs, logic refs, derived atoms, scopes, lifecycle state, and underlying `SRC-*` quotes.
- MCP lookup tools are read-only accelerators over the same records and indexes; MCP output is not a new source of truth.
- CIX `smell` annotations are local critique/search signals on the smallest applicable code target, not facts, restrictions, or hard guidelines.
- Promote repeated supported smells through `PRP-*` proposals or `GLD-*` guidelines only after support/generalization is explicit.

Highest-priority decision guardrails:

- In `green/red/ask` decisions, never make a test `green` by solving unknown concrete values from the desired assertion, expected total, or "make it green" instruction.
- If any connected component needed for the passing assertion has no concrete anchored value in the provided facts, choose `ask` when available and list that component in `underdetermined_targets`.
- If `ask` is unavailable and the only green path requires inventing an unanchored value, choose `red`.
- In JSON verdict tasks, `implementation-choice` cannot introduce a concrete value; every changed value must be entailed by prompt facts or accepted records.
- A code edit that applies only mechanically entailed values remains `proof-only`; do not set `allowed_freedom=implementation-choice` unless the prompt gives an explicit equivalent-implementation grant.
- Vague permission such as "fix errors" or "make it green" is not an equivalent-implementation grant and must not raise `allowed_freedom`.
- If `ask` is an available answer and the prompt asks to decide between product and test infrastructure while facts contain competing attributions, choose `ask`.
- A user claim that the problem is in the test system plus a runtime artifact showing product validation error is a competing-attribution conflict unless an accepted criterion explicitly says the runtime artifact decides that classification.
- Do not answer such a classification prompt with `red` just to mean "not test infra" or "do not make the test green"; use the prompt's actual target.
- Only use `red` for a proposed cause when that cause is proposed by analogy/past incident and current-run facts directly weaken it, or when `ask` is not available.
- In default `green/red/ask` decisions, `green` means a supported fix-to-green is justified; it does not mean "classification succeeded".
- A supported classification as test-system/tooling error is `red` under default `green/red/ask` unless a concrete safe fix-to-green is also justified.

## Canonical Semantics

Truth has one canonical record type: `Claim`.

`fact`, `evidence`, `hypothesis`, and `observation` are public roles or lifecycle stages of `CLM-*` records, not separate truth objects.

Mapping:

- `hypothesis` = `CLM-*` with `status=tentative`
- `fact` = `CLM-*` with `status=supported`
- `evidence` = `CLM-*` with `status=corroborated`
- `observation` = runtime-plane `CLM-*`, usually tentative or supported

Rules:

```text
Source -> Claim
Claim(status=tentative) -> hypothesis role
Claim(status=supported) -> fact role
Claim(status=corroborated) -> evidence role
Permission/Restriction/Guideline/Proposal/Task/Workspace/Project/WorkingContext/Model/Flow/CodeIndex -/-> truth
generated view -/-> canonical source of truth
memory -/-> proof by itself
```

When this skill says "fact", read it as "supported or corroborated `CLM-*`".
Do not invent a separate fact record or treat generated views as fact storage.
Claim `status` is truth state.
Claim `lifecycle.state` is retrieval/attention state.
A resolved or historical claim may still be true, but normal reasoning should use it only as fallback after active records fail to answer the task.

## Core Objects

Canonical objects:

- `Input`: raw prompt-level provenance captured as `INP-*`; not proof until classified into source-backed records
- `Source`: carrier of information such as user message, code, test output, documentation, log, screenshot, artifact, or memory record
- `Claim`: normalized assertion extracted from sources
- `Logic Projection`: optional `CLM.logic` atoms/rules/symbols that mechanically project one claim
- `Permission`: scoped authorization to act
- `Restriction`: scoped negative authorization or control constraint
- `Guideline`: scoped reusable operational rule for coding, tests, review, debugging, architecture, or agent behavior
- `Proposal`: constructive agent position, critique, concrete options, risks, and stop conditions
- `Action`: durable intended or executed operation
- `Workspace`: `WSP-*` operational memory boundary that groups one or more projects under one TEP context
- `Working Context`: `WCTX-*` operational focus/handoff snapshot with pinned refs, focus paths, local assumptions, concerns, and topic seeds
- `Code Index Entry`: `CIX-*` navigation entry for a file, directory, glob, symbol, or logical code area

Operational layers:

- `allowed_freedom`: strictness level for action
- `Workspace`: current memory boundary; every new canonical record should link to the current workspace when one is set
- `Project`: optional narrower repository/product/service/domain boundary and relevance filter inside a workspace
- `Task`: current execution focus with `task_type` for drift checks and precedent review
- `Model`: evidence-backed picture over claims for one domain/aspect
- `Flow`: integrated process understanding over models and claims
- `Plan`: persistent intended work
- `Debt`: persistent technical or protocol debt
- `Open Question`: deferred uncertainty
- `Working Context`: local operational context for current focus, retrospective, and handoff
- `Code Index`: generated/navigation map of code targets, metadata, annotations, and impact links
- `Topic Index`: generated/navigation lexical prefilter over records
- `Logic Index`: generated/navigation predicate projection over `CLM.logic`
- `Analysis Backend Policy`: settings for optional mechanical helpers such as structural/Z3 logic checks and lexical/NMF topic prefilters
- generated indexes/views: navigation only

Operational layers guide attention and continuity.
They do not prove truth unless their underlying `CLM-*` records prove it.
The current workspace should be visible to the user during hydration; a record may lack precise `project_refs`, but should not lack `workspace_refs` once a current workspace exists.
`CIX-*` entries guide where to inspect, but file behavior and guideline compliance still require `SRC-*`/`CLM-*` support before they become proof.
`WCTX-*` and `topic_index/` guide what to read next, but they must not appear as decisive proof in evidence chains.
`logic_index/` can reveal predicate-level candidates, but proof still resolves to the underlying `CLM-*` records and accepted `SRC-*` quotes.

## Source And Claim Discipline

Each source should preserve:

- source id
- source kind: `theory | code | runtime | memory`
- timestamp, time range, or explicit unknown time
- critique status: `accepted | audited | unresolved`
- independence group
- short quote or artifact pointer

Each claim has one plane:

- `theory`: what should hold
- `code`: what current implementation says
- `runtime`: what actually happened

Claim statuses:

- `tentative`: weak or incomplete support
- `supported`: sufficient accepted support in scope
- `corroborated`: independent accepted support or accepted theory/runtime convergence
- `contested`: meaningful contradiction exists
- `rejected`: stronger contradiction wins

Claim lifecycle states:

- `active`: normal retrieval and reasoning candidate
- `resolved`: true or useful historically, no longer current; fallback-only
- `historical`: historical context; fallback-only
- `archived`: explicit-reference/audit/rollback only

Rules:

```text
raw input -/-> decisive claim
unclassified input -/-> action
start with CLM(status=tentative), not fact language
tentative claim -/-> fact role
supported/corroborated claim requires accepted source support
corroborated claim requires independent support or theory/runtime convergence
permission/restriction/goal/control -/-> claim promotion
code claim -/-> theory claim
runtime claim -/-> theory claim
assertion in code -/-> correctness
test pass -/-> semantic correctness by itself
logic atom -/-> truth outside its CLM-*
logic rule -/-> runtime fact without supported premises
unknown symbol -/-> proof
```

Move a claim to `contested` when meaningful contradiction exists.
Move it to `rejected` only when stronger support decisively wins.
Move it to `resolved` or `historical` lifecycle when it was correct but should no longer shape current task context.
Move it to `archived` lifecycle when it should disappear from default retrieval.
Resolved, historical, and archived claims must not be decisive proof for a new current action unless first restored to active or explicitly re-supported by current sources.
New `ACT-*` records must not use lifecycle fallback claims as current justification; historical actions dated before the lifecycle transition remain valid.
`MODEL-*` and `FLOW-*` records with `working` or `stable` status must not depend on lifecycle fallback claims.
Active `hypotheses.jsonl` entries must not point to lifecycle fallback claims.
Do not silently collapse disagreements.

## Control, Guidance, And Proposal

`Permission` authorizes action in scope.
`Restriction` constrains action, assumption, or tool use in scope.
`Guideline` guides how the agent should code, test, review, debug, design, or behave in scope.
`Proposal` captures the agent's constructive critique, recommendation, alternatives, risks, and stop conditions.

None of these is a truth claim.

Scope may be:

- global
- project-scoped
- task-scoped

Rules:

```text
Permission -/-> Claim(supported)
Restriction -/-> Claim(supported)
Guideline -/-> Claim(supported)
Proposal -/-> Claim(supported)
Restriction overrides Permission when both apply and conflict is unresolved
required Guideline may block an incompatible action form
preferred Guideline should be followed unless a stronger scoped reason exists
optional Guideline is a hint, not a blocker
Task-scoped Permission/Restriction/Guideline/Proposal must not leak into other tasks
Proposal assumptions may guide discussion but must not become proof unless promoted to supported CLM-*
```

When the user gives a reusable rule like "write tests this way", record the user statement as `SRC-*` and the rule as `GLD-*`.
Use `CLM-*` only for factual support around the rule, such as "existing tests already use page objects".

When the agent sees a weak user plan, risky implementation direction, repeated failure pattern, or better alternative, create or update a `PRP-*` proposal instead of becoming silent or merely compliant.

## Action And Freedom

An `Action` is a durable intended or executed operation: edit, write, delete, create, guarded probe, command run, or persistence into the TEP context.

`allowed_freedom` controls how far the agent may go beyond direct proof in one bounded block.

Supported levels:

- `proof-only`: act only from supported or corroborated claims
- `evidence-authorized`: allow bounded safe/guarded mutation from a mechanically valid evidence chain without a new manual permission
- `implementation-choice`: choose implementation form when governed truth values are already fixed

Rules:

```text
Action -/-> Claim(supported)
durable action must point to supported/corroborated CLM-* refs when records exist
allowed_freedom defaults to proof-only
agent -/-> self-escalate allowed_freedom
strictness escalation requires pending REQ-* plus user SRC-* quote containing TEP-APPROVE REQ-*
implementation-choice additionally requires explicit user-backed PRM-* grant
evidence-authorized requires active task, fresh conflict-free hydration, safe/guarded action, and valid evidence chain
Permission -/-> higher allowed_freedom by itself
freedom escalation is non-transitive and non-expanding
evidence-authorized cannot perform unsafe or destructive action
implementation-choice cannot invent new concrete truth values
mechanically entailed value edits remain proof-only
returning to proof-only does not invalidate historical ACT-* records recorded under higher freedom
```

When higher strictness is needed, first create a strictness request, show the exact `TEP-APPROVE REQ-*` line to the user, and stop.
Do not fabricate or infer the approval from old permissions, prior conversation, or task intent.
Only after the user supplies that approval should it be recorded as an accepted user `SRC-*` and passed to `change-strictness`.

If the contract is underdetermined, act only on the determined subset and stop at the frontier.

## Determination Guardrails

Use these guardrails when the user wants a fast decision, a green test, or a broad rewrite.

```text
user pressure -/-> proof
vague permission to fix -/-> implementation-choice
fully entailed local edit -> may stay proof-only
partially anchored chain -/-> mass rewrite
desired assertion value -/-> anchor for free variables
unanchored component + desired assertion -/-> concrete assignment
code edit -/-> implementation-choice by default
absence of confirmed product bug -/-> confirmed test-infra bug
absence of confirmed infra bug -/-> confirmed product bug
conflicting attribution with no deciding criterion -> ask when ask is available
ask available + remaining underdetermined target -> ask
disconfirmed proposed cause + past-incident/analogy-only support -> red for that proposed cause
unsupported positive test condition -> red for making that test green
successful classification -/-> green verdict by itself
unsupported forced binary decision -> red when ask is not available
```

Rules:

- If a chain of equalities or dependencies has no concrete anchored value, do not invent one to make a test green.
- If one connected component is anchored and another is not, fix only the anchored subset or ask before changing the unanchored subset.
- Do not solve for free variables from a desired assertion, expected value, or "make it green" goal; that is inventing a contract.
- If a passing assertion can be reached only by algebraically choosing values for an unanchored component, list that component in `underdetermined_targets` and choose `ask` when available.
- Treat `implementation-choice` as freedom to choose implementation form, not as a label for any code edit; a fully entailed value change can and should stay `proof-only`.
- Vague permission like "fix errors" does not grant `implementation-choice`; it only allows applying facts that are already proven for the exact local target.
- If any variable needed for a passing assertion belongs to an unanchored component, choose `ask` when `ask` is an available answer.
- If all required values are entailed by supported facts, the edit can remain `proof-only`; do not escalate to `implementation-choice`.
- If an assertion or expected value is contradicted by fully entailed facts and the task is to make the test match the entailed behavior, updating that expected value is allowed.
- If the prompt asks whether a test can be made green for a specific positive condition and that condition is unsupported or contradicted by known facts, choose `red`; do not use `ask` merely because an unrelated route or alternative state is underdetermined.
- If the prompt only asks to classify a failure and the classification is test-system/tooling error, choose `red` under default `green/red/ask`; do not use `green` to mean "the classification is true".
- If root cause is underdetermined and `ask` is an available outcome, ask instead of choosing product/test-infra by elimination.
- If the prompt proposes a specific classification only by past-incident analogy and current-run facts directly weaken that classification, reject that proposed classification as `red` even if the broader root cause remains open.
- The past-incident/analogy rule does not apply to a direct user attribution conflict such as "user claims test system" vs "runtime shows product validation"; that remains an attribution conflict requiring `ask` when available.
- If facts contain competing attributions, such as "user claims test system" and "runtime shows product validation error", treat that as a conflict to clarify when `ask` is available, unless the prompt asks only whether one unsupported attribution is safe to rely on.
- Do not use "runtime outweighs user" as a tie-breaker for product-vs-test-infrastructure attribution conflicts; without an accepted criterion it is a conflict, not a resolved classification.
- When the prompt asks to choose between `product` and `test infrastructure` and both appear as competing attributions, choose `ask` if available; do not encode "not test infra" as `red` unless the declared answer option means "reject this specific attribution".
- In `green/red/ask` decisions, if `ask` is present and the unresolved target is "is this product or test infrastructure?", verdict `red` is incorrect; use `ask` and list the attribution conflict in `underdetermined_targets`.
- Do not invent a "fix to green" decision target for a pure classification prompt that provides no code or test-edit request; use the prompt's actual target.
- If the user demands a decision but the proof is insufficient and `ask` is not available, reject the unsupported classification or broad rewrite.
- Do not treat runtime evidence as permission to ignore a conflicting user attribution unless the runtime artifact directly decides the asked question and scope.
- Do not expand a local hypothesis, local fix, or local guideline into a repo-wide sweep without supporting records or explicit scope.

## Public Reasoning Surfaces

This protocol never asks for hidden chain-of-thought.
It asks for short public, auditable surfaces.

Show a `Reasoning Checkpoint` before long analysis, tool-heavy investigation, plan changes, permission requests, and final answers with meaningful uncertainty:

```text
Reasoning Checkpoint:
- Goal: one sentence
- Anchors: CLM-/GLD-/MODEL-/FLOW-/PRP- ids or `none yet`
- Current inference: one sentence, marked tentative when applicable
- Next safe action: one sentence
- Concern: one sentence or `none`
```

Build an `Evidence Chain` before any non-trivial action, permission request, user-facing recommendation, or persistence into the TEP context:

```text
Evidence Chain:
- fact CLM-YYYYMMDD-xxxxxxxx: "short quote"
- observation CLM-YYYYMMDD-xxxxxxxx: "short quote"
- guideline GLD-YYYYMMDD-xxxxxxxx: "short quote"
```

Evidence chain rules:

```text
Reasoning Checkpoint -/-> proof
permission -> fact is forbidden
requested_permission -> fact is forbidden
restriction -> fact is forbidden
guideline -> fact is forbidden
proposal -> fact is forbidden
project/task/model summary/flow summary/open_question -> fact is forbidden
exploration_context -> fact is forbidden
broken chain means no action
```

When you already know the record refs but not the exact quotes, run
`augment-chain --file evidence-chain.json` to let the plugin fill canonical
quotes, public record metadata, source quotes, and validation output. Treat its
output as a mechanical projection over records, not as a new source of truth.

Before substantial code edits, show applicable guidelines:

```text
Guidelines:
- GLD-YYYYMMDD-xxxxxxxx: "short quote"
```

If no guideline applies, say `Guidelines: none found`.
After substantial code edits, include `Guidelines used:` with the used `GLD-* + quote`.

## Workflow Routing

Load the relevant workflow only when the trigger matches:

- [`workflows/information-lookup.md`](workflows/information-lookup.md): when searching, answering, investigating, or reconciling information
- [`workflows/before-action.md`](workflows/before-action.md): before planning, editing, running mutating commands, persisting records, or asking permission
- [`workflows/after-action.md`](workflows/after-action.md): after edits, tests, commands, discoveries, failed attempts, or completed work
- [`workflows/persistence-and-records.md`](workflows/persistence-and-records.md): when deciding whether and how to write TEP context records
- [`workflows/plugin-commands.md`](workflows/plugin-commands.md): when command names, strictness, hydration, or validation details are needed

Always prefer plugin commands over manual edits to canonical records when commands are available.
If commands are unavailable, follow the same semantics manually and state the limitation.

## Required Workflow

For project-claim work:

1. Hydrate the resolved TEP context before relying on persistent records.
2. Notice current project, current task, active permissions, active restrictions, active guidelines, active proposals, plans, debt, and conflicts.
3. If substantial work has no current task, start a task or state why no task is needed.
4. If intended work no longer matches the current `TASK-*`, pause/switch/start the correct task instead of silently drifting.
5. If beginning or switching to a substantial repeated `task_type`, review past precedents when available.
6. Search existing TEP context records before deriving from scratch.
7. Treat hook-captured `INP-*` records as prompt provenance, then classify incoming user messages, files, diffs, docs, outputs, logs, and memory records into appropriate `SRC-*`, `CLM-*`, `GLD-*`, `TASK-*`, `PRP-*`, or other records when they matter.
8. Reconcile new observations against existing supported/corroborated `CLM-*` records.
9. Publish a `Reasoning Checkpoint` before long or plan-changing analysis.
10. Build and validate an `Evidence Chain` before non-trivial action.
11. Act only on the subset allowed by strictness, permissions, restrictions, and required guidelines.
12. Persist reconstructable sources, claims, guidelines, restrictions, permissions, proposals, actions, models, flows, plans, debt, projects, tasks, and open questions when they will matter later.
13. Rehydrate when plugin hooks mark context stale.
14. Complete, pause, or stop the current task when done, deferred, or abandoned.

For small local actions, short form is allowed, but decisive ids and support edges must remain explicit.

If runtime hooks inject a TEP reminder, satisfy it with concrete panels and ids, not prose about the protocol.

## Response Pattern

When ambiguity or risk is present, prefer:

- `Reasoning Checkpoint`
- `Task Check`
- `Sources`
- `Claims`
- `Evidence Chain`
- `Guidelines`
- `Permissions / Restrictions`
- `Conflicts`
- `Decision`
- `Agent Proposal`
- `Open Questions`
- `Question for user`

For low-risk straightforward work, stay concise, but preserve decisive ids and quotes when relying on supported project claims.

Because plugin UI cannot add arbitrary custom chat components, use chat-native markdown panels.
Do not replace these panels with prose about the protocol.
