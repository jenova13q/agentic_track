# Спецификация Serving / Config

## Назначение

Зафиксировать, как PoC запускается, конфигурируется и остаётся воспроизводимым между локальной разработкой и демо-средой.

## Runtime assumptions

- backend service: `FastAPI`
- Python runtime: `3.12`
- storage: relational store + vector index
- LLM и embeddings: внешние провайдеры

## Обязательная конфигурация

- `LLM_MODEL`
- `EMBEDDING_MODEL`
- `LLM_API_KEY`
- `EMBEDDING_API_KEY`
- `EXTERNAL_RESEARCH_API_KEY`
- `MAX_AGENT_STEPS`
- `MAX_TOOL_CALLS`
- `MAX_EXTERNAL_CALLS`
- `REQUEST_TOKEN_BUDGET`
- `REQUEST_TIMEOUT_SECONDS`

## Политика конфигурации

- секреты только через environment variables;
- версии моделей должны быть pinned;
- в development по умолчанию внешний research может быть отключён;
- budgets и лимиты настраиваются без изменения кода.

## Serving behavior

- каждый запрос получает `request_id`;
- каждый ответ возвращает `stop_reason` и `confidence`;
- health checks должны отделять здоровье процесса от доступности внешних upstream API.

## Значение для агентского трека

Даже на агентском треке serving layer важен не сам по себе, а как механизм жёсткого контроля поведения агента. Через config фиксируются budgets, лимиты шагов, лимиты tool calls и модельные версии, без которых evaluation результатов теряет смысл.
