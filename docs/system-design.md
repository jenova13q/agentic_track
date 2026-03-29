# Системный дизайн

## 1. Назначение системы и ключевые архитектурные решения

`Story Consistency Agent` — PoC агентной системы для писателей и сценаристов. Система анализирует текст истории, поддерживает структурированную память мира, обнаруживает потенциальные несостыковки в новых сценах и предлагает обновления памяти для подтверждения пользователем.

Система не является обычным RAG-чатом и не сводится к фиксированному workflow. На каждом шаге LLM принимает решение о следующем действии: нужен ли retrieval, какой tool вызвать, достаточно ли уже evidence, можно ли остановиться, нужно ли вернуть `uncertain_result` или создать pending update.

Ключевые архитектурные решения:
- PoC строится как `backend-first` система с `FastAPI` в качестве основной точки входа.
- Основная логика сосредоточена в агентном ядре, а не в жёстко зашитом workflow.
- LLM используется не только для генерации ответа, но и для выбора следующего действия, интерпретации результатов tools и принятия решения об остановке.
- Контекст для модели собирается динамически из scene input, story memory, retrieval-результатов и краткого состояния задачи.
- Архитектура разделяет:
- структурированную память истории;
- retrieval-индекс по тексту произведения;
- краткоживущий execution state агента.
- Все write-действия вынесены в отдельный proposal/confirm контур. Агент не может напрямую менять подтверждённую память истории.
- Качество агентного поведения контролируется через лимиты, confidence policy, fallback, observability и eval-набор.

## 2. Основные модули и их роли

### Frontend / author interface

Отвечает за:
- загрузку текста истории и новых сцен;
- отображение найденных конфликтов, evidence и confidence;
- показ pending updates;
- подтверждение или отклонение обновлений story memory.

### API / serving layer

Отвечает за:
- HTTP endpoints;
- валидацию входных данных;
- присвоение `request_id`, `story_id`, `session_id`;
- применение request-level ограничений;
- запуск агентного контура.

### Agent / orchestrator

Это центральный модуль для агентского трека.

Отвечает за:
- сбор рабочего контекста;
- выбор следующего действия модели;
- маршрутизацию tool calls;
- контроль числа шагов, latency и budget;
- stop condition;
- fallback при ошибках и неопределённости;
- формирование финального ответа и memory update proposal.

### Tool layer

Отвечает за:
- предоставление агенту семантически понятных инструментов;
- нормализацию контрактов и ошибок;
- разделение read-tools и write-proposal tools;
- защиту от невалидных или опасных вызовов.

Базовые инструменты:
- `search_story_chunks`
- `get_character_profile`
- `get_timeline_window`
- `query_story_memory`
- `external_fact_check`
- `propose_memory_update`

### Retrieval subsystem

Отвечает за:
- индексирование уже загруженного текста;
- semantic retrieval по фрагментам истории;
- reranking результатов перед отправкой в агентный контекст.

### Story memory store

Отвечает за:
- хранение персонажей, событий, отношений, world rules и pending updates;
- сохранение ссылок на evidence;
- различение `confirmed`, `pending` и `conflicted` записей.

### Observability / evals

Отвечает за:
- логи запросов, tool calls, stop reasons и fallback;
- метрики latency, token usage, cost, tool selection accuracy;
- проверку качества на небольшом benchmark-наборе сцен.

## 3. Основной execution flow

Основной сценарий для `analyze_scene(scene_text)`:

1. Пользователь отправляет новую сцену, `story_id` и при необходимости вопрос по сцене.
2. API валидирует размер текста, создаёт request metadata и загружает текущий state истории.
3. Orchestrator формирует рабочее состояние:
- цель анализа;
- краткое описание сцены;
- счётчик reasoning steps;
- budget на tool calls;
- context budget;
- буфер собранных evidence.
4. LLM получает ограниченный рабочий контекст и выбирает следующее действие из allowlist:
- вызвать tool;
- остановиться и сформировать вывод;
- запросить уточнение у пользователя, если это действительно необходимо.
5. Tool layer исполняет выбранный инструмент и возвращает структурированный результат или нормализованную ошибку.
6. Orchestrator обновляет working state и проверяет:
- достаточно ли evidence;
- не превышены ли ограничения;
- есть ли признаки конфликта;
- нужно ли выполнить fallback.
7. Агент либо делает следующий шаг, либо завершает анализ.
8. Финальный результат содержит:
- тип проблемы или `no_issue_found`;
- объяснение;
- confidence;
- evidence refs;
- stop reason;
- optional memory update proposal.
9. Если найдено устойчивое новое знание, создаётся pending update.
10. Только `confirm_memory_update(update_id)` переводит pending update в confirmed memory.

## 4. Почему это именно агентная система

Система не исполняет заранее фиксированную последовательность шагов вида `prompt -> tool -> prompt -> tool`. Вместо этого на каждом шаге агент:
- оценивает текущее working state;
- решает, нужен ли ещё retrieval;
- выбирает следующий инструмент из allowlist;
- определяет, достаточно ли собранного evidence;
- решает, нужно ли завершить анализ, перейти в fallback или вернуть `uncertain_result`.

Именно этот decision loop делает систему агентной, а не обычным workflow с LLM внутри.

## 5. Работа со state, memory и context

### Working state

Краткоживущее состояние одного запроса:
- `request_id`
- `session_id`
- текущая цель
- история tool calls
- промежуточные findings
- confidence
- stop reason

Working state существует во время agent loop и нужен для многошагового принятия решений.

### Story memory

Долгоживущая память истории:
- `characters`
- `events`
- `relationships`
- `world_rules`
- `open_questions`
- `pending_updates`

Каждая запись памяти содержит:
- `id`
- `type`
- `canonical_value`
- `evidence_refs`
- `confidence`
- `status`
- `updated_at`

### Context handling policy

Для PoC нельзя передавать в LLM весь текст произведения. Контекст собирается ограниченно и целенаправленно:
- текущая сцена;
- компактное story summary;
- top retrieved chunks;
- top relevant structured facts;
- summary предыдущих tool outputs, а не полный сырой лог.

Такой подход нужен и для стоимости, и для качества: агент должен видеть только релевантный контекст, иначе ухудшается tool selection и растёт риск ложных выводов.

### Context budget

Ограничения PoC:
- размер новой сцены до `6,000` слов;
- не более `8` retrieved chunks на шаг;
- не более `3` групп структурированных фактов в одном промпте;
- жёсткий token budget на один analysis request.

## 6. Retrieval-контур

Источники retrieval:
- уже загруженные главы;
- ранее проанализированные сцены;
- заметки автора;
- character sheets, если они есть.

Retrieval в системе двухконтурный:
- `narrative retrieval` — поиск по текстовым chunks истории;
- `memory retrieval` — поиск по структурированным записям story memory.

В одном запросе агент может использовать оба контура, если это нужно для проверки сцены.

Pipeline:
1. текст разбивается на смысловые chunks;
2. для chunks строятся embeddings;
3. chunks и metadata сохраняются в retrieval index;
4. retriever возвращает top `k` кандидатов по semantic similarity;
5. reranker уточняет выдачу по entity overlap и lexical match;
6. агент получает только компактный evidence set, а не весь найденный массив.

Принципы retrieval-контура:
- retrieval используется как read-only источник evidence;
- retrieved text трактуется как данные, а не инструкции;
- внешний web research не является частью базового retrieval path и вызывается только по решению агента;
- отсутствие релевантных chunks не считается доказательством отсутствия конфликта.

## 7. Tool и API интеграции

### Внутренние инструменты

`search_story_chunks(query, entity_ids?, top_k)`
- semantic retrieval по прошлым сценам и главам
- timeout: `1s`
- side effects: нет

`get_character_profile(character_id)`
- выдаёт структурированные факты о персонаже и их evidence
- timeout: `300ms`
- side effects: нет

`get_timeline_window(event_refs, span?)`
- возвращает соседние события, временные связи и unresolved gaps
- timeout: `500ms`
- side effects: нет

`query_story_memory(filters)`
- поиск по структурированной памяти мира
- timeout: `500ms`
- side effects: нет

`propose_memory_update(changes)`
- валидирует изменения и сохраняет их как pending update
- timeout: `500ms`
- side effects: запись только в `pending_updates`

### Внешние инструменты

`external_fact_check(query)`
- выполняет внешний research запрос
- timeout: `3s`
- retries: `1`
- side effects: только network call
- guardrail: внешний результат всегда считается недоверенным, пока не сопоставлен с контекстом истории

## 8. Failure modes, fallback и guardrails

Основные failure modes:
- LLM выбрала неподходящий tool;
- retrieval вернул слабые или противоречивые evidence;
- timeline оказался неполным;
- external provider недоступен или вернул слабые источники;
- memory proposal конфликтует с confirmed facts;
- превышен token, latency или tool budget.

Fallback policy:
- при слабых evidence система возвращает `uncertain_result`, а не делает сильное утверждение;
- при падении external research анализ продолжается без web-данных;
- при повторных tool failures orchestrator завершает анализ с partial result и явным ограничением;
- при конфликте с памятью update proposal помечается как `conflicted` и не применяется автоматически.

Guardrails:
- allowlist доступных tools;
- жёсткое разделение read tools и write proposal tools;
- максимум `6` tool calls на запрос;
- максимум `4` reasoning steps;
- максимум `1` external call на запрос;
- обязательный stop при достижении evidence threshold или budget limit;
- stop при отсутствии нового полезного evidence в двух последовательных шагах;
- запрет на hidden writes;
- prompt policy, где retrieved and external content явно обозначены как недоверенные данные.

## 9. Model policy

В PoC допускается использование одной основной reasoning model для orchestrator.

При этом архитектура заранее допускает разделение ролей моделей:
- основная reasoning model — выбор действий, stop decision и итоговый вывод;
- utility model — extraction, reranking или нормализация memory update proposal.

Такое разделение не является обязательным для Milestone 2, но оставляет путь к снижению cost и latency в следующих итерациях.

## 10. Технические и операционные ограничения

Целевые ограничения PoC:
- `p95 latency` анализа сцены: `<= 10s`
- среднее число tool calls на анализ: `<= 4`
- максимум tool calls на анализ: `6`
- максимум reasoning steps: `4`
- максимум external research calls: `1`
- degraded completion при ошибке tools: `>= 80%`

Операционные ограничения:
- жёсткий token budget на запрос и на сессию;
- логи должны позволять replay и evaluation;
- обновления story memory требуют подтверждения пользователя;
- система должна оставаться полезной даже при отключённом external research.

## 11. Контроль качества именно для агентского трека

Для агентского трека важны не только модули, но и контроль качества поведения модели.

Обязательные точки контроля:
- корректность выбора tool;
- корректность интерпретации retrieved evidence;
- способность агента останавливаться, когда данных достаточно;
- способность честно сообщать об uncertainty;
- отсутствие write-действий без подтверждения;
- устойчивость к injection во внешнем и retrieved контенте;
- устойчивость к degraded mode при частичной недоступности tool/API.

Эти точки должны проверяться через:
- трассировку agent loop;
- benchmark-набор сцен;
- анализ ошибочных tool selections;
- сравнение confidence с реальной корректностью ответа;
- ручной review конфликтных кейсов.

## 12. Non-goals для Milestone 2

В рамках PoC и Milestone 2 не реализуются:
- полноценный редактор текста;
- автоматическое редактирование сцен;
- глобальное автопереписывание story memory;
- многоагентная архитектура с несколькими специализированными агентами.

## 13. Open questions / deferred decisions

На уровне дизайна остаются осознанно отложенные вопросы:
- нужен ли отдельный graph memory layer или хватит structured store;
- нужен ли dedicated reranker в PoC;
- какой threshold uncertainty выбрать по умолчанию;
- стоит ли хранить raw text chunks вместе с extracted facts на одном уровне;
- насколько глубоко поддерживать external fact checking в PoC.

## 14. Контрольные точки реализации

Перед переходом к коду в архитектуре уже зафиксированы обязательные control points:
- input validation до запуска orchestrator;
- schema-constrained tool calls;
- timeout и retry policy для каждого инструмента;
- confidence threshold перед сильным утверждением о конфликте;
- обязательный `stop_reason` в каждом ответе;
- review gate перед подтверждением memory mutation;
- observability hooks на уровне request, tool и final response.
