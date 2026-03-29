# C4 Context

```mermaid
flowchart LR
    author[Писатель / сценарист]
    ui[Интерфейс Story Consistency Agent]
    system[Story Consistency Agent]
    llm[LLM API]
    embed[Embedding API]
    research[External Research API]
    storage[(Story Storage)]
    obs[(Logs / Metrics / Traces)]

    author --> ui
    ui --> system
    system --> llm
    system --> embed
    system --> research
    system --> storage
    system --> obs
```

Назначение диаграммы:
- показать границу системы;
- отделить внешние model providers от внутренних компонентов PoC;
- показать, что пользователь взаимодействует не с LLM напрямую, а с агентной системой.
