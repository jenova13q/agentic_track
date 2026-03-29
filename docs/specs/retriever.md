# Спецификация Retriever

## Назначение

Retriever возвращает минимально достаточный набор прошлых фрагментов истории, чтобы агент мог анализировать новую сцену без передачи в LLM всего произведения.

## Источники

Источники retrieval:
- загруженные главы и сцены;
- ранее проанализированные фрагменты;
- заметки автора;
- character sheets, если они есть.

Retriever работает по двум контурам:
- `narrative retrieval` — поиск по текстовым chunks истории;
- `memory retrieval` — поиск по структурированным сущностям, событиям, отношениям и world rules.

Агент может использовать оба контура в одном запросе, если это нужно для проверки сцены.

## Вход

Основной вход:
- текстовый query от orchestrator;
- optional `entity_ids`;
- optional chapter или timeline filters.

## Pipeline

1. Нормализовать и разбить текст на chunks во время ingestion.
2. Построить embeddings для chunks.
3. Сохранить vectors и metadata.
4. Достать кандидатов из structured memory по entity match и metadata filters.
5. Достать top `k` narrative chunks по semantic similarity.
6. Выполнить reranking по lexical overlap и entity match.
7. Вернуть компактные excerpts и source refs.

## Выходной контракт

Каждый результат содержит:
- `chunk_id`
- `source_type`
- `source_ref`
- `excerpt`
- `score`
- `matched_entities`

## Ограничения

- default `top_k = 8`
- max excerpt size per chunk: `600` символов
- max latency: `1s`
- компонент read-only

## Failure behavior

- при пустой выдаче возвращать пустой список и `no_relevant_chunks`;
- при проблеме с индексом возвращать `retrieval_unavailable`;
- orchestrator не должен интерпретировать пустую выдачу как доказательство отсутствия противоречия.

## Значение для агентского трека

Качество retriever напрямую влияет на качество agent reasoning. Если retrieval слабый, агент начинает принимать решения по неполному evidence и растёт доля ложных конфликтов или пропусков. Поэтому retriever для этого проекта — часть agent quality loop, а не просто инфраструктурный сервис.
