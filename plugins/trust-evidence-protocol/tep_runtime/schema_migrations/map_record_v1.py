"""Migration for MAP-* records introduced as record_version=1."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

from ..record_versions import CURRENT_RECORD_CONTRACT_VERSION, CURRENT_RECORD_VERSION
from .base import SchemaMigrationIssue, SchemaMigrationResult


ARRAY_FIELDS = (
    "anchor_refs",
    "derived_from_refs",
    "up_refs",
    "down_refs",
    "adjacent_map_refs",
    "contradicts_map_refs",
    "refines_map_refs",
    "supersedes_refs",
    "tension_refs",
    "unknown_links",
    "proof_routes",
)
SCOPE_REF_FIELDS = ("workspace_refs", "project_refs", "task_refs", "wctx_refs")


class MapRecordV1Migration:
    id = "20260423_map_record_v1"
    description = "Normalize MAP-* records to contract_version=0.4 and record_version=1."

    def applies_to(self, path: Path, record: dict) -> bool:
        if str(record.get("record_type", "")).strip() != "map" and path.parent.name != "map":
            return False
        return (
            record.get("contract_version") != CURRENT_RECORD_CONTRACT_VERSION
            or record.get("record_version") != CURRENT_RECORD_VERSION
            or "schema_version" in record
        )

    def migrate(self, path: Path, record: dict, *, relative_path: str) -> SchemaMigrationResult:
        migrated: dict[str, Any] = deepcopy(dict(record))
        issues: list[SchemaMigrationIssue] = []
        record_id = str(migrated.get("id", "")).strip()

        if migrated.get("map_is_proof") is True:
            issues.append(
                SchemaMigrationIssue(
                    path=relative_path,
                    reason="map_record_claims_proof",
                    detail="MAP-* is navigation only; migration will not silently convert map_is_proof=true.",
                    migration_id=self.id,
                    record_id=record_id,
                )
            )

        migrated.pop("schema_version", None)
        migrated["contract_version"] = CURRENT_RECORD_CONTRACT_VERSION
        migrated["record_version"] = CURRENT_RECORD_VERSION
        migrated.setdefault("record_type", "map")
        migrated.setdefault("map_is_proof", False)
        migrated.setdefault("status", "active")
        migrated.setdefault("scope_refs", {})
        migrated.setdefault("signals", {})

        for key in ARRAY_FIELDS:
            migrated.setdefault(key, [])
        if isinstance(migrated.get("scope_refs"), dict):
            scope_refs = dict(migrated["scope_refs"])
            for key in SCOPE_REF_FIELDS:
                scope_refs.setdefault(key, [])
            migrated["scope_refs"] = scope_refs
        else:
            issues.append(
                SchemaMigrationIssue(
                    path=relative_path,
                    reason="invalid_scope_refs",
                    detail="scope_refs must be an object before MAP record_version=1 can be applied.",
                    migration_id=self.id,
                    record_id=record_id,
                )
            )
        if not isinstance(migrated.get("signals"), dict):
            issues.append(
                SchemaMigrationIssue(
                    path=relative_path,
                    reason="invalid_signals",
                    detail="signals must be an object before MAP record_version=1 can be applied.",
                    migration_id=self.id,
                    record_id=record_id,
                )
            )

        return SchemaMigrationResult(record=migrated, issues=tuple(issues))


MIGRATION = MapRecordV1Migration()
