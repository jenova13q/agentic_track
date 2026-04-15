# Demo Runbook

## Цель

Этот файл нужен для быстрого и повторяемого запуска демо перед защитой. Здесь собраны точные шаги, команды и ожидаемые результаты.

## 1. Поднять сервис

### Локально

```bash
uvicorn app.main:app --reload
```

Базовая проверка:

```bash
curl http://127.0.0.1:8000/health
```

Ожидаемый ответ:

```json
{"status":"ok"}
```

## 2. Happy path без конфликта

### 2.1. Ingest

```bash
curl -X POST http://127.0.0.1:8000/stories/ingest \
  -H "Content-Type: application/json" \
  -d "{\"title\":\"Happy Path Demo\",\"text\":\"Day 1. Anna lives in Tashkent. Anna is brave.\n\nDay 2. Boris lives in Samarkand. Boris is kind.\"}"
```

Что сохранить из ответа:
- `story_id`

### 2.2. Analyze

```bash
curl -X POST http://127.0.0.1:8000/stories/{story_id}/analyze \
  -H "Content-Type: application/json" \
  -d "{\"scene_text\":\"Day 3. Anna meets Boris in Tashkent.\"}"
```

Ожидание:
- `status = no_conflict`
- `issue_type = none`
- есть `tool_traces`
- есть `orchestrator_mode`

## 3. Character conflict

### 3.1. Ingest

```bash
curl -X POST http://127.0.0.1:8000/stories/ingest \
  -H "Content-Type: application/json" \
  -d "{\"title\":\"Character Conflict Demo\",\"text\":\"Day 1. Anna lives in Tashkent. Anna is brave.\"}"
```

### 3.2. Analyze

```bash
curl -X POST http://127.0.0.1:8000/stories/{story_id}/analyze \
  -H "Content-Type: application/json" \
  -d "{\"scene_text\":\"Day 2. Anna is cowardly.\"}"
```

Ожидание:
- `status = conflict`
- `issue_type = character`
- `stop_reason = conflict_detected`

## 4. Fact conflict

### 4.1. Ingest

```bash
curl -X POST http://127.0.0.1:8000/stories/ingest \
  -H "Content-Type: application/json" \
  -d "{\"title\":\"Fact Conflict Demo\",\"text\":\"Day 1. Anna lives in Tashkent. Anna is brave.\"}"
```

### 4.2. Analyze

```bash
curl -X POST http://127.0.0.1:8000/stories/{story_id}/analyze \
  -H "Content-Type: application/json" \
  -d "{\"scene_text\":\"Day 2. Anna lives in Samarkand.\"}"
```

Ожидание:
- `status = conflict`
- `issue_type = fact`

## 5. Timeline conflict

### 5.1. Ingest

```bash
curl -X POST http://127.0.0.1:8000/stories/ingest \
  -H "Content-Type: application/json" \
  -d "{\"title\":\"Timeline Conflict Demo\",\"text\":\"Day 1. Anna lives in Tashkent.\n\nDay 2. Boris lives in Samarkand.\"}"
```

### 5.2. Analyze

```bash
curl -X POST http://127.0.0.1:8000/stories/{story_id}/analyze \
  -H "Content-Type: application/json" \
  -d "{\"scene_text\":\"Day 7. Anna meets Boris.\"}"
```

Ожидание:
- `status = conflict`
- `issue_type = timeline`

## 6. Uncertain case

### 6.1. Ingest

```bash
curl -X POST http://127.0.0.1:8000/stories/ingest \
  -H "Content-Type: application/json" \
  -d "{\"title\":\"Uncertain Demo\",\"text\":\"Day 1. Anna lives in Tashkent. Anna is brave.\"}"
```

### 6.2. Analyze

```bash
curl -X POST http://127.0.0.1:8000/stories/{story_id}/analyze \
  -H "Content-Type: application/json" \
  -d "{\"scene_text\":\"Quantum satellites collapse into mirrors.\"}"
```

Ожидание:
- `status = uncertain`
- `stop_reason = insufficient_evidence`

## 7. Pending update и confirm

### 7.1. Ingest

```bash
curl -X POST http://127.0.0.1:8000/stories/ingest \
  -H "Content-Type: application/json" \
  -d "{\"title\":\"Pending Update Demo\",\"text\":\"Day 1. Anna lives in Tashkent. Anna is brave.\"}"
```

### 7.2. Analyze

```bash
curl -X POST http://127.0.0.1:8000/stories/{story_id}/analyze \
  -H "Content-Type: application/json" \
  -d "{\"scene_text\":\"Day 2. Boris lives in Samarkand. Boris is kind.\"}"
```

Из ответа сохранить:
- `memory_update_proposal_id`

### 7.3. Confirm

```bash
curl -X POST http://127.0.0.1:8000/stories/{story_id}/pending-updates/{proposal_id}/confirm
```

Ожидание:
- `status = confirmed`
- `promoted_memory_ids` непустой

## 8. Что проговаривать во время показа

- Оркестратор выбирает tools, а не идёт по жёсткому pipeline.
- Есть `story memory`, retrieval и bounded agent loop.
- Система умеет возвращать `conflict`, `no_conflict`, `uncertain`.
- Обновления памяти не применяются автоматически.
- Даже при недоступности live LLM path остаётся рабочий heuristic fallback.
