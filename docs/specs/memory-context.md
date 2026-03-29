# Спецификация Memory / Context

## Назначение

Модуль отвечает за хранение долговременной story memory и за сбор ограниченного, объяснимого контекста для каждого шага agent loop.

## Слои памяти

### Working state

Краткоживущее состояние выполнения:
- текущий запрос;
- текущая цель;
- число шагов;
- история tool calls;
- промежуточные findings;
- накопленные evidence.

### Persistent story memory

Долгоживущая память:
- `characters`
- `events`
- `relationships`
- `world_rules`
- `open_questions`
- `pending_updates`

## Схема записи

Каждая запись содержит:
- `id`
- `type`
- `canonical_value`
- `evidence_refs`
- `confidence`
- `status`
- `updated_at`

## Политика сборки контекста

Контекст для модели собирается из:
- текущей сцены;
- story summary;
- relevant structured records;
- retriever excerpts;
- summary истории предыдущих tool calls.

Полный raw history не должен накапливаться в prompt. Orchestrator обязан сжимать старые результаты в компактные summaries, иначе деградируют качество и стоимость.

## Budget policy

- max scene size: `6,000` слов
- max retrieved chunks per step: `8`
- max fact groups в одном prompt: `3`
- hard token budget enforced by serving layer

## Mutation policy

- новые факты сначала попадают в `pending_updates`;
- только после подтверждения становятся `confirmed`;
- conflicting facts могут существовать как `conflicted`, пока пользователь не примет решение.

## Значение для агентского трека

State и memory здесь не вторичны. Именно они делают систему агентом, а не stateless chat. Качество работы агента зависит от того, насколько:
- память остаётся структурированной;
- контекст не переполнен;
- модель видит только релевантные факты;
- update path отделён от простого ответа.
