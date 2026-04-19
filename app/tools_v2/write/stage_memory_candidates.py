from __future__ import annotations

from app.storage.service import StoryMemoryDataService
from app.tools_v2.contracts import ExtractionResult, StagedMemoryResult
from app.tools_v2.helpers import canonicalize, entity_lookup_key


class StageMemoryCandidatesTool:
    name = 'stage_memory_candidates'

    def __init__(self, data_service: StoryMemoryDataService | None = None) -> None:
        self.data_service = data_service or StoryMemoryDataService()

    def _find_existing_entity(self, story_id: str, candidate_name: str, candidate_canonical_name: str, entity_kind: str):
        existing = self.data_service.find_entity_by_name(
            story_id=story_id,
            canonical_name=candidate_canonical_name,
            entity_kind=entity_kind,
        )
        if existing is not None:
            return existing

        lookup_key = entity_lookup_key(candidate_name)
        for entity in self.data_service.list_entities(story_id=story_id, entity_kind=entity_kind, status='confirmed'):
            if entity_lookup_key(entity.name) == lookup_key or entity_lookup_key(entity.canonical_name) == lookup_key:
                return entity
        return None

    def run(self, story_id: str, extraction: ExtractionResult, fragment_id: str | None = None, chunk_ids: list[str] | None = None) -> StagedMemoryResult:
        pending_update = self.data_service.create_pending_update(
            story_id=story_id,
            fragment_id=fragment_id,
            summary=extraction.scene_summary or 'Pending scene extraction update.',
        )
        chunk_ids = chunk_ids or []
        debug_messages: list[str] = []

        created_entity_ids: list[str] = []
        created_event_ids: list[str] = []
        created_fact_ids: list[str] = []
        created_relation_ids: list[str] = []
        entity_ids_by_name: dict[str, str] = {}

        for candidate in extraction.characters + extraction.objects:
            existing = self._find_existing_entity(
                story_id=story_id,
                candidate_name=candidate.name,
                candidate_canonical_name=candidate.canonical_name,
                entity_kind=candidate.kind,
            )
            if existing is not None:
                entity_ids_by_name[candidate.name] = existing.id
                debug_messages.append(f'Найден уже имеющийся {candidate.kind}: "{candidate.name}"')
                continue
            created = self.data_service.create_entity(
                story_id=story_id,
                entity_kind=candidate.kind,
                name=candidate.name,
                canonical_name=candidate.canonical_name,
                summary=candidate.summary,
                status='pending',
                confidence=0.6,
            )
            entity_ids_by_name[candidate.name] = created.id
            created_entity_ids.append(created.id)
            debug_messages.append(f'Найден новый {candidate.kind}: "{candidate.name}"')
            self.data_service.add_pending_update_item(
                pending_update_id=pending_update.id,
                item_type='entity',
                item_id=created.id,
                action='create',
                summary=f'Create {candidate.kind} {candidate.name}',
            )
            if candidate.kind == 'character':
                self.data_service.upsert_character_profile(entity_id=created.id, trait_summary=candidate.summary)
            if candidate.kind == 'object':
                self.data_service.upsert_object_profile(entity_id=created.id, description=candidate.summary)
            for chunk_id in chunk_ids[:1]:
                self.data_service.add_evidence_link(story_id=story_id, target_table='entity', target_id=created.id, chunk_id=chunk_id)

        event_ids_by_title: dict[str, str] = {}
        for event in extraction.events:
            created_event = self.data_service.create_event(
                story_id=story_id,
                title=event.title,
                summary=event.summary,
                timeline_note=event.timeline_note,
                temporal_relation=event.temporal_relation,
                sequence_hint=event.anchor_phrase,
                fragment_id=fragment_id,
                status='pending',
                confidence=0.58,
            )
            event_ids_by_title[event.title] = created_event.id
            created_event_ids.append(created_event.id)
            debug_messages.append(f'Найдено новое событие: "{event.title}"')
            self.data_service.add_pending_update_item(
                pending_update_id=pending_update.id,
                item_type='event',
                item_id=created_event.id,
                action='create',
                summary=f'Create event {event.title}',
            )
            for participant_name in event.participant_names:
                participant_id = entity_ids_by_name.get(participant_name)
                if participant_id is not None:
                    self.data_service.add_event_entity(event_id=created_event.id, entity_id=participant_id, role='participant')
            for chunk_id in chunk_ids[:1]:
                self.data_service.add_evidence_link(story_id=story_id, target_table='event', target_id=created_event.id, chunk_id=chunk_id)

        for fact in extraction.facts:
            created_fact = self.data_service.create_fact(
                story_id=story_id,
                fact_kind=fact.fact_kind,
                summary=fact.summary,
                subject_entity_id=entity_ids_by_name.get(fact.subject_name or ''),
                object_entity_id=entity_ids_by_name.get(fact.object_name or ''),
                event_id=event_ids_by_title.get(fact.related_event_title or ''),
                status='pending',
                confidence=0.56,
            )
            created_fact_ids.append(created_fact.id)
            debug_messages.append(f'Найден новый факт: "{fact.summary}"')
            self.data_service.add_pending_update_item(
                pending_update_id=pending_update.id,
                item_type='fact',
                item_id=created_fact.id,
                action='create',
                summary=f'Create fact {fact.summary}',
            )
            for chunk_id in chunk_ids[:1]:
                self.data_service.add_evidence_link(story_id=story_id, target_table='fact', target_id=created_fact.id, chunk_id=chunk_id)

        for relation in extraction.relations:
            left_id = entity_ids_by_name.get(relation.left_name)
            right_id = entity_ids_by_name.get(relation.right_name)
            if left_id is None or right_id is None:
                continue
            created_relation = self.data_service.create_relation(
                story_id=story_id,
                left_entity_id=left_id,
                right_entity_id=right_id,
                relation_kind=relation.relation_kind,
                summary=relation.summary,
                status='pending',
                confidence=0.55,
            )
            created_relation_ids.append(created_relation.id)
            debug_messages.append(f'Найдена новая связь: "{relation.summary}"')
            self.data_service.add_pending_update_item(
                pending_update_id=pending_update.id,
                item_type='relation',
                item_id=created_relation.id,
                action='create',
                summary=f'Create relation {relation.summary}',
            )
            for chunk_id in chunk_ids[:1]:
                self.data_service.add_evidence_link(story_id=story_id, target_table='relation', target_id=created_relation.id, chunk_id=chunk_id)

        return StagedMemoryResult(
            pending_update=pending_update,
            created_entity_ids=created_entity_ids,
            created_event_ids=created_event_ids,
            created_fact_ids=created_fact_ids,
            created_relation_ids=created_relation_ids,
            debug_messages=debug_messages,
        )
