"""TEP 0.4 public contract helpers.

These modules define the stable payload shapes before adapters are rebuilt.
They intentionally avoid runtime IO and dependencies so CLI, MCP, hooks, and
tests can share the same contract vocabulary.
"""

from .chain import CHAIN_VALIDATION_RESPONSE_SCHEMA, ChainValidationResponse
from .common import ACTION_KINDS, CONTRACT_VERSION, LEGACY_API_CONTRACT_VERSION
from .evidence import RECORD_EVIDENCE_REQUEST_SCHEMA, RecordEvidenceRequest
from .grant import GRANT_RECORD_SCHEMA, GrantRecord
from .lookup import LOOKUP_RESPONSE_SCHEMA, LookupResponse
from .map_session import MAP_VIEW_RESPONSE_SCHEMA, MapViewResponse
from .migration import MIGRATION_REPORT_SCHEMA, MigrationReport
from .next_step import NEXT_STEP_RESPONSE_SCHEMA, NextStepResponse
from .reason import REASON_LEDGER_ENTRY_SCHEMA, REASON_STEP_REQUEST_SCHEMA, ReasonLedgerEntry, ReasonStepRequest
from .run import RUN_RECORD_SCHEMA, RunRecord
from .wctx import (
    AGENT_IDENTITY_RECORD_SCHEMA,
    WORKING_CONTEXT_RECORD_SCHEMA,
    AgentIdentityRecord,
    WorkingContextRecord,
)

__all__ = [
    "ACTION_KINDS",
    "AGENT_IDENTITY_RECORD_SCHEMA",
    "CHAIN_VALIDATION_RESPONSE_SCHEMA",
    "CONTRACT_VERSION",
    "GRANT_RECORD_SCHEMA",
    "LEGACY_API_CONTRACT_VERSION",
    "LOOKUP_RESPONSE_SCHEMA",
    "MAP_VIEW_RESPONSE_SCHEMA",
    "MIGRATION_REPORT_SCHEMA",
    "NEXT_STEP_RESPONSE_SCHEMA",
    "REASON_STEP_REQUEST_SCHEMA",
    "REASON_LEDGER_ENTRY_SCHEMA",
    "RECORD_EVIDENCE_REQUEST_SCHEMA",
    "RUN_RECORD_SCHEMA",
    "WORKING_CONTEXT_RECORD_SCHEMA",
    "AgentIdentityRecord",
    "ChainValidationResponse",
    "GrantRecord",
    "LookupResponse",
    "MapViewResponse",
    "MigrationReport",
    "NextStepResponse",
    "ReasonStepRequest",
    "ReasonLedgerEntry",
    "RecordEvidenceRequest",
    "RunRecord",
    "WorkingContextRecord",
]
