from __future__ import annotations

from uuid import uuid4

from app.storage.models import ChunkRecord, FragmentRecord, StoryRecord
from app.storage.repositories._shared import row_to_model


class StoryRepository:
    def __init__(self, connection) -> None:
        self.connection = connection

    def create_story(self, title: str, synopsis: str = "", story_id: str | None = None) -> StoryRecord:
        story_id = story_id or str(uuid4())
        self.connection.execute(
            "INSERT INTO stories(id, title, synopsis) VALUES (?, ?, ?)",
            (story_id, title, synopsis),
        )
        self.connection.commit()
        return self.get_story(story_id)

    def get_story(self, story_id: str) -> StoryRecord | None:
        row = self.connection.execute(
            "SELECT id, title, synopsis, created_at, updated_at FROM stories WHERE id = ?",
            (story_id,),
        ).fetchone()
        return row_to_model(StoryRecord, row) if row else None

    def list_stories(self) -> list[StoryRecord]:
        rows = self.connection.execute(
            "SELECT id, title, synopsis, created_at, updated_at FROM stories ORDER BY created_at"
        ).fetchall()
        return [row_to_model(StoryRecord, row) for row in rows]

    def add_fragment(
        self,
        story_id: str,
        text: str,
        fragment_kind: str,
        status: str,
        source_label: str,
        fragment_order: int | None = None,
        fragment_id: str | None = None,
    ) -> FragmentRecord:
        fragment_id = fragment_id or str(uuid4())
        self.connection.execute(
            """
            INSERT INTO story_fragments(id, story_id, fragment_kind, status, source_label, text, fragment_order)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (fragment_id, story_id, fragment_kind, status, source_label, text, fragment_order),
        )
        self.connection.execute(
            "UPDATE stories SET updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (story_id,),
        )
        self.connection.commit()
        return self.get_fragment(fragment_id)

    def get_fragment(self, fragment_id: str) -> FragmentRecord | None:
        row = self.connection.execute(
            """
            SELECT id, story_id, fragment_kind, status, source_label, text, fragment_order, created_at, updated_at
            FROM story_fragments WHERE id = ?
            """,
            (fragment_id,),
        ).fetchone()
        return row_to_model(FragmentRecord, row) if row else None

    def set_fragment_status(self, fragment_id: str, status: str, fragment_order: int | None = None) -> FragmentRecord | None:
        if fragment_order is None:
            self.connection.execute(
                "UPDATE story_fragments SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (status, fragment_id),
            )
        else:
            self.connection.execute(
                "UPDATE story_fragments SET status = ?, fragment_order = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (status, fragment_order, fragment_id),
            )
        self.connection.commit()
        return self.get_fragment(fragment_id)

    def list_fragments(self, story_id: str, status: str | None = None) -> list[FragmentRecord]:
        if status is None:
            rows = self.connection.execute(
                """
                SELECT id, story_id, fragment_kind, status, source_label, text, fragment_order, created_at, updated_at
                FROM story_fragments WHERE story_id = ?
                ORDER BY COALESCE(fragment_order, 999999), created_at
                """,
                (story_id,),
            ).fetchall()
        else:
            rows = self.connection.execute(
                """
                SELECT id, story_id, fragment_kind, status, source_label, text, fragment_order, created_at, updated_at
                FROM story_fragments WHERE story_id = ? AND status = ?
                ORDER BY COALESCE(fragment_order, 999999), created_at
                """,
                (story_id, status),
            ).fetchall()
        return [row_to_model(FragmentRecord, row) for row in rows]

    def next_confirmed_fragment_order(self, story_id: str) -> int:
        row = self.connection.execute(
            "SELECT COALESCE(MAX(fragment_order), -1) AS max_order FROM story_fragments WHERE story_id = ? AND status = 'confirmed'",
            (story_id,),
        ).fetchone()
        return int(row["max_order"]) + 1

    def add_chunk(
        self,
        story_id: str,
        fragment_id: str,
        chunk_index: int,
        source_ref: str,
        text: str,
        token_count: int = 0,
        chunk_id: str | None = None,
    ) -> ChunkRecord:
        chunk_id = chunk_id or str(uuid4())
        self.connection.execute(
            """
            INSERT INTO story_chunks(id, story_id, fragment_id, chunk_index, source_ref, text, token_count)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (chunk_id, story_id, fragment_id, chunk_index, source_ref, text, token_count),
        )
        self.connection.commit()
        return self.get_chunk(chunk_id)

    def get_chunk(self, chunk_id: str) -> ChunkRecord | None:
        row = self.connection.execute(
            """
            SELECT id, story_id, fragment_id, chunk_index, source_ref, text, token_count, created_at
            FROM story_chunks WHERE id = ?
            """,
            (chunk_id,),
        ).fetchone()
        return row_to_model(ChunkRecord, row) if row else None

    def list_chunks(self, story_id: str) -> list[ChunkRecord]:
        rows = self.connection.execute(
            """
            SELECT id, story_id, fragment_id, chunk_index, source_ref, text, token_count, created_at
            FROM story_chunks WHERE story_id = ?
            ORDER BY chunk_index
            """,
            (story_id,),
        ).fetchall()
        return [row_to_model(ChunkRecord, row) for row in rows]

    def get_chunk_window(self, chunk_id: str, before: int = 2, after: int = 1) -> tuple[ChunkRecord, list[ChunkRecord], list[ChunkRecord]] | None:
        center = self.get_chunk(chunk_id)
        if center is None:
            return None
        previous_rows = self.connection.execute(
            """
            SELECT id, story_id, fragment_id, chunk_index, source_ref, text, token_count, created_at
            FROM story_chunks
            WHERE story_id = ? AND chunk_index < ?
            ORDER BY chunk_index DESC
            LIMIT ?
            """,
            (center.story_id, center.chunk_index, before),
        ).fetchall()
        next_rows = self.connection.execute(
            """
            SELECT id, story_id, fragment_id, chunk_index, source_ref, text, token_count, created_at
            FROM story_chunks
            WHERE story_id = ? AND chunk_index > ?
            ORDER BY chunk_index ASC
            LIMIT ?
            """,
            (center.story_id, center.chunk_index, after),
        ).fetchall()
        previous_chunks = [row_to_model(ChunkRecord, row) for row in reversed(previous_rows)]
        next_chunks = [row_to_model(ChunkRecord, row) for row in next_rows]
        return center, previous_chunks, next_chunks
