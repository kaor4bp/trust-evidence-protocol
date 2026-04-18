from __future__ import annotations

import json
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
    match = re.search(rf"Recorded {record_type} ([A-Z]+-\d{{8}}-[0-9a-f]{{8}})", result.stdout)
    assert match, result.stdout
    return match.group(1)


def run_mcp(messages: list[dict]) -> list[dict]:
    payload = "\n".join(json.dumps(message) for message in messages) + "\n"
    result = subprocess.run(
        [sys.executable, str(MCP_SERVER)],
        cwd=REPO_ROOT,
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


def test_mcp_manifest_declares_readonly_server() -> None:
    plugin_manifest = json.loads((PLUGIN_ROOT / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8"))
    assert plugin_manifest["mcpServers"] == "./.mcp.json"

    manifest = json.loads((PLUGIN_ROOT / ".mcp.json").read_text(encoding="utf-8"))
    server = manifest["mcpServers"]["trust-evidence-protocol"]
    assert server["command"] == "python3"
    assert server["args"] == ["mcp/tep_server.py"]
    assert MCP_SERVER.exists()


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
                    {"role": "fact", "ref": claim_id},
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
                    "arguments": {"context": str(context), "format": "json"},
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
        ]
    )

    by_id = {response["id"]: response for response in responses}
    assert by_id[1]["result"]["serverInfo"]["name"] == "trust-evidence-protocol"
    tool_names = {tool["name"] for tool in by_id[2]["result"]["tools"]}
    assert {
        "search_records",
        "record_detail",
        "linked_records",
        "code_search",
        "code_smell_report",
        "cleanup_candidates",
        "cleanup_archives",
        "augment_chain",
        "topic_search",
        "topic_info",
        "topic_conflict_candidates",
        "attention_map",
        "curiosity_probes",
        "probe_inspect",
        "probe_chain_draft",
        "probe_pack",
        "working_contexts",
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

    topic_result = by_id[5]["result"]
    assert topic_result["isError"] is False
    assert claim_id in topic_result["content"][0]["text"]

    wctx_result = by_id[6]["result"]
    assert wctx_result["isError"] is False
    assert wctx_id in wctx_result["content"][0]["text"]

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

    attention_map = by_id[12]["result"]
    assert attention_map["isError"] is False
    assert '"attention_index_is_proof": false' in attention_map["content"][0]["text"]

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


def test_mcp_uses_cwd_for_local_tep_anchor_resolution(tmp_path: Path) -> None:
    context = bootstrap_context(tmp_path)
    workdir = tmp_path / "anchored-workdir"
    workdir.mkdir()
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
    workspace_id = only_record_id(context, "workspace")
    run_cli(context, "set-current-workspace", "--workspace", workspace_id)
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
    run_cli(
        context,
        "init-anchor",
        "--directory",
        str(workdir),
        "--workspace",
        workspace_id,
        "--project",
        project_id,
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
                    "arguments": {"cwd": str(workdir), "task": "mcp cwd anchor lookup"},
                },
            },
        ]
    )

    result = {response["id"]: response for response in responses}[2]["result"]
    assert result["isError"] is False
    assert f"`{workspace_id}` status=`active` key=`mcp-anchored`" in result["content"][0]["text"]
    assert f"`{project_id}` status=`active` key=`mcp-project`" in result["content"][0]["text"]
