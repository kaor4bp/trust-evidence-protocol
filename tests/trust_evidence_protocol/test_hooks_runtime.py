from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
BOOTSTRAP = REPO_ROOT / "plugins" / "trust-evidence-protocol" / "scripts" / "bootstrap_codex_context.py"
CLI = REPO_ROOT / "plugins" / "trust-evidence-protocol" / "scripts" / "context_cli.py"
RUNTIME_GATE = REPO_ROOT / "plugins" / "trust-evidence-protocol" / "scripts" / "runtime_gate.py"
HYDRATE_WRAPPER = REPO_ROOT / "plugins" / "trust-evidence-protocol" / "hooks" / "hydrate_context.sh"
PREFLIGHT_WRAPPER = REPO_ROOT / "plugins" / "trust-evidence-protocol" / "hooks" / "preflight_task.sh"
HOOK_DIR = REPO_ROOT / "plugins" / "trust-evidence-protocol" / "hooks" / "codex"


def run_script(script: Path, payload: dict | None = None, *, check: bool = True) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    if payload:
        cwd = payload.get("cwd")
        if isinstance(cwd, str):
            fixture_context = Path(cwd) / ".codex_context"
            if fixture_context.is_dir():
                env["TEP_CONTEXT_ROOT"] = str(fixture_context)
    result = subprocess.run(
        [sys.executable, str(script)],
        input=json.dumps(payload or {}),
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    if check and result.returncode != 0:
        raise AssertionError(f"script failed: {script}\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}")
    return result


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


def run_runtime(context: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        [sys.executable, str(RUNTIME_GATE), "--context", str(context), *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if check and result.returncode != 0:
        raise AssertionError(
            f"runtime command failed: {args}\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
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


def bootstrap_named_context(path: Path) -> Path:
    result = subprocess.run(
        [sys.executable, str(BOOTSTRAP), str(path)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise AssertionError(f"bootstrap failed\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}")
    return path


def record_ids(context: Path, record_type: str) -> list[str]:
    return sorted(path.stem for path in (context / "records" / record_type).glob("*.json"))


def recorded_id(result: subprocess.CompletedProcess[str], record_type: str) -> str:
    match = re.search(rf"Recorded {record_type} ([A-Z]+-\d{{8}}-[0-9a-f]{{8}})", result.stdout)
    assert match, result.stdout
    return match.group(1)


def strictness_approval(context: Path, value: str, permission_id: str | None = None) -> tuple[str, str]:
    request_args = [
        "request-strictness-change",
        value,
        "--reason",
        f"hook test approval for {value}",
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


def hook_payload(context: Path, command: str) -> dict:
    return {
        "cwd": str(context.parent),
        "tool_input": {
            "command": command,
        },
    }


def hook_json(script: Path, payload: dict) -> dict:
    result = run_script(script, payload)
    output = result.stdout.strip()
    assert output, f"expected hook output from {script}"
    return json.loads(output)


def test_runtime_gate_hydration_and_invalidation_cycle(tmp_path: Path) -> None:
    context = bootstrap_context(tmp_path)

    hydrate = run_runtime(context, "hydrate-context")
    assert hydrate.returncode == 0
    assert "Hydrated context" in hydrate.stdout

    show = run_runtime(context, "show-hydration")
    assert show.returncode == 0
    assert "hydration_status=hydrated" in show.stdout

    invalidate = run_runtime(context, "invalidate-hydration", "--reason", "test mutation")
    assert invalidate.returncode == 0
    assert "marked stale" in invalidate.stdout

    stale = run_runtime(context, "show-hydration", check=False)
    assert stale.returncode == 1
    assert "hydration_status=stale" in stale.stdout


def test_shell_wrappers_default_to_resolved_global_context(tmp_path: Path) -> None:
    home = tmp_path / "home"
    global_context = bootstrap_named_context(home / ".tep_context")
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    env = {**os.environ, "HOME": str(home)}

    hydrate = subprocess.run(
        [str(HYDRATE_WRAPPER)],
        cwd=workspace,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert hydrate.returncode == 0, hydrate.stderr
    assert f"Hydrated context: {global_context}" in hydrate.stdout

    preflight = subprocess.run(
        [str(PREFLIGHT_WRAPPER), "--mode", "reasoning"],
        cwd=workspace,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert preflight.returncode == 0, preflight.stdout + preflight.stderr


def test_shell_wrappers_keep_explicit_legacy_context_override(tmp_path: Path) -> None:
    home = tmp_path / "home"
    bootstrap_named_context(home / ".tep_context")
    legacy_context = bootstrap_context(tmp_path / "workspace")
    env = {**os.environ, "HOME": str(home)}

    hydrate = subprocess.run(
        [str(HYDRATE_WRAPPER), str(legacy_context)],
        cwd=legacy_context.parent,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert hydrate.returncode == 0, hydrate.stderr
    assert f"Hydrated context: {legacy_context}" in hydrate.stdout


def test_task_layer_is_explicit_in_hydration_and_hooks(tmp_path: Path) -> None:
    context = bootstrap_context(tmp_path)

    start = run_cli(
        context,
        "start-task",
        "--scope",
        "demo.task",
        "--title",
        "Debug bridge check-r1 retry",
        "--description",
        "Investigate current retry behavior.",
        "--note",
        "current execution focus",
    )
    assert "Started task" in start.stdout
    task_id = record_ids(context, "task")[0]

    settings = json.loads((context / "settings.json").read_text(encoding="utf-8"))
    assert settings["current_task_ref"] == task_id

    show = run_cli(context, "show-task")
    assert task_id in show.stdout
    assert "Debug bridge check-r1 retry" in show.stdout

    hydrate = run_runtime(context, "hydrate-context")
    assert f"Current task: {task_id}" in hydrate.stdout

    state = json.loads((context / "runtime" / "hydration.json").read_text(encoding="utf-8"))
    assert state["current_task"]["id"] == task_id
    assert state["current_task"]["status"] == "active"

    payload = hook_json(HOOK_DIR / "session_start_hydrate.py", hook_payload(context, ""))
    assert payload["systemMessage"] == "🛡️ Context hydrated with current task."
    assert task_id in payload["hookSpecificOutput"]["additionalContext"]

    complete = run_cli(context, "complete-task", "--note", "done")
    assert f"Completed task {task_id}" in complete.stdout
    task = json.loads((context / "records" / "task" / f"{task_id}.json").read_text(encoding="utf-8"))
    assert task["status"] == "completed"

    settings = json.loads((context / "settings.json").read_text(encoding="utf-8"))
    assert settings["current_task_ref"] is None

    hydrate_after = run_runtime(context, "hydrate-context")
    assert "Current task:" not in hydrate_after.stdout

    run_cli(
        context,
        "start-task",
        "--scope",
        "demo.task",
        "--title",
        "Stop probe",
        "--note",
        "temporary focus",
    )
    stopped_task_id = [record_id for record_id in record_ids(context, "task") if record_id != task_id][0]
    stop = run_cli(context, "stop-task", "--note", "not needed now")
    assert f"Stopped task {stopped_task_id}" in stop.stdout
    stopped_task = json.loads(
        (context / "records" / "task" / f"{stopped_task_id}.json").read_text(encoding="utf-8")
    )
    assert stopped_task["status"] == "stopped"


def test_project_and_restriction_layers_scope_context(tmp_path: Path) -> None:
    context = bootstrap_context(tmp_path)

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
    workspace_id = record_ids(context, "workspace")[0]
    run_cli(context, "set-current-workspace", "--workspace", workspace_id)

    run_cli(
        context,
        "record-project",
        "--project-key",
        "pray-and-run",
        "--title",
        "Pray And Run",
        "--root-ref",
        "/tmp/pray-and-run",
        "--note",
        "project boundary",
    )
    project_id = record_ids(context, "project")[0]
    workspace = json.loads((context / "records" / "workspace" / f"{workspace_id}.json").read_text(encoding="utf-8"))
    assert workspace["project_refs"] == [project_id]

    run_cli(context, "set-current-project", "--project", project_id)

    run_cli(
        context,
        "record-source",
        "--scope",
        "demo.project",
        "--source-kind",
        "runtime",
        "--critique-status",
        "accepted",
        "--origin-kind",
        "command",
        "--origin-ref",
        "pytest project",
        "--quote",
        "project scoped runtime fact",
        "--note",
        "runtime source",
    )
    source_id = record_ids(context, "source")[0]
    source = json.loads((context / "records" / "source" / f"{source_id}.json").read_text(encoding="utf-8"))
    assert source["workspace_refs"] == [workspace_id]
    assert source["project_refs"] == [project_id]

    run_cli(
        context,
        "record-claim",
        "--scope",
        "demo.project",
        "--plane",
        "runtime",
        "--status",
        "supported",
        "--statement",
        "Project scoped claim is available.",
        "--source",
        source_id,
        "--note",
        "supported claim",
    )
    claim_id = record_ids(context, "claim")[0]
    claim = json.loads((context / "records" / "claim" / f"{claim_id}.json").read_text(encoding="utf-8"))
    assert claim["workspace_refs"] == [workspace_id]
    assert claim["project_refs"] == [project_id]
    run_cli(context, "assign-project", "--project", project_id, "--record", claim_id)

    run_cli(
        context,
        "start-task",
        "--scope",
        "demo.project",
        "--title",
        "Project scoped task",
        "--project",
        project_id,
        "--note",
        "task under project",
    )
    task_id = record_ids(context, "task")[0]
    run_cli(context, "assign-task", "--task", task_id, "--record", claim_id)
    claim = json.loads((context / "records" / "claim" / f"{claim_id}.json").read_text(encoding="utf-8"))
    assert claim["task_refs"] == [task_id]

    run_cli(
        context,
        "record-permission",
        "--scope",
        "demo.project",
        "--applies-to",
        "task",
        "--grant",
        "Allow task-local safe debugging.",
        "--note",
        "task-local permission",
    )
    permission_id = record_ids(context, "permission")[0]
    permission = json.loads(
        (context / "records" / "permission" / f"{permission_id}.json").read_text(encoding="utf-8")
    )
    assert permission["task_refs"] == [task_id]

    run_cli(
        context,
        "record-restriction",
        "--scope",
        "demo.project",
        "--title",
        "No destructive probes",
        "--applies-to",
        "project",
        "--project",
        project_id,
        "--rule",
        "Do not run destructive probes for this project.",
        "--note",
        "project restriction",
    )
    restriction_id = record_ids(context, "restriction")[0]

    hydrate = run_runtime(context, "hydrate-context")
    assert f"Current workspace: {workspace_id}" in hydrate.stdout
    assert f"Current project: {project_id}" in hydrate.stdout
    assert f"Current task: {task_id}" in hydrate.stdout
    assert f"Active restrictions: 1 ({restriction_id})" in hydrate.stdout

    attention = (context / "review" / "attention.md").read_text(encoding="utf-8")
    assert "generated as an attention/navigation view" in attention
    assert "Trust order for lookup" in attention
    assert workspace_id in attention
    assert project_id in attention
    assert task_id in attention
    assert claim_id in attention
    assert restriction_id in attention

    show = run_runtime(context, "show-hydration")
    assert f"current_project={project_id}" in show.stdout
    assert "active_restrictions=1" in show.stdout

    brief = run_cli(context, "brief-context", "--task", "project scoped claim").stdout
    assert "Context Brief (compact)" in brief
    assert "project:" in brief
    assert project_id in brief
    assert permission_id in brief
    assert restriction_id in brief
    assert claim_id in brief

    chain = tmp_path / "restriction-chain.json"
    chain.write_text(
        json.dumps(
            {
                "task": "bad restriction proof",
                "nodes": [
                    {"role": "restriction", "ref": restriction_id, "quote": "No destructive probes"},
                    {"role": "fact", "ref": claim_id, "quote": "Project scoped claim is available."},
                ],
                "edges": [{"from": restriction_id, "to": claim_id, "relation": "invalid-control-as-proof"}],
            }
        ),
        encoding="utf-8",
    )
    invalid = run_cli(context, "validate-evidence-chain", "--file", str(chain), check=False)
    assert invalid.returncode == 1
    assert "uses authorization/control" in invalid.stdout


def test_session_start_hook_reports_conflicts(tmp_path: Path) -> None:
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
        "observed state",
        "--note",
        "runtime source",
    )
    source_id = record_ids(context, "source")[0]

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
        "Flag is true.",
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
        "true",
        "--comparison-polarity",
        "affirmed",
        "--note",
        "supported claim one",
    )
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
        "Flag is false.",
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
        "false",
        "--comparison-polarity",
        "affirmed",
        "--note",
        "supported claim two",
    )

    payload = hook_json(HOOK_DIR / "session_start_hydrate.py", hook_payload(context, ""))
    assert payload["systemMessage"] == "🛡️ Context hydrated with conflicts."
    assert "conflicts" in payload["hookSpecificOutput"]["additionalContext"]


def test_user_prompt_hook_warns_when_context_is_stale(tmp_path: Path) -> None:
    context = bootstrap_context(tmp_path)

    run_runtime(context, "hydrate-context")
    run_cli(
        context,
        "record-source",
        "--scope",
        "demo.stale",
        "--source-kind",
        "runtime",
        "--critique-status",
        "accepted",
        "--origin-kind",
        "command",
        "--origin-ref",
        "pytest stale",
        "--quote",
        "mutated context",
        "--note",
        "runtime source",
    )

    payload = hook_json(HOOK_DIR / "user_prompt_hydration_notice.py", hook_payload(context, ""))
    assert payload["systemMessage"] == "🛡️ Context hydration is stale."
    assert "stale or unhydrated" in payload["hookSpecificOutput"]["additionalContext"]


def test_user_prompt_hook_reminds_when_context_is_fresh(tmp_path: Path) -> None:
    context = bootstrap_context(tmp_path)

    run_runtime(context, "hydrate-context")

    payload = hook_json(HOOK_DIR / "user_prompt_hydration_notice.py", hook_payload(context, ""))
    assert payload["systemMessage"] == "🛡️ Trust Evidence Protocol reminder."
    additional_context = payload["hookSpecificOutput"]["additionalContext"]
    assert "Use the Trust Evidence Protocol skill" in additional_context
    assert "Evidence Chain" in additional_context
    assert "GLD-* + quote" in additional_context


def test_user_prompt_hook_captures_prompt_input_and_keeps_hydration_fresh(tmp_path: Path) -> None:
    context = bootstrap_context(tmp_path)

    run_runtime(context, "hydrate-context")
    payload = hook_payload(context, "")
    payload.update(
        {
            "prompt": "Remember that deterministic tests should avoid live agents.",
            "session_id": "session-123",
        }
    )

    hook_output = hook_json(HOOK_DIR / "user_prompt_hydration_notice.py", payload)
    assert hook_output["systemMessage"] == "🛡️ Trust Evidence Protocol reminder."
    assert "Use the Trust Evidence Protocol skill" in hook_output["hookSpecificOutput"]["additionalContext"]

    input_ids = record_ids(context, "input")
    assert len(input_ids) == 1
    record = json.loads((context / "records" / "input" / f"{input_ids[0]}.json").read_text(encoding="utf-8"))
    assert record["input_kind"] == "user_prompt"
    assert record["origin"] == {"kind": "codex-hook", "ref": "UserPromptSubmit:session-123"}
    assert record["session_ref"] == "session-123"
    assert record["text"] == "Remember that deterministic tests should avoid live agents."

    show = run_runtime(context, "show-hydration")
    assert "hydration_status=hydrated" in show.stdout


def test_quiet_hook_verbosity_compacts_session_and_suppresses_fresh_prompt_reminder(tmp_path: Path) -> None:
    context = bootstrap_context(tmp_path)

    run_cli(
        context,
        "start-task",
        "--type",
        "investigation",
        "--scope",
        "demo.quiet",
        "--title",
        "Investigate quiet hooks",
        "--note",
        "quiet hook task",
    )
    run_cli(context, "configure-runtime", "--hook-verbosity", "quiet", "--context-budget", "hydration=compact")

    session_payload = hook_json(HOOK_DIR / "session_start_hydrate.py", hook_payload(context, ""))
    assert session_payload["systemMessage"] == "🛡️ Context hydrated."
    additional_context = session_payload["hookSpecificOutput"]["additionalContext"]
    assert "Current task:" in additional_context
    assert "Use the Trust Evidence Protocol skill" not in additional_context

    prompt_result = run_script(HOOK_DIR / "user_prompt_hydration_notice.py", hook_payload(context, ""))
    assert prompt_result.stdout.strip() == ""


def test_pre_and_post_tool_hooks_track_mutating_bash_commands(tmp_path: Path) -> None:
    context = bootstrap_context(tmp_path)

    run_cli(context, "change-strictness", "proof-only")
    run_runtime(context, "hydrate-context")

    deny_payload = hook_json(
        HOOK_DIR / "pre_tool_use_guard.py",
        hook_payload(context, "rm -rf /tmp/example"),
    )
    assert deny_payload["hookSpecificOutput"]["permissionDecision"] == "deny"
    assert "Current allowed_freedom: `proof-only`" in deny_payload["hookSpecificOutput"]["additionalContext"]

    run_cli(
        context,
        "record-permission",
        "--scope",
        "demo.hooks",
        "--applies-to",
        "global",
        "--granted-by",
        "user",
        "--grant",
        "allowed_freedom:implementation-choice",
        "--note",
        "user explicitly allows implementation-choice for hook test",
    )
    permission_id = record_ids(context, "permission")[0]
    scoped_deny_payload = hook_json(
        HOOK_DIR / "pre_tool_use_guard.py",
        hook_payload(context, "rm -rf /tmp/example"),
    )
    assert permission_id in scoped_deny_payload["hookSpecificOutput"]["additionalContext"]
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
    run_runtime(context, "hydrate-context")

    allow_result = run_script(
        HOOK_DIR / "pre_tool_use_guard.py",
        hook_payload(context, "rm -rf /tmp/example"),
    )
    assert allow_result.stdout.strip() == ""

    post_payload = hook_json(
        HOOK_DIR / "post_tool_use_review.py",
        hook_payload(context, "echo hi > /tmp/example"),
    )
    assert "Hydration marked stale" in post_payload["systemMessage"]

    stale = run_runtime(context, "show-hydration", check=False)
    assert stale.returncode == 1
    assert "hydration_status=stale" in stale.stdout


def test_pre_tool_hook_allows_evidence_authorized_mutation_with_active_task(tmp_path: Path) -> None:
    context = bootstrap_context(tmp_path)

    run_cli(
        context,
        "record-source",
        "--scope",
        "demo.evidence-hook",
        "--source-kind",
        "runtime",
        "--critique-status",
        "accepted",
        "--origin-kind",
        "command",
        "--origin-ref",
        "pytest evidence hook",
        "--quote",
        "bounded hook mutation is supported",
        "--note",
        "evidence hook source",
    )
    source_id = record_ids(context, "source")[0]
    run_cli(
        context,
        "record-claim",
        "--scope",
        "demo.evidence-hook",
        "--plane",
        "runtime",
        "--status",
        "supported",
        "--statement",
        "Bounded hook mutation is supported.",
        "--source",
        source_id,
        "--note",
        "evidence hook claim",
    )
    claim_id = record_ids(context, "claim")[0]
    run_cli(
        context,
        "start-task",
        "--scope",
        "demo.evidence-hook",
        "--title",
        "Evidence hook task",
        "--related-claim",
        claim_id,
        "--note",
        "active task for evidence-authorized preflight",
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
    run_runtime(context, "hydrate-context")

    allow_result = run_script(
        HOOK_DIR / "pre_tool_use_guard.py",
        hook_payload(context, "echo hi > /tmp/example"),
    )
    assert allow_result.stdout.strip() == ""


def test_pre_tool_hook_does_not_block_read_only_shell_checks_with_stderr_redirect(tmp_path: Path) -> None:
    context = bootstrap_context(tmp_path)

    run_cli(context, "change-strictness", "proof-only")
    run_runtime(context, "hydrate-context")

    read_only_commands = [
        "rg -n \"needle\" . 2>/dev/null",
        "find . -maxdepth 2 -type f -print 2>/dev/null",
        "sed -n '1,20p' README.md 2>/dev/null",
        "rg -n \"needle\" patches/fix.patch 2>/dev/null",
        "sed -n '1,20p' docs/patch/notes.md 2>/dev/null",
        "find patches -type f -name '*.patch' 2>/dev/null",
        "rg -n \"needle\" . 2>/dev/null | head -20",
    ]
    for command in read_only_commands:
        result = run_script(HOOK_DIR / "pre_tool_use_guard.py", hook_payload(context, command))
        assert result.stdout.strip() == ""

    artifact_writes = [
        "printf '%s' screenshot > .codex_context/artifacts/screenshot.txt",
        "printf '%s' screenshot >> .codex_context/artifacts/screenshot.txt",
        "printf '%s' screenshot | tee .codex_context/artifacts/screenshot.txt",
        f"printf '%s' screenshot > {context / 'artifacts' / 'screenshot.txt'}",
    ]
    for command in artifact_writes:
        result = run_script(HOOK_DIR / "pre_tool_use_guard.py", hook_payload(context, command))
        assert result.stdout.strip() == ""

    stdout_redirect = hook_json(
        HOOK_DIR / "pre_tool_use_guard.py",
        hook_payload(context, "rg -n \"needle\" . > /tmp/rg-results"),
    )
    assert stdout_redirect["hookSpecificOutput"]["permissionDecision"] == "deny"

    tee_write = hook_json(
        HOOK_DIR / "pre_tool_use_guard.py",
        hook_payload(context, "rg -n \"needle\" . | tee /tmp/rg-results"),
    )
    assert tee_write["hookSpecificOutput"]["permissionDecision"] == "deny"

    workspace_artifact_name = hook_json(
        HOOK_DIR / "pre_tool_use_guard.py",
        hook_payload(context, "printf '%s' screenshot > artifacts/screenshot.txt"),
    )
    assert workspace_artifact_name["hookSpecificOutput"]["permissionDecision"] == "deny"

    patch_command = hook_json(
        HOOK_DIR / "pre_tool_use_guard.py",
        hook_payload(context, "patch -p1 < /tmp/change.diff"),
    )
    assert patch_command["hookSpecificOutput"]["permissionDecision"] == "deny"


def test_tool_hooks_ignore_heredoc_body_when_classifying_shell_policy(tmp_path: Path) -> None:
    context = bootstrap_context(tmp_path)

    run_cli(context, "change-strictness", "proof-only")
    run_runtime(context, "hydrate-context")

    read_only_version_check = """git status --short && git rev-parse --short HEAD && python3 - <<'PY'
import json
from pathlib import Path
print(json.loads(Path('plugins/trust-evidence-protocol/.codex-plugin/plugin.json').read_text())['version'])
PY"""
    pre_result = run_script(HOOK_DIR / "pre_tool_use_guard.py", hook_payload(context, read_only_version_check))
    assert pre_result.stdout.strip() == ""
    post_result = run_script(HOOK_DIR / "post_tool_use_review.py", hook_payload(context, read_only_version_check))
    assert post_result.stdout.strip() == ""

    heredoc_with_mutating_text = """python3 - <<'PY'
print("rm -rf /tmp/example")
print("patch -p1 < /tmp/change.diff")
print("not a redirect > /tmp/not-written")
PY"""
    pre_result = run_script(HOOK_DIR / "pre_tool_use_guard.py", hook_payload(context, heredoc_with_mutating_text))
    assert pre_result.stdout.strip() == ""
    post_result = run_script(HOOK_DIR / "post_tool_use_review.py", hook_payload(context, heredoc_with_mutating_text))
    assert post_result.stdout.strip() == ""

    heredoc_redirect = hook_json(
        HOOK_DIR / "pre_tool_use_guard.py",
        hook_payload(
            context,
            """python3 - <<'PY' > /tmp/heredoc-output
print("hello")
PY""",
        ),
    )
    assert heredoc_redirect["hookSpecificOutput"]["permissionDecision"] == "deny"
