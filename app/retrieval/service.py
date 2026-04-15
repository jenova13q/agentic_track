from __future__ import annotations

import re

from app.models.schemas import MemoryRecord, StoryChunk, StoryData


WORD_RE = re.compile(r"[A-Za-zА-Яа-яЁё0-9]+")


def tokenize(text: str) -> list[str]:
    return [match.group(0).lower() for match in WORD_RE.finditer(text)]


def score_overlap(left: str, right: str) -> int:
    left_tokens = set(tokenize(left))
    right_tokens = set(tokenize(right))
    return len(left_tokens & right_tokens)


class RetrieverService:
    def retrieve_chunks(self, story: StoryData, query: str, top_k: int = 5) -> list[StoryChunk]:
        ranked = sorted(
            story.chunks,
            key=lambda chunk: score_overlap(query, chunk.text),
            reverse=True,
        )
        return [chunk for chunk in ranked[:top_k] if score_overlap(query, chunk.text) > 0]

    def retrieve_memory(self, story: StoryData, query: str, top_k: int = 5) -> list[MemoryRecord]:
        ranked = sorted(
            story.memory,
            key=lambda record: score_overlap(query, record.canonical_value),
            reverse=True,
        )
        return [record for record in ranked[:top_k] if score_overlap(query, record.canonical_value) > 0]
