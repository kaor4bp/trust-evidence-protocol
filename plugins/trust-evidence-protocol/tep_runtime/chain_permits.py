"""Time-limited permits produced by validated decision chains."""

from __future__ import annotations

import hashlib
import json
import secrets
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from .hydration import compute_context_fingerprint
from .io import parse_json_file, write_json_file
from .paths import chain_permits_dir
from .scopes import current_project_ref, current_task_ref, current_workspace_ref


DEFAULT_CHAIN_PERMIT_TTL_SECONDS = 20 * 60


def _now() -> datetime:
    return datetime.now().astimezone()


def _parse_timestamp(value: str) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.astimezone()
    return parsed


def chain_hash(payload: dict[str, Any]) -> str:
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def next_chain_permit_id(root: Path) -> str:
    today = _now().strftime("%Y%m%d")
    existing = {path.stem for path in chain_permits_dir(root).glob("CHSIG-*.json")}
    for _ in range(32):
        candidate = f"CHSIG-{today}-{secrets.token_hex(4)}"
        if candidate not in existing:
            return candidate
    raise RuntimeError(f"could not allocate collision-free chain permit id for CHSIG-{today}")


def create_chain_permit(
    root: Path,
    chain_payload: dict[str, Any],
    decision_payload: dict[str, Any],
    *,
    mode: str,
    action_kind: str | None,
    ttl_seconds: int,
) -> tuple[dict[str, Any] | None, str | None]:
    if not decision_payload.get("decision_valid"):
        return None, "cannot emit chain permit for an invalid decision chain"
    normalized_kind = (action_kind or "").strip()
    if mode == "edit" and not normalized_kind:
        return None, "edit chain permits require --kind matching the planned action kind"

    issued = _now()
    safe_ttl = max(30, min(int(ttl_seconds), 24 * 60 * 60))
    permit = {
        "id": next_chain_permit_id(root),
        "kind": "chain_permit",
        "version": 1,
        "mode": mode,
        "action_kind": normalized_kind,
        "chain_hash": chain_hash(chain_payload),
        "valid_for": decision_payload.get("valid_for", []),
        "hypothesis_refs": decision_payload.get("hypothesis_refs", []),
        "exploration_context_refs": decision_payload.get("exploration_context_refs", []),
        "workspace_ref": current_workspace_ref(root),
        "project_ref": current_project_ref(root),
        "task_ref": current_task_ref(root),
        "context_fingerprint": compute_context_fingerprint(root),
        "issued_at": issued.isoformat(timespec="seconds"),
        "expires_at": (issued + timedelta(seconds=safe_ttl)).isoformat(timespec="seconds"),
    }
    write_json_file(chain_permits_dir(root) / f"{permit['id']}.json", permit)
    return permit, None


def load_chain_permits(root: Path) -> list[dict[str, Any]]:
    directory = chain_permits_dir(root)
    if not directory.exists():
        return []
    permits: list[dict[str, Any]] = []
    for path in sorted(directory.glob("CHSIG-*.json")):
        try:
            payload = parse_json_file(path)
        except (OSError, ValueError, json.JSONDecodeError):
            continue
        if payload.get("kind") == "chain_permit":
            payload["_path"] = str(path)
            permits.append(payload)
    return permits


def validate_chain_permit(
    root: Path,
    *,
    mode: str,
    action_kind: str | None,
    context_fingerprint: str | None = None,
) -> dict[str, Any]:
    normalized_kind = (action_kind or "").strip()
    current_refs = {
        "workspace_ref": current_workspace_ref(root),
        "project_ref": current_project_ref(root),
        "task_ref": current_task_ref(root),
    }
    current_fingerprint = context_fingerprint or compute_context_fingerprint(root)
    now = _now()
    failures: list[str] = []
    candidates = sorted(
        load_chain_permits(root),
        key=lambda item: str(item.get("issued_at", "")),
        reverse=True,
    )
    for permit in candidates:
        permit_id = str(permit.get("id", "")).strip() or "unknown"
        if str(permit.get("mode", "")).strip() != mode:
            failures.append(f"{permit_id}: mode mismatch")
            continue
        permit_kind = str(permit.get("action_kind", "")).strip()
        if normalized_kind and permit_kind not in {normalized_kind, "*"}:
            failures.append(f"{permit_id}: action kind mismatch")
            continue
        if mode not in permit.get("valid_for", []):
            failures.append(f"{permit_id}: permit is not valid for mode {mode}")
            continue
        expires = _parse_timestamp(str(permit.get("expires_at", "")))
        if expires is None or expires < now:
            failures.append(f"{permit_id}: expired")
            continue
        if str(permit.get("context_fingerprint", "")).strip() != current_fingerprint:
            failures.append(f"{permit_id}: context fingerprint changed")
            continue
        mismatched_ref = next(
            (
                key
                for key, value in current_refs.items()
                if str(permit.get(key, "")).strip() != value
            ),
            None,
        )
        if mismatched_ref:
            failures.append(f"{permit_id}: {mismatched_ref} mismatch")
            continue
        return {"ok": True, "permit": permit, "reason": ""}

    reason = "no chain permits found" if not candidates else failures[0] if failures else "no matching chain permit"
    return {
        "ok": False,
        "permit": None,
        "reason": reason,
        "checked_count": len(candidates),
    }


def chain_permit_text_lines(permit: dict[str, Any]) -> list[str]:
    return [
        "## Chain Permit",
        f"- permit: `{permit.get('id')}`",
        f"- mode: `{permit.get('mode')}`",
        f"- action_kind: `{permit.get('action_kind') or 'none'}`",
        f"- expires_at: `{permit.get('expires_at')}`",
    ]
