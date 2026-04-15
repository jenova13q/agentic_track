# Demo Critical Path

## Цель

Этот файл важнее полного implementation plan для финального показа. Здесь только то, что нужно, чтобы показать систему целиком и получить итоговую оценку.

## 1. Перед запуском

- [ ] Убедиться, что `.env` заполнен
- [ ] Поднять backend
- [ ] Проверить `GET /health`
- [ ] При необходимости прогнать `tests/live_smoke.py`

## 2. Обязательные demo capabilities

- [ ] Ingest истории работает
- [ ] Analyze scene работает end-to-end
- [ ] Есть `conflict`, `no_conflict` и `uncertain`
- [ ] Есть `tool_traces`
- [ ] Есть `orchestrator_mode`
- [ ] Есть pending update / confirm flow
- [ ] Confirmed memory не меняется без confirm

## 3. Обязательные сценарии показа

- [ ] Happy path без конфликта
- [ ] Character conflict
- [ ] Fact conflict
- [ ] Timeline conflict
- [ ] Uncertain case
- [ ] Pending update + confirm

## 4. Что нужно проговорить на защите

- [ ] Почему это агент, а не workflow
- [ ] Где находится story memory
- [ ] Какие tools использует orchestrator
- [ ] Какие есть guardrails
- [ ] Почему write path отделён от read path
- [ ] Как система показывает uncertainty
- [ ] Как меряется качество

## 5. Что не должно сломаться

- [ ] `GET /stories`
- [ ] `POST /stories/ingest`
- [ ] `POST /stories/{story_id}/analyze`
- [ ] `POST /stories/{story_id}/pending-updates/{proposal_id}/confirm`
- [ ] fallback в heuristic mode при проблеме с live LLM

## 6. Минимальный критерий готовности к защите

- [ ] Все 6 demo сценариев проходят
- [ ] Обычный smoke suite зелёный
- [ ] Live LLM path хотя бы один раз проверен перед показом
- [ ] Можно объяснить архитектуру за 2-3 минуты
