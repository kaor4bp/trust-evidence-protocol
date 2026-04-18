# After Action Workflow

Use this workflow after edits, tests, commands, discoveries, failed attempts, permission grants, or completed work.

## Immediate Review

After a meaningful command or edit:

1. Classify the output or diff as source material.
2. Decide whether it creates, confirms, narrows, contests, rejects, or supersedes a `CLM-*`.
3. Decide whether an old true claim became resolved/historical and should be fallback-only.
4. Check whether dependent `MODEL-*` or `FLOW-*` records became stale.
5. Check whether plans, debt, open questions, proposals, permissions, restrictions, or guidelines need updates.
6. Rehydrate if hooks or mutating commands marked context stale.

## After Code Edits

After substantial code edits, include:

```text
Guidelines used:
- GLD-YYYYMMDD-xxxxxxxx: "short quote"
```

Then persist when useful:

- `SRC-*` for relevant diffs, command outputs, logs, or user instructions
- `CLM-*` for observed code/runtime/theory facts
- `ACT-*` for meaningful executed or planned operations
- `GLD-*` for reusable coding/test/review/debugging rules
- `DEBT-*` for known cleanup or validator gaps
- `PLN-*` for durable follow-up plans
- `OPEN-*` for unresolved concerns
- `PRP-*` for constructive critique and solution alternatives

If a previously high-trust claim no longer reproduces, use `resolve-claim` rather than leaving it active or deleting it.

## Test And Runtime Outputs

- A test pass is runtime evidence, not semantic proof by itself.
- A failing test is a runtime observation and may support a claim about current behavior.
- A command error is source material; do not discard it if it changes the plan.
- If runtime output contradicts theory or code-plane claims, mark the conflict instead of smoothing it over.
- If runtime output shows a historical failure no longer reproduces, resolve the old claim and record the new observation separately when it matters.

## Completion

Before final response after substantial work:

- show a final `Reasoning Checkpoint` when uncertainty or tradeoffs mattered
- summarize decisive claims and observations with ids when records exist
- list `Guidelines used:` when code changed substantially
- mention unresolved conflicts, open questions, debt, and residual risk
- include relevant `PRP-*` recommendation or alternatives when the work exposed a meaningful tradeoff
- complete or stop the current `TASK-*` when lifecycle ends

## Optional Retrospective

Use retrospective thinking when it can change future work, not after every small action.
Do it when completing substantial tasks, changing direction after failed attempts, discovering a prior assumption was wrong, handing work to another agent/thread, or when the user asks why a decision was made.

Retrospective should answer:

- what the task/action intended
- which `TASK-*`, `ACT-*`, `PLN-*`, `PRP-*`, `DEBT-*`, `MODEL-*`, `FLOW-*`, `CLM-*`, and `GLD-*` shaped the decision
- which assumptions held, weakened, or failed
- which records should be updated so the next agent does not reconstruct the same path from chat

Before starting a substantial task type that has past examples, use `review-precedents` to inspect prior `TASK-*` records of the same `task_type`.

## Do Not Lose Context

Do not leave durable discoveries only in chat.
If a future agent would benefit from the result, write or update records.
If the information is too large, store an artifact and reference it from records.
