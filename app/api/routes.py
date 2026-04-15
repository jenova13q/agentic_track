from fastapi import APIRouter, HTTPException

from app.agent.orchestrator import DemoOrchestrator
from app.memory.store import StoryStore
from app.models.schemas import (
    AnalyzeSceneRequest,
    AnalyzeSceneResponse,
    ConfirmUpdateResponse,
    HealthResponse,
    IngestStoryRequest,
    IngestStoryResponse,
    RejectUpdateResponse,
    StoryListResponse,
    StoryResponse,
)

router = APIRouter()
store = StoryStore()
orchestrator = DemoOrchestrator(store=store)


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok")


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
def analyze_scene(story_id: str, payload: AnalyzeSceneRequest) -> AnalyzeSceneResponse:
    story = store.get_story(story_id)
    if story is None:
        raise HTTPException(status_code=404, detail="story_not_found")
    return orchestrator.analyze_scene(story, payload)


@router.post(
    "/stories/{story_id}/pending-updates/{update_id}/confirm",
    response_model=ConfirmUpdateResponse,
)
def confirm_memory_update(story_id: str, update_id: str) -> ConfirmUpdateResponse:
    update = store.confirm_update(story_id=story_id, update_id=update_id)
    if update is None:
        raise HTTPException(status_code=404, detail="pending_update_not_found")
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
    return RejectUpdateResponse(
        status="rejected",
        story_id=story_id,
        update_id=update_id,
    )
