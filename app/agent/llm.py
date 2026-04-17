from __future__ import annotations

import json
import logging
from typing import Literal

import httpx

from app.core.config import settings

logger = logging.getLogger("story-consistency-agent.llm")

ToolName = Literal[
    "search_story_chunks",
    "query_story_memory",
    "get_character_profile",
    "get_timeline_window",
]

ALLOWED_TOOLS: tuple[ToolName, ...] = (
    "search_story_chunks",
    "query_story_memory",
    "get_character_profile",
    "get_timeline_window",
)


class LLMDecisionEngine:
    def __init__(self) -> None:
        self.openai_api_key = settings.openai_api_key
        self.model = settings.llm_model

    @property
    def enabled(self) -> bool:
        return bool(self.openai_api_key)

    def choose_tool_plan(
        self,
        *,
        story_title: str,
        scene_text: str,
        question: str | None,
        memory_preview: list[str],
    ) -> tuple[list[ToolName], str]:
        if not self.enabled:
            return self._heuristic_plan(scene_text=scene_text, question=question)

        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are an orchestration planner for a story consistency agent. "
                        "Choose the smallest useful ordered subset of tools. "
                        "Return strict JSON with keys tools and rationale. "
                        "Tools must come only from the allowed list."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "story_title": story_title,
                            "scene_text": scene_text,
                            "question": question,
                            "allowed_tools": list(ALLOWED_TOOLS),
                            "memory_preview": memory_preview[:6],
                        },
                        ensure_ascii=False,
                    ),
                },
            ],
            "temperature": 0.1,
            "response_format": {"type": "json_object"},
        }

        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.openai_api_key}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                )
                response.raise_for_status()
        except Exception as exc:
            logger.warning("llm tool planning failed, falling back to heuristics: %s", exc)
            return self._heuristic_plan(scene_text=scene_text, question=question)

        try:
            content = response.json()["choices"][0]["message"]["content"]
            parsed = json.loads(content)
            tools = [tool for tool in parsed.get("tools", []) if tool in ALLOWED_TOOLS]
            rationale = str(parsed.get("rationale", "llm_planned_tools"))
            if not tools:
                return self._heuristic_plan(scene_text=scene_text, question=question)
            return tools[:4], rationale
        except Exception as exc:
            logger.warning("llm tool plan parse failed, falling back to heuristics: %s", exc)
            return self._heuristic_plan(scene_text=scene_text, question=question)

    def synthesize_explanation(
        self,
        *,
        scene_text: str,
        issue_type: str,
        status: str,
        issues: list[str],
        evidence_refs: list[str],
        proposed_change_count: int,
    ) -> str | None:
        if not self.enabled:
            return None

        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You explain story consistency findings for a writer. "
                        "Be concise and specific. "
                        "Use these result labels: no_conflict, conflict, uncertain. "
                        "Use these conflict types when relevant: character, fact, timeline, object, mixed. "
                        "Start the explanation by explicitly naming the result and, if status=conflict, the conflict type. "
                        "Then briefly explain why."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "scene_text": scene_text,
                            "status": status,
                            "issue_type": issue_type,
                            "issues": issues,
                            "evidence_refs": evidence_refs[:5],
                            "proposed_change_count": proposed_change_count,
                        },
                        ensure_ascii=False,
                    ),
                },
            ],
            "temperature": 0.2,
        }

        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.openai_api_key}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                )
                response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"].strip()
        except Exception as exc:
            logger.warning("llm explanation synthesis failed, falling back to default text: %s", exc)
            return None

    def _heuristic_plan(self, *, scene_text: str, question: str | None) -> tuple[list[ToolName], str]:
        lowered = scene_text.lower()
        if question:
            lowered = f"{lowered} {question.lower()}"

        tools: list[ToolName] = ["search_story_chunks", "query_story_memory"]

        if any(token in lowered for token in ("day ", "день ", "timeline", "утро", "вечер", "неделю")):
            tools.append("get_timeline_window")

        if any(
            token in lowered
            for token in (
                "brave",
                "cowardly",
                "kind",
                "cruel",
                "смел",
                "труслив",
                "добр",
                "жесток",
            )
        ):
            tools.append("get_character_profile")

        deduped: list[ToolName] = []
        for tool in tools:
            if tool not in deduped:
                deduped.append(tool)
        return deduped[:4], "heuristic_tool_plan"
