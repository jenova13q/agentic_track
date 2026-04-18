from __future__ import annotations

from dataclasses import dataclass, field

from app.storage.models import ChunkWindow, EntityBundle, PendingUpdateRecord


@dataclass(slots=True)
class SceneEntityCandidate:
    kind: str
    name: str
    canonical_name: str
    summary: str = ""


@dataclass(slots=True)
class SceneEventCandidate:
    title: str
    summary: str
    timeline_note: str = ""
    temporal_relation: str = "unknown"
    participant_names: list[str] = field(default_factory=list)
    object_names: list[str] = field(default_factory=list)
    anchor_phrase: str | None = None


@dataclass(slots=True)
class SceneFactCandidate:
    fact_kind: str
    summary: str
    subject_name: str | None = None
    object_name: str | None = None
    related_event_title: str | None = None


@dataclass(slots=True)
class SceneRelationCandidate:
    left_name: str
    right_name: str
    relation_kind: str
    summary: str


@dataclass(slots=True)
class ExtractionResult:
    characters: list[SceneEntityCandidate] = field(default_factory=list)
    objects: list[SceneEntityCandidate] = field(default_factory=list)
    events: list[SceneEventCandidate] = field(default_factory=list)
    facts: list[SceneFactCandidate] = field(default_factory=list)
    relations: list[SceneRelationCandidate] = field(default_factory=list)
    temporal_hints: list[str] = field(default_factory=list)
    unresolved_references: list[str] = field(default_factory=list)
    scene_summary: str = ""


@dataclass(slots=True)
class ContextCollectionResult:
    matched_entity_bundles: list[EntityBundle] = field(default_factory=list)
    chunk_windows: list[ChunkWindow] = field(default_factory=list)
    unresolved_references: list[str] = field(default_factory=list)


@dataclass(slots=True)
class StagedFragmentResult:
    fragment_id: str
    chunk_ids: list[str] = field(default_factory=list)


@dataclass(slots=True)
class StagedMemoryResult:
    pending_update: PendingUpdateRecord
    created_entity_ids: list[str] = field(default_factory=list)
    created_event_ids: list[str] = field(default_factory=list)
    created_fact_ids: list[str] = field(default_factory=list)
    created_relation_ids: list[str] = field(default_factory=list)
