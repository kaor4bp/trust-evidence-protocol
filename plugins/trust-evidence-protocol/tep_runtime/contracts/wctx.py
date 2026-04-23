from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from .common import (
    CONTRACT_VERSION,
    RECORD_VERSION,
    compact_object_schema,
    jsonable,
    loose_array,
    loose_object,
)


@dataclass(frozen=True)
class AgentIdentityRecord:
    id: str
    scope: str
    agent_name: str
    key_fingerprint: str
    created_at: str
    record_type: str = "agent_identity"
    key_algorithm: str = "hmac-sha256"
    key_scope: str = "local-agent"
    status: str = "active"
    note: str = "Public local-agent identity metadata only."
    contract_version: str = CONTRACT_VERSION
    record_version: int = RECORD_VERSION

    def to_payload(self) -> dict[str, Any]:
        return jsonable(self)


@dataclass(frozen=True)
class WorkingContextRecord:
    id: str
    title: str
    scope: str
    context_kind: str
    agent_identity_ref: str
    agent_key_fingerprint: str
    owner_signature: Mapping[str, Any]
    created_at: str
    updated_at: str
    status: str = "active"
    record_type: str = "working_context"
    ownership_mode: str = "owner-only"
    handoff_policy: str = "fork-required"
    pinned_refs: tuple[str, ...] = ()
    focus_paths: tuple[str, ...] = ()
    topic_terms: tuple[str, ...] = ()
    topic_seed_refs: tuple[str, ...] = ()
    map_sessions: Mapping[str, Any] = field(default_factory=dict)
    assumptions: tuple[Mapping[str, Any], ...] = ()
    concerns: tuple[str, ...] = ()
    parent_context_ref: str = ""
    supersedes_refs: tuple[str, ...] = ()
    project_refs: tuple[str, ...] = ()
    task_refs: tuple[str, ...] = ()
    tags: tuple[str, ...] = ()
    note: str = ""
    contract_version: str = CONTRACT_VERSION
    record_version: int = RECORD_VERSION

    def to_payload(self) -> dict[str, Any]:
        return jsonable(self)


OWNER_SIGNATURE_SCHEMA = {
    "type": "object",
    "required": ("algorithm", "signed_payload_hash", "signature"),
    "properties": {
        "algorithm": {"type": "string", "const": "hmac-sha256"},
        "signed_payload_hash": {"type": "string", "pattern": "^sha256:"},
        "signature": {"type": "string", "pattern": "^hmac-sha256:"},
        "signed_fields": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Canonical WCTX fields covered by signed_payload_hash.",
        },
    },
    "additionalProperties": True,
}


AGENT_IDENTITY_RECORD_SCHEMA = compact_object_schema(
    schema_id="https://trust-evidence-protocol.local/schemas/0.4/agent_identity.record.schema.json",
    title="TEP 0.4 agent identity record",
    description=(
        "Local agent identity metadata. The private key material is never stored in this public record; "
        "the record only exposes the fingerprint needed to verify owner-bound WCTX signatures."
    ),
    required=(
        "contract_version",
        "record_version",
        "id",
        "record_type",
        "scope",
        "agent_name",
        "key_algorithm",
        "key_fingerprint",
        "key_scope",
        "status",
        "created_at",
        "note",
    ),
    properties={
        "contract_version": {"type": "string", "const": CONTRACT_VERSION},
        "record_version": {"type": "integer", "const": RECORD_VERSION},
        "id": {"type": "string", "pattern": "^AGENT-"},
        "record_type": {"type": "string", "const": "agent_identity"},
        "scope": {"type": "string", "minLength": 1},
        "agent_name": {"type": "string", "minLength": 1},
        "key_algorithm": {"type": "string", "const": "hmac-sha256"},
        "key_fingerprint": {"type": "string", "pattern": "^sha256:"},
        "key_scope": {"type": "string", "const": "local-agent"},
        "status": {"type": "string", "enum": ["active", "revoked", "archived"]},
        "created_at": {"type": "string"},
        "note": {"type": "string", "minLength": 1},
    },
)


WORKING_CONTEXT_RECORD_SCHEMA = compact_object_schema(
    schema_id="https://trust-evidence-protocol.local/schemas/0.4/working_context.record.schema.json",
    title="TEP 0.4 working context record",
    description=(
        "Owner-bound WCTX operational focus. Other agents may inspect it as navigation/handoff context, "
        "but cannot use it as current focus; they must create a signed fork."
    ),
    required=(
        "contract_version",
        "record_version",
        "id",
        "record_type",
        "scope",
        "title",
        "status",
        "context_kind",
        "agent_identity_ref",
        "agent_key_fingerprint",
        "ownership_mode",
        "handoff_policy",
        "owner_signature",
        "created_at",
        "updated_at",
        "note",
    ),
    properties={
        "contract_version": {"type": "string", "const": CONTRACT_VERSION},
        "record_version": {"type": "integer", "const": RECORD_VERSION},
        "id": {"type": "string", "pattern": "^WCTX-"},
        "record_type": {"type": "string", "const": "working_context"},
        "scope": {"type": "string", "minLength": 1},
        "title": {"type": "string", "minLength": 1},
        "status": {"type": "string", "enum": ["active", "paused", "closed", "archived"]},
        "context_kind": {"type": "string", "minLength": 1},
        "agent_identity_ref": {"type": "string", "pattern": "^AGENT-"},
        "agent_key_fingerprint": {"type": "string", "pattern": "^sha256:"},
        "ownership_mode": {"type": "string", "const": "owner-only"},
        "handoff_policy": {"type": "string", "const": "fork-required"},
        "owner_signature": OWNER_SIGNATURE_SCHEMA,
        "pinned_refs": loose_array(),
        "focus_paths": loose_array(),
        "topic_terms": loose_array(),
        "topic_seed_refs": loose_array(),
        "map_sessions": loose_object("Owner-bound personal map sessions keyed by session name."),
        "assumptions": loose_array(),
        "concerns": loose_array(),
        "parent_context_ref": {"type": "string"},
        "supersedes_refs": loose_array(),
        "project_refs": loose_array(),
        "task_refs": loose_array(),
        "tags": loose_array(),
        "note": {"type": "string"},
        "created_at": {"type": "string"},
        "updated_at": {"type": "string"},
        "adoption_request": loose_object("Optional explicit request when an agent wants a fork/adopt workflow."),
    },
)
