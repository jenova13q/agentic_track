from __future__ import annotations

import json
from pathlib import Path

from app.core.config import settings
from app.models.schemas import AgentTrace, ObservabilitySummaryResponse, RecentTracesResponse


class ObservabilityStore:
    def __init__(self, base_dir: Path | None = None) -> None:
        self.base_dir = base_dir or settings.telemetry_dir
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.trace_file = self.base_dir / "agent_traces.jsonl"

    def record_trace(self, trace: AgentTrace) -> None:
        with self.trace_file.open("a", encoding="utf-8") as handle:
            handle.write(trace.model_dump_json())
            handle.write("\n")

    def recent_traces(self, limit: int = 20) -> RecentTracesResponse:
        traces = self._load_traces()
        return RecentTracesResponse(traces=traces[-limit:])

    def summary(self) -> ObservabilitySummaryResponse:
        traces = self._load_traces()
        analysis_traces = [trace for trace in traces if trace.event_type == "analysis"]
        average_latency = sum(trace.latency_ms for trace in traces) / len(traces) if traces else 0.0
        average_tool_calls = (
            sum(trace.tool_call_count for trace in analysis_traces) / len(analysis_traces)
            if analysis_traces
            else 0.0
        )
        average_agent_steps = (
            sum(trace.agent_step_count for trace in analysis_traces) / len(analysis_traces)
            if analysis_traces
            else 0.0
        )
        last_stop_reasons = [
            trace.stop_reason
            for trace in analysis_traces[-5:]
            if trace.stop_reason
        ]
        return ObservabilitySummaryResponse(
            total_events=len(traces),
            analysis_requests=len(analysis_traces),
            conflict_count=len([trace for trace in analysis_traces if trace.status == "conflict"]),
            uncertain_count=len([trace for trace in analysis_traces if trace.status == "uncertain"]),
            no_conflict_count=len([trace for trace in analysis_traces if trace.status == "no_conflict"]),
            confirmed_updates=len([trace for trace in traces if trace.event_type == "confirm_update"]),
            rejected_updates=len([trace for trace in traces if trace.event_type == "reject_update"]),
            average_latency_ms=round(average_latency, 2),
            average_tool_calls=round(average_tool_calls, 2),
            average_agent_steps=round(average_agent_steps, 2),
            last_stop_reasons=last_stop_reasons,
        )

    def _load_traces(self) -> list[AgentTrace]:
        if not self.trace_file.exists():
            return []

        traces: list[AgentTrace] = []
        for line in self.trace_file.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            traces.append(AgentTrace.model_validate(json.loads(line)))
        return traces
