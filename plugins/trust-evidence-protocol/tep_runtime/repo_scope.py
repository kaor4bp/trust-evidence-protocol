"""Repository-root scope helpers.

Code navigation paths are project-relative. The agent cwd and local `.tep`
anchor select focus, but they must not redefine a target repository root.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from .records import load_records
from .scopes import current_project_ref, current_workspace_ref


RepoRootSource = Literal["explicit", "project-root", "workspace-root", "cwd-fallback", "unresolved"]


def path_contains(root_value: str, target: Path) -> bool:
    if not root_value.strip():
        return False
    try:
        root_path = Path(root_value).expanduser().resolve()
    except OSError:
        return False
    return target == root_path or target.is_relative_to(root_path)


def record_root_refs(record: dict | None) -> list[str]:
    if not isinstance(record, dict):
        return []
    return [str(item).strip() for item in record.get("root_refs", []) if str(item).strip()]


def normalize_root_ref(value: str | Path, *, base: Path | None = None) -> str:
    path = Path(str(value)).expanduser()
    if not path.is_absolute():
        path = (base or Path.cwd()) / path
    return path.resolve().as_posix()


def normalize_root_refs(values: list[str], *, base: Path | None = None) -> list[str]:
    normalized: list[str] = []
    for value in values:
        stripped = str(value).strip()
        if not stripped:
            continue
        normalized.append(normalize_root_ref(stripped, base=base))
    return normalized


def root_refs_are_absolute(values: list[str]) -> bool:
    return all(Path(str(value)).expanduser().is_absolute() for value in values if str(value).strip())


def repo_scope_for_root(root: Path, repo_root: Path) -> tuple[str, str]:
    """Return workspace/project refs whose root_refs contain repo_root."""

    records, errors = load_records(root)
    if errors:
        return "", ""
    target = repo_root.expanduser().resolve()
    matching_projects = [
        record
        for record in records.values()
        if record.get("record_type") == "project"
        and str(record.get("status", "active")) == "active"
        and any(path_contains(root_ref, target) for root_ref in record_root_refs(record))
    ]
    current_project = current_project_ref(root)
    project_ref = ""
    if current_project and any(record.get("id") == current_project for record in matching_projects):
        project_ref = current_project
    elif matching_projects:
        project_ref = str(sorted(matching_projects, key=lambda item: str(item.get("id", "")))[0].get("id", ""))

    matching_workspaces = [
        record
        for record in records.values()
        if record.get("record_type") == "workspace"
        and str(record.get("status", "active")) == "active"
        and (
            any(path_contains(root_ref, target) for root_ref in record_root_refs(record))
            or (project_ref and project_ref in record.get("project_refs", []))
        )
    ]
    current_workspace = current_workspace_ref(root)
    workspace_ref = ""
    if current_workspace and any(record.get("id") == current_workspace for record in matching_workspaces):
        workspace_ref = current_workspace
    elif matching_workspaces:
        workspace_ref = str(sorted(matching_workspaces, key=lambda item: str(item.get("id", "")))[0].get("id", ""))
    return workspace_ref, project_ref


def focused_repo_root(root: Path) -> tuple[Path | None, RepoRootSource]:
    records, errors = load_records(root)
    if errors:
        return None, "unresolved"
    for record_ref, source in (
        (current_project_ref(root), "project-root"),
        (current_workspace_ref(root), "workspace-root"),
    ):
        record = records.get(record_ref)
        for root_ref in record_root_refs(record):
            return Path(root_ref).expanduser().resolve(), source
    return None, "unresolved"


def resolve_code_repo_root(root: Path, requested_root: str | Path | None, *, fallback_to_cwd: bool = True) -> tuple[Path | None, RepoRootSource]:
    if requested_root is not None and str(requested_root).strip():
        return Path(str(requested_root)).expanduser().resolve(), "explicit"
    focused, source = focused_repo_root(root)
    if focused is not None:
        return focused, source
    return (Path.cwd().resolve(), "cwd-fallback") if fallback_to_cwd else (None, "unresolved")


def code_entry_matches_repo_scope(entry: dict, workspace_ref: str, project_ref: str) -> bool:
    entry_project = str(entry.get("project_ref", "") or "").strip()
    entry_workspace = str(entry.get("workspace_ref", "") or "").strip()
    if project_ref and entry_project and entry_project != project_ref:
        return False
    if workspace_ref and entry_workspace and entry_workspace != workspace_ref:
        return False
    return True


def repo_scope_payload(root: Path, repo_root: Path | None, root_source: str | None = None) -> dict:
    workspace_ref, project_ref = repo_scope_for_root(root, repo_root) if repo_root is not None else ("", "")
    return {
        "repo_root": str(repo_root) if repo_root is not None else "",
        "repo_root_source": root_source or "",
        "workspace_ref": workspace_ref,
        "project_ref": project_ref,
        "paths_are_project_relative": True,
    }
