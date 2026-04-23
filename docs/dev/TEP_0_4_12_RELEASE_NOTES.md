# TEP 0.4.12 Release Notes

TEP 0.4.12 removes the remaining `local-agent` contract remnants.

## Changed

- AGENT schema export now requires `key_scope=agent-owned`.
- AGENT schema migration now normalizes to `agent-owned` instead of
  `local-agent`.
- Bootstrap/template AGENT payloads now emit `agent-owned`.
- Contract notes and tests were aligned to the same owner model.

## Rationale

The runtime had already moved to the personal `agent_private_key` +
`agent-owned` model, but schema/template leftovers still described the old
`local-agent` shape. That mismatch kept old contexts looking valid and made
repair work noisier than necessary.
