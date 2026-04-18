from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class PendingUpdateView(BaseModel):
    id: str
    summary: str
    status: str
    item_count: int
    fragment_id: str | None = None


class StoryListItemV2(BaseModel):
    story_id: str
    title: str
    confirmed_fragment_count: int
    total_chunk_count: int
    pending_update_count: int


class StoryListResponseV2(BaseModel):
    stories: list[StoryListItemV2]


class StoryResponseV2(BaseModel):
    story_id: str
    title: str
    confirmed_fragment_count: int
    pending_fragment_count: int
    total_chunk_count: int
    memory_counts: dict[str, int] = Field(default_factory=dict)
    pending_updates: list[PendingUpdateView] = Field(default_factory=list)


class IngestStoryResponseV2(BaseModel):
    status: Literal['ingested']
    story_id: str
    title: str
    initial_analysis_status: str
    pending_update_id: str | None = None
    orchestrator_mode: Literal['heuristic', 'llm']


class AnalyzeSceneResponseV2(BaseModel):
    status: Literal['conflict', 'no_conflict', 'uncertain']
    issue_type: Literal['character', 'fact', 'timeline', 'object', 'mixed', 'none']
    explanation: str
    confidence: float
    stop_reason: str
    orchestrator_mode: Literal['heuristic', 'llm']
    step_count: int
    staged_update_id: str | None = None
    staged_fragment_id: str | None = None
    staged_item_counts: dict[str, int] = Field(default_factory=dict)
    extracted_counts: dict[str, int] = Field(default_factory=dict)
    unresolved_references: list[str] = Field(default_factory=list)
