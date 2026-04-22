from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import asdict, is_dataclass
from typing import Any


CONTRACT_VERSION = "0.4"
LEGACY_API_CONTRACT_VERSION = 1
JSON_SCHEMA_DRAFT = "https://json-schema.org/draft/2020-12/schema"

ACTION_KINDS = ("bash", "file-write", "mcp-write", "git", "final")


def jsonable(value: Any) -> Any:
    """Convert contract dataclasses and tuples into JSON-compatible values."""

    if is_dataclass(value) and not isinstance(value, type):
        return jsonable(asdict(value))
    if isinstance(value, Mapping):
        return {str(key): jsonable(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [jsonable(item) for item in value]
    if isinstance(value, list):
        return [jsonable(item) for item in value]
    return value


def compact_object_schema(
    *,
    schema_id: str,
    title: str,
    required: Sequence[str],
    properties: Mapping[str, Mapping[str, Any]],
    description: str = "",
    additional_properties: bool = True,
) -> dict[str, Any]:
    schema: dict[str, Any] = {
        "$schema": JSON_SCHEMA_DRAFT,
        "$id": schema_id,
        "title": title,
        "type": "object",
        "required": list(required),
        "properties": dict(properties),
        "additionalProperties": additional_properties,
    }
    if description:
        schema["description"] = description
    return schema


CONTRACT_VERSION_PROPERTY = {"type": "string", "const": CONTRACT_VERSION}
ROUTE_TOKEN_PROPERTY = {"type": "string", "pattern": "^ROUTE-[A-Za-z0-9_.:-]+$"}


def ref_property(prefix: str) -> dict[str, Any]:
    return {"type": "string", "pattern": f"^{prefix}-"}


def nullable_ref_property(prefix: str) -> dict[str, Any]:
    return {"anyOf": [ref_property(prefix), {"type": "null"}]}


def loose_array(description: str = "") -> dict[str, Any]:
    schema: dict[str, Any] = {"type": "array", "items": {}}
    if description:
        schema["description"] = description
    return schema


def loose_object(description: str = "") -> dict[str, Any]:
    schema: dict[str, Any] = {"type": "object", "additionalProperties": True}
    if description:
        schema["description"] = description
    return schema
