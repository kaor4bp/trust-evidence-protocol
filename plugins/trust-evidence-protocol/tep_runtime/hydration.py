"""Hydration state and context fingerprint helpers."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from .ids import now_timestamp
from .io import write_json_file
from .paths import hydration_state_path, hypotheses_index_path, settings_path


def load_hydration_state(root: Path) -> dict:
    path = hydration_state_path(root)
    if not path.exists():
        return {"status": "unhydrated"}
    with path.open(encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        return {"status": "unhydrated"}
    return data


def write_hydration_state(root: Path, payload: dict) -> None:
    write_json_file(hydration_state_path(root), payload)


def compute_context_fingerprint(root: Path) -> str:
    digest = hashlib.sha256()
    paths: list[Path] = []
    settings = settings_path(root)
    if settings.exists():
        paths.append(settings)
    records_root = root / "records"
    if records_root.exists():
        paths.extend(sorted(path for path in records_root.rglob("*.json") if path.is_file()))
    artifacts_root = root / "artifacts"
    if artifacts_root.exists():
        paths.extend(sorted(path for path in artifacts_root.rglob("*") if path.is_file() and not path.name.endswith(".tmp")))
    code_index_root = root / "code_index"
    if code_index_root.exists():
        paths.extend(sorted(path for path in code_index_root.rglob("*.json") if path.is_file() and not path.name.endswith(".tmp")))
    hypotheses = hypotheses_index_path(root)
    if hypotheses.exists():
        paths.append(hypotheses)

    for path in paths:
        digest.update(str(path.relative_to(root)).encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def invalidate_hydration_state(root: Path, reason: str) -> None:
    current = load_hydration_state(root)
    payload = {
        "status": "stale",
        "reason": reason,
        "observed_at": now_timestamp(),
        "current_fingerprint": compute_context_fingerprint(root),
    }
    if current.get("hydrated_at"):
        payload["hydrated_at"] = current.get("hydrated_at")
    if current.get("fingerprint"):
        payload["last_hydrated_fingerprint"] = current.get("fingerprint")
    if isinstance(current.get("confirmed_task"), dict):
        payload["confirmed_task"] = current.get("confirmed_task")
    write_hydration_state(root, payload)
