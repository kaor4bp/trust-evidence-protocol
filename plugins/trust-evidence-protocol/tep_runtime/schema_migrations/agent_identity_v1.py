"""Migration for AGENT-* records introduced as record_version=1."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

from ..record_versions import CURRENT_RECORD_CONTRACT_VERSION, CURRENT_RECORD_VERSION
from .base import SchemaMigrationIssue, SchemaMigrationResult


class AgentIdentityV1Migration:
    id = "20260423_agent_identity_v1"
    description = "Normalize AGENT-* records to contract_version=0.4 and record_version=1."

    def applies_to(self, path: Path, record: dict) -> bool:
        if str(record.get("record_type", "")).strip() != "agent_identity" and path.parent.name != "agent_identity":
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

        key_algorithm = str(migrated.get("key_algorithm", "")).strip()
        if key_algorithm and key_algorithm != "hmac-sha256":
            issues.append(
                SchemaMigrationIssue(
                    path=relative_path,
                    reason="unsupported_agent_key_algorithm",
                    detail="AGENT-* record_version=1 requires key_algorithm=hmac-sha256.",
                    migration_id=self.id,
                    record_id=record_id,
                )
            )
        key_scope = str(migrated.get("key_scope", "")).strip()
        if key_scope and key_scope != "local-agent":
            issues.append(
                SchemaMigrationIssue(
                    path=relative_path,
                    reason="unsupported_agent_key_scope",
                    detail="AGENT-* record_version=1 requires key_scope=local-agent.",
                    migration_id=self.id,
                    record_id=record_id,
                )
            )

        migrated.pop("schema_version", None)
        migrated["contract_version"] = CURRENT_RECORD_CONTRACT_VERSION
        migrated["record_version"] = CURRENT_RECORD_VERSION
        migrated.setdefault("record_type", "agent_identity")
        migrated.setdefault("scope", "agent.local")
        migrated.setdefault("key_algorithm", "hmac-sha256")
        migrated.setdefault("key_scope", "local-agent")
        migrated.setdefault("status", "active")
        if not str(migrated.get("note", "")).strip():
            migrated["note"] = "Migrated AGENT identity metadata. Private key material remains runtime-private."

        return SchemaMigrationResult(record=migrated, issues=tuple(issues))


MIGRATION = AgentIdentityV1Migration()
