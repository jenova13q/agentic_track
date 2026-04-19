from __future__ import annotations

import json
import logging

import httpx

from app.agent_v2.models import ConsistencyVerdict, OrchestratorDecision
from app.llm_prompts import NEXT_ACTION_SYSTEM_PROMPT, VERDICT_SYSTEM_PROMPT
from app.core.config import settings
from app.tools_v2.contracts import ContextCollectionResult, ExtractionResult

logger = logging.getLogger('story-consistency-agent.agent-v2')

OPPOSITE_TRAITS = {
    'смелый': 'трусливый',
    'трусливый': 'смелый',
    'добрый': 'жестокий',
    'жестокий': 'добрый',
}


class LLMAdapterV2:
    def __init__(self) -> None:
        self.api_key = settings.openai_api_key
        self.model = settings.llm_model

    @property
    def enabled(self) -> bool:
        return bool(self.api_key)

    def choose_next_action(self, *, scene_text: str, extraction: ExtractionResult, context: ContextCollectionResult, step_count: int) -> OrchestratorDecision:
        if not self.enabled:
            return self._fallback_next_action(extraction=extraction, context=context)

        payload = {
            'model': self.model,
            'messages': [
                {'role': 'system', 'content': NEXT_ACTION_SYSTEM_PROMPT},
                {
                    'role': 'user',
                    'content': json.dumps(
                        {
                            'scene_text': scene_text,
                            'step_count': step_count,
                            'character_count': len(extraction.characters),
                            'object_count': len(extraction.objects),
                            'event_count': len(extraction.events),
                            'fact_count': len(extraction.facts),
                            'unresolved_references': extraction.unresolved_references,
                            'context_entity_count': len(context.matched_entity_bundles),
                            'context_chunk_window_count': len(context.chunk_windows),
                            'allowed_actions': ['collect_relevant_context', 'finish'],
                        },
                        ensure_ascii=False,
                    ),
                },
            ],
            'temperature': 0.1,
            'response_format': {'type': 'json_object'},
        }
        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.post(
                    'https://api.openai.com/v1/chat/completions',
                    headers={'Authorization': f'Bearer {self.api_key}', 'Content-Type': 'application/json'},
                    json=payload,
                )
                response.raise_for_status()
            content = response.json()['choices'][0]['message']['content']
            parsed = json.loads(content)
            action = parsed.get('action', 'finish')
            if action not in {'collect_relevant_context', 'finish'}:
                return self._fallback_next_action(extraction=extraction, context=context)
            return OrchestratorDecision(action=action, rationale=str(parsed.get('rationale', 'llm_decision')))
        except Exception as exc:
            logger.warning('agent_v2 next_action failed, falling back to heuristic: %s', exc)
            return self._fallback_next_action(extraction=extraction, context=context)

    def assess_scene(self, *, scene_text: str, extraction: ExtractionResult, context: ContextCollectionResult) -> ConsistencyVerdict:
        precheck = self._precheck_verdict(extraction=extraction, context=context)
        if precheck is not None:
            return precheck

        if not self.enabled:
            return self._fallback_verdict(extraction=extraction, context=context)

        compact_context = {
            'entities': [bundle.entity.canonical_name for bundle in context.matched_entity_bundles],
            'facts': [fact.summary for bundle in context.matched_entity_bundles for fact in bundle.facts[:3]],
            'relations': [rel.summary for bundle in context.matched_entity_bundles for rel in bundle.relations[:2]],
            'chunk_windows': [
                {
                    'center': window.center.text,
                    'previous': [chunk.text for chunk in window.previous_chunks],
                    'next': [chunk.text for chunk in window.next_chunks],
                }
                for window in context.chunk_windows[:3]
            ],
        }
        payload = {
            'model': self.model,
            'messages': [
                {'role': 'system', 'content': VERDICT_SYSTEM_PROMPT},
                {
                    'role': 'user',
                    'content': json.dumps(
                        {
                            'scene_text': scene_text,
                            'extraction': {
                                'characters': [candidate.name for candidate in extraction.characters],
                                'objects': [candidate.name for candidate in extraction.objects],
                                'events': [event.summary for event in extraction.events],
                                'facts': [fact.summary for fact in extraction.facts],
                                'relations': [relation.summary for relation in extraction.relations],
                                'temporal_hints': extraction.temporal_hints,
                                'unresolved_references': extraction.unresolved_references,
                            },
                            'context': compact_context,
                        },
                        ensure_ascii=False,
                    ),
                },
            ],
            'temperature': 0.1,
            'response_format': {'type': 'json_object'},
        }
        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.post(
                    'https://api.openai.com/v1/chat/completions',
                    headers={'Authorization': f'Bearer {self.api_key}', 'Content-Type': 'application/json'},
                    json=payload,
                )
                response.raise_for_status()
            parsed = json.loads(response.json()['choices'][0]['message']['content'])
            return ConsistencyVerdict(
                status=parsed.get('status', 'uncertain'),
                issue_type=parsed.get('issue_type', 'none'),
                explanation=str(parsed.get('explanation', 'Недостаточно данных для уверенного вывода.')),
                confidence=float(parsed.get('confidence', 0.5)),
                should_stage_update=bool(parsed.get('should_stage_update', False)),
                stop_reason=str(parsed.get('stop_reason', 'llm_verdict')),
            )
        except Exception as exc:
            logger.warning('agent_v2 verdict failed, falling back to heuristic: %s', exc)
            return self._fallback_verdict(extraction=extraction, context=context)

    def _precheck_verdict(self, *, extraction: ExtractionResult, context: ContextCollectionResult) -> ConsistencyVerdict | None:
        trait_facts_by_subject: dict[str, list[str]] = {}
        for fact in extraction.facts:
            if fact.fact_kind != 'character_trait' or not fact.subject_name:
                continue
            trait_facts_by_subject.setdefault(fact.subject_name.lower(), []).append(fact.summary.lower())

        for subject_name, summaries in trait_facts_by_subject.items():
            for trait, opposite in OPPOSITE_TRAITS.items():
                if any(trait in summary for summary in summaries) and any(opposite in summary for summary in summaries):
                    return ConsistencyVerdict(
                        status='conflict',
                        issue_type='character',
                        explanation=f'Найден character conflict: в новом фрагменте персонаж {subject_name.capitalize()} одновременно описан противоположными чертами.',
                        confidence=0.83,
                        should_stage_update=False,
                        stop_reason='internal_character_conflict',
                    )

        if extraction.unresolved_references and not context.chunk_windows:
            return ConsistencyVerdict(
                status='uncertain',
                issue_type='none',
                explanation='Недостаточно контекста для разрешения ссылок в сцене.',
                confidence=0.4,
                should_stage_update=False,
                stop_reason='unresolved_references',
            )
        return None

    def _fallback_next_action(self, *, extraction: ExtractionResult, context: ContextCollectionResult) -> OrchestratorDecision:
        if (extraction.characters or extraction.objects or extraction.unresolved_references) and not context.matched_entity_bundles and not context.chunk_windows:
            return OrchestratorDecision(action='collect_relevant_context', rationale='need_memory_context')
        return OrchestratorDecision(action='finish', rationale='enough_local_structure')

    def _fallback_verdict(self, *, extraction: ExtractionResult, context: ContextCollectionResult) -> ConsistencyVerdict:
        for bundle in context.matched_entity_bundles:
            if bundle.character_profile is None:
                continue
            trait_summary = bundle.character_profile.trait_summary.lower()
            for fact in extraction.facts:
                if fact.fact_kind != 'character_trait' or not fact.subject_name:
                    continue
                if fact.subject_name.lower() != bundle.entity.name.lower():
                    continue
                lowered_fact = fact.summary.lower()
                for trait, opposite in OPPOSITE_TRAITS.items():
                    if trait in trait_summary and opposite in lowered_fact:
                        return ConsistencyVerdict(
                            status='conflict',
                            issue_type='character',
                            explanation=f'Найден character conflict: новое поведение противоречит закреплённому описанию персонажа {bundle.entity.name}.',
                            confidence=0.77,
                            should_stage_update=False,
                            stop_reason='character_conflict',
                        )

        for bundle in context.matched_entity_bundles:
            if bundle.object_profile is None:
                continue
            object_name = bundle.entity.name.lower()
            related_facts = ' '.join(fact.summary.lower() for fact in bundle.facts)
            for fact in extraction.facts:
                if fact.fact_kind != 'object_state' or not fact.object_name:
                    continue
                if fact.object_name.lower() != object_name:
                    continue
                lowered = fact.summary.lower()
                if 'потер' in related_facts and any(token in lowered for token in ('вынул', 'вытащил', 'достал', 'держал', 'открыл')):
                    return ConsistencyVerdict(
                        status='conflict',
                        issue_type='object',
                        explanation=f'Найден object conflict: объект {bundle.entity.name} ранее считался утраченным, но в новой сцене снова используется без объяснения.',
                        confidence=0.81,
                        should_stage_update=False,
                        stop_reason='object_conflict',
                    )

        should_stage_update = bool(extraction.characters or extraction.objects or extraction.events or extraction.facts or extraction.relations)
        return ConsistencyVerdict(
            status='no_conflict',
            issue_type='none',
            explanation='Явных конфликтов с доступной memory не найдено.',
            confidence=0.68,
            should_stage_update=should_stage_update,
            stop_reason='heuristic_verdict_complete',
        )

