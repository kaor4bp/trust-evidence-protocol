from __future__ import annotations


CONFIDENCE_LEVELS = {"high", "moderate", "low"}


def ensure_list(data: dict, key: str) -> list[str]:
    value = data.get(key, [])
    if value in ("", None):
        return []
    if isinstance(value, list):
        return [str(item) for item in value]
    raise ValueError(f"{key} must be a list")


def ensure_dict(data: dict, key: str) -> dict:
    value = data.get(key, {})
    if isinstance(value, dict):
        return value
    raise ValueError(f"{key} must be an object")


def ensure_string_list(data: dict, key: str) -> list[str]:
    values = ensure_list(data, key)
    return [str(value).strip() for value in values if str(value).strip()]


def safe_list(data: dict, key: str) -> list[str]:
    try:
        return ensure_list(data, key)
    except ValueError:
        return []


def validate_optional_confidence(data: dict, key: str = "confidence") -> list[str]:
    confidence = data.get(key)
    if confidence in ("", None):
        return []
    if str(confidence).strip() not in CONFIDENCE_LEVELS:
        return [f"{key} must be high, moderate, or low"]
    return []


def validate_optional_red_flags(data: dict, key: str = "red_flags") -> list[str]:
    if key not in data:
        return []
    try:
        values = ensure_string_list(data, key)
    except ValueError as exc:
        return [str(exc)]
    if not values and data.get(key) not in ([], "", None):
        return [f"{key} must contain non-empty strings when provided"]
    return []
