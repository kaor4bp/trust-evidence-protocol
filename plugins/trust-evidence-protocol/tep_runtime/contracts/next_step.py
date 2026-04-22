from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from .common import CONTRACT_VERSION, CONTRACT_VERSION_PROPERTY, compact_object_schema, jsonable, loose_array, loose_object


@dataclass(frozen=True)
class NextStepResponse:
    focus: Mapping[str, Any]
    route_graph: Mapping[str, Any]
    required_next: Sequence[str] = ("lookup",)
    blocked: bool = False
    repair: Sequence[Mapping[str, Any]] = field(default_factory=tuple)
    contract_version: str = CONTRACT_VERSION

    def to_payload(self) -> dict[str, Any]:
        return jsonable(self)


NEXT_STEP_RESPONSE_SCHEMA = compact_object_schema(
    schema_id="https://trust-evidence-protocol.local/schemas/0.4/next_step.response.schema.json",
    title="TEP 0.4 next_step response",
    description="Route selection response for the normal MCP front door.",
    required=("contract_version", "focus", "route_graph", "required_next", "blocked", "repair"),
    properties={
        "contract_version": CONTRACT_VERSION_PROPERTY,
        "focus": loose_object("Workspace/project/task/WCTX focus projection."),
        "route_graph": loose_object("Bounded route branches for the next allowed action."),
        "required_next": {"type": "array", "items": {"type": "string"}},
        "blocked": {"type": "boolean"},
        "repair": loose_array("Repair routes when blocked."),
    },
)
