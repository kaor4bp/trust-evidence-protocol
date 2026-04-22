# Workspace, Project, Task, And WCTX Focus

## Responsibility

This mechanic prevents agents in one context from accidentally treating another
workspace, project, or task as their own.

Global current focus is not a reliable operating model. TEP should require a
workspace anchor for normal work.

## Focus Hierarchy

```text
WSP-* -> PRJ-* -> TASK-*
WSP-* -> WCTX-*
```

Rules:

- Every durable record should have `workspace_refs`, except explicit legacy or
  migration records.
- A record may have no `project_refs` only when it truly spans projects or is
  workspace-level.
- Local `.tep` anchors select the focus for a working directory.
- Hydration must display workspace, project, task, active restrictions, and
  active guidelines.
- WCTX is agent-owned operational context and cannot prove truth.

## Workspace Admission

When a user asks the agent to inspect another repository, the agent must not
silently add it to the current workspace.

Expected route:

```text
workspace-admission(repo)
-> ask: new workspace, add project to current workspace, or inspect read-only
```

## WCTX Behavior

`WCTX-*` should be cheap for agents to create. It stores current investigation
focus, assumptions, concerns, topic seeds, and relevant task/project links.

It is not user policy and not truth. It is a routing and retrospective anchor.

## API Requirements

- Hydration should fail or warn hard when active workspaces exist and no
  workspace anchor is present.
- MCP and CLI must resolve paths relative to the caller cwd, not their own
  process cwd.
- Lookup should require WCTX or auto-create one only when workspace focus is
  explicit.
- Task switching should trigger drift checks and may fork/close WCTX.

## Coherence Notes

- REASON steps bind to workspace/project/task and current fingerprint.
- Grants bind to the same focus, so focus drift invalidates protected actions.
- Curator mode must not rely on local `.tep` focus; it receives an explicit pool.

## Known Gaps

- The migration rule for records spanning multiple workspaces needs a stable
  merge policy.
- WCTX creation is agent-owned, but the exact threshold for creating vs reusing
  a WCTX still needs product tuning.

