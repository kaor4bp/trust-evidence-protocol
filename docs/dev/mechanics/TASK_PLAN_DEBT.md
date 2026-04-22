# Task, Plan, Debt, And Autonomous Work

## Responsibility

This mechanic prevents agents from treating broad goals as executable work and
prevents autonomous tasks from ending by self-declaration.

## Task Shape

`TASK-*` can be:

- parent/orchestration task
- atomic leaf task
- decomposed task with child tasks

An atomic task must fit one working iteration and define deliverable, done
criteria, verification, boundary, and blocker policy.

Mutating work belongs on an atomic leaf task.

## Plans And Debt

`PLN-*` and `DEBT-*` are persistent operational records, not markdown backlog.

They should link to workspace/project/task and define enough status for
prioritization:

- active/proposed/blocked/done/cancelled status
- priority or severity
- owner/focus if relevant
- blockers
- verification or exit condition

## Autonomous Tasks

An autonomous task cannot end casually. A terminal response must state exactly
one outcome:

```text
TEP TASK OUTCOME: done
TEP TASK OUTCOME: blocked
TEP TASK OUTCOME: user-question
```

The runtime validates the outcome. `done` is invalid if linked blockers,
planned actions, unresolved debt, or open questions remain.

## API Requirements

- `preflight-task` should block planning/edit/action/final when current task is
  unconfirmed.
- Mutating action should require atomic leaf task.
- Autonomous stop guard should force continuation unless a valid terminal
  outcome is present.
- Task split tools should help the agent create subtasks and plans.
- Retrospective tools should surface previous tasks with similar type/scope.

## Coherence Notes

- REASON ledger is task-local and cannot parent across tasks.
- WCTX may be tied to one or more tasks; switching task may require WCTX fork.
- Curator tasks are organizational and may be long-running but still need a
  scoped pool and explicit outcome.

## Known Gaps

- "One working iteration" is partly subjective; tests need examples of too-broad
  tasks and acceptable atomic tasks.
- Finish-task validation needs clear treatment of low-priority debt: does it
  block `done`, downgrade outcome, or require explicit carry-forward?

