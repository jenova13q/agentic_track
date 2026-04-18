from __future__ import annotations

from app.storage.connection import Database
from app.storage.models import ChunkWindow, EntityBundle, EventBundle
from app.storage.repositories import StoryMemoryRepository, StoryRepository


class StoryMemoryDataService:
    def __init__(self, database: Database | None = None) -> None:
        self.database = database or Database()

    def _repos(self):
        connection = self.database.connect()
        return connection, StoryRepository(connection), StoryMemoryRepository(connection)

    def create_story(self, title: str, synopsis: str = ""):
        connection, story_repo, _ = self._repos()
        try:
            return story_repo.create_story(title=title, synopsis=synopsis)
        finally:
            connection.close()

    def add_fragment(self, **kwargs):
        connection, story_repo, _ = self._repos()
        try:
            return story_repo.add_fragment(**kwargs)
        finally:
            connection.close()

    def add_chunk(self, **kwargs):
        connection, story_repo, _ = self._repos()
        try:
            return story_repo.add_chunk(**kwargs)
        finally:
            connection.close()

    def create_entity(self, **kwargs):
        connection, _, memory_repo = self._repos()
        try:
            return memory_repo.create_entity(**kwargs)
        finally:
            connection.close()

    def upsert_character_profile(self, **kwargs):
        connection, _, memory_repo = self._repos()
        try:
            return memory_repo.upsert_character_profile(**kwargs)
        finally:
            connection.close()

    def upsert_object_profile(self, **kwargs):
        connection, _, memory_repo = self._repos()
        try:
            return memory_repo.upsert_object_profile(**kwargs)
        finally:
            connection.close()

    def create_event(self, **kwargs):
        connection, _, memory_repo = self._repos()
        try:
            return memory_repo.create_event(**kwargs)
        finally:
            connection.close()

    def add_event_entity(self, **kwargs):
        connection, _, memory_repo = self._repos()
        try:
            memory_repo.add_event_entity(**kwargs)
        finally:
            connection.close()

    def create_fact(self, **kwargs):
        connection, _, memory_repo = self._repos()
        try:
            return memory_repo.create_fact(**kwargs)
        finally:
            connection.close()

    def create_relation(self, **kwargs):
        connection, _, memory_repo = self._repos()
        try:
            return memory_repo.create_relation(**kwargs)
        finally:
            connection.close()

    def add_evidence_link(self, **kwargs):
        connection, _, memory_repo = self._repos()
        try:
            return memory_repo.add_evidence_link(**kwargs)
        finally:
            connection.close()

    def create_pending_update(self, **kwargs):
        connection, _, memory_repo = self._repos()
        try:
            return memory_repo.create_pending_update(**kwargs)
        finally:
            connection.close()

    def add_pending_update_item(self, **kwargs):
        connection, _, memory_repo = self._repos()
        try:
            return memory_repo.add_pending_update_item(**kwargs)
        finally:
            connection.close()

    def get_entity_bundle(self, entity_id: str) -> EntityBundle | None:
        connection, _, memory_repo = self._repos()
        try:
            return memory_repo.get_entity_bundle(entity_id)
        finally:
            connection.close()

    def get_event_bundle(self, event_id: str) -> EventBundle | None:
        connection, _, memory_repo = self._repos()
        try:
            return memory_repo.get_event_bundle(event_id)
        finally:
            connection.close()

    def get_chunk_window(self, chunk_id: str, before: int = 2, after: int = 1) -> ChunkWindow | None:
        connection, story_repo, _ = self._repos()
        try:
            result = story_repo.get_chunk_window(chunk_id, before=before, after=after)
            if result is None:
                return None
            center, previous_chunks, next_chunks = result
            return ChunkWindow(center=center, previous_chunks=previous_chunks, next_chunks=next_chunks)
        finally:
            connection.close()

    def find_entity_by_name(self, story_id: str, canonical_name: str, entity_kind: str | None = None):
        connection, _, memory_repo = self._repos()
        try:
            return memory_repo.find_entity_by_name(story_id=story_id, canonical_name=canonical_name, entity_kind=entity_kind)
        finally:
            connection.close()

    def list_entities(self, story_id: str, entity_kind: str | None = None, status: str | None = None):
        connection, _, memory_repo = self._repos()
        try:
            return memory_repo.list_entities(story_id=story_id, entity_kind=entity_kind, status=status)
        finally:
            connection.close()

    def list_stories(self):
        connection, story_repo, _ = self._repos()
        try:
            return story_repo.list_stories()
        finally:
            connection.close()

    def list_fragments(self, story_id: str, status: str | None = None):
        connection, story_repo, _ = self._repos()
        try:
            return story_repo.list_fragments(story_id=story_id, status=status)
        finally:
            connection.close()

    def list_chunks(self, story_id: str):
        connection, story_repo, _ = self._repos()
        try:
            return story_repo.list_chunks(story_id=story_id)
        finally:
            connection.close()
