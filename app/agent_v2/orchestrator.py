from __future__ import annotations

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

        return AgentV2Result(
            status=verdict.status,
            issue_type=verdict.issue_type,
            explanation=verdict.explanation,
            confidence=verdict.confidence,
            extraction=extraction,
            context=context,
            staged_update_id=staged_update_id,
            staged_fragment_id=staged_fragment_id,
            staged_item_counts=staged_item_counts,
            orchestrator_mode='llm' if self.llm_adapter.enabled else 'heuristic',
            step_count=step_count,
        )
