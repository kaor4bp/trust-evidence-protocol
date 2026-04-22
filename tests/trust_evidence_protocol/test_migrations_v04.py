from __future__ import annotations

import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
PLUGIN_ROOT = REPO_ROOT / "plugins" / "trust-evidence-protocol"

plugin_root = str(PLUGIN_ROOT)
if plugin_root not in sys.path:
    sys.path.insert(0, plugin_root)

from tep_runtime.migrations import build_migration_dry_run_report  # noqa: E402


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
