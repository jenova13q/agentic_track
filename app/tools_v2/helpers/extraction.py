from __future__ import annotations

from app.tools_v2.contracts import ExtractionResult, SceneEntityCandidate, SceneEventCandidate, SceneFactCandidate, SceneRelationCandidate
from app.tools_v2.helpers.text import MEETING_RE, OBJECT_ACTION_RE, TRAIT_RE, LIVE_RE, canonicalize, extract_names, extract_pronouns, extract_temporal_hints, split_sentences, summarize_sentence


def extract_scene_candidates(scene_text: str) -> ExtractionResult:
    names = extract_names(scene_text)
    pronouns = extract_pronouns(scene_text)
    temporal_hints = extract_temporal_hints(scene_text)

    characters = [
        SceneEntityCandidate(kind='character', name=name, canonical_name=canonicalize(name), summary=f'Персонаж {name}.')
        for name in names
    ]

    objects_map: dict[str, SceneEntityCandidate] = {}
    facts: list[SceneFactCandidate] = []
    relations: list[SceneRelationCandidate] = []

    for match in OBJECT_ACTION_RE.finditer(scene_text):
        actor, obj = match.groups()
        canonical_object = canonicalize(obj)
        objects_map.setdefault(
            canonical_object,
            SceneEntityCandidate(kind='object', name=obj, canonical_name=canonical_object, summary=f'Объект {obj} из сцены.'),
        )
        facts.append(
            SceneFactCandidate(
                fact_kind='object_state',
                summary=f'{actor} {match.group(1).lower()} {obj}.',
                subject_name=actor,
                object_name=obj,
            )
        )

    for match in TRAIT_RE.finditer(scene_text):
        actor, trait = match.groups()
        facts.append(
            SceneFactCandidate(
                fact_kind='character_trait',
                summary=f'{actor} был {trait}.',
                subject_name=actor,
            )
        )

    for match in LIVE_RE.finditer(scene_text):
        actor, location = match.groups()
        facts.append(
            SceneFactCandidate(
                fact_kind='location',
                summary=f'{actor} живёт в {location}.',
                subject_name=actor,
                object_name=location,
            )
        )

    for match in MEETING_RE.finditer(scene_text):
        left, right = match.groups()
        relations.append(
            SceneRelationCandidate(
                left_name=left,
                right_name=right,
                relation_kind='interaction',
                summary=f'{left} встречает {right}.',
            )
        )

    events: list[SceneEventCandidate] = []
    for sentence in split_sentences(scene_text):
        sentence_names = [name for name in names if name in sentence]
        sentence_objects = [candidate.name for candidate in objects_map.values() if candidate.name in sentence]
        if not sentence_names and not sentence_objects:
            continue
        timeline_note = sentence if sentence in temporal_hints else ''
        temporal_relation = 'before' if 'перед' in sentence.lower() else 'after' if 'после' in sentence.lower() or 'потом' in sentence.lower() else 'unknown'
        events.append(
            SceneEventCandidate(
                title=summarize_sentence(sentence),
                summary=sentence,
                timeline_note=timeline_note,
                temporal_relation=temporal_relation,
                participant_names=sentence_names,
                object_names=sentence_objects,
            )
        )

    return ExtractionResult(
        characters=characters,
        objects=list(objects_map.values()),
        events=events,
        facts=facts,
        relations=relations,
        temporal_hints=temporal_hints,
        unresolved_references=pronouns,
        scene_summary=summarize_sentence(scene_text, max_words=18),
    )
