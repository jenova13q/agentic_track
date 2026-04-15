from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory

from fastapi.testclient import TestClient

from app.agent.orchestrator import DemoOrchestrator
from app.api import routes
from app.main import app
from app.memory.store import StoryStore
from app.observability.service import ObservabilityStore


def run_demo_eval() -> int:
    scenario_path = Path("data/demo-scenarios.json")
    scenarios = json.loads(scenario_path.read_text(encoding="utf-8"))

    results: list[dict[str, object]] = []
    with TemporaryDirectory() as tmp:
        store = StoryStore(base_dir=Path(tmp))
        observability = ObservabilityStore(base_dir=Path(tmp) / "telemetry")
        routes.store = store
        routes.orchestrator = DemoOrchestrator(store=store)
        routes.orchestrator.llm.openai_api_key = None
        routes.observability = observability
        client = TestClient(app)

        for scenario in scenarios:
            ingest = client.post(
                "/stories/ingest",
                json={"title": scenario["name"], "text": scenario["story_text"]},
            )
            if ingest.status_code != 200:
                print(f"FAIL: ingest failed for {scenario['name']}")
                return 1

            story_id = ingest.json()["story_id"]
            analyze = client.post(
                f"/stories/{story_id}/analyze",
                json={"scene_text": scenario["scene_text"]},
            )
            if analyze.status_code != 200:
                print(f"FAIL: analyze failed for {scenario['name']}")
                return 1

            payload = analyze.json()
            status_match = payload["status"] == scenario["expected_status"]
            issue_type_match = payload["issue_type"] == scenario["expected_issue_type"]
            results.append(
                {
                    "name": scenario["name"],
                    "status_match": status_match,
                    "issue_type_match": issue_type_match,
                    "actual_status": payload["status"],
                    "actual_issue_type": payload["issue_type"],
                    "expected_status": scenario["expected_status"],
                    "expected_issue_type": scenario["expected_issue_type"],
                    "orchestrator_mode": payload["orchestrator_mode"],
                }
            )

    passed_status = sum(1 for item in results if item["status_match"])
    passed_issue_type = sum(1 for item in results if item["issue_type_match"])
    summary = {
        "scenario_count": len(results),
        "status_accuracy": round(passed_status / len(results), 2) if results else 0.0,
        "issue_type_accuracy": round(passed_issue_type / len(results), 2) if results else 0.0,
        "results": results,
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))

    if passed_status != len(results) or passed_issue_type != len(results):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(run_demo_eval())
