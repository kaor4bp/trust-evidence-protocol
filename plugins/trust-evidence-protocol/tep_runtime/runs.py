from __future__ import annotations


RUN_STATUSES = {"unknown", "completed", "failed"}


def run_status_from_exit_code(exit_code: int | None) -> str:
    if exit_code is None:
        return "unknown"
    return "completed" if exit_code == 0 else "failed"


def build_run_payload(
    *,
    record_id: str,
    scope: str,
    captured_at: str,
    tool: str,
    command: str,
    cwd: str,
    exit_code: int | None,
    stdout_quote: str,
    stderr_quote: str,
    action_kind: str | None,
    grant_ref: str | None,
    artifact_refs: list[str],
    workspace_refs: list[str],
    project_refs: list[str],
    task_refs: list[str],
    tags: list[str],
    note: str,
) -> dict:
    payload = {
        "id": record_id,
        "record_type": "run",
        "status": run_status_from_exit_code(exit_code),
        "scope": scope.strip(),
        "tool": tool.strip() or "bash",
        "command": command.strip(),
        "cwd": cwd.strip(),
        "captured_at": captured_at,
        "stdout_quote": stdout_quote.strip(),
        "stderr_quote": stderr_quote.strip(),
        "artifact_refs": artifact_refs,
        "workspace_refs": workspace_refs,
        "project_refs": project_refs,
        "task_refs": task_refs,
        "tags": tags,
        "note": note.strip(),
    }
    if exit_code is not None:
        payload["exit_code"] = exit_code
    if action_kind:
        payload["action_kind"] = action_kind.strip()
    if grant_ref:
        payload["grant_ref"] = grant_ref.strip()
    return payload
