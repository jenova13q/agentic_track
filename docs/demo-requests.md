# Demo-Ready Requests and Expected Responses

## Цель

Этот файл нужен для защиты и репетиции демо. Здесь зафиксированы готовые запросы, ожидаемое поведение системы и ключевые моменты, которые нужно проговорить во время показа.

## Сценарий 1. Happy path без конфликта

### История для ingestion

```text
Day 1. Anna lives in Tashkent. Anna is brave.

Day 2. Boris lives in Samarkand. Boris is kind.
```

### Запрос на анализ

```json
{
  "scene_text": "Day 3. Anna meets Boris in Tashkent."
}
```

### Ожидаемый результат

- `status`: `no_conflict`
- `issue_type`: `none`
- `stop_reason`: `evidence_threshold_met`
- `memory_update_proposal_id`: может присутствовать, если сцена добавляет новое устойчивое знание
- `tool_traces`: есть
- `orchestrator_mode`: `heuristic` или `llm`

### Что показать

- агент не находит явного конфликта;
- агент использует tools, а не просто отвечает “из головы”;
- при необходимости создаёт pending update, но не пишет confirmed memory автоматически.

## Сценарий 2. Character conflict

### История для ingestion

```text
Day 1. Anna lives in Tashkent. Anna is brave.
```

### Запрос на анализ

```json
{
  "scene_text": "Day 2. Anna is cowardly."
}
```

### Ожидаемый результат

- `status`: `conflict`
- `issue_type`: `character`
- `stop_reason`: `conflict_detected`
- `explanation`: указывает на противоречие между `brave` и `cowardly`

### Что показать

- агент сопоставляет новую сцену с существующей memory facts;
- конфликт формируется как explainable output, а не как “магическое мнение модели”.

## Сценарий 3. Fact conflict

### История для ingestion

```text
Day 1. Anna lives in Tashkent. Anna is brave.
```

### Запрос на анализ

```json
{
  "scene_text": "Day 2. Anna lives in Samarkand."
}
```

### Ожидаемый результат

- `status`: `conflict`
- `issue_type`: `fact`
- `stop_reason`: `conflict_detected`
- `explanation`: указывает на конфликт по месту жительства

### Что показать

- story memory работает как structured source of truth;
- проект не сводится к semantic search по тексту.

## Сценарий 4. Timeline conflict

### История для ingestion

```text
Day 1. Anna lives in Tashkent.

Day 2. Boris lives in Samarkand.
```

### Запрос на анализ

```json
{
  "scene_text": "Day 7. Anna meets Boris."
}
```

### Ожидаемый результат

- `status`: `conflict`
- `issue_type`: `timeline`
- `stop_reason`: `conflict_detected`

### Что показать

- агент использует timeline-aware analysis;
- bounded loop приводит к конкретному типу конфликта.

## Сценарий 5. Uncertain result

### История для ingestion

```text
Day 1. Anna lives in Tashkent. Anna is brave.
```

### Запрос на анализ

```json
{
  "scene_text": "Quantum satellites collapse into mirrors."
}
```

### Ожидаемый результат

- `status`: `uncertain`
- `issue_type`: `none`
- `stop_reason`: `insufficient_evidence`

### Что показать

- система умеет честно сообщать о недостатке evidence;
- это важный элемент агентного качества и guardrails.

## Сценарий 6. Pending update and confirm

### История для ingestion

```text
Day 1. Anna lives in Tashkent. Anna is brave.
```

### Запрос на анализ

```json
{
  "scene_text": "Day 2. Boris lives in Samarkand. Boris is kind."
}
```

### Ожидаемый результат анализа

- `status`: обычно `no_conflict`
- `memory_update_proposal_id`: не `null`

### Следующий шаг

Вызвать:

```text
POST /stories/{story_id}/pending-updates/{proposal_id}/confirm
```

### Ожидаемый результат confirm

- `status`: `confirmed`
- `promoted_memory_ids`: непустой список

### Что показать

- write path отделён от read/analyze path;
- система не делает auto-write в story memory;
- user confirmation встроен в архитектуру, а не добавлен постфактум.

## Короткие тезисы для защиты

- Это агентная система, потому что orchestrator выбирает tools и stop condition, а не идёт по жёстко заданному pipeline.
- Story memory отделена от raw story text и от временного working state.
- Система поддерживает `conflict`, `no_conflict` и `uncertain`, а не притворяется всегда уверенной.
- Pending update / confirm path реализует безопасную memory mutation policy.
- Даже если live LLM path недоступен, heuristic fallback сохраняет работоспособный bounded demo flow.
