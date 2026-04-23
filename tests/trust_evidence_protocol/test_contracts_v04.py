from __future__ import annotations

import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
PLUGIN_ROOT = REPO_ROOT / "plugins" / "trust-evidence-protocol"
SCHEMA_ROOT = REPO_ROOT / "schemas" / "0.4"

plugin_root = str(PLUGIN_ROOT)
if plugin_root not in sys.path:
    sys.path.insert(0, plugin_root)

from tep_runtime.contracts import (  # noqa: E402
    ACTION_KINDS,
    AGENT_IDENTITY_RECORD_SCHEMA,
    CHAIN_VALIDATION_RESPONSE_SCHEMA,
    CONTRACT_VERSION,
    GRANT_RECORD_SCHEMA,
    LOOKUP_RESPONSE_SCHEMA,
    MAP_RECORD_SCHEMA,
    MAP_VIEW_RESPONSE_SCHEMA,
    MIGRATION_REPORT_SCHEMA,
    NEXT_STEP_RESPONSE_SCHEMA,
    REASON_LEDGER_ENTRY_SCHEMA,
    REASON_STEP_REQUEST_SCHEMA,
    RECORD_EVIDENCE_REQUEST_SCHEMA,
    RUN_RECORD_SCHEMA,
    WORKING_CONTEXT_RECORD_SCHEMA,
    AgentIdentityRecord,
    ChainValidationResponse,
    GrantRecord,
    LookupResponse,
    MapRecord,
    MapViewResponse,
    MigrationReport,
    NextStepResponse,
    ReasonLedgerEntry,
    ReasonStepRequest,
    RecordEvidenceRequest,
    RunRecord,
    WorkingContextRecord,
)
from tep_runtime.record_versions import is_current_record_contract, validate_record_version  # noqa: E402


SCHEMA_EXPORTS = {
    "next_step.response.schema.json": NEXT_STEP_RESPONSE_SCHEMA,
    "lookup.response.schema.json": LOOKUP_RESPONSE_SCHEMA,
    "record_evidence.request.schema.json": RECORD_EVIDENCE_REQUEST_SCHEMA,
    "validate_chain.response.schema.json": CHAIN_VALIDATION_RESPONSE_SCHEMA,
    "reason_step.request.schema.json": REASON_STEP_REQUEST_SCHEMA,
    "reason_ledger.entry.schema.json": REASON_LEDGER_ENTRY_SCHEMA,
    "agent_identity.record.schema.json": AGENT_IDENTITY_RECORD_SCHEMA,
    "working_context.record.schema.json": WORKING_CONTEXT_RECORD_SCHEMA,
    "grant.record.schema.json": GRANT_RECORD_SCHEMA,
    "run.record.schema.json": RUN_RECORD_SCHEMA,
    "migration.report.schema.json": MIGRATION_REPORT_SCHEMA,
    "map_view.response.schema.json": MAP_VIEW_RESPONSE_SCHEMA,
    "map.record.schema.json": MAP_RECORD_SCHEMA,
}


def load_schema(name: str) -> dict:
    return json.loads((SCHEMA_ROOT / name).read_text(encoding="utf-8"))


def test_v04_schema_files_exist_and_match_exported_contract_metadata() -> None:
    assert CONTRACT_VERSION == "0.4"
    assert is_current_record_contract({"contract_version": "0.4"})
    assert not is_current_record_contract({"schema_version": "0.4"})
    assert validate_record_version("claim", {"record_version": 1}) == [
        "contract_version is required when record_version is set"
    ]
    assert validate_record_version("working_context", {"contract_version": "0.4"}) == [
        "working_context record_version is required"
    ]
    assert validate_record_version("working_context", {}) == []
    for name, exported in SCHEMA_EXPORTS.items():
        schema = load_schema(name)
        assert schema["$id"] == exported["$id"]
        assert schema["title"] == exported["title"]
        assert schema["required"] == exported["required"]
        assert schema["type"] == "object"
        if "contract_version" in schema["properties"]:
            assert schema["properties"]["contract_version"]["const"] == "0.4"


def test_grant_and_reason_contracts_reject_legacy_action_kind_shape() -> None:
    assert ACTION_KINDS == ("bash", "file-write", "mcp-write", "git", "final")

    grant_action_enum = load_schema("grant.record.schema.json")["properties"]["action_kind"]["enum"]
    reason_action_enum = load_schema("reason_step.request.schema.json")["properties"]["action_kind"]["enum"]

    assert grant_action_enum == list(ACTION_KINDS)
    assert reason_action_enum == list(ACTION_KINDS)
    assert "write" not in grant_action_enum
    assert "edit" not in grant_action_enum


def test_reason_ledger_contract_preserves_hash_seal_and_pow_fields() -> None:
    schema = load_schema("reason_ledger.entry.schema.json")
    required = set(schema["required"])

    assert {"prev_ledger_hash", "entry_hash", "ledger_hash", "seal", "pow"} <= required
    assert schema["properties"]["pow"]["properties"]["algorithm"]["const"] == "sha256-leading-zero-bits"

    entry = ReasonLedgerEntry(
        id="STEP-20260423-demo",
        entry_type="claim_step",
        created_at="2026-04-23T00:00:00+03:00",
        prev_ledger_hash="sha256:0",
        entry_hash="sha256:entry",
        ledger_hash="sha256:ledger",
        seal="hmac-sha256:seal",
        pow={
            "algorithm": "sha256-leading-zero-bits",
            "difficulty_bits": 12,
            "nonce": "abc:1",
            "digest": "000abc",
        },
        chain_hash="sha256:chain",
        signed_chain={"node_count": 1, "edge_count": 0},
        chain_payload={"nodes": [], "edges": []},
    ).to_payload()

    assert entry["contract_version"] == "0.4"
    assert entry["record_type"] == "reason"
    assert entry["version"] == 2
    assert entry["pow"]["algorithm"] == "sha256-leading-zero-bits"


def test_working_context_contract_is_agent_owned_and_signed() -> None:
    agent_schema = load_schema("agent_identity.record.schema.json")
    wctx_schema = load_schema("working_context.record.schema.json")

    assert agent_schema["properties"]["key_algorithm"]["const"] == "hmac-sha256"
    assert agent_schema["properties"]["record_version"]["const"] == 1
    assert agent_schema["properties"]["key_scope"]["const"] == "local-agent"

    required = set(wctx_schema["required"])
    assert {"record_version", "agent_identity_ref", "agent_key_fingerprint", "ownership_mode", "owner_signature"} <= required
    assert wctx_schema["properties"]["ownership_mode"]["const"] == "owner-only"
    assert wctx_schema["properties"]["handoff_policy"]["const"] == "fork-required"
    assert wctx_schema["properties"]["record_version"]["const"] == 1
    assert wctx_schema["properties"]["owner_signature"]["properties"]["algorithm"]["const"] == "hmac-sha256"
    assert "map_sessions" in wctx_schema["properties"]

    agent = AgentIdentityRecord(
        id="AGENT-20260423-demo",
        scope="agent.local",
        agent_name="pytest-agent",
        key_fingerprint="sha256:agent-key",
        created_at="2026-04-23T00:00:00+03:00",
    ).to_payload()
    assert agent["record_type"] == "agent_identity"
    assert agent["record_version"] == 1
    assert agent["key_fingerprint"] == "sha256:agent-key"

    context = WorkingContextRecord(
        id="WCTX-20260423-demo",
        title="Owned WCTX",
        scope="pytest",
        context_kind="investigation",
        agent_identity_ref="AGENT-20260423-demo",
        agent_key_fingerprint="sha256:agent-key",
        owner_signature={
            "algorithm": "hmac-sha256",
            "signed_payload_hash": "sha256:wctx-payload",
            "signature": "hmac-sha256:wctx-signature",
        },
        created_at="2026-04-23T00:00:00+03:00",
        updated_at="2026-04-23T00:00:00+03:00",
    ).to_payload()
    assert context["record_type"] == "working_context"
    assert context["record_version"] == 1
    assert context["ownership_mode"] == "owner-only"
    assert context["handoff_policy"] == "fork-required"
    assert context["agent_identity_ref"] == agent["id"]
    assert context["map_sessions"] == {}


def test_front_door_contract_payloads_expose_routes_without_proof() -> None:
    next_step = NextStepResponse(
        focus={
            "workspace_ref": "WSP-20260423-demo",
            "project_ref": "PRJ-20260423-demo",
            "task_ref": "TASK-20260423-demo",
            "wctx_ref": "WCTX-20260423-demo",
            "focus_source": "local-tep",
        },
        route_graph={
            "start": "lookup",
            "branches": [
                {
                    "id": "need_fact_support",
                    "condition": "answer needs proof",
                    "tool": "lookup",
                    "args_hint": {"kind": "facts"},
                }
            ],
        },
    ).to_payload()
    assert next_step["contract_version"] == "0.4"
    assert next_step["required_next"] == ["lookup"]

    lookup = LookupResponse(
        focus={"workspace_ref": "WSP-20260423-demo", "project_ref": "PRJ-20260423-demo"},
        route_token="ROUTE-demo",
        ranked_context=[{"ref": "MODEL-20260423-demo", "role": "integrated_picture"}],
        chain_candidates=[{"ref": "CLM-20260423-demo", "role": "fact", "quote": "supported fact"}],
        curiosity={"probe_suggestions": []},
        map_navigation={"map_navigation_is_proof": False, "cells": [{"ref": "MAP-20260423-demo", "map_is_proof": False}]},
        next_allowed_tools=("record_detail", "linked_records", "augment_chain"),
    ).to_payload()
    assert lookup["lookup_is_proof"] is False
    assert lookup["map_navigation"]["map_navigation_is_proof"] is False
    assert lookup["map_navigation"]["cells"][0]["map_is_proof"] is False
    assert lookup["route_token"] == "ROUTE-demo"
    assert lookup["next_allowed_tools"] == ["record_detail", "linked_records", "augment_chain"]


def test_map_contract_payload_is_navigation_only_and_session_based() -> None:
    view = MapViewResponse(
        map_session_ref="WCTX-20260423-demo#map-session",
        zone={"id": "MZONE-topology-demo", "kind": "topology", "summary": "Runtime grants"},
        anchor_facts=[{"ref": "MODEL-20260423-demo"}],
        ignored_but_relevant=[{"ref": "CLM-20260423-cold"}],
        bridge_facts=[{"ref": "CLM-20260423-bridge"}],
        tension_facts=[{"ref": "CLM-20260423-runtime", "status": "runtime"}],
        signals={
            "tap_smell": [{"ref": "CLM-20260423-hot", "score": 0.7}],
            "neglect_pressure": [{"ref": "CLM-20260423-cold", "score": 0.5}],
            "inquiry_pressure": [{"ref": "CLM-20260423-hypothesis-cloud", "score": 0.4}],
            "promotion_pressure": [],
        },
        allowed_moves=[{"move": "inspect_bridge", "target": "CLM-20260423-bridge"}],
        proof_routes=[{"tool": "lookup", "args_hint": {"query": "Runtime grants"}}],
    ).to_payload()

    assert view["map_is_proof"] is False
    assert view["map_session_ref"].startswith("WCTX-")
    assert view["signals"]["tap_smell"]
    assert view["signals"]["inquiry_pressure"]
    assert view["proof_routes"][0]["tool"] == "lookup"


def test_map_record_contract_is_versioned_and_navigation_only() -> None:
    schema = load_schema("map.record.schema.json")
    required = set(schema["required"])

    assert {"contract_version", "record_version", "map_is_proof", "proof_routes"} <= required
    assert schema["properties"]["contract_version"]["const"] == "0.4"
    assert schema["properties"]["record_version"]["const"] == 1
    assert schema["properties"]["map_is_proof"]["const"] is False

    record = MapRecord(
        id="MAP-20260423-demo",
        scope="pytest",
        level="L1",
        map_kind="evidence_patch",
        summary="Evidence around MAP record contract validation.",
        source_set_fingerprint="sha256:map-contract",
        generated_by="map_refresh",
        generated_at="2026-04-23T00:00:00+03:00",
        updated_at="2026-04-23T00:00:00+03:00",
        stale_policy="source_set_changed",
        scope_refs={"workspace_refs": ["WSP-20260423-demo"], "project_refs": [], "task_refs": [], "wctx_refs": []},
        anchor_refs=("CLM-20260423-demo",),
        proof_routes=(
            {
                "route_kind": "claim_support",
                "route_refs": ["CLM-20260423-demo", "SRC-20260423-demo"],
                "required_drilldown": True,
            },
        ),
        signals={"tap_smell": {"score": 0.0, "half_life_days": 7.0}},
    ).to_payload()

    assert record["record_type"] == "map"
    assert record["contract_version"] == "0.4"
    assert record["record_version"] == 1
    assert record["map_is_proof"] is False
    assert record["level"] == "L1"
    assert record["proof_routes"][0]["required_drilldown"] is True


def test_mutating_contract_payloads_keep_runtime_authorization_boundaries() -> None:
    evidence = RecordEvidenceRequest(
        kind="command-output",
        quote="1 passed",
        command="uv run pytest tests/trust_evidence_protocol/test_contracts_v04.py -q",
        claim_text="The 0.4 contract tests passed.",
    ).to_payload()
    assert evidence["kind"] == "command-output"
    assert evidence["quote"] == "1 passed"

    reason = ReasonStepRequest(
        task_ref="TASK-20260423-demo",
        mode="edit",
        claim_ref="CLM-20260423-demo",
        intent="Prepare Milestone 1 contracts",
        action_kind="file-write",
    ).to_payload()
    assert reason["action_kind"] == "file-write"

    grant = GrantRecord(
        id="GRANT-20260423-demo",
        reason_ref="STEP-20260423-demo",
        workspace_ref="WSP-20260423-demo",
        task_ref="TASK-20260423-demo",
        mode="edit",
        action_kind="file-write",
        cwd=str(REPO_ROOT),
        valid_from="2026-04-23T00:00:00+03:00",
        valid_until="2026-04-23T00:05:00+03:00",
        context_fingerprint="sha256:demo",
        project_ref="PRJ-20260423-demo",
    ).to_payload()
    assert grant["action_kind"] == "file-write"
    assert "used" not in grant

    run = RunRecord(
        id="RUN-20260423-demo",
        workspace_ref="WSP-20260423-demo",
        cwd=str(REPO_ROOT),
        command="git diff --check",
        command_hash="sha256:demo",
        started_at="2026-04-23T00:00:00+03:00",
        finished_at="2026-04-23T00:00:01+03:00",
        exit_code=0,
        output_quotes=("no whitespace errors",),
        grant_ref="GRANT-20260423-demo",
    ).to_payload()
    assert run["grant_ref"] == "GRANT-20260423-demo"
    assert run["output_quotes"] == ["no whitespace errors"]


def test_chain_and_migration_contracts_capture_repair_and_legacy_decisions() -> None:
    chain = ChainValidationResponse(
        valid=False,
        proof_allowed=False,
        gaps=[{"reason": "missing runtime RUN provenance"}],
        repair=[{"tool": "record_evidence", "why": "capture command output as RUN-backed support"}],
    ).to_payload()
    assert chain["contract_version"] == "0.4"
    assert chain["valid"] is False
    assert chain["repair"][0]["tool"] == "record_evidence"

    migration = MigrationReport(
        mode="dry-run",
        source="/legacy/.codex_context",
        target="~/.tep_context",
        planned_actions=[{"action": "create_migration_input", "input_kind": "migration_batch"}],
        created_refs=("INP-20260423-demo",),
        preserved_refs=("CLM-20260423-demo",),
        revoked_grants=("GRANT-20260422-legacy",),
    ).to_payload()
    assert migration["mode"] == "dry-run"
    assert migration["created_refs"] == ["INP-20260423-demo"]
    assert migration["revoked_grants"] == ["GRANT-20260422-legacy"]
    assert migration["applied"] is False
