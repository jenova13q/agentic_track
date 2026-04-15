import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from app.agent.orchestrator import DemoOrchestrator
from app.api import routes
from app.main import app
from app.memory.store import StoryStore


class StoryApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.store = StoryStore(base_dir=Path(self.temp_dir.name))
        routes.store = self.store
        routes.orchestrator = DemoOrchestrator(store=self.store)
        routes.orchestrator.llm.openai_api_key = None
        self.client = TestClient(app)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_health_endpoint(self) -> None:
        response = self.client.get("/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})
        self.assertIn("X-Request-ID", response.headers)

    def test_ingest_and_list_story(self) -> None:
        ingest_response = self.client.post(
            "/stories/ingest",
            json={
                "title": "Demo Story",
                "text": (
                    "Day 1. Anna lives in Tashkent. Anna is brave.\n\n"
                    "Day 2. Boris lives in Samarkand. Boris is kind."
                ),
            },
        )

        self.assertEqual(ingest_response.status_code, 200)
        payload = ingest_response.json()
        self.assertEqual(payload["status"], "ingested")
        self.assertGreaterEqual(payload["chunk_count"], 1)

        list_response = self.client.get("/stories")
        self.assertEqual(list_response.status_code, 200)
        stories = list_response.json()["stories"]
        self.assertEqual(len(stories), 1)
        self.assertEqual(stories[0]["title"], "Demo Story")

    def test_analyze_scene_returns_conflict(self) -> None:
        story_id = self._ingest_story(
            text=(
                "Day 1. Anna lives in Tashkent. Anna is brave.\n\n"
                "Day 2. Anna meets Boris."
            )
        )

        response = self.client.post(
            f"/stories/{story_id}/analyze",
            json={
                "scene_text": "Day 2. Anna lives in Samarkand. Anna is cowardly.",
            },
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["status"], "conflict")
        self.assertIn(payload["issue_type"], {"fact", "character", "mixed"})
        self.assertTrue(payload["tool_traces"])
        self.assertIn(payload["orchestrator_mode"], {"heuristic", "llm"})

    def test_analyze_scene_creates_pending_update_and_confirm_promotes_it(self) -> None:
        story_id = self._ingest_story(
            text="Day 1. Anna lives in Tashkent. Anna is brave."
        )

        analyze_response = self.client.post(
            f"/stories/{story_id}/analyze",
            json={
                "scene_text": "Day 2. Boris lives in Samarkand. Boris is kind.",
            },
        )

        self.assertEqual(analyze_response.status_code, 200)
        analyze_payload = analyze_response.json()
        proposal_id = analyze_payload["memory_update_proposal_id"]
        self.assertIsNotNone(proposal_id)

        story_before_confirm = self.client.get(f"/stories/{story_id}").json()
        self.assertEqual(len(story_before_confirm["pending_updates"]), 1)

        confirm_response = self.client.post(
            f"/stories/{story_id}/pending-updates/{proposal_id}/confirm"
        )
        self.assertEqual(confirm_response.status_code, 200)
        confirm_payload = confirm_response.json()
        self.assertEqual(confirm_payload["status"], "confirmed")
        self.assertGreaterEqual(len(confirm_payload["promoted_memory_ids"]), 1)

        story_after_confirm = self.client.get(f"/stories/{story_id}").json()
        confirmed_facts = [
            item for item in story_after_confirm["memory"] if item["attributes"].get("name") == "Boris"
        ]
        self.assertTrue(confirmed_facts)

    def test_analyze_scene_returns_uncertain_when_memory_is_irrelevant(self) -> None:
        story_id = self._ingest_story(
            text="Day 1. Anna lives in Tashkent. Anna is brave."
        )

        response = self.client.post(
            f"/stories/{story_id}/analyze",
            json={"scene_text": "Quantum satellites collapse into mirrors."},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["status"], "uncertain")
        self.assertEqual(payload["stop_reason"], "insufficient_evidence")

    def _ingest_story(self, text: str) -> str:
        response = self.client.post(
            "/stories/ingest",
            json={"title": "Base Story", "text": text},
        )
        self.assertEqual(response.status_code, 200)
        return response.json()["story_id"]
