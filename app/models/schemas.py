from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class HealthResponse(BaseModel):
    status: Literal["ok"]


class IngestStoryRequest(BaseModel):
    title: str
    text: str = Field(min_length=1)


class IngestStoryResponse(BaseModel):
    status: Literal["ingested"]
    story_id: str
    title: str
    chunk_count: int
    extracted_character_count: int
    extracted_event_count: int


class AnalyzeSceneRequest(BaseModel):
    scene_text: str = Field(min_length=1)
    question: str | None = None


class MemoryRecord(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    type: Literal["character", "event", "relationship", "world_rule", "fact"]
    canonical_value: str
    evidence_refs: list[str] = Field(default_factory=list)
    confidence: float = 0.5
    status: Literal["confirmed", "pending", "conflicted"] = "confirmed"
    updated_at: datetime = Field(default_factory=utc_now)
    attributes: dict[str, Any] = Field(default_factory=dict)


class PendingUpdate(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    summary: str
    changes: list[MemoryRecord]
    status: Literal["pending", "confirmed", "rejected"] = "pending"
    created_at: datetime = Field(default_factory=utc_now)
    promoted_memory_ids: list[str] = Field(default_factory=list)


class StoryChunk(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    story_id: str
    index: int
    source_ref: str
    text: str
    tokens: list[str] = Field(default_factory=list)


class StoryData(BaseModel):
    story_id: str
    title: str
    raw_text: str
    chunks: list[StoryChunk] = Field(default_factory=list)
    memory: list[MemoryRecord] = Field(default_factory=list)
    pending_updates: list[PendingUpdate] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class ToolTrace(BaseModel):
    tool_name: str
    success: bool
    detail: str


class AnalyzeSceneResponse(BaseModel):
    status: Literal["conflict", "no_conflict", "uncertain"]
    issue_type: Literal["character", "timeline", "fact", "none", "mixed"]
    explanation: str
    confidence: float
    evidence_refs: list[str] = Field(default_factory=list)
    stop_reason: str
    orchestrator_mode: Literal["heuristic", "llm"]
    tool_traces: list[ToolTrace] = Field(default_factory=list)
    memory_update_proposal_id: str | None = None


class ConfirmUpdateResponse(BaseModel):
    status: Literal["confirmed"]
    story_id: str
    update_id: str
    promoted_memory_ids: list[str]


class StoryResponse(BaseModel):
    story_id: str
    title: str
    memory: list[MemoryRecord]
    pending_updates: list[PendingUpdate]
    chunk_count: int


class StoryListItem(BaseModel):
    story_id: str
    title: str
    chunk_count: int
    pending_update_count: int


class StoryListResponse(BaseModel):
    stories: list[StoryListItem]
