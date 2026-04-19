from __future__ import annotations

import json
from typing import Protocol

import httpx

from app.llm_prompts import EXTRACTION_SYSTEM_PROMPT
from app.core.config import settings
from app.tools_v2.contracts import ExtractionResult, SceneEntityCandidate, SceneEventCandidate, SceneFactCandidate, SceneRelationCandidate
from app.tools_v2.helpers import canonicalize


class SceneExtractionBackend(Protocol):
    def extract(self, *, scene_text: str, recent_story_excerpt: str = '') -> ExtractionResult: ...


class LLMSceneExtractionBackend:
    def __init__(self, api_key: str | None = None, model: str | None = None) -> None:
        self.api_key = api_key if api_key is not None else settings.openai_api_key
        self.model = model or settings.llm_model

    @property
    def enabled(self) -> bool:
        return bool(self.api_key)

    def extract(self, *, scene_text: str, recent_story_excerpt: str = '') -> ExtractionResult:
        if not self.enabled:
            raise RuntimeError('LLM scene extraction requires OPENAI_API_KEY.')

        payload = {
            'model': self.model,
            'messages': [
                {'role': 'system', 'content': EXTRACTION_SYSTEM_PROMPT},
                {
                    'role': 'user',
                    'content': json.dumps(
                        {
                            'recent_story_excerpt': recent_story_excerpt,
                            'scene_text': scene_text,
                        },
                        ensure_ascii=False,
                    ),
                },
            ],
            'temperature': 0.1,
            'response_format': {'type': 'json_object'},
        }

        with httpx.Client(timeout=20.0) as client:
            response = client.post(
                'https://api.openai.com/v1/chat/completions',
                headers={'Authorization': f'Bearer {self.api_key}', 'Content-Type': 'application/json'},
                json=payload,
            )
            response.raise_for_status()
        parsed = json.loads(response.json()['choices'][0]['message']['content'])
        return _parse_extraction_payload(parsed)


class ExtractSceneElementsTool:
    name = 'extract_scene_elements'

    def __init__(self, backend: SceneExtractionBackend | None = None) -> None:
        self.backend = backend or LLMSceneExtractionBackend()

    def run(self, scene_text: str, recent_story_excerpt: str = '') -> ExtractionResult:
        return self.backend.extract(scene_text=scene_text, recent_story_excerpt=recent_story_excerpt)


def _parse_entity_list(items: list[dict[str, object]] | None, kind: str) -> list[SceneEntityCandidate]:
    results: list[SceneEntityCandidate] = []
    seen: set[str] = set()
    for item in items or []:
        name = str(item.get('name', '')).strip()
        if not name:
            continue
        canonical_name = canonicalize(name)
        if canonical_name in seen:
            continue
        seen.add(canonical_name)
        results.append(
            SceneEntityCandidate(
                kind=kind,
                name=name,
                canonical_name=canonical_name,
                summary=str(item.get('summary', '')).strip(),
            )
        )
    return results


def _parse_extraction_payload(payload: dict[str, object]) -> ExtractionResult:
    events: list[SceneEventCandidate] = []
    for item in payload.get('events', []) or []:
        if not isinstance(item, dict):
            continue
        title = str(item.get('title', '')).strip()
        summary = str(item.get('summary', '')).strip()
        if not title or not summary:
            continue
        events.append(
            SceneEventCandidate(
                title=title,
                summary=summary,
                timeline_note=str(item.get('timeline_note', '')).strip(),
                temporal_relation=str(item.get('temporal_relation', 'unknown')).strip() or 'unknown',
                participant_names=[str(value).strip() for value in item.get('participant_names', []) or [] if str(value).strip()],
                object_names=[str(value).strip() for value in item.get('object_names', []) or [] if str(value).strip()],
                anchor_phrase=(str(item.get('anchor_phrase')).strip() if item.get('anchor_phrase') else None),
            )
        )

    facts: list[SceneFactCandidate] = []
    for item in payload.get('facts', []) or []:
        if not isinstance(item, dict):
            continue
        summary = str(item.get('summary', '')).strip()
        fact_kind = str(item.get('fact_kind', '')).strip()
        if not summary or not fact_kind:
            continue
        facts.append(
            SceneFactCandidate(
                fact_kind=fact_kind,
                summary=summary,
                subject_name=(str(item.get('subject_name')).strip() if item.get('subject_name') else None),
                object_name=(str(item.get('object_name')).strip() if item.get('object_name') else None),
                related_event_title=(str(item.get('related_event_title')).strip() if item.get('related_event_title') else None),
            )
        )

    relations: list[SceneRelationCandidate] = []
    for item in payload.get('relations', []) or []:
        if not isinstance(item, dict):
            continue
        left_name = str(item.get('left_name', '')).strip()
        right_name = str(item.get('right_name', '')).strip()
        relation_kind = str(item.get('relation_kind', '')).strip()
        summary = str(item.get('summary', '')).strip()
        if not left_name or not right_name or not relation_kind or not summary:
            continue
        relations.append(
            SceneRelationCandidate(
                left_name=left_name,
                right_name=right_name,
                relation_kind=relation_kind,
                summary=summary,
            )
        )

    return ExtractionResult(
        scene_summary=str(payload.get('scene_summary', '')).strip(),
        characters=_parse_entity_list(payload.get('characters', []), 'character'),
        locations=_parse_entity_list(payload.get('locations', []), 'location'),
        objects=_parse_entity_list(payload.get('objects', []), 'object'),
        events=events,
        facts=facts,
        relations=relations,
        temporal_hints=[str(value).strip() for value in payload.get('temporal_hints', []) or [] if str(value).strip()],
        unresolved_references=[str(value).strip() for value in payload.get('unresolved_references', []) or [] if str(value).strip()],
    )

