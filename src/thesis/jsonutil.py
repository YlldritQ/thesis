"""Strict JSON conversion for persistent scientific-Python artifacts."""

from __future__ import annotations

import json
import math
from dataclasses import fields, is_dataclass
from datetime import date, datetime
from enum import Enum
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


def json_ready(value: Any, *, _seen: set[int] | None = None) -> Any:
    """Convert supported values to JSON types without silent stringification."""
    seen = set() if _seen is None else _seen

    if value is None or isinstance(value, (str, bool, int)):
        return value
    if value is pd.NA or value is pd.NaT:
        return None
    if isinstance(value, np.bool_):
        return bool(value)
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, (float, np.floating)):
        number = float(value)
        return number if math.isfinite(number) else None
    if isinstance(value, (datetime, date, pd.Timestamp)):
        return value.isoformat()
    if isinstance(value, np.datetime64):
        return None if np.isnat(value) else pd.Timestamp(value).isoformat()
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, Enum):
        return json_ready(value.value, _seen=seen)
    if isinstance(value, np.ndarray):
        return json_ready(value.tolist(), _seen=seen)

    object_id = id(value)
    if isinstance(value, dict):
        if object_id in seen:
            raise ValueError("Circular reference detected")
        seen.add(object_id)
        try:
            output: dict[str, Any] = {}
            for key, item in value.items():
                if not isinstance(key, str):
                    raise TypeError(f"JSON object keys must be strings, got {type(key).__name__}")
                output[key] = json_ready(item, _seen=seen)
            return output
        finally:
            seen.remove(object_id)
    if isinstance(value, (list, tuple)):
        if object_id in seen:
            raise ValueError("Circular reference detected")
        seen.add(object_id)
        try:
            return [json_ready(item, _seen=seen) for item in value]
        finally:
            seen.remove(object_id)
    if is_dataclass(value) and not isinstance(value, type):
        if object_id in seen:
            raise ValueError("Circular reference detected")
        seen.add(object_id)
        try:
            return {
                field.name: json_ready(getattr(value, field.name), _seen=seen)
                for field in fields(value)
            }
        finally:
            seen.remove(object_id)
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


def dumps_json(
    value: Any,
    *,
    indent: int | None = None,
    sort_keys: bool = False,
) -> str:
    """Serialize with RFC-compliant numbers and deterministic type handling."""
    return json.dumps(
        json_ready(value),
        indent=indent,
        sort_keys=sort_keys,
        ensure_ascii=False,
        allow_nan=False,
    )


def _reject_nonstandard_constant(token: str) -> None:
    raise ValueError(f"non-standard JSON numeric constant: {token}")


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON object key: {key!r}")
        result[key] = value
    return result


def loads_json(value: str | bytes | bytearray) -> Any:
    """Parse strict RFC JSON, rejecting extensions and duplicate keys."""
    return json.loads(
        value,
        parse_constant=_reject_nonstandard_constant,
        object_pairs_hook=_reject_duplicate_keys,
    )
