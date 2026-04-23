from __future__ import annotations

import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
PLUGIN_ROOT = REPO_ROOT / "plugins" / "trust-evidence-protocol"

plugin_root = str(PLUGIN_ROOT)
if plugin_root not in sys.path:
    sys.path.insert(0, plugin_root)

from tep_runtime.migrations import build_migration_dry_run_report, build_schema_migration_report  # noqa: E402
from tep_runtime.schema_migrations import registered_schema_migrations  # noqa: E402


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def test_migration_dry_run_reports_preserved_refs_and_revoked_grants(tmp_path: Path) -> None:
    source = tmp_path / ".codex_context"
    target = tmp_path / ".tep_context"
    write_json(
        source / "records" / "claim" / "CLM-20260423-demo.json",
        {"id": "CLM-20260423-demo", "record_type": "claim"},
    )
    write_json(
        source / "records" / "source" / "SRC-20260423-demo.json",
        {"id": "SRC-20260423-demo", "record_type": "source"},
    )
    ledger = source / "runtime" / "reasoning" / "reasons.jsonl"
    ledger.parent.mkdir(parents=True, exist_ok=True)
    ledger.write_text(
        json.dumps({"id": "GRANT-20260423-demo", "entry_type": "grant"}) + "\n",
        encoding="utf-8",
    )

    report = build_migration_dry_run_report(source, target).to_payload()

    assert report["contract_version"] == "0.4"
    assert report["mode"] == "dry-run"
    assert report["applied"] is False
    assert report["preserved_refs"] == ["CLM-20260423-demo", "SRC-20260423-demo"]
    assert report["revoked_grants"] == ["GRANT-20260423-demo"]
    assert report["created_refs"] == []
    assert {
        "action": "create_migration_input",
        "input_kind": "migration_batch",
        "origin": {
            "kind": "legacy_context",
            "ref": "records/claim/CLM-20260423-demo.json",
        },
    } in report["planned_actions"]

    assert not target.exists()


def test_migration_dry_run_reports_invalid_legacy_records_without_writing(tmp_path: Path) -> None:
    source = tmp_path / ".codex_context"
    target = tmp_path / ".tep_context"
    bad_record = source / "records" / "claim" / "bad.json"
    bad_record.parent.mkdir(parents=True, exist_ok=True)
    bad_record.write_text("[1, 2, 3]\n", encoding="utf-8")

    ledger = source / "runtime" / "reasoning" / "reasons.jsonl"
    ledger.parent.mkdir(parents=True, exist_ok=True)
    ledger.write_text("{not-json}\n", encoding="utf-8")

    report = build_migration_dry_run_report(source, target).to_payload()

    reasons = {item["reason"] for item in report["unresolved"]}
    assert "invalid_json_record" in reasons
    assert "invalid_reason_ledger_json" in reasons
    assert report["preserved_refs"] == []
    assert report["applied"] is False
    assert not target.exists()


def map_payload(**overrides: object) -> dict:
    payload: dict = {
        "id": "MAP-20260423-demo",
        "record_type": "map",
        "schema_version": "0.4",
        "scope": "pytest.map",
        "note": "Legacy map record requiring schema migration.",
        "level": "L1",
        "map_kind": "evidence_patch",
        "status": "active",
        "summary": "Legacy MAP shape.",
        "scope_refs": {"workspace_refs": [], "project_refs": [], "task_refs": [], "wctx_refs": []},
        "anchor_refs": ["CLM-20260423-demo"],
        "derived_from_refs": [],
        "source_set_fingerprint": "sha256:legacy-map",
        "up_refs": [],
        "down_refs": [],
        "adjacent_map_refs": [],
        "contradicts_map_refs": [],
        "refines_map_refs": [],
        "supersedes_refs": [],
        "tension_refs": [],
        "unknown_links": [],
        "proof_routes": [
            {
                "route_kind": "claim_support",
                "route_refs": ["CLM-20260423-demo", "SRC-20260423-demo"],
                "required_drilldown": True,
            }
        ],
        "signals": {},
        "map_is_proof": False,
        "generated_by": "map_refresh",
        "generated_at": "2026-04-23T00:00:00+03:00",
        "updated_at": "2026-04-23T00:00:00+03:00",
        "stale_policy": "source_set_changed",
    }
    payload.update(overrides)
    return payload


def agent_payload(**overrides: object) -> dict:
    payload: dict = {
        "id": "AGENT-20260423-demo",
        "record_type": "agent_identity",
        "contract_version": "0.4",
        "scope": "agent.local",
        "agent_name": "pytest-agent",
        "key_algorithm": "hmac-sha256",
        "key_fingerprint": "sha256:agent-key",
        "key_scope": "local-agent",
        "status": "active",
        "created_at": "2026-04-23T00:00:00+03:00",
    }
    payload.update(overrides)
    return payload


def wctx_payload(**overrides: object) -> dict:
    payload: dict = {
        "id": "WCTX-20260423-demo",
        "record_type": "working_context",
        "contract_version": "0.4",
        "scope": "pytest.wctx",
        "title": "Legacy WCTX shape",
        "status": "active",
        "context_kind": "investigation",
        "agent_identity_ref": "AGENT-20260423-demo",
        "agent_key_fingerprint": "sha256:agent-key",
        "ownership_mode": "owner-only",
        "handoff_policy": "fork-required",
        "owner_signature": {
            "algorithm": "hmac-sha256",
            "signed_payload_hash": "sha256:wctx",
            "signature": "hmac-sha256:signature",
        },
        "created_at": "2026-04-23T00:00:00+03:00",
        "updated_at": "2026-04-23T00:00:00+03:00",
    }
    payload.update(overrides)
    return payload


def test_schema_migration_plan_is_read_only_and_each_change_has_module(tmp_path: Path) -> None:
    context = tmp_path / ".tep_context"
    map_file = context / "records" / "map" / "MAP-20260423-demo.json"
    write_json(map_file, map_payload())

    migrations = registered_schema_migrations()
    assert [migration.id for migration in migrations] == [
        "20260423_agent_identity_v1",
        "20260423_working_context_v1",
        "20260423_map_record_v1",
    ]
    assert migrations[0].__class__.__module__.endswith(".agent_identity_v1")
    assert migrations[1].__class__.__module__.endswith(".working_context_v1")
    assert migrations[2].__class__.__module__.endswith(".map_record_v1")

    report = build_schema_migration_report(context).to_payload()

    assert report["mode"] == "dry-run"
    assert report["applied"] is False
    assert report["unresolved"] == []
    assert report["preserved_refs"] == ["MAP-20260423-demo"]
    assert report["planned_actions"][0]["migration_id"] == "20260423_map_record_v1"
    stored = json.loads(map_file.read_text(encoding="utf-8"))
    assert stored["schema_version"] == "0.4"
    assert "record_version" not in stored


def test_schema_migration_versions_agent_identity_and_wctx_records(tmp_path: Path) -> None:
    context = tmp_path / ".tep_context"
    agent_file = context / "records" / "agent_identity" / "AGENT-20260423-demo.json"
    wctx_file = context / "records" / "working_context" / "WCTX-20260423-demo.json"
    write_json(agent_file, agent_payload())
    write_json(wctx_file, wctx_payload())

    report = build_schema_migration_report(context, apply=True).to_payload()

    assert report["applied"] is True
    assert report["unresolved"] == []
    assert report["preserved_refs"] == ["AGENT-20260423-demo", "WCTX-20260423-demo"]
    agent = json.loads(agent_file.read_text(encoding="utf-8"))
    wctx = json.loads(wctx_file.read_text(encoding="utf-8"))
    assert agent["record_version"] == 1
    assert agent["note"]
    assert wctx["record_version"] == 1
    assert wctx["note"]


def test_schema_migration_refuses_unsafe_identity_and_wctx_policy_changes(tmp_path: Path) -> None:
    context = tmp_path / ".tep_context"
    agent_file = context / "records" / "agent_identity" / "AGENT-20260423-demo.json"
    wctx_file = context / "records" / "working_context" / "WCTX-20260423-demo.json"
    write_json(agent_file, agent_payload(key_algorithm="ed25519"))
    write_json(wctx_file, wctx_payload(ownership_mode="shared"))

    report = build_schema_migration_report(context, apply=True).to_payload()

    reasons = {item["reason"] for item in report["unresolved"]}
    assert "unsupported_agent_key_algorithm" in reasons
    assert "unsupported_wctx_ownership_mode" in reasons
    assert report["applied"] is False
    assert "record_version" not in json.loads(agent_file.read_text(encoding="utf-8"))
    assert "record_version" not in json.loads(wctx_file.read_text(encoding="utf-8"))


def test_schema_migration_reports_unknown_selected_migration(tmp_path: Path) -> None:
    context = tmp_path / ".tep_context"
    (context / "records").mkdir(parents=True)

    report = build_schema_migration_report(context, migration_ids=["missing-migration"]).to_payload()

    assert report["planned_actions"] == []
    assert report["applied"] is False
    assert report["unresolved"] == [
        {"path": "", "reason": "unknown_schema_migration", "migration_id": "missing-migration"}
    ]


def test_schema_migration_apply_rewrites_only_after_validation(tmp_path: Path) -> None:
    context = tmp_path / ".tep_context"
    map_file = context / "records" / "map" / "MAP-20260423-demo.json"
    write_json(map_file, map_payload())

    report = build_schema_migration_report(context, apply=True).to_payload()

    assert report["mode"] == "apply"
    assert report["applied"] is True
    assert report["unresolved"] == []
    stored = json.loads(map_file.read_text(encoding="utf-8"))
    assert stored["contract_version"] == "0.4"
    assert stored["record_version"] == 1
    assert "schema_version" not in stored


def test_schema_migration_apply_refuses_unvalidated_partial_writes(tmp_path: Path) -> None:
    context = tmp_path / ".tep_context"
    map_file = context / "records" / "map" / "MAP-20260423-demo.json"
    write_json(map_file, map_payload(map_is_proof=True))

    report = build_schema_migration_report(context, apply=True).to_payload()

    reasons = {item["reason"] for item in report["unresolved"]}
    assert "map_record_claims_proof" in reasons
    assert "post_migration_validation_failed" in reasons
    assert report["applied"] is False
    stored = json.loads(map_file.read_text(encoding="utf-8"))
    assert stored["schema_version"] == "0.4"
    assert "record_version" not in stored
