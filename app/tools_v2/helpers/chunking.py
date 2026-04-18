from __future__ import annotations

import re

from app.retrieval.service import tokenize


def build_story_chunks(story_id: str, fragment_id: str, text: str) -> list[dict[str, object]]:
    paragraphs = [paragraph.strip() for paragraph in re.split(r"\n\s*\n", text) if paragraph.strip()]
    chunks: list[dict[str, object]] = []
    for index, paragraph in enumerate(paragraphs):
        chunks.append(
            {
                'story_id': story_id,
                'fragment_id': fragment_id,
                'chunk_index': index,
                'source_ref': f'fragment:{fragment_id}:chunk:{index}',
                'text': paragraph,
                'token_count': len(tokenize(paragraph)),
            }
        )
    if not chunks:
        normalized = text.strip()
        chunks.append(
            {
                'story_id': story_id,
                'fragment_id': fragment_id,
                'chunk_index': 0,
                'source_ref': f'fragment:{fragment_id}:chunk:0',
                'text': normalized,
                'token_count': len(tokenize(normalized)),
            }
        )
    return chunks
