from __future__ import annotations

from app.storage.service import StoryMemoryDataService
from app.tools_v2.contracts import StagedFragmentResult
from app.tools_v2.helpers import build_story_chunks


class StageFragmentTool:
    name = 'stage_fragment'

    def __init__(self, data_service: StoryMemoryDataService | None = None) -> None:
        self.data_service = data_service or StoryMemoryDataService()

    def run(self, story_id: str, scene_text: str, fragment_kind: str = 'scene', source_label: str = 'submission') -> StagedFragmentResult:
        fragment = self.data_service.add_fragment(
            story_id=story_id,
            text=scene_text,
            fragment_kind=fragment_kind,
            status='pending',
            source_label=source_label,
            fragment_order=None,
        )
        existing_chunks = self.data_service.list_chunks(story_id)
        next_index = len(existing_chunks)
        chunk_ids: list[str] = []
        for offset, chunk in enumerate(build_story_chunks(story_id=story_id, fragment_id=fragment.id, text=scene_text)):
            created = self.data_service.add_chunk(
                story_id=story_id,
                fragment_id=fragment.id,
                chunk_index=next_index + offset,
                source_ref=chunk['source_ref'],
                text=chunk['text'],
                token_count=chunk['token_count'],
            )
            chunk_ids.append(created.id)
        return StagedFragmentResult(fragment_id=fragment.id, chunk_ids=chunk_ids)
