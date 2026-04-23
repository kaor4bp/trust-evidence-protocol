# Reason Ledger, Grants, And Runs

## Responsibility

This mechanic turns validated reasoning into an append-only task-local,
agent-owned ledger and uses that ledger to authorize protected actions.

## Ledger Shape

`STEP-* entry_type=claim_step` records reasoning progression under the local agent identity.
The 0.4 runtime writes one ledger per agent:

```text
runtime/reasoning/agents/AGENT-*/reasons.jsonl
```

Rules:

- task-local
- agent-owned; current entries carry the ledger `agent_identity_ref`
- workspace/project/task bound
- claim-step chain
- branch labels for alternatives
- no cross-task parents
- direct same-mode continuation cannot reuse the same parent claim on the same
  branch; it must advance through an explicit relation `CLM-*`
- hash-chain seal and weak proof-of-work detect rewriting

The ledger is not canonical truth. It is runtime control evidence. A valid
ledger proves that the agent produced an untampered, owner-bound, mode-valid
CLM traversal. It does not prove semantic correctness, optimality,
or that no better interpretation was available.
Current claim steps carry `justification_valid` and `decision_chain_valid` for
that mode-valid CLM traversal; `decision_valid` is only a compatible API alias.

The ledger also functions as task-local working-memory pressure. Each step
forces the agent to attach its next move to cited facts, observations, marked
hypotheses, or an explicit fork. The runtime can verify that structure and
progression, but it cannot verify that the agent chose the globally best
reasoning path.
`next-step` and `lookup` expose `start_briefing` and `reason_pressure` to make
that pressure visible before work starts: agents see the current branch, recent
reason steps, recent actions/runs, a compact rights snapshot, and whether the
next cheap move is lookup or `reason_step`.
The rights snapshot is advisory only. It must always show `next_step` and
`lookup` as allowed entrypoints, but protected actions still validate against
the current runtime grant state at use time.

## Planning And Final Gates

- Planning continuation requires a current valid `STEP-*` for the active task.
- Meaningful test/verification runs should have a current `STEP-* mode=test`
  unless they are trivial local probes with no task consequence.
- Final response requires `STEP-* mode=final`.
- Autonomous `done` requires final reason and `GRANT-* mode=final`.
- Lookup/read/reasoning can happen before a reason step so the agent can gather
  material.
- Interrupted work without final reason is resumable.

## Grants

`GRANT-*` is authorization, not reasoning.

```text
STEP-* -> GRANT-* -> RUN-* / protected write
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
- `reason-step` appends only reviewed steps from chains that validate for the
  requested mode; justification-invalid chains must be fixed before ledger
  write.
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
