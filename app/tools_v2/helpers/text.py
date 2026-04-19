from __future__ import annotations

import re

NAME_RE = re.compile(r"\b[А-ЯЁ][а-яё]+\b")
PRONOUN_RE = re.compile(r"\b(он|она|они|его|её|ее|ему|ей|их|ему|нему|ней|им)\b", re.IGNORECASE)
TIME_HINT_RE = re.compile(r"\b(перед|после|затем|потом|раньше|позже|утром|вечером|ночью|накануне|через|спустя|до|во время)\b", re.IGNORECASE)
OBJECT_ACTION_RE = re.compile(r"\b(потерял|потеряла|вынул|вынула|вытащил|вытащила|достал|достала|наш[её]л|нашла|открыл|открыла|сжал|сжала|держал|держала|уронил|уронила|оставил|оставила)\s+([а-яё-]+)\b", re.IGNORECASE)
TRAIT_RE = re.compile(r"\b([А-ЯЁ][а-яё]+)\s+(?:был|была|казался|казалась|оставался|оставалась)\s+([а-яё-]+(?:\s+[а-яё-]+)*)", re.IGNORECASE)
LIVE_RE = re.compile(r"\b([А-ЯЁ][а-яё]+)\s+(?:жив[её]т|жил|жила)\s+в\s+([А-ЯЁ][а-яё-]+)\b", re.IGNORECASE)
MEETING_RE = re.compile(r"\b([А-ЯЁ][а-яё]+)\s+(?:встретил|встретила|встречает)\s+([А-ЯЁ][а-яё]+)\b", re.IGNORECASE)
ARRIVAL_RE = re.compile(r"\b([А-ЯЁ][а-яё]+)\s+(?:приехал|приехала|пришел|пришла|вернулся|вернулась|ждал|ждала|стоял|стояла|смотрел|смотрела|слушал|слушала|молчал|молчала|ответил|ответила)\b", re.IGNORECASE)

STOP_NAMES = {"К", "В", "И", "На", "По", "Но", "Он", "Она", "Они", "Это", "Тем", "Перед", "После"}


def canonicalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


def entity_lookup_key(text: str) -> str:
    value = canonicalize(text).replace("ё", "е")
    value = re.sub(r"[ьъ]", "", value)
    value = re.sub(r"(ом|ем|ой|ей|ою|ею|ами|ями|ах|ях|ам|ям|у|ю|а|я|е|ы|и)$", "", value)
    value = re.sub(r"[аеёиоуыэюя]", "", value)
    return value or canonicalize(text)


def normalize_location_name(text: str) -> str:
    value = text.strip()
    lowered = value.lower()
    if lowered.endswith("ске"):
        return value[:-1]
    if lowered.endswith("цке"):
        return value[:-1]
    if lowered.endswith("ном"):
        return value[:-2] + "ый"
    if lowered.endswith("ем"):
        return value[:-2]
    if lowered.endswith("ом") and len(value) > 4:
        return value[:-2] + "ый"
    if lowered.endswith("е") and len(value) > 5:
        return value[:-1]
    return value


def split_sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return [part.strip() for part in parts if part.strip()]


def extract_names(text: str) -> list[str]:
    seen: list[str] = []
    for match in NAME_RE.findall(text):
        if match in STOP_NAMES:
            continue
        if match not in seen:
            seen.append(match)
    return seen


def extract_pronouns(text: str) -> list[str]:
    seen: list[str] = []
    for match in PRONOUN_RE.findall(text):
        value = match.lower()
        if value not in seen:
            seen.append(value)
    return seen


def extract_temporal_hints(text: str) -> list[str]:
    hints: list[str] = []
    for sentence in split_sentences(text):
        if TIME_HINT_RE.search(sentence):
            hints.append(sentence)
    return hints


def summarize_sentence(sentence: str, max_words: int = 8) -> str:
    words = sentence.split()
    return " ".join(words[:max_words]).strip(" .,;:")
