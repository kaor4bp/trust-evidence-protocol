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

```text
route / next_step -> lookup -> support capture -> REASON step/review -> action/final
```

Navigation output is not proof.
Proof requires canonical ids plus quotes and a valid provenance chain.

Normal graph direction:

```text
INP/FILE/ART/RUN -> SRC -> CLM -> MODEL/FLOW
TASK/PLAN        -> scope and decomposition
REASON           -> task-scoped reasoning step
GRANT            -> one-shot authorization bound to REASON/task/action/window
RUN              -> factual execution trace; using a grant means linking RUN.grant_ref
CIX              -> code navigation only
PRP              -> constructive agent proposal
```

`MODEL-*` and `FLOW-*` are compact derivative pictures.
They should rank above scattered claims, but they must come from supported or user-confirmed theory claims.

## Start Here

1. If unsure what to do, call `next_step` or CLI `next-step`.
2. If looking for facts, code, policy, or theory, call `lookup` first with a concrete reason.
3. If the route says task decomposition is missing, use `validate-task-decomposition`, `confirm-atomic-task`, or `decompose-task`.
4. If making or relying on a claim, use the support-capture API and then validate or augment the chain.
5. Before protected edits, model/flow updates, final autonomous completion, or permission-sensitive writes, create or reuse a `REASON-*` step and get it reviewed into a `GRANT-*`. Bash mutations need a command-bound `GRANT-*`.

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

For user-facing decisions, permission requests, edits, model/flow updates, and final claims, present a compact public chain:

```text
fact: CLM-* "quote" -> observation: SRC/RUN/INP/ART "quote" -> decision
```

Then run chain validation when the decision matters.
If the chain does not validate, do not treat the conclusion as proved.
Protected actions need a reviewed `REASON-*` ledger step, not just a loose chain file.
Bash authorization is append-only: `REASON-* -> GRANT-* -> RUN-*`.
`GRANT-*` is valid only for its task, mode, action kind, optional exact command, current context fingerprint, and configured time window.
Do not rely on mutable `used=true` state; a grant is considered consumed when a linked `RUN-*` or protected record exists.
Fork or roll back the reasoning ledger when observations change direction.

Hypotheses are allowed for exploration.
They must not become proof until supported.
Exploration hypotheses may guide lookup and probes; proof chains must reject unsupported hypotheses.

## Output Panels

Use short panels only when they help the user or the runtime requires them:

```text
Reasoning Checkpoint
Evidence Chain
Guidelines
Proposal
Open Questions
```

Keep them compact.
Prefer ids and quotes over prose.

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

## Documentation Boundary

This file is the agent mental model.
Command details belong in the plugin README, runtime help, and developer docs.
