from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .common import ACTION_KINDS, compact_object_schema, jsonable


GRANT_MODES = ("edit", "test", "permission", "final")


@dataclass(frozen=True)
class GrantRecord:
    id: str
    reason_ref: str
    workspace_ref: str
    task_ref: str
    mode: str
    action_kind: str
    cwd: str
    valid_from: str
    valid_until: str
    context_fingerprint: str
    project_ref: str | None = None
    command_hash: str | None = None

    def to_payload(self) -> dict[str, Any]:
        return {key: value for key, value in jsonable(self).items() if value is not None}


GRANT_RECORD_SCHEMA = compact_object_schema(
    schema_id="https://trust-evidence-protocol.local/schemas/0.4/grant.record.schema.json",
    title="TEP 0.4 GRANT record",
    description="Append-only authorization record. Use is inferred from linked RUN/protected records.",
    required=(
        "id",
        "reason_ref",
        "workspace_ref",
        "task_ref",
        "mode",
        "action_kind",
        "cwd",
        "valid_from",
        "valid_until",
        "context_fingerprint",
    ),
    properties={
        "id": {"type": "string", "pattern": "^GRANT-"},
        "reason_ref": {"type": "string", "pattern": "^STEP-"},
        "workspace_ref": {"type": "string", "pattern": "^WSP-"},
        "project_ref": {"type": ["string", "null"], "pattern": "^PRJ-"},
        "task_ref": {"type": "string", "pattern": "^TASK-"},
        "mode": {"type": "string", "enum": list(GRANT_MODES)},
        "action_kind": {"type": "string", "enum": list(ACTION_KINDS)},
        "cwd": {"type": "string", "minLength": 1},
        "command_hash": {"type": "string"},
        "valid_from": {"type": "string"},
        "valid_until": {"type": "string"},
        "context_fingerprint": {"type": "string", "minLength": 1},
    },
)
