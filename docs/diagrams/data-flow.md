# Data Flow Diagram

```mermaid
flowchart LR
    scene[Текст новой сцены]
    api[API layer]
    chunker[Chunking and preprocessing]
    retr[Retriever]
    mem[Structured story memory]
    orch[Agent orchestrator]
    proposal[Pending update store]
    logs[Logs and traces]
    result[Final response]

    scene --> api
    api --> chunker
    chunker --> retr
    api --> orch
    mem --> orch
    retr --> orch
    orch --> proposal
    orch --> logs
    orch --> result
```

Назначение диаграммы:
- показать, как входной текст превращается в retrieval evidence и итоговый ответ;
- отделить confirmed memory от pending updates;
- показать, какие данные логируются для observability и evals.
