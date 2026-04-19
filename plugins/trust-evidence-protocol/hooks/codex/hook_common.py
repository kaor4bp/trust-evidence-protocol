#!/usr/bin/env python3
"""Shared helpers for repo-local Codex hook adapters."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path


PLUGIN_SOURCE_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = PLUGIN_SOURCE_ROOT.parents[1]
CACHE_PLUGIN_ROOT = (
    Path.home()
    / ".codex"
    / "plugins"
    / "cache"
    / "home-local-plugins"
    / "trust-evidence-protocol"
)


def _version_key(path: Path) -> tuple[int, ...]:
    try:
        return tuple(int(part) for part in path.name.split("."))
    except ValueError:
        return ()


def _plugin_root_candidates() -> list[Path]:
    candidates = [PLUGIN_SOURCE_ROOT, REPO_ROOT / "plugins" / "trust-evidence-protocol"]
    if CACHE_PLUGIN_ROOT.is_dir():
        versions = sorted(
            (path for path in CACHE_PLUGIN_ROOT.iterdir() if path.is_dir()),
            key=_version_key,
            reverse=True,
        )
        candidates.extend(versions)
    return candidates


def _locate_plugin_root() -> Path:
    candidates = _plugin_root_candidates()
    for candidate in candidates:
        runtime_gate = candidate / "scripts" / "runtime_gate.py"
        if runtime_gate.is_file():
            return candidate
    raise RuntimeError(
        "Could not locate trust-evidence-protocol plugin root from known paths: "
        + ", ".join(str(path) for path in candidates)
    )


PLUGIN_ROOT = _locate_plugin_root()
RUNTIME_GATE = PLUGIN_ROOT / "scripts" / "runtime_gate.py"
CONTEXT_CLI = PLUGIN_ROOT / "scripts" / "context_cli.py"
PLUGIN_SCRIPTS = PLUGIN_ROOT / "scripts"
if str(PLUGIN_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(PLUGIN_SCRIPTS))

from context_lib import (  # noqa: E402
    DEFAULT_HOOK_SETTINGS,
    append_access_event,
    build_next_step_payload,
    claim_refs_from_text,
    command_reads_raw_claims,
    load_effective_settings,
    load_hydration_state,
    load_records,
    load_settings,
    next_step_inline,
    resolve_context_root,
)

TEP_ICON = "🛡️"

GIT_MUTATING_SUBCOMMANDS = {
    "add": "write",
    "apply": "patch",
    "branch": "create",
    "checkout": "update",
    "cherry-pick": "update",
    "clean": "delete",
    "commit": "write",
    "merge": "update",
    "mv": "move",
    "rebase": "update",
    "reset": "delete",
    "restore": "update",
    "revert": "update",
    "rm": "delete",
    "stash": "write",
    "switch": "update",
    "tag": "create",
}

PATTERN_ACTIONS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\brm\s+-", re.IGNORECASE), "delete"),
    (re.compile(r"\bmv\s+", re.IGNORECASE), "move"),
    (re.compile(r"\bcp\s+", re.IGNORECASE), "create"),
    (re.compile(r"\bmkdir\s+", re.IGNORECASE), "create"),
    (re.compile(r"\btouch\s+", re.IGNORECASE), "create"),
    (re.compile(r"\binstall\s+", re.IGNORECASE), "create"),
    (re.compile(r"\bln\s+-s?\b", re.IGNORECASE), "create"),
    (re.compile(r"\bchmod\s+", re.IGNORECASE), "update"),
    (re.compile(r"\bchown\s+", re.IGNORECASE), "update"),
    (re.compile(r"\bsed\s+-i(?:[^\s]*)?\b", re.IGNORECASE), "edit"),
    (re.compile(r"\bperl\s+-pi(?:[^\s]*)?\b", re.IGNORECASE), "edit"),
    (re.compile(r"(^|[;&|]\s*)(?:sudo\s+)?patch(?:\s|$)", re.IGNORECASE), "patch"),
    (re.compile(r"\btee\b", re.IGNORECASE), "write"),
    (re.compile(r"\b(?:npm|pnpm|yarn)\s+(?:install|add|remove|upgrade)\b", re.IGNORECASE), "update"),
    (re.compile(r"\b(?:pip|pip3)\s+install\b", re.IGNORECASE), "update"),
    (re.compile(r"\buv\s+(?:add|remove|sync|pip\s+install)\b", re.IGNORECASE), "update"),
    (re.compile(r"\bcargo\s+(?:add|remove|install)\b", re.IGNORECASE), "update"),
    (re.compile(r"\bgo\s+get\b", re.IGNORECASE), "update"),
]

STDOUT_REDIRECTION_PATTERN = re.compile(r"(^|[\s;|&])(?:1)?>>?(?![&])")
COMBINED_REDIRECTION_PATTERN = re.compile(r"(^|[\s;|&])&>>?")
STDOUT_REDIRECT_TARGET_PATTERN = re.compile(r"(?:^|[\s;|&])(?:1)?>>?\s*(?![&])(?P<target>\"[^\"]+\"|'[^']+'|[^\s;|&]+)")
COMBINED_REDIRECT_TARGET_PATTERN = re.compile(r"(?:^|[\s;|&])&>>?\s*(?P<target>\"[^\"]+\"|'[^']+'|[^\s;|&]+)")
TEE_TARGET_PATTERN = re.compile(r"\btee(?:\s+-a)?\s+(?P<target>\"[^\"]+\"|'[^']+'|[^\s;|&]+)", re.IGNORECASE)
HEREDOC_PATTERN = re.compile(r"<<-?\s*(?P<delimiter>\"[^\"]+\"|'[^']+'|\\?[A-Za-z_][A-Za-z0-9_]*)")


def load_payload() -> dict:
    raw = sys.stdin.read().strip()
    if not raw:
        return {}
    return json.loads(raw)


def strip_heredoc_bodies(command: str) -> str:
    """Remove heredoc payload lines so policy only scans shell syntax."""
    lines = command.splitlines()
    if len(lines) <= 1:
        return command

    sanitized: list[str] = []
    pending_delimiters: list[str] = []
    for line in lines:
        if pending_delimiters:
            delimiter = pending_delimiters[0]
            if line.strip() == delimiter:
                pending_delimiters.pop(0)
            continue

        sanitized.append(line)
        for match in HEREDOC_PATTERN.finditer(line):
            delimiter = unquote_shell_token(match.group("delimiter").lstrip("\\"))
            if delimiter:
                pending_delimiters.append(delimiter)
    return "\n".join(sanitized)


def locate_context(start: str | None) -> Path | None:
    return resolve_context_root(start=start or REPO_ROOT, stop=REPO_ROOT.resolve(), require_exists=True)


def load_hook_settings(context_root: Path | None) -> dict:
    if context_root is None:
        return dict(DEFAULT_HOOK_SETTINGS)
    settings = load_effective_settings(context_root)
    hooks = settings.get("hooks")
    if isinstance(hooks, dict):
        return {**DEFAULT_HOOK_SETTINGS, **hooks}
    return dict(DEFAULT_HOOK_SETTINGS)


def hook_mode(context_root: Path | None, key: str) -> str:
    hooks = load_hook_settings(context_root)
    return str(hooks.get(key, DEFAULT_HOOK_SETTINGS.get(key, "off")))


def hook_verbosity(context_root: Path | None) -> str:
    hooks = load_hook_settings(context_root)
    return str(hooks.get("verbosity", "normal"))


def hooks_enabled(context_root: Path | None) -> bool:
    hooks = load_hook_settings(context_root)
    return bool(hooks.get("enabled", True))


def has_context_anchor(context_root: Path, cwd: str | Path | None) -> bool:
    settings = load_effective_settings(context_root, start=cwd)
    return bool(str(settings.get("anchor_path") or "").strip())


def should_preserve_anchored_hydration(context_root: Path, cwd: str | Path | None) -> bool:
    if has_context_anchor(context_root, cwd):
        return False
    state = load_hydration_state(context_root)
    return bool(str(state.get("anchor_path") or "").strip())


def active_workspace_records(context_root: Path) -> list[dict]:
    records, errors = load_records(context_root)
    if errors:
        return []
    return [
        record
        for record in records.values()
        if record.get("record_type") == "workspace" and str(record.get("status", "")).strip() == "active"
    ]


def should_defer_unanchored_hydration(context_root: Path, cwd: str | Path | None) -> bool:
    if has_context_anchor(context_root, cwd):
        return False
    if should_preserve_anchored_hydration(context_root, cwd):
        return False
    return len(active_workspace_records(context_root)) > 1


def anchored_hydration_preserved_message(context_root: Path) -> str:
    state = load_hydration_state(context_root)
    workspace = state.get("current_workspace") if isinstance(state, dict) else None
    project = state.get("current_project") if isinstance(state, dict) else None
    task = state.get("current_task") if isinstance(state, dict) else None
    lines = [
        "TEP kept the existing anchored hydration because the hook cwd has no `.tep` anchor.",
        "Run `hydrate-context` from the intended workdir if you are switching workspace/project focus.",
    ]
    if isinstance(workspace, dict) and workspace.get("id"):
        lines.append(f"Preserved workspace: {workspace.get('id')} | {workspace.get('workspace_key', '')}")
    if isinstance(project, dict) and project.get("id"):
        lines.append(f"Preserved project: {project.get('id')} | {project.get('project_key', '')}")
    if isinstance(task, dict) and task.get("id"):
        lines.append(f"Preserved task: {task.get('id')} | {task.get('scope', '')}")
    return "\n".join(lines)


def unanchored_hydration_deferred_message(context_root: Path) -> str:
    workspaces = active_workspace_records(context_root)
    lines = [
        "TEP did not hydrate automatically because the hook cwd has no `.tep` anchor and the context has multiple active workspaces.",
        "Run `hydrate-context` from a workdir with the intended `.tep` anchor, or create/validate a local `.tep` anchor before relying on workspace/project facts.",
    ]
    if workspaces:
        lines.append("Active workspaces:")
        for workspace in sorted(workspaces, key=lambda item: str(item.get("id", "")))[:8]:
            lines.append(f"- {workspace.get('id')} | {workspace.get('workspace_key', '')}")
    return "\n".join(lines)


def permission_applies(permission: dict, project_ref: str | None, task_ref: str | None) -> bool:
    applies_to = str(permission.get("applies_to", "")).strip()
    project_refs = [str(ref) for ref in permission.get("project_refs", [])]
    task_refs = [str(ref) for ref in permission.get("task_refs", [])]
    if not applies_to:
        applies_to = "task" if task_refs else "project" if project_refs else "global"
    if applies_to == "global":
        return True
    if applies_to == "project":
        return bool(project_ref and project_ref in project_refs)
    if applies_to == "task":
        return bool(task_ref and task_ref in task_refs)
    return False


def active_permission_context(context_root: Path, action_kind: str, *, limit: int = 5) -> str:
    settings = load_effective_settings(context_root)
    records, errors = load_records(context_root)
    project_ref = str(settings.get("current_project_ref") or "").strip() or None
    task_ref = str(settings.get("current_task_ref") or "").strip() or None
    active_permissions = [
        record
        for record in records.values()
        if record.get("record_type") == "permission" and permission_applies(record, project_ref, task_ref)
    ]
    action_matches = []
    other_permissions = []
    for permission in active_permissions:
        grants = [str(grant) for grant in permission.get("grants", [])]
        haystack = " ".join(grants).lower()
        bucket = action_matches if action_kind.lower() in haystack or "allowed_freedom" in haystack else other_permissions
        bucket.append(permission)
    selected = (action_matches + other_permissions)[:limit]
    lines = [
        f"{TEP_ICON} TEP preflight blocked Bash action kind `{action_kind}`.",
        f"Current allowed_freedom: `{settings.get('allowed_freedom', 'proof-only')}`.",
    ]
    if selected:
        lines.append("Relevant active permissions in current scope:")
        for permission in selected:
            grants = "; ".join(str(grant) for grant in permission.get("grants", [])[:3])
            lines.append(
                f"- `{permission.get('id')}` applies_to=`{permission.get('applies_to', 'global')}` "
                f"scope=`{permission.get('scope', '')}` grants=`{grants}`"
            )
    else:
        lines.append("No active scoped permissions were found for the current project/task.")
    if errors:
        lines.append(f"Permission context was partial because {len(errors)} record load issue(s) were found.")
    lines.append("If a permission should authorize this action, cite its `PRM-*` in the public Evidence Chain.")
    return "\n".join(lines)


def next_step_hint(context_root: Path, *, intent: str = "auto", task: str = "") -> str:
    records, errors = load_records(context_root)
    if errors:
        return "TEP route: review-context -> fix record load issues"
    payload = build_next_step_payload(records, context_root, intent=intent, task=task)
    return next_step_inline(payload)


def unquote_shell_token(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def is_under_path(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def is_artifact_output_target(target: str, context_root: Path | None) -> bool:
    if context_root is None:
        return False
    cleaned = unquote_shell_token(target)
    if not cleaned:
        return False
    if "$" in cleaned or "`" in cleaned or cleaned.startswith(("~", "-")):
        return False
    path = Path(cleaned)
    if not path.is_absolute():
        path = context_root.parent / path
    artifacts_root = context_root / "artifacts"
    return is_under_path(path, artifacts_root)


def is_artifact_write_command(command: str, context_root: Path | None) -> bool:
    normalized = strip_heredoc_bodies(command).strip()
    if not normalized:
        return False
    targets = [
        match.group("target")
        for pattern in (STDOUT_REDIRECT_TARGET_PATTERN, COMBINED_REDIRECT_TARGET_PATTERN, TEE_TARGET_PATTERN)
        for match in pattern.finditer(normalized)
    ]
    return bool(targets) and all(is_artifact_output_target(target, context_root) for target in targets)


def infer_action_kind(command: str, context_root: Path | None = None) -> str | None:
    normalized = strip_heredoc_bodies(command).strip()
    if not normalized:
        return None
    if is_artifact_write_command(normalized, context_root):
        return None

    match = re.search(r"\bgit\s+([A-Za-z-]+)\b", normalized)
    if match:
        subcommand = match.group(1).lower()
        if subcommand in GIT_MUTATING_SUBCOMMANDS:
            return GIT_MUTATING_SUBCOMMANDS[subcommand]

    for pattern, action in PATTERN_ACTIONS:
        if pattern.search(normalized):
            return action

    if STDOUT_REDIRECTION_PATTERN.search(normalized) or COMBINED_REDIRECTION_PATTERN.search(normalized):
        return "write"

    return None


def run_runtime_gate(*args: str, cwd: str | Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(RUNTIME_GATE), *args],
        capture_output=True,
        text=True,
        cwd=str(cwd or REPO_ROOT),
        check=False,
    )


def run_context_cli(*args: str, input_text: str | None = None, cwd: str | Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(CONTEXT_CLI), *args],
        input=input_text,
        capture_output=True,
        text=True,
        cwd=str(cwd or REPO_ROOT),
        check=False,
    )


def append_raw_claim_read_event(context_root: Path, command: str, *, cwd: str | Path | None = None) -> None:
    if not command_reads_raw_claims(command):
        return
    refs = claim_refs_from_text(command)
    raw_path_count = max(1, command.count("records/claim") + len(refs))
    try:
        append_access_event(
            context_root,
            {
                "channel": "hook",
                "tool": "bash",
                "access_kind": "raw_claim_read",
                "record_refs": refs,
                "raw_path_count": raw_path_count,
                "cwd": str(cwd or ""),
                "note": "Bash command referenced raw claim record storage",
                "access_is_proof": False,
            },
        )
    except OSError:
        return
