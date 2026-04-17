from time import perf_counter
import json
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse

from app.agent.orchestrator import DemoOrchestrator
from app.memory.store import StoryStore
from app.models.schemas import (
    AgentTrace,
    AnalyzeSceneRequest,
    AnalyzeSceneResponse,
    AppendSceneRequest,
    AppendSceneResponse,
    ConfirmUpdateResponse,
    HealthResponse,
    IngestStoryRequest,
    IngestStoryResponse,
    ObservabilitySummaryResponse,
    RecentTracesResponse,
    RejectUpdateResponse,
    StoryListResponse,
    StoryResponse,
)
from app.observability.service import ObservabilityStore

router = APIRouter()
store = StoryStore()
orchestrator = DemoOrchestrator(store=store)
observability = ObservabilityStore()
data_dir = Path("data")


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok")


@router.get("/")
def root() -> FileResponse:
    return FileResponse("app/frontend/index.html")


@router.get("/stories", response_model=StoryListResponse)
def list_stories() -> StoryListResponse:
    return store.list_stories()


@router.post("/stories/ingest", response_model=IngestStoryResponse)
def ingest_story(payload: IngestStoryRequest) -> IngestStoryResponse:
    return orchestrator.ingest_story(payload)


@router.get("/stories/{story_id}", response_model=StoryResponse)
def get_story(story_id: str) -> StoryResponse:
    story = store.get_story(story_id)
    if story is None:
        raise HTTPException(status_code=404, detail="story_not_found")
    return story


@router.post("/stories/{story_id}/analyze", response_model=AnalyzeSceneResponse)
def analyze_scene(story_id: str, payload: AnalyzeSceneRequest, request: Request) -> AnalyzeSceneResponse:
    story = store.get_story(story_id)
    if story is None:
        raise HTTPException(status_code=404, detail="story_not_found")

    started_at = perf_counter()
    response = orchestrator.analyze_scene(story, payload)
    observability.record_trace(
        AgentTrace(
            request_id=request.state.request_id,
            story_id=story_id,
            event_type="analysis",
            status=response.status,
            issue_type=response.issue_type,
            stop_reason=response.stop_reason,
            orchestrator_mode=response.orchestrator_mode,
            model_name=orchestrator.llm.model,
            latency_ms=round((perf_counter() - started_at) * 1000, 2),
            agent_step_count=response.agent_step_count,
            tool_call_count=response.tool_call_count,
            evidence_ref_count=len(response.evidence_refs),
            created_pending_update=response.memory_update_proposal_id is not None,
            update_id=response.memory_update_proposal_id,
            tool_traces=response.tool_traces,
        )
    )
    return response


@router.post("/stories/{story_id}/append-scene", response_model=AppendSceneResponse)
def append_scene(story_id: str, payload: AppendSceneRequest) -> AppendSceneResponse:
    story = store.get_story(story_id)
    if story is None:
        raise HTTPException(status_code=404, detail="story_not_found")
    return orchestrator.append_scene(story_id=story_id, payload=payload)


@router.post(
    "/stories/{story_id}/pending-updates/{update_id}/confirm",
    response_model=ConfirmUpdateResponse,
)
def confirm_memory_update(story_id: str, update_id: str) -> ConfirmUpdateResponse:
    update = store.confirm_update(story_id=story_id, update_id=update_id)
    if update is None:
        raise HTTPException(status_code=404, detail="pending_update_not_found")
    observability.record_trace(
        AgentTrace(
            request_id=f"confirm:{update_id}",
            story_id=story_id,
            event_type="confirm_update",
            status="confirmed",
            latency_ms=0.0,
            update_id=update_id,
        )
    )
    return ConfirmUpdateResponse(
        status="confirmed",
        story_id=story_id,
        update_id=update_id,
        promoted_memory_ids=update.promoted_memory_ids,
    )


@router.post(
    "/stories/{story_id}/pending-updates/{update_id}/reject",
    response_model=RejectUpdateResponse,
)
def reject_memory_update(story_id: str, update_id: str) -> RejectUpdateResponse:
    update = store.reject_update(story_id=story_id, update_id=update_id)
    if update is None:
        raise HTTPException(status_code=404, detail="pending_update_not_found")
    observability.record_trace(
        AgentTrace(
            request_id=f"reject:{update_id}",
            story_id=story_id,
            event_type="reject_update",
            status="rejected",
            latency_ms=0.0,
            update_id=update_id,
        )
    )
    return RejectUpdateResponse(
        status="rejected",
        story_id=story_id,
        update_id=update_id,
    )


@router.get("/observability/summary", response_model=ObservabilitySummaryResponse)
def get_observability_summary() -> ObservabilitySummaryResponse:
    return observability.summary()


@router.get("/observability/traces", response_model=RecentTracesResponse)
def get_recent_observability_traces() -> RecentTracesResponse:
    return observability.recent_traces()


@router.get("/demo/story")
def get_demo_story() -> dict[str, str]:
    return {"text": data_dir.joinpath("demo-story.txt").read_text(encoding="utf-8")}


@router.get("/demo/writing-session")
def get_demo_writing_session() -> dict[str, object]:
    return json.loads(data_dir.joinpath("demo-writing-session.json").read_text(encoding="utf-8"))


@router.get("/demo/scenarios")
def get_demo_scenarios() -> list[dict[str, object]]:
    return json.loads(data_dir.joinpath("demo-scenarios.json").read_text(encoding="utf-8"))
