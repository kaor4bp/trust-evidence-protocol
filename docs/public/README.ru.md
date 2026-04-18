# Trust Evidence Protocol

Trust Evidence Protocol (TEP) — это runtime для памяти и рассуждений кодовых
агентов, построенный вокруг принципа evidence-first.

TEP помогает агенту не принимать чат-память, догадки, сгенерированные индексы
или старые наблюдения за доказательства. Он разделяет клеймы, подтверждённые
источниками, и отдельные сущности: permissions, restrictions, guidelines,
tasks, working context, plans, debt, proposals и hypotheses.

## Что Даёт TEP

- Персистентный структурированный контекст для работы агента.
- Канонические записи источников `SRC-*` и клеймов `CLM-*`.
- Lifecycle для активных, решённых, исторических и архивных фактов.
- Явные записи планов, техдолга, открытых вопросов, предложений и рабочего
  контекста.
- Сгенерированные индексы для поиска, навигации по коду, topic-prefiltering и
  logic checks.
- Интеграцию Codex plugin: hooks, CLI-команды, skill и read-only MCP tools.
- Тесты deterministic runtime behavior и live-agent conformance.

## Текущая Структура

Сейчас Codex plugin находится здесь:

```text
plugins/trust-evidence-protocol/
```

Такая структура сохраняет уже проверенный plugin layout, пока runtime
разбивается на более маленькие модули.

## Модель Безопасности

TEP не считает память автоматически истинной.

Generated views и indexes помогают агенту находить записи, но доказательство
должно сводиться к каноническим клеймам с источниками. Исторические или
решённые клеймы остаются доступными для поиска, но не должны доминировать в
текущем reasoning.

## Документация

- [Developer docs](../dev/README.md)
- [Reference docs](../reference/README.md)
- [Research docs](../research/README.md)
