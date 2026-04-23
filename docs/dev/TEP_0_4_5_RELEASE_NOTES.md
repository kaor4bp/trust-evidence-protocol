# TEP 0.4.5 Release Notes

## Summary

TEP 0.4.5 clarifies the normal agent cognition loop in the stable docs and
skill instructions.

## Changes

- Documents `lookup` as the direct retrieval path and map/curiosity tools as
  the broader navigation path for anchors, ignored facts, bridges, tap smell,
  cold zones, and CIX/backend signals.
- Establishes `STEP-*` claim-step entries as the normal reasoning sink for 0.4
  agents, with `REASON-*` described as the compatible public-chain route.
- Clarifies that map, lookup, CIX, backend hits, and telemetry remain
  navigation-only until drilled down into canonical `SRC-*`, `CLM-*`, or
  relation `CLM-*` records.
- Makes refutation explicit in the agent flow: contradictions must become CLM
  state or relation work through `contested`, `rejected`,
  `contradiction_refs`, structured `comparison`, or `meta_conflict`.

## Migration Notes

No record migration is required. This release changes documentation, skill
guidance, and version metadata only.

