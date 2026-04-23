from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from .common import ACTION_KINDS, CONTRACT_VERSION, compact_object_schema, jsonable


REASON_MODES = ("planning", "edit", "test", "debugging", "permission", "final", "curiosity")


@dataclass(frozen=True)
class ReasonStepRequest:
    task_ref: str
    mode: str
    intent: str
    claim_ref: str | None = None
    prev_claim_ref: str | None = None
    relation_claim_ref: str | None = None
    prev_step_ref: str | None = None
    wctx_ref: str | None = None
    branch: str = "main"
    action_kind: str | None = None

    def to_payload(self) -> dict[str, Any]:
        return {key: value for key, value in jsonable(self).items() if value is not None}


@dataclass(frozen=True)
class ReasonLedgerEntry:
    id: str
    entry_type: str
    created_at: str
    prev_ledger_hash: str
    entry_hash: str
    ledger_hash: str
    seal: str
    pow: Mapping[str, Any]
    version: int = 2
    record_type: str = "reason"
    chain_hash: str | None = None
    contract_version: str = CONTRACT_VERSION

    def to_payload(self) -> dict[str, Any]:
        return {key: value for key, value in jsonable(self).items() if value is not None}


REASON_STEP_REQUEST_SCHEMA = compact_object_schema(
    schema_id="https://trust-evidence-protocol.local/schemas/0.4/reason_step.request.schema.json",
    title="TEP 0.4 reason_step request",
    description="Task-local STEP claim-step append request.",
    required=("task_ref", "mode", "intent", "claim_ref"),
    properties={
        "task_ref": {"type": "string", "pattern": "^TASK-"},
        "mode": {"type": "string", "enum": list(REASON_MODES)},
        "branch": {"type": "string", "minLength": 1},
        "claim_ref": {"type": ["string", "null"], "pattern": "^CLM-"},
        "prev_claim_ref": {"type": ["string", "null"], "pattern": "^CLM-"},
        "relation_claim_ref": {"type": ["string", "null"], "pattern": "^CLM-"},
        "prev_step_ref": {"type": ["string", "null"], "pattern": "^STEP-"},
        "wctx_ref": {"type": ["string", "null"], "pattern": "^WCTX-"},
        "intent": {"type": "string", "minLength": 1},
        "action_kind": {"type": "string", "enum": list(ACTION_KINDS)},
    },
)


REASON_LEDGER_ENTRY_SCHEMA = compact_object_schema(
    schema_id="https://trust-evidence-protocol.local/schemas/0.4/reason_ledger.entry.schema.json",
    title="TEP 0.4 reason ledger entry",
    description=(
        "Append-only STEP/GRANT ledger entry with hash-chain, HMAC seal, and weak proof-of-work. "
        "PoW is tamper friction, not a security boundary."
    ),
    required=(
        "contract_version",
        "id",
        "record_type",
        "version",
        "entry_type",
        "created_at",
        "prev_ledger_hash",
        "entry_hash",
        "ledger_hash",
        "seal",
        "pow",
    ),
    properties={
        "contract_version": {"type": "string", "const": CONTRACT_VERSION},
        "id": {"type": "string", "pattern": "^(STEP|GRANT)-"},
        "record_type": {"type": "string", "const": "reason"},
        "version": {"type": "integer", "minimum": 2},
        "entry_type": {"type": "string", "enum": ["claim_step", "grant"]},
        "created_at": {"type": "string"},
        "prev_ledger_hash": {"type": "string", "pattern": "^sha256:"},
        "entry_hash": {"type": "string", "pattern": "^sha256:"},
        "ledger_hash": {"type": "string", "pattern": "^sha256:"},
        "seal": {"type": "string", "pattern": "^hmac-sha256:"},
        "pow": {
            "type": "object",
            "required": ("algorithm", "difficulty_bits", "nonce", "digest"),
            "properties": {
                "algorithm": {"type": "string", "const": "sha256-leading-zero-bits"},
                "difficulty_bits": {"type": "integer", "minimum": 0},
                "nonce": {"type": "string"},
                "digest": {"type": "string"},
            },
            "additionalProperties": True,
        },
        "chain_hash": {"type": "string"},
        "justification_valid": {"type": "boolean"},
        "decision_chain_valid": {"type": "boolean"},
        "decision_valid": {
            "type": "boolean",
            "description": "Compatibility alias for decision_chain_valid; new clients should read justification_valid/decision_chain_valid.",
        },
        "claim_ref": {"type": "string", "pattern": "^CLM-"},
        "prev_claim_ref": {"type": "string", "pattern": "^CLM-"},
        "relation_claim_ref": {"type": "string", "pattern": "^CLM-"},
        "prev_step_ref": {"type": "string", "pattern": "^STEP-"},
        "claim_step_hash": {"type": "string"},
    },
)
