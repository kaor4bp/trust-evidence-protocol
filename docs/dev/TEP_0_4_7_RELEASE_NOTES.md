# TEP 0.4.7 Release Notes

TEP 0.4.7 removes the legacy evidence-chain reasoning ledger path.

## Changed

- `reason-step` now appends only `STEP-* entry_type=claim_step` entries over
  explicit `CLM-*` transitions.
- `validate-decision --chain ...` is read-only; it no longer has
  `--emit-permit`, `--kind`, or `--ttl-seconds`.
- The reason ledger validator accepts only `STEP-*` claim steps and `GRANT-*`
  grants. Legacy `REASON-*`, `AUTH-*`, `USE-*`, and `entry_type=step` entries
  are rejected instead of treated as compatible runtime state.
- `GRANT-*` creation requires a reviewed `STEP-* claim_step`.
- Hook/runtime guidance now points agents to `reason-step --claim CLM-*`
  followed by `reason-review --reason STEP-*`.

## Rationale

The 0.4 line now treats `CLM-*` as the semantic chain and `STEP-*` as the
agent-local cursor over that chain. Evidence-chain files remain useful for
read-only validation and presentation, but they are no longer a permit shortcut
or ledger object.
