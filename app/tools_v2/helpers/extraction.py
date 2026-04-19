from __future__ import annotations

from app.tools_v2.contracts import ExtractionResult, SceneEntityCandidate, SceneEventCandidate, SceneFactCandidate, SceneRelationCandidate
from app.tools_v2.helpers.text import (
    ARRIVAL_RE,
    LIVE_RE,
    MEETING_RE,
    OBJECT_ACTION_RE,
    TRAIT_RE,
    canonicalize,
    entity_lookup_key,
    extract_names,
    extract_pronouns,
    extract_temporal_hints,
    normalize_location_name,
    split_sentences,
    summarize_sentence,
)

EVENT_VERBS = (
    'встретил', 'встретила', 'встречает',
    'приехал', 'приехала', 'пришел', 'пришла', 'вернулся', 'вернулась',
    'ждал', 'ждала', 'стоял', 'стояла', 'слушал', 'слушала', 'смотрел', 'смотрела', 'молчал', 'молчала', 'отвечал', 'отвечала', 'отвязал', 'отвязала', 'отвязали',
    'открыл', 'открыла', 'решил', 'решила', 'решили',
    'потерял', 'потеряла', 'вынул', 'вынула', 'вытащил', 'вытащила',
    'достал', 'достала', 'нашел', 'нашла',
)

DESCRIPTION_PREFIXES = ('к вечеру', 'к утру', 'утром', 'вечером', 'ночью')


def _add_unique_entity(collection: list[SceneEntityCandidate], kind: str, raw_name: str, registry: dict[tuple[str, str], SceneEntityCandidate], summary: str) -> str:
    display_name = raw_name.strip()
    if kind == 'location':
        display_name = normalize_location_name(display_name)
    key = (kind, entity_lookup_key(display_name))
    existing = registry.get(key)
    if existing is not None:
        return existing.name

    candidate = SceneEntityCandidate(
        kind=kind,
        name=display_name,
        canonical_name=canonicalize(display_name),
        summary=summary,
    )
    registry[key] = candidate
    collection.append(candidate)
    return candidate.name


def _is_event_sentence(sentence: str) -> bool:
    lowered = sentence.lower()
    if any(f' {verb} ' in f' {lowered} ' for verb in EVENT_VERBS):
        return True
    return False


def extract_scene_candidates(scene_text: str) -> ExtractionResult:
    pronouns = extract_pronouns(scene_text)
    temporal_hints = extract_temporal_hints(scene_text)

    characters: list[SceneEntityCandidate] = []
    locations: list[SceneEntityCandidate] = []
    objects_map: dict[str, SceneEntityCandidate] = {}
    registry: dict[tuple[str, str], SceneEntityCandidate] = {}
    facts: list[SceneFactCandidate] = []
    relations: list[SceneRelationCandidate] = []

    for match in TRAIT_RE.finditer(scene_text):
        actor, trait = match.groups()
        actor_name = _add_unique_entity(characters, 'character', actor, registry, f'Персонаж {actor}.')
        facts.append(
            SceneFactCandidate(
                fact_kind='character_trait',
                summary=f'{actor_name} был {trait}.',
                subject_name=actor_name,
            )
        )

    for match in LIVE_RE.finditer(scene_text):
        actor, location = match.groups()
        actor_name = _add_unique_entity(characters, 'character', actor, registry, f'Персонаж {actor}.')
        location_name = _add_unique_entity(locations, 'location', location, registry, f'Место {normalize_location_name(location)}.')
        facts.append(
            SceneFactCandidate(
                fact_kind='location',
                summary=f'{actor_name} живёт в {location_name}.',
                subject_name=actor_name,
                object_name=location_name,
            )
        )

    for match in MEETING_RE.finditer(scene_text):
        left, right = match.groups()
        left_name = _add_unique_entity(characters, 'character', left, registry, f'Персонаж {left}.')
        right_name = _add_unique_entity(characters, 'character', right, registry, f'Персонаж {right}.')
        relations.append(
            SceneRelationCandidate(
                left_name=left_name,
                right_name=right_name,
                relation_kind='interaction',
                summary=f'{left_name} встречает {right_name}.',
            )
        )

    for match in ARRIVAL_RE.finditer(scene_text):
        actor = match.group(1)
        _add_unique_entity(characters, 'character', actor, registry, f'Персонаж {actor}.')

    for match in OBJECT_ACTION_RE.finditer(scene_text):
        actor, obj = match.groups()
        actor_name = _add_unique_entity(characters, 'character', actor, registry, f'Персонаж {actor}.')
        canonical_object = canonicalize(obj)
        objects_map.setdefault(
            canonical_object,
            SceneEntityCandidate(kind='object', name=obj, canonical_name=canonical_object, summary=f'Объект {obj} из сцены.'),
        )
        facts.append(
            SceneFactCandidate(
                fact_kind='object_state',
                summary=f'{actor_name} {match.group(1).lower()} {obj}.',
                subject_name=actor_name,
                object_name=obj,
            )
        )

    events: list[SceneEventCandidate] = []
    for sentence in split_sentences(scene_text):
        lowered = sentence.lower()
        sentence_names_raw = extract_names(sentence)
        sentence_characters = [candidate.name for candidate in characters if candidate.name in sentence]
        sentence_locations = [candidate.name for candidate in locations if candidate.name in sentence or candidate.canonical_name in lowered]
        sentence_objects = [candidate.name for candidate in objects_map.values() if candidate.name in sentence]

        if _is_event_sentence(sentence):
            for raw_name in sentence_names_raw:
                if any(location.name == raw_name for location in locations):
                    continue
                normalized_name = _add_unique_entity(characters, 'character', raw_name, registry, f'Персонаж {raw_name}.')
                if normalized_name not in sentence_characters:
                    sentence_characters.append(normalized_name)
            timeline_note = sentence if sentence in temporal_hints else ''
            temporal_relation = 'before' if 'перед' in lowered else 'after' if 'после' in lowered or 'потом' in lowered else 'unknown'
            events.append(
                SceneEventCandidate(
                    title=summarize_sentence(sentence),
                    summary=sentence,
                    timeline_note=timeline_note,
                    temporal_relation=temporal_relation,
                    participant_names=sentence_characters,
                    object_names=sentence_objects + sentence_locations,
                )
            )
        elif lowered.startswith(DESCRIPTION_PREFIXES) or 'становил' in lowered:
            facts.append(
                SceneFactCandidate(
                    fact_kind='scene_description',
                    summary=sentence,
                )
            )

    return ExtractionResult(
        characters=characters,
        locations=locations,
        objects=list(objects_map.values()),
        events=events,
        facts=facts,
        relations=relations,
        temporal_hints=temporal_hints,
        unresolved_references=pronouns,
        scene_summary=summarize_sentence(scene_text, max_words=18),
    )
