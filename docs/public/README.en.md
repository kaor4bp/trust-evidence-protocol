# Trust Evidence Protocol

Trust Evidence Protocol (TEP) is an evidence-first memory and reasoning
runtime for coding agents.

TEP helps an agent avoid treating chat memory, guesses, generated indexes, or
old observations as proof. It separates source-backed claims from permissions,
restrictions, guidelines, tasks, working context, plans, debt, proposals, and
hypotheses.

## What TEP Provides

- Persistent structured context for agent work.
- Canonical `SRC-*` source records and `CLM-*` claim records.
- Lifecycle handling for active, resolved, historical, and archived facts.
- Explicit planning, debt, open-question, proposal, and working-context records.
- Generated indexes for lookup, code navigation, topic prefiltering, and logic
  checks.
- Codex plugin integration with hooks, CLI commands, a skill, and read-only MCP
  tools.
- Tests for deterministic runtime behavior and live-agent conformance.

## Current Shape

The repository currently keeps the Codex plugin under:

```text
plugins/trust-evidence-protocol/
```

This layout preserves the tested plugin structure while the runtime is being
split into smaller modules.

## Safety Model

TEP does not make memory automatically true.

Generated views and indexes help an agent find records, but proof must resolve
to canonical source-backed claims. Historical or resolved claims remain
searchable, but they should not dominate current reasoning.

## More Documentation

- [Developer docs](../dev/README.md)
- [Reference docs](../reference/README.md)
- [Research docs](../research/README.md)
