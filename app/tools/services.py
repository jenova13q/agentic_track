from __future__ import annotations

import re
from collections import Counter

from app.models.schemas import MemoryRecord, PendingUpdate, StoryData, ToolTrace
from app.retrieval.service import RetrieverService, tokenize

CHARACTER_RE = re.compile(r"\b[А-ЯЁA-Z][а-яёa-z]+\b")
DAY_RE = re.compile(r"\b(?:day|день)\s*(\d+)\b", re.IGNORECASE)
LOCATION_RE = re.compile(
    r"\b([А-ЯЁA-Z][а-яёa-z]+)\s+(?:lives in|жив[её]т в)\s+([А-ЯЁA-Z][\w-]+)",
    re.IGNORECASE,
)
TRAIT_RE = re.compile(
    r"\b([А-ЯЁA-Z][а-яёa-z]+)\s+(?:is|was|является|был|была)\s+([A-Za-zА-Яа-яЁё-]+)",
    re.IGNORECASE,
)

OPPOSITE_TRAITS = {
    "brave": "cowardly",
    "cowardly": "brave",
    "kind": "cruel",
    "cruel": "kind",
    "смелый": "трусливый",
    "трусливый": "смелый",
    "добрый": "жестокий",
    "жестокий": "добрый",
}


class ToolService:
    def __init__(self) -> None:
        self.retriever = RetrieverService()

    def search_story_chunks(self, story: StoryData, query: str) -> tuple[list[str], ToolTrace]:
        chunks = self.retriever.retrieve_chunks(story, query=query)
        refs = [chunk.source_ref for chunk in chunks]
        return refs, ToolTrace(
            tool_name="search_story_chunks",
            success=True,
            detail=f"retrieved {len(refs)} chunk refs",
        )

    def query_story_memory(self, story: StoryData, query: str) -> tuple[list[MemoryRecord], ToolTrace]:
        memory = self.retriever.retrieve_memory(story, query=query)
        return memory, ToolTrace(
            tool_name="query_story_memory",
            success=True,
            detail=f"retrieved {len(memory)} memory records",
        )

    def get_character_profile(self, story: StoryData, scene_text: str) -> tuple[list[MemoryRecord], ToolTrace]:
        names = set(CHARACTER_RE.findall(scene_text))
        character_records = [
            record
            for record in story.memory
            if record.type == "character" and record.attributes.get("name") in names
        ]
        return character_records, ToolTrace(
            tool_name="get_character_profile",
            success=True,
            detail=f"matched {len(character_records)} character records",
        )

    def get_timeline_window(self, story: StoryData, scene_text: str) -> tuple[list[MemoryRecord], ToolTrace]:
        markers = DAY_RE.findall(scene_text)
        timeline_records = [
            record for record in story.memory if record.type == "event" and "day" in record.attributes
        ]
        if markers:
            day_values = {int(value) for value in markers}
            timeline_records = [
                record
                for record in timeline_records
                if int(record.attributes.get("day", -999)) in day_values
            ]
        return timeline_records, ToolTrace(
            tool_name="get_timeline_window",
            success=True,
            detail=f"matched {len(timeline_records)} timeline records",
        )

    def propose_memory_update(self, summary: str, changes: list[MemoryRecord]) -> tuple[PendingUpdate | None, ToolTrace]:
        if not changes:
            return None, ToolTrace(
                tool_name="propose_memory_update",
                success=True,
                detail="no changes proposed",
            )
        return PendingUpdate(summary=summary, changes=changes), ToolTrace(
            tool_name="propose_memory_update",
            success=True,
            detail=f"prepared {len(changes)} pending changes",
        )


def build_story_chunks(story_id: str, text: str) -> list[dict[str, object]]:
    paragraphs = [paragraph.strip() for paragraph in re.split(r"\n\s*\n", text) if paragraph.strip()]
    chunks: list[dict[str, object]] = []
    for index, paragraph in enumerate(paragraphs):
        chunks.append(
            {
                "story_id": story_id,
                "index": index,
                "source_ref": f"chunk:{index}",
                "text": paragraph,
                "tokens": tokenize(paragraph),
            }
        )
    if not chunks:
        chunks.append(
            {
                "story_id": story_id,
                "index": 0,
                "source_ref": "chunk:0",
                "text": text.strip(),
                "tokens": tokenize(text),
            }
        )
    return chunks


def extract_memory_records(text: str) -> list[MemoryRecord]:
    records: list[MemoryRecord] = []

    names = [name for name in CHARACTER_RE.findall(text) if len(name) > 2]
    for name, count in Counter(names).items():
        if count < 2:
            continue
        records.append(
            MemoryRecord(
                type="character",
                canonical_value=f"Character {name}",
                confidence=0.55,
                evidence_refs=[f"name:{name}"],
                attributes={"name": name},
            )
        )

    for match in LOCATION_RE.finditer(text):
        name, location = match.groups()
        records.append(
            MemoryRecord(
                type="fact",
                canonical_value=f"{name} lives in {location}",
                confidence=0.75,
                evidence_refs=[f"location:{name}:{location}"],
                attributes={"name": name, "location": location},
            )
        )

    for match in TRAIT_RE.finditer(text):
        name, trait = match.groups()
        records.append(
            MemoryRecord(
                type="fact",
                canonical_value=f"{name} trait {trait.lower()}",
                confidence=0.7,
                evidence_refs=[f"trait:{name}:{trait.lower()}"],
                attributes={"name": name, "trait": trait.lower()},
            )
        )

    for match in DAY_RE.finditer(text):
        day_value = int(match.group(1))
        records.append(
            MemoryRecord(
                type="event",
                canonical_value=f"Timeline anchor day {day_value}",
                confidence=0.65,
                evidence_refs=[f"day:{day_value}"],
                attributes={"day": day_value},
            )
        )

    return records


def detect_conflicts(scene_text: str, memory: list[MemoryRecord]) -> tuple[list[str], list[MemoryRecord], str]:
    issues: list[str] = []
    proposed: list[MemoryRecord] = []
    issue_type = "none"

    memory_by_name: dict[str, list[MemoryRecord]] = {}
    for record in memory:
        name = record.attributes.get("name")
        if isinstance(name, str):
            memory_by_name.setdefault(name, []).append(record)

    for match in LOCATION_RE.finditer(scene_text):
        name, location = match.groups()
        known_locations = {
            item.attributes["location"]
            for item in memory_by_name.get(name, [])
            if "location" in item.attributes
        }
        if known_locations and location not in known_locations:
            issues.append(f"Факт о месте для {name} конфликтует с памятью истории.")
            issue_type = "fact"
        elif not known_locations:
            proposed.append(
                MemoryRecord(
                    type="fact",
                    canonical_value=f"{name} lives in {location}",
                    confidence=0.7,
                    status="pending",
                    evidence_refs=[f"scene-location:{name}:{location}"],
                    attributes={"name": name, "location": location},
                )
            )

    for match in TRAIT_RE.finditer(scene_text):
        name, trait = match.groups()
        trait = trait.lower()
        known_traits = {
            item.attributes["trait"]
            for item in memory_by_name.get(name, [])
            if "trait" in item.attributes
        }
        opposites = {OPPOSITE_TRAITS.get(value) for value in known_traits}
        if trait in opposites:
            issues.append(f"Черта {trait} для {name} противоречит ранее зафиксированному характеру.")
            issue_type = "character"
        elif not known_traits:
            proposed.append(
                MemoryRecord(
                    type="fact",
                    canonical_value=f"{name} trait {trait}",
                    confidence=0.65,
                    status="pending",
                    evidence_refs=[f"scene-trait:{name}:{trait}"],
                    attributes={"name": name, "trait": trait},
                )
            )

    scene_days = [int(value) for value in DAY_RE.findall(scene_text)]
    known_days = [int(item.attributes["day"]) for item in memory if "day" in item.attributes]
    if scene_days and known_days:
        min_known = min(known_days)
        max_known = max(known_days)
        for scene_day in scene_days:
            if scene_day < min_known or scene_day > max_known + 1:
                issues.append(
                    f"Таймлайн-ссылка на day {scene_day} выходит за ожидаемое окно истории."
                )
                issue_type = "timeline"
    elif scene_days:
        for scene_day in scene_days:
            proposed.append(
                MemoryRecord(
                    type="event",
                    canonical_value=f"Timeline anchor day {scene_day}",
                    confidence=0.6,
                    status="pending",
                    evidence_refs=[f"scene-day:{scene_day}"],
                    attributes={"day": scene_day},
                )
            )

    if issues and proposed and issue_type == "none":
        issue_type = "mixed"

    return issues, proposed, issue_type
