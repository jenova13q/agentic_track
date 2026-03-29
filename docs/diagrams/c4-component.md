# C4 Component

```mermaid
flowchart LR
    req[Request Handler]
    planner[Action Planner]
    policy[Execution Policy]
    state[Working State Manager]
    toolrouter[Tool Router]
    synth[Answer Synthesizer]
    updater[Memory Proposal Builder]
    stop[Stop and Confidence Checker]

    req --> state
    state --> planner
    policy --> planner
    planner --> toolrouter
    toolrouter --> state
    state --> stop
    stop --> planner
    stop --> synth
    synth --> updater
```

Назначение диаграммы:
- объяснить внутреннее устройство агентного ядра;
- показать, что planner, state manager и stop checker разделены;
- подчеркнуть наличие отдельного memory proposal path.
