# Demo-Ready Requests and Expected Responses

## Цель

Этот файл нужен для репетиции защиты и быстрой ручной проверки API.

Ниже не “абстрактные” кейсы, а запросы под наш текущий литературный demo-world.

## Сценарий 1. Consistent scene

### История для ingestion

```text
К вечеру Приморск всегда становился похож на плохо вытертое зеркало. Лев живёт в Приморске. Лев был смелый.

На следующее утро Павел приехал с острова. Павел живёт в Маячном. Павел был добрый. Лев встречает Павла у рыбного склада.

Тем же вечером они открыли журнал маяка и решили отплыть к острову перед рассветом.
```

### Запрос

```json
{
  "scene_text": "Перед рассветом Павел ждал Льва у причала с термосом, и они молча отвязали лодку."
}
```

### Ожидание

- `status = no_conflict`
- `issue_type = none`

## Сценарий 2. Character conflict

### Запрос

```json
{
  "scene_text": "Перед выходом к воде Лев был трусливый и боялся даже посмотреть на бухту."
}
```

### Ожидание

- `status = conflict`
- `issue_type = character`

## Сценарий 3. Fact conflict

### Запрос

```json
{
  "scene_text": "Тем же вечером Павел живёт в Приморске и говорит, что никогда не бывал на Маячном."
}
```

### Ожидание

- `status = conflict`
- `issue_type = fact`

## Сценарий 4. Timeline conflict

### История для ingestion

```text
На следующее утро Павел приехал с острова. Павел живёт в Маячном.

Тем же вечером Лев и Павел решили отплыть к острову перед рассветом.
```

### Запрос

```json
{
  "scene_text": "Через неделю, на следующее утро после разговора, они только собрались выйти к причалу."
}
```

### Ожидание

- `status = conflict`
- `issue_type = timeline`

## Сценарий 5. Uncertain result

### Запрос

```json
{
  "scene_text": "Под мостовой запели стеклянные рыбы, и город ответил им зелёным светом."
}
```

### Ожидание

- `status = uncertain`
- `issue_type = none`
- `stop_reason = insufficient_evidence`

## Сценарий 6. Object-state conflict

### История для ingestion

```text
Лев жил в Приморске. Тем же вечером Лев потерял ключ у пристани.
```

### Запрос

```json
{
  "scene_text": "Через час Лев держал ключ в ладони, хотя никто его не находил."
}
```

### Ожидание

- `status = conflict`
- `issue_type = object`

## Сценарий 7. Pending update and confirm

### Запрос

```json
{
  "scene_text": "Перед рассветом Павел ждал Льва у причала с термосом."
}
```

### Ожидание

- `status = no_conflict`
- `memory_update_proposal_id != null`

Следующий шаг:

```text
POST /stories/{story_id}/pending-updates/{proposal_id}/confirm
```

Ожидание:

- `status = confirmed`
- `promoted_memory_ids` непустой

## Что показывать в ответе

На защите полезно подсвечивать не только `status`, но и:
- `issue_type`
- `explanation`
- `tool_traces`
- `orchestrator_mode`
- `stop_reason`
- `memory_update_proposal_id`
