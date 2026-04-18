from __future__ import annotations

from uuid import uuid4

from app.storage.models import CharacterProfileRecord, EntityBundle, EntityRecord, EventBundle, EventRecord, EvidenceLinkRecord, FactRecord, ObjectProfileRecord, PendingUpdateItemRecord, PendingUpdateRecord, RelationRecord
from app.storage.repositories._shared import row_to_model


class StoryMemoryRepository:
    def __init__(self, connection) -> None:
        self.connection = connection

    def create_entity(self, story_id: str, entity_kind: str, name: str, canonical_name: str, summary: str, status: str = "pending", confidence: float = 0.5, attributes_json: str = "{}", entity_id: str | None = None) -> EntityRecord:
        entity_id = entity_id or str(uuid4())
        self.connection.execute(
            "INSERT INTO entities(id, story_id, entity_kind, name, canonical_name, summary, status, confidence, attributes_json) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (entity_id, story_id, entity_kind, name, canonical_name, summary, status, confidence, attributes_json),
        )
        self.connection.commit()
        return self.get_entity(entity_id)

    def get_entity(self, entity_id: str) -> EntityRecord | None:
        row = self.connection.execute(
            "SELECT id, story_id, entity_kind, name, canonical_name, summary, status, confidence, created_at, updated_at, attributes_json FROM entities WHERE id = ?",
            (entity_id,),
        ).fetchone()
        return row_to_model(EntityRecord, row) if row else None

    def find_entity_by_name(self, story_id: str, canonical_name: str, entity_kind: str | None = None) -> EntityRecord | None:
        if entity_kind is None:
            row = self.connection.execute(
                "SELECT id, story_id, entity_kind, name, canonical_name, summary, status, confidence, created_at, updated_at, attributes_json FROM entities WHERE story_id = ? AND canonical_name = ? ORDER BY CASE status WHEN 'confirmed' THEN 0 ELSE 1 END, updated_at DESC LIMIT 1",
                (story_id, canonical_name),
            ).fetchone()
        else:
            row = self.connection.execute(
                "SELECT id, story_id, entity_kind, name, canonical_name, summary, status, confidence, created_at, updated_at, attributes_json FROM entities WHERE story_id = ? AND canonical_name = ? AND entity_kind = ? ORDER BY CASE status WHEN 'confirmed' THEN 0 ELSE 1 END, updated_at DESC LIMIT 1",
                (story_id, canonical_name, entity_kind),
            ).fetchone()
        return row_to_model(EntityRecord, row) if row else None

    def list_entities(self, story_id: str, entity_kind: str | None = None, status: str | None = None) -> list[EntityRecord]:
        clauses = ["story_id = ?"]
        params: list[object] = [story_id]
        if entity_kind is not None:
            clauses.append("entity_kind = ?")
            params.append(entity_kind)
        if status is not None:
            clauses.append("status = ?")
            params.append(status)
        rows = self.connection.execute(
            f"SELECT id, story_id, entity_kind, name, canonical_name, summary, status, confidence, created_at, updated_at, attributes_json FROM entities WHERE {' AND '.join(clauses)} ORDER BY canonical_name, created_at",
            params,
        ).fetchall()
        return [row_to_model(EntityRecord, row) for row in rows]

    def upsert_character_profile(self, entity_id: str, trait_summary: str, factual_summary: str = "") -> CharacterProfileRecord:
        self.connection.execute(
            "INSERT INTO character_profiles(entity_id, trait_summary, factual_summary) VALUES (?, ?, ?) ON CONFLICT(entity_id) DO UPDATE SET trait_summary = excluded.trait_summary, factual_summary = excluded.factual_summary",
            (entity_id, trait_summary, factual_summary),
        )
        self.connection.commit()
        return self.get_character_profile(entity_id)

    def get_character_profile(self, entity_id: str) -> CharacterProfileRecord | None:
        row = self.connection.execute("SELECT entity_id, trait_summary, factual_summary FROM character_profiles WHERE entity_id = ?", (entity_id,)).fetchone()
        return row_to_model(CharacterProfileRecord, row) if row else None

    def upsert_object_profile(self, entity_id: str, description: str, current_state_summary: str = "") -> ObjectProfileRecord:
        self.connection.execute(
            "INSERT INTO object_profiles(entity_id, description, current_state_summary) VALUES (?, ?, ?) ON CONFLICT(entity_id) DO UPDATE SET description = excluded.description, current_state_summary = excluded.current_state_summary",
            (entity_id, description, current_state_summary),
        )
        self.connection.commit()
        return self.get_object_profile(entity_id)

    def get_object_profile(self, entity_id: str) -> ObjectProfileRecord | None:
        row = self.connection.execute("SELECT entity_id, description, current_state_summary FROM object_profiles WHERE entity_id = ?", (entity_id,)).fetchone()
        return row_to_model(ObjectProfileRecord, row) if row else None

    def create_event(self, story_id: str, title: str, summary: str, timeline_note: str, anchor_event_id: str | None = None, temporal_relation: str = "unknown", sequence_hint: str | None = None, fragment_id: str | None = None, status: str = "pending", confidence: float = 0.5, attributes_json: str = "{}", event_id: str | None = None) -> EventRecord:
        event_id = event_id or str(uuid4())
        self.connection.execute(
            "INSERT INTO events(id, story_id, title, summary, timeline_note, anchor_event_id, temporal_relation, sequence_hint, fragment_id, status, confidence, attributes_json) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (event_id, story_id, title, summary, timeline_note, anchor_event_id, temporal_relation, sequence_hint, fragment_id, status, confidence, attributes_json),
        )
        self.connection.commit()
        return self.get_event(event_id)

    def get_event(self, event_id: str) -> EventRecord | None:
        row = self.connection.execute("SELECT id, story_id, title, summary, timeline_note, anchor_event_id, temporal_relation, sequence_hint, fragment_id, status, confidence, created_at, updated_at, attributes_json FROM events WHERE id = ?", (event_id,)).fetchone()
        return row_to_model(EventRecord, row) if row else None

    def add_event_entity(self, event_id: str, entity_id: str, role: str = 'participant') -> None:
        self.connection.execute("INSERT OR IGNORE INTO event_entities(event_id, entity_id, role) VALUES (?, ?, ?)", (event_id, entity_id, role))
        self.connection.commit()

    def list_event_entities(self, event_id: str) -> list[tuple[EntityRecord, str]]:
        rows = self.connection.execute(
            "SELECT e.id, e.story_id, e.entity_kind, e.name, e.canonical_name, e.summary, e.status, e.confidence, e.created_at, e.updated_at, e.attributes_json, ee.role FROM event_entities ee JOIN entities e ON e.id = ee.entity_id WHERE ee.event_id = ? ORDER BY ee.role, e.canonical_name",
            (event_id,),
        ).fetchall()
        return [(row_to_model(EntityRecord, row), row['role']) for row in rows]

    def create_fact(self, story_id: str, fact_kind: str, summary: str, subject_entity_id: str | None = None, object_entity_id: str | None = None, event_id: str | None = None, timeline_event_id: str | None = None, valid_from_event_id: str | None = None, valid_to_event_id: str | None = None, status: str = "pending", confidence: float = 0.5, attributes_json: str = "{}", fact_id: str | None = None) -> FactRecord:
        fact_id = fact_id or str(uuid4())
        self.connection.execute(
            "INSERT INTO facts(id, story_id, fact_kind, summary, subject_entity_id, object_entity_id, event_id, timeline_event_id, valid_from_event_id, valid_to_event_id, status, confidence, attributes_json) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (fact_id, story_id, fact_kind, summary, subject_entity_id, object_entity_id, event_id, timeline_event_id, valid_from_event_id, valid_to_event_id, status, confidence, attributes_json),
        )
        self.connection.commit()
        return self.get_fact(fact_id)

    def get_fact(self, fact_id: str) -> FactRecord | None:
        row = self.connection.execute("SELECT id, story_id, fact_kind, summary, subject_entity_id, object_entity_id, event_id, timeline_event_id, valid_from_event_id, valid_to_event_id, status, confidence, created_at, updated_at, attributes_json FROM facts WHERE id = ?", (fact_id,)).fetchone()
        return row_to_model(FactRecord, row) if row else None

    def list_facts_for_entity(self, entity_id: str, status: str | None = None) -> list[FactRecord]:
        if status is None:
            rows = self.connection.execute("SELECT id, story_id, fact_kind, summary, subject_entity_id, object_entity_id, event_id, timeline_event_id, valid_from_event_id, valid_to_event_id, status, confidence, created_at, updated_at, attributes_json FROM facts WHERE subject_entity_id = ? OR object_entity_id = ? ORDER BY created_at", (entity_id, entity_id)).fetchall()
        else:
            rows = self.connection.execute("SELECT id, story_id, fact_kind, summary, subject_entity_id, object_entity_id, event_id, timeline_event_id, valid_from_event_id, valid_to_event_id, status, confidence, created_at, updated_at, attributes_json FROM facts WHERE (subject_entity_id = ? OR object_entity_id = ?) AND status = ? ORDER BY created_at", (entity_id, entity_id, status)).fetchall()
        return [row_to_model(FactRecord, row) for row in rows]

    def create_relation(self, story_id: str, left_entity_id: str, right_entity_id: str, relation_kind: str, summary: str, status: str = "pending", confidence: float = 0.5, attributes_json: str = "{}", relation_id: str | None = None) -> RelationRecord:
        relation_id = relation_id or str(uuid4())
        self.connection.execute(
            "INSERT INTO relations(id, story_id, left_entity_id, right_entity_id, relation_kind, summary, status, confidence, attributes_json) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (relation_id, story_id, left_entity_id, right_entity_id, relation_kind, summary, status, confidence, attributes_json),
        )
        self.connection.commit()
        return self.get_relation(relation_id)

    def get_relation(self, relation_id: str) -> RelationRecord | None:
        row = self.connection.execute("SELECT id, story_id, left_entity_id, right_entity_id, relation_kind, summary, status, confidence, created_at, updated_at, attributes_json FROM relations WHERE id = ?", (relation_id,)).fetchone()
        return row_to_model(RelationRecord, row) if row else None

    def list_relations_for_entity(self, entity_id: str, status: str | None = None) -> list[RelationRecord]:
        if status is None:
            rows = self.connection.execute("SELECT id, story_id, left_entity_id, right_entity_id, relation_kind, summary, status, confidence, created_at, updated_at, attributes_json FROM relations WHERE left_entity_id = ? OR right_entity_id = ? ORDER BY created_at", (entity_id, entity_id)).fetchall()
        else:
            rows = self.connection.execute("SELECT id, story_id, left_entity_id, right_entity_id, relation_kind, summary, status, confidence, created_at, updated_at, attributes_json FROM relations WHERE (left_entity_id = ? OR right_entity_id = ?) AND status = ? ORDER BY created_at", (entity_id, entity_id, status)).fetchall()
        return [row_to_model(RelationRecord, row) for row in rows]

    def add_evidence_link(self, story_id: str, target_table: str, target_id: str, chunk_id: str, note: str = "", evidence_id: str | None = None) -> EvidenceLinkRecord:
        evidence_id = evidence_id or str(uuid4())
        self.connection.execute("INSERT INTO evidence_links(id, story_id, target_table, target_id, chunk_id, note) VALUES (?, ?, ?, ?, ?, ?)", (evidence_id, story_id, target_table, target_id, chunk_id, note))
        self.connection.commit()
        return self.get_evidence_link(evidence_id)

    def get_evidence_link(self, evidence_id: str) -> EvidenceLinkRecord | None:
        row = self.connection.execute("SELECT id, story_id, target_table, target_id, chunk_id, note, created_at FROM evidence_links WHERE id = ?", (evidence_id,)).fetchone()
        return row_to_model(EvidenceLinkRecord, row) if row else None

    def list_evidence_for_target(self, target_table: str, target_id: str) -> list[EvidenceLinkRecord]:
        rows = self.connection.execute("SELECT id, story_id, target_table, target_id, chunk_id, note, created_at FROM evidence_links WHERE target_table = ? AND target_id = ? ORDER BY created_at", (target_table, target_id)).fetchall()
        return [row_to_model(EvidenceLinkRecord, row) for row in rows]

    def create_pending_update(self, story_id: str, summary: str, status: str = "pending", fragment_id: str | None = None, update_id: str | None = None) -> PendingUpdateRecord:
        update_id = update_id or str(uuid4())
        self.connection.execute("INSERT INTO pending_updates(id, story_id, fragment_id, summary, status) VALUES (?, ?, ?, ?, ?)", (update_id, story_id, fragment_id, summary, status))
        self.connection.commit()
        return self.get_pending_update(update_id)

    def get_pending_update(self, update_id: str) -> PendingUpdateRecord | None:
        row = self.connection.execute("SELECT id, story_id, fragment_id, summary, status, created_at, updated_at FROM pending_updates WHERE id = ?", (update_id,)).fetchone()
        return row_to_model(PendingUpdateRecord, row) if row else None

    def list_pending_updates(self, story_id: str, status: str | None = None) -> list[PendingUpdateRecord]:
        if status is None:
            rows = self.connection.execute(
                "SELECT id, story_id, fragment_id, summary, status, created_at, updated_at FROM pending_updates WHERE story_id = ? ORDER BY created_at DESC",
                (story_id,),
            ).fetchall()
        else:
            rows = self.connection.execute(
                "SELECT id, story_id, fragment_id, summary, status, created_at, updated_at FROM pending_updates WHERE story_id = ? AND status = ? ORDER BY created_at DESC",
                (story_id, status),
            ).fetchall()
        return [row_to_model(PendingUpdateRecord, row) for row in rows]

    def set_pending_update_status(self, update_id: str, status: str) -> PendingUpdateRecord | None:
        self.connection.execute(
            "UPDATE pending_updates SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (status, update_id),
        )
        self.connection.commit()
        return self.get_pending_update(update_id)

    def add_pending_update_item(self, pending_update_id: str, item_type: str, item_id: str, action: str, summary: str, link_id: str | None = None) -> PendingUpdateItemRecord:
        link_id = link_id or str(uuid4())
        self.connection.execute("INSERT INTO pending_update_items(id, pending_update_id, item_type, item_id, action, summary) VALUES (?, ?, ?, ?, ?, ?)", (link_id, pending_update_id, item_type, item_id, action, summary))
        self.connection.commit()
        return self.get_pending_update_item(link_id)

    def get_pending_update_item(self, link_id: str) -> PendingUpdateItemRecord | None:
        row = self.connection.execute("SELECT id, pending_update_id, item_type, item_id, action, summary FROM pending_update_items WHERE id = ?", (link_id,)).fetchone()
        return row_to_model(PendingUpdateItemRecord, row) if row else None

    def list_pending_update_items(self, pending_update_id: str) -> list[PendingUpdateItemRecord]:
        rows = self.connection.execute("SELECT id, pending_update_id, item_type, item_id, action, summary FROM pending_update_items WHERE pending_update_id = ? ORDER BY id", (pending_update_id,)).fetchall()
        return [row_to_model(PendingUpdateItemRecord, row) for row in rows]

    def set_record_status(self, item_type: str, item_id: str, status: str) -> None:
        table_map = {
            'entity': 'entities',
            'event': 'events',
            'fact': 'facts',
            'relation': 'relations',
        }
        table_name = table_map.get(item_type)
        if table_name is None:
            return
        self.connection.execute(
            f"UPDATE {table_name} SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (status, item_id),
        )

    def get_entity_bundle(self, entity_id: str) -> EntityBundle | None:
        entity = self.get_entity(entity_id)
        if entity is None:
            return None
        event_rows = self.connection.execute(
            "SELECT ev.id, ev.story_id, ev.title, ev.summary, ev.timeline_note, ev.anchor_event_id, ev.temporal_relation, ev.sequence_hint, ev.fragment_id, ev.status, ev.confidence, ev.created_at, ev.updated_at, ev.attributes_json FROM event_entities ee JOIN events ev ON ev.id = ee.event_id WHERE ee.entity_id = ? ORDER BY ev.created_at",
            (entity_id,),
        ).fetchall()
        return EntityBundle(
            entity=entity,
            character_profile=self.get_character_profile(entity_id) if entity.entity_kind == 'character' else None,
            object_profile=self.get_object_profile(entity_id) if entity.entity_kind == 'object' else None,
            facts=self.list_facts_for_entity(entity_id),
            events=[row_to_model(EventRecord, row) for row in event_rows],
            relations=self.list_relations_for_entity(entity_id),
            evidence_links=self.list_evidence_for_target('entity', entity_id),
        )

    def get_event_bundle(self, event_id: str) -> EventBundle | None:
        event = self.get_event(event_id)
        if event is None:
            return None
        fact_rows = self.connection.execute(
            "SELECT id, story_id, fact_kind, summary, subject_entity_id, object_entity_id, event_id, timeline_event_id, valid_from_event_id, valid_to_event_id, status, confidence, created_at, updated_at, attributes_json FROM facts WHERE event_id = ? OR timeline_event_id = ? ORDER BY created_at",
            (event_id, event_id),
        ).fetchall()
        return EventBundle(
            event=event,
            participants=self.list_event_entities(event_id),
            facts=[row_to_model(FactRecord, row) for row in fact_rows],
            evidence_links=self.list_evidence_for_target('event', event_id),
        )
