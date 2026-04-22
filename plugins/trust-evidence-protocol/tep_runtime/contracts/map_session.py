from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from .common import CONTRACT_VERSION, CONTRACT_VERSION_PROPERTY, compact_object_schema, jsonable, loose_array, loose_object


@dataclass(frozen=True)
class MapViewResponse:
    map_session_ref: str
    zone: Mapping[str, Any]
    anchor_facts: Sequence[Mapping[str, Any]] = field(default_factory=tuple)
    ignored_but_relevant: Sequence[Mapping[str, Any]] = field(default_factory=tuple)
    bridge_facts: Sequence[Mapping[str, Any]] = field(default_factory=tuple)
    tension_facts: Sequence[Mapping[str, Any]] = field(default_factory=tuple)
    signals: Mapping[str, Any] = field(default_factory=dict)
    allowed_moves: Sequence[Mapping[str, Any]] = field(default_factory=tuple)
    proof_routes: Sequence[Mapping[str, Any]] = field(default_factory=tuple)
    map_is_proof: bool = False
    contract_version: str = CONTRACT_VERSION

    def to_payload(self) -> dict[str, Any]:
        return jsonable(self)


MAP_VIEW_RESPONSE_SCHEMA = compact_object_schema(
    schema_id="https://trust-evidence-protocol.local/schemas/0.4/map_view.response.schema.json",
    title="TEP 0.4 map_view response",
    description="Bounded cognitive fact-map view. Navigation only, never proof.",
    required=(
        "contract_version",
        "map_is_proof",
        "map_session_ref",
        "zone",
        "anchor_facts",
        "ignored_but_relevant",
        "bridge_facts",
        "tension_facts",
        "signals",
        "allowed_moves",
        "proof_routes",
    ),
    properties={
        "contract_version": CONTRACT_VERSION_PROPERTY,
        "map_is_proof": {"type": "boolean", "const": False},
        "map_session_ref": {"type": "string", "pattern": "^WCTX-"},
        "zone": loose_object("Current bounded map zone."),
        "anchor_facts": loose_array("Primary support anchors for the current zone."),
        "ignored_but_relevant": loose_array("Cold but connected facts."),
        "bridge_facts": loose_array("Facts connecting this zone to another zone."),
        "tension_facts": loose_array("Stale, runtime, tentative, conflict, gap, or hypothesis signals."),
        "signals": loose_object("tap_smell, neglect_pressure, inquiry_pressure, promotion_pressure arrays."),
        "allowed_moves": loose_array("Allowed map moves from this zone."),
        "proof_routes": loose_array("Routes required before relying on map facts."),
    },
)
