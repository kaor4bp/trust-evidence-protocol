# TEP 0.4.11 Release Notes

TEP 0.4.11 separates operational hydration/reindex validation from full audit.

## Changed

- Added an `operational` validation mode for state checks.
- `hydrate-context` now ignores foreign invalid `AGENT-*` and foreign owner-bound
  `WCTX-*` records while validating the current agent's working state.
- `reindex-context` now uses the same operational profile, so it can refresh
  generated artifacts without being blocked by unrelated broken agent records.
- Full audit commands and full state validation still see invalid foreign
  `AGENT-*` records.

## Rationale

Hydration and reindex are operational paths. They must not fail because another
agent left a broken identity record behind. Full audit remains available for
repair and review, but normal work should only be blocked by problems relevant
to the current agent and current focus.
