# Developer Documentation

These documents are for maintainers and contributors working on the TEP
runtime, Codex adapter, MCP tools, hooks, and tests.

Keep developer docs in English. Move user-facing content to `docs/public/`.
Move stable data contracts to `docs/reference/`. Move exploratory material to
`docs/research/`.

## Documents

- [Repository Organization](REPOSITORY_ORGANIZATION.md)
- [TEP Developer Reference](TEP_DEVELOPER_REFERENCE.md)
- [TEP Core Rewrite Working Context](TEP_CORE_REWRITE_CONTEXT.md)
- [TEP Core Baseline](TEP_CORE_BASELINE.md)

## Maintenance Rules

- Keep deterministic behavior and test commands explicit.
- Record migration notes when layout, storage, or command behavior changes.
- Do not document local absolute paths, private workspaces, or secrets.
- Prefer linking to reference docs for stable semantics instead of duplicating
  record rules in developer notes.
