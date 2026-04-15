# Demo Script

## Цель показа

Показать, что система является агентной, а не просто RAG-чатом:
- есть story memory;
- есть bounded orchestrator;
- есть tool selection;
- есть explainable output;
- есть pending update / confirm path.

## Сценарии

### 1. Happy path без конфликта

- Загрузить историю из `data/demo-scenarios.json`, сценарий `happy_path_new_fact`
- Вызвать `POST /stories/ingest`
- Вызвать `POST /stories/{story_id}/analyze`
- Показать:
- `status = no_conflict`
- `tool_traces`
- `orchestrator_mode`
- отсутствие автоматической записи в confirmed memory

### 2. Character conflict

- Использовать сценарий `character_conflict`
- Показать, что агент поднимает `conflict`
- Обратить внимание на explanation, confidence и evidence refs

### 3. Fact conflict

- Использовать сценарий `fact_conflict`
- Показать конфликт с уже известной memory facts

### 4. Pending update и confirm

- Загрузить базовую историю про Anna
- Проанализировать сцену с новым персонажем Boris
- Показать `memory_update_proposal_id`
- Подтвердить update через `confirm` endpoint
- Показать, что запись появилась в confirmed memory только после confirm

## Что проговорить на защите

- orchestrator выбирает tools через bounded loop;
- read path и write path разделены;
- без достаточного evidence система может вернуть `uncertain`;
- даже при наличии LLM path система сохраняет deterministic guardrails;
- если LLM недоступен, демо продолжает работать в heuristic mode.
