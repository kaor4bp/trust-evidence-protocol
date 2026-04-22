# Controls, Proposals, And Curator

## Responsibility

This mechanic controls action boundaries and gives agents a safe place to
criticize, organize, and propose alternatives.

## Controls

- `PRM-*`: permission boundary
- `RST-*`: restriction or prohibition
- `GLD-*`: operational guideline

Controls can be global, project-scoped, or task-scoped. They guide or block
actions. They do not prove factual claims.

Agents should cite guideline ids and quotes before substantial code edits.

## Proposals

`PRP-*` is constructive criticism and solution options.

Use proposal when the agent disagrees with user direction, implementation looks
risky, current model is likely incomplete, or user rejects an agent concern but
the concern may matter later.

Proposal should cite claims/models/flows/guidelines/open questions when
possible, but it may contain bounded agent judgment.

## Curator

Curator is an organizational mode for context hygiene.

Curator receives a pool of records. It should not roam all records directly.

Responsibilities:

- find duplicates
- find contradictions
- propose MODEL/FLOW updates
- identify stale/resolved claims
- prepare user questions
- link related records
- create proposals when the knowledge shape looks wrong

Curator may talk to the user. It is not a code execution role.

## API Requirements

- Curator needs a dedicated entry point that returns a bounded pool and expected
  outputs.
- Curator output should be records or review reports, not unstructured prose.
- Proposal creation should be easy enough that agents do not drop critique.
- Guideline creation by agent should require user confirmation before active
  use.

## Coherence Notes

- Curator can feed cleanup, MODEL/FLOW, and map curiosity.
- Proposal is not proof, but it can guide future lookup.
- Restrictions must be checked by preflight gates.

## Known Gaps

- Curator pool scoring and chunking is not fully specified.
- Proposal lifecycle needs close/accept/reject semantics that do not create
  stale noise.

