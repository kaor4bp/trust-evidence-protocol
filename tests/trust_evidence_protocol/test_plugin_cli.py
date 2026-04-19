from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import zipfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
PLUGIN_ROOT = REPO_ROOT / "plugins" / "trust-evidence-protocol"
SKILL_ROOT = PLUGIN_ROOT / "skills" / "trust-evidence-protocol"
BOOTSTRAP = REPO_ROOT / "plugins" / "trust-evidence-protocol" / "scripts" / "bootstrap_codex_context.py"
CLI = REPO_ROOT / "plugins" / "trust-evidence-protocol" / "scripts" / "context_cli.py"
INSTALL_LOCAL_PLUGIN = REPO_ROOT / "scripts" / "install-local-plugin.sh"


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


def only_record_id(context: Path, record_type: str) -> str:
    files = sorted((context / "records" / record_type).glob("*.json"))
    assert len(files) == 1, [file.name for file in files]
    return files[0].stem


def recorded_id(result: subprocess.CompletedProcess[str], record_type: str) -> str:
    match = re.search(rf"Recorded {record_type} ([A-Z]+-\d{{8}}-[0-9a-f]{{8}})", result.stdout)
    assert match, result.stdout
    return match.group(1)


def load_record(context: Path, record_type: str, record_id: str) -> dict:
    return json.loads((context / "records" / record_type / f"{record_id}.json").read_text(encoding="utf-8"))


def test_install_local_plugin_script_creates_single_active_cache_version(tmp_path: Path) -> None:
    local_source = tmp_path / "plugins" / "trust-evidence-protocol"
    cache = tmp_path / "cache" / "trust-evidence-protocol"
    version = json.loads((PLUGIN_ROOT / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8"))["version"]
    old_version = cache / "0.1.1"
    old_version.mkdir(parents=True)
    (old_version / "old.txt").write_text("old", encoding="utf-8")
    stale_local_bytecode = local_source / "tep_runtime" / "__pycache__"
    stale_cache_bytecode = cache / version / "tep_runtime" / "__pycache__"
    stale_local_bytecode.mkdir(parents=True)
    stale_cache_bytecode.mkdir(parents=True)
    (stale_local_bytecode / "stale.pyc").write_bytes(b"stale")
    (stale_cache_bytecode / "stale.pyc").write_bytes(b"stale")

    result = subprocess.run(
        [str(INSTALL_LOCAL_PLUGIN)],
        cwd=REPO_ROOT,
        env={
            **os.environ,
            "HOME": str(tmp_path / "home"),
            "TEP_LOCAL_PLUGIN_SOURCE": str(local_source),
            "TEP_CODEX_PLUGIN_CACHE": str(cache),
        },
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr

    assert (local_source / ".codex-plugin" / "plugin.json").is_file()
    assert (cache / version / ".codex-plugin" / "plugin.json").is_file()
    assert (cache / "_archived-pre-active" / "0.1.1" / "old.txt").read_text(encoding="utf-8") == "old"
    active_dirs = sorted(path.name for path in cache.iterdir() if path.is_dir())
    assert active_dirs == [version, "_archived-pre-active"]
    installed_roots = [local_source, cache / version]
    for root in installed_roots:
        assert not list(root.rglob("__pycache__")), root
        assert not list(root.rglob("*.pyc")), root


def strictness_approval(context: Path, value: str, permission_id: str | None = None) -> tuple[str, str]:
    request_args = [
        "request-strictness-change",
        value,
        "--reason",
        f"test approval for {value}",
    ]
    if permission_id:
        request_args.extend(["--permission", permission_id])
    request_result = run_cli(context, *request_args)
    request_match = re.search(r"(REQ-\d{8}-[0-9a-f]{8})", request_result.stdout)
    assert request_match, request_result.stdout
    request_id = request_match.group(1)
    source_id = recorded_id(
        run_cli(
            context,
            "record-source",
            "--scope",
            "strictness.approval",
            "--source-kind",
            "theory",
            "--critique-status",
            "accepted",
            "--origin-kind",
            "user",
            "--origin-ref",
            "strictness approval",
            "--quote",
            f"TEP-APPROVE {request_id}",
            "--note",
            "strictness approval source",
        ),
        "source",
    )
    return request_id, source_id


def test_skill_package_is_core_plus_workflows_without_legacy_identity_artifacts() -> None:
    skill = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
    assert "workflows/information-lookup.md" in skill
    assert "workflows/before-action.md" in skill
    assert "workflows/after-action.md" in skill
    assert "workflows/persistence-and-records.md" in skill
    assert "workflows/plugin-commands.md" in skill

    workflow_files = sorted(path.name for path in (SKILL_ROOT / "workflows").glob("*.md"))
    assert workflow_files == [
        "after-action.md",
        "before-action.md",
        "information-lookup.md",
        "persistence-and-records.md",
        "plugin-commands.md",
    ]

    assert not (REPO_ROOT / "trust-evidence-protocol").exists()

    package_files = [path for path in SKILL_ROOT.rglob("*") if path.is_file()]
    forbidden_names = {
        "identity-profiles.md",
        "startup-pipeline.md",
        "feedback-ledger.md",
        "profile-optimization.md",
        "online-evolution.md",
        "breed_profiles.py",
        "protocol-spec.yaml",
        "trait-catalog.template.json",
        "trait-relations.template.json",
    }
    assert not [path for path in package_files if path.name in forbidden_names]

    package_text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in package_files
        if path.suffix in {".md", ".yaml", ".yml", ".json"} and path.name != "SKILL.md"
    )
    for forbidden in ("identity_pool", "identity_events", "review_events", "trust_state"):
        assert forbidden not in package_text


def test_new_record_ids_use_random_suffix_and_legacy_ids_remain_valid(tmp_path: Path) -> None:
    context = bootstrap_context(tmp_path)

    run_cli(
        context,
        "record-source",
        "--scope",
        "demo.ids",
        "--source-kind",
        "runtime",
        "--critique-status",
        "accepted",
        "--origin-kind",
        "command",
        "--origin-ref",
        "pytest id allocation",
        "--quote",
        "new ids use random suffixes",
        "--note",
        "id allocation check",
    )
    source_id = only_record_id(context, "source")
    assert re.match(r"^SRC-\d{8}-[0-9a-f]{8}$", source_id)

    legacy_record = context / "records" / "claim" / "CLM-20260416-9999.json"
    legacy_record.write_text(
        json.dumps(
            {
                "id": "CLM-20260416-9999",
                "record_type": "claim",
                "scope": "demo.ids",
                "plane": "runtime",
                "status": "supported",
                "statement": "Legacy sequential ids remain valid.",
                "source_refs": [source_id],
                "support_refs": [],
                "contradiction_refs": [],
                "derived_from": [],
                "project_refs": [],
                "task_refs": [],
                "tags": [],
                "recorded_at": "2026-04-16T00:00:00+03:00",
                "note": "legacy compatibility check",
            }
        ),
        encoding="utf-8",
    )

    result = run_cli(context, "review-context")
    assert result.returncode == 0


def test_record_input_creates_prompt_provenance_and_runtime_configures_capture(tmp_path: Path) -> None:
    context = bootstrap_context(tmp_path)

    config = run_cli(
        context,
        "configure-runtime",
        "--input-capture",
        "user_prompts=metadata-only",
        "--input-capture",
        "session_linking=false",
    )
    assert "input_capture.user_prompts=metadata-only" in config.stdout
    assert "input_capture.session_linking=false" in config.stdout

    prompt = "Use pytest fixtures for deterministic runtime tests."
    result = run_cli(
        context,
        "record-input",
        "--scope",
        "demo.input",
        "--input-kind",
        "user_prompt",
        "--origin-kind",
        "user",
        "--origin-ref",
        "chat-turn-1",
        "--text",
        prompt,
        "--session-ref",
        "session-1",
        "--tag",
        "guideline-candidate",
        "--note",
        "captured prompt fixture",
    )
    input_id = recorded_id(result, "input")
    record = load_record(context, "input", input_id)

    assert input_id.startswith("INP-")
    assert record["text"] == prompt
    assert record["input_kind"] == "user_prompt"
    assert record["origin"] == {"kind": "user", "ref": "chat-turn-1"}
    assert record["session_ref"] == "session-1"
    assert record["tags"] == ["guideline-candidate"]
    assert run_cli(context, "review-context").returncode == 0


def test_record_feedback_creates_source_and_debt(tmp_path: Path) -> None:
    context = bootstrap_context(tmp_path)

    result = run_cli(
        context,
        "record-feedback",
        "--scope",
        "tep.plugin",
        "--kind",
        "false-positive",
        "--surface",
        "hook",
        "--severity",
        "high",
        "--title",
        "Read-only command was blocked",
        "--actual",
        "The hook classified rg as a mutating write.",
        "--expected",
        "Read-only search should pass without strictness escalation.",
        "--repro",
        "Run rg over plugin docs.",
        "--suggestion",
        "Classify shell commands by parsed operation, not path substrings.",
        "--origin-ref",
        "beta-agent-report",
        "--created-by",
        "beta-agent",
    )
    assert "Recorded source SRC-" in result.stdout
    debt_id = recorded_id(result, "feedback debt")
    debt = load_record(context, "debt", debt_id)

    assert debt["title"] == "[feedback:false-positive] Read-only command was blocked"
    assert debt["priority"] == "high"
    assert debt["evidence_refs"][0].startswith("SRC-")
    assert "feedback:false-positive" in debt["tags"]
    assert "surface:hook" in debt["tags"]
    assert "Read-only search should pass" in debt["note"]
    source = load_record(context, "source", debt["evidence_refs"][0])
    assert source["source_kind"] == "memory"
    assert source["origin"] == {"kind": "agent-feedback", "ref": "beta-agent-report"}
    assert run_cli(context, "review-context").returncode == 0


def test_claim_lifecycle_pushes_resolved_claims_to_fallback_retrieval(tmp_path: Path) -> None:
    context = bootstrap_context(tmp_path)

    old_source_id = recorded_id(
        run_cli(
            context,
            "record-source",
            "--scope",
            "smartpick.gateway",
            "--source-kind",
            "runtime",
            "--critique-status",
            "accepted",
            "--origin-kind",
            "command",
            "--origin-ref",
            "pytest old failure",
            "--quote",
            "The smartpick browser-use gateway blocker reproduced.",
            "--note",
            "old runtime source",
        ),
        "source",
    )
    old_claim_id = recorded_id(
        run_cli(
            context,
            "record-claim",
            "--scope",
            "smartpick.gateway",
            "--plane",
            "runtime",
            "--status",
            "corroborated",
            "--statement",
            "The smartpick browser-use gateway blocker reproduced.",
            "--source",
            old_source_id,
            "--comparison-key",
            "smartpick.browser-use-gateway-blocker-reproduces",
            "--comparison-subject",
            "smartpick flow",
            "--comparison-aspect",
            "browser-use gateway blocker reproduces",
            "--comparison-comparator",
            "boolean",
            "--comparison-value",
            "true",
            "--comparison-polarity",
            "affirmed",
            "--note",
            "old supported runtime claim",
        ),
        "claim",
    )

    current_source_id = recorded_id(
        run_cli(
            context,
            "record-source",
            "--scope",
            "smartpick.gateway",
            "--source-kind",
            "runtime",
            "--critique-status",
            "accepted",
            "--origin-kind",
            "command",
            "--origin-ref",
            "pytest current check",
            "--quote",
            "The smartpick browser-use gateway blocker no longer reproduces.",
            "--note",
            "current runtime source",
        ),
        "source",
    )
    current_claim_id = recorded_id(
        run_cli(
            context,
            "record-claim",
            "--scope",
            "smartpick.gateway",
            "--plane",
            "runtime",
            "--status",
            "supported",
            "--statement",
            "The smartpick browser-use gateway blocker no longer reproduces.",
            "--source",
            current_source_id,
            "--comparison-key",
            "smartpick.browser-use-gateway-blocker-reproduces",
            "--comparison-subject",
            "smartpick flow",
            "--comparison-aspect",
            "browser-use gateway blocker reproduces",
            "--comparison-comparator",
            "boolean",
            "--comparison-value",
            "false",
            "--comparison-polarity",
            "affirmed",
            "--note",
            "current supported runtime claim",
        ),
        "claim",
    )

    conflict_before = run_cli(context, "scan-conflicts").stdout
    assert "comparable claims disagree" in (context / "review" / "conflicts.md").read_text(encoding="utf-8")
    assert "conflict issue" in conflict_before

    run_cli(
        context,
        "resolve-claim",
        "--claim",
        old_claim_id,
        "--resolved-by-claim",
        current_claim_id,
        "--reactivate-when",
        "the browser-use gateway blocker reproduces again in current runtime",
        "--note",
        "The old blocker claim was correct historically, but current runtime says it no longer reproduces.",
    )
    old_claim = load_record(context, "claim", old_claim_id)
    assert old_claim["status"] == "corroborated"
    assert old_claim["lifecycle"]["state"] == "resolved"
    assert old_claim["lifecycle"]["attention"] == "fallback-only"
    assert old_claim["lifecycle"]["resolved_by_claim_refs"] == [current_claim_id]

    review = run_cli(context, "review-context").stdout
    assert "Reviewed context:" in review
    assert "comparable claims disagree" not in (context / "review" / "conflicts.md").read_text(encoding="utf-8")

    brief = run_cli(context, "brief-context", "--task", "smartpick browser-use gateway blocker", "--detail", "full").stdout
    candidate_section = brief.split("## Candidate Facts", 1)[1].split("## Fallback Historical Facts", 1)[0]
    fallback_section = brief.split("## Fallback Historical Facts", 1)[1].split("## Active Hypotheses", 1)[0]
    assert current_claim_id in candidate_section
    assert old_claim_id not in candidate_section
    assert old_claim_id in fallback_section

    attention = (context / "review" / "attention.md").read_text(encoding="utf-8")
    recent_section = attention.split("## Recent Claims", 1)[1].split("## Recent Models And Flows", 1)[0]
    fallback_attention = attention.split("## Fallback Historical Claims", 1)[1]
    assert old_claim_id not in recent_section
    assert old_claim_id in fallback_attention
    resolved_view = (context / "review" / "resolved.md").read_text(encoding="utf-8")
    assert old_claim_id in resolved_view

    show = run_cli(context, "show-claim-lifecycle", "--claim", old_claim_id).stdout
    assert "lifecycle.state: resolved" in show
    assert current_claim_id in show

    chain = tmp_path / "fallback-chain.json"
    chain.write_text(
        json.dumps(
            {
                "nodes": [
                    {
                        "role": "fact",
                        "ref": old_claim_id,
                        "quote": "smartpick browser-use gateway blocker reproduced",
                    },
                    {
                        "role": "requested_permission",
                        "ref": "REQ-test",
                        "quote": "permission to act on old blocker",
                    },
                ],
                "edges": [{"from": old_claim_id, "to": "REQ-test"}],
            }
        ),
        encoding="utf-8",
    )
    chain_result = run_cli(context, "validate-evidence-chain", "--file", str(chain), check=False)
    assert chain_result.returncode == 1
    assert "fallback/archived" in chain_result.stdout

    blocked_action = run_cli(
        context,
        "record-action",
        "--kind",
        "probe",
        "--scope",
        "smartpick.gateway",
        "--justify",
        old_claim_id,
        "--safety-class",
        "guarded",
        "--status",
        "planned",
        "--note",
        "new action must not rely on resolved old blocker",
        check=False,
    )
    assert blocked_action.returncode == 1
    assert "lifecycle fallback/archived" in blocked_action.stdout

    historical_action = context / "records" / "action" / "ACT-20260416-9999.json"
    historical_action.write_text(
        json.dumps(
            {
                "id": "ACT-20260416-9999",
                "record_type": "action",
                "kind": "probe",
                "safety_class": "safe",
                "scope": "smartpick.gateway",
                "justified_by": [old_claim_id],
                "project_refs": [],
                "task_refs": [],
                "planned_at": "2026-04-16T00:00:00+03:00",
                "status": "planned",
                "tags": [],
                "note": "historical action before the claim was resolved remains valid",
            }
        ),
        encoding="utf-8",
    )
    assert run_cli(context, "review-context").returncode == 0

    blocked_model = run_cli(
        context,
        "record-model",
        "--knowledge-class",
        "domain",
        "--domain",
        "smartpick",
        "--scope",
        "smartpick.gateway",
        "--aspect",
        "gateway blocker",
        "--status",
        "stable",
        "--summary",
        "Stable current model must not depend on a resolved historical claim.",
        "--claim",
        old_claim_id,
        "--note",
        "resolved claims cannot anchor stable models",
        check=False,
    )
    assert blocked_model.returncode == 1
    assert "lifecycle fallback claim" in blocked_model.stdout

    run_cli(context, "archive-claim", "--claim", old_claim_id, "--note", "audit-only after repeated no-repro checks")
    brief_after_archive = run_cli(
        context, "brief-context", "--task", "smartpick browser-use gateway blocker", "--detail", "full"
    ).stdout
    fallback_after_archive = brief_after_archive.split("## Fallback Historical Facts", 1)[1].split("## Active Hypotheses", 1)[0]
    assert old_claim_id not in fallback_after_archive
    assert "lifecycle.state: archived" in run_cli(context, "show-claim-lifecycle", "--claim", old_claim_id).stdout
    reasoning = run_cli(context, "build-reasoning-case", "--task", "audit old blocker", "--claim", old_claim_id).stdout
    assert old_claim_id in reasoning
    assert "lifecycle fallback/archived claims are background or audit context only" in reasoning

    run_cli(context, "restore-claim", "--claim", old_claim_id, "--note", "reopened for explicit investigation")
    restored = load_record(context, "claim", old_claim_id)
    assert restored["lifecycle"]["state"] == "active"
    assert restored["lifecycle"]["attention"] == "normal"
    assert "resolved_at" not in restored["lifecycle"]
    assert "resolved_by_claim_refs" not in restored["lifecycle"]


def test_active_hypothesis_entries_cannot_point_to_lifecycle_fallback_claims(tmp_path: Path) -> None:
    context = bootstrap_context(tmp_path)

    source_id = recorded_id(
        run_cli(
            context,
            "record-source",
            "--scope",
            "hypothesis.lifecycle",
            "--source-kind",
            "runtime",
            "--critique-status",
            "accepted",
            "--origin-kind",
            "command",
            "--origin-ref",
            "pytest tentative",
            "--quote",
            "The tentative lifecycle hypothesis was observed during exploration.",
            "--note",
            "tentative source",
        ),
        "source",
    )
    claim_id = recorded_id(
        run_cli(
            context,
            "record-claim",
            "--scope",
            "hypothesis.lifecycle",
            "--plane",
            "runtime",
            "--status",
            "tentative",
            "--statement",
            "The tentative lifecycle hypothesis was observed during exploration.",
            "--source",
            source_id,
            "--note",
            "tentative claim",
        ),
        "claim",
    )

    run_cli(context, "hypothesis", "add", "--claim", claim_id, "--note", "active tentative hypothesis")
    blocked_resolve = run_cli(
        context,
        "resolve-claim",
        "--claim",
        claim_id,
        "--note",
        "cannot resolve while active hypothesis index still points here",
        check=False,
    )
    assert blocked_resolve.returncode == 1
    assert "active hypothesis index may reference only active lifecycle claims" in blocked_resolve.stdout

    run_cli(context, "hypothesis", "close", "--claim", claim_id, "--status", "abandoned", "--note", "no longer active")
    run_cli(
        context,
        "resolve-claim",
        "--claim",
        claim_id,
        "--note",
        "closed hypothesis can become fallback historical context",
    )
    resolved = load_record(context, "claim", claim_id)
    assert resolved["lifecycle"]["state"] == "resolved"
    assert run_cli(context, "review-context").returncode == 0


def test_linked_records_returns_incoming_and_outgoing_edges_for_any_record(tmp_path: Path) -> None:
    context = bootstrap_context(tmp_path)

    source_id = recorded_id(
        run_cli(
            context,
            "record-source",
            "--scope",
            "linked.demo",
            "--source-kind",
            "runtime",
            "--critique-status",
            "accepted",
            "--origin-kind",
            "command",
            "--origin-ref",
            "pytest linked records",
            "--quote",
            "Linked records should expose incoming and outgoing edges.",
            "--note",
            "linked source",
        ),
        "source",
    )
    claim_id = recorded_id(
        run_cli(
            context,
            "record-claim",
            "--scope",
            "linked.demo",
            "--plane",
            "runtime",
            "--status",
            "supported",
            "--statement",
            "Linked records should expose incoming and outgoing edges.",
            "--source",
            source_id,
            "--note",
            "linked claim",
        ),
        "claim",
    )
    guideline_id = recorded_id(
        run_cli(
            context,
            "record-guideline",
            "--scope",
            "linked.demo",
            "--domain",
            "agent-behavior",
            "--applies-to",
            "global",
            "--priority",
            "preferred",
            "--rule",
            "Use linked-records before changing records that have unknown dependents.",
            "--source",
            source_id,
            "--related-claim",
            claim_id,
            "--note",
            "linked guideline",
        ),
        "guideline",
    )
    started_task = run_cli(
        context,
        "start-task",
        "--scope",
        "linked.demo",
        "--title",
        "Linked record traversal",
        "--related-claim",
        claim_id,
        "--note",
        "linked task",
    )
    task_match = re.search(r"(TASK-\d{8}-[0-9a-f]{8})", started_task.stdout)
    assert task_match, started_task.stdout
    task_id = task_match.group(1)

    text = run_cli(context, "linked-records", "--record", claim_id).stdout
    assert "Direct Outgoing" in text
    assert source_id in text
    assert "source_refs" in text
    assert "Direct Incoming" in text
    assert guideline_id in text
    assert "related_claim_refs" in text
    assert task_id in text

    payload = json.loads(
        run_cli(context, "linked-records", "--record", claim_id, "--direction", "both", "--depth", "2", "--format", "json").stdout
    )
    assert payload["anchor"]["id"] == claim_id
    edge_pairs = {(edge["from"], edge["to"]) for edge in payload["edges"]}
    assert (claim_id, source_id) in edge_pairs
    assert (guideline_id, claim_id) in edge_pairs
    assert (task_id, claim_id) in edge_pairs
    linked_ids = {record["id"] for record in payload["records"]}
    assert {source_id, guideline_id, task_id}.issubset(linked_ids)


def test_runtime_help_budget_task_modes_and_precedents(tmp_path: Path) -> None:
    context = bootstrap_context(tmp_path)

    help_text = run_cli(context, "help", "modes").stdout
    assert "precedent review" in help_text
    assert "task control" in help_text
    assert "--format json route_graph" in help_text

    alias_text = run_cli(context, "tep-help", "modes").stdout
    assert alias_text == help_text

    commands_help = run_cli(context, "help", "commands").stdout
    assert "next-step --intent answer|plan|edit|test|persist|permission|debug --task ... [--format json]" in commands_help
    assert "backend-status [--format json] | backend-check --backend derivation.datalog [--format json]" in commands_help
    assert "validate-facts --backend rdf_shacl [--format json]" in commands_help
    assert "export-rdf --format turtle|jsonld [--output path]" in commands_help

    configured = run_cli(
        context,
        "configure-runtime",
        "--hook-verbosity",
        "quiet",
        "--context-budget",
        "hydration=compact",
        "--context-budget",
        "brief=compact",
        "--analysis",
        "logic_solver.backend=z3",
        "--analysis",
        "logic_solver.install_policy=ask",
        "--analysis",
        "topic_prefilter.backend=nmf",
        "--analysis",
        "topic_prefilter.rebuild=manual",
        "--backend",
        "derivation.backend=datalog",
        "--backend",
        "derivation.datalog.enabled=true",
        "--backend",
        "derivation.datalog.mode=fake",
    ).stdout
    assert "hooks.verbosity=quiet" in configured
    assert "analysis.logic_solver.backend=z3" in configured
    assert "analysis.topic_prefilter.backend=nmf" in configured
    assert "backends.derivation.backend=datalog" in configured
    assert "backends.derivation.datalog.enabled=true" in configured
    settings = json.loads((context / "settings.json").read_text(encoding="utf-8"))
    assert settings["hooks"]["verbosity"] == "quiet"
    assert settings["context_budget"]["hydration"] == "compact"
    assert settings["analysis"]["logic_solver"]["backend"] == "z3"
    assert settings["analysis"]["logic_solver"]["install_policy"] == "ask"
    assert settings["analysis"]["topic_prefilter"]["backend"] == "nmf"
    assert settings["analysis"]["topic_prefilter"]["rebuild"] == "manual"
    assert settings["backends"]["derivation"]["backend"] == "datalog"
    assert settings["backends"]["derivation"]["datalog"]["enabled"] is True
    assert settings["backends"]["derivation"]["datalog"]["mode"] == "fake"

    invalid_analysis = run_cli(context, "configure-runtime", "--analysis", "logic_solver.backend=bad", check=False)
    assert invalid_analysis.returncode == 1
    assert "invalid value for analysis.logic_solver.backend" in invalid_analysis.stdout
    invalid_backend = run_cli(context, "configure-runtime", "--backend", "code_intelligence.backend=ctags", check=False)
    assert invalid_backend.returncode == 1
    assert "backends.code_intelligence.backend has invalid value" in invalid_backend.stdout

    status_payload = json.loads(run_cli(context, "backend-status", "--format", "json").stdout)
    assert status_payload["backend_status_is_proof"] is False
    assert status_payload["groups"]["derivation"]["selected"] == "datalog"
    assert any(item["id"] == "datalog" and item["available"] is True for item in status_payload["backends"])
    check_payload = json.loads(
        run_cli(context, "backend-check", "--backend", "derivation.datalog", "--format", "json").stdout
    )
    assert check_payload["backend_status_is_proof"] is False
    assert check_payload["matches"][0]["backend_output_is_proof"] is False
    telemetry = json.loads(run_cli(context, "telemetry-report", "--format", "json").stdout)
    assert telemetry["by_tool"]["backend-status"] >= 1
    assert telemetry["by_tool"]["backend-check"] >= 1
    assert telemetry["by_access_kind"]["backend_status"] >= 1
    assert telemetry["by_access_kind"]["backend_check"] >= 1

    first = run_cli(
        context,
        "start-task",
        "--type",
        "investigation",
        "--scope",
        "prompt.retry",
        "--title",
        "Investigate prompt retry behavior",
        "--note",
        "first investigation precedent",
    )
    first_id = re.search(r"(TASK-\d{8}-[0-9a-f]{8})", first.stdout).group(1)
    assert load_record(context, "task", first_id)["task_type"] == "investigation"

    drift = run_cli(
        context,
        "task-drift-check",
        "--intent",
        "Investigate prompt retry failure",
        "--type",
        "investigation",
    ).stdout
    assert "alignment=aligned" in drift

    run_cli(context, "complete-task", "--note", "investigation completed")
    second = run_cli(
        context,
        "start-task",
        "--type",
        "investigation",
        "--scope",
        "prompt.retry",
        "--title",
        "Investigate prompt retry regression",
        "--note",
        "second investigation",
    )
    second_id = re.search(r"(TASK-\d{8}-[0-9a-f]{8})", second.stdout).group(1)
    precedents = run_cli(context, "review-precedents", "--query", "prompt retry").stdout
    assert first_id in precedents
    assert "task_type=`investigation`" in precedents

    drifted = run_cli(
        context,
        "task-drift-check",
        "--intent",
        "Implement prompt retry fix",
        "--type",
        "implementation",
    ).stdout
    assert "alignment=drifted" in drifted

    run_cli(context, "pause-task", "--note", "pause investigation")
    assert load_record(context, "task", second_id)["status"] == "paused"
    run_cli(context, "resume-task", "--task", second_id, "--note", "resume investigation")
    assert load_record(context, "task", second_id)["status"] == "active"
    run_cli(context, "pause-task", "--note", "prepare switch test")
    third = run_cli(
        context,
        "start-task",
        "--type",
        "implementation",
        "--scope",
        "prompt.retry",
        "--title",
        "Implement prompt retry fix",
        "--note",
        "implementation task",
    )
    third_id = re.search(r"(TASK-\d{8}-[0-9a-f]{8})", third.stdout).group(1)
    switched = run_cli(context, "switch-task", "--task", second_id, "--note", "return to investigation").stdout
    assert f"Paused task {third_id}" in switched
    assert f"Switched current task to {second_id}" in switched
    assert load_record(context, "task", third_id)["status"] == "paused"
    assert load_record(context, "task", second_id)["status"] == "active"


def test_validate_facts_fake_backend_reports_candidates_and_telemetry(tmp_path: Path) -> None:
    context = bootstrap_context(tmp_path)
    run_cli(
        context,
        "configure-runtime",
        "--backend",
        "fact_validation.backend=rdf_shacl",
        "--backend",
        "fact_validation.rdf_shacl.enabled=true",
        "--backend",
        "fact_validation.rdf_shacl.mode=fake",
    )
    source_id = recorded_id(
        run_cli(
            context,
            "record-source",
            "--scope",
            "demo.fact-validation",
            "--source-kind",
            "runtime",
            "--critique-status",
            "accepted",
            "--origin-kind",
            "command",
            "--origin-ref",
            "unit",
            "--quote",
            "runtime fact source",
            "--note",
            "runtime source",
        ),
        "source",
    )
    claim_id = recorded_id(
        run_cli(
            context,
            "record-claim",
            "--scope",
            "demo.fact-validation",
            "--plane",
            "runtime",
            "--status",
            "supported",
            "--statement",
            "Supported claim initially has a source.",
            "--source",
            source_id,
            "--note",
            "supported claim",
        ),
        "claim",
    )
    claim_path = context / "records" / "claim" / f"{claim_id}.json"
    claim = json.loads(claim_path.read_text(encoding="utf-8"))
    claim["source_refs"] = []
    claim_path.write_text(json.dumps(claim, indent=2, ensure_ascii=False), encoding="utf-8")

    payload = json.loads(run_cli(context, "validate-facts", "--backend", "rdf_shacl", "--format", "json").stdout)
    assert payload["validation_is_proof"] is False
    assert payload["backend_output_is_proof"] is False
    assert payload["candidate_count"] >= 1
    assert payload["candidates"][0]["candidate_is_proof"] is False
    assert any(candidate["shape_ref"] == "tep:SupportedClaimHasSource" for candidate in payload["candidates"])
    text = run_cli(context, "validate-facts", "--backend", "rdf_shacl").stdout
    assert "Validation output is diagnostic/navigation data only" in text
    telemetry = json.loads(run_cli(context, "telemetry-report", "--format", "json").stdout)
    assert telemetry["by_tool"]["validate-facts"] >= 2
    assert telemetry["by_access_kind"]["backend_validation"] >= 2

    turtle_output = tmp_path / "tep.ttl"
    exported = run_cli(context, "export-rdf", "--format", "turtle", "--output", str(turtle_output)).stdout
    assert "Exported RDF projection" in exported
    turtle = turtle_output.read_text(encoding="utf-8")
    assert "# export_is_proof=false" in turtle
    assert f"<urn:tep:record:{claim_id}>" in turtle
    jsonld_payload = json.loads(run_cli(context, "export-rdf", "--format", "jsonld").stdout)
    assert jsonld_payload["export_is_proof"] is False
    telemetry = json.loads(run_cli(context, "telemetry-report", "--format", "json").stdout)
    assert telemetry["by_tool"]["export-rdf"] >= 2
    assert telemetry["by_access_kind"]["backend_export"] >= 2


def test_search_records_finds_keywords_before_expanding_links(tmp_path: Path) -> None:
    context = bootstrap_context(tmp_path)

    source_id = recorded_id(
        run_cli(
            context,
            "record-source",
            "--scope",
            "search.demo",
            "--source-kind",
            "runtime",
            "--critique-status",
            "accepted",
            "--origin-kind",
            "command",
            "--origin-ref",
            "pytest search records",
            "--quote",
            "Keyword search should find the active gateway record.",
            "--note",
            "search source",
        ),
        "source",
    )
    active_claim_id = recorded_id(
        run_cli(
            context,
            "record-claim",
            "--scope",
            "search.demo",
            "--plane",
            "runtime",
            "--status",
            "supported",
            "--statement",
            "Keyword search should find the active gateway record.",
            "--source",
            source_id,
            "--note",
            "active gateway search claim",
        ),
        "claim",
    )
    fallback_claim_id = recorded_id(
        run_cli(
            context,
            "record-claim",
            "--scope",
            "search.demo",
            "--plane",
            "runtime",
            "--status",
            "supported",
            "--statement",
            "Keyword search should hide the historical gateway record by default.",
            "--source",
            source_id,
            "--note",
            "historical gateway search claim",
        ),
        "claim",
    )
    run_cli(
        context,
        "resolve-claim",
        "--claim",
        fallback_claim_id,
        "--resolved-by-claim",
        active_claim_id,
        "--note",
        "fallback search fixture",
    )

    default_search = run_cli(context, "search-records", "--query", "gateway search", "--type", "claim").stdout
    assert active_claim_id in default_search
    assert fallback_claim_id not in default_search

    fallback_search = run_cli(
        context,
        "search-records",
        "--query",
        "gateway search",
        "--type",
        "claim",
        "--include-fallback",
    ).stdout
    assert active_claim_id in fallback_search
    assert fallback_claim_id in fallback_search
    assert "lifecycle=`resolved`" in fallback_search

    payload = json.loads(
        run_cli(
            context,
            "search-records",
            "--query",
            "gateway search",
            "--type",
            "claim",
            "--include-fallback",
            "--format",
            "json",
        ).stdout
    )
    result_ids = [item["id"] for item in payload["results"]]
    assert active_claim_id in result_ids
    assert fallback_claim_id in result_ids
    assert payload["terms"] == ["gateway", "search"]

    graph_text = run_cli(context, "claim-graph", "--query", "gateway search").stdout
    assert "# Claim Graph" in graph_text
    assert "Navigation only, not proof" in graph_text
    assert active_claim_id in graph_text
    assert fallback_claim_id not in graph_text

    graph_payload = json.loads(
        run_cli(context, "claim-graph", "--query", "gateway search", "--format", "json").stdout
    )
    anchor_ids = [item["id"] for item in graph_payload["anchors"]]
    linked_ids = [item["id"] for item in graph_payload["records"]]
    assert graph_payload["claim_graph_is_proof"] is False
    assert active_claim_id in anchor_ids
    assert fallback_claim_id not in anchor_ids
    assert source_id in linked_ids
    assert {
        "from": active_claim_id,
        "to": source_id,
        "fields": ["source_refs"],
    } in graph_payload["edges"]

    fallback_graph = json.loads(
        run_cli(
            context,
            "claim-graph",
            "--query",
            "gateway search",
            "--include-fallback",
            "--format",
            "json",
        ).stdout
    )
    fallback_anchor_ids = [item["id"] for item in fallback_graph["anchors"]]
    assert fallback_claim_id in fallback_anchor_ids

    telemetry = json.loads(run_cli(context, "telemetry-report", "--format", "json").stdout)
    assert telemetry["telemetry_is_proof"] is False
    assert telemetry["by_tool"]["search-records"] >= 3
    assert telemetry["by_tool"]["claim-graph"] >= 3
    assert telemetry["raw_event_count"] == 0
    assert active_claim_id in [item["record_ref"] for item in telemetry["top_records"]]


def test_topic_index_builds_searchable_prefilter_and_candidate_report(tmp_path: Path) -> None:
    context = bootstrap_context(tmp_path)

    source_id = recorded_id(
        run_cli(
            context,
            "record-source",
            "--scope",
            "topic.demo",
            "--source-kind",
            "runtime",
            "--critique-status",
            "accepted",
            "--origin-kind",
            "command",
            "--origin-ref",
            "pytest topic index",
            "--quote",
            "Gateway retry backoff behavior was observed.",
            "--note",
            "topic source",
        ),
        "source",
    )
    first_claim_id = recorded_id(
        run_cli(
            context,
            "record-claim",
            "--scope",
            "topic.demo",
            "--plane",
            "runtime",
            "--status",
            "supported",
            "--statement",
            "Gateway retry returns 200 after backoff.",
            "--source",
            source_id,
            "--note",
            "first topic claim",
        ),
        "claim",
    )
    second_claim_id = recorded_id(
        run_cli(
            context,
            "record-claim",
            "--scope",
            "topic.demo",
            "--plane",
            "runtime",
            "--status",
            "supported",
            "--statement",
            "Gateway retry returns an error after backoff.",
            "--source",
            source_id,
            "--note",
            "second topic claim",
        ),
        "claim",
    )

    built = run_cli(context, "topic-index", "build", "--method", "lexical").stdout
    assert "Built lexical topic index" in built
    assert "not proof" in built
    assert (context / "topic_index" / "records.json").exists()
    assert (context / "topic_index" / "conflict_candidates.md").exists()

    search = run_cli(context, "topic-search", "--query", "gateway retry", "--type", "claim").stdout
    assert first_claim_id in search
    assert second_claim_id in search
    assert "navigation candidates, not proof" in search

    info_payload = json.loads(run_cli(context, "topic-info", "--record", first_claim_id, "--format", "json").stdout)
    assert info_payload["topic_index_is_proof"] is False
    assert any(item["id"] == second_claim_id for item in info_payload["similar"])

    candidates = run_cli(context, "topic-conflict-candidates").stdout
    assert first_claim_id in candidates
    assert second_claim_id in candidates
    assert "Candidates require normal claim comparison" in candidates


def test_attention_index_tracks_taps_and_generates_curiosity_probes(tmp_path: Path) -> None:
    context = bootstrap_context(tmp_path)

    source_id = recorded_id(
        run_cli(
            context,
            "record-source",
            "--scope",
            "attention.demo",
            "--source-kind",
            "runtime",
            "--critique-status",
            "accepted",
            "--origin-kind",
            "command",
            "--origin-ref",
            "pytest attention index",
            "--quote",
            "Attention map inputs are test records.",
            "--note",
            "attention source",
        ),
        "source",
    )
    tapped_claim_id = recorded_id(
        run_cli(
            context,
            "record-claim",
            "--scope",
            "attention.demo",
            "--plane",
            "runtime",
            "--status",
            "supported",
            "--statement",
            "Gateway retry is inspected by the agent.",
            "--source",
            source_id,
            "--note",
            "tapped claim",
        ),
        "claim",
    )
    facility_claim_id = recorded_id(
        run_cli(
            context,
            "record-claim",
            "--scope",
            "attention.demo",
            "--plane",
            "runtime",
            "--status",
            "supported",
            "--statement",
            "Facility inventory reaches Program marketplace listings.",
            "--source",
            source_id,
            "--note",
            "facility claim",
        ),
        "claim",
    )
    program_claim_id = recorded_id(
        run_cli(
            context,
            "record-claim",
            "--scope",
            "attention.demo",
            "--plane",
            "runtime",
            "--status",
            "supported",
            "--statement",
            "Program marketplace listings imply Facility inventory dependency.",
            "--source",
            source_id,
            "--note",
            "program claim",
        ),
        "claim",
    )

    tap = run_cli(context, "tap-record", "--record", tapped_claim_id, "--kind", "cited", "--intent", "support")
    assert "not proof" in tap.stdout
    run_cli(context, "record-detail", "--record", tapped_claim_id)

    built = run_cli(context, "attention-index", "build", "--probe-limit", "10").stdout
    assert "Built attention index" in built
    assert "access_events=1" in built
    assert "not proof" in built
    assert (context / "activity" / "taps.jsonl").exists()
    assert (context / "attention_index" / "records.json").exists()
    assert (context / "attention_index" / "probes.json").exists()

    records_payload = json.loads((context / "attention_index" / "records.json").read_text(encoding="utf-8"))
    assert records_payload[tapped_claim_id]["tap_count"] == 1
    assert records_payload[tapped_claim_id]["access_count"] == 1
    assert records_payload[tapped_claim_id]["attention_index_is_proof"] is False

    map_text = run_cli(context, "attention-map").stdout
    assert "Not proof" in map_text
    assert "taps: `1`" in map_text
    assert "access_events: `1`" in map_text
    diagram_text = run_cli(context, "attention-diagram", "--limit", "3").stdout
    assert "# Attention Diagram" in diagram_text
    assert "```mermaid" in diagram_text
    assert "Not proof" in diagram_text
    assert "graph TD" in diagram_text
    assert "detail: `compact`" in diagram_text
    assert "omitted=`record_summaries`" in diagram_text
    diagram_compare = json.loads(
        run_cli(context, "attention-diagram-compare", "--limit", "3", "--scope", "all", "--format", "json").stdout
    )
    assert diagram_compare["comparison_is_proof"] is False
    assert diagram_compare["metrics_are_proof"] is False
    assert diagram_compare["compact"]["omitted_fields"] == ["record_summaries"]
    assert diagram_compare["full"]["omitted_fields"] == []
    assert diagram_compare["delta"]["payload_char_count"] > 0
    probes_payload = json.loads(run_cli(context, "curiosity-probes", "--budget", "10", "--format", "json").stdout)
    assert probes_payload["attention_index_is_proof"] is False
    assert all(ref.startswith("CLM-") for probe in probes_payload["probes"] for ref in probe["record_refs"])
    assert all(probe["score_is_proof"] is False for probe in probes_payload["probes"])
    assert all(probe["score"] > 0 for probe in probes_payload["probes"])
    assert all("navigation_only=true" in probe["explanation"] for probe in probes_payload["probes"])
    assert len({tuple(sorted(probe["record_refs"])) for probe in probes_payload["probes"]}) == len(probes_payload["probes"])
    assert any(
        {facility_claim_id, program_claim_id}.issubset(set(probe["record_refs"]))
        for probe in probes_payload["probes"]
    )
    inspection = json.loads(run_cli(context, "probe-inspect", "--index", "1", "--scope", "all", "--format", "json").stdout)
    assert inspection["inspection_is_proof"] is False
    assert inspection["probe"]["score_is_proof"] is False
    assert inspection["direct_edges"] == []
    assert inspection["record_details"]
    assert any(command.startswith("record-detail --record") for command in inspection["suggested_commands"])
    draft = json.loads(run_cli(context, "probe-chain-draft", "--index", "1", "--scope", "all", "--format", "json").stdout)
    assert draft["draft_is_proof"] is False
    assert draft["chain"]["draft_is_proof"] is False
    assert draft["augmented"]["validation"]["ok"] is True
    assert draft["chain"]["nodes"][0]["role"] == "fact"
    assert {facility_claim_id, program_claim_id} == {node["ref"] for node in draft["chain"]["nodes"]}
    route = json.loads(run_cli(context, "probe-route", "--index", "1", "--scope", "all", "--format", "json").stdout)
    assert route["route_is_proof"] is False
    assert route["chain_validation"]["ok"] is True
    assert route["record_refs"]
    assert route["diagram_delta"]["payload_char_count"] > 0
    assert any(command.startswith("probe-inspect --index 1") for command in route["recommended_commands"])
    assert any(command.startswith("attention-diagram-compare") for command in route["recommended_commands"])
    assert any(command.startswith("probe-chain-draft --index 1") for command in route["recommended_commands"])
    assert any(command.startswith("probe-pack-compare") for command in route["recommended_commands"])
    assert route["context_delta"]["payload_char_count"] > 0
    pack = json.loads(run_cli(context, "probe-pack", "--budget", "2", "--scope", "all", "--format", "json").stdout)
    assert pack["pack_is_proof"] is False
    assert pack["detail"] == "compact"
    assert pack["metrics"]["metrics_are_proof"] is False
    assert pack["metrics"]["detail"] == "compact"
    assert pack["metrics"]["returned_items"] == len(pack["items"])
    assert pack["metrics"]["source_quote_count"] == 0
    assert pack["metrics"]["chain_node_count"] == 0
    assert pack["metrics"]["omitted_fields"] == ["source_quotes", "chain"]
    assert pack["metrics"]["payload_char_count"] > 0
    assert pack["items"]
    assert pack["items"][0]["chain_validation"]["ok"] is True
    assert "source_quotes" not in pack["items"][0]
    assert "chain" not in pack["items"][0]
    assert {facility_claim_id, program_claim_id}.issubset(
        {record["id"] for item in pack["items"] for record in item["records"]}
    )
    full_pack = json.loads(
        run_cli(context, "probe-pack", "--budget", "1", "--scope", "all", "--detail", "full", "--format", "json").stdout
    )
    assert full_pack["detail"] == "full"
    assert full_pack["metrics"]["detail"] == "full"
    assert full_pack["metrics"]["source_quote_count"] > 0
    assert full_pack["metrics"]["chain_node_count"] > 0
    assert full_pack["metrics"]["omitted_fields"] == []
    assert "source_quotes" in full_pack["items"][0]
    assert "chain" in full_pack["items"][0]
    comparison = json.loads(
        run_cli(context, "probe-pack-compare", "--budget", "1", "--scope", "all", "--format", "json").stdout
    )
    assert comparison["comparison_is_proof"] is False
    assert comparison["metrics_are_proof"] is False
    assert comparison["compact"]["detail"] == "compact"
    assert comparison["full"]["detail"] == "full"
    assert comparison["delta"]["payload_char_count"] > 0
    assert comparison["delta"]["source_quote_count"] > 0
    assert comparison["delta"]["chain_node_count"] > 0
    assert comparison["delta"]["omitted_fields_compact"] == ["source_quotes", "chain"]


def test_attention_output_defaults_to_current_project_scope(tmp_path: Path) -> None:
    context = bootstrap_context(tmp_path)

    workspace_id = recorded_id(
        run_cli(
            context,
            "record-workspace",
            "--workspace-key",
            "attention-scope",
            "--title",
            "Attention Scope Workspace",
            "--root-ref",
            "/tmp/attention-scope",
            "--note",
            "attention scope workspace",
        ),
        "workspace",
    )
    run_cli(context, "set-current-workspace", "--workspace", workspace_id)
    current_project_id = recorded_id(
        run_cli(
            context,
            "record-project",
            "--project-key",
            "current-scope",
            "--title",
            "Current Scope",
            "--root-ref",
            "/tmp/current-scope",
            "--note",
            "current project",
        ),
        "project",
    )
    other_project_id = recorded_id(
        run_cli(
            context,
            "record-project",
            "--project-key",
            "other-scope",
            "--title",
            "Other Scope",
            "--root-ref",
            "/tmp/other-scope",
            "--note",
            "other project",
        ),
        "project",
    )

    run_cli(context, "set-current-project", "--project", current_project_id)
    source_id = recorded_id(
        run_cli(
            context,
            "record-source",
            "--scope",
            "attention.scope",
            "--source-kind",
            "runtime",
            "--critique-status",
            "accepted",
            "--origin-kind",
            "command",
            "--origin-ref",
            "current project observation",
            "--quote",
            "Current project has Facility and Program relation candidates.",
            "--note",
            "current source",
        ),
        "source",
    )
    current_claim_id = recorded_id(
        run_cli(
            context,
            "record-claim",
            "--scope",
            "attention.scope",
            "--plane",
            "runtime",
            "--status",
            "supported",
            "--statement",
            "Current Facility inventory reaches Current Program listings.",
            "--source",
            source_id,
            "--note",
            "current claim",
        ),
        "claim",
    )
    current_pair_id = recorded_id(
        run_cli(
            context,
            "record-claim",
            "--scope",
            "attention.scope",
            "--plane",
            "runtime",
            "--status",
            "supported",
            "--statement",
            "Current Program listings depend on Current Facility inventory.",
            "--source",
            source_id,
            "--note",
            "current pair claim",
        ),
        "claim",
    )

    run_cli(context, "set-current-project", "--project", other_project_id)
    other_source_id = recorded_id(
        run_cli(
            context,
            "record-source",
            "--scope",
            "attention.scope",
            "--source-kind",
            "runtime",
            "--critique-status",
            "accepted",
            "--origin-kind",
            "command",
            "--origin-ref",
            "other project observation",
            "--quote",
            "Other project has Facility and Program relation candidates.",
            "--note",
            "other source",
        ),
        "source",
    )
    other_claim_id = recorded_id(
        run_cli(
            context,
            "record-claim",
            "--scope",
            "attention.scope",
            "--plane",
            "runtime",
            "--status",
            "supported",
            "--statement",
            "Other Facility inventory reaches Other Program listings.",
            "--source",
            other_source_id,
            "--note",
            "other claim",
        ),
        "claim",
    )

    run_cli(context, "set-current-project", "--project", current_project_id)
    run_cli(context, "attention-index", "build", "--probe-limit", "20")

    current_payload = json.loads(run_cli(context, "curiosity-probes", "--budget", "20", "--format", "json").stdout)
    current_refs = {ref for probe in current_payload["probes"] for ref in probe["record_refs"]}
    assert current_payload["attention_index_is_proof"] is False
    assert current_payload["scope"] == "current"
    assert current_payload["probes"]
    assert all(ref.startswith("CLM-") for probe in current_payload["probes"] for ref in probe["record_refs"])
    assert current_claim_id in current_refs
    assert current_pair_id in current_refs
    assert other_claim_id not in current_refs

    inspection_text = run_cli(context, "probe-inspect", "--index", "1").stdout
    assert "Curiosity Probe Inspection" in inspection_text
    assert "no direct canonical link" in inspection_text
    assert "Do not cite this inspection as proof" in inspection_text
    draft_text = run_cli(context, "probe-chain-draft", "--index", "1").stdout
    assert "Probe Evidence-Chain Draft" in draft_text
    assert "Draft is not proof" in draft_text
    pack_text = run_cli(context, "probe-pack", "--budget", "1").stdout
    assert "Curiosity Reasoning Pack" in pack_text
    assert "detail: `compact`" in pack_text
    assert "metrics: returned=`" in pack_text
    assert "pack_is_proof=`False`" in pack_text
    compare_text = run_cli(context, "probe-pack-compare", "--budget", "1").stdout
    assert "# Probe Pack Detail Comparison" in compare_text
    assert "comparison_is_proof=`False`" in compare_text
    assert "Recommendation:" in compare_text
    route_text = run_cli(context, "probe-route", "--index", "1").stdout
    assert "# Probe Inspection Route" in route_text
    assert "route_is_proof=`False`" in route_text
    assert "diagram_delta_if_full" in route_text
    assert "Recommended Commands" in route_text
    route_payload = json.loads(run_cli(context, "probe-route", "--index", "1", "--format", "json").stdout)
    assert route_payload["scope"] == "current"
    assert route_payload["route_is_proof"] is False
    assert current_claim_id in route_payload["record_refs"]
    assert current_pair_id in route_payload["record_refs"]
    assert other_claim_id not in route_payload["record_refs"]
    assert all("--scope current" in command for command in route_payload["recommended_commands"] if "--scope" in command)
    diagram_payload = json.loads(run_cli(context, "attention-diagram", "--limit", "2", "--format", "json").stdout)
    full_diagram_payload = json.loads(
        run_cli(context, "attention-diagram", "--limit", "2", "--detail", "full", "--format", "json").stdout
    )
    assert diagram_payload["diagram_is_proof"] is False
    assert diagram_payload["detail"] == "compact"
    assert diagram_payload["scope"] == "current"
    assert diagram_payload["metrics"]["omitted_fields"] == ["record_summaries"]
    assert full_diagram_payload["detail"] == "full"
    assert full_diagram_payload["metrics"]["omitted_fields"] == []
    assert full_diagram_payload["metrics"]["payload_char_count"] > diagram_payload["metrics"]["payload_char_count"]
    assert "graph TD" in diagram_payload["mermaid"]
    diagram_compare_text = run_cli(context, "attention-diagram-compare", "--limit", "2").stdout
    assert "# Attention Diagram Detail Comparison" in diagram_compare_text
    assert "comparison_is_proof=`False`" in diagram_compare_text
    assert "Recommendation:" in diagram_compare_text

    all_payload = json.loads(run_cli(context, "curiosity-probes", "--budget", "20", "--scope", "all", "--format", "json").stdout)
    all_refs = {ref for probe in all_payload["probes"] for ref in probe["record_refs"]}
    assert all_payload["scope"] == "all"
    assert other_claim_id in all_refs


def test_claim_logic_index_validates_symbols_rules_and_conflict_candidates(tmp_path: Path) -> None:
    context = bootstrap_context(tmp_path)

    source_id = recorded_id(
        run_cli(
            context,
            "record-source",
            "--scope",
            "logic.demo",
            "--source-kind",
            "runtime",
            "--critique-status",
            "accepted",
            "--origin-kind",
            "command",
            "--origin-ref",
            "pytest logic source",
            "--quote",
            "Alice is a student and studies algebra.",
            "--note",
            "logic source",
        ),
        "source",
    )
    first_claim_id = recorded_id(
        run_cli(
            context,
            "record-claim",
            "--scope",
            "logic.demo",
            "--plane",
            "runtime",
            "--status",
            "supported",
            "--statement",
            "Alice is a student and studies algebra.",
            "--source",
            source_id,
            "--logic-symbol",
            "person:alice|entity|Alice introduced by runtime source",
            "--logic-symbol",
            "subject:algebra|concept|Algebra subject used in the study example",
            "--logic-atom",
            "Student|person:alice|affirmed",
            "--logic-atom",
            "Studies|person:alice,subject:algebra|affirmed",
            "--note",
            "logic atom claim",
        ),
        "claim",
    )
    rule_claim_id = recorded_id(
        run_cli(
            context,
            "record-claim",
            "--scope",
            "logic.demo",
            "--plane",
            "theory",
            "--status",
            "supported",
            "--statement",
            "Students who study a subject are expected to pass the related exam.",
            "--source",
            source_id,
            "--logic-rule",
            "student-study-pass|Student(?x)&Studies(?x,?subject)->ExpectedPassesExam(?x,?subject)",
            "--note",
            "logic rule claim",
        ),
        "claim",
    )
    second_claim_id = recorded_id(
        run_cli(
            context,
            "record-claim",
            "--scope",
            "logic.demo",
            "--plane",
            "runtime",
            "--status",
            "supported",
            "--statement",
            "Alice is not a student in the current runtime.",
            "--source",
            source_id,
            "--logic-atom",
            "Student|person:alice|denied",
            "--note",
            "conflicting logic atom claim",
        ),
        "claim",
    )

    built = run_cli(context, "logic-index", "build").stdout
    assert "Built logic index" in built
    assert "CLM-* remains the truth record" in built
    atoms_payload = json.loads((context / "logic_index" / "atoms.json").read_text(encoding="utf-8"))
    assert {item["claim_ref"] for item in atoms_payload} >= {first_claim_id, second_claim_id}
    graph_payload = json.loads((context / "logic_index" / "variable_graph.json").read_text(encoding="utf-8"))
    assert graph_payload["logic_graph_is_proof"] is False
    assert graph_payload["symbols"]["person:alice"]["meanings"] == ["Alice introduced by runtime source"]
    assert "Student" in graph_payload["predicates"]

    search = run_cli(context, "logic-search", "--predicate", "Student").stdout
    assert first_claim_id in search
    assert second_claim_id in search
    assert "Not proof" in search

    graph_search = run_cli(context, "logic-graph", "--symbol", "person:alice", "--format", "json").stdout
    graph_search_payload = json.loads(graph_search)
    assert graph_search_payload["logic_graph_is_proof"] is False
    assert "person:alice" in graph_search_payload["symbols"]

    graph_smells = run_cli(context, "logic-graph", "--smells").stdout
    assert "Logic Vocabulary Graph" in graph_smells

    rule_search = run_cli(context, "logic-search", "--predicate", "ExpectedPassesExam").stdout
    assert rule_claim_id in rule_search
    assert "student-study-pass" in rule_search

    candidates = run_cli(context, "logic-conflict-candidates").stdout
    assert first_claim_id in candidates
    assert second_claim_id in candidates
    assert "opposite polarity" in candidates

    check_payload = json.loads(run_cli(context, "logic-check", "--format", "json").stdout)
    assert check_payload["logic_index_is_proof"] is False
    assert check_payload["solver"] == "structural"
    assert check_payload["candidate_count"] == 1

    auto_payload = json.loads(run_cli(context, "logic-check", "--solver", "auto", "--closure", "rules", "--format", "json").stdout)
    assert auto_payload["logic_index_is_proof"] is False
    assert auto_payload["solver"] in {"structural", "z3"}
    if auto_payload["solver"] == "structural":
        assert "z3-solver is not installed" in auto_payload["solver_warning"]

    z3_payload = json.loads(run_cli(context, "logic-check", "--solver", "z3", "--format", "json").stdout)
    assert z3_payload["logic_index_is_proof"] is False
    if z3_payload.get("available") is False:
        assert z3_payload["error"] == "z3-solver is not installed"
    else:
        assert z3_payload["solver"] == "z3"

    missing_symbol = run_cli(
        context,
        "record-claim",
        "--scope",
        "logic.demo",
        "--plane",
        "runtime",
        "--status",
        "supported",
        "--statement",
        "Bob appears without a symbol introduction.",
        "--source",
        source_id,
        "--logic-atom",
        "Student|person:bob|affirmed",
        "--note",
        "should fail because person:bob is not introduced",
        check=False,
    )
    assert missing_symbol.returncode == 1
    assert "references unknown symbol: person:bob" in missing_symbol.stdout

    tentative_intro = recorded_id(
        run_cli(
            context,
            "record-claim",
            "--scope",
            "logic.demo",
            "--plane",
            "runtime",
            "--status",
            "tentative",
            "--statement",
            "Bob may be a student.",
            "--source",
            source_id,
            "--logic-symbol",
            "person:bob|entity|Bob tentative person symbol for hypothesis lifecycle coverage",
            "--logic-atom",
            "Student|person:bob|affirmed",
            "--note",
            "tentative symbol introduction is allowed only for tentative use",
        ),
        "claim",
    )
    unsupported_symbol_intro = run_cli(
        context,
        "record-claim",
        "--scope",
        "logic.demo",
        "--plane",
        "runtime",
        "--status",
        "supported",
        "--statement",
        "Bob is supported as a student without supported symbol introduction.",
        "--source",
        source_id,
        "--logic-atom",
        "Student|person:bob|affirmed",
        "--note",
        "should fail because person:bob has only tentative introduction",
        check=False,
    )
    assert tentative_intro.startswith("CLM-")
    assert unsupported_symbol_intro.returncode == 1
    assert "symbol lacks supported/corroborated introduction: person:bob" in unsupported_symbol_intro.stdout


def test_working_context_records_support_copy_on_write_focus(tmp_path: Path) -> None:
    context = bootstrap_context(tmp_path)

    source_id = recorded_id(
        run_cli(
            context,
            "record-source",
            "--scope",
            "wctx.demo",
            "--source-kind",
            "runtime",
            "--critique-status",
            "accepted",
            "--origin-kind",
            "command",
            "--origin-ref",
            "pytest working context",
            "--quote",
            "Working context should pin useful records without becoming proof.",
            "--note",
            "wctx source",
        ),
        "source",
    )
    claim_id = recorded_id(
        run_cli(
            context,
            "record-claim",
            "--scope",
            "wctx.demo",
            "--plane",
            "runtime",
            "--status",
            "supported",
            "--statement",
            "Working context should pin useful records without becoming proof.",
            "--source",
            source_id,
            "--note",
            "wctx claim",
        ),
        "claim",
    )

    created = run_cli(
        context,
        "working-context",
        "create",
        "--scope",
        "wctx.demo",
        "--title",
        "Investigate working context",
        "--kind",
        "investigation",
        "--pin",
        claim_id,
        "--topic-seed",
        claim_id,
        "--assumption",
        "Pinned context is useful for handoff|exploration-only",
        "--concern",
        "Working context must not be proof.",
        "--note",
        "create working context",
    )
    wctx_id = recorded_id(created, "working_context")
    wctx = load_record(context, "working_context", wctx_id)
    assert wctx["pinned_refs"] == [claim_id]
    assert wctx["topic_seed_refs"] == [claim_id]
    assert wctx["assumptions"][0]["mode"] == "exploration-only"

    forked = run_cli(
        context,
        "working-context",
        "fork",
        "--context",
        wctx_id,
        "--title",
        "Forked working context",
        "--add-topic-term",
        "handoff",
        "--add-concern",
        "Need a current source before proof.",
        "--note",
        "copy-on-write fork",
    )
    fork_id = recorded_id(forked, "working_context")
    fork = load_record(context, "working_context", fork_id)
    original = load_record(context, "working_context", wctx_id)
    assert original["status"] == "active"
    assert fork["parent_context_ref"] == wctx_id
    assert wctx_id in fork["supersedes_refs"]
    assert "handoff" in fork["topic_terms"]

    show = run_cli(context, "working-context", "show", "--context", fork_id).stdout
    assert fork_id in show
    assert claim_id in show

    run_cli(context, "working-context", "close", "--context", fork_id, "--note", "done")
    assert load_record(context, "working_context", fork_id)["status"] == "closed"
    assert run_cli(context, "review-context").returncode == 0


def test_record_detail_and_neighborhood_expose_drilldown_context(tmp_path: Path) -> None:
    context = bootstrap_context(tmp_path)

    source_id = recorded_id(
        run_cli(
            context,
            "record-source",
            "--scope",
            "detail.demo",
            "--source-kind",
            "runtime",
            "--critique-status",
            "accepted",
            "--origin-kind",
            "command",
            "--origin-ref",
            "pytest record detail",
            "--quote",
            "Record detail should show source quotes and dependent guidelines.",
            "--note",
            "detail source",
        ),
        "source",
    )
    claim_id = recorded_id(
        run_cli(
            context,
            "record-claim",
            "--scope",
            "detail.demo",
            "--plane",
            "runtime",
            "--status",
            "supported",
            "--statement",
            "Record detail should show source quotes and dependent guidelines.",
            "--source",
            source_id,
            "--note",
            "detail claim",
        ),
        "claim",
    )
    guideline_id = recorded_id(
        run_cli(
            context,
            "record-guideline",
            "--scope",
            "detail.demo",
            "--domain",
            "agent-behavior",
            "--applies-to",
            "global",
            "--priority",
            "preferred",
            "--rule",
            "Use record-detail before editing unfamiliar linked records.",
            "--source",
            source_id,
            "--related-claim",
            claim_id,
            "--note",
            "detail guideline",
        ),
        "guideline",
    )

    text = run_cli(context, "record-detail", "--record", claim_id).stdout
    assert "Record Detail" in text
    assert "Source Quotes" in text
    assert source_id in text
    assert guideline_id in text
    assert "related_claim_refs" in text

    payload = json.loads(run_cli(context, "record-neighborhood", "--record", claim_id, "--format", "json").stdout)
    assert payload["summary"]["id"] == claim_id
    edge_pairs = {(edge["from"], edge["to"]) for edge in payload["links"]["edges"]}
    assert (claim_id, source_id) in edge_pairs
    assert (guideline_id, claim_id) in edge_pairs


def test_guidelines_for_filters_active_rules_for_task_and_domain(tmp_path: Path) -> None:
    context = bootstrap_context(tmp_path)

    source_id = recorded_id(
        run_cli(
            context,
            "record-source",
            "--scope",
            "guidelines.demo",
            "--source-kind",
            "theory",
            "--critique-status",
            "accepted",
            "--origin-kind",
            "user",
            "--origin-ref",
            "test style instruction",
            "--quote",
            "Write pytest coverage through page objects.",
            "--note",
            "guideline source",
        ),
        "source",
    )
    tests_guideline_id = recorded_id(
        run_cli(
            context,
            "record-guideline",
            "--scope",
            "guidelines.demo",
            "--domain",
            "tests",
            "--applies-to",
            "global",
            "--priority",
            "required",
            "--rule",
            "Write pytest coverage through page objects.",
            "--source",
            source_id,
            "--note",
            "tests guideline",
        ),
        "guideline",
    )
    code_guideline_id = recorded_id(
        run_cli(
            context,
            "record-guideline",
            "--scope",
            "guidelines.demo",
            "--domain",
            "code",
            "--applies-to",
            "global",
            "--priority",
            "preferred",
            "--rule",
            "Keep production code changes minimal.",
            "--source",
            source_id,
            "--note",
            "code guideline",
        ),
        "guideline",
    )

    text = run_cli(
        context,
        "guidelines-for",
        "--task",
        "write pytest coverage through page objects",
        "--domain",
        "tests",
    ).stdout
    assert tests_guideline_id in text
    assert code_guideline_id not in text

    payload = json.loads(
        run_cli(
            context,
            "guidelines-for",
            "--task",
            "write pytest coverage through page objects",
            "--domain",
            "tests",
            "--format",
            "json",
        ).stdout
    )
    assert [guideline["id"] for guideline in payload["guidelines"]] == [tests_guideline_id]


def test_cleanup_candidates_reports_read_only_attention_mismatches(tmp_path: Path) -> None:
    context = bootstrap_context(tmp_path)

    source_id = recorded_id(
        run_cli(
            context,
            "record-source",
            "--scope",
            "cleanup.demo",
            "--source-kind",
            "runtime",
            "--critique-status",
            "accepted",
            "--origin-kind",
            "command",
            "--origin-ref",
            "pytest cleanup candidates",
            "--quote",
            "Cleanup candidates should report stale attention mismatches.",
            "--note",
            "cleanup source",
        ),
        "source",
    )
    current_claim_id = recorded_id(
        run_cli(
            context,
            "record-claim",
            "--scope",
            "cleanup.demo",
            "--plane",
            "runtime",
            "--status",
            "supported",
            "--statement",
            "Cleanup candidates should report current replacement facts.",
            "--source",
            source_id,
            "--note",
            "current cleanup claim",
        ),
        "claim",
    )
    stale_claim_id = recorded_id(
        run_cli(
            context,
            "record-claim",
            "--scope",
            "cleanup.demo",
            "--plane",
            "runtime",
            "--status",
            "supported",
            "--statement",
            "Cleanup candidates should report stale attention mismatches.",
            "--source",
            source_id,
            "--note",
            "stale cleanup claim",
        ),
        "claim",
    )
    run_cli(
        context,
        "resolve-claim",
        "--claim",
        stale_claim_id,
        "--resolved-by-claim",
        current_claim_id,
        "--note",
        "resolved cleanup fixture",
    )

    stale_record_path = context / "records" / "claim" / f"{stale_claim_id}.json"
    stale_record = json.loads(stale_record_path.read_text(encoding="utf-8"))
    stale_record["lifecycle"]["attention"] = "normal"
    stale_record_path.write_text(json.dumps(stale_record, indent=2), encoding="utf-8")

    result = run_cli(context, "cleanup-candidates", check=False)
    assert result.returncode == 0
    assert "read-only report" in result.stdout
    assert stale_claim_id in result.stdout
    assert "claim_lifecycle_attention_mismatch" in result.stdout

    payload = json.loads(run_cli(context, "cleanup-candidates", "--format", "json", check=False).stdout)
    assert payload["cleanup_is_read_only"] is True
    assert payload["candidate_count"] >= 1
    assert stale_claim_id in json.dumps(payload)

    input_id = "INP-20260418-abcdef12"
    input_path = context / "records" / "input" / f"{input_id}.json"
    input_path.write_text(
        json.dumps(
            {
                "id": input_id,
                "record_type": "input",
                "input_kind": "user_prompt",
                "scope": "cleanup.demo",
                "captured_at": "1970-01-01T00:00:00+00:00",
                "origin": {"kind": "user_prompt", "ref": "pytest"},
                "text": "Old orphan input should appear in archive dry-run.",
                "note": "cleanup archive fixture",
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    archive_result = run_cli(context, "cleanup-archive", "--dry-run", check=False)
    assert archive_result.returncode == 0
    assert "Mode: dry-run" in archive_result.stdout
    assert input_id in archive_result.stdout
    archive_payload = json.loads(
        run_cli(context, "cleanup-archive", "--dry-run", "--format", "json", check=False).stdout
    )
    assert archive_payload["archive_plan_is_dry_run"] is True
    assert archive_payload["archive_format"] == "zip"
    assert archive_payload["items"][0]["record_id"] == input_id
    assert not list((context / "archives").glob("*"))

    apply_payload = json.loads(
        run_cli(context, "cleanup-archive", "--apply", "--format", "json", check=False).stdout
    )
    assert apply_payload["archive_plan_is_dry_run"] is False
    assert apply_payload["archive_written"] is True
    assert apply_payload["records_mutated"] is False
    assert apply_payload["records_deleted"] is False
    assert input_path.exists()
    archive_path = context / apply_payload["archive_path"]
    manifest_path = context / apply_payload["manifest_path"]
    assert archive_path.exists()
    assert manifest_path.exists()
    with zipfile.ZipFile(archive_path) as archive:
        assert "manifest.json" in archive.namelist()
        assert f"records/input/{input_id}.json" in archive.namelist()
    assert json.loads(manifest_path.read_text(encoding="utf-8"))["items"][0]["record_id"] == input_id

    archive_catalog = json.loads(run_cli(context, "cleanup-archives", "--format", "json", check=False).stdout)
    assert archive_catalog["cleanup_archives_is_read_only"] is True
    assert archive_catalog["archives"][0]["archive_id"] == apply_payload["archive_id"]
    archive_detail = run_cli(
        context,
        "cleanup-archives",
        "--archive",
        apply_payload["archive_id"],
        check=False,
    )
    assert archive_detail.returncode == 0
    assert input_id in archive_detail.stdout

    restore_existing = run_cli(
        context,
        "cleanup-restore",
        "--archive",
        apply_payload["archive_id"],
        "--dry-run",
        check=False,
    )
    assert restore_existing.returncode == 0
    assert "already-present" in restore_existing.stdout

    archived_input_payload = json.loads(input_path.read_text(encoding="utf-8"))
    input_path.unlink()
    restore_plan = run_cli(
        context,
        "cleanup-restore",
        "--archive",
        apply_payload["archive_id"],
        "--dry-run",
        check=False,
    )
    assert restore_plan.returncode == 0
    assert "restore-ready" in restore_plan.stdout

    restore_payload = json.loads(
        run_cli(
            context,
            "cleanup-restore",
            "--archive",
            apply_payload["archive_id"],
            "--apply",
            "--format",
            "json",
            check=False,
        ).stdout
    )
    assert restore_payload["restore_applied"] is True
    assert restore_payload["restored_count"] == 1
    assert json.loads(input_path.read_text(encoding="utf-8")) == archived_input_payload

    input_path.write_text(json.dumps({"different": True}, indent=2), encoding="utf-8")
    restore_conflict = run_cli(
        context,
        "cleanup-restore",
        "--archive",
        apply_payload["archive_id"],
        "--apply",
        "--format",
        "json",
        check=False,
    )
    assert restore_conflict.returncode == 1
    conflict_payload = json.loads(restore_conflict.stdout)
    assert conflict_payload["restore_blocked"] is True
    assert conflict_payload["items"][0]["status"] == "target-conflict"
    assert json.loads(input_path.read_text(encoding="utf-8")) == {"different": True}


def test_code_index_supports_ast_search_refresh_annotations_and_links(tmp_path: Path) -> None:
    context = bootstrap_context(tmp_path)
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "src").mkdir()
    (repo / "tests").mkdir()
    (repo / "src" / "app.py").write_text(
        "class PromptChoiceElement:\n"
        "    def choose(self):\n"
        "        return 'ok'\n",
        encoding="utf-8",
    )
    test_file = repo / "tests" / "test_app.py"
    test_file.write_text(
        "import pytest\n"
        "from src.app import PromptChoiceElement\n\n"
        "@pytest.fixture\n"
        "def choice():\n"
        "    return PromptChoiceElement()\n\n"
        "def test_choice(choice):\n"
        "    assert choice.choose() == 'ok'\n",
        encoding="utf-8",
    )
    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True, text=True)
    subprocess.run(["git", "add", "src/app.py", "tests/test_app.py"], cwd=repo, check=True, capture_output=True, text=True)

    run_cli(context, "init-code-index", "--root", str(repo))
    entries = sorted((context / "code_index" / "entries").glob("CIX-*.json"))
    assert len(entries) == 2

    search_payload = json.loads(
        run_cli(
            context,
            "code-search",
            "--root",
            str(repo),
            "--import",
            "pytest",
            "--fields",
            "target,imports,symbols,features,freshness",
            "--format",
            "json",
        ).stdout
    )
    assert len(search_payload["results"]) == 1
    test_entry_id = search_payload["results"][0]["id"]
    assert search_payload["results"][0]["target"]["path"] == "tests/test_app.py"
    assert search_payload["results"][0]["symbols"]["tests"] == ["test_choice"]
    assert "fixtures" in search_payload["results"][0]["features"]["detected"]

    info_payload = json.loads(
        run_cli(
            context,
            "code-info",
            "--root",
            str(repo),
            "--path",
            "tests/test_app.py",
            "--fields",
            "target,hash,freshness",
            "--format",
            "json",
        ).stdout
    )
    assert info_payload["id"] == test_entry_id
    assert info_payload["freshness"]["stale"] is False

    run_cli(
        context,
        "annotate-code",
        "--path",
        "tests/test_app.py",
        "--kind",
        "agent-note",
        "--note",
        "This file covers prompt choice behavior.",
    )
    entry = json.loads((context / "code_index" / "entries" / f"{test_entry_id}.json").read_text(encoding="utf-8"))
    assert entry["annotations"][0]["observed_sha256"] == info_payload["hash"]["sha256"]

    denied_critical_smell = run_cli(
        context,
        "annotate-code",
        "--path",
        "tests/test_app.py",
        "--kind",
        "smell",
        "--category",
        "mixed-responsibility",
        "--severity",
        "critical",
        "--note",
        "Critical smells require claim support.",
        check=False,
    )
    assert denied_critical_smell.returncode == 1
    assert "critical smell annotations require" in denied_critical_smell.stdout

    run_cli(
        context,
        "annotate-code",
        "--path",
        "tests/test_app.py",
        "--kind",
        "smell",
        "--category",
        "mixed-responsibility",
        "--category",
        "custom:prompt-choice",
        "--severity",
        "high",
        "--suggestion",
        "Split setup from assertion logic.",
        "--note",
        "This test mixes prompt fixture setup with behavior assertion.",
    )
    smell_search = json.loads(
        run_cli(
            context,
            "code-search",
            "--root",
            str(repo),
            "--annotation-kind",
            "smell",
            "--annotation-category",
            "mixed-responsibility",
            "--fields",
            "target,annotations",
            "--format",
            "json",
        ).stdout
    )
    assert smell_search["results"][0]["id"] == test_entry_id
    smell_annotations = [item for item in smell_search["results"][0]["annotations"] if item["kind"] == "smell"]
    assert smell_annotations[0]["categories"] == ["custom:prompt-choice", "mixed-responsibility"]
    assert smell_annotations[0]["severity"] == "high"

    smell_report = json.loads(
        run_cli(
            context,
            "code-smell-report",
            "--root",
            str(repo),
            "--category",
            "mixed-responsibility",
            "--format",
            "json",
        ).stdout
    )
    assert smell_report["results"][0]["entry"]["id"] == test_entry_id
    assert smell_report["results"][0]["stale"] is False

    source_id = recorded_id(
        run_cli(
            context,
            "record-source",
            "--scope",
            "code-index.guideline",
            "--source-kind",
            "theory",
            "--critique-status",
            "accepted",
            "--origin-kind",
            "user",
            "--origin-ref",
            "test guideline",
            "--quote",
            "Pytest files should use focused fixtures.",
            "--note",
            "guideline source",
        ),
        "source",
    )
    guideline_id = recorded_id(
        run_cli(
            context,
            "record-guideline",
            "--scope",
            "code-index.guideline",
            "--domain",
            "tests",
            "--applies-to",
            "global",
            "--priority",
            "preferred",
            "--rule",
            "Pytest files should use focused fixtures.",
            "--source",
            source_id,
            "--note",
            "guideline",
        ),
        "guideline",
    )
    run_cli(context, "link-code", "--entry", test_entry_id, "--guideline", guideline_id, "--note", "guideline applies to this test file")
    claim_id = recorded_id(
        run_cli(
            context,
            "record-claim",
            "--scope",
            "code-index.smell",
            "--plane",
            "code",
            "--status",
            "supported",
            "--statement",
            "Prompt choice tests have a supported critical smell in this fixture layout.",
            "--source",
            source_id,
            "--note",
            "critical smell support",
        ),
        "claim",
    )
    run_cli(
        context,
        "annotate-code",
        "--entry",
        test_entry_id,
        "--kind",
        "smell",
        "--category",
        "poor-error-boundary",
        "--severity",
        "critical",
        "--claim",
        claim_id,
        "--note",
        "Critical smell is supported by a claim.",
    )
    critical_report = json.loads(
        run_cli(context, "code-smell-report", "--root", str(repo), "--severity", "critical", "--format", "json").stdout
    )
    assert critical_report["results"][0]["annotation"]["claim_refs"] == [claim_id]

    linked_payload = json.loads(
        run_cli(
            context,
            "code-search",
            "--root",
            str(repo),
            "--ref",
            guideline_id,
            "--fields",
            "target,links",
            "--format",
            "json",
        ).stdout
    )
    assert linked_payload["results"][0]["id"] == test_entry_id

    run_cli(context, "assign-code-index", "--record", guideline_id, "--entry", test_entry_id, "--note", "scope link")
    guideline = load_record(context, "guideline", guideline_id)
    assert guideline["code_index_refs"] == [test_entry_id]

    test_file.write_text(test_file.read_text(encoding="utf-8") + "\ndef test_second(choice):\n    assert choice.choose()\n", encoding="utf-8")
    stale_smell_report = json.loads(
        run_cli(context, "code-smell-report", "--root", str(repo), "--format", "json").stdout
    )
    assert stale_smell_report["results"] == []
    stale_smell_report = json.loads(
        run_cli(context, "code-smell-report", "--root", str(repo), "--include-stale", "--format", "json").stdout
    )
    assert stale_smell_report["results"][0]["stale"] is True

    stale_payload = json.loads(
        run_cli(context, "code-search", "--root", str(repo), "--stale", "true", "--fields", "target,freshness", "--format", "json").stdout
    )
    assert stale_payload["results"][0]["id"] == test_entry_id

    run_cli(context, "code-refresh", "--root", str(repo), "--path", "tests/test_app.py")
    refreshed = json.loads(
        run_cli(context, "code-info", "--root", str(repo), "--path", "tests/test_app.py", "--fields", "symbols,freshness", "--format", "json").stdout
    )
    assert refreshed["freshness"]["stale"] is False
    assert "test_second" in refreshed["symbols"]["tests"]

    test_file.unlink()
    run_cli(context, "code-refresh", "--root", str(repo), "--path", "tests/test_app.py")
    missing = json.loads(
        run_cli(
            context,
            "code-search",
            "--root",
            str(repo),
            "--path",
            "tests/test_app.py",
            "--include-missing",
            "--fields",
            "target,freshness",
            "--format",
            "json",
        ).stdout
    )
    assert missing["results"][0]["status"] == "missing"

    test_file.write_text("def test_recreated():\n    assert True\n", encoding="utf-8")
    run_cli(context, "code-refresh", "--root", str(repo), "--path", "tests/test_app.py")
    all_versions = json.loads(
        run_cli(
            context,
            "code-search",
            "--root",
            str(repo),
            "--path",
            "tests/test_app.py",
            "--include-superseded",
            "--fields",
            "target",
            "--format",
            "json",
        ).stdout
    )
    assert len(all_versions["results"]) == 2
    active = [item for item in all_versions["results"] if item["status"] == "active"][0]
    active_entry = json.loads((context / "code_index" / "entries" / f"{active['id']}.json").read_text(encoding="utf-8"))
    assert test_entry_id in active_entry["supersedes_refs"]

    denied = run_cli(context, "assign-code-index", "--record", source_id, "--entry", test_entry_id, check=False)
    assert denied.returncode == 1
    assert "cannot reference CIX" in denied.stdout


def test_parallel_record_writes_are_lock_safe(tmp_path: Path) -> None:
    context = bootstrap_context(tmp_path)
    processes = []

    for index in range(8):
        processes.append(
            subprocess.Popen(
                [
                    sys.executable,
                    str(CLI),
                    "--context",
                    str(context),
                    "record-source",
                    "--scope",
                    "demo.parallel",
                    "--source-kind",
                    "runtime",
                    "--critique-status",
                    "accepted",
                    "--origin-kind",
                    "command",
                    "--origin-ref",
                    f"parallel {index}",
                    "--quote",
                    f"parallel write {index}",
                    "--note",
                    "parallel write check",
                ],
                cwd=REPO_ROOT,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
        )

    results = [process.communicate(timeout=20) + (process.returncode,) for process in processes]
    failures = [result for result in results if result[2] != 0]
    assert not failures

    source_ids = sorted(path.stem for path in (context / "records" / "source").glob("*.json"))
    assert len(source_ids) == 8
    assert len(set(source_ids)) == 8
    assert all(re.match(r"^SRC-\d{8}-[0-9a-f]{8}$", source_id) for source_id in source_ids)

    result = run_cli(context, "review-context")
    assert result.returncode == 0


def test_returning_to_proof_only_allows_historical_mutating_actions(tmp_path: Path) -> None:
    context = bootstrap_context(tmp_path)

    run_cli(
        context,
        "record-source",
        "--scope",
        "demo.action",
        "--source-kind",
        "runtime",
        "--critique-status",
        "accepted",
        "--origin-kind",
        "command",
        "--origin-ref",
        "pytest action",
        "--quote",
        "supported action reason",
        "--note",
        "action source",
    )
    source_id = only_record_id(context, "source")
    run_cli(
        context,
        "record-claim",
        "--scope",
        "demo.action",
        "--plane",
        "runtime",
        "--status",
        "supported",
        "--statement",
        "A bounded edit was justified.",
        "--source",
        source_id,
        "--note",
        "action claim",
    )
    claim_id = only_record_id(context, "claim")

    blocked = run_cli(
        context,
        "record-action",
        "--kind",
        "edit",
        "--scope",
        "demo.action",
        "--justify",
        claim_id,
        "--safety-class",
        "safe",
        "--status",
        "executed",
        "--note",
        "should be blocked in proof-only",
        check=False,
    )
    assert blocked.returncode == 1
    assert "requires implementation-choice" in blocked.stdout

    denied_escalation = run_cli(context, "change-strictness", "implementation-choice", check=False)
    assert denied_escalation.returncode == 1
    assert "requires --request" in denied_escalation.stdout

    run_cli(
        context,
        "record-permission",
        "--scope",
        "demo.action",
        "--applies-to",
        "global",
        "--granted-by",
        "user",
        "--grant",
        "allowed_freedom:implementation-choice",
        "--note",
        "user explicitly allows implementation-choice for bounded action test",
    )
    permission_id = only_record_id(context, "permission")

    old_permission_only = run_cli(
        context,
        "change-strictness",
        "implementation-choice",
        "--permission",
        permission_id,
        check=False,
    )
    assert old_permission_only.returncode == 1
    assert "requires --request" in old_permission_only.stdout

    request_id, approval_source_id = strictness_approval(context, "implementation-choice", permission_id)
    run_cli(
        context,
        "change-strictness",
        "implementation-choice",
        "--permission",
        permission_id,
        "--request",
        request_id,
        "--approval-source",
        approval_source_id,
    )
    run_cli(
        context,
        "record-action",
        "--kind",
        "edit",
        "--scope",
        "demo.action",
        "--justify",
        claim_id,
        "--safety-class",
        "safe",
        "--status",
        "executed",
        "--note",
        "historical mutating action",
    )
    assert only_record_id(context, "action").startswith("ACT-")

    returned = run_cli(context, "change-strictness", "proof-only")
    assert returned.returncode == 0
    reused_request = run_cli(
        context,
        "change-strictness",
        "implementation-choice",
        "--permission",
        permission_id,
        "--request",
        request_id,
        "--approval-source",
        approval_source_id,
        check=False,
    )
    assert reused_request.returncode == 1
    assert "is not pending" in reused_request.stdout
    review = run_cli(context, "review-context")
    assert review.returncode == 0


def test_evidence_authorized_allows_bounded_mutating_action_with_valid_chain(tmp_path: Path) -> None:
    context = bootstrap_context(tmp_path)

    run_cli(
        context,
        "record-source",
        "--scope",
        "demo.evidence-authorized",
        "--source-kind",
        "runtime",
        "--critique-status",
        "accepted",
        "--origin-kind",
        "command",
        "--origin-ref",
        "pytest evidence-authorized",
        "--quote",
        "bounded edit is supported by runtime evidence",
        "--note",
        "evidence-authorized source",
    )
    source_id = only_record_id(context, "source")
    run_cli(
        context,
        "record-claim",
        "--scope",
        "demo.evidence-authorized",
        "--plane",
        "runtime",
        "--status",
        "supported",
        "--statement",
        "Bounded edit is supported by runtime evidence.",
        "--source",
        source_id,
        "--note",
        "evidence-authorized claim",
    )
    claim_id = only_record_id(context, "claim")
    run_cli(
        context,
        "start-task",
        "--scope",
        "demo.evidence-authorized",
        "--title",
        "Bounded evidence-authorized edit",
        "--related-claim",
        claim_id,
        "--note",
        "active task for evidence-authorized mutation",
    )
    task_id = only_record_id(context, "task")

    chain = context.parent / "evidence-chain.json"
    chain.write_text(
        json.dumps(
            {
                "task": "Bounded evidence-authorized edit",
                "nodes": [
                    {
                        "role": "fact",
                        "ref": claim_id,
                        "quote": "Bounded edit is supported by runtime evidence.",
                    },
                    {
                        "role": "task",
                        "ref": task_id,
                        "quote": "Bounded evidence-authorized edit",
                    },
                ],
                "edges": [
                    {"from": claim_id, "to": task_id, "relation": "supports bounded task"},
                ],
            }
        ),
        encoding="utf-8",
    )

    request_id, approval_source_id = strictness_approval(context, "evidence-authorized")
    run_cli(
        context,
        "change-strictness",
        "evidence-authorized",
        "--request",
        request_id,
        "--approval-source",
        approval_source_id,
    )

    missing_chain = run_cli(
        context,
        "record-action",
        "--kind",
        "edit",
        "--scope",
        "demo.evidence-authorized",
        "--justify",
        claim_id,
        "--safety-class",
        "safe",
        "--status",
        "executed",
        "--note",
        "missing evidence chain",
        check=False,
    )
    assert missing_chain.returncode == 1
    assert "require --evidence-chain" in missing_chain.stdout

    run_cli(
        context,
        "record-action",
        "--kind",
        "edit",
        "--scope",
        "demo.evidence-authorized",
        "--justify",
        claim_id,
        "--safety-class",
        "safe",
        "--status",
        "executed",
        "--evidence-chain",
        str(chain),
        "--note",
        "evidence-authorized historical mutating action",
    )
    assert only_record_id(context, "action").startswith("ACT-")


def test_flow_accepted_deviation_allows_user_permission(tmp_path: Path) -> None:
    context = bootstrap_context(tmp_path)

    run_cli(
        context,
        "record-source",
        "--scope",
        "demo.issue",
        "--source-kind",
        "runtime",
        "--critique-status",
        "accepted",
        "--origin-kind",
        "command",
        "--origin-ref",
        "pytest demo",
        "--quote",
        "observed deviation",
        "--note",
        "runtime source",
    )
    source_id = only_record_id(context, "source")

    run_cli(
        context,
        "record-claim",
        "--scope",
        "demo.issue",
        "--plane",
        "runtime",
        "--status",
        "supported",
        "--statement",
        "Deviation exists in runtime behavior.",
        "--source",
        source_id,
        "--note",
        "runtime-backed claim",
    )
    claim_id = only_record_id(context, "claim")

    run_cli(
        context,
        "record-model",
        "--knowledge-class",
        "investigation",
        "--domain",
        "payments",
        "--scope",
        "demo.issue",
        "--aspect",
        "runtime-behavior",
        "--status",
        "working",
        "--summary",
        "Investigating a runtime deviation.",
        "--claim",
        claim_id,
        "--note",
        "working model",
    )
    model_id = only_record_id(context, "model")

    run_cli(
        context,
        "record-permission",
        "--scope",
        "demo.issue",
        "--granted-by",
        "user",
        "--grant",
        "accept current deviation for this scope",
        "--note",
        "explicit user approval",
    )
    permission_id = only_record_id(context, "permission")

    run_cli(
        context,
        "record-flow",
        "--knowledge-class",
        "investigation",
        "--domain",
        "payments",
        "--scope",
        "demo.issue",
        "--status",
        "draft",
        "--summary",
        "Flow with accepted deviation.",
        "--model",
        model_id,
        "--step-id",
        "step-1",
        "--step-label",
        "Observed behavior diverges",
        "--step-status",
        "accepted-deviation",
        "--step-claims",
        claim_id,
        "--step-next",
        "",
        "--step-open-questions",
        "",
        "--step-accepted-deviation-refs",
        permission_id,
        "--note",
        "draft flow",
    )

    flow_id = only_record_id(context, "flow")
    flow = load_record(context, "flow", flow_id)
    assert flow["steps"][0]["accepted_deviation_refs"] == [permission_id]


def test_promote_model_and_mark_stale_are_conservative(tmp_path: Path) -> None:
    context = bootstrap_context(tmp_path)

    run_cli(
        context,
        "record-source",
        "--scope",
        "demo.issue",
        "--source-kind",
        "runtime",
        "--critique-status",
        "accepted",
        "--origin-kind",
        "command",
        "--origin-ref",
        "pytest demo",
        "--quote",
        "observed timeout before ack",
        "--note",
        "runtime source",
    )
    source_id = only_record_id(context, "source")

    run_cli(
        context,
        "record-claim",
        "--scope",
        "demo.issue",
        "--plane",
        "runtime",
        "--status",
        "supported",
        "--statement",
        "Gateway times out before provider ack.",
        "--source",
        source_id,
        "--note",
        "supported runtime claim",
    )
    claim_id = only_record_id(context, "claim")

    run_cli(
        context,
        "record-open-question",
        "--domain",
        "payments",
        "--scope",
        "demo.issue",
        "--aspect",
        "runtime-behavior",
        "--question",
        "Does retry burst amplify timeout?",
        "--note",
        "deferred question",
    )
    open_question_id = only_record_id(context, "open_question")

    run_cli(
        context,
        "record-model",
        "--knowledge-class",
        "investigation",
        "--domain",
        "payments",
        "--scope",
        "demo.issue",
        "--aspect",
        "runtime-behavior",
        "--status",
        "stable",
        "--primary",
        "--summary",
        "Timeout happens before provider ack.",
        "--claim",
        claim_id,
        "--open-question",
        open_question_id,
        "--note",
        "stable investigation model",
    )
    source_model_id = only_record_id(context, "model")

    run_cli(
        context,
        "record-flow",
        "--knowledge-class",
        "investigation",
        "--domain",
        "payments",
        "--scope",
        "demo.issue",
        "--status",
        "stable",
        "--primary",
        "--summary",
        "Gateway then provider path.",
        "--model",
        source_model_id,
        "--oracle-success",
        claim_id,
        "--oracle-failure",
        claim_id,
        "--step-id",
        "step-1",
        "--step-label",
        "Gateway receives request",
        "--step-status",
        "aligned",
        "--step-claims",
        claim_id,
        "--step-next",
        "",
        "--step-open-questions",
        "",
        "--step-accepted-deviation-refs",
        "",
        "--note",
        "stable investigation flow",
    )
    source_flow_id = only_record_id(context, "flow")

    run_cli(context, "promote-model-to-domain", "--model", source_model_id)
    model_files = sorted((context / "records" / "model").glob("*.json"))
    assert len(model_files) == 2
    promoted_model_id = [path.stem for path in model_files if path.stem != source_model_id][0]

    source_model = load_record(context, "model", source_model_id)
    promoted_model = load_record(context, "model", promoted_model_id)
    assert source_model["status"] == "superseded"
    assert source_model["is_primary"] is False
    assert promoted_model["knowledge_class"] == "domain"
    assert source_model_id in promoted_model["promoted_from_refs"]

    run_cli(context, "promote-flow-to-domain", "--flow", source_flow_id)
    flow_files = sorted((context / "records" / "flow").glob("*.json"))
    assert len(flow_files) == 2
    promoted_flow_id = [path.stem for path in flow_files if path.stem != source_flow_id][0]

    run_cli(context, "mark-stale-from-claim", "--claim", claim_id)

    source_flow = load_record(context, "flow", source_flow_id)
    promoted_flow = load_record(context, "flow", promoted_flow_id)
    refreshed_promoted_model = load_record(context, "model", promoted_model_id)
    refreshed_open_question = load_record(context, "open_question", open_question_id)

    assert source_flow["status"] == "superseded"
    assert promoted_flow["status"] == "stale"
    assert refreshed_promoted_model["status"] == "stale"
    assert refreshed_open_question["status"] == "open"


def test_brief_and_reasoning_case_expose_fact_chain(tmp_path: Path) -> None:
    context = bootstrap_context(tmp_path)

    run_cli(
        context,
        "record-source",
        "--scope",
        "demo.bridge",
        "--source-kind",
        "runtime",
        "--critique-status",
        "accepted",
        "--origin-kind",
        "command",
        "--origin-ref",
        "pytest bridge",
        "--quote",
        "check-r1 returned 200 OK after retry",
        "--note",
        "runtime source",
    )
    source_id = only_record_id(context, "source")

    run_cli(
        context,
        "record-claim",
        "--scope",
        "demo.bridge",
        "--plane",
        "runtime",
        "--status",
        "supported",
        "--statement",
        "Bridge check-r1 recovers after retry.",
        "--source",
        source_id,
        "--note",
        "supported runtime claim",
    )
    claim_id = only_record_id(context, "claim")

    run_cli(
        context,
        "record-model",
        "--knowledge-class",
        "investigation",
        "--domain",
        "bridge",
        "--scope",
        "demo.bridge",
        "--aspect",
        "runtime-behavior",
        "--status",
        "working",
        "--primary",
        "--summary",
        "Bridge check-r1 recovery works after retry.",
        "--claim",
        claim_id,
        "--note",
        "working model",
    )
    model_id = only_record_id(context, "model")

    run_cli(
        context,
        "record-flow",
        "--knowledge-class",
        "investigation",
        "--domain",
        "bridge",
        "--scope",
        "demo.bridge",
        "--status",
        "working",
        "--primary",
        "--summary",
        "Bridge check-r1 retry flow.",
        "--model",
        model_id,
        "--oracle-success",
        claim_id,
        "--step-id",
        "step-1",
        "--step-label",
        "retry check-r1",
        "--step-status",
        "aligned",
        "--step-claims",
        claim_id,
        "--step-next",
        "",
        "--step-open-questions",
        "",
        "--step-accepted-deviation-refs",
        "",
        "--note",
        "working flow",
    )
    flow_id = only_record_id(context, "flow")

    brief = run_cli(context, "brief-context", "--task", "debug bridge check-r1 retry").stdout
    assert "Context Brief" in brief
    assert model_id in brief
    assert claim_id in brief

    next_step = run_cli(context, "next-step", "--intent", "edit", "--task", "debug bridge check-r1 retry").stdout
    assert "TEP Next Step" in next_step
    assert "intent: edit" in next_step
    assert "hydrate-context" in next_step
    next_step_payload = json.loads(
        run_cli(context, "next-step", "--intent", "edit", "--task", "debug bridge check-r1 retry", "--format", "json").stdout
    )
    assert next_step_payload["intent"] == "edit"
    assert next_step_payload["route_graph"]["graph_version"] == 1
    assert {"if": "proof gap", "then": "build/validate evidence chain"} in next_step_payload["route_graph"]["branches"]

    reasoning = run_cli(
        context,
        "build-reasoning-case",
        "--task",
        "debug bridge check-r1 retry",
        "--model",
        model_id,
        "--flow",
        flow_id,
    ).stdout
    assert "Reasoning Case" in reasoning
    assert claim_id in reasoning
    assert source_id in reasoning
    assert "check-r1 returned 200 OK after retry" in reasoning
    assert "every listed claim has source refs" in reasoning


def test_validate_planning_chain_checks_roles_and_quotes(tmp_path: Path) -> None:
    context = bootstrap_context(tmp_path)

    run_cli(
        context,
        "record-source",
        "--scope",
        "demo.bridge",
        "--source-kind",
        "runtime",
        "--critique-status",
        "accepted",
        "--origin-kind",
        "command",
        "--origin-ref",
        "pytest bridge",
        "--quote",
        "check-r1 returned 200 OK after retry",
        "--note",
        "runtime source",
    )
    source_id = only_record_id(context, "source")

    run_cli(
        context,
        "record-claim",
        "--scope",
        "demo.bridge",
        "--plane",
        "runtime",
        "--status",
        "supported",
        "--statement",
        "Bridge check-r1 recovers after retry.",
        "--source",
        source_id,
        "--note",
        "supported runtime claim",
    )
    fact_id = only_record_id(context, "claim")

    run_cli(
        context,
        "record-claim",
        "--scope",
        "demo.bridge",
        "--plane",
        "runtime",
        "--status",
        "tentative",
        "--statement",
        "Bridge check-r1 may still have a transient first-call gap.",
        "--source",
        source_id,
        "--note",
        "hypothesis-stage claim",
    )
    claims = sorted((context / "records" / "claim").glob("*.json"))
    hypothesis_id = [path.stem for path in claims if path.stem != fact_id][0]

    chain = tmp_path / "planning-chain.json"
    chain.write_text(
        json.dumps(
            {
                "task": "debug bridge check-r1 retry",
                "nodes": [
                    {"role": "fact", "ref": fact_id, "quote": "Bridge check-r1 recovers after retry."},
                    {
                        "role": "observation",
                        "ref": hypothesis_id,
                        "quote": "Bridge check-r1 may still have a transient first-call gap.",
                    },
                ],
                "edges": [{"from": fact_id, "to": hypothesis_id, "relation": "frames"}],
            }
        ),
        encoding="utf-8",
    )
    valid = run_cli(context, "validate-evidence-chain", "--file", str(chain))
    assert "evidence chain is mechanically valid" in valid.stdout

    compact_chain = tmp_path / "compact-planning-chain.json"
    compact_chain.write_text(
        json.dumps(
            {
                "task": "debug bridge check-r1 retry",
                "nodes": [
                    {"role": "fact", "ref": fact_id},
                    {"role": "observation", "ref": hypothesis_id},
                ],
                "edges": [{"from": fact_id, "to": hypothesis_id, "relation": "frames"}],
            }
        ),
        encoding="utf-8",
    )
    augmented = json.loads(
        run_cli(context, "augment-chain", "--file", str(compact_chain), "--format", "json").stdout
    )
    assert augmented["augment_is_read_only"] is True
    assert augmented["validation"]["ok"] is True
    assert augmented["chain"]["nodes"][0]["quote"] == "Bridge check-r1 recovers after retry."
    assert augmented["chain"]["nodes"][0]["record"]["status"] == "supported"
    assert augmented["chain"]["nodes"][0]["source_quotes"][0]["ref"] == source_id
    augmented_text = run_cli(context, "augment-chain", "--file", str(compact_chain)).stdout
    assert "Augmented Evidence Chain" in augmented_text
    assert "evidence chain is mechanically valid" in augmented_text

    invalid_chain = tmp_path / "invalid-planning-chain.json"
    invalid_chain.write_text(
        json.dumps(
            {
                "task": "bad chain",
                "nodes": [
                    {
                        "role": "fact",
                        "ref": hypothesis_id,
                        "quote": "Bridge check-r1 may still have a transient first-call gap.",
                    }
                ],
                "edges": [{"from": hypothesis_id, "to": hypothesis_id, "relation": "self"}],
            }
        ),
        encoding="utf-8",
    )
    invalid = run_cli(context, "validate-planning-chain", "--file", str(invalid_chain), check=False)
    assert invalid.returncode == 1
    assert "must be supported/corroborated" in invalid.stdout

    permission_request = tmp_path / "permission-request-chain.json"
    permission_request.write_text(
        json.dumps(
            {
                "task": "request permission for guarded check-r1 probe",
                "nodes": [
                    {"role": "fact", "ref": fact_id, "quote": "Bridge check-r1 recovers after retry."},
                    {
                        "role": "requested_permission",
                        "ref": "REQ-check-r1-probe",
                        "quote": "Run guarded check-r1 probe without deleting data.",
                    },
                ],
                "edges": [{"from": fact_id, "to": "REQ-check-r1-probe", "relation": "motivates-permission-request"}],
            }
        ),
        encoding="utf-8",
    )
    request_valid = run_cli(context, "validate-evidence-chain", "--file", str(permission_request))
    assert "evidence chain is mechanically valid" in request_valid.stdout


def test_exploration_hypothesis_is_blocked_as_proof_but_allowed_as_context(tmp_path: Path) -> None:
    context = bootstrap_context(tmp_path)

    run_cli(
        context,
        "record-source",
        "--scope",
        "demo.bridge",
        "--source-kind",
        "runtime",
        "--critique-status",
        "accepted",
        "--origin-kind",
        "command",
        "--origin-ref",
        "pytest bridge",
        "--quote",
        "check-r1 failed once and later recovered",
        "--note",
        "runtime source",
    )
    source_id = only_record_id(context, "source")

    run_cli(
        context,
        "record-claim",
        "--scope",
        "demo.bridge",
        "--plane",
        "runtime",
        "--status",
        "supported",
        "--statement",
        "Bridge check-r1 recovered after an earlier failure.",
        "--source",
        source_id,
        "--note",
        "supported runtime fact",
    )
    fact_id = only_record_id(context, "claim")

    run_cli(
        context,
        "record-claim",
        "--scope",
        "demo.bridge",
        "--plane",
        "runtime",
        "--status",
        "tentative",
        "--statement",
        "The first failure may be caused by stale R1 connection state.",
        "--source",
        source_id,
        "--note",
        "exploration hypothesis claim",
    )
    claims = sorted((context / "records" / "claim").glob("*.json"))
    hypothesis_id = [path.stem for path in claims if path.stem != fact_id][0]

    run_cli(
        context,
        "hypothesis",
        "add",
        "--claim",
        hypothesis_id,
        "--mode",
        "exploration",
        "--based-on-hypothesis",
        hypothesis_id,
        "--note",
        "local exploration only",
    )

    blocked_chain = tmp_path / "blocked-evidence-chain.json"
    blocked_chain.write_text(
        json.dumps(
            {
                "task": "bad proof from exploration hypothesis",
                "nodes": [
                    {"role": "fact", "ref": fact_id, "quote": "Bridge check-r1 recovered"},
                    {
                        "role": "hypothesis",
                        "ref": hypothesis_id,
                        "quote": "stale R1 connection state",
                    },
                ],
                "edges": [{"from": fact_id, "to": hypothesis_id, "relation": "supports"}],
            }
        ),
        encoding="utf-8",
    )
    blocked = run_cli(context, "validate-evidence-chain", "--file", str(blocked_chain), check=False)
    assert blocked.returncode == 1
    assert "evidence chains cannot use unconfirmed exploration hypotheses as proof" in blocked.stdout

    context_chain = tmp_path / "exploration-context-chain.json"
    context_chain.write_text(
        json.dumps(
            {
                "task": "request safe probe for exploration hypothesis",
                "nodes": [
                    {"role": "fact", "ref": fact_id, "quote": "Bridge check-r1 recovered"},
                    {
                        "role": "exploration_context",
                        "ref": hypothesis_id,
                        "quote": "stale R1 connection state",
                    },
                    {
                        "role": "requested_permission",
                        "ref": "REQ-safe-probe",
                        "quote": "Run a safe probe to test stale R1 connection state.",
                    },
                ],
                "edges": [
                    {"from": fact_id, "to": "REQ-safe-probe", "relation": "justifies-request"},
                    {"from": hypothesis_id, "to": "REQ-safe-probe", "relation": "motivates-probe"},
                ],
            }
        ),
        encoding="utf-8",
    )
    allowed = run_cli(context, "validate-evidence-chain", "--file", str(context_chain))
    assert "evidence chain is mechanically valid" in allowed.stdout


def test_review_reindex_and_scan_report_conflicts_without_aborting(tmp_path: Path) -> None:
    context = bootstrap_context(tmp_path)

    run_cli(
        context,
        "record-source",
        "--scope",
        "demo.conflict",
        "--source-kind",
        "runtime",
        "--critique-status",
        "accepted",
        "--origin-kind",
        "command",
        "--origin-ref",
        "pytest conflict",
        "--quote",
        "observed flag state",
        "--note",
        "runtime source",
    )
    source_id = only_record_id(context, "source")

    for value, statement, note in [
        ("true", "Flag is true.", "supported claim one"),
        ("false", "Flag is false.", "supported claim two"),
    ]:
        run_cli(
            context,
            "record-claim",
            "--scope",
            "demo.conflict",
            "--plane",
            "runtime",
            "--status",
            "supported",
            "--statement",
            statement,
            "--source",
            source_id,
            "--comparison-key",
            "demo.flag",
            "--comparison-subject",
            "demo flag",
            "--comparison-aspect",
            "state",
            "--comparison-comparator",
            "boolean",
            "--comparison-value",
            value,
            "--comparison-polarity",
            "affirmed",
            "--note",
            note,
        )

    for command in ("review-context", "reindex-context", "scan-conflicts"):
        result = run_cli(context, command, check=False)
        assert result.returncode == 0
        assert "1 conflict issue(s)" in result.stdout

    conflict_report = (context / "review" / "conflicts.md").read_text(encoding="utf-8")
    assert "demo.flag" in conflict_report


def test_review_still_fails_on_structural_validation_errors(tmp_path: Path) -> None:
    context = bootstrap_context(tmp_path)
    bad_record = context / "records" / "claim" / "CLM-20260416-9999.json"
    bad_record.write_text(
        json.dumps(
            {
                "id": "CLM-20260416-9999",
                "record_type": "claim",
                "scope": "demo.invalid",
                "note": "invalid claim missing required fields",
            }
        ),
        encoding="utf-8",
    )

    result = run_cli(context, "review-context", check=False)
    assert result.returncode == 1
    assert "invalid plane" in result.stdout


def test_guidelines_store_operational_coding_rules_separately_from_claims(tmp_path: Path) -> None:
    context = bootstrap_context(tmp_path)

    run_cli(
        context,
        "record-project",
        "--project-key",
        "smartpick",
        "--title",
        "Smartpick",
        "--root-ref",
        "/tmp/smartpick",
        "--note",
        "project boundary",
    )
    project_id = only_record_id(context, "project")
    run_cli(context, "set-current-project", "--project", project_id)

    run_cli(
        context,
        "record-source",
        "--scope",
        "smartpick.tests",
        "--source-kind",
        "theory",
        "--critique-status",
        "accepted",
        "--origin-kind",
        "user",
        "--origin-ref",
        "thread instruction",
        "--quote",
        "Write browser E2E tests through page objects, not raw selectors.",
        "--note",
        "user coding convention",
    )
    source_id = only_record_id(context, "source")

    run_cli(
        context,
        "record-claim",
        "--scope",
        "smartpick.tests",
        "--plane",
        "theory",
        "--status",
        "supported",
        "--statement",
        "The user supplied a project testing convention for browser E2E tests.",
        "--source",
        source_id,
        "--note",
        "supported user instruction claim",
    )
    claim_id = only_record_id(context, "claim")

    run_cli(
        context,
        "record-guideline",
        "--scope",
        "smartpick.tests",
        "--domain",
        "tests",
        "--applies-to",
        "project",
        "--priority",
        "preferred",
        "--rule",
        "Write browser E2E tests through page objects, not raw selectors.",
        "--source",
        source_id,
        "--example",
        "Use PickerPage.open() instead of duplicating selector setup.",
        "--rationale",
        "Keeps tests resilient to UI refactors.",
        "--note",
        "project testing convention",
    )
    guideline_id = only_record_id(context, "guideline")
    guideline = load_record(context, "guideline", guideline_id)
    assert guideline["project_refs"] == [project_id]
    assert guideline["priority"] == "preferred"

    shown = run_cli(context, "show-guidelines", "--domain", "tests")
    assert guideline_id in shown.stdout
    assert "page objects" in shown.stdout

    brief = run_cli(context, "brief-context", "--task", "write browser e2e tests")
    assert "## Controls" in brief.stdout
    assert guideline_id in brief.stdout

    run_cli(context, "review-context")
    attention = (context / "review" / "attention.md").read_text(encoding="utf-8")
    assert "Active Guidelines" in attention
    assert guideline_id in attention

    chain = tmp_path / "guideline-chain.json"
    chain.write_text(
        json.dumps(
            {
                "task": "request permission using guideline context",
                "nodes": [
                    {
                        "role": "fact",
                        "ref": claim_id,
                        "quote": "project testing convention",
                    },
                    {
                        "role": "guideline",
                        "ref": guideline_id,
                        "quote": "Write browser E2E tests through page objects",
                    },
                    {
                        "role": "requested_permission",
                        "ref": "REQ-test-refactor",
                        "quote": "Update tests to follow the page object guideline.",
                    },
                ],
                "edges": [
                    {"from": claim_id, "to": "REQ-test-refactor", "relation": "justifies-request"},
                    {"from": guideline_id, "to": "REQ-test-refactor", "relation": "guides-action"},
                ],
            }
        ),
        encoding="utf-8",
    )
    valid = run_cli(context, "validate-evidence-chain", "--file", str(chain))
    assert "evidence chain is mechanically valid" in valid.stdout


def test_workspace_commands_make_workspace_explicit_and_support_legacy_assignment(tmp_path: Path) -> None:
    context = bootstrap_context(tmp_path)

    run_cli(
        context,
        "record-source",
        "--scope",
        "legacy.import",
        "--source-kind",
        "runtime",
        "--critique-status",
        "accepted",
        "--origin-kind",
        "command",
        "--origin-ref",
        "legacy import",
        "--quote",
        "legacy source before workspace assignment",
        "--note",
        "legacy source",
    )
    source_id = only_record_id(context, "source")
    source = load_record(context, "source", source_id)
    assert "workspace_refs" not in source

    run_cli(
        context,
        "record-workspace",
        "--workspace-key",
        "qa-tim",
        "--title",
        "QA TIM Workspace",
        "--root-ref",
        "/tmp/pray-and-run",
        "--note",
        "workspace boundary",
    )
    workspace_id = only_record_id(context, "workspace")
    run_cli(context, "set-current-workspace", "--workspace", workspace_id)

    show = run_cli(context, "show-workspace")
    assert f"`{workspace_id}` status=`active` key=`qa-tim`" in show.stdout

    run_cli(
        context,
        "record-project",
        "--project-key",
        "smartpick",
        "--title",
        "SmartPick",
        "--root-ref",
        "/tmp/smartpick",
        "--note",
        "project inside current workspace",
    )
    project_id = only_record_id(context, "project")
    project = load_record(context, "project", project_id)
    workspace = load_record(context, "workspace", workspace_id)
    assert project["workspace_refs"] == [workspace_id]
    assert workspace["project_refs"] == [project_id]

    workdir = tmp_path / "anchored-workdir"
    workdir.mkdir()
    run_cli(
        context,
        "init-anchor",
        "--directory",
        str(workdir),
        "--workspace",
        workspace_id,
        "--project",
        project_id,
        "--allowed-freedom",
        "proof-only",
        "--note",
        "local test anchor",
    )
    anchor = json.loads((workdir / ".tep").read_text(encoding="utf-8"))
    assert anchor["context_root"] == str(context)
    assert anchor["workspace_ref"] == workspace_id
    assert anchor["project_ref"] == project_id

    anchored_show = subprocess.run(
        [sys.executable, str(CLI), "show-workspace"],
        cwd=workdir,
        capture_output=True,
        text=True,
        check=False,
    )
    assert anchored_show.returncode == 0, anchored_show.stderr
    assert f"`{workspace_id}` status=`active` key=`qa-tim`" in anchored_show.stdout

    validate_anchor = subprocess.run(
        [sys.executable, str(CLI), "validate-anchor"],
        cwd=workdir,
        capture_output=True,
        text=True,
        check=False,
    )
    assert validate_anchor.returncode == 0, validate_anchor.stdout + validate_anchor.stderr

    run_cli(context, "assign-workspace", "--workspace", workspace_id, "--all-unassigned")
    assigned = load_record(context, "source", source_id)
    assert assigned["workspace_refs"] == [workspace_id]

    run_cli(
        context,
        "record-source",
        "--scope",
        "qa-tim.runtime",
        "--source-kind",
        "runtime",
        "--critique-status",
        "accepted",
        "--origin-kind",
        "command",
        "--origin-ref",
        "current workspace",
        "--quote",
        "new source inherits workspace",
        "--note",
        "current workspace source",
    )
    new_source_id = next(
        path.stem
        for path in (context / "records" / "source").glob("*.json")
        if "new source inherits workspace" in path.read_text(encoding="utf-8")
    )
    new_source = load_record(context, "source", new_source_id)
    assert new_source["workspace_refs"] == [workspace_id]


def test_proposals_are_recorded_scoped_surfaced_and_not_proof(tmp_path: Path) -> None:
    context = bootstrap_context(tmp_path)

    run_cli(
        context,
        "record-source",
        "--scope",
        "proposal.demo",
        "--source-kind",
        "runtime",
        "--critique-status",
        "accepted",
        "--origin-kind",
        "command",
        "--origin-ref",
        "pytest proposal",
        "--quote",
        "Focused regression tests are cheaper to validate than broad refactors.",
        "--note",
        "proposal source",
    )
    source_id = only_record_id(context, "source")
    run_cli(
        context,
        "record-claim",
        "--scope",
        "proposal.demo",
        "--plane",
        "runtime",
        "--status",
        "supported",
        "--statement",
        "Focused regression tests are cheaper to validate than broad refactors.",
        "--source",
        source_id,
        "--note",
        "supported proposal anchor",
    )
    claim_id = only_record_id(context, "claim")

    run_cli(
        context,
        "record-proposal",
        "--scope",
        "proposal.demo",
        "--subject",
        "Retry test strategy",
        "--position",
        "Prefer a focused regression test before broad refactoring.",
        "--proposal",
        "Add focused retry regression first|It preserves the observed failure boundary.|May need a second pass;Avoids premature refactor|recommended",
        "--claim",
        claim_id,
        "--assumption",
        "The failure is local to retry behavior until contradicted.",
        "--risk",
        "The runtime observation may be stale.",
        "--stop-condition",
        "Stop if a new supported claim shows the failure is orchestration-wide.",
        "--note",
        "constructive proposal record",
    )
    proposal_id = only_record_id(context, "proposal")
    assert re.match(r"^PRP-\d{8}-[0-9a-f]{8}$", proposal_id)
    proposal = load_record(context, "proposal", proposal_id)
    assert proposal["claim_refs"] == [claim_id]
    assert proposal["proposals"][0]["recommended"] is True

    brief = run_cli(context, "brief-context", "--task", "retry test strategy").stdout
    assert "## Follow-ups" in brief
    assert proposal_id in brief
    assert "Prefer a focused regression test" in brief

    run_cli(context, "review-context")
    attention = (context / "review" / "attention.md").read_text(encoding="utf-8")
    assert "Active Proposals" in attention
    assert proposal_id in attention

    chain = tmp_path / "proposal-chain.json"
    chain.write_text(
        json.dumps(
            {
                "task": "proposal is not proof",
                "nodes": [
                    {
                        "role": "proposal",
                        "ref": proposal_id,
                        "quote": "constructive proposal record",
                    },
                    {
                        "role": "fact",
                        "ref": claim_id,
                        "quote": "Focused regression tests are cheaper",
                    },
                ],
                "edges": [
                    {"from": proposal_id, "to": claim_id, "relation": "invalid-proof"},
                ],
            }
        ),
        encoding="utf-8",
    )
    invalid = run_cli(context, "validate-evidence-chain", "--file", str(chain), check=False)
    assert invalid.returncode == 1
    assert "proposal" in invalid.stdout
