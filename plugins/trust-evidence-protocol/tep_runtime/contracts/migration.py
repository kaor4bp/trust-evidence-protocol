from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from .common import CONTRACT_VERSION, CONTRACT_VERSION_PROPERTY, compact_object_schema, jsonable, loose_array


MIGRATION_MODES = ("dry-run", "apply")


@dataclass(frozen=True)
class MigrationReport:
    mode: str
    source: str
    target: str
    planned_actions: Sequence[Mapping[str, Any]] = field(default_factory=tuple)
    created_refs: Sequence[str] = field(default_factory=tuple)
    preserved_refs: Sequence[str] = field(default_factory=tuple)
    revoked_grants: Sequence[str] = field(default_factory=tuple)
    unresolved: Sequence[Mapping[str, Any]] = field(default_factory=tuple)
    backup_path: str | None = None
    applied: bool = False
    contract_version: str = CONTRACT_VERSION

    def to_payload(self) -> dict[str, Any]:
        return {key: value for key, value in jsonable(self).items() if value is not None}


MIGRATION_REPORT_SCHEMA = compact_object_schema(
    schema_id="https://trust-evidence-protocol.local/schemas/0.4/migration.report.schema.json",
    title="TEP 0.4 migration report",
    description="Dry-run/apply migration report for moving legacy context into ~/.tep_context.",
    required=("contract_version", "mode", "source", "target", "planned_actions", "created_refs", "preserved_refs", "revoked_grants", "unresolved", "applied"),
    properties={
        "contract_version": CONTRACT_VERSION_PROPERTY,
        "mode": {"type": "string", "enum": list(MIGRATION_MODES)},
        "source": {"type": "string", "minLength": 1},
        "target": {"type": "string", "minLength": 1},
        "planned_actions": loose_array("Actions the migration will or did perform."),
        "created_refs": {"type": "array", "items": {"type": "string"}},
        "preserved_refs": {"type": "array", "items": {"type": "string"}},
        "revoked_grants": {"type": "array", "items": {"type": "string", "pattern": "^GRANT-"}},
        "unresolved": loose_array("Records or issues requiring manual repair."),
        "backup_path": {"type": "string"},
        "applied": {"type": "boolean"},
    },
)
