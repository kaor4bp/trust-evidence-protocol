# TEP 0.4.15 Release Notes

TEP 0.4.15 closes the remaining bootstrap gap for new agents by making
`agent_private_key` mandatory in MCP schemas and teaching startup hooks to begin
with identity bootstrap instead of an immediate TEP route.

## Changed

- MCP tool schemas now require `agent_private_key` whenever a tool exposes that
  field.
- Codex startup hooks now emit an explicit bootstrap hint when no
  `TEP_AGENT_PRIVATE_KEY` is present, instead of synthesizing a misleading
  `next_step` route.
- Session-start and user-prompt hook reminders now say the first TEP step is to
  generate and keep a personal `agent_private_key`.
- Mirrored the same hook bootstrap fix into the repo-local `.codex/hooks`
  mirror used for integration testing.

## Rationale

`0.4.14` made the key explicit in CLI/MCP transport and error text, but a new
agent could still enter a loop because startup hooks told it to use TEP
front-door commands before establishing a personal identity key. That made the
system feel hung or contradictory: the route hint said “go forward” while the
runtime said “missing identity”. This release fixes the bootstrap order.

## Migration Notes

Agents and MCP clients should now treat `agent_private_key` as required for
identity-bound tools. Startup environments that do not yet inject
`TEP_AGENT_PRIVATE_KEY` will still work, but hooks will first instruct the
agent to create and retain its own key before using front-door tools.
