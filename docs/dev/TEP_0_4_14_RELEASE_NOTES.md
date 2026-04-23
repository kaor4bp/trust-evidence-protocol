# TEP 0.4.14 Release Notes

TEP 0.4.14 makes `agent_private_key` an explicit front-door contract instead of
an implicit environment convention.

## Changed

- CLI now accepts a global `--agent-private-key` argument.
- MCP-to-CLI bridging now forwards the key explicitly as a CLI argument instead
  of relying on hidden subprocess environment propagation.
- Front-door CLI commands `brief-context`, `next-step`, `lookup`, and
  `guidelines-for` now fail early with `agent_identity_required` before falling
  into secondary context-validation noise.
- `agent_identity_required` text now tells the agent to generate its own key,
  keep it in session state, and pass it explicitly through CLI/MCP.
- MCP schema text for `agent_private_key` now explains the same ownership rule.

## Rationale

The previous contract was too implicit. Agents could treat missing
`agent_private_key` as a plugin/runtime failure because the key was not surfaced
as an explicit call parameter all the way through the CLI bridge, and the
resulting errors often appeared as secondary `WCTX-*` validation failures. This
release makes the key requirement visible in the API shape and visible in the
error text.

## Migration Notes

Direct CLI callers should prefer `--agent-private-key` over relying on
`TEP_AGENT_PRIVATE_KEY`. The environment variable still works as a compatibility
fallback for existing hooks and scripts, but the intended contract is now the
explicit parameter.
