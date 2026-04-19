from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from app.agent_v2 import LLMAdapterV2, StoryConsistencyOrchestratorV2
from app.storage import Database, StoryMemoryDataService


class AgentV2Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / 'story_memory.sqlite3'
        self.data_service = StoryMemoryDataService(database=Database(self.db_path))
        self.adapter = LLMAdapterV2()
        self.adapter.api_key = None
        self.orchestrator = StoryConsistencyOrchestratorV2(data_service=self.data_service, llm_adapter=self.adapter)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_orchestrator_v2_stages_pending_update_for_non_conflicting_scene(self) -> None:
        story = self.data_service.create_story(title='Колокол без моря')

        result = self.orchestrator.analyze_scene(
            story_id=story.id,
            scene_text='Лев встретил Павла у пристани. Перед отплытием Лев потерял ключ.',
        )

        self.assertEqual('no_conflict', result.status)
        self.assertIsNotNone(result.staged_fragment_id)
        self.assertIsNotNone(result.staged_update_id)
        self.assertGreaterEqual(result.staged_item_counts.get('entities', 0), 2)

    def test_orchestrator_v2_detects_object_conflict_and_does_not_stage(self) -> None:
        story = self.data_service.create_story(title='Колокол без моря')
        fragment = self.data_service.add_fragment(
            story_id=story.id,
            text='Перед отплытием Лев потерял ключ у пристани.',
            fragment_kind='scene',
            status='confirmed',
            source_label='scene:1',
            fragment_order=0,
        )
        chunk = self.data_service.add_chunk(
            story_id=story.id,
            fragment_id=fragment.id,
            chunk_index=0,
            source_ref='chunk:0',
            text='Перед отплытием Лев потерял ключ у пристани.',
            token_count=6,
        )
        lev = self.data_service.create_entity(
            story_id=story.id,
            entity_kind='character',
            name='Лев',
            canonical_name='лев',
            summary='Главный герой.',
            status='confirmed',
            confidence=0.9,
        )
        key = self.data_service.create_entity(
            story_id=story.id,
            entity_kind='object',
            name='ключ',
            canonical_name='ключ',
            summary='Старый ключ.',
            status='confirmed',
            confidence=0.9,
        )
        self.data_service.upsert_object_profile(entity_id=key.id, description='Старый ключ.', current_state_summary='Потерян у пристани.')
        self.data_service.create_fact(
            story_id=story.id,
            fact_kind='object_state',
            summary='Лев потерял ключ у пристани.',
            subject_entity_id=lev.id,
            object_entity_id=key.id,
            status='confirmed',
            confidence=0.95,
        )
        self.data_service.add_evidence_link(story_id=story.id, target_table='entity', target_id=key.id, chunk_id=chunk.id)

        result = self.orchestrator.analyze_scene(
            story_id=story.id,
            scene_text='На острове Лев вынул ключ из кармана и открыл дверь.',
        )

        self.assertEqual('conflict', result.status)
        self.assertEqual('object', result.issue_type)
        self.assertIsNone(result.staged_fragment_id)
        self.assertIsNone(result.staged_update_id)

    def test_orchestrator_v2_returns_uncertain_when_reference_context_is_missing(self) -> None:
        story = self.data_service.create_story(title='Колокол без моря')

        result = self.orchestrator.analyze_scene(
            story_id=story.id,
            scene_text='Он долго смотрел на воду и молчал.',
        )

        self.assertEqual('uncertain', result.status)
        self.assertIsNone(result.staged_update_id)

    def test_orchestrator_v2_detects_internal_character_conflict_in_same_fragment(self) -> None:
        story = self.data_service.create_story(title='Колокол без моря')

        result = self.orchestrator.analyze_scene(
            story_id=story.id,
            scene_text='Лев был смелый. Перед выходом к воде Лев был трусливый и боялся даже посмотреть на бухту.',
        )

        self.assertEqual('conflict', result.status)
        self.assertEqual('character', result.issue_type)
        self.assertEqual('internal_character_conflict', result.stop_reason)
        self.assertIsNone(result.staged_update_id)

    def test_internal_character_conflict_precheck_runs_even_when_llm_key_is_present(self) -> None:
        story = self.data_service.create_story(title='Колокол без моря')
        self.adapter.api_key = 'fake-key'

        result = self.orchestrator.analyze_scene(
            story_id=story.id,
            scene_text='Лев был смелый. Перед выходом к воде Лев был трусливый и боялся даже посмотреть на бухту.',
        )

        self.assertEqual('conflict', result.status)
        self.assertEqual('character', result.issue_type)
        self.assertEqual('internal_character_conflict', result.stop_reason)

    def test_orchestrator_returns_debug_payload(self) -> None:
        story = self.data_service.create_story(title='Колокол без моря')

        result = self.orchestrator.analyze_scene(
            story_id=story.id,
            scene_text='Лев встретил Павла у пристани. Перед отплытием Лев потерял ключ.',
        )

        self.assertIn('messages', result.debug_payload)
        self.assertIn('extraction', result.debug_payload)
        self.assertIn('staging', result.debug_payload)
        self.assertGreaterEqual(len(result.debug_payload['messages']), 1)


if __name__ == '__main__':
    unittest.main()
