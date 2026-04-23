"""Migration for owner-bound WCTX-* records introduced as record_version=1."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

from ..record_versions import CURRENT_RECORD_CONTRACT_VERSION, CURRENT_RECORD_VERSION
from .base import SchemaMigrationIssue, SchemaMigrationResult


ARRAY_FIELDS = (
    "pinned_refs",
    "focus_paths",
    "topic_terms",
    "topic_seed_refs",
    "assumptions",
    "concerns",
    "supersedes_refs",
    "project_refs",
    "task_refs",
    "tags",
)


class WorkingContextV1Migration:
    id = "20260423_working_context_v1"
    description = "Normalize owner-bound WCTX-* records to contract_version=0.4 and record_version=1."

    def applies_to(self, path: Path, record: dict) -> bool:
        if str(record.get("record_type", "")).strip() != "working_context" and path.parent.name != "working_context":
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

        ownership_mode = str(migrated.get("ownership_mode", "")).strip()
        if ownership_mode and ownership_mode != "owner-only":
            issues.append(
                SchemaMigrationIssue(
                    path=relative_path,
                    reason="unsupported_wctx_ownership_mode",
                    detail="WCTX-* record_version=1 requires ownership_mode=owner-only.",
                    migration_id=self.id,
                    record_id=record_id,
                )
            )
        handoff_policy = str(migrated.get("handoff_policy", "")).strip()
        if handoff_policy and handoff_policy != "fork-required":
            issues.append(
                SchemaMigrationIssue(
                    path=relative_path,
                    reason="unsupported_wctx_handoff_policy",
                    detail="WCTX-* record_version=1 requires handoff_policy=fork-required.",
                    migration_id=self.id,
                    record_id=record_id,
                )
            )

        migrated.pop("schema_version", None)
        migrated["contract_version"] = CURRENT_RECORD_CONTRACT_VERSION
        migrated["record_version"] = CURRENT_RECORD_VERSION
        migrated.setdefault("record_type", "working_context")
        migrated.setdefault("status", "active")
        migrated.setdefault("context_kind", "general")
        migrated.setdefault("ownership_mode", "owner-only")
        migrated.setdefault("handoff_policy", "fork-required")
        migrated.setdefault("parent_context_ref", "")
        if not str(migrated.get("note", "")).strip():
            migrated["note"] = "Migrated owner-bound WCTX operational context."
        for key in ARRAY_FIELDS:
            migrated.setdefault(key, [])

        return SchemaMigrationResult(record=migrated, issues=tuple(issues))


MIGRATION = WorkingContextV1Migration()
