# Спецификация Observability / Evals

## Назначение

Проверять, что система достаточно точная, объяснимая и устойчивая, чтобы считаться качественным агентным PoC.

## Обязательная телеметрия

На уровень запроса:
- `request_id`
- `story_id`
- `session_id`
- latency
- model name
- token usage
- `stop_reason`

На уровень tool call:
- `tool_name`
- краткое summary аргументов
- latency
- success / failure
- `error_code`, если вызов упал

На уровень ответа:
- `issue_type`
- `confidence`
- число evidence refs
- был ли создан memory proposal

## Метрики

Агентские метрики:
- `tool selection accuracy`
- среднее число reasoning steps
- `precision` / `recall` по конфликтам
- доля `uncertain_result`

Системные метрики:
- `p95 latency`
- tool failure rate
- degraded success rate
- cost per request

Продуктовые метрики:
- доля полезных замечаний по user feedback;
- доля реально найденных несостыковок;
- время, за которое автор может проверить сцену.

## Eval setup

Нужен небольшой benchmark-набор:
- сцены без конфликтов;
- сцены с factual conflicts;
- сцены с timeline conflicts;
- сцены с намеренной неоднозначностью.

Benchmark должен прогоняться после:
- смены prompt policy;
- изменений tool schema;
- изменений retrieval logic;
- смены model version.

## Значение для агентского трека

На агентском треке недостаточно просто иметь рабочий demo flow. Нужно уметь показать, как вы контролируете качество agent behavior. Именно observability и evals отвечают на вопросы:
- выбирает ли агент правильные tools;
- не переходит ли он в лишние шаги;
- умеет ли он останавливаться;
- честно ли он сообщает о неопределённости;
- как меняется качество после смены prompts, tools или моделей.
