from __future__ import annotations

from app.tools_v2.contracts import ExtractionResult
from app.tools_v2.helpers import extract_scene_candidates


class ExtractSceneElementsTool:
    name = 'extract_scene_elements'

    def run(self, scene_text: str) -> ExtractionResult:
        return extract_scene_candidates(scene_text)
