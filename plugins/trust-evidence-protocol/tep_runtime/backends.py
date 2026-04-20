"""Optional backend status reporting for TEP integrations."""

from __future__ import annotations

import importlib.metadata
import importlib.util
import shutil
from pathlib import Path

from .repo_scope import repo_scope_for_root
from .settings import load_settings
from .scopes import current_project_ref, current_task_ref, current_workspace_ref


BACKEND_IS_PROOF = False


def _python_package_status(package: str) -> tuple[bool, str]:
    if importlib.util.find_spec(package) is None:
        return False, "unknown"
    try:
        return True, importlib.metadata.version(package)
    except importlib.metadata.PackageNotFoundError:
        return True, "unknown"


def _command_status(commands: list[str]) -> tuple[bool, str]:
    for command in commands:
        path = shutil.which(command)
        if path:
            return True, path
    return False, "unknown"


def _repo_focus_refs(root: Path, repo_root: Path | None, fallback_workspace_ref: str, fallback_project_ref: str) -> tuple[str, str]:
    if repo_root is None:
        return fallback_workspace_ref, fallback_project_ref
    return repo_scope_for_root(root, repo_root)


def _disabled_status(group: str, backend: str, mode: str, setup_hint: str) -> dict:
    return {
        "id": backend,
        "group": group,
        "enabled": False,
        "selected": False,
        "available": False,
        "version": "unknown",
        "mode": mode,
        "freshness": "unknown",
        "warnings": [],
        "setup_hint": setup_hint,
        "backend_output_is_proof": BACKEND_IS_PROOF,
    }


def _available_builtin(group: str, selected: bool) -> dict:
    return {
        "id": "builtin",
        "group": group,
        "enabled": True,
        "selected": selected,
        "available": True,
        "version": "builtin",
        "mode": "builtin",
        "freshness": "fresh",
        "warnings": [],
        "setup_hint": "",
        "backend_output_is_proof": BACKEND_IS_PROOF,
    }


def _resolve_scoped_storage_dir(
    context_root: Path,
    *,
    scope: str,
    workspace_ref: str,
    project_ref: str,
    storage_root: str,
) -> Path | None:
    root_value = (storage_root or "<context>/backends/cocoindex").strip()
    if root_value.startswith("<context>"):
        base = context_root / root_value.removeprefix("<context>").lstrip("/")
    else:
        base = Path(root_value).expanduser()
        if not base.is_absolute():
            base = context_root / base
    if scope == "project":
        return base / "projects" / project_ref / ".cocoindex_code" if project_ref else None
    if scope == "workspace":
        return base / "workspaces" / workspace_ref / ".cocoindex_code" if workspace_ref else None
    return None


def _cocoindex_diagnostics(
    root: Path,
    *,
    settings: dict,
    repo_root: Path | None,
    scope: str | None,
    workspace_ref: str,
    project_ref: str,
) -> dict:
    default_scope = str(settings.get("default_scope") or "project")
    effective_scope = scope or default_scope
    if effective_scope not in {"project", "workspace"}:
        effective_scope = default_scope if default_scope in {"project", "workspace"} else "project"
    storage_root = str(settings.get("storage_root") or "<context>/backends/cocoindex")
    storage_dir = _resolve_scoped_storage_dir(
        root,
        scope=effective_scope,
        workspace_ref=workspace_ref,
        project_ref=project_ref,
        storage_root=storage_root,
    )
    repo = repo_root.expanduser().resolve() if repo_root else None
    repo_marker = repo / ".cocoindex_code" / "settings.yml" if repo else None
    storage_marker = storage_dir / "settings.yml" if storage_dir else None
    storage_index = storage_dir / "target_sqlite.db" if storage_dir else None
    storage_marker_exists = bool(storage_marker and storage_marker.is_file())
    storage_index_exists = bool(storage_index and storage_index.exists())
    repo_marker_exists = bool(repo_marker and repo_marker.is_file())
    runtime_search_ready = storage_index_exists and storage_marker_exists
    cli_search_ready = runtime_search_ready and repo_marker_exists
    return {
        "default_scope": default_scope,
        "effective_scope": effective_scope,
        "workspace_glance": bool(settings.get("workspace_glance")),
        "storage_root": storage_root,
        "storage": {
            "repo_root": str(repo) if repo else "",
            "workspace_ref": workspace_ref,
            "project_ref": project_ref,
            "scoped_db_dir": str(storage_dir) if storage_dir else "",
            "target_sqlite_db": str(storage_index) if storage_index else "",
            "settings_path": str(storage_marker) if storage_marker else "",
            "repo_marker_path": str(repo_marker) if repo_marker else "",
            "db_path_mapping": f"{repo}={storage_dir}" if repo and storage_dir else "",
            "index_exists": storage_index_exists,
            "storage_marker_exists": storage_marker_exists,
            "repo_marker_exists": repo_marker_exists,
            "cli_search_ready": cli_search_ready,
            "runtime_search_ready": runtime_search_ready,
            "search_ready": runtime_search_ready,
            "runtime_path": "repo-marker-cli" if cli_search_ready else ("direct-scoped-db" if runtime_search_ready else ""),
        },
    }


def backend_status_payload(root: Path, *, repo_root: Path | None = None, scope: str | None = None) -> dict:
    settings = load_settings(root)
    backend_settings = settings.get("backends", {})
    workspace_ref = current_workspace_ref(root)
    project_ref = current_project_ref(root)
    workspace_ref, project_ref = _repo_focus_refs(root, repo_root, workspace_ref, project_ref)
    task_ref = current_task_ref(root)
    payload = {
        "backend_status_is_proof": BACKEND_IS_PROOF,
        "context": str(root),
        "focus": {
            "workspace_ref": workspace_ref,
            "project_ref": project_ref,
            "task_ref": task_ref,
        },
        "groups": {},
        "backends": [],
    }

    fact = backend_settings.get("fact_validation", {}) if isinstance(backend_settings, dict) else {}
    fact_selected = str(fact.get("backend") or "builtin")
    fact_entries = [_available_builtin("fact_validation", selected=fact_selected == "builtin")]
    rdf_settings = fact.get("rdf_shacl", {}) if isinstance(fact, dict) else {}
    rdf_enabled = bool(rdf_settings.get("enabled"))
    rdf_mode = str(rdf_settings.get("mode") or "local")
    if rdf_enabled and rdf_mode == "fake":
        fact_entries.append(
            {
                "id": "rdf_shacl",
                "group": "fact_validation",
                "enabled": True,
                "selected": fact_selected == "rdf_shacl",
                "available": True,
                "version": "fake",
                "mode": "fake",
                "freshness": "fresh",
                "warnings": ["fake backend returns deterministic validation candidates only"],
                "setup_hint": "",
                "backend_output_is_proof": BACKEND_IS_PROOF,
            }
        )
    elif rdf_enabled:
        available, version = _python_package_status("pyshacl")
        fact_entries.append(
            {
                "id": "rdf_shacl",
                "group": "fact_validation",
                "enabled": True,
                "selected": fact_selected == "rdf_shacl",
                "available": available,
                "version": version,
                "mode": rdf_mode,
                "freshness": "unknown",
                "warnings": [] if available else ["pySHACL is not installed"],
                "setup_hint": "" if available else "Install optional dependency `pyshacl` or disable fact_validation.rdf_shacl.",
                "backend_output_is_proof": BACKEND_IS_PROOF,
            }
        )
    else:
        fact_entries.append(
            _disabled_status(
                "fact_validation",
                "rdf_shacl",
                rdf_mode,
                "Enable backends.fact_validation.rdf_shacl.enabled after installing pySHACL.",
            )
        )
    payload["groups"]["fact_validation"] = {"selected": fact_selected, "items": fact_entries}

    code = backend_settings.get("code_intelligence", {}) if isinstance(backend_settings, dict) else {}
    code_selected = str(code.get("backend") or "builtin")
    code_entries = [_available_builtin("code_intelligence", selected=code_selected == "builtin")]
    serena_settings = code.get("serena", {}) if isinstance(code, dict) else {}
    serena_enabled = bool(serena_settings.get("enabled"))
    serena_mode = str(serena_settings.get("mode") or "mcp")
    if serena_enabled:
        command_available, command_path = _command_status(["serena-mcp-server", "serena"])
        code_entries.append(
            {
                "id": "serena",
                "group": "code_intelligence",
                "enabled": True,
                "selected": code_selected == "serena",
                "available": command_available,
                "version": command_path,
                "mode": serena_mode,
                "freshness": "unknown",
                "warnings": [] if command_available else ["Serena command was not found on PATH"],
                "setup_hint": "" if command_available else "Install/configure Serena MCP before selecting code_intelligence.serena.",
                "backend_output_is_proof": BACKEND_IS_PROOF,
            }
        )
    else:
        code_entries.append(
            _disabled_status(
                "code_intelligence",
                "serena",
                serena_mode,
                "Enable backends.code_intelligence.serena.enabled after configuring Serena MCP.",
            )
        )
    coco_settings = code.get("cocoindex", {}) if isinstance(code, dict) else {}
    coco_enabled = bool(coco_settings.get("enabled"))
    coco_mode = str(coco_settings.get("mode") or "cli")
    coco_diagnostics = _cocoindex_diagnostics(
        root,
        settings=coco_settings if isinstance(coco_settings, dict) else {},
        repo_root=repo_root,
        scope=scope,
        workspace_ref=workspace_ref,
        project_ref=project_ref,
    )
    if coco_enabled:
        command_available, command_path = _command_status(["cocoindex-code", "ccc", "cocoindex"])
        code_entries.append(
            {
                "id": "cocoindex",
                "group": "code_intelligence",
                "enabled": True,
                "selected": code_selected == "cocoindex",
                "available": command_available,
                "version": command_path,
                "mode": coco_mode,
                "freshness": "present" if coco_diagnostics["storage"]["index_exists"] else "missing",
                "warnings": (
                    ([] if command_available else ["CocoIndex command was not found on PATH"])
                    + (
                        ["CocoIndex repo marker is absent; TEP code-search will use direct scoped DB runtime path."]
                        if coco_diagnostics["storage"]["runtime_search_ready"]
                        and not coco_diagnostics["storage"]["repo_marker_exists"]
                        else []
                    )
                ),
                "setup_hint": "" if command_available else "Install/configure CocoIndex before selecting code_intelligence.cocoindex.",
                "backend_output_is_proof": BACKEND_IS_PROOF,
                **coco_diagnostics,
            }
        )
    else:
        disabled = _disabled_status(
            "code_intelligence",
            "cocoindex",
            coco_mode,
            "Enable backends.code_intelligence.cocoindex.enabled after configuring CocoIndex.",
        )
        disabled.update(coco_diagnostics)
        code_entries.append(disabled)
    payload["groups"]["code_intelligence"] = {"selected": code_selected, "items": code_entries}

    derivation = backend_settings.get("derivation", {}) if isinstance(backend_settings, dict) else {}
    derivation_selected = str(derivation.get("backend") or "builtin")
    derivation_entries = [_available_builtin("derivation", selected=derivation_selected == "builtin")]
    datalog_settings = derivation.get("datalog", {}) if isinstance(derivation, dict) else {}
    datalog_enabled = bool(datalog_settings.get("enabled"))
    datalog_mode = str(datalog_settings.get("mode") or "fake")
    if datalog_enabled and datalog_mode == "fake":
        derivation_entries.append(
            {
                "id": "datalog",
                "group": "derivation",
                "enabled": True,
                "selected": derivation_selected == "datalog",
                "available": True,
                "version": "fake",
                "mode": "fake",
                "freshness": "fresh",
                "warnings": ["fake backend returns deterministic test candidates only"],
                "setup_hint": "",
                "backend_output_is_proof": BACKEND_IS_PROOF,
            }
        )
    elif datalog_enabled:
        command_available, command_path = _command_status(["souffle"])
        derivation_entries.append(
            {
                "id": "datalog",
                "group": "derivation",
                "enabled": True,
                "selected": derivation_selected == "datalog",
                "available": command_available,
                "version": command_path,
                "mode": datalog_mode,
                "freshness": "unknown",
                "warnings": [] if command_available else ["Souffle command was not found on PATH"],
                "setup_hint": "" if command_available else "Install Souffle or keep derivation.datalog.mode=fake.",
                "backend_output_is_proof": BACKEND_IS_PROOF,
            }
        )
    else:
        derivation_entries.append(
            _disabled_status(
                "derivation",
                "datalog",
                datalog_mode,
                "Enable backends.derivation.datalog.enabled after choosing fake or Souffle mode.",
            )
        )
    payload["groups"]["derivation"] = {"selected": derivation_selected, "items": derivation_entries}

    for group in payload["groups"].values():
        for item in group["items"]:
            item["will_be_used_by_default"] = bool(item.get("enabled") and item.get("available") and item.get("selected"))
        payload["backends"].extend(group["items"])
    return payload


def select_backend_status(payload: dict, backend: str) -> list[dict]:
    query = backend.strip()
    if not query:
        return []
    if query in payload.get("groups", {}):
        return list(payload["groups"][query].get("items", []))
    if "." in query:
        group, backend_id = query.split(".", 1)
        return [
            item
            for item in payload.get("backends", [])
            if item.get("group") == group and item.get("id") == backend_id
        ]
    return [item for item in payload.get("backends", []) if item.get("id") == query]


def backend_status_text_lines(payload: dict, *, selected: list[dict] | None = None) -> list[str]:
    lines = [
        "# TEP Backend Status",
        "",
        "Backend status is diagnostic/navigation data only. It is not proof.",
    ]
    focus = payload.get("focus", {})
    if focus:
        lines.append(
            "Focus: "
            f"workspace=`{focus.get('workspace_ref') or '<none>'}` "
            f"project=`{focus.get('project_ref') or '<none>'}` "
            f"task=`{focus.get('task_ref') or '<none>'}`"
        )
    groups: dict[str, dict] = payload.get("groups", {})
    if selected is not None:
        groups = {}
        for item in selected:
            groups.setdefault(str(item.get("group") or "unknown"), {"selected": "", "items": []})["items"].append(item)
    for group_name, group in groups.items():
        lines.append("")
        selected_name = group.get("selected") or "n/a"
        lines.append(f"## {group_name} selected=`{selected_name}`")
        for item in group.get("items", []):
            warnings = "; ".join(item.get("warnings", [])) or "none"
            setup_hint = item.get("setup_hint") or ""
            lines.append(
                f"- `{item.get('id')}` enabled=`{str(item.get('enabled')).lower()}` "
                f"selected=`{str(item.get('selected')).lower()}` available=`{str(item.get('available')).lower()}` "
                f"mode=`{item.get('mode')}` freshness=`{item.get('freshness')}` "
                f"default=`{str(item.get('will_be_used_by_default')).lower()}` warnings=`{warnings}`"
            )
            storage = item.get("storage") if isinstance(item.get("storage"), dict) else {}
            if storage:
                lines.append(
                    f"  scope: effective=`{item.get('effective_scope')}` default=`{item.get('default_scope')}` "
                    f"index_exists=`{str(storage.get('index_exists')).lower()}` "
                    f"repo_marker=`{str(storage.get('repo_marker_exists')).lower()}` "
                    f"runtime_path=`{storage.get('runtime_path') or '<none>'}` "
                    f"search_ready=`{str(storage.get('search_ready')).lower()}`"
                )
                if storage.get("scoped_db_dir"):
                    lines.append(f"  storage: {storage.get('scoped_db_dir')}")
                if storage.get("db_path_mapping"):
                    lines.append(f"  mapping: {storage.get('db_path_mapping')}")
            if setup_hint:
                lines.append(f"  setup: {setup_hint}")
    if selected is not None and not selected:
        lines.append("")
        lines.append("- no backend matched")
    return lines
