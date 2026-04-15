from __future__ import annotations

from uuid import uuid4

from app.memory.store import StoryStore
from app.models.schemas import (
    AnalyzeSceneRequest,
    AnalyzeSceneResponse,
    IngestStoryRequest,
    IngestStoryResponse,
    MemoryRecord,
    StoryChunk,
    StoryData,
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

    def analyze_scene(self, story_response, payload: AnalyzeSceneRequest) -> AnalyzeSceneResponse:
        story = self.store.load_story_data(story_response.story_id)
        if story is None:
            raise ValueError("story_not_found")

        tool_traces = []

        chunk_refs, trace = self.tools.search_story_chunks(story, payload.scene_text)
        tool_traces.append(trace)

        memory_records, trace = self.tools.query_story_memory(story, payload.scene_text)
        tool_traces.append(trace)

        character_records, trace = self.tools.get_character_profile(story, payload.scene_text)
        tool_traces.append(trace)

        timeline_records, trace = self.tools.get_timeline_window(story, payload.scene_text)
        tool_traces.append(trace)

        combined_memory: list[MemoryRecord] = []
        seen_ids: set[str] = set()
        for record in story.memory + memory_records + character_records + timeline_records:
            if record.id in seen_ids:
                continue
            seen_ids.add(record.id)
            combined_memory.append(record)

        issues, proposed, issue_type = detect_conflicts(payload.scene_text, combined_memory)

        pending_update_id = None
        if proposed:
            pending_update, trace = self.tools.propose_memory_update(
                summary="Memory updates proposed from scene analysis",
                changes=proposed,
            )
            tool_traces.append(trace)
            if pending_update is not None:
                stored = self.store.add_pending_update(story.story_id, pending_update)
                if stored is not None:
                    pending_update_id = stored.id

        if issues:
            return AnalyzeSceneResponse(
                status="conflict",
                issue_type=issue_type if issue_type != "none" else "mixed",
                explanation=" ".join(issues),
                confidence=0.8,
                evidence_refs=chunk_refs[:3],
                stop_reason="conflict_detected",
                tool_traces=tool_traces,
                memory_update_proposal_id=pending_update_id,
            )

        if not chunk_refs and not combined_memory:
            return AnalyzeSceneResponse(
                status="uncertain",
                issue_type="none",
                explanation=(
                    "Недостаточно релевантной памяти или narrative evidence для уверенной оценки сцены."
                ),
                confidence=0.35,
                evidence_refs=[],
                stop_reason="insufficient_evidence",
                tool_traces=tool_traces,
                memory_update_proposal_id=pending_update_id,
            )

        explanation = "Сцена не показала явных конфликтов с текущей story memory."
        if pending_update_id is not None:
            explanation += " При этом найдено новое знание, вынесенное в pending update."

        return AnalyzeSceneResponse(
            status="no_conflict",
            issue_type="none",
            explanation=explanation,
            confidence=0.72,
            evidence_refs=chunk_refs[:3],
            stop_reason="evidence_threshold_met",
            tool_traces=tool_traces,
            memory_update_proposal_id=pending_update_id,
        )
