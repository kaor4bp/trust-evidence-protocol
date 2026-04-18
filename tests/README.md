# Test Layers

This repository has two test layers.

## Deterministic Tests

Deterministic tests validate Python runtime, CLI, hooks, MCP adapters, fixtures,
and pure helper behavior. They do not call live agents and do not require
`OPENAI_API_KEY`.

The default pytest command runs only deterministic tests:

```bash
uv run pytest -q
```

This default is enforced by `pyproject.toml` with:

```text
addopts = "-m 'not live_agent'"
```

## Live-Agent Tests

Live-agent tests run real `codex exec` inside Docker with a separate temporary
`CODEX_HOME`.

Docker is the isolation boundary for real tests against real agents. Live-agent
tests require `OPENAI_API_KEY` in an untracked repository-root `.env` file or in
the environment.

The harness never reads the user-level `~/.codex/auth.json`. It runs
`codex login --with-api-key` inside the isolated `CODEX_HOME` and creates a
temporary auth cache only for the test run.

Run live-agent tests explicitly:

```bash
uv run pytest -m live_agent -q
```

Run one live-agent file explicitly:

```bash
uv run pytest -m live_agent tests/trust_evidence_protocol/test_logic.py -q
```

## `.env` Setup

Create a repository-root `.env` only when running live-agent tests:

```bash
OPENAI_API_KEY=sk-...
```

`.env` is ignored by git and must never be committed.

## Harness Behavior

The live-agent harness:

- reads `OPENAI_API_KEY` from `.env` or the process environment
- creates a temporary workspace
- creates a temporary `CODEX_HOME`
- copies the skill from `plugins/trust-evidence-protocol/skills/trust-evidence-protocol`
- builds the Docker image `tim-codex-skill-runner` if needed
- logs Codex CLI into the isolated `CODEX_HOME` with `codex login --with-api-key`
- runs `codex exec` inside Docker
- writes JSON output validated by `tests/case_output.schema.json`

Most live-agent tests validate the agent's TEP reasoning behavior through the
skill and JSON verdict schema. They are not sufficient proof that the full
plugin runtime is installed.

`tests/trust_evidence_protocol/test_live_plugin_runtime.py` is the plugin
runtime canary. It installs the full plugin bundle into isolated
`CODEX_HOME/plugins/cache/home-local-plugins/...`, enables the plugin in
`config.toml`, creates an anchored `.tep_context`, and requires the live agent
to run plugin runtime commands such as `context_cli.py`. This test should fail
if the environment only has a copied standalone skill or if the runtime image
cannot execute the plugin.

## Manual `codex exec`

Run a one-off prompt through the same isolated harness:

```bash
tests/run_codex_exec.sh /absolute/path/to/workspace \
  "Use the trust-evidence-protocol skill and make the minimal safe change."
```

Or via stdin:

```bash
cat /absolute/path/to/prompt.txt | tests/run_codex_exec.sh /absolute/path/to/workspace
```

`tests/run_codex_exec.sh` uses the same `.env`, Docker image, and isolated
`CODEX_HOME` as the Python live-agent harness.
