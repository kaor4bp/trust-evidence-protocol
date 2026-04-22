from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from .common import ACTION_KINDS, compact_object_schema, jsonable, loose_object


REASON_MODES = ("planning", "edit", "test", "debug", "permission", "final")


@dataclass(frozen=True)
class ReasonStepRequest:
    task_ref: str
    mode: str
    chain: Mapping[str, Any]
    intent: str
    parent_reason_ref: str | None = None
    branch: str = "main"
    action_kind: str | None = None

    def to_payload(self) -> dict[str, Any]:
        return {key: value for key, value in jsonable(self).items() if value is not None}


REASON_STEP_REQUEST_SCHEMA = compact_object_schema(
    schema_id="https://trust-evidence-protocol.local/schemas/0.4/reason_step.request.schema.json",
    title="TEP 0.4 reason_step request",
    description="Task-local REASON ledger append request.",
    required=("task_ref", "mode", "chain", "intent"),
    properties={
        "task_ref": {"type": "string", "pattern": "^TASK-"},
        "mode": {"type": "string", "enum": list(REASON_MODES)},
        "parent_reason_ref": {"type": ["string", "null"], "pattern": "^REASON-"},
        "branch": {"type": "string", "minLength": 1},
        "chain": loose_object("Public evidence/explanatory chain payload."),
        "intent": {"type": "string", "minLength": 1},
        "action_kind": {"type": "string", "enum": list(ACTION_KINDS)},
    },
)
