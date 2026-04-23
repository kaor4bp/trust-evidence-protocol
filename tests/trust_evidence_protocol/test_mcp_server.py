from __future__ import annotations

import json
import importlib.util
import re
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
PLUGIN_ROOT = REPO_ROOT / "plugins" / "trust-evidence-protocol"
BOOTSTRAP = PLUGIN_ROOT / "scripts" / "bootstrap_codex_context.py"
CLI = PLUGIN_ROOT / "scripts" / "context_cli.py"
MCP_SERVER = PLUGIN_ROOT / "mcp" / "tep_server.py"


def run_cli(context: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        [sys.executable, str(CLI), "--context", str(context), *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if check and result.returncode != 0:
        raise AssertionError(
            f"command failed: {args}\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
    return result


def bootstrap_context(tmp_path: Path) -> Path:
    context = tmp_path / ".codex_context"
    result = subprocess.run(
        [sys.executable, str(BOOTSTRAP), str(context)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise AssertionError(f"bootstrap failed\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}")
    return context


def recorded_id(result: subprocess.CompletedProcess[str], record_type: str) -> str:
    match = re.search(rf"(?:Recorded {record_type}|Started {record_type}) ([A-Z]+-\d{{8}}-[0-9a-f]{{8}})", result.stdout)
    assert match, result.stdout
    return match.group(1)


def run_mcp(messages: list[dict], cwd: Path = REPO_ROOT) -> list[dict]:
    payload = "\n".join(json.dumps(message) for message in messages) + "\n"
    result = subprocess.run(
        [sys.executable, str(MCP_SERVER)],
        cwd=cwd,
        input=payload,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise AssertionError(f"mcp server failed\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}")
    return [json.loads(line) for line in result.stdout.splitlines() if line.strip()]


def only_record_id(context: Path, record_type: str) -> str:
    records = sorted((context / "records" / record_type).glob("*.json"))
    assert len(records) == 1
    return records[0].stem


def load_record(context: Path, record_type: str, record_id: str) -> dict:
    return json.loads((context / "records" / record_type / f"{record_id}.json").read_text(encoding="utf-8"))


def load_mcp_server_module():
    spec = importlib.util.spec_from_file_location("tep_mcp_server_under_test", MCP_SERVER)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_mcp_manifest_declares_readonly_server() -> None:
    plugin_manifest = json.loads((PLUGIN_ROOT / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8"))
    assert plugin_manifest["mcpServers"] == "./.mcp.json"
    assert plugin_manifest["version"] == "0.4.0"

    claude_manifest = json.loads((PLUGIN_ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
    assert claude_manifest["version"] == plugin_manifest["version"]

    manifest = json.loads((PLUGIN_ROOT / ".mcp.json").read_text(encoding="utf-8"))
    server = manifest["mcpServers"]["trust-evidence-protocol"]
    assert server["command"] == "python3"
    assert server["args"] == ["mcp/tep_server.py"]
    assert MCP_SERVER.exists()

    module = load_mcp_server_module()
    assert module.SERVER_VERSION == plugin_manifest["version"]


def test_mcp_migration_dry_run_uses_service_without_writing_target(tmp_path: Path) -> None:
    source = tmp_path / ".codex_context"
    target = tmp_path / ".tep_context"
    claim = source / "records" / "claim" / "CLM-20260423-demo.json"
    claim.parent.mkdir(parents=True, exist_ok=True)
    claim.write_text(
        json.dumps({"id": "CLM-20260423-demo", "record_type": "claim"}) + "\n",
        encoding="utf-8",
    )
    ledger = source / "runtime" / "reasoning" / "reasons.jsonl"
    ledger.parent.mkdir(parents=True, exist_ok=True)
    ledger.write_text(
        json.dumps({"id": "GRANT-20260423-demo", "entry_type": "grant"}) + "\n",
        encoding="utf-8",
    )

    responses = run_mcp(
        [
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "pytest"}},
            },
            {"jsonrpc": "2.0", "method": "notifications/initialized"},
            {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
            {
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {
                    "name": "migration_dry_run",
                    "arguments": {
                        "source": str(source),
                        "target": str(target),
                        "format": "json",
                    },
                },
            },
        ]
    )

    tools = {tool["name"]: tool for tool in responses[1]["result"]["tools"]}
    assert "migration_dry_run" in tools
    assert "Read-only" in tools["migration_dry_run"]["description"]

    call_result = responses[2]["result"]
    assert call_result["isError"] is False
    payload = json.loads(call_result["content"][0]["text"])
    assert payload["contract_version"] == "0.4"
    assert payload["mode"] == "dry-run"
    assert payload["preserved_refs"] == ["CLM-20260423-demo"]
    assert payload["revoked_grants"] == ["GRANT-20260423-demo"]
    assert payload["applied"] is False
    assert not target.exists()


def test_mcp_schema_migration_plan_and_apply_use_service(tmp_path: Path) -> None:
    context = tmp_path / ".tep_context"
    map_file = context / "records" / "map" / "MAP-20260423-demo.json"
    map_file.parent.mkdir(parents=True, exist_ok=True)
    map_file.write_text(
        json.dumps(
            {
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
        )
        + "\n",
        encoding="utf-8",
    )

    plan_responses = run_mcp(
        [
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "pytest"}},
            },
            {"jsonrpc": "2.0", "method": "notifications/initialized"},
            {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
            {
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {
                    "name": "schema_migration_plan",
                    "arguments": {"context": str(context), "format": "json"},
                },
            },
        ]
    )

    tools = {tool["name"]: tool for tool in plan_responses[1]["result"]["tools"]}
    assert "schema_migration_plan" in tools
    assert "Read-only" in tools["schema_migration_plan"]["description"]
    assert "schema_migration_apply" in tools

    plan = json.loads(plan_responses[2]["result"]["content"][0]["text"])
    assert plan["mode"] == "dry-run"
    assert plan["applied"] is False
    assert plan["planned_actions"][0]["migration_id"] == "20260423_map_record_v1"
    assert "record_version" not in json.loads(map_file.read_text(encoding="utf-8"))

    apply_responses = run_mcp(
        [
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "pytest"}},
            },
            {"jsonrpc": "2.0", "method": "notifications/initialized"},
            {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {
                    "name": "schema_migration_apply",
                    "arguments": {"context": str(context), "format": "json"},
                },
            },
        ]
    )

    applied = json.loads(apply_responses[1]["result"]["content"][0]["text"])
    assert applied["mode"] == "apply"
    assert applied["applied"] is True
    stored = json.loads(map_file.read_text(encoding="utf-8"))
    assert stored["contract_version"] == "0.4"
    assert stored["record_version"] == 1
    assert "schema_version" not in stored


def test_mcp_front_doors_call_services_without_cli_shellout(tmp_path: Path, monkeypatch) -> None:
    context = bootstrap_context(tmp_path)
    run_cli(
        context,
        "record-workspace",
        "--workspace-key",
        "mcp-services",
        "--title",
        "MCP Service Workspace",
        "--root-ref",
        str(tmp_path),
        "--note",
        "workspace for direct MCP service test",
    )
    workspace_id = only_record_id(context, "workspace")
    run_cli(context, "set-current-workspace", "--workspace", workspace_id)
    run_cli(context, "init-anchor", "--directory", str(tmp_path), "--workspace", workspace_id)
    source_id = recorded_id(
        run_cli(
            context,
            "record-source",
            "--scope",
            "mcp.services",
            "--source-kind",
            "runtime",
            "--critique-status",
            "accepted",
            "--origin-kind",
            "command",
            "--origin-ref",
            "pytest mcp service",
            "--quote",
            "MCP services can append reason ledger entries directly.",
            "--note",
            "direct mcp reason service source",
        ),
        "source",
    )
    claim_id = recorded_id(
        run_cli(
            context,
            "record-claim",
            "--scope",
            "mcp.services",
            "--plane",
            "runtime",
            "--status",
            "supported",
            "--statement",
            "MCP services can append reason ledger entries directly.",
            "--source",
            source_id,
            "--note",
            "direct mcp reason service claim",
        ),
        "claim",
    )
    task_id = recorded_id(
        run_cli(
            context,
            "start-task",
            "--scope",
            "mcp.services",
            "--title",
            "Exercise direct MCP reason services",
            "--related-claim",
            claim_id,
            "--note",
            "active task for direct mcp reason service test",
        ),
        "task",
    )
    chain_payload = {
        "task": "exercise direct MCP reason services",
        "nodes": [
            {"role": "fact", "ref": claim_id, "quote": "MCP services can append reason ledger entries directly."},
            {"role": "task", "ref": task_id, "quote": "Exercise direct MCP reason services"},
        ],
        "edges": [{"from": claim_id, "to": task_id, "relation": "supports direct MCP reason services"}],
    }
    chain_file = tmp_path / "direct-mcp-chain.json"
    chain_file.write_text(json.dumps(chain_payload), encoding="utf-8")

    tep_server = load_mcp_server_module()

    def fail_run_cli(*_args, **_kwargs):
        raise AssertionError("front-door MCP tools must not shell out to context_cli.py")

    monkeypatch.setattr(tep_server, "run_cli", fail_run_cli)

    ok, next_step_text = tep_server.tool_next_step(
        {"context": str(context), "cwd": str(tmp_path), "intent": "plan", "task": "direct service route"}
    )
    assert ok is True
    assert "TEP Next Step" in next_step_text
    assert "intent: plan" in next_step_text

    ok, lookup_text = tep_server.tool_lookup(
        {
            "context": str(context),
            "cwd": str(tmp_path),
            "query": "direct service lookup",
            "reason": "orientation",
            "kind": "facts",
            "format": "json",
        }
    )
    assert ok is True
    payload = json.loads(lookup_text)
    assert payload["lookup_is_proof"] is False
    assert payload["focus"]["workspace_ref"] == workspace_id
    assert payload["focus"]["working_context_ref"].startswith("WCTX-")
    wctx = load_record(context, "working_context", payload["focus"]["working_context_ref"])
    assert wctx["record_version"] == 1
    assert wctx["owner_signature"]["algorithm"] == "hmac-sha256"
    agent = load_record(context, "agent_identity", wctx["agent_identity_ref"])
    assert agent["key_fingerprint"] == wctx["agent_key_fingerprint"]

    ok, evidence_text = tep_server.tool_record_evidence(
        {
            "context": str(context),
            "cwd": str(tmp_path),
            "scope": "mcp.services",
            "kind": "command-output",
            "command": "printf direct-mcp-record-evidence",
            "exit_code": 0,
            "quote": "direct-mcp-record-evidence",
            "claim_text": "MCP record_evidence writes support through the service layer.",
            "claim_status": "supported",
            "note": "direct mcp record_evidence service test",
            "format": "json",
        }
    )
    assert ok is True
    evidence = json.loads(evidence_text)
    assert evidence["source_ref"].startswith("SRC-")
    assert evidence["claim_ref"].startswith("CLM-")
    assert evidence["run_ref"].startswith("RUN-")
    assert evidence["records"][evidence["source_ref"]]["run_refs"] == [evidence["run_ref"]]
    assert evidence["records"][evidence["claim_ref"]]["source_refs"] == [evidence["source_ref"]]

    ok, augmented_text = tep_server.tool_augment_chain(
        {"context": str(context), "cwd": str(tmp_path), "file": str(chain_file), "format": "json"}
    )
    assert ok is True
    augmented = json.loads(augmented_text)
    assert augmented["augment_is_read_only"] is True
    assert augmented["validation"]["ok"] is True
    assert augmented["chain"]["nodes"][0]["record"]["id"] == claim_id

    ok, validated_text = tep_server.tool_validate_chain(
        {"context": str(context), "cwd": str(tmp_path), "file": str(chain_file), "format": "json"}
    )
    assert ok is True
    validated = json.loads(validated_text)
    assert validated["contract_version"] == "0.4"
    assert validated["validate_chain_is_proof"] is False
    assert validated["valid"] is True
    assert validated["proof_allowed"] is True

    ok, reason_step_text = tep_server.tool_reason_step(
        {
            "context": str(context),
            "cwd": str(tmp_path),
            "chain_payload": chain_payload,
            "intent": "editing",
            "mode": "edit",
            "action_kind": "write",
            "why": "prove MCP can create ledger steps through the service layer",
            "format": "json",
        }
    )
    assert ok is True
    reason = json.loads(reason_step_text)
    assert reason["id"].startswith("REASON-")
    assert reason["task_ref"] == task_id
    assert reason["chain_payload"] == chain_payload

    ok, reason_review_text = tep_server.tool_reason_review(
        {
            "context": str(context),
            "cwd": str(tmp_path),
            "reason_ref": reason["id"],
            "mode": "edit",
            "action_kind": "write",
            "grant": True,
            "format": "json",
        }
    )
    assert ok is True
    review = json.loads(reason_review_text)
    assert review["reason"]["id"] == reason["id"]
    assert review["grant"]["id"].startswith("GRANT-")
    assert review["grant"]["reason_ref"] == reason["id"]

    ok, outcome_text = tep_server.tool_task_outcome_check(
        {
            "context": str(context),
            "cwd": str(tmp_path),
            "task_ref": task_id,
            "outcome": "done",
            "format": "json",
        }
    )
    assert ok is True
    outcome = json.loads(outcome_text)
    assert outcome["task_ref"] == task_id
    assert outcome["outcome"] == "done"
    assert outcome["accepted"] is True
    assert outcome["obligations"] == []


def test_mcp_lists_and_calls_readonly_record_tools(tmp_path: Path) -> None:
    context = bootstrap_context(tmp_path)
    source_id = recorded_id(
        run_cli(
            context,
            "record-source",
            "--scope",
            "mcp.test",
            "--source-kind",
            "theory",
            "--critique-status",
            "accepted",
            "--origin-kind",
            "user",
            "--origin-ref",
            "mcp test",
            "--quote",
            "MCP gateway exposes read-only trust record lookup.",
            "--note",
            "mcp server test source",
        ),
        "source",
    )
    claim_id = recorded_id(
        run_cli(
            context,
            "record-claim",
            "--scope",
            "mcp.test",
            "--plane",
            "theory",
            "--status",
            "supported",
            "--statement",
            "MCP gateway can search canonical trust records.",
            "--source",
            source_id,
            "--logic-symbol",
            "service:mcp-gateway|system|MCP gateway symbol used for read-only tool lookup tests",
            "--logic-atom",
            "Searchable|service:mcp-gateway|affirmed",
            "--note",
            "mcp server test claim",
        ),
        "claim",
    )
    related_claim_id = recorded_id(
        run_cli(
            context,
            "record-claim",
            "--scope",
            "mcp.test",
            "--plane",
            "theory",
            "--status",
            "supported",
            "--statement",
            "Facility inventory reaches Program marketplace listings.",
            "--source",
            source_id,
            "--note",
            "mcp server related claim",
        ),
        "claim",
    )
    probe_pair_claim_id = recorded_id(
        run_cli(
            context,
            "record-claim",
            "--scope",
            "mcp.test",
            "--plane",
            "theory",
            "--status",
            "supported",
            "--statement",
            "Program marketplace listings imply Facility inventory dependency.",
            "--source",
            source_id,
            "--note",
            "mcp server probe pair claim",
        ),
        "claim",
    )
    run_cli(context, "topic-index", "build", "--method", "lexical")
    run_cli(context, "logic-index", "build")
    run_cli(context, "tap-record", "--record", claim_id, "--kind", "cited", "--intent", "mcp test")
    run_cli(context, "attention-index", "build")
    workspace_id = recorded_id(
        run_cli(
            context,
            "record-workspace",
            "--workspace-key",
            "mcp-readonly",
            "--title",
            "MCP read-only workspace",
            "--note",
            "workspace for signed MCP WCTX fixture",
        ),
        "workspace",
    )
    run_cli(context, "set-current-workspace", "--workspace", workspace_id)
    wctx_id = recorded_id(
        run_cli(
            context,
            "working-context",
            "create",
            "--scope",
            "mcp.test",
            "--title",
            "MCP read-only working context",
            "--pin",
            claim_id,
            "--note",
            "mcp working context",
        ),
        "working_context",
    )
    chain_file = tmp_path / "mcp-chain.json"
    chain_file.write_text(
        json.dumps(
            {
                "task": "mcp read-only evidence chain",
                "nodes": [
                    {"role": "fact", "ref": claim_id, "quote": "MCP gateway can search canonical trust records."},
                    {
                        "role": "requested_permission",
                        "ref": "REQ-mcp-read",
                        "quote": "Read MCP evidence chain metadata.",
                    },
                ],
                "edges": [{"from": claim_id, "to": "REQ-mcp-read", "relation": "motivates"}],
            }
        ),
        encoding="utf-8",
    )

    responses = run_mcp(
        [
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "pytest"}},
            },
            {"jsonrpc": "2.0", "method": "notifications/initialized"},
            {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
            {
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {
                    "name": "search_records",
                    "arguments": {
                        "context": str(context),
                        "query": "MCP gateway",
                        "record_types": ["claim"],
                        "format": "json",
                    },
                },
            },
            {
                "jsonrpc": "2.0",
                "id": 4,
                "method": "tools/call",
                "params": {
                    "name": "record_detail",
                    "arguments": {"context": str(context), "record": claim_id, "format": "json"},
                },
            },
            {
                "jsonrpc": "2.0",
                "id": 23,
                "method": "tools/call",
                "params": {
                    "name": "claim_graph",
                    "arguments": {"context": str(context), "query": "MCP gateway", "format": "json"},
                },
            },
            {
                "jsonrpc": "2.0",
                "id": 5,
                "method": "tools/call",
                "params": {
                    "name": "topic_search",
                    "arguments": {
                        "context": str(context),
                        "query": "MCP gateway",
                        "record_types": ["claim"],
                        "format": "json",
                    },
                },
            },
            {
                "jsonrpc": "2.0",
                "id": 6,
                "method": "tools/call",
                "params": {
                    "name": "working_contexts",
                    "arguments": {"context": str(context), "record": wctx_id, "format": "json"},
                },
            },
            {
                "jsonrpc": "2.0",
                "id": 7,
                "method": "tools/call",
                "params": {
                    "name": "logic_search",
                    "arguments": {
                        "context": str(context),
                        "predicate": "Searchable",
                        "format": "json",
                    },
                },
            },
            {
                "jsonrpc": "2.0",
                "id": 8,
                "method": "tools/call",
                "params": {
                    "name": "logic_check",
                    "arguments": {"context": str(context), "format": "json"},
                },
            },
            {
                "jsonrpc": "2.0",
                "id": 9,
                "method": "tools/call",
                "params": {
                    "name": "logic_graph",
                    "arguments": {"context": str(context), "symbol": "service:mcp-gateway", "format": "json"},
                },
            },
            {
                "jsonrpc": "2.0",
                "id": 10,
                "method": "tools/call",
                "params": {
                    "name": "cleanup_archives",
                    "arguments": {"context": str(context), "format": "json"},
                },
            },
            {
                "jsonrpc": "2.0",
                "id": 11,
                "method": "tools/call",
                "params": {
                    "name": "augment_chain",
                    "arguments": {"context": str(context), "file": str(chain_file), "format": "json"},
                },
            },
            {
                "jsonrpc": "2.0",
                "id": 12,
                "method": "tools/call",
                "params": {
                    "name": "attention_map",
                    "arguments": {"context": str(context), "mode": "research", "format": "json"},
                },
            },
            {
                "jsonrpc": "2.0",
                "id": 13,
                "method": "tools/call",
                "params": {
                    "name": "curiosity_probes",
                    "arguments": {"context": str(context), "budget": 3, "format": "json"},
                },
            },
            {
                "jsonrpc": "2.0",
                "id": 14,
                "method": "tools/call",
                "params": {
                    "name": "probe_inspect",
                    "arguments": {"context": str(context), "index": 1, "scope": "all", "format": "json"},
                },
            },
            {
                "jsonrpc": "2.0",
                "id": 15,
                "method": "tools/call",
                "params": {
                    "name": "probe_chain_draft",
                    "arguments": {"context": str(context), "index": 1, "scope": "all", "format": "json"},
                },
            },
            {
                "jsonrpc": "2.0",
                "id": 16,
                "method": "tools/call",
                "params": {
                    "name": "probe_pack",
                    "arguments": {"context": str(context), "budget": 1, "scope": "all", "format": "json"},
                },
            },
            {
                "jsonrpc": "2.0",
                "id": 17,
                "method": "tools/call",
                "params": {
                    "name": "probe_pack_compare",
                    "arguments": {"context": str(context), "budget": 1, "scope": "all", "format": "json"},
                },
            },
            {
                "jsonrpc": "2.0",
                "id": 18,
                "method": "tools/call",
                "params": {
                    "name": "attention_diagram",
                    "arguments": {"context": str(context), "limit": 3, "scope": "all", "detail": "compact", "format": "json"},
                },
            },
            {
                "jsonrpc": "2.0",
                "id": 19,
                "method": "tools/call",
                "params": {
                    "name": "probe_route",
                    "arguments": {"context": str(context), "index": 1, "scope": "all", "format": "json"},
                },
            },
            {
                "jsonrpc": "2.0",
                "id": 20,
                "method": "tools/call",
                "params": {
                    "name": "attention_diagram_compare",
                    "arguments": {"context": str(context), "limit": 3, "scope": "all", "format": "json"},
                },
            },
            {
                "jsonrpc": "2.0",
                "id": 30,
                "method": "tools/call",
                "params": {
                    "name": "curiosity_map",
                    "arguments": {
                        "context": str(context),
                        "volume": "compact",
                        "scope": "all",
                        "mode": "theory",
                        "html": True,
                        "format": "json",
                    },
                },
            },
            {
                "jsonrpc": "2.0",
                "id": 34,
                "method": "tools/call",
                "params": {
                    "name": "map_refresh",
                    "arguments": {
                        "context": str(context),
                        "volume": "compact",
                        "scope": "all",
                        "limit": 2,
                        "format": "json",
                    },
                },
            },
            {
                "jsonrpc": "2.0",
                "id": 35,
                "method": "tools/call",
                "params": {
                    "name": "map_open",
                    "arguments": {
                        "context": str(context),
                        "query": "Facility Program relationship",
                        "scope": "all",
                        "format": "json",
                    },
                },
            },
            {
                "jsonrpc": "2.0",
                "id": 31,
                "method": "tools/call",
                "params": {
                    "name": "lookup",
                    "arguments": {
                        "context": str(context),
                        "query": "MCP gateway code lookup",
                        "reason": "orientation",
                        "kind": "auto",
                        "format": "json",
                    },
                },
            },
            {
                "jsonrpc": "2.0",
                "id": 32,
                "method": "tools/call",
                "params": {
                    "name": "validate_chain",
                    "arguments": {"context": str(context), "file": str(chain_file), "format": "json"},
                },
            },
            {
                "jsonrpc": "2.0",
                "id": 33,
                "method": "tools/call",
                "params": {
                    "name": "task_outcome_check",
                    "arguments": {
                        "context": str(context),
                        "task_ref": "TASK-missing",
                        "outcome": "done",
                        "format": "json",
                    },
                },
            },
            {
                "jsonrpc": "2.0",
                "id": 21,
                "method": "tools/call",
                "params": {
                    "name": "next_step",
                    "arguments": {"context": str(context), "intent": "plan", "task": "MCP route"},
                },
            },
            {
                "jsonrpc": "2.0",
                "id": 22,
                "method": "tools/call",
                "params": {
                    "name": "next_step",
                    "arguments": {"context": str(context), "intent": "edit", "task": "MCP route", "format": "json"},
                },
            },
            {
                "jsonrpc": "2.0",
                "id": 24,
                "method": "tools/call",
                "params": {
                    "name": "telemetry_report",
                    "arguments": {"context": str(context), "format": "json"},
                },
            },
            {
                "jsonrpc": "2.0",
                "id": 25,
                "method": "tools/call",
                "params": {
                    "name": "working_context_drift",
                    "arguments": {"context": str(context), "task": "mcp working context handoff", "format": "json"},
                },
            },
            {
                "jsonrpc": "2.0",
                "id": 26,
                "method": "tools/call",
                "params": {
                    "name": "workspace_admission",
                    "arguments": {"context": str(context), "repo": str(tmp_path / "unknown-repo"), "format": "json"},
                },
            },
            {
                "jsonrpc": "2.0",
                "id": 27,
                "method": "tools/call",
                "params": {
                    "name": "code_search",
                    "arguments": {"context": str(context), "scope": "workspace", "format": "json"},
                },
            },
            {
                "jsonrpc": "2.0",
                "id": 28,
                "method": "tools/call",
                "params": {
                    "name": "backend_status",
                    "arguments": {"context": str(context), "root": str(tmp_path), "scope": "project", "format": "json"},
                },
            },
            {
                "jsonrpc": "2.0",
                "id": 29,
                "method": "tools/call",
                "params": {
                    "name": "backend_check",
                    "arguments": {
                        "context": str(context),
                        "backend": "code_intelligence.cocoindex",
                        "root": str(tmp_path),
                        "scope": "project",
                        "format": "json",
                    },
                },
            },
        ]
    )

    by_id = {response["id"]: response for response in responses}
    assert by_id[1]["result"]["serverInfo"]["name"] == "trust-evidence-protocol"
    tool_names = {tool["name"] for tool in by_id[2]["result"]["tools"]}
    tools_payload = json.dumps(by_id[2]["result"]["tools"])
    assert "Path to TEP context root" in tools_payload
    assert "nearest .tep context_root" in tools_payload
    assert "Read a task-oriented TEP context brief" in tools_payload
    assert "chain_starter" in tools_payload
    assert "Path to .codex_context. Defaults to ./.codex_context." not in tools_payload
    context_schemas = {
        json.dumps(tool["inputSchema"]["properties"]["context"], sort_keys=True)
        for tool in by_id[2]["result"]["tools"]
        if "context" in tool["inputSchema"]["properties"]
    }
    assert len(context_schemas) == 1
    assert {
        "search_records",
        "next_step",
        "lookup",
        "record_evidence",
        "reason_step",
        "reason_review",
        "task_outcome_check",
        "record_detail",
        "claim_graph",
        "linked_records",
        "telemetry_report",
        "backend_status",
        "backend_check",
        "code_search",
        "code_feedback",
        "code_smell_report",
        "cleanup_candidates",
        "cleanup_archives",
        "augment_chain",
        "validate_chain",
        "topic_search",
        "topic_info",
        "topic_conflict_candidates",
        "attention_map",
        "attention_diagram",
        "attention_diagram_compare",
        "curiosity_map",
        "map_refresh",
        "map_open",
        "map_view",
        "map_move",
        "map_drilldown",
        "map_checkpoint",
        "curiosity_probes",
        "probe_inspect",
        "probe_chain_draft",
        "probe_route",
        "probe_pack",
        "probe_pack_compare",
        "working_contexts",
        "working_context_drift",
        "workspace_admission",
        "logic_search",
        "logic_check",
        "logic_graph",
        "logic_conflict_candidates",
    } <= tool_names

    search_result = by_id[3]["result"]
    assert search_result["isError"] is False
    assert claim_id in search_result["content"][0]["text"]

    detail_result = by_id[4]["result"]
    assert detail_result["isError"] is False
    assert source_id in detail_result["content"][0]["text"]

    claim_graph = by_id[23]["result"]
    assert claim_graph["isError"] is False
    claim_graph_payload = json.loads(claim_graph["content"][0]["text"])
    assert claim_graph_payload["claim_graph_is_proof"] is False
    assert claim_id in [item["id"] for item in claim_graph_payload["anchors"]]
    assert source_id in [item["id"] for item in claim_graph_payload["records"]]
    assert {"from": claim_id, "to": source_id, "fields": ["source_refs"]} in claim_graph_payload["edges"]

    topic_result = by_id[5]["result"]
    assert topic_result["isError"] is False
    assert claim_id in topic_result["content"][0]["text"]

    wctx_result = by_id[6]["result"]
    assert wctx_result["isError"] is False
    assert wctx_id in wctx_result["content"][0]["text"]

    wctx_drift = by_id[25]["result"]
    assert wctx_drift["isError"] is False
    wctx_drift_payload = json.loads(wctx_drift["content"][0]["text"])
    assert wctx_drift_payload["working_context_drift_is_proof"] is False
    assert wctx_drift_payload["best_matching_context"]["id"] == wctx_id

    backend_status = by_id[28]["result"]
    assert backend_status["isError"] is False
    backend_status_payload = json.loads(backend_status["content"][0]["text"])
    assert backend_status_payload["backend_status_is_proof"] is False
    assert "workspace_ref" in backend_status_payload["focus"]

    backend_check = by_id[29]["result"]
    assert backend_check["isError"] is False
    backend_check_payload = json.loads(backend_check["content"][0]["text"])
    assert backend_check_payload["backend_status_is_proof"] is False
    assert backend_check_payload["matches"][0]["id"] == "cocoindex"

    workspace_admission = by_id[26]["result"]
    assert workspace_admission["isError"] is False
    workspace_admission_payload = json.loads(workspace_admission["content"][0]["text"])
    assert workspace_admission_payload["workspace_admission_is_proof"] is False
    assert workspace_admission_payload["requires_user_decision"] is True
    assert "create-new-workspace" in workspace_admission_payload["options"]

    code_search = by_id[27]["result"]
    assert code_search["isError"] is False
    assert json.loads(code_search["content"][0]["text"])["results"] == []

    logic_result = by_id[7]["result"]
    assert logic_result["isError"] is False
    assert claim_id in logic_result["content"][0]["text"]

    logic_check = by_id[8]["result"]
    assert logic_check["isError"] is False
    assert '"atom_count": 1' in logic_check["content"][0]["text"]

    logic_graph = by_id[9]["result"]
    assert logic_graph["isError"] is False
    assert "service:mcp-gateway" in logic_graph["content"][0]["text"]

    cleanup_archives = by_id[10]["result"]
    assert cleanup_archives["isError"] is False
    assert '"cleanup_archives_is_read_only": true' in cleanup_archives["content"][0]["text"]

    augmented_chain = by_id[11]["result"]
    assert augmented_chain["isError"] is False
    assert claim_id in augmented_chain["content"][0]["text"]
    assert '"ok": true' in augmented_chain["content"][0]["text"]

    validated_chain = by_id[32]["result"]
    assert validated_chain["isError"] is False
    validated_chain_payload = json.loads(validated_chain["content"][0]["text"])
    assert validated_chain_payload["contract_version"] == "0.4"
    assert validated_chain_payload["validate_chain_is_proof"] is False
    assert validated_chain_payload["valid"] is True

    attention_map = by_id[12]["result"]
    assert attention_map["isError"] is False
    assert '"attention_index_is_proof": false' in attention_map["content"][0]["text"]
    assert '"mode": "research"' in attention_map["content"][0]["text"]

    curiosity = by_id[13]["result"]
    assert curiosity["isError"] is False
    assert '"attention_index_is_proof": false' in curiosity["content"][0]["text"]

    probe_inspect = by_id[14]["result"]
    assert probe_inspect["isError"] is False
    assert '"inspection_is_proof": false' in probe_inspect["content"][0]["text"]
    assert related_claim_id in probe_inspect["content"][0]["text"]
    assert probe_pair_claim_id in probe_inspect["content"][0]["text"]

    probe_chain_draft = by_id[15]["result"]
    assert probe_chain_draft["isError"] is False
    assert '"draft_is_proof": false' in probe_chain_draft["content"][0]["text"]
    assert '"ok": true' in probe_chain_draft["content"][0]["text"]

    probe_pack = by_id[16]["result"]
    assert probe_pack["isError"] is False
    assert '"pack_is_proof": false' in probe_pack["content"][0]["text"]
    assert '"detail": "compact"' in probe_pack["content"][0]["text"]
    assert '"metrics_are_proof": false' in probe_pack["content"][0]["text"]
    assert '"chain_validation"' in probe_pack["content"][0]["text"]

    probe_pack_compare = by_id[17]["result"]
    assert probe_pack_compare["isError"] is False
    assert '"comparison_is_proof": false' in probe_pack_compare["content"][0]["text"]
    assert '"payload_char_count"' in probe_pack_compare["content"][0]["text"]
    assert '"omitted_fields_compact"' in probe_pack_compare["content"][0]["text"]

    attention_diagram = by_id[18]["result"]
    assert attention_diagram["isError"] is False
    assert '"diagram_is_proof": false' in attention_diagram["content"][0]["text"]
    assert '"detail": "compact"' in attention_diagram["content"][0]["text"]
    assert '"omitted_fields": [' in attention_diagram["content"][0]["text"]
    assert "graph TD" in attention_diagram["content"][0]["text"]

    probe_route = by_id[19]["result"]
    assert probe_route["isError"] is False
    assert '"route_is_proof": false' in probe_route["content"][0]["text"]
    assert '"recommended_commands"' in probe_route["content"][0]["text"]
    assert '"diagram_delta"' in probe_route["content"][0]["text"]
    assert "attention-diagram-compare" in probe_route["content"][0]["text"]
    assert "probe-pack-compare" in probe_route["content"][0]["text"]

    attention_diagram_compare = by_id[20]["result"]
    assert attention_diagram_compare["isError"] is False
    assert '"comparison_is_proof": false' in attention_diagram_compare["content"][0]["text"]
    assert '"record_summaries"' in attention_diagram_compare["content"][0]["text"]
    assert '"payload_char_count"' in attention_diagram_compare["content"][0]["text"]

    curiosity_map = by_id[30]["result"]
    assert curiosity_map["isError"] is False
    assert '"map_is_proof": false' in curiosity_map["content"][0]["text"]
    assert '"volume": "compact"' in curiosity_map["content"][0]["text"]
    assert '"mode": "theory"' in curiosity_map["content"][0]["text"]
    assert '"curiosity_prompts"' in curiosity_map["content"][0]["text"]
    assert "graph TD" in curiosity_map["content"][0]["text"]
    curiosity_payload = json.loads(curiosity_map["content"][0]["text"])
    assert Path(curiosity_payload["html_path"]).exists()

    map_refresh = by_id[34]["result"]
    assert map_refresh["isError"] is False
    map_refresh_payload = json.loads(map_refresh["content"][0]["text"])
    assert map_refresh_payload["map_refresh_is_proof"] is False
    assert map_refresh_payload["applied"] is True
    assert map_refresh_payload["refresh_triggers_are_proof"] is False
    assert "refresh_triggers" in map_refresh_payload
    assert map_refresh_payload["created_refs"]

    map_open = by_id[35]["result"]
    assert map_open["isError"] is False
    map_open_payload = json.loads(map_open["content"][0]["text"])
    assert map_open_payload["map_is_proof"] is False
    assert map_open_payload["map_session_ref"].endswith("#map-session")
    assert map_open_payload["anchor_facts"]
    map_session_ref = map_open_payload["map_session_ref"]
    map_target = map_open_payload["zone"]["map_ref"]
    anchor_ref = map_open_payload["anchor_facts"][0]["ref"]
    followup = run_mcp(
        [
            {
                "jsonrpc": "2.0",
                "id": 101,
                "method": "initialize",
                "params": {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "pytest"}},
            },
            {"jsonrpc": "2.0", "method": "notifications/initialized"},
            {
                "jsonrpc": "2.0",
                "id": 102,
                "method": "tools/call",
                "params": {
                    "name": "map_view",
                    "arguments": {"context": str(context), "map_session_ref": map_session_ref, "format": "json"},
                },
            },
            {
                "jsonrpc": "2.0",
                "id": 103,
                "method": "tools/call",
                "params": {
                    "name": "map_move",
                    "arguments": {"context": str(context), "map_session_ref": map_session_ref, "target": map_target, "format": "json"},
                },
            },
            {
                "jsonrpc": "2.0",
                "id": 104,
                "method": "tools/call",
                "params": {
                    "name": "map_drilldown",
                    "arguments": {"context": str(context), "map_session_ref": map_session_ref, "record": anchor_ref, "format": "json"},
                },
            },
            {
                "jsonrpc": "2.0",
                "id": 105,
                "method": "tools/call",
                "params": {
                    "name": "map_checkpoint",
                    "arguments": {"context": str(context), "map_session_ref": map_session_ref, "note": "mcp checkpoint", "format": "json"},
                },
            },
        ]
    )
    followup_by_id = {response["id"]: response for response in followup}
    assert followup_by_id[102]["result"]["isError"] is False
    assert json.loads(followup_by_id[102]["result"]["content"][0]["text"])["map_session_ref"] == map_session_ref
    assert followup_by_id[103]["result"]["isError"] is False
    assert followup_by_id[104]["result"]["isError"] is False
    assert json.loads(followup_by_id[104]["result"]["content"][0]["text"])["drilldown_is_proof"] is False
    assert followup_by_id[105]["result"]["isError"] is False
    assert json.loads(followup_by_id[105]["result"]["content"][0]["text"])["checkpoint"]["note"] == "mcp checkpoint"

    lookup = by_id[31]["result"]
    assert lookup["isError"] is False
    lookup_payload = json.loads(lookup["content"][0]["text"])
    assert lookup_payload["lookup_is_proof"] is False
    assert lookup_payload["kind"] == "code"
    assert lookup_payload["mode"] == "code"
    assert lookup_payload["primary_tool"] == "code-search"
    assert lookup_payload["api_contract_version"] == 1
    assert lookup_payload["map_navigation"]["map_navigation_is_proof"] is False
    assert lookup_payload["map_navigation"]["cells"]
    assert all(not node["ref"].startswith("MAP-") for node in lookup_payload["chain_starter"]["nodes"])
    assert lookup_payload["output_contract"]["if_chain_needed"].startswith("draft ids/quotes")
    assert lookup_payload["chain_starter"]["chain_starter_is_proof"] is False
    assert lookup_payload["chain_starter"]["decision_mode"] == "planning"
    assert any(node["ref"] == claim_id and node["role"] == "fact" for node in lookup_payload["chain_starter"]["nodes"])
    assert any(command.startswith("augment-chain") for command in lookup_payload["chain_starter"]["next_commands"])

    next_step = by_id[21]["result"]
    assert next_step["isError"] is False
    assert "TEP Next Step" in next_step["content"][0]["text"]
    assert "intent: plan" in next_step["content"][0]["text"]
    graph_lines = [line for line in next_step["content"][0]["text"].splitlines() if line.startswith("- graph: ")]
    assert graph_lines
    assert "=>" in graph_lines[0]

    next_step_json = by_id[22]["result"]
    assert next_step_json["isError"] is False
    next_step_payload = json.loads(next_step_json["content"][0]["text"])
    assert next_step_payload["intent"] == "edit"
    assert next_step_payload["route_graph"]["graph_version"] == 1

    outcome_check = by_id[33]["result"]
    assert outcome_check["isError"] is False
    outcome_payload = json.loads(outcome_check["content"][0]["text"])
    assert outcome_payload["accepted"] is False
    assert outcome_payload["task_ref"] == "TASK-missing"
    assert "missing task record TASK-missing" in outcome_payload["errors"]

    telemetry = by_id[24]["result"]
    assert telemetry["isError"] is False
    telemetry_payload = json.loads(telemetry["content"][0]["text"])
    assert telemetry_payload["telemetry_is_proof"] is False
    assert telemetry_payload["by_channel"]["mcp"] >= 1
    assert telemetry_payload["by_tool"]["claim-graph"] >= 1


def test_mcp_uses_cwd_for_local_tep_anchor_resolution(tmp_path: Path) -> None:
    context = bootstrap_context(tmp_path)
    global_workdir = tmp_path / "global-workdir"
    global_workdir.mkdir()
    workdir = tmp_path / "anchored-workdir"
    workdir.mkdir()
    run_cli(
        context,
        "record-workspace",
        "--workspace-key",
        "mcp-global",
        "--title",
        "MCP Global Workspace",
        "--root-ref",
        str(global_workdir),
        "--note",
        "global workspace boundary",
    )
    global_workspace_id = only_record_id(context, "workspace")
    run_cli(context, "set-current-workspace", "--workspace", global_workspace_id)
    global_task_id = recorded_id(
        run_cli(
            context,
            "start-task",
            "--scope",
            "mcp.global.task",
            "--title",
            "MCP Global Task",
            "--note",
            "global task must not leak into anchored MCP calls",
        ),
        "task",
    )
    run_cli(
        context,
        "record-workspace",
        "--workspace-key",
        "mcp-anchored",
        "--title",
        "MCP Anchored Workspace",
        "--root-ref",
        str(workdir),
        "--note",
        "workspace boundary",
    )
    workspace_id = [
        path.stem
        for path in sorted((context / "records" / "workspace").glob("*.json"))
        if path.stem != global_workspace_id
    ][0]
    run_cli(context, "set-current-workspace", "--workspace", workspace_id)
    run_cli(context, "pause-task", "--task", global_task_id, "--note", "pause global task before anchor task")
    run_cli(
        context,
        "record-project",
        "--project-key",
        "mcp-project",
        "--title",
        "MCP Project",
        "--root-ref",
        str(workdir),
        "--note",
        "project inside current workspace",
    )
    project_id = only_record_id(context, "project")
    task_id = recorded_id(
        run_cli(
            context,
            "start-task",
            "--scope",
            "mcp.anchor.task",
            "--title",
            "MCP Anchor Task",
            "--project",
            project_id,
            "--note",
            "local anchor task",
        ),
        "task",
    )
    run_cli(context, "switch-task", "--task", global_task_id, "--note", "restore global task before MCP cwd call")
    run_cli(
        context,
        "init-anchor",
        "--directory",
        str(workdir),
        "--workspace",
        workspace_id,
        "--project",
        project_id,
        "--task",
        task_id,
        "--note",
        "local mcp anchor",
    )

    responses = run_mcp(
        [
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "pytest"}},
            },
            {"jsonrpc": "2.0", "method": "notifications/initialized"},
            {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {
                    "name": "brief_context",
                    "arguments": {"cwd": str(workdir), "task": "mcp cwd anchor lookup", "detail": "full"},
                },
            },
        ]
    )

    result = {response["id"]: response for response in responses}[2]["result"]
    assert result["isError"] is False
    text = result["content"][0]["text"]
    assert "requested: mcp cwd anchor lookup" in text
    assert f"`{workspace_id}` status=`active` key=`mcp-anchored`" in text
    assert f"`{project_id}` status=`active` key=`mcp-project`" in text
    assert f"`{task_id}` status=`paused` type=`general` mode=`manual` scope=`mcp.anchor.task`" in text
    assert global_task_id not in text

    mcp_server_cwd = tmp_path / "mcp-server-cwd"
    mcp_server_cwd.mkdir()
    unanchored_responses = run_mcp(
        [
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "pytest"}},
            },
            {"jsonrpc": "2.0", "method": "notifications/initialized"},
            {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {
                    "name": "brief_context",
                    "arguments": {"context": str(context), "task": "mcp cwd anchor lookup", "detail": "compact"},
                },
            },
        ],
        cwd=mcp_server_cwd,
    )
    unanchored_result = {response["id"]: response for response in unanchored_responses}[2]["result"]
    assert unanchored_result["isError"] is True
    assert "MCP workspace anchor is required" in unanchored_result["content"][0]["text"]
    assert global_task_id not in unanchored_result["content"][0]["text"]
