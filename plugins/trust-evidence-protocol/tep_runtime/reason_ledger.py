"""Append-only reasoning ledger for protected action access."""

from __future__ import annotations

import hashlib
import hmac
import json
import secrets
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from .hydration import compute_context_fingerprint
from .io import write_json_file
from .paths import reasoning_runtime_dir, reasoning_seal_path, reasons_ledger_path
from .scopes import current_project_ref, current_task_ref, current_workspace_ref
from .settings import chain_permit_ttl_seconds
from .telemetry import append_access_event


REASON_ENTRY_VERSION = 1
REASON_SIGNED_CHAIN_NODE_LIMIT = 8
ZERO_LEDGER_HASH = "sha256:0"


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


def _concise(value: str, limit: int) -> str:
    normalized = " ".join(str(value or "").split())
    if len(normalized) <= limit:
        return normalized
    return normalized[: max(0, limit - 3)].rstrip() + "..."


def _canonical_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha256_text(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def chain_payload_hash(payload: dict[str, Any]) -> str:
    return hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()


def _entry_material(entry: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in entry.items()
        if key not in {"entry_hash", "ledger_hash", "seal"}
    }


def _entry_hash(entry: dict[str, Any]) -> str:
    return _sha256_text(_canonical_json(_entry_material(entry)))


def _ledger_hash(prev_ledger_hash: str, entry_hash: str, seal: str) -> str:
    return _sha256_text(f"{prev_ledger_hash}\n{entry_hash}\n{seal}")


def _seal_payload(secret: str, entry_hash: str) -> str:
    digest = hmac.new(secret.encode("utf-8"), entry_hash.encode("utf-8"), hashlib.sha256).hexdigest()
    return "hmac-sha256:" + digest


def ensure_reasoning_secret(root: Path) -> str:
    path = reasoning_seal_path(root)
    if path.exists():
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            payload = {}
        secret = str(payload.get("secret", "")).strip()
        if secret:
            return secret
    secret = secrets.token_hex(32)
    payload = {
        "version": 1,
        "created_at": _now().isoformat(timespec="seconds"),
        "secret": secret,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    write_json_file(path, payload)
    try:
        path.chmod(0o600)
    except OSError:
        pass
    return secret


def signed_chain_summary(chain_payload: dict[str, Any]) -> dict[str, Any]:
    nodes = chain_payload.get("nodes", [])
    edges = chain_payload.get("edges", [])
    node_list = nodes if isinstance(nodes, list) else []
    edge_list = edges if isinstance(edges, list) else []
    display_nodes: list[dict[str, str]] = []
    for node in node_list:
        if not isinstance(node, dict):
            continue
        role = str(node.get("role", "")).strip()
        ref = str(node.get("ref", "")).strip()
        quote = _concise(str(node.get("quote", "")), 220)
        if not (role or ref or quote):
            continue
        display_nodes.append({"role": role, "ref": ref, "quote": quote})
    return {
        "task": _concise(str(chain_payload.get("task", "")), 180),
        "node_count": len(node_list),
        "edge_count": len(edge_list),
        "nodes": display_nodes[:REASON_SIGNED_CHAIN_NODE_LIMIT],
        "truncated_node_count": max(0, len(display_nodes) - REASON_SIGNED_CHAIN_NODE_LIMIT),
    }


def read_reason_entries(root: Path) -> tuple[list[dict[str, Any]], list[str]]:
    path = reasons_ledger_path(root)
    if not path.exists():
        return [], []
    entries: list[dict[str, Any]] = []
    errors: list[str] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        return [], [f"{path}: {exc}"]
    for index, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError as exc:
            errors.append(f"{path}:{index}: invalid JSON: {exc}")
            continue
        if not isinstance(payload, dict):
            errors.append(f"{path}:{index}: entry must be an object")
            continue
        entries.append(payload)
    return entries, errors


def validate_reason_ledger(root: Path) -> dict[str, Any]:
    entries, errors = read_reason_entries(root)
    secret = ensure_reasoning_secret(root)
    previous = ZERO_LEDGER_HASH
    ids: set[str] = set()
    for index, entry in enumerate(entries, start=1):
        entry_id = str(entry.get("id", "")).strip()
        if not entry_id.startswith("REASON-"):
            errors.append(f"entry {index}: missing REASON-* id")
        elif entry_id in ids:
            errors.append(f"{entry_id}: duplicate id")
        ids.add(entry_id)
        if str(entry.get("prev_ledger_hash", "")).strip() != previous:
            errors.append(f"{entry_id or index}: prev_ledger_hash mismatch")
        expected_entry_hash = _entry_hash(entry)
        if str(entry.get("entry_hash", "")).strip() != expected_entry_hash:
            errors.append(f"{entry_id or index}: entry_hash mismatch; ledger appears tampered")
        expected_seal = _seal_payload(secret, expected_entry_hash)
        if str(entry.get("seal", "")).strip() != expected_seal:
            errors.append(f"{entry_id or index}: seal mismatch; ledger appears tampered")
        expected_ledger_hash = _ledger_hash(previous, expected_entry_hash, expected_seal)
        if str(entry.get("ledger_hash", "")).strip() != expected_ledger_hash:
            errors.append(f"{entry_id or index}: ledger_hash mismatch; ledger appears tampered")
        previous = str(entry.get("ledger_hash", "")).strip()
    return {
        "ok": not errors,
        "entries": entries,
        "errors": errors,
        "head_hash": previous,
    }


def _next_reason_id(entries: list[dict[str, Any]]) -> str:
    today = _now().strftime("%Y%m%d")
    existing = {str(entry.get("id", "")).strip() for entry in entries}
    for _ in range(32):
        candidate = f"REASON-{today}-{secrets.token_hex(4)}"
        if candidate not in existing:
            return candidate
    raise RuntimeError(f"could not allocate collision-free reason id for REASON-{today}")


def append_reason_entry(root: Path, payload: dict[str, Any]) -> tuple[dict[str, Any] | None, str | None]:
    validation = validate_reason_ledger(root)
    if not validation["ok"]:
        return None, "; ".join(validation["errors"])
    entries = validation["entries"]
    secret = ensure_reasoning_secret(root)
    entry = {
        "id": _next_reason_id(entries),
        "record_type": "reason",
        "version": REASON_ENTRY_VERSION,
        "created_at": _now().isoformat(timespec="seconds"),
        "prev_ledger_hash": validation["head_hash"],
        **payload,
    }
    entry_hash = _entry_hash(entry)
    seal = _seal_payload(secret, entry_hash)
    entry["entry_hash"] = entry_hash
    entry["seal"] = seal
    entry["ledger_hash"] = _ledger_hash(str(entry["prev_ledger_hash"]), entry_hash, seal)
    path = reasons_ledger_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(_canonical_json(entry) + "\n")
    return entry, None


def reason_by_id(entries: list[dict[str, Any]], reason_ref: str) -> dict[str, Any] | None:
    return next((entry for entry in entries if str(entry.get("id", "")).strip() == reason_ref), None)


def latest_reason_step(entries: list[dict[str, Any]], task_ref: str | None = None) -> dict[str, Any] | None:
    for entry in reversed(entries):
        if str(entry.get("entry_type", "")).strip() != "step":
            continue
        if task_ref and str(entry.get("task_ref", "")).strip() != task_ref:
            continue
        return entry
    return None


def create_reason_step(
    root: Path,
    *,
    chain_payload: dict[str, Any],
    decision_payload: dict[str, Any],
    intent: str,
    mode: str,
    action_kind: str | None,
    why: str,
    parent_refs: list[str] | None = None,
    branch: str = "main",
) -> tuple[dict[str, Any] | None, str | None]:
    task_ref = current_task_ref(root)
    if not task_ref:
        return None, "reason steps require an active TASK-*"
    validation = validate_reason_ledger(root)
    if not validation["ok"]:
        return None, "; ".join(validation["errors"])
    entries = validation["entries"]
    parents = [ref.strip() for ref in parent_refs or [] if ref.strip()]
    task_steps = [
        entry
        for entry in entries
        if str(entry.get("entry_type", "")).strip() == "step"
        and str(entry.get("task_ref", "")).strip() == task_ref
    ]
    if task_steps and not parents:
        latest = task_steps[-1]
        parents = [str(latest.get("id", "")).strip()]
    for parent in parents:
        parent_entry = reason_by_id(entries, parent)
        if not parent_entry:
            return None, f"missing parent reason {parent}"
        if str(parent_entry.get("task_ref", "")).strip() != task_ref:
            return None, f"parent reason {parent} belongs to another TASK-*"
    return append_reason_entry(
        root,
        {
            "entry_type": "step",
            "status": "reviewed" if decision_payload.get("decision_valid") else "draft",
            "workspace_ref": current_workspace_ref(root),
            "project_ref": current_project_ref(root),
            "task_ref": task_ref,
            "parent_refs": parents,
            "branch": branch.strip() or "main",
            "intent": intent.strip() or mode,
            "mode": mode,
            "action_kind": (action_kind or "").strip(),
            "why": why.strip(),
            "decision_valid": bool(decision_payload.get("decision_valid")),
            "valid_for": decision_payload.get("valid_for", []),
            "blockers": decision_payload.get("blockers", []),
            "hypothesis_refs": decision_payload.get("hypothesis_refs", []),
            "exploration_context_refs": decision_payload.get("exploration_context_refs", []),
            "chain_hash": chain_payload_hash(chain_payload),
            "signed_chain": signed_chain_summary(chain_payload),
            "chain_payload": chain_payload,
            "context_fingerprint": compute_context_fingerprint(root),
        },
    )


def grant_reason_access(
    root: Path,
    *,
    reason_ref: str,
    mode: str,
    action_kind: str | None,
    ttl_seconds: int | None,
) -> tuple[dict[str, Any] | None, str | None]:
    validation = validate_reason_ledger(root)
    if not validation["ok"]:
        return None, "; ".join(validation["errors"])
    entries = validation["entries"]
    reason = reason_by_id(entries, reason_ref)
    if not reason:
        return None, f"missing reason {reason_ref}"
    if str(reason.get("entry_type", "")).strip() != "step":
        return None, f"{reason_ref} is not a reason step"
    if not reason.get("decision_valid"):
        return None, f"{reason_ref} has not passed decision validation"
    task_ref = current_task_ref(root)
    if not task_ref or str(reason.get("task_ref", "")).strip() != task_ref:
        return None, f"{reason_ref} does not match current TASK-* {task_ref or 'none'}"
    normalized_kind = (action_kind or "").strip()
    if mode == "edit" and not normalized_kind:
        return None, "edit reason access requires action kind"
    reason_mode = str(reason.get("mode", "")).strip()
    reason_kind = str(reason.get("action_kind", "")).strip()
    if reason_mode and reason_mode != mode:
        return None, f"{reason_ref} mode mismatch: {reason_mode}"
    if normalized_kind and reason_kind and reason_kind not in {normalized_kind, "*"}:
        return None, f"{reason_ref} action kind mismatch: {reason_kind}"
    if mode not in reason.get("valid_for", []):
        return None, f"{reason_ref} is not valid for mode {mode}"
    issued = _now()
    safe_ttl = chain_permit_ttl_seconds(root, ttl_seconds)
    return append_reason_entry(
        root,
        {
            "entry_type": "access_granted",
            "status": "active",
            "reason_ref": reason_ref,
            "workspace_ref": current_workspace_ref(root),
            "project_ref": current_project_ref(root),
            "task_ref": task_ref,
            "mode": mode,
            "action_kind": normalized_kind,
            "chain_hash": str(reason.get("chain_hash", "")).strip(),
            "context_fingerprint": compute_context_fingerprint(root),
            "single_use": True,
            "issued_at": issued.isoformat(timespec="seconds"),
            "expires_at": (issued + timedelta(seconds=safe_ttl)).isoformat(timespec="seconds"),
        },
    )


def append_reason_access_event(
    root: Path,
    access_kind: str,
    *,
    access: dict[str, Any] | None = None,
    mode: str,
    action_kind: str | None,
    reason: str = "",
    channel: str = "cli",
    tool: str = "reason",
) -> None:
    payload = {
        "channel": channel,
        "tool": tool,
        "access_kind": access_kind,
        "permit_reason": "reason-ledger-gate",
        "mode": mode,
        "action_kind": (action_kind or "").strip(),
        "workspace_ref": current_workspace_ref(root),
        "project_ref": current_project_ref(root),
        "task_ref": current_task_ref(root),
        "access_is_proof": False,
    }
    if access:
        payload["reason_access_ref"] = str(access.get("id", "")).strip()
        payload["reason_ref"] = str(access.get("reason_ref", "")).strip()
    if reason:
        payload["failure_reason"] = reason
    try:
        append_access_event(root, payload)
    except OSError:
        return


def used_access_refs(entries: list[dict[str, Any]]) -> set[str]:
    return {
        str(entry.get("access_ref", "")).strip()
        for entry in entries
        if str(entry.get("entry_type", "")).strip() == "access_used"
    }


def validate_reason_access(
    root: Path,
    *,
    mode: str,
    action_kind: str | None,
    chain_hash_value: str | None = None,
    context_fingerprint: str | None = None,
    telemetry: dict[str, str] | None = None,
) -> dict[str, Any]:
    validation = validate_reason_ledger(root)
    if not validation["ok"]:
        reason = "; ".join(validation["errors"])
        if telemetry:
            append_reason_access_event(
                root,
                "reason_access_rejected",
                mode=mode,
                action_kind=action_kind,
                reason=reason,
                channel=telemetry.get("channel", "cli"),
                tool=telemetry.get("tool", "validate-reason-access"),
            )
        return {"ok": False, "access": None, "reason": reason, "checked_count": 0}
    entries = validation["entries"]
    normalized_kind = (action_kind or "").strip()
    now = _now()
    current_refs = {
        "workspace_ref": current_workspace_ref(root),
        "project_ref": current_project_ref(root),
        "task_ref": current_task_ref(root),
    }
    current_fingerprint = context_fingerprint or compute_context_fingerprint(root)
    used_refs = used_access_refs(entries)
    failures: list[str] = []
    candidates = [
        entry
        for entry in entries
        if str(entry.get("entry_type", "")).strip() == "access_granted"
    ]
    for access in reversed(candidates):
        access_id = str(access.get("id", "")).strip() or "unknown"
        if str(access.get("mode", "")).strip() != mode:
            failures.append(f"{access_id}: mode mismatch")
            continue
        access_kind = str(access.get("action_kind", "")).strip()
        if normalized_kind and access_kind not in {normalized_kind, "*"}:
            failures.append(f"{access_id}: action kind mismatch")
            continue
        if access_id in used_refs:
            failures.append(f"{access_id}: used")
            continue
        if chain_hash_value and str(access.get("chain_hash", "")).strip() != chain_hash_value:
            failures.append(f"{access_id}: chain hash mismatch")
            continue
        expires = _parse_timestamp(str(access.get("expires_at", "")))
        if expires is None or expires < now:
            failures.append(f"{access_id}: expired")
            continue
        if str(access.get("context_fingerprint", "")).strip() != current_fingerprint:
            failures.append(f"{access_id}: context fingerprint changed")
            continue
        mismatched_ref = next(
            (
                key
                for key, value in current_refs.items()
                if str(access.get(key, "")).strip() != value
            ),
            None,
        )
        if mismatched_ref:
            failures.append(f"{access_id}: {mismatched_ref} mismatch")
            continue
        if telemetry:
            append_reason_access_event(
                root,
                "reason_access_used",
                access=access,
                mode=mode,
                action_kind=normalized_kind,
                channel=telemetry.get("channel", "cli"),
                tool=telemetry.get("tool", "validate-reason-access"),
            )
        return {"ok": True, "access": access, "reason": "", "checked_count": len(candidates)}
    reason = "no reason access grants found" if not candidates else failures[0] if failures else "no matching reason access"
    if telemetry:
        access_kind = "reason_access_missing"
        if "expired" in reason:
            access_kind = "reason_access_expired"
        elif "used" in reason:
            access_kind = "reason_access_used_rejected"
        elif candidates:
            access_kind = "reason_access_rejected"
        append_reason_access_event(
            root,
            access_kind,
            mode=mode,
            action_kind=normalized_kind,
            reason=reason,
            channel=telemetry.get("channel", "cli"),
            tool=telemetry.get("tool", "validate-reason-access"),
        )
    return {"ok": False, "access": None, "reason": reason, "checked_count": len(candidates)}


def consume_reason_access(
    root: Path,
    *,
    mode: str,
    action_kind: str | None,
    used_by_ref: str,
) -> tuple[dict[str, Any] | None, str | None]:
    validation = validate_reason_access(root, mode=mode, action_kind=action_kind)
    if not validation.get("ok"):
        return None, str(validation.get("reason", "missing reason access"))
    access = validation["access"]
    return append_reason_entry(
        root,
        {
            "entry_type": "access_used",
            "status": "used",
            "access_ref": str(access.get("id", "")).strip(),
            "reason_ref": str(access.get("reason_ref", "")).strip(),
            "workspace_ref": current_workspace_ref(root),
            "project_ref": current_project_ref(root),
            "task_ref": current_task_ref(root),
            "mode": mode,
            "action_kind": (action_kind or "").strip(),
            "used_by_ref": used_by_ref.strip(),
            "used_at": _now().isoformat(timespec="seconds"),
        },
    )


def reason_access_text_lines(access: dict[str, Any]) -> list[str]:
    return [
        "## Reason Access",
        f"- access: `{access.get('id')}`",
        f"- reason: `{access.get('reason_ref')}`",
        f"- mode: `{access.get('mode')}`",
        f"- action_kind: `{access.get('action_kind') or 'none'}`",
        f"- expires_at: `{access.get('expires_at')}`",
        f"- single_use: `{str(bool(access.get('single_use'))).lower()}`",
    ]


def reason_current_text_lines(root: Path) -> tuple[list[str], int]:
    validation = validate_reason_ledger(root)
    if not validation["ok"]:
        return ["Reason ledger tampered or invalid:", *[f"- {error}" for error in validation["errors"]]], 1
    entries = validation["entries"]
    task_ref = current_task_ref(root)
    step = latest_reason_step(entries, task_ref)
    accesses = [
        entry
        for entry in entries
        if str(entry.get("entry_type", "")).strip() == "access_granted"
        and (not task_ref or str(entry.get("task_ref", "")).strip() == task_ref)
    ]
    used = used_access_refs(entries)
    lines = ["# Reason Ledger", f"- entries: `{len(entries)}`", f"- current_task: `{task_ref or 'none'}`"]
    if step:
        lines.extend(
            [
                f"- current_reason: `{step.get('id')}`",
                f"- intent: `{step.get('intent')}` mode=`{step.get('mode')}` kind=`{step.get('action_kind') or 'none'}`",
                f"- why: {step.get('why')}",
            ]
        )
    else:
        lines.append("- current_reason: `none`")
    for access in accesses[-5:]:
        status = "used" if str(access.get("id", "")).strip() in used else str(access.get("status", "active"))
        lines.append(
            f"- access `{access.get('id')}` reason=`{access.get('reason_ref')}` mode=`{access.get('mode')}` kind=`{access.get('action_kind') or 'none'}` status=`{status}`"
        )
    return lines, 0
