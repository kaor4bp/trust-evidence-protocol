"""Shared primitives for record schema migrations."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol


@dataclass(frozen=True)
class SchemaMigrationIssue:
    path: str
    reason: str
    detail: str = ""
    migration_id: str = ""
    record_id: str = ""

    def to_payload(self) -> dict[str, str]:
        payload = {
            "path": self.path,
            "reason": self.reason,
        }
        if self.detail:
            payload["detail"] = self.detail
        if self.migration_id:
            payload["migration_id"] = self.migration_id
        if self.record_id:
            payload["record_id"] = self.record_id
        return payload


@dataclass(frozen=True)
class SchemaMigrationResult:
    record: Mapping
    issues: Sequence[SchemaMigrationIssue] = field(default_factory=tuple)


class RecordSchemaMigration(Protocol):
    """One schema change module exposes exactly one object matching this protocol."""

    id: str
    description: str

    def applies_to(self, path: Path, record: Mapping) -> bool:
        """Return true when this migration should inspect and rewrite the record."""

    def migrate(self, path: Path, record: Mapping, *, relative_path: str) -> SchemaMigrationResult:
        """Return the migrated payload plus any blockers."""
