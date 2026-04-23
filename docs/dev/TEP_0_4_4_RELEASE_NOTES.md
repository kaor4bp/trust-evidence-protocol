# TEP 0.4.4 Release Notes

## Summary

TEP 0.4.4 tightens the `STEP-*` claim-step ledger graph validator.
Before appending a new claim step, the runtime now validates the current
branch plus the candidate relation edge as one directed CLM graph.

## Changes

- Blocks proof-capable relation cycles in one `STEP-*` branch, not only direct
  inverse edges. A candidate `CLM-A -> CLM-B` is rejected when the same branch
  already contains a same-kind path `CLM-B -> ... -> CLM-A`.
- Returns structured JSON repair hints for failed `reason-step --format json`
  and MCP `reason_step format=json` calls. The payload includes the candidate
  relation, existing path refs, existing relation refs, and a fork suggestion.
- Keeps `co_relevant` navigation relations out of proof graph cycle checks.

## Migration Notes

No record migration is required. Existing ledgers that contain same-kind
relation cycles will now fail state validation until the branch is forked or
the relation CLMs are revised.

