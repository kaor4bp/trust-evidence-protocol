# TEP 0.4.6 Release Notes

## Summary

TEP 0.4.6 removes the compatibility alias that exposed the current `STEP-*`
cursor as `current_reason_ref` in normal agent-facing route payloads.

## Changes

- `next_step.start_briefing` now exposes `current_step_ref` and
  `expected_step_mode`.
- `lookup.chain_starter.chain_extension` now exposes `current_step_ref` and
  `current_step_mode`.
- Normal lookup chain-starter commands no longer advertise the legacy
  `augment-chain` fallback path.
- Contract descriptions and docs now describe `STEP-*` as the route cursor
  without `current_reason_ref` compatibility wording.

## Migration Notes

This is an intentional breaking change for pre-release consumers. Update callers
that read `current_reason_ref` or `current_reason_mode` to read
`current_step_ref` or `current_step_mode`.

