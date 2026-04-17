from __future__ import annotations

from uuid import uuid4

from app.agent.llm import LLMDecisionEngine
from app.core.config import settings
from app.memory.store import StoryStore
from app.models.schemas import (
    AgentWorkingState,
    AnalyzeSceneRequest,
    AnalyzeSceneResponse,
    AppendSceneRequest,
    AppendSceneResponse,
    IngestStoryRequest,
    IngestStoryResponse,
    MemoryRecord,
    StoryChunk,
    StoryData,
    ToolTrace,
)
from app.tools.services import (
    ToolService,
    build_story_chunks,
    detect_conflicts,
    extract_memory_records,
)


class DemoOrchestrator:
    def __init__(self, store: StoryStore) -> None:
        self.store = store
        self.tools = ToolService()
        self.llm = LLMDecisionEngine()

    def ingest_story(self, payload: IngestStoryRequest) -> IngestStoryResponse:
        story_id = str(uuid4())
        chunk_models = [StoryChunk(**chunk) for chunk in build_story_chunks(story_id, payload.text)]
        memory = extract_memory_records(payload.text)
        story = StoryData(
            story_id=story_id,
            title=payload.title,
            raw_text=payload.text,
            chunks=chunk_models,
            memory=memory,
            pending_updates=[],
        )
        self.store.create_story(story)
        event_count = len([item for item in memory if item.type == "event"])
        character_count = len([item for item in memory if item.type == "character"])
        return IngestStoryResponse(
            status="ingested",
            story_id=story_id,
            title=payload.title,
            chunk_count=len(chunk_models),
            extracted_character_count=character_count,
            extracted_event_count=event_count,
        )

    def append_scene(self, story_id: str, payload: AppendSceneRequest) -> AppendSceneResponse:
        story = self.store.load_story_data(story_id)
        if story is None:
            raise ValueError("story_not_found")

        new_chunks = build_story_chunks(story.story_id, payload.scene_text)
        next_index = len(story.chunks)
        chunk_models: list[StoryChunk] = []
        for offset, chunk in enumerate(new_chunks):
            chunk["index"] = next_index + offset
            chunk["source_ref"] = f"chunk:{next_index + offset}"
            chunk_models.append(StoryChunk(**chunk))

        appended_memory = extract_memory_records(payload.scene_text)
        story.raw_text = f"{story.raw_text}\n\n{payload.scene_text}".strip()
        story.chunks.extend(chunk_models)
        story.memory.extend(appended_memory)
        self.store.append_scene(story)

        return AppendSceneResponse(
            status="appended",
            story_id=story.story_id,
            chunk_count=len(story.chunks),
            appended_memory_count=len(appended_memory),
        )

    def analyze_scene(self, story_response, payload: AnalyzeSceneRequest) -> AnalyzeSceneResponse:
        story = self.store.load_story_data(story_response.story_id)
        if story is None:
            raise ValueError("story_not_found")

        working_state = AgentWorkingState(
            request_id=str(uuid4()),
            story_id=story.story_id,
            current_goal=payload.question or "Проверить сцену на консистентность с памятью истории.",
        )

        tool_plan, planning_reason = self.llm.choose_tool_plan(
            story_title=story.title,
            scene_text=payload.scene_text,
            question=payload.question,
            memory_preview=[record.canonical_value for record in story.memory[:8]],
        )

        tool_traces: list[ToolTrace] = [
            ToolTrace(
                step_index=0,
                tool_name="tool_planner",
                success=True,
                detail=f"{planning_reason}: {', '.join(tool_plan)}",
            )
        ]

        chunk_refs: list[str] = []
        memory_records: list[MemoryRecord] = []
        character_records: list[MemoryRecord] = []
        timeline_records: list[MemoryRecord] = []

        for tool_name in tool_plan:
            if working_state.current_step >= settings.max_agent_steps:
                working_state.stop_reason = "max_agent_steps_exceeded"
                break
            if working_state.tool_calls >= settings.max_tool_calls:
                working_state.stop_reason = "max_tool_calls_exceeded"
                break

            previous_evidence_count = len(working_state.evidence_refs)
            previous_memory_count = len(memory_records) + len(character_records) + len(timeline_records)
            current_chunk_refs: list[str] = []

            if tool_name == "search_story_chunks":
                current_chunk_refs, trace = self.tools.search_story_chunks(story, payload.scene_text)
                chunk_refs = current_chunk_refs
            elif tool_name == "query_story_memory":
                memory_records, trace = self.tools.query_story_memory(story, payload.scene_text)
            elif tool_name == "get_character_profile":
                character_records, trace = self.tools.get_character_profile(story, payload.scene_text)
            elif tool_name == "get_timeline_window":
                timeline_records, trace = self.tools.get_timeline_window(story, payload.scene_text)
            else:
                continue

            working_state.current_step += 1
            working_state.tool_calls += 1
            working_state.tool_history.append(tool_name)
            trace.step_index = working_state.current_step
            tool_traces.append(trace)

            for ref in current_chunk_refs:
                if ref not in working_state.evidence_refs:
                    working_state.evidence_refs.append(ref)

            current_memory_count = len(memory_records) + len(character_records) + len(timeline_records)
            if len(working_state.evidence_refs) == previous_evidence_count and current_memory_count == previous_memory_count:
                working_state.no_new_evidence_steps += 1
            else:
                working_state.no_new_evidence_steps = 0

            if working_state.no_new_evidence_steps >= 2:
                working_state.stop_reason = "no_new_evidence"
                break

        combined_memory: list[MemoryRecord] = []
        seen_ids: set[str] = set()
        for record in memory_records + character_records + timeline_records:
            if record.id in seen_ids:
                continue
            seen_ids.add(record.id)
            combined_memory.append(record)

        issues, proposed, issue_type = detect_conflicts(payload.scene_text, combined_memory)
        working_state.findings = issues

        pending_update_id = None
        if proposed and working_state.tool_calls < settings.max_tool_calls:
            pending_update, trace = self.tools.propose_memory_update(
                summary="Memory updates proposed from scene analysis",
                changes=proposed,
            )
            working_state.current_step += 1
            working_state.tool_calls += 1
            trace.step_index = working_state.current_step
            tool_traces.append(trace)
            if pending_update is not None:
                stored = self.store.add_pending_update(story.story_id, pending_update)
                if stored is not None:
                    pending_update_id = stored.id

        llm_explanation = None
        if issues:
            llm_explanation = self.llm.synthesize_explanation(
                scene_text=payload.scene_text,
                issues=issues,
                evidence_refs=chunk_refs,
                proposed_change_count=len(proposed),
            )
        orchestrator_mode = "llm" if self.llm.enabled else "heuristic"

        if issues:
            working_state.confidence = 0.8
            working_state.stop_reason = working_state.stop_reason or "conflict_detected"
            return AnalyzeSceneResponse(
                status="conflict",
                issue_type=issue_type if issue_type != "none" else "mixed",
                explanation=llm_explanation or " ".join(issues),
                confidence=working_state.confidence,
                evidence_refs=working_state.evidence_refs[:3],
                stop_reason=working_state.stop_reason,
                orchestrator_mode=orchestrator_mode,
                agent_step_count=working_state.current_step,
                tool_call_count=working_state.tool_calls,
                tool_traces=tool_traces,
                memory_update_proposal_id=pending_update_id,
            )

        if not working_state.evidence_refs and not combined_memory:
            working_state.confidence = 0.35
            working_state.stop_reason = "insufficient_evidence"
            return AnalyzeSceneResponse(
                status="uncertain",
                issue_type="none",
                explanation="Недостаточно релевантной памяти или narrative evidence для уверенной оценки сцены.",
                confidence=working_state.confidence,
                evidence_refs=[],
                stop_reason=working_state.stop_reason,
                orchestrator_mode=orchestrator_mode,
                agent_step_count=working_state.current_step,
                tool_call_count=working_state.tool_calls,
                tool_traces=tool_traces,
                memory_update_proposal_id=pending_update_id,
            )

        explanation = "Сцена не показала явных конфликтов с текущей story memory."
        if pending_update_id is not None:
            explanation += " При этом найдено новое знание, вынесенное в pending update."

        working_state.confidence = 0.72
        working_state.stop_reason = working_state.stop_reason or "evidence_threshold_met"
        return AnalyzeSceneResponse(
            status="no_conflict",
            issue_type="none",
            explanation=explanation,
            confidence=working_state.confidence,
            evidence_refs=working_state.evidence_refs[:3],
            stop_reason=working_state.stop_reason,
            orchestrator_mode=orchestrator_mode,
            agent_step_count=working_state.current_step,
            tool_call_count=working_state.tool_calls,
            tool_traces=tool_traces,
            memory_update_proposal_id=pending_update_id,
        )
