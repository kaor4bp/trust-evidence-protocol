from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from .common import CONTRACT_VERSION, CONTRACT_VERSION_PROPERTY, ROUTE_TOKEN_PROPERTY, compact_object_schema, jsonable, loose_array, loose_object


@dataclass(frozen=True)
class LookupResponse:
    focus: Mapping[str, Any]
    route_token: str
    ranked_context: Sequence[Mapping[str, Any]] = field(default_factory=tuple)
    chain_candidates: Sequence[Mapping[str, Any]] = field(default_factory=tuple)
    curiosity: Mapping[str, Any] = field(default_factory=dict)
    map_navigation: Mapping[str, Any] = field(default_factory=dict)
    next_allowed_tools: Sequence[str] = field(default_factory=tuple)
    repair: Sequence[Mapping[str, Any]] = field(default_factory=tuple)
    lookup_is_proof: bool = False
    contract_version: str = CONTRACT_VERSION

    def to_payload(self) -> dict[str, Any]:
        return jsonable(self)


LOOKUP_RESPONSE_SCHEMA = compact_object_schema(
    schema_id="https://trust-evidence-protocol.local/schemas/0.4/lookup.response.schema.json",
    title="TEP 0.4 lookup response",
    description="Navigation response for fact, code, policy, theory, and chain-extension lookup.",
    required=(
        "contract_version",
        "lookup_is_proof",
        "focus",
        "ranked_context",
        "chain_candidates",
        "curiosity",
        "map_navigation",
        "next_allowed_tools",
        "route_token",
        "repair",
    ),
    properties={
        "contract_version": CONTRACT_VERSION_PROPERTY,
        "lookup_is_proof": {"type": "boolean", "const": False},
        "focus": loose_object("Workspace/project/task/WCTX focus projection."),
        "ranked_context": loose_array("Navigation candidates ranked by authority and relevance."),
        "chain_candidates": loose_array("Proof-capable candidate nodes for chain construction."),
        "curiosity": loose_object("Compact curiosity/map signals."),
        "map_navigation": loose_object("Navigation-only durable MAP-* cells and map-session hints."),
        "start_briefing": loose_object("Navigation-only current STEP branch, recent steps, recent actions, and checks."),
        "reason_pressure": loose_object("Navigation/control pressure that makes STEP-* the preferred next cursor update."),
        "next_allowed_tools": {"type": "array", "items": {"type": "string"}},
        "route_token": ROUTE_TOKEN_PROPERTY,
        "repair": loose_array("Repair routes when lookup is blocked or weak."),
    },
)
