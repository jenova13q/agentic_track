# Demo Critical Path

## Цель

Это короткий checklist именно под запись финального видео. Здесь только то, что нужно для цельного показа системы.

## 1. Перед записью

- [ ] `.env` заполнен
- [ ] backend поднят
- [ ] `GET /health` отвечает `ok`
- [ ] web UI открывается по `GET /`
- [ ] при необходимости прогнан `tests/live_smoke.py`

## 2. Что обязательно должно работать

- [ ] ingest истории
- [ ] analyze scene end-to-end
- [ ] есть `conflict`
- [ ] есть `no_conflict`
- [ ] есть `uncertain`
- [ ] есть `tool_traces`
- [ ] есть `orchestrator_mode`
- [ ] есть `pending update`
- [ ] работает `confirm`
- [ ] работает `reject`
- [ ] работает `append scene`
- [ ] observability summary и traces открываются

## 3. Сценарии показа

- [ ] consistent scene
- [ ] character conflict
- [ ] fact conflict
- [ ] timeline conflict
- [ ] uncertain case
- [ ] pending update + confirm
- [ ] object-state conflict

## 4. Что нужно проговорить

- [ ] почему это агент, а не workflow
- [ ] где находится story memory
- [ ] какие tools выбирает orchestrator
- [ ] почему write path отделён от read path
- [ ] как система показывает uncertainty
- [ ] какие guardrails есть
- [ ] как наблюдается качество через traces
- [ ] почему graph memory и MEMO 0 вынесены в дальнейшую работу

## 5. Что не должно сломаться во время видео

- [ ] `GET /`
- [ ] `GET /stories`
- [ ] `POST /stories/ingest`
- [ ] `POST /stories/{story_id}/analyze`
- [ ] `POST /stories/{story_id}/append-scene`
- [ ] `POST /stories/{story_id}/pending-updates/{proposal_id}/confirm`
- [ ] `POST /stories/{story_id}/pending-updates/{proposal_id}/reject`
- [ ] `GET /observability/summary`

## 6. Минимальный критерий готовности к записи

- [ ] обычный smoke suite зелёный
- [ ] demo benchmark зелёный
- [ ] live LLM path хотя бы один раз проверен перед показом
- [ ] можно объяснить архитектуру за 2-3 минуты
- [ ] можно показать всю систему от загрузки рассказа до observability
