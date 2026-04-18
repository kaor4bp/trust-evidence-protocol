# Before Action Workflow

Use this workflow before planning, editing, running mutating commands, persisting records, asking permission, or making a substantial recommendation.

## Preflight

1. Hydrate the resolved TEP context root if it exists and is stale or missing; prefer `~/.tep_context` over legacy repo-local `.codex_context`.
2. Notice the current `PRJ-*`, current `TASK-*`, active `PRM-*`, active `RST-*`, active `GLD-*`, active `PRP-*`, plans, debt, and conflicts.
3. Notice active `WCTX-*` working contexts and whether their pinned refs/focus paths match the intended work.
4. If substantial work has no current task, start a task or state why no task is needed.
5. If the intended work may not match the current task, run or emulate `task-drift-check`.
6. If work has drifted, pause/switch/start the appropriate task before continuing, or ask the user.
7. If starting a substantial task type that has past examples, run `review-precedents`.
8. Check whether the action is local, project-scoped, or task-scoped.
9. Check `allowed_freedom`.

## Planning And Reasoning

- Use compact `brief-context --task "..."` before planning substantial work; request `--detail full` only when compact context is insufficient.
- Use `working-context show` when the current task has pinned refs, focus paths, or local assumptions that affect continuity.
- Use `topic-search` only to find candidate records faster; do not use topic overlap as proof.
- Use `logic-check` when the decision depends on typed predicate facts or rules; do not use logic-index output as proof without underlying `CLM-*` / `SRC-*`.
- Use `review-precedents` before repeating a substantial task type such as investigation, implementation, review, debugging, refactor, migration, test-writing, or release.
- Use `build-reasoning-case` when a decision spans multiple claims, models, flows, or derived layers.
- Treat `Fallback Historical Facts` from `brief-context` as background only unless no active record answers the task or the user explicitly asks about history.
- Show a `Reasoning Checkpoint` before long analysis, multi-tool batches, plan changes, permission requests, or substantial edits.
- Build an `Evidence Chain` before non-trivial action or recommendation.
- Validate the chain mechanically when possible.

## Before Code Edits

Show applicable guidelines before planning substantial code edits:

```text
Guidelines:
- GLD-YYYYMMDD-xxxxxxxx: "short quote"
```

If no guideline applies, say:

```text
Guidelines: none found
```

Then verify:

- no active hard restriction blocks the edit
- required guidelines are compatible with the planned implementation form
- preferred guidelines are followed unless a stronger scoped reason exists
- the action is inside the current task/project boundary
- the edit is supported by `CLM-*` facts or explicitly allowed by the current freedom mode
- fallback/historical/archived claims are not being used as current action justification

## Evidence-Authorized Mutation

Under `evidence-authorized`, mutating action is allowed only when:

- hydration is fresh and conflict-free for the relevant plan/action boundary
- an active `TASK-*` exists
- the action is safe or guarded, not unsafe/destructive
- no active hard restriction blocks it
- a valid evidence chain exists
- the executed or intended action is recorded as `ACT-*`

The agent must not self-escalate `allowed_freedom`.
If higher strictness is needed, create a strictness request, show the exact `TEP-APPROVE REQ-*` line to the user, and stop until the user sends that approval.
Existing `PRM-*` records or broad task permission are not enough to change strictness upward.

## Permission Requests

When asking the user for permission:

- show what is known
- show what is not known
- show the evidence chain or explain why mechanical validation is unavailable
- make the requested grant narrow and reconstructable
- use temporary `REQ-*` ids in the public chain when a `PRM-*` record does not yet exist
- after the user grants permission, record it as `PRM-*` when it will matter later

## Stop Conditions

Stop or ask before acting when:

- the evidence chain is broken
- the action depends on an unsupported or underdetermined step
- a restriction blocks the intended action
- a required guideline conflicts with the implementation form
- the agent would need to invent API, domain semantics, product behavior, or concrete values
- the only support is memory, generated views, task context, or proposal assumptions
- the only support is `WCTX-*` focus context or `topic_index` overlap
- the only support is generated `logic_index` output rather than underlying source-backed claims
- the current task is drifted and the agent has not paused/switched/started the right task
