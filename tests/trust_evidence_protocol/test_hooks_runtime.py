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
CLAUDE_HOOK_DIR = REPO_ROOT / "plugins" / "trust-evidence-protocol" / "hooks" / "claude"


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


def run_runtime(
    context: Path,
    *args: str,
    check: bool = True,
    cwd: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        [sys.executable, str(RUNTIME_GATE), "--context", str(context), *args],
        cwd=cwd or REPO_ROOT,
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
    match = re.search(rf"(?:Recorded {record_type}|Started {record_type}) ([A-Z]+-\d{{8}}-[0-9a-f]{{8}})", result.stdout)
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


def hook_json_with_env(script: Path, payload: dict, env: dict[str, str]) -> dict:
    result = subprocess.run(
        [sys.executable, str(script)],
        input=json.dumps(payload),
        cwd=REPO_ROOT,
        env={**os.environ, **env},
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
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


def test_runtime_gate_refuses_ambiguous_unanchored_hydration(tmp_path: Path) -> None:
    context = bootstrap_context(tmp_path)

    for key in ("first-workspace", "second-workspace"):
        run_cli(
            context,
            "record-workspace",
            "--workspace-key",
            key,
            "--title",
            key,
            "--root-ref",
            str(tmp_path / key),
            "--note",
            key,
        )

    blocked = run_runtime(context, "hydrate-context", check=False)
    assert blocked.returncode == 1
    assert "Explicit TEP workspace anchor required" in blocked.stdout
    assert "first-workspace" in blocked.stdout
    assert "second-workspace" in blocked.stdout

    still_blocked = run_runtime(context, "hydrate-context", "--allow-unanchored", check=False)
    assert still_blocked.returncode == 1
    assert "workspace_ref" in still_blocked.stdout


def test_runtime_gate_refuses_single_workspace_without_anchor(tmp_path: Path) -> None:
    context = bootstrap_context(tmp_path)
    workdir = tmp_path / "only-workspace"
    workdir.mkdir()
    run_cli(
        context,
        "record-workspace",
        "--workspace-key",
        "only-workspace",
        "--title",
        "Only Workspace",
        "--root-ref",
        str(workdir),
        "--note",
        "single workspace still requires anchor",
    )

    blocked = run_runtime(context, "hydrate-context", check=False)
    assert blocked.returncode == 1
    assert "Explicit TEP workspace anchor required" in blocked.stdout


def test_runtime_gate_points_full_cli_commands_to_context_cli(tmp_path: Path) -> None:
    context = bootstrap_context(tmp_path)

    result = run_runtime(context, "next-step", check=False)

    assert result.returncode == 2
    assert "runtime_gate.py only handles hook gates" in result.stderr
    assert "scripts/context_cli.py --context <context> next-step" in result.stderr

    reason_value = run_runtime(context, "invalidate-hydration", "--reason", "next-step")
    assert reason_value.returncode == 0
    assert "marked stale" in reason_value.stdout


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


def test_final_preflight_blocks_unclassified_inputs(tmp_path: Path) -> None:
    context = bootstrap_context(tmp_path)
    input_id = recorded_id(
        run_cli(
            context,
            "record-input",
            "--scope",
            "demo.final",
            "--input-kind",
            "user_prompt",
            "--origin-kind",
            "user",
            "--origin-ref",
            "chat-final",
            "--text",
            "Remember that final answers need classified input provenance.",
            "--note",
            "final preflight fixture",
        ),
        "input",
    )
    run_runtime(context, "hydrate-context")

    blocked = run_runtime(context, "preflight-task", "--mode", "final", check=False)
    assert blocked.returncode == 1
    assert "Final response blocked" in blocked.stdout
    assert input_id in blocked.stdout

    source_id = recorded_id(
        run_cli(
            context,
            "record-source",
            "--scope",
            "demo.final",
            "--source-kind",
            "memory",
            "--critique-status",
            "accepted",
            "--origin-kind",
            "input",
            "--origin-ref",
            input_id,
            "--quote",
            "final answers need classified input provenance",
            "--note",
            "classified final input",
        ),
        "source",
    )
    run_cli(context, "classify-input", "--input", input_id, "--derived-record", source_id, "--note", "closed")
    run_runtime(context, "hydrate-context")

    allowed = run_runtime(context, "preflight-task", "--mode", "final")
    assert "Preflight passed for final" in allowed.stdout


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

    blocked = run_runtime(context, "preflight-task", "--mode", "planning", check=False)
    assert blocked.returncode == 1
    assert "Current TASK-* is not confirmed" in blocked.stdout
    assert task_id in blocked.stdout

    confirmed = run_runtime(context, "confirm-task", "--task", task_id, "--note", "user confirmed focus")
    assert f"Confirmed current task {task_id}" in confirmed.stdout
    planning = run_runtime(context, "preflight-task", "--mode", "planning")
    assert "Preflight passed for planning" in planning.stdout

    run_cli(
        context,
        "record-source",
        "--scope",
        "demo.task",
        "--source-kind",
        "runtime",
        "--critique-status",
        "accepted",
        "--origin-kind",
        "command",
        "--origin-ref",
        "pytest",
        "--quote",
        "Task confirmation survives unrelated records.",
        "--note",
        "unrelated source after task confirmation",
    )
    run_runtime(context, "hydrate-context")
    still_confirmed = run_runtime(context, "preflight-task", "--mode", "planning")
    assert "Preflight passed for planning" in still_confirmed.stdout

    payload = hook_json(HOOK_DIR / "session_start_hydrate.py", hook_payload(context, ""))
    assert payload["systemMessage"] == "🛡️ Context hydrated with current task."
    session_context = payload["hookSpecificOutput"]["additionalContext"]
    assert task_id in session_context
    assert "TEP route:" in session_context
    assert "graph=" in session_context
    assert "Use TEP skill" in session_context

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


def test_autonomous_task_stop_guard_requires_terminal_outcome(tmp_path: Path) -> None:
    context = bootstrap_context(tmp_path)

    start = run_cli(
        context,
        "start-task",
        "--scope",
        "demo.autonomous",
        "--title",
        "Autonomous completion guard",
        "--autonomous",
        "--note",
        "autonomous task must not stop silently",
    )
    task_id = recorded_id(start, "task")
    task = json.loads((context / "records" / "task" / f"{task_id}.json").read_text(encoding="utf-8"))
    assert task["execution_mode"] == "autonomous"
    source_id = recorded_id(
        run_cli(
            context,
            "record-source",
            "--scope",
            "demo.autonomous",
            "--source-kind",
            "runtime",
            "--critique-status",
            "accepted",
            "--origin-kind",
            "command",
            "--origin-ref",
            "pytest autonomous completion",
            "--quote",
            "autonomous completion guard work is complete",
            "--note",
            "autonomous final permit source",
        ),
        "source",
    )
    claim_id = recorded_id(
        run_cli(
            context,
            "record-claim",
            "--scope",
            "demo.autonomous",
            "--plane",
            "runtime",
            "--status",
            "supported",
            "--statement",
            "Autonomous completion guard work is complete.",
            "--source",
            source_id,
            "--note",
            "autonomous final permit claim",
        ),
        "claim",
    )
    final_chain = tmp_path / "final-chain.json"
    final_chain.write_text(
        json.dumps(
            {
                "task": "autonomous completion proof",
                "nodes": [
                    {"role": "fact", "ref": claim_id, "quote": "Autonomous completion guard work is complete."},
                    {"role": "task", "ref": task_id, "quote": "Autonomous completion guard"},
                ],
                "edges": [{"from": claim_id, "to": task_id, "relation": "supports-completion"}],
            }
        ),
        encoding="utf-8",
    )
    run_cli(
        context,
        "confirm-atomic-task",
        "--task",
        task_id,
        "--deliverable",
        "Autonomous completion guard final response is controlled.",
        "--done",
        "Final stop requires a valid chain permit.",
        "--verify",
        "Stop guard and final preflight pass with permit.",
        "--boundary",
        "Only autonomous final gating.",
        "--blocker-policy",
        "Record OPEN-* for blockers.",
        "--note",
        "autonomous final task is atomic",
    )

    hydrate = run_runtime(context, "hydrate-context")
    assert f"Current task: {task_id}" in hydrate.stdout
    assert "mode=autonomous" in hydrate.stdout
    run_runtime(context, "confirm-task", "--task", task_id, "--note", "autonomous final focus")

    blocked = run_runtime(context, "stop-guard", "--last-assistant-message", "partial status", check=False)
    assert blocked.returncode == 1
    assert "Autonomous TASK-* cannot stop" in blocked.stdout
    assert "TEP TASK OUTCOME: done" in blocked.stdout

    no_final_permit = run_runtime(
        context,
        "stop-guard",
        "--last-assistant-message",
        "TEP TASK OUTCOME: done\nCompleted the requested work.",
        check=False,
    )
    assert no_final_permit.returncode == 1
    assert "mode=final" in no_final_permit.stdout
    final_preflight_block = run_runtime(context, "preflight-task", "--mode", "final", check=False)
    assert final_preflight_block.returncode == 1
    assert "mode=final" in final_preflight_block.stdout

    run_cli(context, "validate-decision", "--mode", "final", "--chain", str(final_chain), "--emit-permit")
    final_preflight = run_runtime(context, "preflight-task", "--mode", "final")
    assert "Preflight passed for final" in final_preflight.stdout
    accepted = run_runtime(
        context,
        "stop-guard",
        "--last-assistant-message",
        "TEP TASK OUTCOME: done\nCompleted the requested work.",
    )
    assert "Autonomous task stop accepted: done" in accepted.stdout

    telemetry = json.loads(run_cli(context, "telemetry-report", "--format", "json").stdout)
    assert telemetry["reason_access_missing_count"] >= 1
    assert telemetry["permit_issued_count"] >= 1
    assert telemetry["reason_access_used_count"] >= 1

    codex_payload = hook_json(
        HOOK_DIR / "stop_guard.py",
        {
            "cwd": str(context.parent),
            "last_assistant_message": "Stopping without classifying the autonomous task.",
        },
    )
    assert codex_payload["decision"] == "block"
    assert codex_payload["hookSpecificOutput"]["hookEventName"] == "Stop"
    assert "TEP TASK OUTCOME" in codex_payload["reason"]

    claude_payload = hook_json(
        CLAUDE_HOOK_DIR / "stop_guard.py",
        {
            "cwd": str(context.parent),
            "last_assistant_message": "Stopping without classifying the autonomous task.",
        },
    )
    assert claude_payload["decision"] == "block"
    assert claude_payload["hookSpecificOutput"]["hookEventName"] == "Stop"
    assert "TEP TASK OUTCOME" in claude_payload["reason"]

    recursive = run_script(
        HOOK_DIR / "stop_guard.py",
        {
            "cwd": str(context.parent),
            "last_assistant_message": "Still no marker.",
            "stop_hook_active": True,
        },
    )
    assert recursive.stdout.strip() == ""


def test_autonomous_task_outcome_check_requires_linked_obligations(tmp_path: Path) -> None:
    context = bootstrap_context(tmp_path)
    start = run_cli(
        context,
        "start-task",
        "--scope",
        "demo.autonomous.blocked",
        "--title",
        "Autonomous blocked work",
        "--autonomous",
        "--note",
        "autonomous task with a user question",
    )
    task_id = recorded_id(start, "task")
    run_runtime(context, "hydrate-context")

    blocked_without_obligation = run_runtime(
        context,
        "stop-guard",
        "--last-assistant-message",
        "TEP TASK OUTCOME: blocked",
        check=False,
    )
    assert blocked_without_obligation.returncode == 1
    assert "blocked requires a linked open question" in blocked_without_obligation.stdout

    open_question = run_cli(
        context,
        "record-open-question",
        "--domain",
        "demo",
        "--scope",
        "demo.autonomous.blocked",
        "--aspect",
        "user-answer",
        "--question",
        "Should the autonomous task continue with option A or option B?",
        "--task",
        task_id,
        "--note",
        "question required to unblock autonomous task",
    )
    open_question_id = recorded_id(open_question, "open_question")
    run_runtime(context, "hydrate-context")

    done_with_open_question = run_runtime(
        context,
        "stop-guard",
        "--last-assistant-message",
        "TEP TASK OUTCOME: done",
        check=False,
    )
    assert done_with_open_question.returncode == 1
    assert open_question_id in done_with_open_question.stdout
    assert "done requires no linked open obligations" in done_with_open_question.stdout

    user_question = run_runtime(
        context,
        "stop-guard",
        "--last-assistant-message",
        "TEP TASK OUTCOME: user-question",
    )
    assert "Autonomous task stop accepted: user-question" in user_question.stdout

    blocked = run_runtime(
        context,
        "stop-guard",
        "--last-assistant-message",
        "TEP TASK OUTCOME: blocked",
    )
    assert "Autonomous task stop accepted: blocked" in blocked.stdout

    completed = run_cli(context, "complete-task", "--task", task_id, "--note", "claim done anyway", check=False)
    assert completed.returncode == 1
    assert "Autonomous task cannot be completed" in completed.stdout

    outcome_json = json.loads(
        run_cli(context, "task-outcome-check", "--task", task_id, "--outcome", "user-question", "--format", "json").stdout
    )
    assert outcome_json["accepted"] is True
    assert outcome_json["blocking_obligations"][0]["id"] == open_question_id


def test_manual_task_stop_guard_allows_silent_stop(tmp_path: Path) -> None:
    context = bootstrap_context(tmp_path)
    run_cli(
        context,
        "start-task",
        "--scope",
        "demo.manual",
        "--title",
        "Manual task",
        "--note",
        "manual task should not require terminal outcome marker",
    )
    run_runtime(context, "hydrate-context")

    allowed = run_runtime(context, "stop-guard", "--last-assistant-message", "ordinary final answer")
    assert allowed.stdout.strip() == ""


def test_project_and_restriction_layers_scope_context(tmp_path: Path) -> None:
    context = bootstrap_context(tmp_path)
    workdir = tmp_path / "pray-and-run"
    workdir.mkdir()

    run_cli(
        context,
        "record-workspace",
        "--workspace-key",
        "qa-tim",
        "--title",
        "QA TIM Workspace",
        "--root-ref",
        str(workdir),
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
        str(workdir),
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
        "project scope test anchor",
    )

    hydrate = run_runtime(context, "hydrate-context", cwd=workdir)
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

    show = run_runtime(context, "show-hydration", cwd=workdir)
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


def test_show_hydration_warns_when_snapshot_focus_differs_from_local_anchor(tmp_path: Path) -> None:
    context = bootstrap_context(tmp_path)
    global_workdir = tmp_path / "global"
    global_workdir.mkdir()

    run_cli(
        context,
        "record-workspace",
        "--workspace-key",
        "global-workspace",
        "--title",
        "Global Workspace",
        "--root-ref",
        str(global_workdir),
        "--note",
        "global workspace",
    )
    global_workspace_id = record_ids(context, "workspace")[0]
    run_cli(context, "set-current-workspace", "--workspace", global_workspace_id)
    run_cli(
        context,
        "record-project",
        "--project-key",
        "global-project",
        "--title",
        "Global Project",
        "--root-ref",
        str(global_workdir),
        "--note",
        "global project",
    )
    global_project_id = record_ids(context, "project")[0]
    run_cli(context, "set-current-project", "--project", global_project_id)
    global_task_id = recorded_id(
        run_cli(
            context,
            "start-task",
            "--scope",
            "global.task",
            "--title",
            "Global task",
            "--type",
            "implementation",
            "--project",
            global_project_id,
            "--note",
            "global task",
        ),
        "task",
    )

    workdir = tmp_path / "anchored-workdir"
    workdir.mkdir()
    run_cli(
        context,
        "record-workspace",
        "--workspace-key",
        "anchor-workspace",
        "--title",
        "Anchor Workspace",
        "--root-ref",
        str(workdir),
        "--note",
        "anchor workspace",
    )
    anchor_workspace_id = [record_id for record_id in record_ids(context, "workspace") if record_id != global_workspace_id][0]
    run_cli(
        context,
        "record-project",
        "--project-key",
        "anchor-project",
        "--title",
        "Anchor Project",
        "--root-ref",
        str(workdir),
        "--workspace",
        anchor_workspace_id,
        "--note",
        "anchor project",
    )
    anchor_project_id = [record_id for record_id in record_ids(context, "project") if record_id != global_project_id][0]
    run_cli(context, "pause-task", "--task", global_task_id, "--note", "pause global task before anchor task")
    anchor_task_id = recorded_id(
        run_cli(
            context,
            "start-task",
            "--scope",
            "anchor.task",
            "--title",
            "Anchor task",
            "--type",
            "implementation",
            "--project",
            anchor_project_id,
            "--note",
            "anchor task",
        ),
        "task",
    )
    run_cli(context, "switch-task", "--task", global_task_id, "--note", "restore global task before anchor check")
    (global_workdir / ".tep").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "context_root": str(context),
                "workspace_ref": global_workspace_id,
                "project_ref": global_project_id,
                "task_ref": global_task_id,
                "note": "global local anchor",
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    global_hydrate = subprocess.run(
        [sys.executable, str(RUNTIME_GATE), "--context", str(context), "hydrate-context"],
        cwd=global_workdir,
        capture_output=True,
        text=True,
        check=False,
    )
    assert global_hydrate.returncode == 0, global_hydrate.stdout + global_hydrate.stderr
    (workdir / ".tep").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "context_root": str(context),
                "workspace_ref": anchor_workspace_id,
                "project_ref": anchor_project_id,
                "task_ref": anchor_task_id,
                "note": "local anchor",
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    mismatched = subprocess.run(
        [sys.executable, str(RUNTIME_GATE), "--context", str(context), "show-hydration"],
        cwd=workdir,
        capture_output=True,
        text=True,
        check=False,
    )
    assert mismatched.returncode == 1
    assert "snapshot_mismatch=current_workspace,current_project,current_task" in mismatched.stdout
    assert f"snapshot_current_workspace={global_workspace_id}" in mismatched.stdout
    assert f"effective_current_workspace={anchor_workspace_id}" in mismatched.stdout
    assert f"snapshot_current_project={global_project_id}" in mismatched.stdout
    assert f"effective_current_project={anchor_project_id}" in mismatched.stdout
    assert f"snapshot_current_task={global_task_id}" in mismatched.stdout
    assert f"effective_current_task={anchor_task_id}" in mismatched.stdout
    assert "action=run hydrate-context" in mismatched.stdout

    hydrated = subprocess.run(
        [sys.executable, str(RUNTIME_GATE), "--context", str(context), "hydrate-context"],
        cwd=workdir,
        capture_output=True,
        text=True,
        check=False,
    )
    assert hydrated.returncode == 0, hydrated.stdout + hydrated.stderr
    aligned = subprocess.run(
        [sys.executable, str(RUNTIME_GATE), "--context", str(context), "show-hydration"],
        cwd=workdir,
        capture_output=True,
        text=True,
        check=False,
    )
    assert aligned.returncode == 0
    assert "snapshot_mismatch=" not in aligned.stdout
    assert f"current_workspace={anchor_workspace_id}" in aligned.stdout
    assert f"current_task={anchor_task_id}" in aligned.stdout


def test_hooks_require_anchor_in_unanchored_cwd_when_multiple_workspaces_are_active(tmp_path: Path) -> None:
    context = bootstrap_context(tmp_path)

    run_cli(
        context,
        "record-workspace",
        "--workspace-key",
        "global-workspace",
        "--title",
        "Global Workspace",
        "--root-ref",
        str(tmp_path / "global"),
        "--note",
        "global workspace",
    )
    global_workspace_id = record_ids(context, "workspace")[0]
    run_cli(context, "set-current-workspace", "--workspace", global_workspace_id)

    workdir = tmp_path / "anchored-workdir"
    workdir.mkdir()
    run_cli(
        context,
        "record-workspace",
        "--workspace-key",
        "anchor-workspace",
        "--title",
        "Anchor Workspace",
        "--root-ref",
        str(workdir),
        "--note",
        "anchor workspace",
    )
    anchor_workspace_id = [record_id for record_id in record_ids(context, "workspace") if record_id != global_workspace_id][0]
    (workdir / ".tep").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "context_root": str(context),
                "workspace_ref": anchor_workspace_id,
                "note": "local anchor",
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    anchored_hydrate = subprocess.run(
        [sys.executable, str(RUNTIME_GATE), "--context", str(context), "hydrate-context"],
        cwd=workdir,
        capture_output=True,
        text=True,
        check=False,
    )
    assert anchored_hydrate.returncode == 0, anchored_hydrate.stdout + anchored_hydrate.stderr

    unanchored = tmp_path / "unanchored-cwd"
    unanchored.mkdir()
    payload = {"cwd": str(unanchored), "prompt": "continue TEP work", "session_id": "session-unanchored"}
    env = {"TEP_CONTEXT_ROOT": str(context)}

    prompt_output = hook_json_with_env(HOOK_DIR / "user_prompt_hydration_notice.py", payload, env)
    assert prompt_output["systemMessage"] == "🛡️ Explicit TEP anchor required."
    assert "active workspaces" in prompt_output["hookSpecificOutput"]["additionalContext"]
    assert "anchor-workspace" in prompt_output["hookSpecificOutput"]["additionalContext"]

    session_output = hook_json_with_env(HOOK_DIR / "session_start_hydrate.py", {"cwd": str(unanchored)}, env)
    assert session_output["systemMessage"] == "🛡️ Explicit TEP anchor required."

    aligned = subprocess.run(
        [sys.executable, str(RUNTIME_GATE), "--context", str(context), "show-hydration"],
        cwd=workdir,
        capture_output=True,
        text=True,
        check=False,
    )
    assert aligned.returncode == 0
    assert f"current_workspace={anchor_workspace_id}" in aligned.stdout
    assert not record_ids(context, "input")


def test_hooks_defer_unanchored_hydration_when_multiple_workspaces_are_active(tmp_path: Path) -> None:
    context = bootstrap_context(tmp_path)

    for key in ("first-workspace", "second-workspace"):
        run_cli(
            context,
            "record-workspace",
            "--workspace-key",
            key,
            "--title",
            key,
            "--root-ref",
            str(tmp_path / key),
            "--note",
            key,
        )
    unanchored = tmp_path / "unanchored-cwd"
    unanchored.mkdir()
    payload = {"cwd": str(unanchored), "prompt": "continue TEP work", "session_id": "session-unanchored"}
    env = {"TEP_CONTEXT_ROOT": str(context)}

    session_output = hook_json_with_env(HOOK_DIR / "session_start_hydrate.py", {"cwd": str(unanchored)}, env)
    assert session_output["systemMessage"] == "🛡️ Explicit TEP anchor required."
    assert "active workspaces" in session_output["hookSpecificOutput"]["additionalContext"]

    prompt_output = hook_json_with_env(HOOK_DIR / "user_prompt_hydration_notice.py", payload, env)
    assert prompt_output["systemMessage"] == "🛡️ Explicit TEP anchor required."
    assert "first-workspace" in prompt_output["hookSpecificOutput"]["additionalContext"]
    assert "second-workspace" in prompt_output["hookSpecificOutput"]["additionalContext"]
    assert not record_ids(context, "input")

    show = run_runtime(context, "show-hydration", check=False)
    assert show.returncode == 1
    assert "hydration_status=stale" in show.stdout


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
    assert payload["systemMessage"] == "🛡️ TEP reminder."
    additional_context = payload["hookSpecificOutput"]["additionalContext"]
    assert "TEP route:" in additional_context
    assert "graph=" in additional_context
    assert "Use TEP skill" in additional_context
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
    assert hook_output["systemMessage"] == "🛡️ TEP reminder."
    assert "TEP route:" in hook_output["hookSpecificOutput"]["additionalContext"]
    assert "graph=" in hook_output["hookSpecificOutput"]["additionalContext"]
    assert "Use TEP skill" in hook_output["hookSpecificOutput"]["additionalContext"]

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
    assert "TEP route:" in additional_context
    assert "graph=" in additional_context
    assert "Use TEP skill" not in additional_context

    quiet_prompt = hook_payload(context, "")
    quiet_prompt["prompt"] = "implement quiet route"
    prompt_payload = hook_json(HOOK_DIR / "user_prompt_hydration_notice.py", quiet_prompt)
    assert prompt_payload["systemMessage"] == "🛡️ TEP route."
    assert "TEP route: intent=edit" in prompt_payload["hookSpecificOutput"]["additionalContext"]
    assert "graph=" in prompt_payload["hookSpecificOutput"]["additionalContext"]
    assert "Use TEP skill" not in prompt_payload["hookSpecificOutput"]["additionalContext"]


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

    missing_task = run_script(
        HOOK_DIR / "pre_tool_use_guard.py",
        hook_payload(context, "rm -rf /tmp/example"),
    )
    assert "requires an active TASK-*" in missing_task.stdout

    source_id = recorded_id(
        run_cli(
            context,
            "record-source",
            "--scope",
            "demo.hooks",
            "--source-kind",
            "runtime",
            "--critique-status",
            "accepted",
            "--origin-kind",
            "command",
            "--origin-ref",
            "pytest hook mutation",
            "--quote",
            "hook mutation is bounded by a test fixture",
            "--note",
            "hook mutation source",
        ),
        "source",
    )
    claim_id = recorded_id(
        run_cli(
            context,
            "record-claim",
            "--scope",
            "demo.hooks",
            "--plane",
            "runtime",
            "--status",
            "supported",
            "--statement",
            "Hook mutation is bounded by a test fixture.",
            "--source",
            source_id,
            "--note",
            "hook mutation claim",
        ),
        "claim",
    )
    run_cli(
        context,
        "start-task",
        "--scope",
        "demo.hooks",
        "--title",
        "Track mutating hook command",
        "--related-claim",
        claim_id,
        "--note",
        "active task for mutating hook command",
    )
    task_id = record_ids(context, "task")[0]
    run_cli(
        context,
        "confirm-atomic-task",
        "--task",
        task_id,
        "--deliverable",
        "Mutating hook command is preflighted and reviewed.",
        "--done",
        "Pre and post hook assertions pass.",
        "--verify",
        "Focused hook test passes.",
        "--boundary",
        "Only hook command tracking behavior.",
        "--blocker-policy",
        "Record OPEN-* for blockers.",
        "--note",
        "confirm hook tracking task as atomic",
    )
    run_runtime(context, "hydrate-context")
    run_runtime(context, "confirm-task", "--task", task_id, "--note", "hook tracking focus confirmed")
    chain = tmp_path / "delete-chain.json"
    chain.write_text(
        json.dumps(
            {
                "task": "track mutating hook command",
                "nodes": [
                    {"role": "fact", "ref": claim_id, "quote": "Hook mutation is bounded by a test fixture."},
                    {"role": "task", "ref": task_id, "quote": "Track mutating hook command"},
                ],
                "edges": [{"from": claim_id, "to": task_id, "relation": "supports bounded task"}],
            }
        ),
        encoding="utf-8",
    )
    run_cli(
        context,
        "validate-decision",
        "--mode",
        "edit",
        "--kind",
        "delete",
        "--chain",
        str(chain),
        "--emit-permit",
    )

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
    run_id = record_ids(context, "run")[0]
    run_payload = json.loads((context / "records" / "run" / f"{run_id}.json").read_text(encoding="utf-8"))
    assert run_payload["command"] == "echo hi > /tmp/example"

    stale = run_runtime(context, "show-hydration", check=False)
    assert stale.returncode == 1
    assert "hydration_status=stale" in stale.stdout


def test_pre_tool_hook_blocks_mutation_targets_outside_current_workspace(tmp_path: Path) -> None:
    context = bootstrap_context(tmp_path)
    workdir = tmp_path / "current-workspace"
    workdir.mkdir()
    outside = tmp_path / "other-workspace"
    outside.mkdir()
    outside_file = outside / "plugin.py"
    outside_file.write_text("value = 'old'\n", encoding="utf-8")

    workspace_id = recorded_id(
        run_cli(
            context,
            "record-workspace",
            "--workspace-key",
            "current-workspace",
            "--title",
            "Current Workspace",
            "--root-ref",
            str(workdir),
            "--note",
            "current workspace boundary",
        ),
        "workspace",
    )
    run_cli(
        context,
        "init-anchor",
        "--directory",
        str(workdir),
        "--workspace",
        workspace_id,
        "--note",
        "path scope guard anchor",
    )
    anchored_hydrate = subprocess.run(
        [sys.executable, str(RUNTIME_GATE), "--context", str(context), "hydrate-context"],
        cwd=workdir,
        capture_output=True,
        text=True,
        check=False,
    )
    assert anchored_hydrate.returncode == 0, anchored_hydrate.stdout + anchored_hydrate.stderr

    denial = hook_json(
        HOOK_DIR / "pre_tool_use_guard.py",
        {
            "cwd": str(workdir),
            "tool_input": {"command": f"sed -i '' 's/old/new/' {outside_file}"},
        },
    )
    assert denial["hookSpecificOutput"]["permissionDecision"] == "deny"
    reason = denial["hookSpecificOutput"]["permissionDecisionReason"]
    assert "Mutation target outside current TEP workspace roots" in reason
    assert str(outside_file) in reason


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
    task_id = record_ids(context, "task")[0]
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
    run_runtime(context, "confirm-task", "--task", task_id, "--note", "hook test focus confirmed")

    blocked_result = run_script(
        HOOK_DIR / "pre_tool_use_guard.py",
        hook_payload(context, "echo hi > /tmp/example"),
    )
    assert "valid atomic leaf task" in blocked_result.stdout

    run_cli(
        context,
        "confirm-atomic-task",
        "--task",
        task_id,
        "--deliverable",
        "Evidence hook task can run one bounded mutation.",
        "--done",
        "PreToolUse allows the bounded mutation.",
        "--verify",
        "Hook smoke passes.",
        "--boundary",
        "Only evidence-authorized preflight hook behavior.",
        "--blocker-policy",
        "Record OPEN-* for blockers.",
        "--note",
        "confirm hook task as atomic",
    )
    run_runtime(context, "hydrate-context")
    run_runtime(context, "confirm-task", "--task", task_id, "--note", "hook test focus confirmed after decomposition")

    permit_block = run_script(
        HOOK_DIR / "pre_tool_use_guard.py",
        hook_payload(context, "echo hi > /tmp/example"),
    )
    assert "requires a fresh valid REASON-* access" in permit_block.stdout

    chain = tmp_path / "edit-chain.json"
    chain.write_text(
        json.dumps(
            {
                "task": "evidence-authorized edit",
                "nodes": [
                    {"role": "fact", "ref": claim_id, "quote": "Bounded hook mutation is supported."},
                    {"role": "task", "ref": task_id, "quote": "Evidence hook task"},
                ],
                "edges": [{"from": claim_id, "to": task_id, "relation": "justifies-action"}],
            }
        ),
        encoding="utf-8",
    )
    permit = json.loads(
        run_cli(
            context,
            "validate-decision",
            "--mode",
            "edit",
            "--kind",
            "write",
            "--chain",
            str(chain),
            "--emit-permit",
            "--format",
            "json",
        ).stdout
    )
    assert permit["decision_valid"] is True
    assert permit["permit"]["mode"] == "edit"
    assert permit["permit"]["action_kind"] == "write"
    assert permit["reason_access"]["mode"] == "edit"
    assert permit["reason_access"]["action_kind"] == "write"
    assert permit["permit"]["signed_chain"]["node_count"] == 2
    assert permit["permit"]["signed_chain"]["nodes"][0]["ref"] == claim_id
    assert permit["permit"]["signed_chain"]["nodes"][0]["quote"] == "Bounded hook mutation is supported."
    run_cli(context, "reason-use-access", "--mode", "edit", "--kind", "write", "--used-by", "RUN-20260422-abcdef12")

    used_result = run_script(
        HOOK_DIR / "pre_tool_use_guard.py",
        hook_payload(context, "echo hi > /tmp/example"),
    )
    assert "used" in used_result.stdout or "no matching" in used_result.stdout

    run_cli(
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

    allow_result = run_script(
        HOOK_DIR / "pre_tool_use_guard.py",
        hook_payload(context, "echo hi > /tmp/example"),
    )
    assert allow_result.stdout.strip() == ""


def test_pre_tool_hook_blocks_direct_reason_ledger_writes(tmp_path: Path) -> None:
    context = bootstrap_context(tmp_path)
    run_runtime(context, "hydrate-context")

    blocked = hook_json(
        HOOK_DIR / "pre_tool_use_guard.py",
        hook_payload(context, "echo '{}' >> .codex_context/runtime/reasoning/reasons.jsonl"),
    )
    assert blocked["hookSpecificOutput"]["permissionDecision"] == "deny"
    assert "Direct TEP reasoning runtime writes are blocked" in blocked["hookSpecificOutput"]["permissionDecisionReason"]


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

    raw_claim_read = "sed -n '1,20p' .codex_context/records/claim/CLM-20260419-abcdef12.json"
    blocked_raw = hook_json(HOOK_DIR / "pre_tool_use_guard.py", hook_payload(context, raw_claim_read))
    assert blocked_raw["hookSpecificOutput"]["permissionDecision"] == "deny"
    assert "Raw TEP claim JSON reads are blocked" in blocked_raw["hookSpecificOutput"]["permissionDecisionReason"]

    allowed_raw = run_script(
        HOOK_DIR / "pre_tool_use_guard.py",
        hook_payload(context, f"TEP_RAW_RECORD_MODE=plugin-dev {raw_claim_read}"),
    )
    assert allowed_raw.stdout.strip() == ""
    telemetry = json.loads(run_cli(context, "telemetry-report", "--format", "json").stdout)
    assert telemetry["raw_event_count"] == 2
    assert telemetry["raw_path_count"] >= 1
    assert telemetry["by_access_kind"]["raw_claim_read_blocked"] == 1
    assert telemetry["by_access_kind"]["raw_claim_read"] == 1
    assert "CLM-20260419-abcdef12" in [item["record_ref"] for item in telemetry["top_records"]]

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
    assert record_ids(context, "run") == []

    run_cli(context, "configure-runtime", "--hook-run-capture", "all")
    run_script(HOOK_DIR / "post_tool_use_review.py", hook_payload(context, read_only_version_check))
    assert len(record_ids(context, "run")) == 1

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
