import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from app.agent_v2 import LLMAdapterV2, StoryConsistencyOrchestratorV2
from app.api import routes
from app.main import app
from app.observability.service import ObservabilityStore
from app.storage import Database, StoryMemoryDataService
from app.tools_v2 import ExtractSceneElementsTool
from tests.fake_extraction import FakeSceneExtractionBackend


class StoryApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        db_path = Path(self.temp_dir.name) / 'api_story_memory.sqlite3'
        self.data_service = StoryMemoryDataService(database=Database(db_path))
        self.observability = ObservabilityStore(base_dir=Path(self.temp_dir.name) / 'telemetry')
        self.adapter = LLMAdapterV2()
        self.adapter.api_key = None
        self.extract_tool = ExtractSceneElementsTool(backend=FakeSceneExtractionBackend())
        self.orchestrator = StoryConsistencyOrchestratorV2(data_service=self.data_service, llm_adapter=self.adapter, extract_tool=self.extract_tool)
        routes.data_service = self.data_service
        routes.orchestrator_v2 = self.orchestrator
        routes.observability = self.observability
        self.client = TestClient(app)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_health_endpoint(self) -> None:
        response = self.client.get('/health')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'status': 'ok'})

    def test_root_serves_ui(self) -> None:
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn('Story Consistency Agent', response.text)
        self.assertIn('Создать историю и проверить текст', response.text)

    def test_ingest_creates_story_and_pending_update(self) -> None:
        response = self.client.post(
            '/stories/ingest',
            json={
                'title': 'Колокол без моря',
                'text': 'Лев встретил Павла у пристани. Перед отплытием Лев потерял ключ.',
            },
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual('ingested', payload['status'])
        self.assertEqual('no_conflict', payload['initial_analysis_status'])
        self.assertIsNotNone(payload['pending_update_id'])
        self.assertIn('debug', payload)
        self.assertIn('extracted_counts', payload)

        story = self.client.get(f"/stories/{payload['story_id']}").json()
        self.assertEqual(1, story['pending_fragment_count'])
        self.assertEqual(1, len(story['pending_updates']))

    def test_ingest_bootstraps_initial_story_even_with_pronouns(self) -> None:
        response = self.client.post(
            '/stories/ingest',
            json={
                'title': 'Черновик истории',
                'text': 'Лев долго стоял у причала. Он слушал воду и не отвечал Павлу.',
            },
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual('ingested', payload['status'])
        self.assertIsNotNone(payload['pending_update_id'])
        self.assertIn(payload['initial_analysis_status'], {'no_conflict', 'uncertain'})
        self.assertGreaterEqual(payload['extracted_counts']['characters'], 1)

    def test_analyze_scene_stages_uncertain_non_conflicting_piece_with_new_entities(self) -> None:
        story_id = self._create_empty_story()

        response = self.client.post(
            f'/stories/{story_id}/analyze',
            json={'scene_text': 'Перед рассветом Павел ждал Льва у причала с термосом, и они молча отвязали лодку.'},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual('uncertain', payload['status'])
        self.assertIsNotNone(payload['staged_update_id'])
        self.assertGreaterEqual(payload['extracted_counts']['characters'], 2)

    def test_analyze_scene_can_stage_pending_update(self) -> None:
        story_id = self._create_empty_story()

        response = self.client.post(
            f'/stories/{story_id}/analyze',
            json={'scene_text': 'Лев встретил Павла у пристани. Перед отплытием Лев потерял ключ.'},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual('no_conflict', payload['status'])
        self.assertIsNotNone(payload['staged_update_id'])
        self.assertGreaterEqual(payload['staged_item_counts']['entities'], 2)
        self.assertIn('debug', payload)
        self.assertIn('messages', payload['debug'])
        self.assertIn('extraction', payload['debug'])
        self.assertGreaterEqual(len(payload['debug']['messages']), 1)

    def test_analyze_scene_detects_object_conflict(self) -> None:
        story_id = self._create_story_with_confirmed_loss()

        response = self.client.post(
            f'/stories/{story_id}/analyze',
            json={'scene_text': 'На острове Лев вынул ключ из кармана и открыл дверь.'},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual('conflict', payload['status'])
        self.assertEqual('object', payload['issue_type'])
        self.assertIsNone(payload['staged_update_id'])

    def test_analyze_scene_detects_internal_character_conflict(self) -> None:
        story_id = self._create_empty_story()

        response = self.client.post(
            f'/stories/{story_id}/analyze',
            json={'scene_text': 'Лев был смелый. Перед выходом к воде Лев был трусливый и боялся даже посмотреть на бухту.'},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual('conflict', payload['status'])
        self.assertEqual('character', payload['issue_type'])
        self.assertIsNone(payload['staged_update_id'])
        self.assertEqual('internal_character_conflict', payload['stop_reason'])
        self.assertIn('debug', payload)

    def test_story_flow_e2e_preserves_entities_and_detects_character_conflict(self) -> None:
        ingest = self.client.post(
            '/stories/ingest',
            json={
                'title': 'Колокол без моря',
                'text': 'К вечеру Приморск всегда становился похож на плохо вытертое зеркало. Лев живёт в Приморске. Лев был смелый. На следующее утро Павел приехал с острова. Павел живёт в Маячном. Павел был добрый. Лев встречает Павла у рыбного склада.',
            },
        )
        self.assertEqual(200, ingest.status_code)
        ingest_payload = ingest.json()
        self.assertEqual(2, ingest_payload['extracted_counts']['characters'])
        self.assertEqual(3, ingest_payload['extracted_counts']['locations'])
        self.assertEqual(2, ingest_payload['extracted_counts']['events'])
        self.assertEqual(5, ingest_payload['extracted_counts']['facts'])
        self.assertEqual(1, ingest_payload['extracted_counts']['relations'])
        self.assertEqual(['Лев', 'Павел'], [item['name'] for item in ingest_payload['debug']['extraction']['characters']])
        self.assertEqual(['Приморск', 'Маячный', 'рыбный склад'], [item['name'] for item in ingest_payload['debug']['extraction']['locations']])

        story_id = ingest_payload['story_id']
        update_id = ingest_payload['pending_update_id']
        confirm = self.client.post(f'/stories/{story_id}/pending-updates/{update_id}/confirm')
        self.assertEqual(200, confirm.status_code)

        analyze = self.client.post(
            f'/stories/{story_id}/analyze',
            json={'scene_text': 'Лев был смелый. Перед выходом к воде Лев был трусливый и боялся даже посмотреть на бухту.'},
        )
        self.assertEqual(200, analyze.status_code)
        analyze_payload = analyze.json()
        self.assertEqual('conflict', analyze_payload['status'])
        self.assertEqual('character', analyze_payload['issue_type'])
        matched = analyze_payload['debug']['context']['matched_entities']
        self.assertTrue(any(item['name'] == 'Лев' for item in matched))
        self.assertEqual(['Лев'], [item['name'] for item in analyze_payload['debug']['extraction']['characters']])
        self.assertEqual(2, analyze_payload['extracted_counts']['facts'])

    def test_confirm_pending_update_promotes_fragment_and_memory(self) -> None:
        ingest = self.client.post(
            '/stories/ingest',
            json={
                'title': 'Колокол без моря',
                'text': 'Лев встретил Павла у пристани. Перед отплытием Лев потерял ключ.',
            },
        )
        story_id = ingest.json()['story_id']
        update_id = ingest.json()['pending_update_id']

        confirm = self.client.post(f'/stories/{story_id}/pending-updates/{update_id}/confirm')
        self.assertEqual(confirm.status_code, 200)
        self.assertEqual('confirmed', confirm.json()['status'])
        self.assertGreaterEqual(len(confirm.json()['promoted_memory_ids']), 1)

        story = self.client.get(f'/stories/{story_id}').json()
        self.assertEqual(1, story['confirmed_fragment_count'])
        self.assertEqual(0, story['pending_fragment_count'])
        self.assertEqual(0, len([item for item in story['pending_updates'] if item['status'] == 'pending']))

    def test_reject_pending_update_marks_it_rejected(self) -> None:
        ingest = self.client.post(
            '/stories/ingest',
            json={
                'title': 'Колокол без моря',
                'text': 'Павел принёс колокол с острова.',
            },
        )
        story_id = ingest.json()['story_id']
        update_id = ingest.json()['pending_update_id']

        reject = self.client.post(f'/stories/{story_id}/pending-updates/{update_id}/reject')
        self.assertEqual(reject.status_code, 200)
        self.assertEqual('rejected', reject.json()['status'])

        story = self.client.get(f'/stories/{story_id}').json()
        rejected = [item for item in story['pending_updates'] if item['id'] == update_id]
        self.assertEqual(1, len(rejected))
        self.assertEqual('rejected', rejected[0]['status'])

    def test_observability_endpoints_show_analysis_activity(self) -> None:
        story_id = self._create_empty_story()
        self.client.post(
            f'/stories/{story_id}/analyze',
            json={'scene_text': 'Лев встретил Павла у пристани.'},
        )

        summary = self.client.get('/observability/summary')
        traces = self.client.get('/observability/traces')
        self.assertEqual(summary.status_code, 200)
        self.assertEqual(traces.status_code, 200)
        self.assertEqual(1, summary.json()['analysis_requests'])
        self.assertEqual(1, len(traces.json()['traces']))

    def _create_empty_story(self) -> str:
        story = self.data_service.create_story(title='Рабочая история')
        return story.id

    def _create_story_with_confirmed_loss(self) -> str:
        story = self.data_service.create_story(title='Рабочая история')
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
        return story.id


if __name__ == '__main__':
    unittest.main()
