# Developer Documentation

These documents are for maintainers and contributors working on the TEP
runtime, Codex adapter, MCP tools, hooks, and tests.

Keep developer docs in English. Move user-facing content to `docs/public/`.
Move stable data contracts to `docs/reference/`. Move exploratory material to
`docs/research/`.

## Documents

- [Repository Organization](REPOSITORY_ORGANIZATION.md)
- [Anti-NIH Tooling Round](ANTI_NIH_TOOLING_ROUND.md)
- [First Integration Stack](FIRST_INTEGRATION_STACK.md)
- [TEP Developer Reference](TEP_DEVELOPER_REFERENCE.md)
- [TEP API-First Contract](TEP_API_FIRST_CONTRACT.md)
- [TEP 0.4.0 Functional Specification](TEP_0_4_0_FUNCTIONAL_SPEC.md)
- [TEP 0.4.0 Agent Interface Contracts](TEP_0_4_0_AGENT_INTERFACE_CONTRACTS.md)
- [TEP 0.4.0 Mechanics Requirements](TEP_0_4_0_MECHANICS_REQUIREMENTS.md)
- [TEP 0.4.0 Mechanics Deep Dives](mechanics/README.md)
- [TEP 0.4.1 Release Notes](TEP_0_4_1_RELEASE_NOTES.md)
- [TEP 0.4.2 Release Notes](TEP_0_4_2_RELEASE_NOTES.md)
- [TEP 0.4.3 Release Notes](TEP_0_4_3_RELEASE_NOTES.md)
- [TEP 0.4.4 Release Notes](TEP_0_4_4_RELEASE_NOTES.md)
- [TEP 0.4.5 Release Notes](TEP_0_4_5_RELEASE_NOTES.md)
- [TEP 0.4.6 Release Notes](TEP_0_4_6_RELEASE_NOTES.md)
- [TEP Map Graph v1](TEP_MAP_GRAPH_V1.md)
- [TEP Core Rewrite Working Context](TEP_CORE_REWRITE_CONTEXT.md)
- [TEP Core Baseline](TEP_CORE_BASELINE.md)
- [Tick-Tock Adoption Contract](TICK_TOCK_ADOPTION.md)

## Maintenance Rules

- Keep deterministic behavior and test commands explicit.
- Record migration notes when layout, storage, or command behavior changes.
- Do not document local absolute paths, private workspaces, or secrets.
- Prefer linking to reference docs for stable semantics instead of duplicating
  record rules in developer notes.
