from __future__ import annotations

import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
PLUGIN_ROOT = REPO_ROOT / "plugins" / "trust-evidence-protocol"

plugin_root = str(PLUGIN_ROOT)
if plugin_root not in sys.path:
    sys.path.insert(0, plugin_root)

from tep_runtime.core_validators import validate_active_focus, validate_core_graph  # noqa: E402
from tep_runtime.agent_identity import agent_identity_scope, sign_working_context_payload  # noqa: E402
from tep_runtime.reason_ledger import (  # noqa: E402
    append_reason_entry,
    command_hash,
    current_reasons_ledger_path,
    normalize_cwd,
    validate_grant_run_lifecycle,
    validate_reason_ledger,
)
from tep_runtime.state_validation import validate_records_state  # noqa: E402


TS = "2026-04-23T00:00:00+03:00"
WORKSPACE_REF = "WSP-20260423-a0000001"


def record(record_type: str, record_id: str, **payload) -> dict:
    data = {
        "id": record_id,
        "record_type": record_type,
        "scope": "pytest.v04",
        "note": "pytest v04 validator fixture",
        "_folder": record_type,
        "_path": Path(f"/tmp/tep/{record_type}/{record_id}.json"),
        **payload,
    }
    return data


def workspace() -> dict:
    return record(
        "workspace",
        WORKSPACE_REF,
        workspace_key="pytest",
        title="Pytest Workspace",
        status="active",
        context_root="/tmp/tep",
        root_refs=["/tmp/tep"],
        created_at=TS,
        updated_at=TS,
    )


def project(project_id: str, **payload) -> dict:
    values = {
        "project_key": "pytest-project",
        "title": "Pytest Project",
        "status": "active",
        "root_refs": ["/tmp/tep/project"],
        "created_at": TS,
        "updated_at": TS,
        "workspace_refs": [WORKSPACE_REF],
        **payload,
    }
    return record(
        "project",
        project_id,
        **values,
    )


def task(task_id: str, **payload) -> dict:
    values = {
        "title": "Pytest Task",
        "status": "active",
        "created_at": TS,
        "updated_at": TS,
        "project_refs": ["PRJ-20260423-a0000011"],
        **payload,
    }
    return record(
        "task",
        task_id,
        **values,
    )


def agent(fingerprint: str = "sha256:agent") -> dict:
    return record(
        "agent_identity",
        "AGENT-20260423-a0000002",
        contract_version="0.4",
        agent_name="pytest-agent",
        key_algorithm="hmac-sha256",
        key_fingerprint=fingerprint,
        key_scope="local-agent",
        status="active",
        created_at=TS,
    )


def run(**payload) -> dict:
    values = {
        "contract_version": "0.4",
        "status": "completed",
        "tool": "bash",
        "command": "pytest",
        "captured_at": TS,
        "exit_code": 0,
        "artifact_refs": [],
        "workspace_refs": [WORKSPACE_REF],
        **payload,
    }
    return record(
        "run",
        "RUN-20260423-a0000003",
        **values,
    )


def source(source_id: str, **payload) -> dict:
    return record(
        "source",
        source_id,
        contract_version="0.4",
        source_kind="runtime",
        critique_status="accepted",
        captured_at=TS,
        independence_group="pytest",
        origin={"kind": "command", "ref": "pytest"},
        quote="runtime observation",
        workspace_refs=[WORKSPACE_REF],
        **payload,
    )


def theory_source(source_id: str) -> dict:
    return record(
        "source",
        source_id,
        contract_version="0.4",
        source_kind="theory",
        critique_status="accepted",
        captured_at=TS,
        independence_group="pytest",
        origin={"kind": "user", "ref": "pytest"},
        quote="theory observation",
        input_refs=["INP-20260423-a0000009"],
        workspace_refs=[WORKSPACE_REF],
    )


def claim(claim_id: str, **payload) -> dict:
    values = {
        "contract_version": "0.4",
        "plane": "runtime",
        "status": "supported",
        "statement": "Runtime claim",
        "recorded_at": TS,
        "workspace_refs": [WORKSPACE_REF],
        **payload,
    }
    return record("claim", claim_id, **values)


def base_records(*items: dict) -> dict[str, dict]:
    records = {WORKSPACE_REF: workspace()}
    for item in items:
        records[item["id"]] = item
    return records


def messages(errors) -> list[str]:
    return [error.message for error in errors]


def test_v04_core_validator_requires_source_provenance_and_runtime_run_link() -> None:
    bad_source = source("SRC-20260423-a0000004")
    bad_claim = claim("CLM-20260423-a0000005", source_refs=[bad_source["id"]])
    records = base_records(bad_source, bad_claim)

    errors = messages(validate_core_graph(Path("/tmp/tep"), records))

    assert "0.4 source requires INP/FILE/RUN/ART provenance" in errors
    assert "0.4 runtime claim requires source transitively linked to RUN-*" in errors

    good_run = run()
    good_source = source("SRC-20260423-a0000006", run_refs=[good_run["id"]])
    good_claim = claim("CLM-20260423-a0000007", source_refs=[good_source["id"]])
    records = base_records(good_run, good_source, good_claim)

    assert messages(validate_core_graph(Path("/tmp/tep"), records)) == []


def test_v04_core_validator_enforces_agent_owned_wctx() -> None:
    owner = agent()
    context = record(
        "working_context",
        "WCTX-20260423-a0000008",
        contract_version="0.4",
        title="Owned focus",
        status="active",
        context_kind="investigation",
        agent_identity_ref=owner["id"],
        agent_key_fingerprint="sha256:other",
        ownership_mode="shared",
        handoff_policy="reuse",
        owner_signature={"algorithm": "none", "signed_payload_hash": "bad", "signature": "bad"},
        created_at=TS,
        updated_at=TS,
        workspace_refs=[WORKSPACE_REF],
    )
    records = base_records(owner, context)

    errors = messages(validate_core_graph(Path("/tmp/tep"), records))

    assert "WCTX agent_key_fingerprint must match agent_identity key_fingerprint" in errors
    assert "0.4 WCTX ownership_mode must be owner-only" in errors
    assert "0.4 WCTX handoff_policy must be fork-required" in errors
    assert "WCTX owner_signature.algorithm must be hmac-sha256" in errors


def test_v04_core_validator_detects_tampered_local_wctx_signature(tmp_path: Path) -> None:
    root = tmp_path / ".tep_context"
    context = record(
        "working_context",
        "WCTX-20260423-a0000008",
        contract_version="0.4",
        title="Owned focus",
        status="active",
        context_kind="investigation",
        pinned_refs=[],
        focus_paths=[],
        topic_terms=[],
        topic_seed_refs=[],
        assumptions=[],
        concerns=[],
        parent_context_ref="",
        supersedes_refs=[],
        project_refs=[],
        task_refs=[],
        tags=[],
        created_at=TS,
        updated_at=TS,
        workspace_refs=[WORKSPACE_REF],
    )
    with agent_identity_scope("validator-agent-token"):
        signed, owner = sign_working_context_payload(root, {}, context, timestamp=TS)
    records = base_records(owner, signed)
    assert messages(validate_core_graph(root, records)) == []

    tampered = dict(signed)
    tampered["title"] = "Tampered focus"
    with agent_identity_scope("validator-agent-token"):
        errors = messages(validate_core_graph(root, base_records(owner, tampered)))

    assert "WCTX owner_signature.signed_payload_hash mismatch" in errors
    assert "WCTX owner_signature.signature mismatch" in errors


def test_v04_model_authority_rejects_runtime_or_tentative_support() -> None:
    runtime_run = run()
    runtime_source = source("SRC-20260423-a0000006", run_refs=[runtime_run["id"]])
    runtime_claim = claim("CLM-20260423-a0000007", source_refs=[runtime_source["id"]])
    tentative_source = theory_source("SRC-20260423-a0000008")
    tentative_claim = claim(
        "CLM-20260423-a0000009",
        plane="theory",
        status="tentative",
        statement="Tentative theory claim",
        source_refs=[tentative_source["id"]],
    )
    model = record(
        "model",
        "MODEL-20260423-a0000010",
        contract_version="0.4",
        knowledge_class="domain",
        status="working",
        domain="pytest",
        aspect="authority",
        summary="Invalid model authority",
        updated_at=TS,
        is_primary=True,
        claim_refs=[runtime_claim["id"], tentative_claim["id"]],
        workspace_refs=[WORKSPACE_REF],
    )
    records = base_records(runtime_run, runtime_source, runtime_claim, tentative_source, tentative_claim, model)

    errors = messages(validate_core_graph(Path("/tmp/tep"), records))

    assert f"0.4 MODEL requires supported theory claim_refs: {runtime_claim['id']}, {tentative_claim['id']}" in errors


def test_v04_core_validators_are_part_of_state_validation(tmp_path: Path) -> None:
    bad_source = source("SRC-20260423-a0000004")
    bad_claim = claim("CLM-20260423-a0000005", source_refs=[bad_source["id"]])
    records = base_records(bad_source, bad_claim)

    errors = messages(validate_records_state(tmp_path, records))

    assert "0.4 source requires INP/FILE/RUN/ART provenance" in errors
    assert "0.4 runtime claim requires source transitively linked to RUN-*" in errors


def test_v04_active_focus_requires_active_compatible_records(tmp_path: Path) -> None:
    project_id = "PRJ-20260423-a0000011"
    task_id = "TASK-20260423-a0000012"
    settings = {
        "current_workspace_ref": WORKSPACE_REF,
        "current_project_ref": project_id,
        "current_task_ref": task_id,
    }
    (tmp_path / "settings.json").write_text(json.dumps(settings), encoding="utf-8")
    current_workspace = workspace()
    current_workspace["contract_version"] = "0.4"
    current_workspace["project_refs"] = []
    records = base_records(
        project(project_id, contract_version="0.4", workspace_refs=[]),
        task(task_id, status="completed", project_refs=["PRJ-20260423-other"]),
    )
    records[WORKSPACE_REF] = current_workspace

    errors = messages(validate_active_focus(tmp_path, records))

    assert f"current_task_ref must reference an open task record: {task_id}" in errors
    assert "current_project_ref must belong to current_workspace_ref" in errors
    assert "current_task_ref must belong to current_project_ref" in errors


def test_reason_ledger_state_validation_is_read_only_when_empty(tmp_path: Path) -> None:
    assert messages(validate_records_state(tmp_path, {})) == []
    assert not (tmp_path / "runtime" / "reasoning" / "agents").exists()


def test_reason_ledger_write_path_creates_per_agent_files(tmp_path: Path) -> None:
    (tmp_path / "settings.json").write_text(
        json.dumps({"reasoning": {"pow": {"enabled": False}}}),
        encoding="utf-8",
    )
    with agent_identity_scope("ledger-agent-token"):
        validation = validate_reason_ledger(tmp_path, create_secret=True)

    assert validation["ok"]
    with agent_identity_scope("ledger-agent-token"):
        ledger = current_reasons_ledger_path(tmp_path)
    assert ledger is not None
    assert ledger.exists()
    assert ledger.parent.name.startswith("AGENT-")
    assert (ledger.parent / "seal.json").exists()
    assert not (tmp_path / "runtime" / "reasoning" / "reasons.jsonl").exists()


def test_reason_ledger_state_validation_detects_tamper(tmp_path: Path) -> None:
    (tmp_path / "settings.json").write_text(
        json.dumps({"reasoning": {"pow": {"enabled": False}}}),
        encoding="utf-8",
    )
    with agent_identity_scope("ledger-tamper-agent-token"):
        entry, error = append_reason_entry(
            tmp_path,
            {
                "version": 3,
                "entry_type": "claim_step",
                "status": "reviewed",
                "workspace_ref": WORKSPACE_REF,
                "project_ref": "PRJ-20260423-a0000011",
                "task_ref": "TASK-20260423-a0000012",
                "wctx_ref": "WCTX-20260423-a0000014",
                "claim_ref": "CLM-20260423-a0000015",
                "prev_claim_ref": "",
                "relation_claim_ref": "",
                "prev_step_ref": "",
                "mode": "edit",
                "justification_valid": True,
                "decision_chain_valid": True,
                "decision_valid": True,
                "valid_for": ["edit"],
                "claim_step_hash": "pytest-step-hash",
            },
        )
    assert entry is not None, error
    assert entry["agent_identity_ref"].startswith("AGENT-")
    assert entry["agent_key_fingerprint"].startswith("sha256:")
    assert not (tmp_path / "runtime" / "reasoning" / "reasons.jsonl").exists()
    assert messages(validate_records_state(tmp_path, {})) == []

    with agent_identity_scope("ledger-tamper-agent-token"):
        ledger = current_reasons_ledger_path(tmp_path)
    assert ledger is not None
    ledger.write_text(
        ledger.read_text(encoding="utf-8").replace("pytest-step-hash", "tampered-step-hash", 1),
        encoding="utf-8",
    )

    errors = messages(validate_records_state(tmp_path, {}))

    assert any("ledger appears tampered" in error for error in errors)


def write_pow_disabled_settings(root: Path) -> None:
    (root / "settings.json").write_text(
        json.dumps({"reasoning": {"pow": {"enabled": False}}}),
        encoding="utf-8",
    )


def grant_for_run(root: Path, *, command: str = "echo hi", max_runs: int = 1) -> dict:
    write_pow_disabled_settings(root)
    with agent_identity_scope("grant-run-agent-token"):
        grant, error = append_reason_entry(
            root,
            {
                "entry_type": "grant",
                "status": "active",
                "grant_type": "exact_command",
                "reason_ref": "STEP-20260423-a0000013",
                "workspace_ref": WORKSPACE_REF,
                "project_ref": "PRJ-20260423-a0000011",
                "task_ref": "TASK-20260423-a0000012",
                "mode": "edit",
                "action_kind": "write",
                "command": command,
                "command_sha256": command_hash(command),
                "cwd": normalize_cwd(root),
                "tool": "bash",
                "max_runs": max_runs,
                "valid_from": "2026-04-23T00:00:00+03:00",
                "expires_at": "2026-04-24T00:00:00+03:00",
                "context_fingerprint": "pytest",
            },
            id_prefix="GRANT",
        )
    assert grant is not None, error
    return grant


def grant_records(*run_records: dict) -> dict[str, dict]:
    project_id = "PRJ-20260423-a0000011"
    task_id = "TASK-20260423-a0000012"
    return base_records(
        project(project_id),
        task(task_id, project_refs=[project_id]),
        *run_records,
    )


def test_grant_run_lifecycle_accepts_matching_command_bound_run(tmp_path: Path) -> None:
    grant = grant_for_run(tmp_path)
    run_record = run(
        command="echo hi",
        cwd=str(tmp_path),
        captured_at=TS,
        action_kind="write",
        grant_ref=grant["id"],
        project_refs=["PRJ-20260423-a0000011"],
        task_refs=["TASK-20260423-a0000012"],
    )

    assert messages(validate_grant_run_lifecycle(tmp_path, grant_records(run_record))) == []
    assert messages(validate_records_state(tmp_path, grant_records(run_record))) == []


def test_grant_run_lifecycle_rejects_command_mismatch_and_double_use(tmp_path: Path) -> None:
    grant = grant_for_run(tmp_path)
    bad_run = run(
        command="echo bye",
        cwd=str(tmp_path),
        captured_at=TS,
        action_kind="write",
        grant_ref=grant["id"],
        project_refs=["PRJ-20260423-a0000011"],
        task_refs=["TASK-20260423-a0000012"],
    )

    errors = messages(validate_grant_run_lifecycle(tmp_path, grant_records(bad_run)))

    assert f"grant_ref {grant['id']} command hash mismatch" in errors

    second_run = dict(bad_run)
    second_run["id"] = "RUN-20260423-a0000014"
    second_run["_path"] = Path(f"/tmp/tep/run/{second_run['id']}.json")
    second_run["command"] = "echo hi"
    bad_run["command"] = "echo hi"

    errors = messages(validate_grant_run_lifecycle(tmp_path, grant_records(bad_run, second_run)))

    assert f"grant_ref {grant['id']} consumed 2 times; max_runs=1" in errors
