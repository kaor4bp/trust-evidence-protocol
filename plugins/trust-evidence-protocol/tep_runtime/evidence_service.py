"""Evidence-capture service shared by CLI and MCP adapters."""

from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path
from typing import Any

from .claims import build_claim_payload
from .cli_common import (
    public_record_payload,
    refresh_generated_outputs,
    sanitize_artifact_name,
    validate_mutated_records,
)
from .files import build_file_payload, file_metadata, infer_file_kind
from .hydration import invalidate_hydration_state
from .ids import next_artifact_id, next_record_id, now_timestamp
from .io import write_json_file
from .notes import append_note
from .paths import record_path
from .records import load_code_index_entries, load_records
from .reports import write_validation_report
from .runs import build_run_payload
from .scopes import project_refs_for_write, task_refs_for_write, workspace_refs_for_write
from .sources import build_source_payload
from .validation import safe_list


EVIDENCE_KIND_DEFAULTS = {
    "file-line": ("code", "file"),
    "url": ("theory", "url"),
    "command-output": ("runtime", "command"),
    "user-confirmation": ("theory", "user_prompt"),
    "user-input": ("theory", "user_prompt"),
    "artifact": ("runtime", "artifact"),
}

MAX_AUTO_FILE_ARTIFACT_BYTES = 1024 * 1024


def record_evidence_service(
    root: Path,
    records: dict[str, dict],
    *,
    scope: str,
    kind: str,
    quote: str,
    path_value: str | None = None,
    line: int | None = None,
    end_line: int | None = None,
    url: str | None = None,
    command: str | None = None,
    cwd: str | None = None,
    exit_code: int | None = None,
    stdout_quote: str | None = None,
    stderr_quote: str | None = None,
    action_kind: str | None = None,
    input_refs: list[str] | None = None,
    artifact_refs: list[str] | None = None,
    origin_ref: str | None = None,
    critique_status: str = "accepted",
    confidence: str | None = None,
    project_refs: list[str] | None = None,
    task_refs: list[str] | None = None,
    tags: list[str] | None = None,
    red_flags: list[str] | None = None,
    note: str = "",
    claim_statement: str | None = None,
    claim_plane: str | None = None,
    claim_status: str = "supported",
    claim_kind: str | None = None,
    support_refs: list[str] | None = None,
    contradiction_refs: list[str] | None = None,
    derived_from: list[str] | None = None,
    recorded_at: str | None = None,
    base_cwd: Path | None = None,
) -> tuple[dict[str, Any] | None, str | None]:
    normalized_kind = str(kind or "").strip()
    if normalized_kind not in EVIDENCE_KIND_DEFAULTS:
        return None, f"unsupported evidence kind: {normalized_kind}"
    if not str(scope or "").strip():
        return None, "record_evidence requires scope"
    if not str(quote or "").strip():
        return None, "record_evidence requires quote"

    resolved_input_refs = list(dict.fromkeys(ref.strip() for ref in input_refs or [] if ref.strip()))
    for input_ref in resolved_input_refs:
        record = records.get(input_ref)
        if not record or record.get("record_type") != "input":
            return None, f"{input_ref} must reference an input record"

    resolved_artifact_refs = list(dict.fromkeys(ref.strip() for ref in artifact_refs or [] if ref.strip()))
    source_kind, origin_kind, resolved_origin_ref, origin_errors = resolve_record_evidence_origin(
        normalized_kind,
        path_value,
        line,
        end_line,
        url,
        command,
        resolved_input_refs,
        resolved_artifact_refs,
        origin_ref,
    )
    if origin_errors:
        return None, "\n".join(origin_errors)

    timestamp = now_timestamp()
    resolved_project_refs = project_refs_for_write(root, project_refs or [])
    resolved_task_refs = task_refs_for_write(root, task_refs or [])
    resolved_workspace_refs = workspace_refs_for_write(root, [])
    resolved_tags = [tag for tag in tags or [] if str(tag).strip()]
    resolved_red_flags = [flag for flag in red_flags or [] if str(flag).strip()]
    updates: dict[str, dict] = {}
    changed_ids: list[str] = []
    file_ref = ""
    run_ref = ""
    base_cwd = base_cwd or Path.cwd()

    if normalized_kind == "file-line" and path_value:
        file_payload, auto_artifacts = build_file_support_record(
            root,
            records,
            str(scope),
            path_value,
            timestamp,
            resolved_artifact_refs,
            resolved_project_refs,
            resolved_task_refs,
            resolved_workspace_refs,
            resolved_tags,
            "file evidence support",
            base_cwd=base_cwd,
        )
        file_ref = str(file_payload["id"])
        resolved_artifact_refs = sorted(set(auto_artifacts))
        updates[file_ref] = file_payload
        changed_ids.append(file_ref)

    if normalized_kind == "command-output" and command:
        run_payload = build_run_support_record(
            {**records, **updates},
            str(scope),
            command,
            timestamp,
            cwd or str(base_cwd),
            exit_code,
            stdout_quote if stdout_quote is not None else quote,
            stderr_quote or "",
            action_kind,
            None,
            resolved_artifact_refs,
            resolved_project_refs,
            resolved_task_refs,
            resolved_workspace_refs,
            resolved_tags,
            "command-output evidence support",
        )
        run_ref = str(run_payload["id"])
        updates[run_ref] = run_payload
        changed_ids.append(run_ref)

    source_id = next_record_id(records, "SRC-")
    source_payload = build_source_payload(
        record_id=source_id,
        source_kind=source_kind,
        scope=str(scope),
        critique_status=critique_status,
        origin_kind=origin_kind,
        origin_ref=resolved_origin_ref,
        quote=quote,
        artifact_refs=resolved_artifact_refs,
        confidence=confidence,
        independence_group=None,
        captured_at=None,
        captured_timestamp=timestamp,
        independence_timestamp=timestamp,
        project_refs=resolved_project_refs,
        task_refs=resolved_task_refs,
        tags=[*resolved_tags, "graph-v2", f"evidence-kind:{normalized_kind}"],
        red_flags=resolved_red_flags,
        note=note.strip() or f"record-evidence source from {normalized_kind}",
    )
    if resolved_input_refs:
        source_payload["input_refs"] = resolved_input_refs
    if resolved_workspace_refs:
        source_payload["workspace_refs"] = resolved_workspace_refs
    if file_ref:
        source_payload["file_refs"] = [file_ref]
        cix_refs = safe_list(updates[file_ref], "cix_refs")
        if cix_refs:
            source_payload["cix_refs"] = cix_refs
    if run_ref:
        source_payload["run_refs"] = [run_ref]

    updates[source_id] = source_payload
    changed_ids.append(source_id)
    claim_id = ""
    if claim_statement and claim_statement.strip():
        resolved_claim_plane = claim_plane or {
            "code": "code",
            "runtime": "runtime",
            "theory": "theory",
            "memory": "theory",
        }.get(source_kind, "theory")
        claim_id = next_record_id({**records, **updates}, "CLM-")
        claim_payload = build_claim_payload(
            record_id=claim_id,
            timestamp=timestamp,
            scope=str(scope),
            plane=resolved_claim_plane,
            status=claim_status,
            statement=claim_statement,
            source_refs=[source_id],
            support_refs=support_refs or [],
            contradiction_refs=contradiction_refs or [],
            derived_from=derived_from or [],
            claim_kind=claim_kind,
            confidence=confidence,
            comparison=None,
            logic=None,
            recorded_at=recorded_at,
            project_refs=resolved_project_refs,
            task_refs=resolved_task_refs,
            tags=[*resolved_tags, "graph-v2", f"evidence-kind:{normalized_kind}"],
            red_flags=resolved_red_flags,
            note=note.strip() or f"record-evidence claim from {normalized_kind}",
        )
        if resolved_input_refs:
            claim_payload["input_refs"] = resolved_input_refs
        if resolved_workspace_refs:
            claim_payload["workspace_refs"] = resolved_workspace_refs
        if file_ref:
            claim_payload["file_refs"] = [file_ref]
        if run_ref:
            claim_payload["run_refs"] = [run_ref]
        updates[claim_id] = claim_payload
        changed_ids.append(claim_id)

    derived_refs = [source_id]
    if claim_id:
        derived_refs.append(claim_id)
    for input_ref in resolved_input_refs:
        input_payload = public_record_payload(records[input_ref])
        existing = [str(ref).strip() for ref in input_payload.get("derived_record_refs", []) if str(ref).strip()]
        input_payload["derived_record_refs"] = sorted(set(existing + derived_refs))
        input_payload["note"] = append_note(
            str(input_payload.get("note", "")),
            f"record-evidence linked derived records: {', '.join(derived_refs)}",
        )
        updates[input_ref] = input_payload
        changed_ids.append(input_ref)

    merged_records, errors = validate_mutated_records(root, records, updates)
    if errors:
        return None, "\n".join(f"{error.path}: {error.message}" for error in errors)

    changed_ids = list(dict.fromkeys(changed_ids))
    for record_id in changed_ids:
        write_json_file(
            record_path(root, merged_records[record_id]["record_type"], record_id),
            public_record_payload(merged_records[record_id]),
        )
    write_validation_report(root, [])
    refresh_generated_outputs(root, merged_records)
    message = f"Recorded evidence {source_id}{f' and claim {claim_id}' if claim_id else ''}"
    invalidate_hydration_state(root, message)
    return {
        "record_evidence_is_proof": False,
        "source_ref": source_id,
        "claim_ref": claim_id,
        "file_ref": file_ref,
        "run_ref": run_ref,
        "input_refs": resolved_input_refs,
        "artifact_refs": resolved_artifact_refs,
        "changed_ids": changed_ids,
        "records": {
            record_id: public_record_payload(merged_records[record_id])
            for record_id in changed_ids
        },
        "message": message,
    }, None


def record_evidence_text(payload: dict[str, Any], root: Path) -> str:
    lines = [
        f"Recorded source {payload['source_ref']} at {record_path(root, 'source', payload['source_ref'])}",
    ]
    claim_ref = str(payload.get("claim_ref") or "").strip()
    if claim_ref:
        lines.append(f"Recorded claim {claim_ref} at {record_path(root, 'claim', claim_ref)}")
    input_refs = payload.get("input_refs", [])
    if input_refs:
        derived_refs = [payload["source_ref"]]
        if claim_ref:
            derived_refs.append(claim_ref)
        lines.append(
            f"Classified input(s) {', '.join(input_refs)} with derived record(s): {', '.join(derived_refs)}"
        )
    return "\n".join(lines)


def resolve_record_evidence_origin(
    kind: str,
    path_value: str | None,
    line: int | None,
    end_line: int | None,
    url: str | None,
    command: str | None,
    input_refs: list[str],
    artifact_refs: list[str],
    origin_ref: str | None,
) -> tuple[str, str, str, list[str]]:
    source_kind, origin_kind = EVIDENCE_KIND_DEFAULTS[kind]
    errors: list[str] = []
    if origin_ref and origin_ref.strip():
        return source_kind, origin_kind, origin_ref.strip(), errors

    if kind == "file-line":
        if not path_value or not path_value.strip():
            errors.append("record-evidence --kind file-line requires --path")
        if line is None:
            errors.append("record-evidence --kind file-line requires --line")
        if line is not None and line <= 0:
            errors.append("--line must be positive")
        if end_line is not None and end_line <= 0:
            errors.append("--end-line must be positive")
        if line is not None and end_line is not None and end_line < line:
            errors.append("--end-line must be greater than or equal to --line")
        if errors:
            return source_kind, origin_kind, "", errors
        if end_line and end_line != line:
            return source_kind, origin_kind, f"{path_value.strip()}:{line}-{end_line}", errors
        return source_kind, origin_kind, f"{path_value.strip()}:{line}", errors

    if kind == "url":
        if not url or not url.strip():
            errors.append("record-evidence --kind url requires --url")
            return source_kind, origin_kind, "", errors
        return source_kind, origin_kind, url.strip(), errors

    if kind == "command-output":
        if not command or not command.strip():
            errors.append("record-evidence --kind command-output requires --command")
            return source_kind, origin_kind, "", errors
        return source_kind, origin_kind, command.strip(), errors

    if kind in {"user-confirmation", "user-input"}:
        if input_refs:
            return source_kind, origin_kind, "inputs:" + ",".join(input_refs), errors
        return source_kind, origin_kind, kind, errors

    if kind == "artifact":
        if not artifact_refs:
            errors.append("record-evidence --kind artifact requires at least one --artifact-ref")
            return source_kind, origin_kind, "", errors
        return source_kind, origin_kind, artifact_refs[0], errors

    errors.append(f"unsupported evidence kind: {kind}")
    return source_kind, origin_kind, "", errors


def resolve_evidence_file_path(path_value: str | None, base_cwd: Path | None = None) -> Path | None:
    if not path_value or not path_value.strip():
        return None
    path = Path(path_value).expanduser()
    if not path.is_absolute():
        path = (base_cwd or Path.cwd()) / path
    return path.resolve()


def cix_refs_for_path(root: Path, resolved_path: Path | None) -> list[str]:
    if resolved_path is None:
        return []
    entries, _ = load_code_index_entries(root)
    records, _ = load_records(root)
    refs: list[str] = []
    for entry_id, entry in entries.items():
        target = entry.get("target", {})
        if not isinstance(target, dict) or target.get("kind") != "file":
            continue
        target_path = str(target.get("path", "")).strip()
        if not target_path:
            continue
        candidates = [Path(target_path)]
        project_ref = str(entry.get("project_ref", "")).strip()
        project = records.get(project_ref) if project_ref else None
        if project and isinstance(project.get("root_refs"), list):
            for root_ref in project.get("root_refs", []):
                root_path = Path(str(root_ref)).expanduser()
                candidates.append(root_path / target_path)
        for candidate in candidates:
            try:
                if candidate.expanduser().resolve() == resolved_path:
                    refs.append(entry_id)
                    break
            except OSError:
                continue
    return sorted(set(refs))


def copy_artifact_file(root: Path, path: Path) -> tuple[str, str]:
    target_root = root / "artifacts"
    target_root.mkdir(parents=True, exist_ok=True)
    artifact_id = next_artifact_id(root)
    suffix = sanitize_artifact_name(path.name)
    target = target_root / f"{artifact_id}__{suffix}"
    with tempfile.NamedTemporaryFile(
        "wb",
        dir=target_root,
        prefix=f".{target.name}.",
        suffix=".tmp",
        delete=False,
    ) as handle:
        tmp_path = Path(handle.name)
    shutil.copy2(path, tmp_path)
    os.replace(tmp_path, target)
    return artifact_id, f"artifacts/{target.name}"


def build_file_support_record(
    root: Path,
    records: dict[str, dict],
    scope: str,
    path_value: str,
    timestamp: str,
    artifact_refs: list[str],
    project_refs: list[str],
    task_refs: list[str],
    workspace_refs: list[str],
    tags: list[str],
    note: str,
    *,
    base_cwd: Path | None = None,
) -> tuple[dict, list[str]]:
    resolved_path = resolve_evidence_file_path(path_value, base_cwd=base_cwd)
    metadata = file_metadata(resolved_path)
    auto_artifacts = list(artifact_refs)
    if (
        resolved_path
        and metadata.get("exists")
        and int(metadata.get("size_bytes") or 0) <= MAX_AUTO_FILE_ARTIFACT_BYTES
    ):
        _, artifact_ref = copy_artifact_file(root, resolved_path)
        auto_artifacts.append(artifact_ref)
    cix_refs = cix_refs_for_path(root, resolved_path)
    payload = build_file_payload(
        record_id=next_record_id(records, "FILE-"),
        scope=scope,
        captured_at=timestamp,
        original_ref=path_value,
        resolved_path=str(resolved_path or ""),
        file_kind=infer_file_kind(resolved_path, auto_artifacts),
        metadata=metadata,
        artifact_refs=sorted(set(auto_artifacts)),
        cix_refs=cix_refs,
        workspace_refs=workspace_refs,
        project_refs=project_refs,
        task_refs=task_refs,
        tags=[*tags, "graph-v2"],
        note=note or "file support metadata",
    )
    return payload, auto_artifacts


def build_run_support_record(
    records: dict[str, dict],
    scope: str,
    command: str,
    timestamp: str,
    cwd: str,
    exit_code: int | None,
    stdout_quote: str,
    stderr_quote: str,
    action_kind: str | None,
    grant_ref: str | None,
    artifact_refs: list[str],
    project_refs: list[str],
    task_refs: list[str],
    workspace_refs: list[str],
    tags: list[str],
    note: str,
) -> dict:
    return build_run_payload(
        record_id=next_record_id(records, "RUN-"),
        scope=scope,
        captured_at=timestamp,
        tool="bash",
        command=command,
        cwd=cwd,
        exit_code=exit_code,
        stdout_quote=stdout_quote,
        stderr_quote=stderr_quote,
        action_kind=action_kind,
        grant_ref=grant_ref,
        artifact_refs=artifact_refs,
        workspace_refs=workspace_refs,
        project_refs=project_refs,
        task_refs=task_refs,
        tags=[*tags, "graph-v2"],
        note=note or "bash run support metadata",
    )
