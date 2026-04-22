from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

from .common import compact_object_schema, jsonable, loose_array


@dataclass(frozen=True)
class RunRecord:
    id: str
    workspace_ref: str
    cwd: str
    command: str
    command_hash: str
    started_at: str
    finished_at: str
    exit_code: int
    output_quotes: Sequence[str] = field(default_factory=tuple)
    project_ref: str | None = None
    task_ref: str | None = None
    grant_ref: str | None = None

    def to_payload(self) -> dict[str, Any]:
        return {key: value for key, value in jsonable(self).items() if value is not None}


RUN_RECORD_SCHEMA = compact_object_schema(
    schema_id="https://trust-evidence-protocol.local/schemas/0.4/run.record.schema.json",
    title="TEP 0.4 RUN record",
    description="Command execution trace used as runtime provenance.",
    required=("id", "workspace_ref", "cwd", "command", "command_hash", "started_at", "finished_at", "exit_code", "output_quotes"),
    properties={
        "id": {"type": "string", "pattern": "^RUN-"},
        "workspace_ref": {"type": "string", "pattern": "^WSP-"},
        "project_ref": {"type": ["string", "null"], "pattern": "^PRJ-"},
        "task_ref": {"type": ["string", "null"], "pattern": "^TASK-"},
        "grant_ref": {"type": ["string", "null"], "pattern": "^GRANT-"},
        "cwd": {"type": "string", "minLength": 1},
        "command": {"type": "string", "minLength": 1},
        "command_hash": {"type": "string", "minLength": 1},
        "started_at": {"type": "string"},
        "finished_at": {"type": "string"},
        "exit_code": {"type": "integer"},
        "output_quotes": loose_array("Quoted command output fragments used for future support."),
    },
)
