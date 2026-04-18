from time import perf_counter

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse

from app.agent_v2 import StoryConsistencyOrchestratorV2
from app.models.api_v2 import AnalyzeSceneResponseV2, IngestStoryResponseV2, PendingUpdateView, StoryListItemV2, StoryListResponseV2, StoryResponseV2
from app.models.schemas import AgentTrace, AnalyzeSceneRequest, ConfirmUpdateResponse, HealthResponse, IngestStoryRequest, ObservabilitySummaryResponse, RecentTracesResponse, RejectUpdateResponse
from app.observability.service import ObservabilityStore
from app.storage.service import StoryMemoryDataService

router = APIRouter()
data_service = StoryMemoryDataService()
orchestrator_v2 = StoryConsistencyOrchestratorV2(data_service=data_service)
observability = ObservabilityStore()


@router.get('/health', response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status='ok')


@router.get('/')
def root() -> FileResponse:
    return FileResponse('app/frontend/index.html')


@router.get('/stories', response_model=StoryListResponseV2)
def list_stories() -> StoryListResponseV2:
    items: list[StoryListItemV2] = []
    for story in data_service.list_stories():
        confirmed_fragment_count = len(data_service.list_fragments(story.id, status='confirmed'))
        total_chunk_count = len(data_service.list_chunks(story.id))
        pending_update_count = len(data_service.list_pending_updates(story.id, status='pending'))
        items.append(
            StoryListItemV2(
                story_id=story.id,
                title=story.title,
                confirmed_fragment_count=confirmed_fragment_count,
                total_chunk_count=total_chunk_count,
                pending_update_count=pending_update_count,
            )
        )
    return StoryListResponseV2(stories=items)


@router.post('/stories/ingest', response_model=IngestStoryResponseV2)
def ingest_story(payload: IngestStoryRequest, request: Request) -> IngestStoryResponseV2:
    story = data_service.create_story(title=payload.title)
    started_at = perf_counter()
    result = orchestrator_v2.analyze_scene(story.id, payload.text)
    observability.record_trace(
        AgentTrace(
            request_id=request.state.request_id,
            story_id=story.id,
            event_type='analysis',
            status=result.status,
            issue_type=result.issue_type,
            stop_reason='ingest_analysis',
            orchestrator_mode=result.orchestrator_mode,
            model_name=orchestrator_v2.llm_adapter.model,
            latency_ms=round((perf_counter() - started_at) * 1000, 2),
            agent_step_count=result.step_count,
            tool_call_count=0,
            evidence_ref_count=0,
            created_pending_update=result.staged_update_id is not None,
            update_id=result.staged_update_id,
            tool_traces=[],
        )
    )
    return IngestStoryResponseV2(
        status='ingested',
        story_id=story.id,
        title=story.title,
        initial_analysis_status=result.status,
        pending_update_id=result.staged_update_id,
        orchestrator_mode=result.orchestrator_mode,
    )


@router.get('/stories/{story_id}', response_model=StoryResponseV2)
def get_story(story_id: str) -> StoryResponseV2:
    story = next((item for item in data_service.list_stories() if item.id == story_id), None)
    if story is None:
        raise HTTPException(status_code=404, detail='story_not_found')

    entities = data_service.list_entities(story_id)
    events = data_service.list_events(story_id, status='confirmed')
    facts = data_service.list_facts(story_id, status='confirmed')
    relations = data_service.list_relations(story_id, status='confirmed')
    pending_updates = data_service.list_pending_updates(story_id)
    pending_views = [
        PendingUpdateView(
            id=update.id,
            summary=update.summary,
            status=update.status,
            item_count=len(data_service.list_pending_update_items(update.id)),
            fragment_id=update.fragment_id,
        )
        for update in pending_updates
    ]
    memory_counts = {
        'characters': len([entity for entity in entities if entity.entity_kind == 'character' and entity.status == 'confirmed']),
        'objects': len([entity for entity in entities if entity.entity_kind == 'object' and entity.status == 'confirmed']),
        'locations': len([entity for entity in entities if entity.entity_kind == 'location' and entity.status == 'confirmed']),
        'groups': len([entity for entity in entities if entity.entity_kind == 'group' and entity.status == 'confirmed']),
        'facts': len(facts),
        'events': len(events),
        'relations': len(relations),
    }
    return StoryResponseV2(
        story_id=story.id,
        title=story.title,
        confirmed_fragment_count=len(data_service.list_fragments(story.id, status='confirmed')),
        pending_fragment_count=len(data_service.list_fragments(story.id, status='pending')),
        total_chunk_count=len(data_service.list_chunks(story.id)),
        memory_counts=memory_counts,
        pending_updates=pending_views,
    )


@router.post('/stories/{story_id}/analyze', response_model=AnalyzeSceneResponseV2)
def analyze_scene(story_id: str, payload: AnalyzeSceneRequest, request: Request) -> AnalyzeSceneResponseV2:
    story = next((item for item in data_service.list_stories() if item.id == story_id), None)
    if story is None:
        raise HTTPException(status_code=404, detail='story_not_found')

    started_at = perf_counter()
    result = orchestrator_v2.analyze_scene(story_id=story_id, scene_text=payload.scene_text, user_comment=payload.question)
    observability.record_trace(
        AgentTrace(
            request_id=request.state.request_id,
            story_id=story_id,
            event_type='analysis',
            status=result.status,
            issue_type=result.issue_type,
            stop_reason='analysis_complete',
            orchestrator_mode=result.orchestrator_mode,
            model_name=orchestrator_v2.llm_adapter.model,
            latency_ms=round((perf_counter() - started_at) * 1000, 2),
            agent_step_count=result.step_count,
            tool_call_count=0,
            evidence_ref_count=sum(len(window.previous_chunks) + len(window.next_chunks) + 1 for window in result.context.chunk_windows),
            created_pending_update=result.staged_update_id is not None,
            update_id=result.staged_update_id,
            tool_traces=[],
        )
    )
    return AnalyzeSceneResponseV2(
        status=result.status,
        issue_type=result.issue_type,
        explanation=result.explanation,
        confidence=result.confidence,
        stop_reason='analysis_complete',
        orchestrator_mode=result.orchestrator_mode,
        step_count=result.step_count,
        staged_update_id=result.staged_update_id,
        staged_fragment_id=result.staged_fragment_id,
        staged_item_counts=result.staged_item_counts,
        extracted_counts={
            'characters': len(result.extraction.characters),
            'objects': len(result.extraction.objects),
            'events': len(result.extraction.events),
            'facts': len(result.extraction.facts),
            'relations': len(result.extraction.relations),
        },
        unresolved_references=result.extraction.unresolved_references,
    )


@router.post('/stories/{story_id}/pending-updates/{update_id}/confirm', response_model=ConfirmUpdateResponse)
def confirm_memory_update(story_id: str, update_id: str) -> ConfirmUpdateResponse:
    update = data_service.confirm_pending_update(update_id)
    if update is None or update.story_id != story_id:
        raise HTTPException(status_code=404, detail='pending_update_not_found')
    observability.record_trace(
        AgentTrace(
            request_id=f'confirm:{update_id}',
            story_id=story_id,
            event_type='confirm_update',
            status='confirmed',
            latency_ms=0.0,
            update_id=update_id,
        )
    )
    item_ids = [item.item_id for item in data_service.list_pending_update_items(update_id)]
    return ConfirmUpdateResponse(status='confirmed', story_id=story_id, update_id=update_id, promoted_memory_ids=item_ids)


@router.post('/stories/{story_id}/pending-updates/{update_id}/reject', response_model=RejectUpdateResponse)
def reject_memory_update(story_id: str, update_id: str) -> RejectUpdateResponse:
    update = data_service.reject_pending_update(update_id)
    if update is None or update.story_id != story_id:
        raise HTTPException(status_code=404, detail='pending_update_not_found')
    observability.record_trace(
        AgentTrace(
            request_id=f'reject:{update_id}',
            story_id=story_id,
            event_type='reject_update',
            status='rejected',
            latency_ms=0.0,
            update_id=update_id,
        )
    )
    return RejectUpdateResponse(status='rejected', story_id=story_id, update_id=update_id)


@router.get('/observability/summary', response_model=ObservabilitySummaryResponse)
def get_observability_summary() -> ObservabilitySummaryResponse:
    return observability.summary()


@router.get('/observability/traces', response_model=RecentTracesResponse)
def get_recent_observability_traces() -> RecentTracesResponse:
    return observability.recent_traces()
