from __future__ import annotations

import hashlib
from datetime import datetime
from pathlib import Path


FILE_KINDS = {"code", "document", "attachment", "artifact", "external", "unknown"}


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def infer_file_kind(path: Path | None, artifact_refs: list[str]) -> str:
    if artifact_refs:
        return "artifact"
    if path is None:
        return "external"
    suffix = path.suffix.lower()
    if suffix in {".py", ".js", ".jsx", ".ts", ".tsx", ".sh", ".bash", ".zsh", ".json", ".yaml", ".yml", ".toml"}:
        return "code"
    if suffix in {".md", ".txt", ".rst", ".csv", ".tsv", ".html", ".xml"}:
        return "document"
    return "unknown"


def file_metadata(path: Path | None) -> dict:
    if path is None or not path.exists() or not path.is_file():
        return {"exists": False}
    stat = path.stat()
    return {
        "exists": True,
        "sha256": sha256_path(path),
        "size_bytes": stat.st_size,
        "mtime": datetime.fromtimestamp(stat.st_mtime).astimezone().isoformat(timespec="seconds"),
    }


def build_file_payload(
    *,
    record_id: str,
    scope: str,
    captured_at: str,
    original_ref: str,
    resolved_path: str,
    file_kind: str,
    metadata: dict,
    artifact_refs: list[str],
    cix_refs: list[str],
    workspace_refs: list[str],
    project_refs: list[str],
    task_refs: list[str],
    tags: list[str],
    note: str,
) -> dict:
    payload = {
        "id": record_id,
        "record_type": "file",
        "file_kind": file_kind,
        "scope": scope.strip(),
        "captured_at": captured_at,
        "original_ref": original_ref.strip(),
        "resolved_path": resolved_path.strip(),
        "metadata": metadata,
        "artifact_refs": artifact_refs,
        "cix_refs": cix_refs,
        "workspace_refs": workspace_refs,
        "project_refs": project_refs,
        "task_refs": task_refs,
        "tags": tags,
        "note": note.strip(),
    }
    return payload
