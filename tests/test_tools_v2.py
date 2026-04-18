from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from app.storage import Database, StoryMemoryDataService
from app.tools_v2 import CollectRelevantContextTool, ExtractSceneElementsTool, StageFragmentTool, StageMemoryCandidatesTool


class ToolsV2Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / 'story_memory.sqlite3'
        self.data_service = StoryMemoryDataService(database=Database(self.db_path))
        self.extract_tool = ExtractSceneElementsTool()
        self.context_tool = CollectRelevantContextTool(self.data_service)
        self.stage_fragment_tool = StageFragmentTool(self.data_service)
        self.stage_memory_tool = StageMemoryCandidatesTool(self.data_service)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_extract_scene_elements_returns_structured_candidates(self) -> None:
        result = self.extract_tool.run(
            'Лев был смелый. Лев встретил Павла у пристани. Перед отплытием Лев потерял ключ.'
        )

        character_names = [candidate.name for candidate in result.characters]
        self.assertIn('Лев', character_names)
        self.assertTrue(any(name.startswith('Павл') for name in character_names))
        self.assertEqual(['ключ'], [candidate.name for candidate in result.objects])
        self.assertTrue(any(fact.fact_kind == 'character_trait' for fact in result.facts))
        self.assertTrue(any(fact.fact_kind == 'object_state' for fact in result.facts))
        self.assertTrue(any(event.timeline_note for event in result.events))
        self.assertEqual(1, len(result.relations))

    def test_collect_relevant_context_uses_entity_evidence_and_chunk_windows(self) -> None:
        story = self.data_service.create_story(title='Колокол без моря')
        fragment = self.data_service.add_fragment(
            story_id=story.id,
            text='Лев ждал у причала. Он слушал колокол.',
            fragment_kind='scene',
            status='confirmed',
            source_label='scene:1',
            fragment_order=0,
        )
        first = self.data_service.add_chunk(story_id=story.id, fragment_id=fragment.id, chunk_index=0, source_ref='chunk:0', text='Лев ждал у причала.', token_count=4)
        self.data_service.add_chunk(story_id=story.id, fragment_id=fragment.id, chunk_index=1, source_ref='chunk:1', text='Он слушал колокол.', token_count=3)
        lev = self.data_service.create_entity(
            story_id=story.id,
            entity_kind='character',
            name='Лев',
            canonical_name='лев',
            summary='Главный герой.',
            status='confirmed',
            confidence=0.9,
        )
        self.data_service.add_evidence_link(story_id=story.id, target_table='entity', target_id=lev.id, chunk_id=first.id)

        result = self.context_tool.run(story_id=story.id, scene_text='Он молчал и смотрел на воду.')

        self.assertEqual(['он'], result.unresolved_references)
        self.assertEqual(1, len(result.chunk_windows))
        self.assertEqual('chunk:1', result.chunk_windows[0].center.source_ref)

    def test_stage_fragment_and_memory_candidates_create_pending_records(self) -> None:
        story = self.data_service.create_story(title='Колокол без моря')
        scene_text = 'Лев встретил Павла у пристани. Перед отплытием Лев потерял ключ.'
        extraction = self.extract_tool.run(scene_text)
        staged_fragment = self.stage_fragment_tool.run(story_id=story.id, scene_text=scene_text)
        staged_memory = self.stage_memory_tool.run(
            story_id=story.id,
            extraction=extraction,
            fragment_id=staged_fragment.fragment_id,
            chunk_ids=staged_fragment.chunk_ids,
        )

        pending_fragment = self.data_service.list_fragments(story.id, status='pending')
        pending_entities = self.data_service.list_entities(story.id, status='pending')
        pending_items = self.data_service.list_pending_update_items(staged_memory.pending_update.id)

        self.assertEqual(1, len(pending_fragment))
        self.assertGreaterEqual(len(staged_fragment.chunk_ids), 1)
        self.assertGreaterEqual(len(pending_entities), 3)
        self.assertGreaterEqual(len(staged_memory.created_event_ids), 1)
        self.assertGreaterEqual(len(staged_memory.created_fact_ids), 1)
        self.assertGreaterEqual(len(pending_items), 3)


if __name__ == '__main__':
    unittest.main()
