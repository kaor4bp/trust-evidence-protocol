"""Registered record schema migrations.

Every schema change gets its own module and exports a single MIGRATION object.
The registry order is the only supported application order.
"""

from __future__ import annotations

from .base import RecordSchemaMigration, SchemaMigrationIssue, SchemaMigrationResult
from .agent_identity_v1 import MIGRATION as AGENT_IDENTITY_V1
from .map_record_v1 import MIGRATION as MAP_RECORD_V1
from .working_context_v1 import MIGRATION as WORKING_CONTEXT_V1


SCHEMA_MIGRATIONS: tuple[RecordSchemaMigration, ...] = (
    AGENT_IDENTITY_V1,
    WORKING_CONTEXT_V1,
    MAP_RECORD_V1,
)


def registered_schema_migrations() -> tuple[RecordSchemaMigration, ...]:
    return SCHEMA_MIGRATIONS


__all__ = [
    "RecordSchemaMigration",
    "SCHEMA_MIGRATIONS",
    "SchemaMigrationIssue",
    "SchemaMigrationResult",
    "registered_schema_migrations",
]
