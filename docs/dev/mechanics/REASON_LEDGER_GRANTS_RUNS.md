# Reason Ledger, Grants, And Runs

## Responsibility

This mechanic turns validated reasoning into an append-only task-local,
agent-owned ledger and uses that ledger to authorize protected actions.

## Ledger Shape

`REASON-*` records reasoning progression under the local agent identity.
The 0.4 runtime writes one ledger per agent:

```text
runtime/reasoning/agents/AGENT-*/reasons.jsonl
runtime/reasoning/agents/AGENT-*/seal.json
```

The old shared `runtime/reasoning/reasons.jsonl` path is migration input only.

Rules:

- task-local
- agent-owned; current entries carry the ledger `agent_identity_ref`
- workspace/project/task bound
- parented DAG
- branch labels for alternatives
- no cross-task parents
- direct same-mode continuation cannot reuse the same parent chain hash on the
  same branch
- hash-chain seal and weak proof-of-work detect rewriting

The ledger is not canonical truth. It is runtime control evidence.

The ledger also functions as task-local working-memory pressure. Each step
forces the agent to attach its next move to cited facts, observations, marked
hypotheses, or an explicit fork. The runtime can verify that structure and
progression, but it cannot verify that the agent chose the globally best
reasoning path.

## Planning And Final Gates

- Planning continuation requires a current valid `REASON-*` for the active task.
- Final response requires `REASON-* mode=final`.
- Autonomous `done` requires final reason and `GRANT-* mode=final`.
- Lookup/read/reasoning can happen before a reason step so the agent can gather
  material.
- Interrupted work without final reason is resumable.

## Grants

`GRANT-*` is authorization, not reasoning.

```text
REASON-* -> GRANT-* -> RUN-* / protected write
```

Grant checks bind mode, action kind, workspace/project/task, context
fingerprint, time window, and optional command hash/cwd.

Grant consumption is inferred from linked `RUN-*` or protected records. Do not
mutate ledger entries with `used=true`.

## Runs

`RUN-*` captures command execution. Runtime claims derived from commands must
transitively reach RUN.

## API Requirements

- Hooks must block direct runtime ledger writes.
- `reason-step` appends reviewed or draft steps based on chain validation.
- `reason-review --grant` creates `GRANT-*`.
- PreToolUse must enforce grant policy for protected actions.
- PostToolUse should record or connect `RUN-*` for mutating shell commands when
  possible.

## Coherence Notes

- Task focus drift invalidates reason/grant use.
- Lookup extension exists to make honest REASON progression easier than bypass.
- Evidence chain validators provide the semantic boundary; ledger validation
  provides append-only integrity.
- REASON progression is a discipline mechanism: it should improve the agent's
  local context formation, not pretend to certify thought quality.

## Known Gaps

- Weak proof-of-work is friction, not security. It should not be described as a
  sandbox boundary.
- Final response enforcement depends on hooks; CLI-only paths need equivalent
  command discipline.
- The policy for non-Bash protected writes should be explicit per tool.
