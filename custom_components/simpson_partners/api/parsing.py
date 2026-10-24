"""Strict readers for JSON values in S&P Connect responses.

Each reader returns the typed value or raises ``ValueError`` naming the key,
so a malformed response fails loudly instead of producing a half-filled model.
"""

from __future__ import annotations

from datetime import datetime

type JsonObject = dict[str, object]


def as_object(value: object) -> JsonObject:
    """Return value as a JSON object, or raise if it is not one."""
    if not isinstance(value, dict):
        raise ValueError("expected a JSON object")
    return {str(key): item for key, item in value.items()}


def get_str(data: JsonObject, key: str) -> str:
    """Return a required string field."""
    value = data.get(key)
    if not isinstance(value, str):
        raise ValueError(f"{key} is missing or not a string")
    return value


def get_optional_str(data: JsonObject, key: str) -> str | None:
    """Return a string field, or None when it is absent or null."""
    return None if data.get(key) is None else get_str(data, key)


def get_bool(data: JsonObject, key: str) -> bool:
    """Return a required boolean field."""
    value = data.get(key)
    if not isinstance(value, bool):
        raise ValueError(f"{key} is missing or not a boolean")
    return value


def get_int(data: JsonObject, key: str) -> int:
    """Return a required integer field (booleans are rejected)."""
    value = data.get(key)
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{key} is missing or not an integer")
    return value


def get_float(data: JsonObject, key: str) -> float:
    """Return a required numeric field as a float (booleans are rejected)."""
    value = data.get(key)
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise ValueError(f"{key} is missing or not a number")
    return float(value)


def get_optional_float(data: JsonObject, key: str) -> float | None:
    """Return a numeric field, or None when it is absent or null."""
    return None if data.get(key) is None else get_float(data, key)


def get_datetime(data: JsonObject, key: str) -> datetime:
    """Return a required ISO 8601 timestamp; it must carry a time zone."""
    parsed = datetime.fromisoformat(get_str(data, key))
    if parsed.tzinfo is None:
        raise ValueError(f"{key} has no time zone")
    return parsed


def get_optional_datetime(data: JsonObject, key: str) -> datetime | None:
    """Return a timestamp field, or None when it is absent or null."""
    return None if data.get(key) is None else get_datetime(data, key)
