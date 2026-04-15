from __future__ import annotations
from pathlib import Path

from app.core.config import settings
from app.models.schemas import (
    PendingUpdate,
    StoryData,
    StoryListItem,
    StoryListResponse,
    StoryResponse,
    utc_now,
)


class StoryStore:
    def __init__(self, base_dir: Path | None = None) -> None:
        self.base_dir = base_dir or settings.stories_dir
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _story_path(self, story_id: str) -> Path:
        return self.base_dir / f"{story_id}.json"

    def save_story(self, story: StoryData) -> None:
        story.updated_at = utc_now()
        path = self._story_path(story.story_id)
        path.write_text(
            story.model_dump_json(indent=2),
            encoding="utf-8",
        )

    def get_story(self, story_id: str) -> StoryResponse | None:
        data = self.load_story_data(story_id)
        if data is None:
            return None
        return StoryResponse(
            story_id=data.story_id,
            title=data.title,
            memory=data.memory,
            pending_updates=data.pending_updates,
            chunk_count=len(data.chunks),
        )

    def list_stories(self) -> StoryListResponse:
        items: list[StoryListItem] = []
        for path in sorted(self.base_dir.glob("*.json")):
            story = StoryData.model_validate_json(path.read_text(encoding="utf-8"))
            items.append(
                StoryListItem(
                    story_id=story.story_id,
                    title=story.title,
                    chunk_count=len(story.chunks),
                    pending_update_count=len(
                        [update for update in story.pending_updates if update.status == "pending"]
                    ),
                )
            )
        return StoryListResponse(stories=items)

    def load_story_data(self, story_id: str) -> StoryData | None:
        path = self._story_path(story_id)
        if not path.exists():
            return None
        return StoryData.model_validate_json(path.read_text(encoding="utf-8"))

    def create_story(self, story: StoryData) -> None:
        self.save_story(story)

    def add_pending_update(self, story_id: str, update: PendingUpdate) -> PendingUpdate | None:
        story = self.load_story_data(story_id)
        if story is None:
            return None
        story.pending_updates.append(update)
        self.save_story(story)
        return update

    def replace_story(self, story: StoryData) -> None:
        self.save_story(story)

    def confirm_update(self, story_id: str, update_id: str) -> PendingUpdate | None:
        story = self.load_story_data(story_id)
        if story is None:
            return None

        for update in story.pending_updates:
            if update.id != update_id or update.status != "pending":
                continue

            promoted_ids: list[str] = []
            for change in update.changes:
                change.status = "confirmed"
                promoted_ids.append(change.id)
                story.memory.append(change)

            update.status = "confirmed"
            update.promoted_memory_ids = promoted_ids
            self.save_story(story)
            return update

        return None
