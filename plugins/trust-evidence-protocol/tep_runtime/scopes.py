"""Project/task scope and applicability helpers."""

from __future__ import annotations

from pathlib import Path

from .settings import load_effective_settings, load_settings


def current_task_ref(root: Path) -> str:
    return str(load_settings(root).get("current_task_ref") or "").strip()


def current_project_ref(root: Path) -> str:
    return str(load_effective_settings(root).get("current_project_ref") or "").strip()


def current_workspace_ref(root: Path) -> str:
    return str(load_effective_settings(root).get("current_workspace_ref") or "").strip()


def workspace_refs_for_write(root: Path, explicit_refs: list[str]) -> list[str]:
    refs = {ref.strip() for ref in explicit_refs if ref.strip()}
    current = current_workspace_ref(root)
    if not refs and current:
        refs.add(current)
    return sorted(refs)


def project_refs_for_write(root: Path, explicit_refs: list[str]) -> list[str]:
    refs = {ref.strip() for ref in explicit_refs if ref.strip()}
    current = current_project_ref(root)
    if not refs and current:
        refs.add(current)
    return sorted(refs)


def task_refs_for_write(root: Path, explicit_refs: list[str]) -> list[str]:
    refs = {ref.strip() for ref in explicit_refs if ref.strip()}
    current = current_task_ref(root)
    if not refs and current:
        refs.add(current)
    return sorted(refs)


def record_belongs_to_project(data: dict, project_ref: str | None) -> bool:
    if not project_ref:
        return True
    if data.get("id") == project_ref:
        return True
    return project_ref in data.get("project_refs", [])


def record_belongs_to_task(data: dict, task_ref: str | None) -> bool:
    task_refs = [str(ref).strip() for ref in data.get("task_refs", []) if str(ref).strip()]
    if not task_refs:
        return True
    if data.get("id") == task_ref:
        return True
    return bool(task_ref and task_ref in task_refs)


def permission_applies(permission: dict, project_ref: str | None, task_ref: str | None) -> bool:
    applies_to = str(permission.get("applies_to", "")).strip()
    project_refs = permission.get("project_refs", [])
    task_refs = permission.get("task_refs", [])
    if not applies_to:
        if task_refs:
            applies_to = "task"
        elif project_refs:
            applies_to = "project"
        else:
            applies_to = "global"
    if applies_to == "global":
        return True
    if applies_to == "project":
        return bool(project_ref and project_ref in project_refs)
    if applies_to == "task":
        return bool(task_ref and task_ref in task_refs)
    return False


def active_restrictions_for(records: dict[str, dict], project_ref: str | None, task_ref: str | None) -> list[dict]:
    restrictions = []
    for restriction in records.values():
        if restriction.get("record_type") != "restriction":
            continue
        if str(restriction.get("status", "")).strip() != "active":
            continue
        applies_to = str(restriction.get("applies_to", "")).strip()
        if applies_to == "global":
            restrictions.append(restriction)
        elif applies_to == "project" and project_ref and project_ref in restriction.get("project_refs", []):
            restrictions.append(restriction)
        elif applies_to == "task" and task_ref and task_ref in restriction.get("task_refs", []):
            restrictions.append(restriction)
    return sorted(restrictions, key=lambda item: (str(item.get("severity", "")), str(item.get("id", ""))))


def guideline_applies(guideline: dict, project_ref: str | None, task_ref: str | None) -> bool:
    if str(guideline.get("status", "")).strip() != "active":
        return False
    applies_to = str(guideline.get("applies_to", "")).strip()
    if applies_to == "global":
        return True
    if applies_to == "project":
        return bool(project_ref and project_ref in guideline.get("project_refs", []))
    if applies_to == "task":
        return bool(task_ref and task_ref in guideline.get("task_refs", []))
    return False
