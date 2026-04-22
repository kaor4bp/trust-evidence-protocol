from __future__ import annotations

import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
PLUGIN_ROOT = REPO_ROOT / "plugins" / "trust-evidence-protocol"

plugin_root = str(PLUGIN_ROOT)
if plugin_root not in sys.path:
    sys.path.insert(0, plugin_root)

from tep_runtime.core_validators import validate_core_graph  # noqa: E402
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


def run() -> dict:
    return record(
        "run",
        "RUN-20260423-a0000003",
        contract_version="0.4",
        status="completed",
        tool="bash",
        command="pytest",
        captured_at=TS,
        exit_code=0,
        artifact_refs=[],
        workspace_refs=[WORKSPACE_REF],
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
