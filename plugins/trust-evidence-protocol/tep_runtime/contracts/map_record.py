from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from .common import (
    CONTRACT_VERSION,
    CONTRACT_VERSION_PROPERTY,
    RECORD_VERSION,
    RECORD_VERSION_PROPERTY,
    compact_object_schema,
    jsonable,
    loose_array,
    loose_object,
)


@dataclass(frozen=True)
class MapRecord:
    id: str
    scope: str
    level: str
    map_kind: str
    summary: str
    source_set_fingerprint: str
    generated_by: str
    generated_at: str
    updated_at: str
    stale_policy: str
    scope_refs: Mapping[str, Sequence[str]] = field(default_factory=dict)
    anchor_refs: Sequence[str] = field(default_factory=tuple)
    derived_from_refs: Sequence[str] = field(default_factory=tuple)
    up_refs: Sequence[str] = field(default_factory=tuple)
    down_refs: Sequence[str] = field(default_factory=tuple)
    adjacent_map_refs: Sequence[str] = field(default_factory=tuple)
    contradicts_map_refs: Sequence[str] = field(default_factory=tuple)
    refines_map_refs: Sequence[str] = field(default_factory=tuple)
    supersedes_refs: Sequence[str] = field(default_factory=tuple)
    tension_refs: Sequence[str] = field(default_factory=tuple)
    unknown_links: Sequence[Mapping[str, Any]] = field(default_factory=tuple)
    proof_routes: Sequence[Mapping[str, Any]] = field(default_factory=tuple)
    signals: Mapping[str, Any] = field(default_factory=dict)
    status: str = "active"
    map_is_proof: bool = False
    note: str = "Navigation only; drill down through proof_routes before using as support."
    record_type: str = "map"
    contract_version: str = CONTRACT_VERSION
    record_version: int = RECORD_VERSION

    def to_payload(self) -> dict[str, Any]:
        return jsonable(self)


MAP_RECORD_SCHEMA = compact_object_schema(
    schema_id="https://trust-evidence-protocol.local/schemas/0.4/map.record.schema.json",
    title="TEP 0.4 MAP record",
    description="Durable cognitive map cell. Navigation only, never proof.",
    required=(
        "contract_version",
        "record_version",
        "id",
        "record_type",
        "scope",
        "level",
        "map_kind",
        "status",
        "summary",
        "scope_refs",
        "anchor_refs",
        "derived_from_refs",
        "source_set_fingerprint",
        "up_refs",
        "down_refs",
        "adjacent_map_refs",
        "contradicts_map_refs",
        "refines_map_refs",
        "supersedes_refs",
        "tension_refs",
        "unknown_links",
        "proof_routes",
        "signals",
        "map_is_proof",
        "generated_by",
        "generated_at",
        "updated_at",
        "stale_policy",
        "note",
    ),
    properties={
        "contract_version": CONTRACT_VERSION_PROPERTY,
        "record_version": RECORD_VERSION_PROPERTY,
        "id": {"type": "string", "pattern": "^MAP-"},
        "record_type": {"type": "string", "const": "map"},
        "scope": {"type": "string", "minLength": 1},
        "level": {"type": "string", "enum": ["L1", "L2", "L3"]},
        "map_kind": {
            "type": "string",
            "enum": [
                "evidence_patch",
                "mechanism_cell",
                "pattern_cell",
                "workflow_cell",
                "code_area_cell",
                "risk_cell",
                "policy_cell",
                "open_frontier_cell",
                "task_situation",
                "debugging_strategy",
                "implementation_strategy",
                "curator_strategy",
                "retrospective_cell",
                "decision_pressure_cell",
            ],
        },
        "status": {"type": "string", "enum": ["active", "stale", "archived"]},
        "summary": {"type": "string", "minLength": 1},
        "scope_refs": loose_object("workspace/project/task/WCTX references for this map cell."),
        "anchor_refs": loose_array("Most important records for understanding this cell."),
        "derived_from_refs": loose_array("Records, cells, or generated views used to derive this cell."),
        "source_set_fingerprint": {"type": "string", "pattern": "^sha256:"},
        "up_refs": loose_array("Higher-abstraction MAP-* refs."),
        "down_refs": loose_array("Lower-abstraction MAP-* refs."),
        "adjacent_map_refs": loose_array("Neighboring MAP-* refs."),
        "contradicts_map_refs": loose_array("MAP-* refs in tension."),
        "refines_map_refs": loose_array("MAP-* refs refined by this cell."),
        "supersedes_refs": loose_array("MAP-* refs superseded by this cell."),
        "tension_refs": loose_array("Nearby claims/questions/cells carrying tension."),
        "unknown_links": loose_array("Candidate/missing/rejected/unknown structured link objects."),
        "proof_routes": loose_array("Drill-down routes to proof-capable records."),
        "signals": loose_object("tap, neglect, inquiry, promotion, staleness, and conflict pressure."),
        "map_is_proof": {"type": "boolean", "const": False},
        "generated_by": {"type": "string", "enum": ["lookup", "curiosity_map", "curator", "agent_request", "map_refresh"]},
        "generated_at": {"type": "string"},
        "updated_at": {"type": "string"},
        "stale_policy": {"type": "string", "enum": ["anchor_changed", "source_set_changed", "time_window_expired", "manual"]},
        "note": {"type": "string", "minLength": 1},
    },
)
