# TEP API-First Contract

TEP should not depend on agents remembering a long behavioral manual.
The skill gives the mental model; the runtime API supplies routes, proof
boundaries, validation, and write contracts.

## Design Direction

Normal agent flow is:

```text
next-step(intent, task)
-> lookup(query, reason, kind)
-> drill down with returned route commands
-> record-evidence / augment-chain / validate-* when the result matters
-> task-outcome-check before autonomous task termination
```

The agent may reason freely between calls, but durable conclusions and
user-facing decisions must pass through the mechanical API.

## Lookup As Front Door

`lookup` is the normal entry point for facts, code, theory, research, and policy.
It returns:

- `api_contract_version`
- `primary_tool`
- `route`
- `next_allowed_commands`
- `route_graph`
- `evidence_profile`
- `output_contract`

`search-records`, `claim-graph`, `record-detail`, and `linked-records` are
drill-down tools after `lookup`, not the preferred first move for normal work.
They remain available for plugin development, migration, forensics, and targeted
follow-up.

## Evidence Profile

Lookup output is navigation, not proof.

The expected read order is:

1. `MODEL-*` / `FLOW-*` for compact integrated picture
2. active corroborated/supported `CLM-*` through compact graph lookup
3. `record-detail` / `linked-records` for proof quotes
4. tentative hypotheses for exploration only
5. resolved/historical fallback only after active records fail

Raw `records/claim/*.json` reads are an escape hatch, not a normal route.

## Output Contract

The runtime should tell the agent what it may do next.

Required contract shape:

```json
{
  "api_contract_version": 1,
  "next_allowed_commands": ["..."],
  "route_graph": {"graph_version": 1, "branches": []},
  "evidence_profile": {"lookup_is_proof": false},
  "output_contract": {
    "if_answering": "...",
    "if_new_support_found": "...",
    "if_chain_needed": "...",
    "if_theory_should_rank_high": "...",
    "if_uncertain": "..."
  }
}
```

This reduces token pressure: the agent chooses from returned routes instead of
reconstructing policy from prose.

## Mechanical Write Path

Common evidence writes should use `record-evidence`.

The agent supplies a concrete support surface:

- file path, line/range, and quote
- command and quoted output
- user confirmation input and quote
- artifact ref and quote

The API creates the `SRC-*` and optional `CLM-*`, links `INP-*` when provided,
and refreshes generated views.

Manual `record-source` / `record-claim` remains for advanced fields such as
logic projections, migration repair, comparison metadata, or source-only staging.

## Model And Flow Priority

`MODEL-*` and `FLOW-*` are prioritized in lookup because they are compact,
derived pictures over claims.

They must not be created from tentative or runtime-only observations.
Promotion requires supported/user-confirmed theory claims. This keeps an agent's
useful hypotheses possible while preventing unsupported guesses from becoming
the shared model of the world.

## Skill Boundary

`SKILL.md` should stay short enough to act as a mental model:

1. Start from `next-step` / `lookup`.
2. Treat lookup output as navigation.
3. Present ids and quotes for proof.
4. Use `record-evidence` for reusable support.
5. Use `augment-chain` / `validate-*` before decisive action.
6. Promote durable integrated understanding into `MODEL-*` / `FLOW-*` only
   through validated write paths.

Detailed command semantics belong in README, workflow docs, and runtime help.

## Autonomous Task Outcomes

Autonomous task termination is not a bare marker.

`TEP TASK OUTCOME: done|blocked|user-question` is accepted only after
`task-outcome-check` verifies linked task obligations:

- `done` requires no linked blocking `OPEN-*`, `PLN-*`, `DEBT-*`, or planned `ACT-*`
- `blocked` requires a linked open question, active/proposed/blocked plan, unresolved debt, or planned action
- `user-question` requires a linked open `OPEN-*`

`complete-task` applies the same `done` check for autonomous tasks.
