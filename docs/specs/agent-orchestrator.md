# Спецификация Agent / Orchestrator

## Назначение

Orchestrator управляет bounded agent loop: выбирает следующий шаг, запускает tools, обновляет state, проверяет stop condition и переводит систему в fallback при ошибках или неопределённости.

## Шаги цикла

1. Собрать working state из запроса, story summary и memory.
2. Передать в LLM ограниченный контекст и allowlist доступных действий.
3. Получить следующее действие:
- вызвать tool;
- остановиться и собрать ответ;
- запросить уточнение у пользователя.
4. Выполнить действие.
5. Обновить state и confidence.
6. Проверить stop conditions.
7. Повторить цикл, если budget и policy это позволяют.

## Правила переходов

- максимум один tool call на одну итерацию;
- неизвестные tool names отклоняются до выполнения;
- агент не может вызывать `confirm_memory_update`;
- внешний research допустим только когда внутреннего evidence недостаточно или вопрос явно требует внешних знаний.

## Stop conditions

- собрано достаточно evidence для bounded answer;
- достигнут максимум `4` reasoning steps;
- достигнут максимум `6` tool calls;
- исчерпан latency budget;
- два последовательных шага не дали нового полезного evidence;
- повторяющиеся retryable failures без прогресса;
- выбран explicit uncertainty outcome.

## Fallback behavior

- если tool failure не даёт завершить анализ, вернуть partial result с limitation note;
- если evidence противоречивы, вернуть `uncertain_result`;
- если найдено правдоподобное новое знание, создать proposal, а не менять memory напрямую.

## Выходной контракт

Финальный ответ должен включать:
- `status`
- `issue_type`
- `explanation`
- `confidence`
- `evidence_refs`
- `stop_reason`
- `memory_update_proposal_id?`

## Значение для агентского трека

Это главный модуль Milestone 2. Именно orchestrator определяет, будет ли система выглядеть как агент, а не как скрытый workflow. Поэтому качество этого модуля оценивается по тому, умеет ли он:
- ограничивать модель рамками доступных действий;
- принимать корректные stop decisions;
- не делать лишних tool calls;
- корректно обрабатывать uncertainty;
- поддерживать explainability на каждом шаге.
