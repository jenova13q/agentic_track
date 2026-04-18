from __future__ import annotations

from dataclasses import fields
from typing import Any, TypeVar

T = TypeVar("T")


def row_to_model(model_cls: type[T], row: Any) -> T:
    payload = {field.name: row[field.name] for field in fields(model_cls) if field.name in row.keys()}
    return model_cls(**payload)
