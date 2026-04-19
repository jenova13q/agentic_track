from __future__ import annotations

from app.storage.service import StoryMemoryDataService
from app.tools_v2.contracts import ContextCollectionResult, ExtractionResult
from app.tools_v2.helpers import canonicalize, entity_lookup_key


class CollectRelevantContextTool:
    name = 'collect_relevant_context'

    def __init__(self, data_service: StoryMemoryDataService | None = None) -> None:
        self.data_service = data_service or StoryMemoryDataService()

    def _find_matching_entity(self, story_id: str, name: str, entity_kind: str | None = None):
        exact = self.data_service.find_entity_by_name(story_id=story_id, canonical_name=canonicalize(name), entity_kind=entity_kind)
        if exact is not None:
            return exact

        lookup_key = entity_lookup_key(name)
        for entity in self.data_service.list_entities(story_id=story_id, entity_kind=entity_kind, status='confirmed'):
            if entity_lookup_key(entity.name) == lookup_key or entity_lookup_key(entity.canonical_name) == lookup_key:
                return entity
        return None

    def run(self, story_id: str, extraction: ExtractionResult, scene_text: str = '') -> ContextCollectionResult:
        names = [candidate.name for candidate in extraction.characters]
        pronouns = extraction.unresolved_references
        matched_entity_bundles = []
        seen_entity_ids: set[str] = set()
        chunk_windows = []
        seen_chunk_ids: set[str] = set()
        debug_messages: list[str] = []

        chunks = self.data_service.list_chunks(story_id)
        if scene_text and chunks:
            fallback_window = self.data_service.get_chunk_window(chunks[-1].id, before=3, after=0)
            if fallback_window is not None and fallback_window.center.id not in seen_chunk_ids:
                seen_chunk_ids.add(fallback_window.center.id)
                chunk_windows.append(fallback_window)
                debug_messages.append('Подтянут локальный диапазон последних кусков текста для базового контекста.')

        for name in names:
            entity = self._find_matching_entity(story_id=story_id, name=name, entity_kind='character')
            if entity is None or entity.id in seen_entity_ids:
                continue
            seen_entity_ids.add(entity.id)
            bundle = self.data_service.get_entity_bundle(entity.id)
            if bundle is not None:
                if bundle.entity.name != name:
                    debug_messages.append(f'Найдено совпадение в памяти: {bundle.entity.entity_kind} "{name}" -> "{bundle.entity.name}"')
                else:
                    debug_messages.append(f'Найдено совпадение в памяти: {bundle.entity.entity_kind} "{bundle.entity.name}"')
                matched_entity_bundles.append(bundle)
                for evidence in bundle.evidence_links[:1]:
                    window = self.data_service.get_chunk_window(evidence.chunk_id, before=2, after=1)
                    if window is not None and window.center.id not in seen_chunk_ids:
                        seen_chunk_ids.add(window.center.id)
                        chunk_windows.append(window)

        for candidate in extraction.locations + extraction.objects:
            entity = self._find_matching_entity(story_id=story_id, name=candidate.name, entity_kind=candidate.kind)
            if entity is None or entity.id in seen_entity_ids:
                continue
            seen_entity_ids.add(entity.id)
            bundle = self.data_service.get_entity_bundle(entity.id)
            if bundle is not None:
                debug_messages.append(f'Найдено совпадение в памяти: {bundle.entity.entity_kind} "{bundle.entity.name}"')
                matched_entity_bundles.append(bundle)
                for evidence in bundle.evidence_links[:1]:
                    window = self.data_service.get_chunk_window(evidence.chunk_id, before=2, after=1)
                    if window is not None and window.center.id not in seen_chunk_ids:
                        seen_chunk_ids.add(window.center.id)
                        chunk_windows.append(window)

        if pronouns and chunk_windows:
            debug_messages.append('Найдены местоименные ссылки, они будут интерпретироваться с опорой на локальный контекст.')

        return ContextCollectionResult(
            matched_entity_bundles=matched_entity_bundles,
            chunk_windows=chunk_windows,
            unresolved_references=pronouns,
            debug_messages=debug_messages,
        )
