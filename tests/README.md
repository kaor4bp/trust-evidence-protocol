# Codex live-agent tests

Этот каталог содержит тесты, которые запускают `codex exec` внутри Docker с отдельным временным `CODEX_HOME`.

Docker нужен как isolation boundary для реальных тестов на реальных агентах.
Для live-agent проверок нужен `OPENAI_API_KEY` в корневом `.env` файле репозитория.
Harness не читает пользовательский `~/.codex/auth.json`: он выполняет `codex login --with-api-key` внутри изолированного `CODEX_HOME` и создаёт временный auth cache только для тестового запуска.

## Настройка `.env`

Из корня репозитория создай файл:

```bash
OPENAI_API_KEY=sk-...
```

Файл `.env` добавлен в `.gitignore` и не должен коммититься.

## Как работает harness

- читает `OPENAI_API_KEY` из `.env` или окружения
- создаёт временный workspace
- создаёт временный `CODEX_HOME`
- копирует skill из `plugins/trust-evidence-protocol/skills/trust-evidence-protocol`
- собирает Docker image `tim-codex-skill-runner`, если его ещё нет
- логинит Codex CLI в изолированный `CODEX_HOME` через `codex login --with-api-key`
- запускает `codex exec` внутри Docker
- пишет результат в JSON по `tests/case_output.schema.json`

## Запуск live-agent тестов

```bash
uv run pytest tests/trust_evidence_protocol/test_logic.py -q
```

Полный live-agent subset медленный и может быть nondeterministic, потому что проверяет поведение модели, а не только Python-runtime.
Для plugin-runtime regression checks сначала запускай deterministic subset:

```bash
uv run pytest -q \
  tests/trust_evidence_protocol/test_plugin_cli.py \
  tests/trust_evidence_protocol/test_hooks_runtime.py \
  tests/trust_evidence_protocol/test_mcp_server.py
```

## Ручной запуск `codex exec`

```bash
tests/run_codex_exec.sh /absolute/path/to/workspace \
  "Use the trust-evidence-protocol skill and make the minimal safe change."
```

Или через stdin:

```bash
cat /absolute/path/to/prompt.txt | tests/run_codex_exec.sh /absolute/path/to/workspace
```

`tests/run_codex_exec.sh` использует тот же `.env`, Docker image и isolated `CODEX_HOME`, что и Python harness.
