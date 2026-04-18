from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from app.storage import Database, StoryMemoryDataService


class StoryMemoryDataServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / 'story_memory.sqlite3'
        self.service = StoryMemoryDataService(database=Database(self.db_path))

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_can_persist_story_fragments_and_chunks(self) -> None:
        story = self.service.create_story(title='Колокол без моря')
        fragment = self.service.add_fragment(
            story_id=story.id,
            text='Лев живёт в Приморске.',
            fragment_kind='scene',
            status='confirmed',
            source_label='scene:1',
            fragment_order=0,
        )
        chunk = self.service.add_chunk(
            story_id=story.id,
            fragment_id=fragment.id,
            chunk_index=0,
            source_ref='chunk:0',
            text='Лев живёт в Приморске.',
            token_count=4,
        )

        fragments = self.service.list_fragments(story.id, status='confirmed')
        chunks = self.service.list_chunks(story.id)

        self.assertEqual(1, len(fragments))
        self.assertEqual(fragment.id, fragments[0].id)
        self.assertEqual(1, len(chunks))
        self.assertEqual(chunk.id, chunks[0].id)

    def test_can_build_character_bundle_with_facts_events_relations_and_evidence(self) -> None:
        story = self.service.create_story(title='Колокол без моря')
        fragment = self.service.add_fragment(
            story_id=story.id,
            text='Лев встретил Павла у причала.',
            fragment_kind='scene',
            status='confirmed',
            source_label='scene:2',
            fragment_order=0,
        )
        chunk = self.service.add_chunk(
            story_id=story.id,
            fragment_id=fragment.id,
            chunk_index=0,
            source_ref='chunk:0',
            text='Лев встретил Павла у причала.',
            token_count=5,
        )

        lev = self.service.create_entity(
            story_id=story.id,
            entity_kind='character',
            name='Лев',
            canonical_name='лев',
            summary='Смотритель почты в Приморске',
            status='confirmed',
            confidence=0.9,
        )
        self.service.upsert_character_profile(
            entity_id=lev.id,
            trait_summary='Смелый, наблюдательный, упрямый.',
            factual_summary='Живёт в Приморске.',
        )
        pavel = self.service.create_entity(
            story_id=story.id,
            entity_kind='character',
            name='Павел',
            canonical_name='павел',
            summary='Смотритель маяка',
            status='confirmed',
            confidence=0.88,
        )
        event = self.service.create_event(
            story_id=story.id,
            title='Встреча у причала',
            summary='Лев встречает Павла у причала.',
            timeline_note='Тем же утром',
            status='confirmed',
            confidence=0.84,
            fragment_id=fragment.id,
        )
        self.service.add_event_entity(event_id=event.id, entity_id=lev.id, role='participant')
        self.service.add_event_entity(event_id=event.id, entity_id=pavel.id, role='participant')
        fact = self.service.create_fact(
            story_id=story.id,
            fact_kind='character_trait',
            summary='Лев был смелый.',
            subject_entity_id=lev.id,
            event_id=event.id,
            status='confirmed',
            confidence=0.93,
        )
        relation = self.service.create_relation(
            story_id=story.id,
            left_entity_id=lev.id,
            right_entity_id=pavel.id,
            relation_kind='acquaintance',
            summary='Лев и Павел знакомы и доверяют друг другу.',
            status='confirmed',
            confidence=0.81,
        )
        self.service.add_evidence_link(
            story_id=story.id,
            target_table='entity',
            target_id=lev.id,
            chunk_id=chunk.id,
            note='Первое явное упоминание Льва',
        )

        bundle = self.service.get_entity_bundle(lev.id)

        self.assertIsNotNone(bundle)
        assert bundle is not None
        self.assertEqual('Лев', bundle.entity.name)
        self.assertIsNotNone(bundle.character_profile)
        self.assertEqual(1, len(bundle.facts))
        self.assertEqual(fact.id, bundle.facts[0].id)
        self.assertEqual(1, len(bundle.events))
        self.assertEqual(event.id, bundle.events[0].id)
        self.assertEqual(1, len(bundle.relations))
        self.assertEqual(relation.id, bundle.relations[0].id)
        self.assertEqual(1, len(bundle.evidence_links))

    def test_can_get_chunk_window_for_pronoun_resolution(self) -> None:
        story = self.service.create_story(title='Колокол без моря')
        fragment = self.service.add_fragment(
            story_id=story.id,
            text='Лев ждал у пристани. Он слушал звон колокола. Потом он увидел Павла.',
            fragment_kind='scene',
            status='confirmed',
            source_label='scene:3',
            fragment_order=0,
        )
        first = self.service.add_chunk(story_id=story.id, fragment_id=fragment.id, chunk_index=0, source_ref='chunk:0', text='Лев ждал у пристани.', token_count=4)
        self.service.add_chunk(story_id=story.id, fragment_id=fragment.id, chunk_index=1, source_ref='chunk:1', text='Он слушал звон колокола.', token_count=4)
        third = self.service.add_chunk(story_id=story.id, fragment_id=fragment.id, chunk_index=2, source_ref='chunk:2', text='Потом он увидел Павла.', token_count=4)

        window = self.service.get_chunk_window(third.id, before=2, after=0)

        self.assertIsNotNone(window)
        assert window is not None
        self.assertEqual('chunk:2', window.center.source_ref)
        self.assertEqual(['chunk:0', 'chunk:1'], [chunk.source_ref for chunk in window.previous_chunks])

    def test_can_persist_pending_update_items(self) -> None:
        story = self.service.create_story(title='Колокол без моря')
        fragment = self.service.add_fragment(
            story_id=story.id,
            text='Павел привёз старый ключ.',
            fragment_kind='scene',
            status='pending',
            source_label='submission:1',
        )
        entity = self.service.create_entity(
            story_id=story.id,
            entity_kind='object',
            name='Ключ',
            canonical_name='ключ',
            summary='Старый ключ от дома на острове.',
            status='pending',
            confidence=0.67,
        )
        update = self.service.create_pending_update(
            story_id=story.id,
            fragment_id=fragment.id,
            summary='Добавить ключ как важный объект сцены.',
        )
        item = self.service.add_pending_update_item(
            pending_update_id=update.id,
            item_type='entity',
            item_id=entity.id,
            action='create',
            summary='Создать объект ключ в story memory.',
        )

        self.assertEqual(update.id, item.pending_update_id)
        self.assertEqual('entity', item.item_type)

    def test_can_confirm_pending_update_and_promote_fragment_and_records(self) -> None:
        story = self.service.create_story(title='Колокол без моря')
        fragment = self.service.add_fragment(
            story_id=story.id,
            text='Лев потерял ключ у пристани.',
            fragment_kind='scene',
            status='pending',
            source_label='submission:2',
        )
        entity = self.service.create_entity(
            story_id=story.id,
            entity_kind='object',
            name='ключ',
            canonical_name='ключ',
            summary='Ключ от дома на острове.',
            status='pending',
            confidence=0.7,
        )
        update = self.service.create_pending_update(
            story_id=story.id,
            fragment_id=fragment.id,
            summary='Добавить сцену и объект ключ.',
        )
        self.service.add_pending_update_item(
            pending_update_id=update.id,
            item_type='entity',
            item_id=entity.id,
            action='create',
            summary='Создать объект ключ.',
        )

        confirmed = self.service.confirm_pending_update(update.id)

        self.assertIsNotNone(confirmed)
        assert confirmed is not None
        self.assertEqual('confirmed', confirmed.status)
        self.assertEqual('confirmed', self.service.list_fragments(story.id)[0].status)
        self.assertEqual('confirmed', self.service.list_entities(story.id)[0].status)

    def test_can_reject_pending_update_and_mark_records_rejected(self) -> None:
        story = self.service.create_story(title='Колокол без моря')
        fragment = self.service.add_fragment(
            story_id=story.id,
            text='Павел принёс чужой колокол.',
            fragment_kind='scene',
            status='pending',
            source_label='submission:3',
        )
        entity = self.service.create_entity(
            story_id=story.id,
            entity_kind='object',
            name='колокол',
            canonical_name='колокол',
            summary='Старый корабельный колокол.',
            status='pending',
            confidence=0.62,
        )
        update = self.service.create_pending_update(
            story_id=story.id,
            fragment_id=fragment.id,
            summary='Добавить колокол.',
        )
        self.service.add_pending_update_item(
            pending_update_id=update.id,
            item_type='entity',
            item_id=entity.id,
            action='create',
            summary='Создать объект колокол.',
        )

        rejected = self.service.reject_pending_update(update.id)

        self.assertIsNotNone(rejected)
        assert rejected is not None
        self.assertEqual('rejected', rejected.status)
        self.assertEqual('rejected', self.service.list_fragments(story.id)[0].status)
        self.assertEqual('rejected', self.service.list_entities(story.id)[0].status)


if __name__ == '__main__':
    unittest.main()
