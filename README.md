# Trust Evidence Protocol

Trust Evidence Protocol (TEP) is an evidence-first memory and reasoning
runtime for coding agents.

The protocol separates source-backed truth from permissions, restrictions,
guidelines, working context, plans, debt, proposals, generated indexes, and
agent hypotheses. The current repository contains the TEP runtime, Codex plugin
adapter, read-only MCP server, hooks, docs, and regression tests.

## Current Status

This repository is the extracted public home for the TEP plugin/runtime.

The initial layout intentionally keeps the proven incubator structure:

```text
plugins/trust-evidence-protocol/
  skills/trust-evidence-protocol/
  scripts/
  tep_runtime/
  mcp/
  hooks/
  templates/
docs/
tests/
```

The runtime is already split into importable `tep_runtime/*` modules, while
`scripts/context_cli.py` still acts as the compatibility CLI dispatcher.
Future refactors should keep deterministic behavior stable and move gradually
toward thinner adapters.

## Safety

This is a public repository. Do not commit secrets or live agent memory.

Ignored local-only paths include:

- `.env`
- `.env.*`
- `.codex_context/`
- `.tep_context/`
- `.codex/`
- `.codex-test-home/`

Live-agent Docker tests read `OPENAI_API_KEY` from an untracked `.env` file or
from the environment.

## Development

Install test dependencies:

```bash
uv sync --extra test
```

Run deterministic path-map reasoning tests:

```bash
uv run pytest tests/trust_evidence_protocol/test_path_map_curiosity.py -q
```

Run the deterministic plugin runtime subset:

```bash
uv run pytest -q \
  tests/trust_evidence_protocol/test_plugin_cli.py \
  tests/trust_evidence_protocol/test_hooks_runtime.py \
  tests/trust_evidence_protocol/test_mcp_server.py
```

Live-agent tests use Docker and real `codex exec`; run them deliberately, not
as part of every local edit loop.

## Documentation

- [Plugin README](plugins/trust-evidence-protocol/README.md)
- [Repository organization](docs/REPOSITORY_ORGANIZATION.md)
- [Developer reference](docs/TEP_DEVELOPER_REFERENCE.md)
- [Data model](docs/TEP_DATA_MODEL.md)
- [Reasoning research](docs/TEP_REASONING_RESEARCH.md)
- [Planning and curiosity research](docs/TEP_PLANNING_CURIOSITY_RESEARCH.md)
