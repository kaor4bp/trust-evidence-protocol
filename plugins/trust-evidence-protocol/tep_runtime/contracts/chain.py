from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from .common import CONTRACT_VERSION, CONTRACT_VERSION_PROPERTY, compact_object_schema, jsonable, loose_array


@dataclass(frozen=True)
class ChainValidationResponse:
    valid: bool
    proof_allowed: bool
    augmented_nodes: Sequence[Mapping[str, Any]] = field(default_factory=tuple)
    missing_links: Sequence[Mapping[str, Any]] = field(default_factory=tuple)
    gaps: Sequence[Mapping[str, Any]] = field(default_factory=tuple)
    repair: Sequence[Mapping[str, Any]] = field(default_factory=tuple)
    contract_version: str = CONTRACT_VERSION

    def to_payload(self) -> dict[str, Any]:
        return jsonable(self)


CHAIN_VALIDATION_RESPONSE_SCHEMA = compact_object_schema(
    schema_id="https://trust-evidence-protocol.local/schemas/0.4/validate_chain.response.schema.json",
    title="TEP 0.4 validate_chain response",
    description="Mechanical chain validation result. Validity is not proof of reasoning quality.",
    required=("contract_version", "valid", "proof_allowed", "augmented_nodes", "missing_links", "gaps", "repair"),
    properties={
        "contract_version": CONTRACT_VERSION_PROPERTY,
        "valid": {"type": "boolean"},
        "proof_allowed": {"type": "boolean"},
        "augmented_nodes": loose_array("Nodes with surfaced provenance, quotes, and warnings."),
        "missing_links": loose_array("Required links that validation could not establish."),
        "gaps": loose_array("Open questions, competing hypotheses, or chain gaps."),
        "repair": loose_array("Repair routes for invalid or incomplete chains."),
    },
)
