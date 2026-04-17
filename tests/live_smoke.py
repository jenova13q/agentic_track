from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory

from fastapi.testclient import TestClient

from app.agent.orchestrator import DemoOrchestrator
from app.api import routes
from app.main import app
from app.memory.store import StoryStore


def run_live_smoke() -> int:
    with TemporaryDirectory() as tmp:
        store = StoryStore(base_dir=Path(tmp))
        routes.store = store
        routes.orchestrator = DemoOrchestrator(store=store)

        client = TestClient(app)

        ingest = client.post(
            "/stories/ingest",
            json={
                "title": "Live Smoke Demo",
                "text": (
                    "К вечеру Приморск всегда становился похож на плохо вытертое зеркало. "
                    "Лев живёт в Приморске. Лев был смелый.\n\n"
                    "На следующее утро Павел приехал с острова. "
                    "Павел живёт в Маячном. Павел был добрый."
                ),
            },
        )
        if ingest.status_code != 200:
            print("FAIL: ingest failed", ingest.status_code, ingest.text)
            return 1

        story_id = ingest.json()["story_id"]

        analyze = client.post(
            f"/stories/{story_id}/analyze",
            json={"scene_text": "Перед выходом к воде Лев был трусливый и боялся даже посмотреть на бухту."},
        )
        if analyze.status_code != 200:
            print("FAIL: analyze failed", analyze.status_code, analyze.text)
            return 1

        payload = analyze.json()
        print(json.dumps(payload, ensure_ascii=False, indent=2))

        if payload.get("orchestrator_mode") != "llm":
            print("FAIL: orchestrator_mode is not llm")
            return 1

        if payload.get("status") != "conflict":
            print("FAIL: expected conflict status")
            return 1

        if payload.get("issue_type") not in {"character", "mixed"}:
            print("FAIL: expected character or mixed issue_type")
            return 1

        print("OK: live LLM smoke check passed")
        return 0


if __name__ == "__main__":
    raise SystemExit(run_live_smoke())
