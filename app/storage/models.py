from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

StatusLiteral = Literal["pending", "confirmed", "rejected", "conflicted"]
EntityKind = Literal["character", "object", "location", "group"]
TemporalRelation = Literal["before", "after", "during", "parallel", "unknown"]
PendingItemType = Literal["entity", "event", "fact", "relation", "fragment"]
PendingAction = Literal["create", "update", "close"]


@dataclass(slots=True)
class StoryRecord:
    id: str
    title: str
    synopsis: str = ""
    created_at: str = ""
    updated_at: str = ""


@dataclass(slots=True)
class FragmentRecord:
    id: str
    story_id: str
    fragment_kind: str
    status: StatusLiteral
    source_label: str
    text: str
    fragment_order: int | None = None
    created_at: str = ""
    updated_at: str = ""


@dataclass(slots=True)
class ChunkRecord:
    id: str
    story_id: str
    fragment_id: str
    chunk_index: int
    source_ref: str
    text: str
    token_count: int = 0
    created_at: str = ""


@dataclass(slots=True)
class EntityRecord:
    id: str
    story_id: str
    entity_kind: EntityKind
    name: str
    canonical_name: str
    summary: str
    status: StatusLiteral
    confidence: float
    created_at: str = ""
    updated_at: str = ""
    attributes_json: str = "{}"


@dataclass(slots=True)
class CharacterProfileRecord:
    entity_id: str
    trait_summary: str
    factual_summary: str = ""


@dataclass(slots=True)
class ObjectProfileRecord:
    entity_id: str
    description: str
    current_state_summary: str = ""


@dataclass(slots=True)
class EventRecord:
    id: str
    story_id: str
    title: str
    summary: str
    timeline_note: str
    anchor_event_id: str | None
    temporal_relation: TemporalRelation
    sequence_hint: str | None
    fragment_id: str | None
    status: StatusLiteral
    confidence: float
    created_at: str = ""
    updated_at: str = ""
    attributes_json: str = "{}"


@dataclass(slots=True)
class FactRecord:
    id: str
    story_id: str
    fact_kind: str
    summary: str
    subject_entity_id: str | None
    object_entity_id: str | None
    event_id: str | None
    timeline_event_id: str | None
    valid_from_event_id: str | None
    valid_to_event_id: str | None
    status: StatusLiteral
    confidence: float
    created_at: str = ""
    updated_at: str = ""
    attributes_json: str = "{}"


@dataclass(slots=True)
class RelationRecord:
    id: str
    story_id: str
    left_entity_id: str
    right_entity_id: str
    relation_kind: str
    summary: str
    status: StatusLiteral
    confidence: float
    created_at: str = ""
    updated_at: str = ""
    attributes_json: str = "{}"


@dataclass(slots=True)
class EvidenceLinkRecord:
    id: str
    story_id: str
    target_table: str
    target_id: str
    chunk_id: str
    note: str = ""
    created_at: str = ""


@dataclass(slots=True)
class PendingUpdateRecord:
    id: str
    story_id: str
    fragment_id: str | None
    summary: str
    status: StatusLiteral
    created_at: str = ""
    updated_at: str = ""


@dataclass(slots=True)
class PendingUpdateItemRecord:
    id: str
    pending_update_id: str
    item_type: PendingItemType
    item_id: str
    action: PendingAction
    summary: str


@dataclass(slots=True)
class EntityBundle:
    entity: EntityRecord
    character_profile: CharacterProfileRecord | None = None
    object_profile: ObjectProfileRecord | None = None
    facts: list[FactRecord] = field(default_factory=list)
    events: list[EventRecord] = field(default_factory=list)
    relations: list[RelationRecord] = field(default_factory=list)
    evidence_links: list[EvidenceLinkRecord] = field(default_factory=list)


@dataclass(slots=True)
class EventBundle:
    event: EventRecord
    participants: list[tuple[EntityRecord, str]] = field(default_factory=list)
    facts: list[FactRecord] = field(default_factory=list)
    evidence_links: list[EvidenceLinkRecord] = field(default_factory=list)


@dataclass(slots=True)
class ChunkWindow:
    center: ChunkRecord
    previous_chunks: list[ChunkRecord] = field(default_factory=list)
    next_chunks: list[ChunkRecord] = field(default_factory=list)
