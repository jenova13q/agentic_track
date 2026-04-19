from __future__ import annotations

from dataclasses import asdict

from app.agent_v2.llm_adapter import LLMAdapterV2
from app.agent_v2.models import AgentV2Result
from app.storage.service import StoryMemoryDataService
from app.tools_v2 import CollectRelevantContextTool, ExtractSceneElementsTool, StageFragmentTool, StageMemoryCandidatesTool


class StoryConsistencyOrchestratorV2:
    def __init__(self, data_service: StoryMemoryDataService | None = None, llm_adapter: LLMAdapterV2 | None = None) -> None:
        self.data_service = data_service or StoryMemoryDataService()
        self.llm_adapter = llm_adapter or LLMAdapterV2()
        self.extract_tool = ExtractSceneElementsTool()
        self.context_tool = CollectRelevantContextTool(self.data_service)
        self.stage_fragment_tool = StageFragmentTool(self.data_service)
        self.stage_memory_tool = StageMemoryCandidatesTool(self.data_service)

    def analyze_scene(self, story_id: str, scene_text: str, user_comment: str | None = None) -> AgentV2Result:
        extraction = self.extract_tool.run(scene_text)
        context = self.context_tool.run(story_id=story_id, scene_text='')
        step_count = 1

        while step_count <= 3:
            decision = self.llm_adapter.choose_next_action(
                scene_text=scene_text if not user_comment else f'{scene_text}\n\nКомментарий автора: {user_comment}',
                extraction=extraction,
                context=context,
                step_count=step_count,
            )
            if decision.action == 'collect_relevant_context':
                context = self.context_tool.run(story_id=story_id, scene_text=scene_text)
                step_count += 1
                continue
            break

        verdict = self.llm_adapter.assess_scene(scene_text=scene_text, extraction=extraction, context=context)
        staged_update_id = None
        staged_fragment_id = None
        staged_item_counts: dict[str, int] = {}
        debug_messages = [
            f'Извлечён новый фрагмент: персонажей {len(extraction.characters)}, объектов {len(extraction.objects)}, событий {len(extraction.events)}, фактов {len(extraction.facts)}, связей {len(extraction.relations)}',
        ]
        debug_messages.extend(context.debug_messages)
        staged_debug_messages: list[str] = []

        if verdict.should_stage_update and verdict.status != 'conflict':
            staged_fragment = self.stage_fragment_tool.run(story_id=story_id, scene_text=scene_text, source_label='analysis_submission')
            staged_memory = self.stage_memory_tool.run(
                story_id=story_id,
                extraction=extraction,
                fragment_id=staged_fragment.fragment_id,
                chunk_ids=staged_fragment.chunk_ids,
            )
            staged_fragment_id = staged_fragment.fragment_id
            staged_update_id = staged_memory.pending_update.id
            staged_item_counts = {
                'entities': len(staged_memory.created_entity_ids),
                'events': len(staged_memory.created_event_ids),
                'facts': len(staged_memory.created_fact_ids),
                'relations': len(staged_memory.created_relation_ids),
            }
            staged_debug_messages = staged_memory.debug_messages
            debug_messages.extend(staged_debug_messages)

        debug_payload = {
            'messages': debug_messages,
            'extraction': {
                'scene_summary': extraction.scene_summary,
                'characters': [asdict(candidate) for candidate in extraction.characters],
                'objects': [asdict(candidate) for candidate in extraction.objects],
                'events': [asdict(event) for event in extraction.events],
                'facts': [asdict(fact) for fact in extraction.facts],
                'relations': [asdict(relation) for relation in extraction.relations],
                'temporal_hints': extraction.temporal_hints,
                'unresolved_references': extraction.unresolved_references,
            },
            'context': {
                'matched_entities': [
                    {
                        'kind': bundle.entity.entity_kind,
                        'name': bundle.entity.name,
                        'summary': bundle.entity.summary,
                        'character_profile': bundle.character_profile.trait_summary if bundle.character_profile else None,
                        'object_profile': bundle.object_profile.current_state_summary if bundle.object_profile else None,
                        'fact_summaries': [fact.summary for fact in bundle.facts],
                        'relation_summaries': [relation.summary for relation in bundle.relations],
                    }
                    for bundle in context.matched_entity_bundles
                ],
                'chunk_windows': [
                    {
                        'center': window.center.text,
                        'previous': [chunk.text for chunk in window.previous_chunks],
                        'next': [chunk.text for chunk in window.next_chunks],
                    }
                    for window in context.chunk_windows
                ],
                'unresolved_references': context.unresolved_references,
                'messages': context.debug_messages,
            },
            'staging': {
                'pending_update_id': staged_update_id,
                'fragment_id': staged_fragment_id,
                'item_counts': staged_item_counts,
                'messages': staged_debug_messages,
            },
            'verdict': {
                'status': verdict.status,
                'issue_type': verdict.issue_type,
                'confidence': verdict.confidence,
                'stop_reason': verdict.stop_reason,
                'should_stage_update': verdict.should_stage_update,
            },
        }

        return AgentV2Result(
            status=verdict.status,
            issue_type=verdict.issue_type,
            explanation=verdict.explanation,
            confidence=verdict.confidence,
            stop_reason=verdict.stop_reason,
            extraction=extraction,
            context=context,
            staged_update_id=staged_update_id,
            staged_fragment_id=staged_fragment_id,
            staged_item_counts=staged_item_counts,
            orchestrator_mode='llm' if self.llm_adapter.enabled else 'heuristic',
            step_count=step_count,
            debug_payload=debug_payload,
        )
