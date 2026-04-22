from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .common import compact_object_schema, jsonable


EVIDENCE_KINDS = ("file-line", "url", "command-output", "user-input", "artifact")


@dataclass(frozen=True)
class RecordEvidenceRequest:
    kind: str
    quote: str
    claim_text: str | None = None
    path: str | None = None
    line_start: int | None = None
    line_end: int | None = None
    url: str | None = None
    command: str | None = None
    input_ref: str | None = None
    artifact_ref: str | None = None

    def to_payload(self) -> dict[str, Any]:
        return {key: value for key, value in jsonable(self).items() if value is not None}


RECORD_EVIDENCE_REQUEST_SCHEMA = compact_object_schema(
    schema_id="https://trust-evidence-protocol.local/schemas/0.4/record_evidence.request.schema.json",
    title="TEP 0.4 record_evidence request",
    description="Agent-supplied support surface. Runtime creates provenance graph records.",
    required=("kind", "quote"),
    properties={
        "kind": {"type": "string", "enum": list(EVIDENCE_KINDS)},
        "quote": {"type": "string", "minLength": 1},
        "claim_text": {"type": "string"},
        "path": {"type": "string"},
        "line_start": {"type": "integer", "minimum": 1},
        "line_end": {"type": "integer", "minimum": 1},
        "url": {"type": "string"},
        "command": {"type": "string"},
        "input_ref": {"type": "string", "pattern": "^INP-"},
        "artifact_ref": {"type": "string", "pattern": "^ART-"},
    },
)
