# Story Consistency Agent | AI writer assistant | StoryWorld Agent | Narrative Consistency Agent

## Что это за система

`Story Consistency Agent` — агентная система для писателя и сценариста, которая помогает поддерживать консистентность мира истории.

Система:
- загружает текст истории;
- извлекает персонажей, события, факты и отношения;
- поддерживает `story memory`;
- анализирует новые сцены;
- сама выбирает полезные инструменты для проверки;
- находит конфликты в характере, фактах и таймлайне;
- возвращает объяснение, `confidence`, `stop_reason` и `tool_traces`;
- создаёт `pending update`, но не меняет подтверждённую память без явного подтверждения пользователя.

Это не просто `RAG` и не жёсткий workflow. В системе есть `orchestrator`, набор `tools`, retrieval, bounded agent execution, `story memory`, `pending -> confirm/reject` write path и слой observability.

## Для кого и какую боль решает

При работе над длинными произведениями автору приходится удерживать в голове:
- характеры персонажей;
- уже зафиксированные факты;
- отношения между героями;
- временную линию событий;
- правила мира.

Из-за этого появляются несостыковки, ручная перепроверка и рост когнитивной нагрузки. `Story Consistency Agent` снимает часть этой нагрузки и помогает проверять новые сцены с опорой на память истории.

## Что система умеет сейчас

Реализованный backend уже поддерживает:
- ingest текста истории;
- chunking и простое retrieval по chunks и memory;
- извлечение `characters`, `facts`, `events`, `relationships`;
- анализ новой сцены через agent orchestrator;
- выбор tools через live LLM path или heuristic fallback;
- статусы результата `conflict`, `no_conflict`, `uncertain`;
- `pending update`, `confirm`, `reject`;
- request tracing, `tool_traces`, observability summary и recent traces;
- smoke tests и отдельный live smoke script.

## Что именно показывается на финальном demo

На финальном показе система должна демонстрировать полный end-to-end поток:
- `ingest` истории;
- `analyze_scene` для новой сцены;
- возврат одного из исходов: `conflict`, `no_conflict`, `uncertain`;
- объяснение найденной проблемы;
- `tool_traces` и `orchestrator_mode`;
- создание `pending update`;
- подтверждение или отклонение обновления памяти;
- observability summary, показывающую поведение агента.

Финальные demo-материалы:
- `data/demo-story.txt`
- `data/demo-scenarios.json`
- `docs/demo-script.md`
- `docs/demo-requests.md`
- `docs/demo-runbook.md`
- `docs/demo-checklist.md`
- `tests/demo_eval.py`

## Что НЕ входит в scope

Система:
- не пишет книгу за автора;
- не оценивает литературный стиль и художественную ценность;
- не заменяет профессионального редактора;
- не гарантирует объективную истинность художественных решений;
- не вносит изменения в подтверждённую память автоматически;
- не реализует полноценный текстовый редактор или сложную IDE-интеграцию.

## Архитектура

```mermaid
flowchart TD
    A[Author submits scene] --> B[API / Backend]
    B --> C[Agent Orchestrator]

    C --> D[Retriever]
    C --> E[Story Memory]
    C --> F[Tools Layer]

    D --> C
    E --> C
    F --> C

    F --> F1[Character Timeline and Story Tools]
    F --> F2[Pending Update Tools]

    C --> G[Explanation and Confidence]
    C --> H[Pending Memory Update]

    G --> I[Author Review]
    H --> I
    I --> J[Confirm or Reject Update]
    J --> E

    C --> K[Observability]
```

Ключевые модули:
- `API / Backend` — HTTP endpoints и request handling;
- `Agent Orchestrator` — выбор tools, bounded execution, stop reasons;
- `Retriever` — narrative retrieval и memory retrieval;
- `Story Memory` — подтверждённые факты и pending updates;
- `Tools Layer` — read tools и write-proposal tools;
- `Observability` — traces и summary по агентному поведению.

Подробности зафиксированы в:
- `docs/system-design.md`
- `docs/specs/`
- `docs/diagrams/`
- `docs/governance.md`

## Реализованные API endpoints

Системные:
- `GET /health`
- `GET /stories`
- `POST /stories/ingest`
- `GET /stories/{story_id}`

Агентный контур:
- `POST /stories/{story_id}/analyze`

Управление памятью:
- `POST /stories/{story_id}/pending-updates/{update_id}/confirm`
- `POST /stories/{story_id}/pending-updates/{update_id}/reject`

Наблюдаемость:
- `GET /observability/summary`
- `GET /observability/traces`

## Что видно в ответе агента

`analyze_scene` возвращает:
- `status`
- `issue_type`
- `explanation`
- `confidence`
- `evidence_refs`
- `stop_reason`
- `orchestrator_mode`
- `agent_step_count`
- `tool_call_count`
- `tool_traces`
- `memory_update_proposal_id`

Это важно для защиты, потому что показывает не только итог, но и поведение агента.

## Guardrails и ограничения

В текущем PoC уже соблюдаются такие правила:
- write path отделён от read path;
- подтверждённая память не меняется без `confirm`;
- есть `reject` path для pending updates;
- live LLM path имеет heuristic fallback;
- orchestrator ограничен по шагам и числу tool calls;
- агент возвращает `uncertain`, если evidence недостаточно;
- observability хранит traces анализа и update actions.

Полные архитектурные ограничения и governance:
- `docs/governance.md`
- `docs/system-design.md`
- `docs/specs/agent-orchestrator.md`
- `docs/specs/observability-evals.md`

## Локальный запуск

После установки зависимостей:

```bash
uvicorn app.main:app --reload
```

Проверка сервиса:

```bash
curl http://127.0.0.1:8000/health
```

Ожидаемый ответ:

```json
{"status":"ok"}
```

## Тесты

Обычный smoke suite:

```bash
python -m unittest -v
```

Live LLM smoke:

```bash
python tests/live_smoke.py
```

Demo benchmark:

```bash
python tests/demo_eval.py
```

Если локального `python` нет, можно использовать контейнерный прогон, который мы применяем для проверки:

```bash
docker run --rm -v "${PWD}:/workspace" -w /workspace python:3.12 sh -lc "python -m pip install -e . && python -m unittest -v"
```

## Структура репозитория

- `app/` — backend, orchestrator, tools, retrieval, memory, observability
- `tests/` — smoke tests и live smoke
- `data/` — demo story, scenarios и runtime stories
- `docs/product-proposal.md` — Milestone 1 proposal
- `docs/governance.md` — risk register и protections
- `docs/system-design.md` — Milestone 2 system design
- `docs/specs/` — спецификации модулей
- `docs/diagrams/` — C4, workflow и data flow диаграммы
- `docs/demo-*` — материалы для финального demo

## Что проговаривать на защите

- почему это агент, а не fixed workflow;
- где находится `story memory`;
- какие tools выбирает orchestrator;
- как система показывает `uncertainty`;
- почему write path защищён через `pending -> confirm/reject`;
- какие guardrails и ограничения есть;
- как наблюдается качество через traces и summary.
