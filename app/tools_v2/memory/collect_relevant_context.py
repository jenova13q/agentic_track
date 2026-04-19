from __future__ import annotations

from app.storage.service import StoryMemoryDataService
from app.tools_v2.contracts import ContextCollectionResult
from app.tools_v2.helpers import canonicalize, extract_names, extract_pronouns, extract_scene_candidates


class CollectRelevantContextTool:
    name = 'collect_relevant_context'

    def __init__(self, data_service: StoryMemoryDataService | None = None) -> None:
        self.data_service = data_service or StoryMemoryDataService()

    def run(self, story_id: str, scene_text: str) -> ContextCollectionResult:
        names = extract_names(scene_text)
        pronouns = extract_pronouns(scene_text)
        extraction = extract_scene_candidates(scene_text)
        matched_entity_bundles = []
        seen_entity_ids: set[str] = set()
        chunk_windows = []
        debug_messages: list[str] = []

        for name in names:
            entity = self.data_service.find_entity_by_name(story_id=story_id, canonical_name=canonicalize(name))
            if entity is None or entity.id in seen_entity_ids:
                continue
            seen_entity_ids.add(entity.id)
            bundle = self.data_service.get_entity_bundle(entity.id)
            if bundle is not None:
                debug_messages.append(f'Найдено совпадение в памяти: {bundle.entity.entity_kind} "{bundle.entity.name}"')
                matched_entity_bundles.append(bundle)
                for evidence in bundle.evidence_links[:1]:
                    window = self.data_service.get_chunk_window(evidence.chunk_id, before=2, after=1)
                    if window is not None:
                        chunk_windows.append(window)

        for candidate in extraction.objects:
            entity = self.data_service.find_entity_by_name(
                story_id=story_id,
                canonical_name=candidate.canonical_name,
                entity_kind='object',
            )
            if entity is None or entity.id in seen_entity_ids:
                continue
            seen_entity_ids.add(entity.id)
            bundle = self.data_service.get_entity_bundle(entity.id)
            if bundle is not None:
                debug_messages.append(f'Найдено совпадение в памяти: {bundle.entity.entity_kind} "{bundle.entity.name}"')
                matched_entity_bundles.append(bundle)
                for evidence in bundle.evidence_links[:1]:
                    window = self.data_service.get_chunk_window(evidence.chunk_id, before=2, after=1)
                    if window is not None:
                        chunk_windows.append(window)

        if pronouns and not chunk_windows:
            chunks = self.data_service.list_chunks(story_id)
            if chunks:
                last_chunk = chunks[-1]
                fallback_window = self.data_service.get_chunk_window(last_chunk.id, before=2, after=0)
                if fallback_window is not None:
                    debug_messages.append('Найдены местоименные ссылки, подтянут последний кусок текста для контекста.')
                    chunk_windows.append(fallback_window)

        return ContextCollectionResult(
            matched_entity_bundles=matched_entity_bundles,
            chunk_windows=chunk_windows,
            unresolved_references=pronouns,
            debug_messages=debug_messages,
        )
