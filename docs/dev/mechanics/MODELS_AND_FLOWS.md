# Models And Flows

## Responsibility

`MODEL-*` and `FLOW-*` provide compact integrated understanding so agents do not
re-read scattered claims.

## Model Rules

MODEL is derived.

It must not be based on tentative hypotheses, exploration context, runtime-only
observations, or navigation outputs. It should be based on supported or
user-confirmed theory claims.

## Flow Rules

FLOW describes movement across models and system states.

It should include model refs, preconditions, oracle, success/failure claims, and
contradictions or expected-vs-actual notes.

Contradictory flows should not be split by default. The system should surface
the contradiction and allow the user to confirm whether it is expected behavior.

## Ranking

Lookup should rank MODEL/FLOW above scattered CLM when they are current and
well-supported. This reduces token pressure and gives agents a coherent picture.

Resolved or stale bug observations should not outrank current theory models.

## API Requirements

- Promotion must validate authority source.
- Active/stable MODEL/FLOW cannot rely on hypothesis refs.
- FLOW preconditions and oracle may use observations during drafting, but stable
  FLOW requires theory/user confirmation.
- Lookup should tell agents that recurring hot CLM should be promoted into
  MODEL/FLOW when appropriate.

## Coherence Notes

- Curator mode should help build or refresh models and flows.
- Telemetry hot-record anomalies can suggest missing MODEL/FLOW.
- Formal logic projection can later check MODEL/FLOW consistency.

## Known Gaps

- "Supported theory" needs a sharper mechanical distinction from runtime
  corroboration.
- Flow contradiction handling needs examples where contradiction is normal after
  user confirmation.

