from __future__ import annotations

import re


def canonicalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


def entity_lookup_key(text: str) -> str:
    value = canonicalize(text).replace("ё", "е")
    value = re.sub(r"[ьъ]", "", value)
    value = re.sub(r"(ом|ем|ой|ей|ою|ею|ами|ями|ах|ях|ам|ям|у|ю|а|я|е|ы|и)$", "", value)
    value = re.sub(r"[аеёиоуыэюя]", "", value)
    return value or canonicalize(text)
