# Tick-Tock Adoption Contract

This document defines the minimum operating contract for using TEP to develop
the next TEP version.

The goal is not to make the current plugin perfect. The goal is to make it safe
enough that an agent can switch to the next plugin version and use that version
to develop the following one.

## Policy

TEP development follows a tick-tock loop:

1. `tick`: use the current installed plugin to develop and validate the next
   plugin version.
2. Publish or install the next plugin version.
3. Merge current local context into the unified TEP context.
4. `tock`: switch the agent to the next plugin version and continue from the
   merged context.
5. Repeat, using feedback from real agents as first-class maintenance input.

The loop is acceptable only when switching does not erase evidence, current
task state, open questions, known debt, or plugin feedback.

## Readiness Gates

A plugin version is switch-ready when all of the following hold:

- deterministic default tests pass without live-agent tests
- selected targeted tests for the edited feature pass
- strict context validation and review pass for the development context
- the installed plugin can hydrate the target context
- the plugin documents any new commands in README and skill workflows
- agents can record plugin feedback without manually editing JSON
- current local records can be merged into the unified context with a dry-run
  report before apply

Full live-agent Docker tests are optional for every small iteration, but they
remain the best isolation boundary before a major switch or public release.

## Context Roots

The target live root is the unified global context:

```text
~/.tep_context
```

Legacy repo-local context roots are still valid migration sources:

```text
.codex_context
```

Runtime resolution order is:

1. explicit `--context`
2. `TEP_CONTEXT_ROOT`
3. existing `~/.tep_context`
4. nearest legacy `.codex_context`
5. default `~/.tep_context`

Agents should prefer explicit `--context` during migration and debugging. After
switching, normal operation should use `~/.tep_context` unless a test fixture or
repository-local experiment intentionally uses another root.

## Merge Contract

The merge command must be conservative. It should preserve canonical records and
avoid inventing truth.

Required behavior:

- support `--dry-run` and `--apply`
- read one or more source context roots
- write to an explicit target context root
- create a restorable backup or report before mutating the target
- preserve record ids when the target does not already contain that id
- deduplicate identical records by content hash when ids collide
- allocate a new id when the same id has different content
- record origin metadata for records whose id changed during merge
- copy artifacts by content hash or collision-safe path
- skip generated views and rebuild them after merge
- never blindly import `current_task_ref`, `current_project_ref`, strictness, or
  hook settings over the target settings
- print a human-readable report of copied, deduplicated, remapped, skipped, and
  conflicted items

Generated directories such as `review/`, `runtime/`, `topic_index/`,
`logic_index/`, and `code_index/` are rebuildable. Canonical JSON records and
artifacts are not rebuildable and must be handled first.

## Feedback Loop

Real agents must be able to report plugin problems into context without editing
JSON directly.

Use:

```bash
python3 plugins/trust-evidence-protocol/scripts/context_cli.py record-feedback \
  --scope "tep.plugin" \
  --kind false-positive \
  --surface hook \
  --severity high \
  --title "Read-only command was blocked" \
  --actual "The hook classified rg as a mutating write." \
  --expected "Read-only search should pass without strictness escalation." \
  --repro "Run rg over plugin docs." \
  --suggestion "Classify shell commands by parsed operation, not path substrings."
```

`record-feedback` creates:

- `SRC-*` with `source_kind=memory` and `origin.kind=agent-feedback`
- `DEBT-*` with `tags=["feedback", "feedback:<kind>", "surface:<surface>"]`

This keeps feedback visible to existing backlog, search, review, and debt
tooling without introducing a separate `FDB-*` record type before it is needed.

Supported feedback kinds:

- `bug`
- `friction`
- `false-positive`
- `false-negative`
- `docs-gap`
- `performance`
- `missing-tool`
- `policy-conflict`
- `migration-issue`
- `other`

Supported surfaces:

- `cli`
- `hook`
- `mcp`
- `skill`
- `docs`
- `context-merge`
- `code-index`
- `reasoning`
- `runtime`
- `other`

Feedback is not proof that the plugin is wrong. It is an agent-authored source
plus a durable debt item. Maintainers must inspect evidence, reproduce when
needed, and then resolve, schedule, or reject the debt.

## Switching Procedure

Before switching an agent to the next plugin version:

1. Run deterministic tests and targeted tests for the changed feature.
2. Validate and review the current context.
3. Record unresolved plugin friction with `record-feedback`.
4. Dry-run context merge into `~/.tep_context`.
5. Apply merge only when the report is understandable and reversible.
6. Install the next local plugin version with `./scripts/install-local-plugin.sh`
   or publish it through the intended release channel.
7. Start a new task under the next version and hydrate from `~/.tep_context`.
8. Ask the new agent to inspect active feedback/debt before planning the next
   implementation slice.

The switch is intentionally explicit. Silent migration is risky because context
records carry permissions, restrictions, tasks, plans, debt, and agent feedback.
