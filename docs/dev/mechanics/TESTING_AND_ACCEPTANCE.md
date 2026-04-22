# Testing And Acceptance

## Responsibility

This mechanic defines what must be proven before the 0.4.0 mechanics are
trusted.

## Deterministic Tests

Required coverage:

- context validation
- hydration and focus display
- workspace admission and local `.tep` anchors
- task confirmation and decomposition
- autonomous stop outcomes
- lookup route graph
- lookup chain extension and fallback
- evidence chain role/quote validation
- hypothesis mode acceptance/rejection
- REASON DAG parent/fork/progression
- duplicate chain rejection
- final reason gating
- GRANT/RUN protected action lifecycle
- MODEL/FLOW authority boundary
- CIX navigation boundary
- backend status honesty
- map graph shape and HTML stability
- telemetry counters and hints
- cleanup candidate staging

## Live-Agent Docker Tests

Live tests should prove that real agents follow the route, not that the model
already knows the answer.

Scenarios:

- route-retrospective pathfinding with unknown shorter route
- layered route observations from people with different speeds
- five daughters allowance multiple-choice hypothesis task
- Facility/Program relation discovery
- resolved bug reappears with same-bug vs new-bug hypotheses
- curator pool review
- hook-blocked mutation repaired by reason/grant route

Live-agent runs are expensive. Full runs require explicit user instruction
during beta.

## Acceptance Criteria

0.4.0 is ready when lookup is the front door, planning/final/action gates use
valid REASON/GRANT/RUN paths, workspace focus is explicit, navigation outputs
stay navigation, MODEL/FLOW promotion is protected, telemetry exposes bypasses,
deterministic tests pass, and explicit live smoke proves route mechanics.

## Known Gaps

- Live-agent harness needs stable assertions over actual TEP artifacts, not only
  text markers.
- We need negative live tests where the wrong behavior is tempting.

