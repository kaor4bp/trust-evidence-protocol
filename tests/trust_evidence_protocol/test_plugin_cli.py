from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import zipfile
from datetime import datetime
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
PLUGIN_ROOT = REPO_ROOT / "plugins" / "trust-evidence-protocol"
SKILL_ROOT = PLUGIN_ROOT / "skills" / "trust-evidence-protocol"
CURATOR_SKILL_ROOT = PLUGIN_ROOT / "skills" / "trust-evidence-curator"
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
    match = re.search(rf"(?:Recorded|Started) {record_type} ([A-Z]+-\d{{8}}-[0-9a-f]{{8}})", result.stdout)
    assert match, result.stdout
    return match.group(1)


def load_record(context: Path, record_type: str, record_id: str) -> dict:
    return json.loads((context / "records" / record_type / f"{record_id}.json").read_text(encoding="utf-8"))


def user_confirmed_theory_claim(context: Path, scope: str, statement: str) -> str:
    source_id = recorded_id(
        run_cli(
            context,
            "record-source",
            "--scope",
            scope,
            "--source-kind",
            "theory",
            "--critique-status",
            "accepted",
            "--origin-kind",
            "user",
            "--origin-ref",
            "pytest user confirmation",
            "--quote",
            statement,
            "--note",
            "user-confirmed theory source",
        ),
        "source",
    )
    return recorded_id(
        run_cli(
            context,
            "record-claim",
            "--scope",
            scope,
            "--plane",
            "theory",
            "--status",
            "supported",
            "--statement",
            statement,
            "--source",
            source_id,
            "--note",
            "user-confirmed theory claim",
        ),
        "claim",
    )


def test_record_evidence_creates_source_claim_and_classifies_input(tmp_path: Path) -> None:
    context = bootstrap_context(tmp_path)
    input_id = recorded_id(
        run_cli(
            context,
            "record-input",
            "--scope",
            "demo.record-evidence",
            "--input-kind",
            "user_prompt",
            "--origin-kind",
            "user",
            "--origin-ref",
            "pytest prompt",
            "--text",
            "User confirmed that cache refresh happens only at startup.",
            "--note",
            "prompt provenance",
        ),
        "input",
    )

    result = run_cli(
        context,
        "record-evidence",
        "--scope",
        "demo.record-evidence",
        "--kind",
        "user-confirmation",
        "--input",
        input_id,
        "--quote",
        "User confirmed that cache refresh happens only at startup.",
        "--claim",
        "Cache refresh happens only at application startup.",
        "--claim-status",
        "supported",
        "--claim-kind",
        "factual",
        "--note",
        "mechanical user-confirmed evidence",
    )
    source_id = recorded_id(result, "source")
    claim_id = recorded_id(result, "claim")

    source = load_record(context, "source", source_id)
    claim = load_record(context, "claim", claim_id)
    input_record = load_record(context, "input", input_id)
    assert source["source_kind"] == "theory"
    assert source["origin"]["kind"] == "user_prompt"
    assert source["origin"]["ref"] == f"inputs:{input_id}"
    assert source["input_refs"] == [input_id]
    assert claim["plane"] == "theory"
    assert claim["status"] == "supported"
    assert claim["source_refs"] == [source_id]
    assert claim["input_refs"] == [input_id]
    assert input_record["derived_record_refs"] == [claim_id, source_id]

    model_result = run_cli(
        context,
        "record-model",
        "--knowledge-class",
        "domain",
        "--domain",
        "cache",
        "--scope",
        "demo.record-evidence",
        "--aspect",
        "refresh",
        "--status",
        "working",
        "--summary",
        "Cache refresh is startup-bound.",
        "--claim",
        claim_id,
        "--note",
        "model from user-confirmed theory claim",
        check=False,
    )
    assert model_result.returncode == 0, model_result.stdout


def test_task_decomposition_cli_confirms_atomic_and_creates_subtasks(tmp_path: Path) -> None:
    context = bootstrap_context(tmp_path)
    start = run_cli(
        context,
        "start-task",
        "--scope",
        "demo.decomposition",
        "--title",
        "Implement graph v2",
        "--type",
        "implementation",
        "--note",
        "task needs explicit decomposition",
    )
    task_id = recorded_id(start, "task")

    missing = run_cli(context, "validate-task-decomposition", "--task", task_id, check=False)
    assert missing.returncode == 1
    assert "needs-decomposition" in missing.stdout

    run_cli(
        context,
        "confirm-atomic-task",
        "--task",
        task_id,
        "--deliverable",
        "Task decomposition validator is implemented.",
        "--done",
        "Validator rejects tasks without decomposition.",
        "--verify",
        "Targeted pytest passes.",
        "--boundary",
        "Only task decomposition runtime behavior.",
        "--blocker-policy",
        "Record OPEN-* for user decisions.",
        "--note",
        "confirmed as one-pass task",
    )
    task = load_record(context, "task", task_id)
    assert task["decomposition"]["status"] == "atomic"
    assert task["decomposition"]["one_pass"] is True
    assert task["decomposition"]["deliverable"] == "Task decomposition validator is implemented."
    accepted = run_cli(context, "validate-task-decomposition", "--task", task_id)
    assert "accepted=True" in accepted.stdout

    second_context = bootstrap_context(tmp_path / "decomposed")
    parent = recorded_id(
        run_cli(
            second_context,
            "start-task",
            "--scope",
            "demo.parent",
            "--title",
            "Rebuild TEP API",
            "--type",
            "implementation",
            "--note",
            "parent orchestration task",
        ),
        "task",
    )
    split = run_cli(
        second_context,
        "decompose-task",
        "--task",
        parent,
        "--subtask",
        "demo.parent.task-decomposition|Implement decomposition API|Working TASK split commands|Commands pass CLI tests|pytest test_plugin_cli.py|Only TASK/PLAN split behavior",
        "--note",
        "split into one leaf task",
    )
    child_id = recorded_id(split, "task")
    parent_task = load_record(second_context, "task", parent)
    child_task = load_record(second_context, "task", child_id)
    assert parent_task["decomposition"]["status"] == "decomposed"
    assert parent_task["decomposition"]["subtask_refs"] == [child_id]
    assert child_task["parent_task_refs"] == [parent]
    assert child_task["decomposition"]["status"] == "atomic"
    assert child_task["decomposition"]["scope_boundary"] == "Only TASK/PLAN split behavior"
    validated_parent = run_cli(second_context, "validate-task-decomposition", "--task", parent)
    assert "accepted=True" in validated_parent.stdout


def test_plan_decomposition_cli_confirms_atomic_plan(tmp_path: Path) -> None:
    context = bootstrap_context(tmp_path)
    claim_id = user_confirmed_theory_claim(
        context,
        "demo.plan-decomposition",
        "Plans should be executable only after decomposition is explicit.",
    )
    plan_id = recorded_id(
        run_cli(
            context,
            "record-plan",
            "--scope",
            "demo.plan-decomposition",
            "--title",
            "Add plan decomposition",
            "--priority",
            "high",
            "--justify",
            claim_id,
            "--step",
            "Implement validators.",
            "--success",
            "Plan decomposition check passes.",
            "--note",
            "plan needs explicit decomposition",
        ),
        "plan",
    )

    missing = run_cli(context, "validate-plan-decomposition", "--plan", plan_id, check=False)
    assert missing.returncode == 1
    assert "needs-decomposition" in missing.stdout

    run_cli(
        context,
        "confirm-atomic-plan",
        "--plan",
        plan_id,
        "--note",
        "existing plan steps are one-pass executable",
    )
    plan = load_record(context, "plan", plan_id)
    assert plan["decomposition"] == {
        "status": "atomic",
        "one_pass": True,
        "task_ref": "",
    }
    accepted = run_cli(context, "validate-plan-decomposition", "--plan", plan_id)
    assert "accepted=True" in accepted.stdout

    parent_plan = recorded_id(
        run_cli(
            context,
            "record-plan",
            "--scope",
            "demo.plan-decomposition.parent",
            "--title",
            "Parent plan",
            "--priority",
            "medium",
            "--justify",
            claim_id,
            "--step",
            "Split plan.",
            "--success",
            "Child plan is executable.",
            "--note",
            "parent plan needs subplans",
        ),
        "plan",
    )
    split = run_cli(
        context,
        "decompose-plan",
        "--plan",
        parent_plan,
        "--subplan",
        f"demo.plan-decomposition.child|Child plan|Implement child behavior|Child plan passes tests|{claim_id}",
        "--note",
        "split parent plan into child plan",
    )
    child_plan = recorded_id(split, "plan")
    parent = load_record(context, "plan", parent_plan)
    child = load_record(context, "plan", child_plan)
    assert parent["decomposition"]["status"] == "decomposed"
    assert parent["decomposition"]["subplan_refs"] == [child_plan]
    assert child["parent_plan_refs"] == [parent_plan]
    assert child["decomposition"]["status"] == "atomic"
    accepted_parent = run_cli(context, "validate-plan-decomposition", "--plan", parent_plan)
    assert "accepted=True" in accepted_parent.stdout


def test_record_evidence_maps_file_and_command_evidence(tmp_path: Path) -> None:
    context = bootstrap_context(tmp_path)
    project_file = tmp_path / "src" / "cache.py"
    project_file.parent.mkdir(parents=True)
    project_file.write_text("def refresh_cache():\n    return True\n", encoding="utf-8")
    command_result = run_cli(
        context,
        "record-evidence",
        "--scope",
        "demo.record-evidence.command",
        "--kind",
        "command-output",
        "--command",
        "uv run pytest tests/unit/test_cache.py -q",
        "--exit-code",
        "0",
        "--quote",
        "1 passed",
        "--claim",
        "The focused cache test passed.",
        "--claim-status",
        "supported",
        "--note",
        "focused runtime evidence",
    )
    command_source_id = recorded_id(command_result, "source")
    command_claim_id = recorded_id(command_result, "claim")
    command_run_id = only_record_id(context, "run")
    command_source = load_record(context, "source", command_source_id)
    command_claim = load_record(context, "claim", command_claim_id)
    command_run = load_record(context, "run", command_run_id)
    assert command_source["source_kind"] == "runtime"
    assert command_source["origin"] == {
        "kind": "command",
        "ref": "uv run pytest tests/unit/test_cache.py -q",
    }
    assert command_source["run_refs"] == [command_run_id]
    assert command_claim["plane"] == "runtime"
    assert command_claim["run_refs"] == [command_run_id]
    assert command_run["status"] == "completed"

    file_result = run_cli(
        context,
        "record-evidence",
        "--scope",
        "demo.record-evidence.file",
        "--kind",
        "file-line",
        "--path",
        str(project_file),
        "--line",
        "12",
        "--end-line",
        "14",
        "--quote",
        "def refresh_cache():",
        "--claim",
        "src/cache.py defines refresh_cache.",
        "--claim-status",
        "supported",
        "--note",
        "file-line evidence",
    )
    file_source_id = recorded_id(file_result, "source")
    file_claim_id = recorded_id(file_result, "claim")
    file_record_id = only_record_id(context, "file")
    file_source = load_record(context, "source", file_source_id)
    file_claim = load_record(context, "claim", file_claim_id)
    file_record = load_record(context, "file", file_record_id)
    assert file_source["source_kind"] == "code"
    assert file_source["origin"] == {"kind": "file", "ref": f"{project_file}:12-14"}
    assert file_source["file_refs"] == [file_record_id]
    assert file_claim["plane"] == "code"
    assert file_record["metadata"]["exists"] is True
    assert file_record["artifact_refs"]


def test_record_support_is_graph_v2_front_door(tmp_path: Path) -> None:
    context = bootstrap_context(tmp_path)

    result = run_cli(
        context,
        "record-support",
        "--scope",
        "demo.record-support",
        "--kind",
        "command-output",
        "--command",
        "uv run pytest tests/unit/test_cache.py -q",
        "--exit-code",
        "0",
        "--quote",
        "1 passed",
        "--thought",
        "The cache unit test passed.",
        "--note",
        "front-door support capture",
    )
    source_id = recorded_id(result, "source")
    claim_id = recorded_id(result, "claim")
    run_id = only_record_id(context, "run")

    source = load_record(context, "source", source_id)
    claim = load_record(context, "claim", claim_id)
    assert "graph-v2" in source["tags"]
    assert source["run_refs"] == [run_id]
    assert claim["run_refs"] == [run_id]
    assert claim["statement"] == "The cache unit test passed."


def test_record_evidence_rejects_incomplete_structured_origin(tmp_path: Path) -> None:
    context = bootstrap_context(tmp_path)

    missing_path = run_cli(
        context,
        "record-evidence",
        "--scope",
        "demo.record-evidence.invalid",
        "--kind",
        "file-line",
        "--line",
        "1",
        "--quote",
        "x",
        "--claim",
        "x exists.",
        check=False,
    )
    assert missing_path.returncode == 1
    assert "requires --path" in missing_path.stdout


def test_install_local_plugin_script_creates_single_active_cache_version(tmp_path: Path) -> None:
    local_source = tmp_path / "plugins" / "trust-evidence-protocol"
    cache = tmp_path / "cache" / "trust-evidence-protocol"
    claude_cache = tmp_path / "claude-cache" / "trust-evidence-protocol"
    version = json.loads((PLUGIN_ROOT / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8"))["version"]
    old_version = cache / "0.1.1"
    old_version.mkdir(parents=True)
    (old_version / "old.txt").write_text("old", encoding="utf-8")
    old_claude_version = claude_cache / "0.1.1"
    old_claude_version.mkdir(parents=True)
    (old_claude_version / "old.txt").write_text("old", encoding="utf-8")
    stale_local_bytecode = local_source / "tep_runtime" / "__pycache__"
    stale_cache_bytecode = cache / version / "tep_runtime" / "__pycache__"
    stale_local_bytecode.mkdir(parents=True)
    stale_cache_bytecode.mkdir(parents=True)
    (stale_local_bytecode / "stale.pyc").write_bytes(b"stale")
    (stale_cache_bytecode / "stale.pyc").write_bytes(b"stale")
    home = tmp_path / "home"
    codex_config = home / ".codex" / "config.toml"
    codex_config.parent.mkdir(parents=True)
    codex_config.write_text(
        "\n".join(
            [
                'model = "gpt-5.4"',
                "",
                "[mcp_servers.trust_evidence_protocol]",
                'args = ["/old/trust-evidence-protocol/0.1.1/mcp/tep_server.py"]',
                'command = "python3"',
                'cwd = "/old/trust-evidence-protocol/0.1.1"',
                "enabled = true",
                "",
                '[plugins."trust-evidence-protocol@home-local-plugins"]',
                "enabled = true",
                "",
            ]
        ),
        encoding="utf-8",
    )

    result = subprocess.run(
        [str(INSTALL_LOCAL_PLUGIN)],
        cwd=REPO_ROOT,
        env={
            **os.environ,
            "HOME": str(home),
            "TEP_LOCAL_PLUGIN_SOURCE": str(local_source),
            "TEP_CODEX_PLUGIN_CACHE": str(cache),
            "TEP_CLAUDE_PLUGIN_CACHE": str(claude_cache),
        },
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr

    assert (local_source / ".codex-plugin" / "plugin.json").is_file()
    assert (cache / version / ".codex-plugin" / "plugin.json").is_file()
    assert (claude_cache / version / ".claude-plugin" / "plugin.json").is_file()
    claude_manifest = json.loads(
        (claude_cache / version / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8")
    )
    assert claude_manifest["version"] == version
    assert claude_manifest["hooks"] == "./hooks/claude/hooks.json"
    claude_hooks = json.loads((claude_cache / version / "hooks" / "claude" / "hooks.json").read_text(encoding="utf-8"))
    user_prompt_command = claude_hooks["hooks"]["UserPromptSubmit"][0]["hooks"][0]["command"]
    assert "\"${CLAUDE_PLUGIN_ROOT}/hooks/claude/user_prompt_hydration_notice.py\"" in user_prompt_command
    stop_command = claude_hooks["hooks"]["Stop"][0]["hooks"][0]["command"]
    assert "\"${CLAUDE_PLUGIN_ROOT}/hooks/claude/stop_guard.py\"" in stop_command
    assert (cache / "_archived-pre-active" / "0.1.1" / "old.txt").read_text(encoding="utf-8") == "old"
    assert (claude_cache / "_archived-pre-active" / "0.1.1" / "old.txt").read_text(encoding="utf-8") == "old"
    active_dirs = sorted(path.name for path in cache.iterdir() if path.is_dir())
    assert active_dirs == [version, "_archived-pre-active"]
    active_claude_dirs = sorted(path.name for path in claude_cache.iterdir() if path.is_dir())
    assert active_claude_dirs == [version, "_archived-pre-active"]
    updated_config = codex_config.read_text(encoding="utf-8")
    assert f'args = ["{cache / version / "mcp" / "tep_server.py"}"]' in updated_config
    assert f'cwd = "{cache / version}"' in updated_config
    assert "/old/trust-evidence-protocol/0.1.1" not in updated_config
    installed_roots = [local_source, cache / version, claude_cache / version]
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
    assert len(skill.splitlines()) <= 160
    assert "route / next_step -> lookup -> support capture -> REASON step/review -> action/final" in skill
    assert "Command details belong in the plugin README, runtime help, and developer docs." in skill
    assert "workflows/plugin-commands.md" not in skill

    workflow_files = sorted(path.name for path in (SKILL_ROOT / "workflows").glob("*.md"))
    assert workflow_files == [
        "after-action.md",
        "before-action.md",
        "information-lookup.md",
        "persistence-and-records.md",
    ]
    assert (REPO_ROOT / "docs" / "reference" / "plugin-commands.md").exists()

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

    curator_skill = (CURATOR_SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
    assert len(curator_skill.splitlines()) <= 90
    assert "explicit `CURP-*` curator pool" in curator_skill
    assert "Do not use current `.tep` focus as authority." in curator_skill
    assert "run-runtime-commands" in curator_skill
    curator_ui = (CURATOR_SKILL_ROOT / "agents" / "openai.yaml").read_text(encoding="utf-8")
    assert "Trust Evidence Curator" in curator_ui


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

    assert "Input records are prompt provenance only" in result.stdout
    assert input_id.startswith("INP-")
    assert record["text"] == prompt
    assert record["input_kind"] == "user_prompt"
    assert record["origin"] == {"kind": "user", "ref": "chat-turn-1"}
    assert record["session_ref"] == "session-1"
    assert record["tags"] == ["guideline-candidate"]
    review = run_cli(context, "review-context")
    assert review.returncode == 0
    assert "unclassified input" in review.stdout
    input_review = (context / "review" / "inputs.md").read_text(encoding="utf-8")
    assert input_id in input_review
    assert "prompt provenance only" in input_review

    source_id = recorded_id(
        run_cli(
            context,
            "record-source",
            "--scope",
            "demo.input",
            "--source-kind",
            "memory",
            "--critique-status",
            "accepted",
            "--origin-kind",
            "input",
            "--origin-ref",
            input_id,
            "--quote",
            prompt,
            "--note",
            "classified prompt as source",
        ),
        "source",
    )
    classified = run_cli(
        context,
        "classify-input",
        "--input",
        input_id,
        "--derived-record",
        source_id,
        "--note",
        "prompt source captured",
    )
    assert f"Classified input {input_id}" in classified.stdout
    review = run_cli(context, "review-context")
    assert "unclassified input" not in review.stdout
    input_review = (context / "review" / "inputs.md").read_text(encoding="utf-8")
    assert input_id not in input_review


def test_input_triage_links_operational_prompts_without_promoting_to_facts(tmp_path: Path) -> None:
    context = bootstrap_context(tmp_path)
    task_id = recorded_id(
        run_cli(
            context,
            "start-task",
            "--scope",
            "demo.input-triage",
            "--title",
            "Input triage task",
            "--note",
            "triage focus",
        ),
        "task",
    )
    input_id = recorded_id(
        run_cli(
            context,
            "record-input",
            "--scope",
            "demo.input-triage",
            "--input-kind",
            "user_prompt",
            "--origin-kind",
            "user",
            "--origin-ref",
            "chat-operational",
            "--text",
            "continue autonomous work",
            "--task",
            task_id,
            "--note",
            "operational prompt",
        ),
        "input",
    )

    report = run_cli(context, "input-triage", "report", "--task", task_id).stdout
    assert input_id in report
    assert "not proof" in report

    linked = run_cli(context, "input-triage", "link-operational", "--task", task_id, "--input", input_id)
    assert "Linked 1 operational input(s)" in linked.stdout
    wctx_id = recorded_id(linked, "working_context")
    wctx = load_record(context, "working_context", wctx_id)
    assert wctx["input_refs"] == [input_id]
    assert wctx["task_refs"] == [task_id]

    review = run_cli(context, "review-context")
    assert "unclassified input" not in review.stdout
    input_review = (context / "review" / "inputs.md").read_text(encoding="utf-8")
    assert input_id not in input_review


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


def test_type_graph_reports_allowed_chains_and_scope_pressure(tmp_path: Path) -> None:
    context = bootstrap_context(tmp_path)
    task = run_cli(
        context,
        "start-task",
        "--type",
        "implementation",
        "--scope",
        "type.graph.demo",
        "--title",
        "Exercise type graph diagnostics",
        "--note",
        "active task should create WCTX pressure",
    )
    task_id = re.search(r"(TASK-\d{8}-[0-9a-f]{8})", task.stdout).group(1)
    cix_id = "CIX-20260420-badscope"
    cix_path = context / "code_index" / "entries" / f"{cix_id}.json"
    cix_path.parent.mkdir(parents=True, exist_ok=True)
    cix_path.write_text(
        json.dumps(
            {
                "id": cix_id,
                "record_type": "code_index_entry",
                "status": "active",
                "target": {"kind": "file", "path": "src/app.py"},
                "target_state": "present",
                "language": "python",
                "code_kind": "source",
                "summary": "unscoped active CIX should be a type-graph issue",
                "metadata": {},
                "detected_features": [],
                "manual_features": [],
                "manual_links": {},
                "annotations": [],
                "links": [],
                "child_entry_refs": [],
                "related_entry_refs": [],
                "supersedes_refs": [],
                "created_at": "2026-04-20T10:00:00+03:00",
                "updated_at": "2026-04-20T10:00:00+03:00",
                "note": "test fixture",
            }
        ),
        encoding="utf-8",
    )

    overview = run_cli(context, "type-graph")
    assert "CIX -/-> proof" in overview.stdout

    checked = run_cli(context, "type-graph", "--check", "--format", "json", check=False)
    assert checked.returncode == 1
    payload = json.loads(checked.stdout)
    assert payload["type_graph_is_proof"] is False
    assert any(item["kind"] == "active-cix-without-project" and item["ref"] == cix_id for item in payload["issues"])
    assert any(item["kind"] == "active-task-without-active-wctx" and item["ref"] == task_id for item in payload["warnings"])


def test_runtime_help_budget_task_modes_and_precedents(tmp_path: Path) -> None:
    context = bootstrap_context(tmp_path)

    help_text = run_cli(context, "help", "modes").stdout
    assert "precedent review" in help_text
    assert "type graph" in help_text
    assert "task control" in help_text
    assert "workspace admission" in help_text
    assert "--format json route_graph" in help_text

    alias_text = run_cli(context, "tep-help", "modes").stdout
    assert alias_text == help_text

    commands_help = run_cli(context, "help", "commands").stdout
    assert "next-step --intent answer|plan|edit|test|persist|permission|debug --task ... [--format json]" in commands_help
    assert "review-context | reindex-context | scan-conflicts | type-graph --check" in commands_help
    assert "record-detail --record ... | linked-records --record ..." in commands_help
    assert "guidelines-for --task ... | code-search [--query ...] [--fields target,symbols] | telemetry-report [--format json]" in commands_help
    assert "backend-status [--format json] | backend-check --backend derivation.datalog [--format json]" in commands_help
    assert "validate-facts --backend rdf_shacl [--format json]" in commands_help
    assert "export-rdf --format turtle|jsonld [--output path]" in commands_help
    assert "configure-runtime --backend-preset minimal|recommended" in commands_help
    assert "working-context create|fork|show|close|check-drift" in commands_help
    assert "curator-pool build --workspace WSP-*" in commands_help
    assert "workspace-admission check --repo path [--format json]" in commands_help
    assert "schema-migration plan [--migration ID] [--format json]" in commands_help

    configured = run_cli(
        context,
        "configure-runtime",
        "--hook-verbosity",
        "quiet",
        "--hook-run-capture",
        "all",
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
        "--backend",
        "code_intelligence.cocoindex.default_scope=workspace",
        "--backend",
        "code_intelligence.cocoindex.storage_root=<context>/backends/cocoindex",
        "--backend",
        "code_intelligence.cocoindex.workspace_glance=false",
    ).stdout
    assert "hooks.verbosity=quiet" in configured
    assert "hooks.run_capture=all" in configured
    assert "analysis.logic_solver.backend=z3" in configured
    assert "analysis.topic_prefilter.backend=nmf" in configured
    assert "backends.derivation.backend=datalog" in configured
    assert "backends.derivation.datalog.enabled=true" in configured
    assert "backends.code_intelligence.cocoindex.default_scope=workspace" in configured
    settings = json.loads((context / "settings.json").read_text(encoding="utf-8"))
    assert settings["hooks"]["verbosity"] == "quiet"
    assert settings["hooks"]["run_capture"] == "all"
    assert settings["context_budget"]["hydration"] == "compact"
    assert settings["analysis"]["logic_solver"]["backend"] == "z3"
    assert settings["analysis"]["logic_solver"]["install_policy"] == "ask"
    assert settings["analysis"]["topic_prefilter"]["backend"] == "nmf"
    assert settings["analysis"]["topic_prefilter"]["rebuild"] == "manual"
    assert settings["backends"]["derivation"]["backend"] == "datalog"
    assert settings["backends"]["derivation"]["datalog"]["enabled"] is True
    assert settings["backends"]["derivation"]["datalog"]["mode"] == "fake"
    assert settings["backends"]["code_intelligence"]["cocoindex"]["default_scope"] == "workspace"
    assert settings["backends"]["code_intelligence"]["cocoindex"]["storage_root"] == "<context>/backends/cocoindex"
    assert settings["backends"]["code_intelligence"]["cocoindex"]["workspace_glance"] is False

    invalid_analysis = run_cli(context, "configure-runtime", "--analysis", "logic_solver.backend=bad", check=False)
    assert invalid_analysis.returncode == 1
    assert "invalid value for analysis.logic_solver.backend" in invalid_analysis.stdout
    invalid_backend = run_cli(context, "configure-runtime", "--backend", "code_intelligence.backend=ctags", check=False)
    assert invalid_backend.returncode == 1
    assert "backends.code_intelligence.backend has invalid value" in invalid_backend.stdout

    workspace_id = recorded_id(
        run_cli(
            context,
            "record-workspace",
            "--workspace-key",
            "backend-status-workspace",
            "--title",
            "Backend status workspace",
            "--root-ref",
            str(context),
            "--note",
            "backend status diagnostics",
        ),
        "workspace",
    )
    run_cli(context, "set-current-workspace", "--workspace", workspace_id)
    status_payload = json.loads(
        run_cli(context, "backend-status", "--root", str(context), "--scope", "workspace", "--format", "json").stdout
    )
    assert status_payload["backend_status_is_proof"] is False
    assert status_payload["groups"]["derivation"]["selected"] == "datalog"
    coco = next(item for item in status_payload["backends"] if item["id"] == "cocoindex")
    assert coco["effective_scope"] == "workspace"
    assert coco["storage"]["repo_root"] == str(context)
    assert coco["storage"]["scoped_db_dir"].endswith(f"/backends/cocoindex/workspaces/{workspace_id}/.cocoindex_code")
    assert any(item["id"] == "datalog" and item["available"] is True for item in status_payload["backends"])
    check_payload = json.loads(
        run_cli(
            context,
            "backend-check",
            "--backend",
            "code_intelligence.cocoindex",
            "--root",
            str(context),
            "--scope",
            "workspace",
            "--format",
            "json",
        ).stdout
    )
    assert check_payload["backend_status_is_proof"] is False
    assert check_payload["matches"][0]["backend_output_is_proof"] is False
    assert check_payload["matches"][0]["storage"]["repo_root"] == str(context)
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


def test_schema_migration_cli_plans_and_applies_record_shape_changes(tmp_path: Path) -> None:
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
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    planned = run_cli(context, "schema-migration", "plan", "--format", "json")
    plan = json.loads(planned.stdout)
    assert plan["mode"] == "dry-run"
    assert plan["applied"] is False
    assert plan["planned_actions"][0]["migration_id"] == "20260423_map_record_v1"
    assert "record_version" not in json.loads(map_file.read_text(encoding="utf-8"))

    applied = run_cli(context, "schema-migration", "apply", "--format", "json")
    report = json.loads(applied.stdout)
    assert report["mode"] == "apply"
    assert report["applied"] is True
    stored = json.loads(map_file.read_text(encoding="utf-8"))
    assert stored["contract_version"] == "0.4"
    assert stored["record_version"] == 1
    assert "schema_version" not in stored


def test_configure_runtime_backend_presets_make_backend_sets_explicit(tmp_path: Path) -> None:
    context = bootstrap_context(tmp_path)

    recommended = run_cli(context, "configure-runtime", "--backend-preset", "recommended").stdout
    assert "backends.code_intelligence.backend=serena" in recommended
    assert "backends.code_intelligence.serena.enabled=true" in recommended
    assert "backends.code_intelligence.cocoindex.enabled=true" in recommended
    assert "backends.code_intelligence.cocoindex.default_scope=project" in recommended
    status = json.loads(run_cli(context, "backend-status", "--format", "json").stdout)
    assert status["groups"]["code_intelligence"]["selected"] == "serena"
    assert any(item["id"] == "serena" and item["selected"] is True for item in status["backends"])
    assert any(item["id"] == "cocoindex" and item["enabled"] is True for item in status["backends"])

    minimal = run_cli(context, "configure-runtime", "--backend-preset", "minimal").stdout
    assert "backends.code_intelligence.backend=builtin" in minimal
    assert "backends.code_intelligence.serena.enabled=false" in minimal
    assert "backends.code_intelligence.cocoindex.enabled=false" in minimal
    assert "backends.fact_validation.rdf_shacl.enabled=false" in minimal
    assert "backends.derivation.datalog.enabled=false" in minimal
    status = json.loads(run_cli(context, "backend-status", "--format", "json").stdout)
    assert status["groups"]["code_intelligence"]["selected"] == "builtin"
    assert all(
        not item["enabled"]
        for item in status["backends"]
        if item["id"] in {"serena", "cocoindex", "datalog", "rdf_shacl"}
    )


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
    input_id = recorded_id(
        run_cli(
            context,
            "record-input",
            "--scope",
            "attention.demo",
            "--input-kind",
            "user_prompt",
            "--origin-kind",
            "user",
            "--origin-ref",
            "pytest",
            "--text",
            "Please inspect the attention map.",
            "--derived-record",
            tapped_claim_id,
            "--note",
            "input should be hidden in code/theory visual modes",
        ),
        "input",
    )
    guideline_id = recorded_id(
        run_cli(
            context,
            "record-guideline",
            "--scope",
            "attention.demo",
            "--domain",
            "agent-behavior",
            "--applies-to",
            "global",
            "--priority",
            "preferred",
            "--rule",
            "Use curiosity-map before spending tokens on broad manual exploration.",
            "--source",
            source_id,
            "--note",
            "guideline should be hidden in research/theory visual modes",
        ),
        "guideline",
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
    curiosity_map = json.loads(run_cli(context, "curiosity-map", "--volume", "compact", "--scope", "all", "--format", "json").stdout)
    assert curiosity_map["map_is_proof"] is False
    assert curiosity_map["attention_index_is_proof"] is False
    assert curiosity_map["mode"] == "general"
    assert curiosity_map["volume"] == "compact"
    assert curiosity_map["map_graph_version"] == "tep.map_graph.v1"
    assert curiosity_map["map_graph"]["format"] == "tep.map_graph.v1"
    assert curiosity_map["map_graph"]["graph_is_proof"] is False
    assert {layer["kind"] for layer in curiosity_map["map_graph"]["cluster_layers"]} == {"topic", "topology"}
    assert any(cluster["kind"] == "topology" for cluster in curiosity_map["map_graph"]["clusters"])
    assert any(edge["relation"] == "cites" for edge in curiosity_map["map_graph"]["edges"])
    assert curiosity_map["map_graph"]["relation_weights"]["candidate_link"] < curiosity_map["map_graph"]["relation_weights"]["supports"]
    assert curiosity_map["metrics"]["metrics_are_proof"] is False
    assert curiosity_map["metrics"]["cluster_count"] <= curiosity_map["budget"]["clusters"]
    assert curiosity_map["metrics"]["probe_count"] <= curiosity_map["budget"]["probes"]
    assert "graph TD" in curiosity_map["mermaid"]
    assert any(
        {facility_claim_id, program_claim_id}.issubset(set(prompt["record_refs"]))
        for prompt in curiosity_map["curiosity_prompts"]
    )
    map_brief = json.loads(run_cli(context, "map-brief", "--volume", "compact", "--scope", "all", "--limit", "4", "--format", "json").stdout)
    assert map_brief["map_brief_is_proof"] is False
    assert map_brief["map_graph_version"] == "tep.map_graph.v1"
    assert map_brief["summary"]["node_count"] == curiosity_map["map_graph"]["node_count"]
    assert map_brief["summary"]["bridge_node_count"] >= 0
    assert map_brief["topology_islands"]
    assert map_brief["candidate_probes"]
    assert any(command.startswith("probe-inspect") for command in map_brief["recommended_commands"])
    map_brief_text = run_cli(context, "map-brief", "--volume", "compact", "--scope", "all").stdout
    assert "# Map Brief" in map_brief_text
    assert "Topology Islands" in map_brief_text
    assert "Bridge Pressure" in map_brief_text
    assert "Use this brief to choose inspection order" in map_brief_text
    curiosity_map_text = run_cli(context, "curiosity-map", "--volume", "compact", "--scope", "all").stdout
    assert "# Curiosity Map" in curiosity_map_text
    assert "visual-thinking map" in curiosity_map_text
    assert "Curiosity Prompts" in curiosity_map_text
    assert "Use the map to decide what to inspect next" in curiosity_map_text
    html_map = json.loads(
        run_cli(context, "curiosity-map", "--volume", "compact", "--scope", "all", "--mode", "theory", "--html", "--format", "json").stdout
    )
    html_path = Path(html_map["html_path"])
    assert html_path == context / "views" / "curiosity" / "curiosity-map-all-theory-compact.html"
    assert html_path.exists()
    html_text = html_path.read_text(encoding="utf-8")
    assert "TEP Curiosity Map" in html_text
    assert "vis-network@10.0.2" in html_text
    assert "new vis.Network" in html_text
    assert "navigationButtons: true" in html_text
    assert "tep.map_graph.v1" in html_text
    assert "mapGraph" in html_text
    assert "Focus cold zones" in html_text
    assert "Focus topology" in html_text
    assert "Focus bridges" in html_text
    assert "topologyCluster" in html_text
    assert "Map edge" in html_text
    assert "cluster-list" in html_text
    assert "graph-data" in html_text
    assert "network.setOptions({ physics: false })" in html_text
    assert "stabilizationIterationsDone" in html_text
    assert "Generated navigation view only" in html_text
    assert facility_claim_id in html_text
    research_map = json.loads(
        run_cli(context, "curiosity-map", "--volume", "compact", "--scope", "all", "--mode", "research", "--format", "json").stdout
    )
    assert research_map["mode"] == "research"
    assert guideline_id not in research_map["records"]
    theory_attention = json.loads(run_cli(context, "attention-map", "--scope", "all", "--mode", "theory", "--format", "json").stdout)
    assert theory_attention["mode"] == "theory"
    assert input_id not in theory_attention["records"]
    assert guideline_id not in theory_attention["records"]
    code_attention = json.loads(run_cli(context, "attention-map", "--scope", "all", "--mode", "code", "--format", "json").stdout)
    assert code_attention["mode"] == "code"
    assert input_id not in code_attention["records"]
    assert tapped_claim_id not in code_attention["records"]
    workspace_id = recorded_id(
        run_cli(
            context,
            "record-workspace",
            "--workspace-key",
            "attention-demo",
            "--title",
            "Attention demo workspace",
            "--note",
            "workspace for lookup auto-WCTX test",
        ),
        "workspace",
    )
    run_cli(context, "set-current-workspace", "--workspace", workspace_id)
    refreshed_map = json.loads(
        run_cli(context, "map-refresh", "--volume", "compact", "--scope", "all", "--limit", "3", "--format", "json").stdout
    )
    assert refreshed_map["map_refresh_is_proof"] is False
    assert refreshed_map["attention_index_is_proof"] is False
    assert refreshed_map["applied"] is True
    assert refreshed_map["candidate_count"] >= 1
    assert refreshed_map["created_refs"]
    assert refreshed_map["updated_refs"] == []
    map_record_id = refreshed_map["created_refs"][0]
    map_record = load_record(context, "map", map_record_id)
    assert map_record["contract_version"] == "0.4"
    assert map_record["record_version"] == 1
    assert map_record["map_is_proof"] is False
    assert map_record["generated_by"] == "map_refresh"
    assert map_record["status"] == "active"
    assert map_record["scope_refs"]["workspace_refs"] == [workspace_id]
    assert map_record["proof_routes"][0]["required_drilldown"] is True
    assert set(map_record["anchor_refs"]).issubset(set(map_record["derived_from_refs"]))
    refreshed_again = json.loads(
        run_cli(context, "map-refresh", "--volume", "compact", "--scope", "all", "--limit", "3", "--format", "json").stdout
    )
    assert refreshed_again["created_refs"] == []
    assert map_record_id in refreshed_again["updated_refs"]
    dry_run = json.loads(
        run_cli(context, "map-refresh", "--volume", "compact", "--scope", "all", "--limit", "3", "--dry-run", "--format", "json").stdout
    )
    assert dry_run["applied"] is False
    lookup_facts = json.loads(
        run_cli(context, "lookup", "--query", "Facility Program relationship", "--reason", "curiosity", "--kind", "facts", "--format", "json").stdout
    )
    assert lookup_facts["lookup_is_proof"] is False
    assert lookup_facts["reason"] == "curiosity"
    assert lookup_facts["focus"]["working_context_ref"].startswith("WCTX-")
    assert lookup_facts["focus"]["auto_created_working_context"] is True
    assert lookup_facts["auto_created_working_context"]["not_proof"] is True
    auto_wctx = load_record(context, "working_context", lookup_facts["focus"]["working_context_ref"])
    assert auto_wctx["contract_version"] == "0.4"
    assert auto_wctx["record_version"] == 1
    assert auto_wctx["ownership_mode"] == "owner-only"
    assert auto_wctx["handoff_policy"] == "fork-required"
    assert auto_wctx["owner_signature"]["algorithm"] == "hmac-sha256"
    agent = load_record(context, "agent_identity", auto_wctx["agent_identity_ref"])
    assert agent["record_version"] == 1
    assert agent["key_fingerprint"] == auto_wctx["agent_key_fingerprint"]
    assert "secret" not in agent
    assert (context / "runtime" / "agent_identity" / "local_agent_key.json").exists()
    assert lookup_facts["primary_tool"] == "claim-graph"
    assert lookup_facts["api_contract_version"] == 1
    assert lookup_facts["evidence_profile"]["normal_entrypoint"] == "lookup"
    assert "record-detail" in lookup_facts["evidence_profile"]["drill_down_tools"]
    assert lookup_facts["output_contract"]["if_new_support_found"].startswith("use record-support/record-evidence")
    assert lookup_facts["route_graph"]["entrypoint"] == "lookup"
    assert lookup_facts["next_allowed_commands"] == lookup_facts["route"]
    assert lookup_facts["map_navigation"]["map_navigation_is_proof"] is False
    assert lookup_facts["map_navigation"]["cells"][0]["ref"] == map_record_id
    assert lookup_facts["map_navigation"]["cells"][0]["map_is_proof"] is False
    assert any(command.startswith("map-open") for command in lookup_facts["route"])
    assert any(command.startswith("claim-graph") for command in lookup_facts["route"])
    chain_starter = lookup_facts["chain_starter"]
    assert chain_starter["chain_starter_is_proof"] is False
    assert chain_starter["decision_mode"] == "curiosity"
    assert chain_starter["validation_preview"]["ok"] is True
    assert any(node["ref"] == facility_claim_id and node["role"] == "fact" for node in chain_starter["nodes"])
    assert any(node["ref"] == program_claim_id and node["role"] == "fact" for node in chain_starter["nodes"])
    assert any(command.startswith("augment-chain") for command in chain_starter["next_commands"])
    assert any(command.startswith("validate-decision --mode curiosity") for command in chain_starter["next_commands"])
    lookup_text = run_cli(context, "lookup", "--query", "Facility Program relationship", "--reason", "curiosity", "--kind", "facts").stdout
    assert "## MAP Navigation" in lookup_text
    assert "## Chain Starter" in lookup_text
    assert "validate-decision --mode curiosity" in lookup_text
    lookup_code = json.loads(
        run_cli(
            context,
            "lookup",
            "--query",
            "code function import lookup",
            "--reason",
            "orientation",
            "--kind",
            "auto",
            "--root",
            str(tmp_path),
            "--format",
            "json",
        ).stdout
    )
    assert lookup_code["kind"] == "code"
    assert lookup_code["reason"] == "orientation"
    assert lookup_code["focus"]["working_context_ref"] == lookup_facts["focus"]["working_context_ref"]
    assert lookup_code["mode"] == "code"
    assert lookup_code["primary_tool"] == "code-search"
    assert any("code-search" in command for command in lookup_code["route"])
    assert all(not node["ref"].startswith("CIX-") for node in lookup_code["chain_starter"]["nodes"])
    lookup_telemetry = json.loads(run_cli(context, "telemetry-report", "--format", "json").stdout)
    assert lookup_telemetry["by_reason"]["curiosity"] >= 1
    assert lookup_telemetry["by_reason"]["orientation"] >= 1
    assert lookup_telemetry["by_working_context"][lookup_facts["focus"]["working_context_ref"]] >= 2
    opened_map = json.loads(
        run_cli(context, "map-open", "--query", "Facility Program relationship", "--scope", "all", "--format", "json").stdout
    )
    assert opened_map["contract_version"] == "0.4"
    assert opened_map["map_is_proof"] is False
    assert opened_map["map_session_ref"].startswith("WCTX-")
    assert opened_map["map_session_ref"].endswith("#map-session")
    assert opened_map["zone"]["id"].startswith("MZONE-")
    assert opened_map["anchor_facts"]
    session_ref = opened_map["map_session_ref"]
    map_wctx = load_record(context, "working_context", session_ref.split("#", 1)[0])
    assert map_wctx["map_sessions"]["default"]["session_ref"] == session_ref
    assert "map_sessions" in map_wctx["owner_signature"]["signed_fields"]
    viewed_map = json.loads(run_cli(context, "map-view", "--session", session_ref, "--format", "json").stdout)
    assert viewed_map["map_session_ref"] == session_ref
    moved_map = json.loads(
        run_cli(context, "map-move", "--session", session_ref, "--target", opened_map["zone"]["map_ref"], "--format", "json").stdout
    )
    assert moved_map["visited_map_refs"]
    drilldown = json.loads(
        run_cli(context, "map-drilldown", "--session", session_ref, "--record", opened_map["anchor_facts"][0]["ref"], "--format", "json").stdout
    )
    assert drilldown["drilldown_is_proof"] is False
    assert drilldown["proof_routes"]
    checkpoint = json.loads(
        run_cli(context, "map-checkpoint", "--session", session_ref, "--note", "pytest checkpoint", "--format", "json").stdout
    )
    assert checkpoint["checkpoint"]["checkpoint_is_proof"] is False
    checkpoint_wctx = load_record(context, "working_context", session_ref.split("#", 1)[0])
    assert checkpoint_wctx["map_sessions"]["default"]["checkpoints"][-1]["note"] == "pytest checkpoint"
    run_cli(context, "set-current-workspace", "--clear")
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
    assert any(command.startswith("record-link --probe-index 1") for command in route["recommended_commands"])
    assert route["context_delta"]["payload_char_count"] > 0
    link_result = run_cli(
        context,
        "record-link",
        "--probe-index",
        "1",
        "--probe-scope",
        "all",
        "--scope",
        "attention.demo",
        "--relation",
        "related",
        "--quote",
        "Inspection found the Facility and Program claims should be linked.",
        "--note",
        "persisted reviewed curiosity probe link",
    )
    link_claim_id = recorded_id(link_result, "link claim")
    link_claim = load_record(context, "claim", link_claim_id)
    assert link_claim["support_refs"] == route["record_refs"]
    linked_after = json.loads(
        run_cli(context, "linked-records", "--record", route["record_refs"][0], "--depth", "2", "--format", "json").stdout
    )
    linked_ids = {record["id"] for record in linked_after["records"]}
    assert link_claim_id in linked_ids
    linked_edges = {(edge["from"], edge["to"]) for edge in linked_after["edges"]}
    assert (link_claim_id, route["record_refs"][0]) in linked_edges
    assert (link_claim_id, route["record_refs"][1]) in linked_edges
    rebuilt_probes = json.loads(run_cli(context, "curiosity-probes", "--budget", "10", "--scope", "all", "--format", "json").stdout)
    rebuilt_pairs = {tuple(sorted(probe["record_refs"])) for probe in rebuilt_probes["probes"]}
    assert tuple(sorted(route["record_refs"])) not in rebuilt_pairs
    linked_map = json.loads(run_cli(context, "curiosity-map", "--volume", "wide", "--scope", "all", "--format", "json").stdout)
    record_link_edges = [
        edge
        for edge in linked_map["map_graph"]["edges"]
        if set(edge.get("source_records", [])) == {link_claim_id} and set(edge["fields"]) == {"record-link.support_refs"}
    ]
    assert record_link_edges
    assert {record_link_edges[0]["from"], record_link_edges[0]["to"]} == set(route["record_refs"])
    assert record_link_edges[0]["relation"] == "related"
    assert any(set(route["record_refs"]).issubset(set(cluster["node_refs"])) for cluster in linked_map["map_graph"]["clusters"] if cluster["kind"] == "topology")
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
    workspace_id = recorded_id(
        run_cli(
            context,
            "record-workspace",
            "--workspace-key",
            "wctx-demo",
            "--title",
            "WCTX demo workspace",
            "--note",
            "workspace for signed WCTX test",
        ),
        "workspace",
    )
    run_cli(context, "set-current-workspace", "--workspace", workspace_id)
    task = run_cli(
        context,
        "start-task",
        "--type",
        "investigation",
        "--scope",
        "wctx.demo",
        "--title",
        "Investigate working context",
        "--note",
        "wctx task",
    )
    task_id = re.search(r"(TASK-\d{8}-[0-9a-f]{8})", task.stdout).group(1)

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
        "--task",
        task_id,
        "--note",
        "create working context",
    )
    wctx_id = recorded_id(created, "working_context")
    wctx = load_record(context, "working_context", wctx_id)
    assert wctx["pinned_refs"] == [claim_id]
    assert wctx["topic_seed_refs"] == [claim_id]
    assert wctx["assumptions"][0]["mode"] == "exploration-only"
    assert wctx["contract_version"] == "0.4"
    assert wctx["record_version"] == 1
    assert wctx["ownership_mode"] == "owner-only"
    assert wctx["owner_signature"]["algorithm"] == "hmac-sha256"
    owner = load_record(context, "agent_identity", wctx["agent_identity_ref"])
    assert owner["key_fingerprint"] == wctx["agent_key_fingerprint"]
    assert "secret" not in owner
    assert wctx_id in load_record(context, "task", task_id)["working_context_refs"]

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
        "--task",
        task_id,
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
    assert fork["contract_version"] == "0.4"
    assert fork["record_version"] == 1
    assert fork["agent_identity_ref"] == wctx["agent_identity_ref"]
    assert fork["owner_signature"]["signed_payload_hash"] != wctx["owner_signature"]["signed_payload_hash"]
    task_after_fork = load_record(context, "task", task_id)
    assert wctx_id in task_after_fork["working_context_refs"]
    assert fork_id in task_after_fork["working_context_refs"]

    show = run_cli(context, "working-context", "show", "--context", fork_id).stdout
    assert fork_id in show
    assert claim_id in show

    run_cli(context, "working-context", "close", "--context", fork_id, "--note", "done")
    closed = load_record(context, "working_context", fork_id)
    assert closed["status"] == "closed"
    assert closed["owner_signature"]["signed_payload_hash"] != fork["owner_signature"]["signed_payload_hash"]
    assert run_cli(context, "review-context").returncode == 0


def test_curator_pool_builds_explicit_workspace_snapshot_without_current_focus(tmp_path: Path) -> None:
    context = bootstrap_context(tmp_path)
    workspace_id = recorded_id(
        run_cli(
            context,
            "record-workspace",
            "--workspace-key",
            "curator-source-workspace",
            "--title",
            "Curator Source Workspace",
            "--root-ref",
            "/tmp/curator-source",
            "--note",
            "workspace to curate",
        ),
        "workspace",
    )
    run_cli(context, "set-current-workspace", "--workspace", workspace_id)
    project_id = recorded_id(
        run_cli(
            context,
            "record-project",
            "--project-key",
            "curator-project",
            "--title",
            "Curator Project",
            "--root-ref",
            "/tmp/curator-project",
            "--note",
            "project to curate",
        ),
        "project",
    )
    run_cli(context, "set-current-project", "--project", project_id)
    source_id = recorded_id(
        run_cli(
            context,
            "record-source",
            "--scope",
            "curator.demo",
            "--source-kind",
            "theory",
            "--critique-status",
            "accepted",
            "--origin-kind",
            "user",
            "--origin-ref",
            "curator test",
            "--quote",
            "Products reach Facility storage before Program marketplace listing configuration.",
            "--note",
            "curator source",
        ),
        "source",
    )
    first_claim = recorded_id(
        run_cli(
            context,
            "record-claim",
            "--scope",
            "curator.demo",
            "--plane",
            "theory",
            "--status",
            "supported",
            "--statement",
            "Products reach Facility storage before Program marketplace listing configuration.",
            "--source",
            source_id,
            "--note",
            "curator claim",
        ),
        "claim",
    )
    second_claim = recorded_id(
        run_cli(
            context,
            "record-claim",
            "--scope",
            "curator.demo",
            "--plane",
            "theory",
            "--status",
            "supported",
            "--statement",
            "Products reach Facility storage before Program marketplace listing configuration.",
            "--source",
            source_id,
            "--note",
            "duplicate curator claim",
        ),
        "claim",
    )

    other_workspace_id = recorded_id(
        run_cli(
            context,
            "record-workspace",
            "--workspace-key",
            "current-but-not-curated",
            "--title",
            "Current But Not Curated",
            "--root-ref",
            "/tmp/current-but-not-curated",
            "--note",
            "current focus should not control curator pool",
        ),
        "workspace",
    )
    run_cli(context, "set-current-workspace", "--workspace", other_workspace_id)

    pool_id = recorded_id(
        run_cli(
            context,
            "curator-pool",
            "build",
            "--workspace",
            workspace_id,
            "--project",
            project_id,
            "--kind",
            "duplicates",
            "--query",
            "Facility Program products marketplace",
            "--limit",
            "5",
            "--note",
            "bounded curator pool",
        ),
        "curator_pool",
    )
    pool = load_record(context, "curator_pool", pool_id)
    assert pool["workspace_ref"] == workspace_id
    assert pool["project_ref"] == project_id
    assert pool["task_ref"] == ""
    assert pool["workspace_refs"] == [workspace_id]
    assert pool["project_refs"] == [project_id]
    assert pool["task_refs"] == []
    assert pool["pool_is_proof"] is False
    assert pool["selection"]["pool_is_proof"] is False
    assert "run-runtime-commands" in pool["forbidden_actions"]
    assert {first_claim, second_claim}.issubset(set(pool["candidate_record_refs"]))
    assert any(set(group["record_refs"]) == {first_claim, second_claim} for group in pool["categories"]["duplicate_candidates"])
    assert all(item["sha256"] for item in pool["record_fingerprints"])
    assert all(item["quote_is_proof"] is False for item in pool["source_quotes"])

    shown = json.loads(run_cli(context, "curator-pool", "show", "--pool", pool_id, "--format", "json").stdout)
    assert shown["id"] == pool_id
    shown_text = run_cli(context, "curator-pool", "show", "--pool", pool_id).stdout
    assert "# Curator Pool" in shown_text
    assert "## Forbidden Actions" in shown_text
    assert "run-runtime-commands" in shown_text


def test_workspace_admission_requires_decision_for_unknown_repo(tmp_path: Path) -> None:
    context = bootstrap_context(tmp_path)
    known_repo = tmp_path / "known-repo"
    unknown_repo = tmp_path / "unknown-repo"
    known_repo.mkdir()
    unknown_repo.mkdir()

    workspace_id = recorded_id(
        run_cli(
            context,
            "record-workspace",
            "--workspace-key",
            "known-workspace",
            "--title",
            "Known workspace",
            "--root-ref",
            str(known_repo),
            "--note",
            "workspace fixture",
        ),
        "workspace",
    )
    run_cli(context, "set-current-workspace", "--workspace", workspace_id)
    project_id = recorded_id(
        run_cli(
            context,
            "record-project",
            "--project-key",
            "known-project",
            "--title",
            "Known project",
            "--root-ref",
            str(known_repo),
            "--note",
            "project fixture",
        ),
        "project",
    )
    run_cli(context, "set-current-project", "--project", project_id)

    known = json.loads(
        run_cli(context, "workspace-admission", "check", "--repo", str(known_repo), "--format", "json").stdout
    )
    assert known["known"] is True
    assert known["in_current_workspace"] is True
    assert known["in_current_project"] is True
    assert known["requires_user_decision"] is False

    unknown = json.loads(
        run_cli(context, "workspace-admission", "check", "--repo", str(unknown_repo), "--format", "json").stdout
    )
    assert unknown["known"] is False
    assert unknown["requires_user_decision"] is True
    assert "create-new-workspace" in unknown["options"]
    assert "inspect-readonly-without-persisting" in unknown["options"]


def test_working_context_check_drift_uses_task_text_against_active_focus(tmp_path: Path) -> None:
    context = bootstrap_context(tmp_path)
    workspace_id = recorded_id(
        run_cli(
            context,
            "record-workspace",
            "--workspace-key",
            "wctx-drift",
            "--title",
            "WCTX drift workspace",
            "--note",
            "workspace for signed WCTX drift test",
        ),
        "workspace",
    )
    run_cli(context, "set-current-workspace", "--workspace", workspace_id)

    created = run_cli(
        context,
        "working-context",
        "create",
        "--scope",
        "backend.cocoindex",
        "--title",
        "CocoIndex backend routing",
        "--kind",
        "edit",
        "--topic-term",
        "cocoindex",
        "--topic-term",
        "backend",
        "--note",
        "track scoped backend index routing",
    )
    wctx_id = recorded_id(created, "working_context")

    related = json.loads(
        run_cli(
            context,
            "working-context",
            "check-drift",
            "--task",
            "Continue CocoIndex backend storage routing",
            "--format",
            "json",
        ).stdout
    )
    assert related["drift_detected"] is False
    assert related["best_current_context"]["id"] == wctx_id
    assert related["recommendation"] == "keep-current-working-context"

    unrelated = json.loads(
        run_cli(
            context,
            "working-context",
            "check-drift",
            "--task",
            "Investigate medical differential diagnosis prompts",
            "--format",
            "json",
        ).stdout
    )
    assert unrelated["drift_detected"] is True
    assert unrelated["recommendation"] == "create-working-context"


def test_lookup_ignores_active_working_context_linked_to_paused_task(tmp_path: Path) -> None:
    context = bootstrap_context(tmp_path)
    workspace_id = recorded_id(
        run_cli(
            context,
            "record-workspace",
            "--workspace-key",
            "stale-wctx-workspace",
            "--title",
            "Stale WCTX Workspace",
            "--note",
            "workspace for stale WCTX lookup",
        ),
        "workspace",
    )
    run_cli(context, "set-current-workspace", "--workspace", workspace_id)
    task_id = recorded_id(
        run_cli(
            context,
            "start-task",
            "--type",
            "investigation",
            "--scope",
            "stale.wctx",
            "--title",
            "Investigate stale WCTX",
            "--note",
            "task that will be paused",
        ),
        "task",
    )
    stale_wctx_id = recorded_id(
        run_cli(
            context,
            "working-context",
            "create",
            "--scope",
            "stale.wctx",
            "--title",
            "Paused task context",
            "--kind",
            "investigation",
            "--task",
            task_id,
            "--note",
            "must not be reused after task pauses",
        ),
        "working_context",
    )
    run_cli(context, "pause-task", "--note", "simulate stale focus")

    settings_path = context / "settings.json"
    settings = json.loads(settings_path.read_text(encoding="utf-8"))
    settings["current_task_ref"] = task_id
    settings_path.write_text(json.dumps(settings, indent=2, ensure_ascii=False), encoding="utf-8")

    shown = json.loads(run_cli(context, "working-context", "show", "--format", "json").stdout)
    assert stale_wctx_id not in [item["id"] for item in shown["contexts"]]

    lookup = json.loads(
        run_cli(
            context,
            "lookup",
            "--query",
            "stale working context route",
            "--reason",
            "orientation",
            "--kind",
            "facts",
            "--format",
            "json",
        ).stdout
    )
    assert lookup["focus"]["auto_created_working_context"] is True
    assert lookup["focus"]["working_context_ref"] != stale_wctx_id
    created = load_record(context, "working_context", lookup["focus"]["working_context_ref"])
    assert created["task_refs"] == []


def test_lookup_forks_focus_when_active_wctx_is_owned_by_another_agent(tmp_path: Path) -> None:
    context = bootstrap_context(tmp_path)
    workspace_id = recorded_id(
        run_cli(
            context,
            "record-workspace",
            "--workspace-key",
            "foreign-wctx-workspace",
            "--title",
            "Foreign WCTX Workspace",
            "--note",
            "workspace for foreign WCTX lookup",
        ),
        "workspace",
    )
    run_cli(context, "set-current-workspace", "--workspace", workspace_id)
    task_id = recorded_id(
        run_cli(
            context,
            "start-task",
            "--type",
            "investigation",
            "--scope",
            "foreign.wctx",
            "--title",
            "Investigate foreign WCTX",
            "--note",
            "task with a foreign active WCTX",
        ),
        "task",
    )
    foreign_wctx_id = recorded_id(
        run_cli(
            context,
            "working-context",
            "create",
            "--scope",
            "foreign.wctx",
            "--title",
            "Foreign-owned active context",
            "--kind",
            "investigation",
            "--task",
            task_id,
            "--note",
            "initial owner context",
        ),
        "working_context",
    )

    secret_path = context / "runtime" / "agent_identity" / "local_agent_key.json"
    secret_path.write_text(
        json.dumps(
            {
                "version": 1,
                "agent_identity_ref": "AGENT-20260423-feedfeed",
                "agent_name": "pytest-other-agent",
                "key_algorithm": "hmac-sha256",
                "key_scope": "local-agent",
                "secret": "other-agent-secret",
                "created_at": "2026-04-23T00:00:00+03:00",
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    close_attempt = run_cli(
        context,
        "working-context",
        "close",
        "--context",
        foreign_wctx_id,
        "--note",
        "should fail for non-owner",
        check=False,
    )
    assert close_attempt.returncode == 1
    assert "owned by another local agent" in close_attempt.stdout

    lookup = json.loads(
        run_cli(
            context,
            "lookup",
            "--query",
            "foreign working context route",
            "--reason",
            "orientation",
            "--kind",
            "facts",
            "--format",
            "json",
        ).stdout
    )
    assert lookup["focus"]["auto_created_working_context"] is True
    assert lookup["focus"]["working_context_ref"] != foreign_wctx_id
    created = load_record(context, "working_context", lookup["focus"]["working_context_ref"])
    assert created["agent_identity_ref"] == "AGENT-20260423-feedfeed"
    assert created["owner_signature"]["algorithm"] == "hmac-sha256"


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


def test_code_search_proxies_cocoindex_backend_through_tep_entrypoint(tmp_path: Path, monkeypatch) -> None:
    context = bootstrap_context(tmp_path)
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "src").mkdir()
    (repo / "src" / "app.py").write_text(
        "def choose_backend():\n"
        "    return 'cocoindex'\n",
        encoding="utf-8",
    )
    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True, text=True)
    subprocess.run(["git", "add", "src/app.py"], cwd=repo, check=True, capture_output=True, text=True)
    workspace_id = recorded_id(
        run_cli(
            context,
            "record-workspace",
            "--workspace-key",
            "code-search-workspace",
            "--title",
            "Code search workspace",
            "--root-ref",
            str(repo),
            "--note",
            "backend workspace fixture",
        ),
        "workspace",
    )
    run_cli(context, "set-current-workspace", "--workspace", workspace_id)
    project_id = recorded_id(
        run_cli(
            context,
            "record-project",
            "--project-key",
            "code-search-project",
            "--title",
            "Code search project",
            "--root-ref",
            str(repo),
            "--note",
            "backend project fixture",
        ),
        "project",
    )
    run_cli(context, "set-current-project", "--project", project_id)
    run_cli(context, "init-code-index", "--root", str(repo))
    source_id = recorded_id(
        run_cli(
            context,
            "record-source",
            "--scope",
            "code-search.backend",
            "--source-kind",
            "code",
            "--critique-status",
            "accepted",
            "--origin-kind",
            "fixture",
            "--origin-ref",
            "src/app.py",
            "--quote",
            "def choose_backend():",
            "--note",
            "backend search link target",
        ),
        "source",
    )
    claim_id = recorded_id(
        run_cli(
            context,
            "record-claim",
            "--scope",
            "code-search.backend",
            "--plane",
            "code",
            "--status",
            "supported",
            "--statement",
            "src/app.py defines choose_backend.",
            "--source",
            source_id,
            "--note",
            "backend search link candidate",
        ),
        "claim",
    )
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    ccc = fake_bin / "ccc"
    ccc.write_text(
        "#!/usr/bin/env python3\n"
        "import os\n"
        "import sys\n"
        "assert sys.argv[1] == 'search'\n"
        "assert os.environ.get('COCOINDEX_CODE_DB_PATH_MAPPING') == os.environ.get('TEP_TEST_EXPECTED_MAPPING')\n"
        "print('--- Result 1 (score: 0.812) ---')\n"
        "print('File: src/app.py:10-12 [python]')\n"
        "print('def choose_backend():')\n"
        "print('    return \\'cocoindex\\'')\n",
        encoding="utf-8",
    )
    ccc.chmod(0o755)
    monkeypatch.setenv("PATH", f"{fake_bin}{os.pathsep}{os.environ.get('PATH', '')}")
    monkeypatch.setenv(
        "TEP_TEST_EXPECTED_MAPPING",
        f"{repo}={context / 'backends' / 'cocoindex' / 'projects' / project_id / '.cocoindex_code'}",
    )

    run_cli(
        context,
        "configure-runtime",
        "--backend",
        "code_intelligence.cocoindex.enabled=true",
        "--backend",
        "code_intelligence.cocoindex.mode=cli",
        "--backend",
        "code_intelligence.cocoindex.max_results=4",
    )
    payload = json.loads(
        run_cli(
            context,
            "code-search",
            "--root",
            str(repo),
            "--query",
            "backend choice",
            "--path",
            "src/*.py",
            "--link-candidate",
            claim_id,
            "--fields",
            "target",
            "--format",
            "json",
        ).stdout
    )

    assert payload["results"][0]["target"]["path"] == "src/app.py"
    backend = payload["backend_results"]
    assert backend["backend"] == "cocoindex"
    assert backend["backend_output_is_proof"] is False
    assert backend["enabled"] is True
    assert backend["available"] is True
    assert backend["scope"] == "project"
    assert backend["storage"]["project_ref"] == project_id
    assert backend["storage"]["workspace_ref"] == workspace_id
    assert backend["storage"]["scoped_db_dir"].endswith(f"/backends/cocoindex/projects/{project_id}/.cocoindex_code")
    assert backend["results"][0]["target"] == {"path": "src/app.py", "line_start": 10, "line_end": 12}
    assert backend["results"][0]["snippet"] == "def choose_backend():\n    return 'cocoindex'"
    assert backend["results"][0]["cix_candidates"][0]["target"]["path"] == "src/app.py"
    assert backend["results"][0]["link_suggestions"][0]["ref"] == claim_id
    assert backend["results"][0]["link_suggestions"][0]["command"].startswith("link-code --entry CIX-")
    assert "index_suggestion" not in backend["results"][0]

    feedback = json.loads(
        run_cli(
            context,
            "code-feedback",
            "--root",
            str(repo),
            "--query",
            "backend choice",
            "--path",
            "src/*.py",
            "--link-candidate",
            claim_id,
            "--format",
            "json",
        ).stdout
    )
    feedback_entry_id = feedback["items"][0]["cix_candidates"][0]["id"]
    assert feedback["feedback_is_proof"] is False
    assert feedback["items"][0]["link_suggestions"][0]["ref"] == claim_id

    run_cli(
        context,
        "code-feedback",
        "--apply",
        "--entry",
        feedback_entry_id,
        "--link-candidate",
        claim_id,
        "--note",
        "reviewed backend hit links this claim to the implementation area",
    )
    linked = json.loads(
        run_cli(
            context,
            "code-search",
            "--root",
            str(repo),
            "--ref",
            claim_id,
            "--fields",
            "target,links",
            "--format",
            "json",
        ).stdout
    )
    assert linked["results"][0]["id"] == feedback_entry_id

    telemetry = json.loads(run_cli(context, "telemetry-report", "--format", "json").stdout)
    assert telemetry["by_tool"]["code-search"] >= 2
    assert telemetry["by_access_kind"]["backend_code_search"] >= 1
    assert telemetry["by_access_kind"]["backend_code_feedback"] >= 1


def test_code_index_commands_refresh_project_and_workspace_cocoindex_storage(tmp_path: Path, monkeypatch) -> None:
    context = bootstrap_context(tmp_path)
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "src").mkdir()
    (repo / "src" / "app.py").write_text("def indexed_by_tep():\n    return True\n", encoding="utf-8")
    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True, text=True)
    subprocess.run(["git", "add", "src/app.py"], cwd=repo, check=True, capture_output=True, text=True)
    workspace_id = recorded_id(
        run_cli(
            context,
            "record-workspace",
            "--workspace-key",
            "backend-index-workspace",
            "--title",
            "Backend index workspace",
            "--root-ref",
            str(repo),
            "--note",
            "backend index workspace fixture",
        ),
        "workspace",
    )
    run_cli(context, "set-current-workspace", "--workspace", workspace_id)
    project_id = recorded_id(
        run_cli(
            context,
            "record-project",
            "--project-key",
            "backend-index-project",
            "--title",
            "Backend index project",
            "--root-ref",
            str(repo),
            "--note",
            "backend index project fixture",
        ),
        "project",
    )
    run_cli(context, "set-current-project", "--project", project_id)

    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    log_path = tmp_path / "cocoindex.log"
    ccc = fake_bin / "ccc"
    ccc.write_text("#!/usr/bin/env python3\nprint('fake ccc command marker')\n", encoding="utf-8")
    ccc.chmod(0o755)
    direct_index = fake_bin / "direct-index"
    direct_index.write_text(
        "#!/usr/bin/env python3\n"
        "import json\n"
        "import os\n"
        "import pathlib\n"
        "import sys\n"
        "payload = json.loads(sys.stdin.read())\n"
        "mapping = os.environ['COCOINDEX_CODE_DB_PATH_MAPPING']\n"
        "repo, storage = mapping.split('=', 1)\n"
        "assert repo == os.environ['TEP_COCOINDEX_SHADOW_ROOT']\n"
        "assert payload['project_root'] == repo\n"
        "assert payload['storage_dir'] == storage\n"
        "assert repo != os.environ['TEP_COCOINDEX_REPO_ROOT']\n"
        "assert pathlib.Path(repo, '.cocoindex_code', 'settings.yml').is_file()\n"
        "assert pathlib.Path(os.environ['TEP_COCOINDEX_REPO_ROOT'], '.cocoindex_code').exists() is False\n"
        "storage_path = pathlib.Path(storage)\n"
        "storage_path.mkdir(parents=True, exist_ok=True)\n"
        "(storage_path / 'settings.yml').write_text('fixture: true\\n', encoding='utf-8')\n"
        "(storage_path / 'target_sqlite.db').write_text('fixture db\\n', encoding='utf-8')\n"
        "with open(os.environ['TEP_TEST_LOG'], 'a', encoding='utf-8') as handle:\n"
        "    handle.write(os.environ['TEP_COCOINDEX_SCOPE'] + '=' + mapping + '\\n')\n",
        encoding="utf-8",
    )
    direct_index.chmod(0o755)
    monkeypatch.setenv("PATH", f"{fake_bin}{os.pathsep}{os.environ.get('PATH', '')}")
    monkeypatch.setenv("TEP_TEST_LOG", str(log_path))
    monkeypatch.setenv("TEP_COCOINDEX_DIRECT_INDEX_HELPER", str(direct_index))
    run_cli(
        context,
        "configure-runtime",
        "--backend",
        "code_intelligence.cocoindex.enabled=true",
        "--backend",
        "code_intelligence.cocoindex.mode=cli",
    )

    result = run_cli(context, "init-code-index", "--root", str(repo))

    assert "Indexed 1 git-tracked code file(s)" in result.stdout
    assert "Backend index: cocoindex scope=project indexed" in result.stdout
    assert "Backend index: cocoindex scope=workspace indexed" in result.stdout
    project_storage = context / "backends" / "cocoindex" / "projects" / project_id / ".cocoindex_code"
    workspace_storage = context / "backends" / "cocoindex" / "workspaces" / workspace_id / ".cocoindex_code"
    assert (project_storage / "settings.yml").is_file()
    assert (project_storage / "target_sqlite.db").is_file()
    assert (workspace_storage / "settings.yml").is_file()
    assert (workspace_storage / "target_sqlite.db").is_file()
    log_lines = log_path.read_text(encoding="utf-8").splitlines()
    assert any(line.startswith("project=") and line.endswith(f"={project_storage}") for line in log_lines)
    assert any(line.startswith("workspace=") and line.endswith(f"={workspace_storage}") for line in log_lines)
    assert not (repo / ".cocoindex_code").exists()

    project_status = json.loads(
        run_cli(
            context,
            "backend-check",
            "--backend",
            "code_intelligence.cocoindex",
            "--root",
            str(repo),
            "--scope",
            "project",
            "--format",
            "json",
        ).stdout
    )["matches"][0]
    workspace_status = json.loads(
        run_cli(
            context,
            "backend-check",
            "--backend",
            "code_intelligence.cocoindex",
            "--root",
            str(repo),
            "--scope",
            "workspace",
            "--format",
            "json",
        ).stdout
    )["matches"][0]
    assert project_status["storage"]["runtime_search_ready"] is True
    assert workspace_status["storage"]["runtime_search_ready"] is True


def test_code_search_resolves_paths_from_project_root_not_agent_cwd(tmp_path: Path, monkeypatch) -> None:
    context = bootstrap_context(tmp_path)
    repo_a = tmp_path / "repo-a"
    repo_b = tmp_path / "repo-b"
    agent_cwd = tmp_path / "agent-cwd"
    for repo, label in ((repo_a, "alpha"), (repo_b, "beta")):
        (repo / "src").mkdir(parents=True)
        (repo / "src" / "app.py").write_text(f"def app_label():\n    return '{label}'\n", encoding="utf-8")
        subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True, text=True)
        subprocess.run(["git", "add", "src/app.py"], cwd=repo, check=True, capture_output=True, text=True)
    (repo_b / "src" / "legacy.py").write_text("def legacy_label():\n    return 'beta-legacy'\n", encoding="utf-8")
    agent_cwd.mkdir()

    workspace_a = recorded_id(
        run_cli(
            context,
            "record-workspace",
            "--workspace-key",
            "workspace-a",
            "--title",
            "Workspace A",
            "--root-ref",
            str(repo_a),
            "--note",
            "workspace a",
        ),
        "workspace",
    )
    run_cli(context, "set-current-workspace", "--workspace", workspace_a)
    project_a = recorded_id(
        run_cli(
            context,
            "record-project",
            "--project-key",
            "project-a",
            "--title",
            "Project A",
            "--root-ref",
            str(repo_a),
            "--note",
            "project a",
        ),
        "project",
    )
    run_cli(context, "set-current-project", "--project", project_a)
    run_cli(context, "init-code-index", "--root", str(repo_a))

    workspace_b = recorded_id(
        run_cli(
            context,
            "record-workspace",
            "--workspace-key",
            "workspace-b",
            "--title",
            "Workspace B",
            "--root-ref",
            str(repo_b),
            "--note",
            "workspace b",
        ),
        "workspace",
    )
    run_cli(context, "set-current-workspace", "--workspace", workspace_b)
    project_b = recorded_id(
        run_cli(
            context,
            "record-project",
            "--project-key",
            "project-b",
            "--title",
            "Project B",
            "--root-ref",
            str(repo_b),
            "--note",
            "project b",
        ),
        "project",
    )
    run_cli(context, "set-current-project", "--project", project_b)
    run_cli(context, "init-code-index", "--root", str(repo_b))

    run_cli(
        context,
        "init-anchor",
        "--directory",
        str(agent_cwd),
        "--workspace",
        workspace_b,
        "--project",
        project_b,
        "--force",
        "--note",
        "agent cwd anchored to project b",
    )
    implicit = subprocess.run(
        [
            sys.executable,
            str(CLI),
            "--context",
            str(context),
            "code-search",
            "--path",
            "src/app.py",
            "--fields",
            "target,freshness",
            "--format",
            "json",
        ],
        cwd=agent_cwd,
        capture_output=True,
        text=True,
        check=False,
    )
    assert implicit.returncode == 0, implicit.stdout + implicit.stderr
    implicit_payload = json.loads(implicit.stdout)
    assert len(implicit_payload["results"]) == 1
    assert implicit_payload["repo_scope"] == {
        "repo_root": str(repo_b),
        "repo_root_source": "project-root",
        "workspace_ref": workspace_b,
        "project_ref": project_b,
        "paths_are_project_relative": True,
    }
    implicit_entry = json.loads(
        (context / "code_index" / "entries" / f"{implicit_payload['results'][0]['id']}.json").read_text(encoding="utf-8")
    )
    assert implicit_entry["project_ref"] == project_b
    assert implicit_payload["results"][0]["freshness"]["stale"] is False

    legacy_unscoped_id = "CIX-20260420-deadbeef"
    legacy_unscoped_path = context / "code_index" / "entries" / f"{legacy_unscoped_id}.json"
    legacy_unscoped_path.write_text(
        json.dumps(
            {
                "id": legacy_unscoped_id,
                "record_type": "code_index_entry",
                "status": "missing",
                "target": {"kind": "file", "path": "src/app.py"},
                "target_state": "missing",
                "language": "python",
                "code_kind": "source",
                "summary": "legacy unscoped duplicate",
                "metadata": {},
                "detected_features": [],
                "manual_features": [],
                "manual_links": {},
                "annotations": [],
                "links": [],
                "child_entry_refs": [],
                "related_entry_refs": [],
                "supersedes_refs": [],
                "created_at": "2026-04-20T10:00:00+03:00",
                "updated_at": "2026-04-20T10:00:00+03:00",
                "note": "legacy unscoped CIX should not leak into project-scoped search",
            }
        ),
        encoding="utf-8",
    )
    active_unscoped_id = "CIX-20260420-feedface"
    active_unscoped_path = context / "code_index" / "entries" / f"{active_unscoped_id}.json"
    active_unscoped_path.write_text(
        json.dumps(
            {
                "id": active_unscoped_id,
                "record_type": "code_index_entry",
                "status": "active",
                "target": {"kind": "file", "path": "src/legacy.py"},
                "target_state": "present",
                "language": "python",
                "code_kind": "source",
                "summary": "legacy active unscoped entry",
                "metadata": {},
                "detected_features": [],
                "manual_features": [],
                "manual_links": {},
                "annotations": [],
                "links": [],
                "child_entry_refs": [],
                "related_entry_refs": [],
                "supersedes_refs": [],
                "created_at": "2026-04-20T10:00:00+03:00",
                "updated_at": "2026-04-20T10:00:00+03:00",
                "note": "explicit --status active should not include default missing",
            }
        ),
        encoding="utf-8",
    )
    scoped_with_missing = json.loads(
        run_cli(
            context,
            "code-search",
            "--root",
            str(repo_b),
            "--path",
            "src/app.py",
            "--include-missing",
            "--format",
            "json",
        ).stdout
    )
    assert [item["id"] for item in scoped_with_missing["results"]] == [implicit_payload["results"][0]["id"]]

    archive_plan = json.loads(run_cli(context, "code-entry", "archive-unscoped", "--format", "json").stdout)
    assert archive_plan["archive_unscoped_is_dry_run"] is True
    assert archive_plan["selected_statuses"] == ["missing"]
    assert archive_plan["count"] == 1
    active_archive_plan = json.loads(
        run_cli(context, "code-entry", "archive-unscoped", "--status", "active", "--format", "json").stdout
    )
    assert active_archive_plan["selected_statuses"] == ["active"]
    assert active_archive_plan["count"] == 1
    assert active_archive_plan["items"][0]["id"] == active_unscoped_id
    attach_plan = json.loads(
        run_cli(context, "code-entry", "attach-unscoped", "--root", str(repo_b), "--format", "json").stdout
    )
    assert attach_plan["attach_unscoped_is_dry_run"] is True
    assert attach_plan["selected_statuses"] == ["active"]
    assert attach_plan["count"] == 1
    assert attach_plan["project_ref"] == project_b
    run_cli(context, "code-entry", "attach-unscoped", "--root", str(repo_b), "--apply")
    attached_entry = json.loads(active_unscoped_path.read_text(encoding="utf-8"))
    assert attached_entry["workspace_ref"] == workspace_b
    assert attached_entry["project_ref"] == project_b
    run_cli(context, "code-entry", "archive-unscoped", "--apply")
    assert json.loads(legacy_unscoped_path.read_text(encoding="utf-8"))["status"] == "archived"
    assert json.loads(active_unscoped_path.read_text(encoding="utf-8"))["status"] == "active"

    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    ccc = fake_bin / "ccc"
    ccc.write_text(
        "#!/usr/bin/env python3\n"
        "import os\n"
        "import sys\n"
        "assert sys.argv[1] == 'search'\n"
        "assert os.environ.get('COCOINDEX_CODE_DB_PATH_MAPPING') == os.environ.get('TEP_TEST_EXPECTED_MAPPING')\n"
        "print('--- Result 1 (score: 0.900) ---')\n"
        "print('File: src/app.py:1-2 [python]')\n"
        "print('def app_label():')\n",
        encoding="utf-8",
    )
    ccc.chmod(0o755)
    monkeypatch.setenv("PATH", f"{fake_bin}{os.pathsep}{os.environ.get('PATH', '')}")
    monkeypatch.setenv(
        "TEP_TEST_EXPECTED_MAPPING",
        f"{repo_b}={context / 'backends' / 'cocoindex' / 'projects' / project_b / '.cocoindex_code'}",
    )
    run_cli(
        context,
        "configure-runtime",
        "--backend",
        "code_intelligence.cocoindex.enabled=true",
        "--backend",
        "code_intelligence.cocoindex.mode=cli",
    )
    run_cli(context, "set-current-workspace", "--workspace", workspace_a)
    run_cli(context, "set-current-project", "--project", project_a)

    explicit = json.loads(
        run_cli(context, "code-search", "--root", str(repo_b), "--query", "app label", "--format", "json").stdout
    )
    assert explicit["repo_scope"] == {
        "repo_root": str(repo_b),
        "repo_root_source": "explicit",
        "workspace_ref": workspace_b,
        "project_ref": project_b,
        "paths_are_project_relative": True,
    }
    backend = explicit["backend_results"]
    assert backend["storage"]["project_ref"] == project_b
    assert backend["storage"]["workspace_ref"] == workspace_b
    assert backend["storage"]["db_path_mapping"] == os.environ["TEP_TEST_EXPECTED_MAPPING"]
    assert backend["results"][0]["cix_candidates"][0]["id"] == implicit_payload["results"][0]["id"]


def test_cocoindex_status_distinguishes_storage_from_cli_search_readiness(tmp_path: Path, monkeypatch) -> None:
    context = bootstrap_context(tmp_path)
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True, text=True)
    workspace_id = recorded_id(
        run_cli(
            context,
            "record-workspace",
            "--workspace-key",
            "coco-readiness-workspace",
            "--title",
            "Coco readiness workspace",
            "--root-ref",
            str(repo),
            "--note",
            "coco readiness workspace",
        ),
        "workspace",
    )
    run_cli(context, "set-current-workspace", "--workspace", workspace_id)
    project_id = recorded_id(
        run_cli(
            context,
            "record-project",
            "--project-key",
            "coco-readiness-project",
            "--title",
            "Coco readiness project",
            "--root-ref",
            str(repo),
            "--note",
            "coco readiness project",
        ),
        "project",
    )
    run_cli(context, "set-current-project", "--project", project_id)
    storage_dir = context / "backends" / "cocoindex" / "projects" / project_id / ".cocoindex_code"
    storage_dir.mkdir(parents=True)
    (storage_dir / "settings.yml").write_text("include_patterns: ['**/*.py']\nexclude_patterns: []\n", encoding="utf-8")
    (storage_dir / "target_sqlite.db").write_text("fake db marker\n", encoding="utf-8")
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    ccc = fake_bin / "ccc"
    ccc.write_text("#!/usr/bin/env bash\necho should-not-run >&2\nexit 99\n", encoding="utf-8")
    ccc.chmod(0o755)
    helper = fake_bin / "direct-helper"
    helper.write_text(
        "#!/usr/bin/env python3\n"
        "import json\n"
        "import sys\n"
        "payload = json.loads(sys.stdin.read())\n"
        "assert payload['storage_dir'].endswith('/.cocoindex_code')\n"
        "assert payload['target_db'].endswith('/target_sqlite.db')\n"
        "assert payload['query'] == 'semantic lookup'\n"
        "print(json.dumps([{\n"
        "  'file_path': 'src/runtime.py',\n"
        "  'language': 'python',\n"
        "  'content': 'def runtime_path():\\n    return \"direct-scoped-db\"',\n"
        "  'start_line': 7,\n"
        "  'end_line': 8,\n"
        "  'score': 0.73\n"
        "}]))\n",
        encoding="utf-8",
    )
    helper.chmod(0o755)
    monkeypatch.setenv("PATH", f"{fake_bin}{os.pathsep}{os.environ.get('PATH', '')}")
    monkeypatch.setenv("TEP_COCOINDEX_DIRECT_SEARCH_HELPER", str(helper))
    run_cli(
        context,
        "configure-runtime",
        "--backend",
        "code_intelligence.cocoindex.enabled=true",
        "--backend",
        "code_intelligence.cocoindex.mode=cli",
    )

    status = json.loads(
        run_cli(context, "backend-check", "--backend", "code_intelligence.cocoindex", "--root", str(repo), "--format", "json").stdout
    )
    coco = status["matches"][0]
    assert coco["storage"]["index_exists"] is True
    assert coco["storage"]["storage_marker_exists"] is True
    assert coco["storage"]["repo_marker_exists"] is False
    assert coco["storage"]["cli_search_ready"] is False
    assert coco["storage"]["runtime_search_ready"] is True
    assert coco["storage"]["search_ready"] is True
    assert coco["storage"]["runtime_path"] == "direct-scoped-db"
    assert any("direct scoped DB runtime path" in warning for warning in coco["warnings"])
    repo_marker = repo / ".cocoindex_code"
    repo_marker.mkdir()
    (repo_marker / "settings.yml").write_text("include_patterns: ['**/*.py']\nexclude_patterns: []\n", encoding="utf-8")
    marker_status = json.loads(
        run_cli(context, "backend-check", "--backend", "code_intelligence.cocoindex", "--root", str(repo), "--format", "json").stdout
    )
    marker_coco = marker_status["matches"][0]
    assert marker_coco["storage"]["repo_marker_exists"] is True
    assert marker_coco["storage"]["cli_search_ready"] is True
    assert marker_coco["storage"]["runtime_path"] == "direct-scoped-db"

    search = json.loads(
        run_cli(context, "code-search", "--root", str(repo), "--query", "semantic lookup", "--format", "json").stdout
    )
    backend = search["backend_results"]
    assert backend["returncode"] == 0
    assert backend["runtime_path"] == "direct-scoped-db"
    assert backend["storage"]["repo_marker_exists"] is True
    assert backend["storage"]["runtime_search_ready"] is True
    assert backend["results"][0]["target"] == {"path": "src/runtime.py", "line_start": 7, "line_end": 8}
    assert backend["results"][0]["runtime_path"] == "direct-scoped-db"


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

    missing_task = run_cli(
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
        "historical mutating action without task",
        check=False,
    )
    assert missing_task.returncode == 1
    assert "require an active TASK-*" in missing_task.stdout

    run_cli(
        context,
        "start-task",
        "--scope",
        "demo.action",
        "--title",
        "Record bounded historical action",
        "--related-claim",
        claim_id,
        "--note",
        "active task for historical action",
    )
    task_id = only_record_id(context, "task")
    chain = context.parent / "historical-action-chain.json"
    chain.write_text(
        json.dumps(
            {
                "task": "record bounded historical action",
                "nodes": [
                    {"role": "fact", "ref": claim_id, "quote": "A bounded edit was justified."},
                    {"role": "task", "ref": task_id, "quote": "Record bounded historical action"},
                ],
                "edges": [{"from": claim_id, "to": task_id, "relation": "supports bounded task"}],
            }
        ),
        encoding="utf-8",
    )
    run_cli(context, "validate-decision", "--mode", "edit", "--kind", "edit", "--chain", str(chain), "--emit-permit")
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
        "--evidence-chain",
        str(chain),
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

    missing_permit = run_cli(
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
        "missing grant",
        check=False,
    )
    assert missing_permit.returncode == 1
    assert "fresh valid GRANT-*" in missing_permit.stdout

    permit_result = run_cli(
        context,
        "validate-decision",
        "--mode",
        "edit",
        "--kind",
        "edit",
        "--chain",
        str(chain),
        "--emit-permit",
    )
    assert "## Reason Grant" in permit_result.stdout
    assert "## Chain Permit" not in permit_result.stdout
    assert "## Signed Chain" in permit_result.stdout
    assert "chain_hash" in permit_result.stdout
    assert f"- fact `{claim_id}`: \"Bounded edit is supported by runtime evidence.\"" in permit_result.stdout
    assert f"- task `{task_id}`: \"Bounded evidence-authorized edit\"" in permit_result.stdout

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


def test_grant_requires_current_task_node_and_uses_configured_ttl(tmp_path: Path) -> None:
    context = bootstrap_context(tmp_path)

    run_cli(
        context,
        "record-source",
            "--scope",
            "demo.grant",
        "--source-kind",
        "runtime",
        "--critique-status",
        "accepted",
        "--origin-kind",
        "command",
        "--origin-ref",
            "pytest grant",
        "--quote",
        "validated reasoning supports a bounded action",
        "--note",
            "grant source",
    )
    source_id = only_record_id(context, "source")
    run_cli(
        context,
        "record-claim",
            "--scope",
            "demo.grant",
        "--plane",
        "runtime",
        "--status",
        "supported",
        "--statement",
        "Validated reasoning supports a bounded action.",
        "--source",
        source_id,
        "--note",
            "grant claim",
    )
    claim_id = only_record_id(context, "claim")
    fact_only_chain = context.parent / "fact-only-chain.json"
    fact_only_chain.write_text(
        json.dumps(
                {
                    "task": "grant without task node",
                    "nodes": [{"role": "fact", "ref": claim_id, "quote": "Validated reasoning supports a bounded action."}],
                    "edges": [{"from": claim_id, "to": claim_id, "relation": "supports-decision"}],
                }
            ),
        encoding="utf-8",
    )

    no_task = run_cli(
        context,
        "validate-decision",
        "--mode",
        "edit",
        "--kind",
        "write",
        "--chain",
        str(fact_only_chain),
        "--emit-permit",
        check=False,
    )
    assert no_task.returncode == 1
    assert "reason steps require an active TASK-*" in no_task.stdout

    run_cli(
        context,
        "start-task",
        "--scope",
        "demo.grant",
        "--title",
        "Bounded grant task",
        "--related-claim",
        claim_id,
        "--note",
        "active task for grant",
    )
    task_id = only_record_id(context, "task")

    missing_task_node = run_cli(
        context,
        "validate-decision",
        "--mode",
        "edit",
        "--kind",
        "write",
        "--chain",
        str(fact_only_chain),
        "--emit-permit",
        check=False,
    )
    assert missing_task_node.returncode == 1
    assert f"exactly one task node matching current TASK-* {task_id}" in missing_task_node.stdout

    task_chain = context.parent / "task-chain.json"
    task_chain.write_text(
        json.dumps(
            {
                "task": "grant with task node",
                "nodes": [
                    {"role": "fact", "ref": claim_id, "quote": "Validated reasoning supports a bounded action."},
                    {"role": "task", "ref": task_id, "quote": "Bounded grant task"},
                ],
                "edges": [{"from": claim_id, "to": task_id, "relation": "supports bounded task"}],
            }
        ),
        encoding="utf-8",
    )
    configured = run_cli(context, "configure-runtime", "--chain-permit", "ttl_seconds=60")
    assert "chain_permits.ttl_seconds=60" in configured.stdout
    grant_payload = json.loads(
        run_cli(
            context,
            "validate-decision",
            "--mode",
            "edit",
            "--kind",
            "write",
            "--chain",
            str(task_chain),
            "--emit-permit",
            "--ttl-seconds",
            "3600",
            "--format",
            "json",
        ).stdout
    )
    grant = grant_payload["grant"]
    assert grant["task_ref"] == task_id
    assert grant["mode"] == "edit"
    assert grant["action_kind"] == "write"
    assert grant["reason_ref"] == grant_payload["reason"]["id"]
    assert grant_payload["reason"]["signed_chain"]["node_count"] == 2
    issued = datetime.fromisoformat(grant["issued_at"])
    expires = datetime.fromisoformat(grant["expires_at"])
    assert 30 <= (expires - issued).total_seconds() <= 60


def test_reason_ledger_grants_one_shot_access_and_detects_tamper(tmp_path: Path) -> None:
    context = bootstrap_context(tmp_path)

    source_id = recorded_id(
        run_cli(
            context,
            "record-source",
            "--scope",
            "demo.reason",
            "--source-kind",
            "runtime",
            "--critique-status",
            "accepted",
            "--origin-kind",
            "command",
            "--origin-ref",
            "pytest reason",
            "--quote",
            "reasoned action is supported",
            "--note",
            "reason source",
        ),
        "source",
    )
    claim_id = recorded_id(
        run_cli(
            context,
            "record-claim",
            "--scope",
            "demo.reason",
            "--plane",
            "runtime",
            "--status",
            "supported",
            "--statement",
            "Reasoned action is supported.",
            "--source",
            source_id,
            "--note",
            "reason claim",
        ),
        "claim",
    )
    task_id = recorded_id(
        run_cli(
            context,
            "start-task",
            "--scope",
            "demo.reason",
            "--title",
            "Execute a reasoned action",
            "--related-claim",
            claim_id,
            "--note",
            "active task for reason ledger",
        ),
        "task",
    )
    chain = context.parent / "reason-chain.json"
    chain.write_text(
        json.dumps(
            {
                "task": "execute a reasoned action",
                "nodes": [
                    {"role": "fact", "ref": claim_id, "quote": "Reasoned action is supported."},
                    {"role": "task", "ref": task_id, "quote": "Execute a reasoned action"},
                ],
                "edges": [{"from": claim_id, "to": task_id, "relation": "supports bounded task"}],
            }
        ),
        encoding="utf-8",
    )

    decision = run_cli(
        context,
        "validate-decision",
        "--mode",
        "edit",
        "--kind",
        "write",
        "--chain",
        str(chain),
        "--emit-permit",
    )
    reason_match = re.search(r"reason: `(REASON-\d{8}-[0-9a-f]{8})`", decision.stdout)
    access_match = re.search(r"grant: `(GRANT-\d{8}-[0-9a-f]{8})`", decision.stdout)
    assert reason_match, decision.stdout
    assert access_match, decision.stdout
    reason_id = reason_match.group(1)
    access_id = access_match.group(1)
    current = run_cli(context, "reason-current")
    assert reason_id in current.stdout
    assert access_id in current.stdout

    run_cli(
        context,
        "record-run",
        "--command",
        "echo reasoned",
        "--exit-code",
        "0",
        "--action-kind",
        "write",
        "--grant-ref",
        access_id,
        "--note",
        "first run consumes the grant by linkage",
    )
    reused = run_cli(
        context,
        "reason-check-grant",
        "--mode",
        "edit",
        "--kind",
        "write",
        "--command",
        "echo reasoned",
        "--cwd",
        str(context.parent),
        check=False,
    )
    assert reused.returncode == 1
    assert "used" in reused.stdout or "no matching" in reused.stdout

    ledger = context / "runtime" / "reasoning" / "reasons.jsonl"
    ledger.write_text(ledger.read_text(encoding="utf-8").replace("execute a reasoned action", "tampered action", 1), encoding="utf-8")
    tampered = run_cli(context, "reason-current", check=False)
    assert tampered.returncode == 1
    assert "tampered" in tampered.stdout


def test_reason_ledger_records_reasoning_steps_parents_and_forks(tmp_path: Path) -> None:
    context = bootstrap_context(tmp_path)

    source_id = recorded_id(
        run_cli(
            context,
            "record-source",
            "--scope",
            "demo.reason-ledger",
            "--source-kind",
            "runtime",
            "--critique-status",
            "accepted",
            "--origin-kind",
            "command",
            "--origin-ref",
            "pytest reason ledger",
            "--quote",
            "reasoning can be recorded as a validated ledger step",
            "--note",
            "reason ledger source",
        ),
        "source",
    )
    claim_id = recorded_id(
        run_cli(
            context,
            "record-claim",
            "--scope",
            "demo.reason-ledger",
            "--plane",
            "runtime",
            "--status",
            "supported",
            "--statement",
            "Reasoning can be recorded as a validated ledger step.",
            "--source",
            source_id,
            "--note",
            "reason ledger claim",
        ),
        "claim",
    )
    task_id = recorded_id(
        run_cli(
            context,
            "start-task",
            "--scope",
            "demo.reason-ledger",
            "--title",
            "Record reason ledger branches",
            "--related-claim",
            claim_id,
            "--note",
            "active task for reason ledger branches",
        ),
        "task",
    )
    chain = context.parent / "ledger-chain.json"
    chain.write_text(
        json.dumps(
            {
                "task": "record reason ledger branches",
                "nodes": [
                    {"role": "fact", "ref": claim_id, "quote": "Reasoning can be recorded as a validated ledger step."},
                    {"role": "task", "ref": task_id, "quote": "Record reason ledger branches"},
                ],
                "edges": [{"from": claim_id, "to": task_id, "relation": "supports reasoning ledger work"}],
            }
        ),
        encoding="utf-8",
    )

    first = json.loads(
        run_cli(
            context,
            "reason-step",
            "--mode",
            "planning",
            "--chain",
            str(chain),
            "--why",
            "establish the first reasoning checkpoint",
            "--format",
            "json",
        ).stdout
    )
    assert first["parent_refs"] == []
    assert first["branch"] == "main"
    assert first["signed_chain"]["nodes"][0]["ref"] == claim_id

    duplicate = run_cli(
        context,
        "reason-step",
        "--mode",
        "planning",
        "--chain",
        str(chain),
        "--why",
        "mechanically repeat the previous checkpoint",
        "--format",
        "json",
        check=False,
    )
    assert duplicate.returncode == 1
    assert "duplicate parent" in duplicate.stdout

    source2_id = recorded_id(
        run_cli(
            context,
            "record-source",
            "--scope",
            "demo.reason-ledger",
            "--source-kind",
            "runtime",
            "--critique-status",
            "accepted",
            "--origin-kind",
            "command",
            "--origin-ref",
            "pytest reason ledger continuation",
            "--quote",
            "reasoning should advance with a changed chain",
            "--note",
            "reason ledger continuation source",
        ),
        "source",
    )
    claim2_id = recorded_id(
        run_cli(
            context,
            "record-claim",
            "--scope",
            "demo.reason-ledger",
            "--plane",
            "runtime",
            "--status",
            "supported",
            "--statement",
            "Reasoning should advance with a changed chain.",
            "--source",
            source2_id,
            "--note",
            "reason ledger continuation claim",
        ),
        "claim",
    )
    chain2 = context.parent / "reason-chain-2.json"
    chain2.write_text(
        json.dumps(
            {
                "task": "record reason ledger branches",
                "nodes": [
                    {"role": "fact", "ref": claim_id, "quote": "Reasoning can be recorded as a validated ledger step."},
                    {"role": "fact", "ref": claim2_id, "quote": "Reasoning should advance with a changed chain."},
                    {"role": "task", "ref": task_id, "quote": "Record reason ledger branches"},
                ],
                "edges": [
                    {"from": claim_id, "to": task_id, "relation": "supports reasoning ledger work"},
                    {"from": claim2_id, "to": task_id, "relation": "supports reasoning progression"},
                ],
            }
        ),
        encoding="utf-8",
    )
    second = json.loads(
        run_cli(
            context,
            "reason-step",
            "--mode",
            "planning",
            "--chain",
            str(chain2),
            "--why",
            "continue from the previous checkpoint with new support",
            "--format",
            "json",
        ).stdout
    )
    assert second["parent_refs"] == [first["id"]]

    fork = json.loads(
        run_cli(
            context,
            "reason-step",
            "--mode",
            "planning",
            "--chain",
            str(chain),
            "--parent",
            first["id"],
            "--branch",
            "alternative",
            "--why",
            "fork an alternative interpretation",
            "--format",
            "json",
        ).stdout
    )
    assert fork["parent_refs"] == [first["id"]]
    assert fork["branch"] == "alternative"

    current = run_cli(context, "reason-current").stdout
    assert "## Recent Reason Steps" in current
    assert f"reason `{first['id']}` branch=`main` parents=`none`" in current
    assert f"reason `{second['id']}` branch=`main` parents=`{first['id']}`" in current
    assert f"reason `{fork['id']}` branch=`alternative` parents=`{first['id']}`" in current

    run_cli(context, "pause-task", "--note", "switch to another task for parent-scope validation")
    other_task_id = recorded_id(
        run_cli(
            context,
            "start-task",
            "--scope",
            "demo.reason-ledger.other",
            "--title",
            "Other reason task",
            "--related-claim",
            claim_id,
            "--note",
            "separate active task",
        ),
        "task",
    )
    other_chain = context.parent / "other-ledger-chain.json"
    other_chain.write_text(
        json.dumps(
            {
                "task": "other reason task",
                "nodes": [
                    {"role": "fact", "ref": claim_id, "quote": "Reasoning can be recorded as a validated ledger step."},
                    {"role": "task", "ref": other_task_id, "quote": "Other reason task"},
                ],
                "edges": [{"from": claim_id, "to": other_task_id, "relation": "supports separate task"}],
            }
        ),
        encoding="utf-8",
    )
    cross_task_parent = run_cli(
        context,
        "reason-step",
        "--mode",
        "planning",
        "--chain",
        str(other_chain),
        "--parent",
        first["id"],
        "--why",
        "try to reuse a parent from another task",
        check=False,
    )
    assert cross_task_parent.returncode == 1
    assert f"parent reason {first['id']} belongs to another TASK-*" in cross_task_parent.stdout


def test_lookup_defaults_to_new_reason_chain_nodes(tmp_path: Path) -> None:
    context = bootstrap_context(tmp_path)
    workspace_id = recorded_id(
        run_cli(
            context,
            "record-workspace",
            "--workspace-key",
            "lookup-chain-workspace",
            "--title",
            "Lookup chain workspace",
            "--note",
            "workspace for lookup chain extension",
        ),
        "workspace",
    )
    run_cli(context, "set-current-workspace", "--workspace", workspace_id)
    source1_id = recorded_id(
        run_cli(
            context,
            "record-source",
            "--scope",
            "demo.lookup-chain",
            "--source-kind",
            "runtime",
            "--critique-status",
            "accepted",
            "--origin-kind",
            "command",
            "--origin-ref",
            "pytest lookup chain alpha",
            "--quote",
            "alpha-only-token supports the lookup chain",
            "--note",
            "lookup chain alpha source",
        ),
        "source",
    )
    claim1_id = recorded_id(
        run_cli(
            context,
            "record-claim",
            "--scope",
            "demo.lookup-chain",
            "--plane",
            "runtime",
            "--status",
            "supported",
            "--statement",
            "Alpha-only-token supports the lookup chain.",
            "--source",
            source1_id,
            "--note",
            "lookup chain alpha claim",
        ),
        "claim",
    )
    source2_id = recorded_id(
        run_cli(
            context,
            "record-source",
            "--scope",
            "demo.lookup-chain",
            "--source-kind",
            "runtime",
            "--critique-status",
            "accepted",
            "--origin-kind",
            "command",
            "--origin-ref",
            "pytest lookup chain beta",
            "--quote",
            "beta extension supports the lookup chain",
            "--note",
            "lookup chain beta source",
        ),
        "source",
    )
    claim2_id = recorded_id(
        run_cli(
            context,
            "record-claim",
            "--scope",
            "demo.lookup-chain",
            "--plane",
            "runtime",
            "--status",
            "supported",
            "--statement",
            "Beta extension supports the lookup chain.",
            "--source",
            source2_id,
            "--note",
            "lookup chain beta claim",
        ),
        "claim",
    )
    task_id = recorded_id(
        run_cli(
            context,
            "start-task",
            "--scope",
            "demo.lookup-chain",
            "--title",
            "Continue lookup chain",
            "--related-claim",
            claim1_id,
            "--note",
            "lookup chain task",
        ),
        "task",
    )
    chain1 = tmp_path / "lookup-chain-1.json"
    chain1.write_text(
        json.dumps(
            {
                "task": "continue lookup chain",
                "nodes": [
                    {"role": "fact", "ref": claim1_id, "quote": "Alpha-only-token supports the lookup chain."},
                    {"role": "task", "ref": task_id, "quote": "Continue lookup chain"},
                ],
                "edges": [{"from": claim1_id, "to": task_id, "relation": "supports initial lookup reasoning"}],
            }
        ),
        encoding="utf-8",
    )
    reason = json.loads(
        run_cli(
            context,
            "reason-step",
            "--mode",
            "planning",
            "--chain",
            str(chain1),
            "--why",
            "seed lookup chain with the first fact",
            "--format",
            "json",
        ).stdout
    )

    lookup = json.loads(
        run_cli(
            context,
            "lookup",
            "--query",
            "beta extension lookup chain",
            "--reason",
            "planning",
            "--kind",
            "facts",
            "--format",
            "json",
        ).stdout
    )
    starter = lookup["chain_starter"]
    assert starter["chain_extension"]["current_reason_ref"] == reason["id"]
    refs = {node["ref"] for node in starter["nodes"]}
    assert claim2_id in refs
    assert claim1_id not in refs
    assert task_id in refs

    fallback = json.loads(
        run_cli(
            context,
            "lookup",
            "--query",
            "alpha-only-token",
            "--reason",
            "planning",
            "--kind",
            "facts",
            "--format",
            "json",
        ).stdout
    )
    fallback_starter = fallback["chain_starter"]
    assert fallback_starter["chain_extension"]["current_reason_ref"] == reason["id"]
    assert not any(node["ref"] == claim1_id for node in fallback_starter["nodes"])
    assert any("No new fact node" in note for note in fallback_starter["notes"])


def test_evidence_authorized_model_and_flow_require_grants(tmp_path: Path) -> None:
    context = bootstrap_context(tmp_path)
    claim_id = user_confirmed_theory_claim(
        context,
        "demo.model-permit",
        "User confirms that the cache refreshes only at startup.",
    )
    run_cli(
        context,
        "start-task",
        "--scope",
        "demo.model-permit",
        "--title",
        "Record model and flow from confirmed theory",
        "--related-claim",
        claim_id,
        "--note",
        "active task for model and flow permits",
    )
    task_id = only_record_id(context, "task")

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

    blocked_model = run_cli(
        context,
        "record-model",
        "--knowledge-class",
        "investigation",
        "--domain",
        "smartpick",
        "--scope",
        "demo.model-permit",
        "--aspect",
        "cache-refresh",
        "--status",
        "working",
        "--summary",
        "Cache refreshes only at startup.",
        "--claim",
        claim_id,
        "--note",
        "model without permit",
        check=False,
    )
    assert blocked_model.returncode == 1
    assert "mode=model" in blocked_model.stdout

    model_chain = context.parent / "model-chain.json"
    model_chain.write_text(
        json.dumps(
            {
                "task": "record model from confirmed theory",
                "nodes": [
                    {"role": "fact", "ref": claim_id, "quote": "cache refreshes only at startup"},
                    {"role": "task", "ref": task_id, "quote": "Record model and flow from confirmed theory"},
                ],
                "edges": [{"from": claim_id, "to": task_id, "relation": "anchors-model-task"}],
            }
        ),
        encoding="utf-8",
    )
    run_cli(context, "validate-decision", "--mode", "model", "--chain", str(model_chain), "--emit-permit")

    model_id = recorded_id(
        run_cli(
            context,
            "record-model",
            "--knowledge-class",
            "investigation",
            "--domain",
            "smartpick",
            "--scope",
            "demo.model-permit",
            "--aspect",
            "cache-refresh",
            "--status",
            "working",
            "--summary",
            "Cache refreshes only at startup.",
            "--claim",
            claim_id,
            "--note",
            "model with permit",
        ),
        "model",
    )

    blocked_flow = run_cli(
        context,
        "record-flow",
        "--knowledge-class",
        "investigation",
        "--domain",
        "smartpick",
        "--scope",
        "demo.model-permit",
        "--status",
        "working",
        "--summary",
        "Startup-only cache flow.",
        "--model",
        model_id,
        "--oracle-success",
        claim_id,
        "--step-id",
        "step-1",
        "--step-label",
        "cache initialized at startup",
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
        "flow without permit",
        check=False,
    )
    assert blocked_flow.returncode == 1
    assert "mode=flow" in blocked_flow.stdout

    flow_chain = context.parent / "flow-chain.json"
    flow_chain.write_text(
        json.dumps(
            {
                "task": "record flow from confirmed model",
                "nodes": [
                    {"role": "fact", "ref": claim_id, "quote": "cache refreshes only at startup"},
                    {"role": "model", "ref": model_id, "quote": "Cache refreshes only at startup."},
                    {"role": "task", "ref": task_id, "quote": "Record model and flow from confirmed theory"},
                ],
                "edges": [
                    {"from": claim_id, "to": model_id, "relation": "anchors-flow"},
                    {"from": model_id, "to": task_id, "relation": "supports-flow-task"},
                ],
            }
        ),
        encoding="utf-8",
    )
    run_cli(context, "validate-decision", "--mode", "flow", "--chain", str(flow_chain), "--emit-permit")

    flow_id = recorded_id(
        run_cli(
            context,
            "record-flow",
            "--knowledge-class",
            "investigation",
            "--domain",
            "smartpick",
            "--scope",
            "demo.model-permit",
            "--status",
            "working",
            "--summary",
            "Startup-only cache flow.",
            "--model",
            model_id,
            "--oracle-success",
            claim_id,
            "--step-id",
            "step-1",
            "--step-label",
            "cache initialized at startup",
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
            "flow with permit",
        ),
        "flow",
    )
    assert flow_id.startswith("FLOW-")


def test_flow_accepted_deviation_allows_user_permission(tmp_path: Path) -> None:
    context = bootstrap_context(tmp_path)

    claim_id = user_confirmed_theory_claim(
        context,
        "demo.issue",
        "User confirms that the accepted deviation exists in this flow.",
    )

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


def test_models_and_flows_require_user_confirmed_theory_claims(tmp_path: Path) -> None:
    context = bootstrap_context(tmp_path)

    runtime_source_id = recorded_id(
        run_cli(
            context,
            "record-source",
            "--scope",
            "demo.theory-boundary",
            "--source-kind",
            "runtime",
            "--critique-status",
            "accepted",
            "--origin-kind",
            "command",
            "--origin-ref",
            "pytest runtime observation",
            "--quote",
            "Runtime observed that cache refresh did not happen immediately.",
            "--note",
            "runtime source is not enough to define a model",
        ),
        "source",
    )
    runtime_claim_id = recorded_id(
        run_cli(
            context,
            "record-claim",
            "--scope",
            "demo.theory-boundary",
            "--plane",
            "runtime",
            "--status",
            "supported",
            "--statement",
            "Cache refresh did not happen immediately in this run.",
            "--source",
            runtime_source_id,
            "--note",
            "runtime-only observation",
        ),
        "claim",
    )

    blocked_runtime_model = run_cli(
        context,
        "record-model",
        "--knowledge-class",
        "investigation",
        "--domain",
        "smartpick",
        "--scope",
        "demo.theory-boundary",
        "--aspect",
        "cache-refresh",
        "--status",
        "working",
        "--summary",
        "Runtime-only observation must not define the system model.",
        "--claim",
        runtime_claim_id,
        "--note",
        "blocked runtime-only model",
        check=False,
    )
    assert blocked_runtime_model.returncode == 1
    assert "user-confirmed theory claim" in blocked_runtime_model.stdout

    tentative_theory_source_id = recorded_id(
        run_cli(
            context,
            "record-source",
            "--scope",
            "demo.theory-boundary",
            "--source-kind",
            "theory",
            "--critique-status",
            "accepted",
            "--origin-kind",
            "agent",
            "--origin-ref",
            "pytest agent hypothesis",
            "--quote",
            "The cache may refresh only at startup.",
            "--note",
            "agent theory source",
        ),
        "source",
    )
    tentative_theory_claim_id = recorded_id(
        run_cli(
            context,
            "record-claim",
            "--scope",
            "demo.theory-boundary",
            "--plane",
            "theory",
            "--status",
            "tentative",
            "--statement",
            "The cache refreshes only at startup.",
            "--source",
            tentative_theory_source_id,
            "--note",
            "tentative theory claim",
        ),
        "claim",
    )

    blocked_tentative_model = run_cli(
        context,
        "record-model",
        "--knowledge-class",
        "investigation",
        "--domain",
        "smartpick",
        "--scope",
        "demo.theory-boundary",
        "--aspect",
        "cache-refresh",
        "--status",
        "working",
        "--summary",
        "Tentative theory must not define the system model.",
        "--claim",
        tentative_theory_claim_id,
        "--note",
        "blocked tentative model",
        check=False,
    )
    assert blocked_tentative_model.returncode == 1
    assert "user-confirmed theory claim" in blocked_tentative_model.stdout

    theory_claim_id = user_confirmed_theory_claim(
        context,
        "demo.theory-boundary",
        "User confirms that the cache refreshes only at startup.",
    )
    model_id = recorded_id(
        run_cli(
            context,
            "record-model",
            "--knowledge-class",
            "investigation",
            "--domain",
            "smartpick",
            "--scope",
            "demo.theory-boundary",
            "--aspect",
            "cache-refresh",
            "--status",
            "working",
            "--summary",
            "Cache refreshes only at startup.",
            "--claim",
            theory_claim_id,
            "--note",
            "allowed user-confirmed theory model",
        ),
        "model",
    )
    flow_id = recorded_id(
        run_cli(
            context,
            "record-flow",
            "--knowledge-class",
            "investigation",
            "--domain",
            "smartpick",
            "--scope",
            "demo.theory-boundary",
            "--status",
            "working",
            "--summary",
            "Startup-only cache flow.",
            "--model",
            model_id,
            "--precondition-claim",
            theory_claim_id,
            "--oracle-success",
            theory_claim_id,
            "--step-id",
            "step-1",
            "--step-label",
            "cache initialized at startup",
            "--step-status",
            "aligned",
            "--step-claims",
            theory_claim_id,
            "--step-next",
            "",
            "--step-open-questions",
            "",
            "--step-accepted-deviation-refs",
            "",
            "--note",
            "allowed user-confirmed theory flow",
        ),
        "flow",
    )
    assert load_record(context, "flow", flow_id)["model_refs"] == [model_id]


def test_promote_model_and_mark_stale_are_conservative(tmp_path: Path) -> None:
    context = bootstrap_context(tmp_path)

    claim_id = user_confirmed_theory_claim(
        context,
        "demo.issue",
        "User confirms that gateway timeout happens before provider ack.",
    )

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

    claim_id = user_confirmed_theory_claim(
        context,
        "demo.bridge",
        "User confirms that Bridge check-r1 recovers after retry.",
    )
    source_id = load_record(context, "claim", claim_id)["source_refs"][0]

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
    assert "- requested: debug bridge check-r1 retry" in brief
    full_brief = run_cli(context, "brief-context", "--task", "debug bridge check-r1 retry", "--detail", "full").stdout
    assert "- requested: debug bridge check-r1 retry" in full_brief
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
    assert next_step_payload["api_contract"]["normal_entrypoint"] == "lookup"
    assert next_step_payload["route_steps"][0].startswith("validate-task-decomposition ")
    assert any(step.startswith("lookup ") for step in next_step_payload["route_steps"])
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
    assert "User confirms that Bridge check-r1 recovers after retry." in reasoning
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


def test_validate_decision_requires_indexed_hypotheses_and_blocks_proof_modes(tmp_path: Path) -> None:
    context = bootstrap_context(tmp_path)

    run_cli(
        context,
        "record-source",
        "--scope",
        "demo.decision",
        "--source-kind",
        "runtime",
        "--critique-status",
        "accepted",
        "--origin-kind",
        "command",
        "--origin-ref",
        "pytest decision",
        "--quote",
        "Retry recovered after a transient failure.",
        "--note",
        "decision source",
    )
    source_id = only_record_id(context, "source")
    fact_id = recorded_id(
        run_cli(
            context,
            "record-claim",
            "--scope",
            "demo.decision",
            "--plane",
            "runtime",
            "--status",
            "supported",
            "--statement",
            "Retry recovered after a transient failure.",
            "--source",
            source_id,
            "--note",
            "decision fact",
        ),
        "claim",
    )
    hypothesis_id = recorded_id(
        run_cli(
            context,
            "record-claim",
            "--scope",
            "demo.decision",
            "--plane",
            "runtime",
            "--status",
            "tentative",
            "--statement",
            "The transient failure may be caused by stale retry state.",
            "--source",
            source_id,
            "--note",
            "decision hypothesis",
        ),
        "claim",
    )

    missing_ref_chain = tmp_path / "missing-hypothesis-ref.json"
    missing_ref_chain.write_text(
        json.dumps(
            {
                "task": "bad unrecorded hypothesis",
                "nodes": [
                    {"role": "fact", "ref": fact_id, "quote": "Retry recovered"},
                    {"role": "hypothesis", "quote": "Probably stale retry state."},
                ],
                "edges": [{"from": fact_id, "to": fact_id, "relation": "frames"}],
            }
        ),
        encoding="utf-8",
    )
    missing_ref = run_cli(context, "validate-evidence-chain", "--file", str(missing_ref_chain), check=False)
    assert missing_ref.returncode == 1
    assert "hypothesis missing ref" in missing_ref.stdout
    assert "hypothesis add" in missing_ref.stdout

    chain = tmp_path / "decision-chain.json"
    chain.write_text(
        json.dumps(
            {
                "task": "planning with uncertainty",
                "nodes": [
                    {"role": "fact", "ref": fact_id, "quote": "Retry recovered"},
                    {
                        "role": "hypothesis",
                        "ref": hypothesis_id,
                        "quote": "stale retry state",
                    },
                ],
                "edges": [{"from": fact_id, "to": hypothesis_id, "relation": "frames-hypothesis"}],
            }
        ),
        encoding="utf-8",
    )
    missing_index = run_cli(context, "validate-evidence-chain", "--file", str(chain), check=False)
    assert missing_index.returncode == 1
    assert f"hypothesis `{hypothesis_id}` requires an active hypothesis index entry" in missing_index.stdout

    run_cli(context, "hypothesis", "add", "--claim", hypothesis_id, "--mode", "durable", "--note", "decision test hypothesis")
    planning = json.loads(
        run_cli(context, "validate-decision", "--mode", "planning", "--chain", str(chain), "--format", "json").stdout
    )
    assert planning["decision_valid"] is True
    assert planning["hypothesis_refs"] == [hypothesis_id]
    assert "planning" in planning["valid_for"]
    assert "edit" in planning["invalid_for"]
    assert planning["hypothesis_modes"][hypothesis_id] == "durable"

    edit = run_cli(context, "validate-decision", "--mode", "edit", "--chain", str(chain), check=False)
    assert edit.returncode == 1
    assert "cannot use hypothesis nodes as decisive proof" in edit.stdout

    second_hypothesis_id = recorded_id(
        run_cli(
            context,
            "record-claim",
            "--scope",
            "demo.decision",
            "--plane",
            "runtime",
            "--status",
            "tentative",
            "--statement",
            "The stale retry state may imply a broader retry scheduler defect.",
            "--source",
            source_id,
            "--note",
            "decision second hypothesis",
        ),
        "claim",
    )
    run_cli(
        context,
        "hypothesis",
        "add",
        "--claim",
        second_hypothesis_id,
        "--mode",
        "durable",
        "--note",
        "second decision test hypothesis",
    )
    stacked_chain = tmp_path / "stacked-hypothesis-chain.json"
    stacked_chain.write_text(
        json.dumps(
            {
                "task": "invalid stacked hypotheses",
                "nodes": [
                    {"role": "fact", "ref": fact_id, "quote": "Retry recovered"},
                    {"role": "hypothesis", "ref": hypothesis_id, "quote": "stale retry state"},
                    {
                        "role": "hypothesis",
                        "ref": second_hypothesis_id,
                        "quote": "broader retry scheduler defect",
                    },
                ],
                "edges": [
                    {"from": fact_id, "to": hypothesis_id, "relation": "frames-hypothesis"},
                    {"from": hypothesis_id, "to": second_hypothesis_id, "relation": "extends-hypothesis"},
                ],
            }
        ),
        encoding="utf-8",
    )
    stacked = run_cli(context, "validate-decision", "--mode", "planning", "--chain", str(stacked_chain), check=False)
    assert stacked.returncode == 1
    assert "uses hypothesis" in stacked.stdout
    assert "must be directly anchored" in stacked.stdout

    augmented = json.loads(run_cli(context, "augment-chain", "--file", str(chain), "--format", "json").stdout)
    hypothesis_node = next(node for node in augmented["chain"]["nodes"] if node["ref"] == hypothesis_id)
    assert hypothesis_node["hypothesis_entry"]["mode"] == "durable"


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
