---
modification_policy: Do not modify this file directly or indirectly without explicit user authorization.
name: trust-evidence-protocol
description: Evidence-first reasoning protocol for agents using TEP Runtime route, lookup, provenance, task decomposition, and chain validation APIs.
---

# Trust Evidence Protocol

TEP is not a long checklist for the agent to memorize.
Use the runtime API as the working path.
This skill only defines the mental model and the few obligations that remain on the agent.

## Mental Model

The agent may think freely, but durable work must pass through the graph API.
Treat navigation and reasoning as different planes.

```text
next_step
-> lookup or map navigation
-> drill-down/support capture
-> CLM-* plus relation CLM-*
-> STEP-* claim-step ledger
-> optional GRANT-* / RUN-* / final answer
```

Navigation output is not proof.
Proof requires canonical ids plus quotes and a valid provenance chain.

`lookup` is the direct retrieval path when you know what you need.
Map/curiosity tools are the broader signal path when you need a cognitive map:
anchors, ignored-but-relevant facts, bridges, tensions, tap smell, cold zones,
and code/backend signals. These signals guide attention only; they must be
drilled down into canonical records before they can enter a `STEP-*`.

Normal graph direction:

```text
INP/FILE/ART/RUN -> SRC -> CLM -> MODEL/FLOW
CLM relation     -> directional semantic edge between CLM records
TASK/PLAN        -> scope and decomposition
STEP             -> task/WCTX-scoped claim-step over connected CLM records
GRANT            -> one-shot authorization bound to STEP/task/action/window
RUN              -> factual execution trace; using a grant means linking RUN.grant_ref
MAP/CIX/backend  -> navigation and signal surfaces only
PRP              -> constructive agent proposal
```

`MODEL-*` and `FLOW-*` are compact derivative pictures.
They should rank above scattered claims, but they must come from supported or user-confirmed theory claims.

## Start Here

1. Invent a private per-agent key at the start of a work session and reuse it for every mutating MCP call as `agent_private_key`, or expose it to CLI/hooks as `TEP_AGENT_PRIVATE_KEY`. Do not share this key with another agent.
2. If unsure what to do, call `next_step` or CLI `next-step`. Read the briefing before acting: it includes the current `STEP-*` cursor and a non-authoritative rights snapshot. `next_step` and `lookup` are always allowed entrypoints; protected writes, mutating bash, and autonomous `done` still need a valid reviewed `STEP-*`/`GRANT-*` checked at use time.
3. If looking for facts, code, policy, or theory, call `lookup` first with a concrete reason. If you do not know what is important yet, use map/curiosity navigation to inspect anchors, bridges, ignored facts, and tap smell. If a current `STEP-*` exists, lookup and map drill-down should prefer records that can extend or safely fork the CLM chain.
4. If the route says task decomposition is missing, use `validate-task-decomposition`, `confirm-atomic-task`, or `decompose-task`.
5. If making or relying on a claim, use the support-capture API. If the next step depends on a previous claim, record an explicit relation CLM such as `supports`, `causes`, `depends_on`, `implies`, or `refines`.
6. Before planning continuation or final answers for an active task, append a relevant `STEP-*` claim step through `reason_step`/`reason-step`. Before protected edits, model/flow updates, autonomous `done`, or permission-sensitive writes, get the relevant `STEP-*` reviewed into a `GRANT-*`. Bash mutations need a command-bound `GRANT-*`.

Do not browse raw records as the normal path.
Use lookup, record detail, linked records, graph/map views, and chain tools.

## Task Rule

Work must be scoped to a valid task.

- A parent `TASK-*` is orchestration only.
- Mutating work belongs on an atomic leaf `TASK-*`.
- A task is not ready for work until it is explicitly `atomic` or `decomposed`.
- A leaf task must fit one working iteration and define deliverable, done criteria, verification, scope boundary, and blocker policy.
- A parent task must have valid child tasks.
- Plans are optional, but when used they follow the same atomic/decomposed split.

If the current task is wrong, stale, or too broad, switch, fork, pause, or decompose it before writing durable records.

## Provenance Rule

Do not create truth directly.

The agent supplies intent and support:

- user input or prompt reference
- file/URL/path plus lines and quote
- command run plus captured output
- artifact reference and quote

The runtime should create or connect the proper graph records.
When graph-v2 support is available, `SRC-*` must be backed by `INP-*`, `FILE-*`, `ART-*`, or `RUN-*`; runtime claims must transitively reach `RUN-*`.

During transition, prefer `record-support` or `record-evidence` over manual `record-source` or `record-claim`.
Manual low-level record creation is for plugin development or migration only.

## Reasoning Rule

For user-facing decisions, permission requests, edits, model/flow updates, and final claims, advance through connected CLM records:

```text
prev CLM-* -> relation CLM-* -> next CLM-*
```

The relation is itself a `CLM-* claim_kind=relation` record.
If the relation does not exist, record it or stop; do not pull a sudden fact into the ledger.
The ledger validates that a new step continues the current CLM graph coherently.
It rejects unsupported jumps, two tentative hops in sequence, navigation-only
relations for proof/action modes, duplicate mechanical reuse, and same-kind
relation cycles in one branch.
Protected actions need a reviewed `STEP-*` ledger step from a valid CLM transition, not just a loose chain file.
Planning continuation for an active task needs a valid `STEP-*` whose transition still validates for `planning`.
Final answers for an active task need a reviewed `STEP-* mode=final`; autonomous `TEP TASK OUTCOME: done` also needs a fresh `GRANT-* mode=final`.
Bash authorization is append-only: `STEP-* -> GRANT-* -> RUN-*`.
`GRANT-*` is valid only for its task, mode, action kind, optional exact command, current context fingerprint, and configured time window.
Do not rely on mutable `used=true` state; a grant is considered consumed when a linked `RUN-*` or protected record exists.
Use `STEP-*` as the task/WCTX-local ledger of justified CLM traversal, not just as a grant prelude.
When your interpretation changes, append a new claim step with a relation CLM and `reason`; when exploring an alternative, fork with an explicit previous step and branch.
Do not reuse the same claim as a mechanical permit; same-mode continuation must advance through a connected relation or fork a named alternative branch.
Fork or roll back the reasoning ledger when observations change direction.

Hypotheses are allowed for exploration.
They must not become proof until supported.
Exploration hypotheses may guide lookup and probes; proof/action modes must reject tentative claims and `co_relevant` navigation relations.

Refutation is first-class. If new evidence weakens or contradicts a claim, do
not hide it in prose. Record or reuse the conflicting `CLM-*`, link it with
`contradiction_refs`, `comparison`, or `meta_conflict`, then advance the
`STEP-*` chain through the explicit relation/status change. Use `contested`
while conflict is unresolved and `rejected` when stronger support wins.

## Autonomous Tasks

If the active `TASK-*` is autonomous, do not end casually.
Continue working unless one terminal outcome is mechanically true:

```text
TEP TASK OUTCOME: done
TEP TASK OUTCOME: blocked
TEP TASK OUTCOME: user-question
```

The Stop hook validates the marker.
`done` cannot leave linked obligations open.
`blocked` needs a linked blocker.
`user-question` needs a linked open `OPEN-*`.

## Hard Stops

Stop and use the runtime route when:

- there is no resolved workspace/project/task focus
- hydration is stale before a decisive action
- the current task is not an atomic leaf for mutating work
- a claim lacks source-backed support
- a runtime claim lacks runtime provenance
- a guideline, restriction, or permission boundary is unclear
- lookup and known records disagree
