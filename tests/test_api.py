import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from app.agent.orchestrator import DemoOrchestrator
from app.api import routes
from app.main import app
from app.memory.store import StoryStore
from app.observability.service import ObservabilityStore


class StoryApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.store = StoryStore(base_dir=Path(self.temp_dir.name))
        self.observability = ObservabilityStore(base_dir=Path(self.temp_dir.name) / "telemetry")
        routes.store = self.store
        routes.orchestrator = DemoOrchestrator(store=self.store)
        routes.observability = self.observability
        routes.orchestrator.llm.openai_api_key = None
        self.client = TestClient(app)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_health_endpoint(self) -> None:
        response = self.client.get("/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})
        self.assertIn("X-Request-ID", response.headers)

    def test_root_serves_demo_ui(self) -> None:
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Story Consistency Agent", response.text)

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
        self.assertGreaterEqual(payload["agent_step_count"], 1)
        self.assertGreaterEqual(payload["tool_call_count"], 1)

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

    def test_reject_pending_update_marks_it_rejected(self) -> None:
        story_id = self._ingest_story(
            text="Day 1. Anna lives in Tashkent. Anna is brave."
        )

        analyze_response = self.client.post(
            f"/stories/{story_id}/analyze",
            json={"scene_text": "Day 2. Boris lives in Samarkand. Boris is kind."},
        )
        self.assertEqual(analyze_response.status_code, 200)
        proposal_id = analyze_response.json()["memory_update_proposal_id"]
        self.assertIsNotNone(proposal_id)

        reject_response = self.client.post(
            f"/stories/{story_id}/pending-updates/{proposal_id}/reject"
        )
        self.assertEqual(reject_response.status_code, 200)
        self.assertEqual(reject_response.json()["status"], "rejected")

        story_after_reject = self.client.get(f"/stories/{story_id}").json()
        rejected = [
            update for update in story_after_reject["pending_updates"] if update["id"] == proposal_id
        ]
        self.assertEqual(len(rejected), 1)
        self.assertEqual(rejected[0]["status"], "rejected")

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
        self.assertGreaterEqual(payload["agent_step_count"], 1)

    def test_observability_summary_and_traces_capture_analysis(self) -> None:
        story_id = self._ingest_story(
            text="Day 1. Anna lives in Tashkent. Anna is brave."
        )

        analyze_response = self.client.post(
            f"/stories/{story_id}/analyze",
            json={"scene_text": "Day 2. Anna is cowardly."},
        )
        self.assertEqual(analyze_response.status_code, 200)

        summary_response = self.client.get("/observability/summary")
        self.assertEqual(summary_response.status_code, 200)
        summary = summary_response.json()
        self.assertEqual(summary["analysis_requests"], 1)
        self.assertEqual(summary["conflict_count"], 1)
        self.assertGreaterEqual(summary["average_tool_calls"], 1.0)
        self.assertIn("conflict_detected", summary["last_stop_reasons"])

        traces_response = self.client.get("/observability/traces")
        self.assertEqual(traces_response.status_code, 200)
        traces = traces_response.json()["traces"]
        self.assertEqual(len(traces), 1)
        self.assertEqual(traces[0]["event_type"], "analysis")
        self.assertEqual(traces[0]["status"], "conflict")

    def test_append_scene_adds_chunk_and_memory(self) -> None:
        story_id = self._ingest_story(
            text="Лев живёт в Приморске. Лев был смелый."
        )

        append_response = self.client.post(
            f"/stories/{story_id}/append-scene",
            json={"scene_text": "Тем же вечером Лев потерял ручку."},
        )
        self.assertEqual(append_response.status_code, 200)
        payload = append_response.json()
        self.assertEqual(payload["status"], "appended")
        self.assertGreaterEqual(payload["chunk_count"], 2)

        story = self.client.get(f"/stories/{story_id}").json()
        object_facts = [
            item for item in story["memory"] if item["attributes"].get("object") == "ручку"
        ]
        self.assertTrue(object_facts)

    def test_object_state_conflict_is_detected(self) -> None:
        story_id = self._ingest_story(
            text="Тем же вечером Лев потерял ручку."
        )

        response = self.client.post(
            f"/stories/{story_id}/analyze",
            json={"scene_text": "На следующее утро Лев достал ручку."},
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["status"], "conflict")
        self.assertIn(payload["issue_type"], {"object", "mixed"})

    def test_object_state_conflict_is_detected_for_vynul_phrase(self) -> None:
        story_id = self._ingest_story(
            text=(
                "Оказалось, что в тот вечер Лев потерял ключ у пристани. "
                "Он его долго искал, но так и не нашел."
            )
        )

        response = self.client.post(
            f"/stories/{story_id}/analyze",
            json={"scene_text": "На острове Лев вынул ключ из кармана и открыл деревянную дверь."},
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["status"], "conflict")
        self.assertIn(payload["issue_type"], {"object", "mixed"})

    def _ingest_story(self, text: str) -> str:
        response = self.client.post(
            "/stories/ingest",
            json={"title": "Base Story", "text": text},
        )
        self.assertEqual(response.status_code, 200)
        return response.json()["story_id"]
