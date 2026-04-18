from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from app.tools_v2.contracts import ContextCollectionResult, ExtractionResult

IssueType = Literal['character', 'fact', 'timeline', 'object', 'mixed', 'none']
StatusType = Literal['conflict', 'no_conflict', 'uncertain']
ActionType = Literal['collect_relevant_context', 'finish']


@dataclass(slots=True)
class OrchestratorDecision:
    action: ActionType
    rationale: str


@dataclass(slots=True)
class ConsistencyVerdict:
    status: StatusType
    issue_type: IssueType
    explanation: str
    confidence: float
    should_stage_update: bool
    stop_reason: str


@dataclass(slots=True)
class AgentV2Result:
    status: StatusType
    issue_type: IssueType
    explanation: str
    confidence: float
    extraction: ExtractionResult
    context: ContextCollectionResult
    staged_update_id: str | None = None
    staged_fragment_id: str | None = None
    staged_item_counts: dict[str, int] = field(default_factory=dict)
    orchestrator_mode: Literal['heuristic', 'llm'] = 'heuristic'
    step_count: int = 0
