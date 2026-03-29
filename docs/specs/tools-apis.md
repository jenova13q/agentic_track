# Спецификация Tools / APIs

## Назначение

Tool layer предоставляет агенту безопасные и семантически понятные действия, а также нормализует внутренние и внешние ошибки в предсказуемый контракт.

## Набор инструментов

`search_story_chunks(query, entity_ids?, top_k?)`
- semantic retrieval по тексту истории

`get_character_profile(character_id)`
- структурированные факты о персонаже

`get_timeline_window(event_refs, span?)`
- соседние события и временные gaps

`query_story_memory(filters)`
- поиск по структурированной памяти

`external_fact_check(query)`
- внешний research по необходимости

`propose_memory_update(changes)`
- сохранение pending update

`confirm_memory_update(update_id)`
- подтверждение update пользователем, а не агентом

## Модель ошибок

Каждый tool возвращает либо `ok`, либо структурированную ошибку:
- `error_code`
- `message`
- `retryable`
- `suggested_action`

Обязательные `error_code`:
- `not_found`
- `timeout`
- `unavailable`
- `invalid_input`
- `conflict_detected`
- `untrusted_source`

## Timeouts и retries

- локальные read-tools: `300ms` до `1s`, без retry по умолчанию
- `external_fact_check`: `3s`, максимум `1` retry
- write proposal tool не ретраится при validation failure

## Guardrails

- все tools используют schema-constrained arguments;
- read tools и write tools разделены;
- tool layer не выполняет произвольный код;
- external data всегда маркируется как `untrusted`;
- только `confirm_memory_update` может сохранить confirmed mutation;
- orchestrator отклоняет неизвестные tool names и malformed arguments.

## Значение для агентского трека

Для агентного PoC качество tools определяется не только доступностью API, но и тем, насколько хорошо LLM может:
- понять семантику инструмента;
- выбрать подходящий tool;
- корректно интерпретировать его результат;
- не перепутать read и write path.
