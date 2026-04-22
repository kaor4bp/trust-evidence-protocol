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
from .settings import DEFAULT_CHAIN_PERMIT_TTL_SECONDS, chain_permit_ttl_seconds
from .telemetry import append_access_event


SIGNED_CHAIN_NODE_LIMIT = 8


def _concise(value: str, limit: int) -> str:
    normalized = " ".join(str(value or "").split())
    if len(normalized) <= limit:
        return normalized
    return normalized[: max(0, limit - 3)].rstrip() + "..."


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
        display_nodes.append(
            {
                "role": role,
                "ref": ref,
                "quote": quote,
            }
        )
    return {
        "task": _concise(str(chain_payload.get("task", "")), 180),
        "node_count": len(node_list),
        "edge_count": len(edge_list),
        "nodes": display_nodes[:SIGNED_CHAIN_NODE_LIMIT],
        "truncated_node_count": max(0, len(display_nodes) - SIGNED_CHAIN_NODE_LIMIT),
    }


def signed_chain_task_refs(chain_payload: dict[str, Any]) -> list[str]:
    refs: list[str] = []
    nodes = chain_payload.get("nodes", [])
    if not isinstance(nodes, list):
        return refs
    for node in nodes:
        if not isinstance(node, dict) or str(node.get("role", "")).strip() != "task":
            continue
        ref = str(node.get("ref", "")).strip()
        if ref and ref not in refs:
            refs.append(ref)
    return refs


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
    ttl_seconds: int | None,
) -> tuple[dict[str, Any] | None, str | None]:
    if not decision_payload.get("decision_valid"):
        return None, "cannot emit chain permit for an invalid decision chain"
    normalized_kind = (action_kind or "").strip()
    if mode == "edit" and not normalized_kind:
        return None, "edit chain permits require --kind matching the planned action kind"
    task_ref = current_task_ref(root)
    if not task_ref:
        return None, "chain permits require an active TASK-*"
    chain_task_refs = signed_chain_task_refs(chain_payload)
    if chain_task_refs != [task_ref]:
        return None, f"chain permits require exactly one task node matching current TASK-* {task_ref}"

    issued = _now()
    safe_ttl = chain_permit_ttl_seconds(root, ttl_seconds)
    chain_hash_value = chain_hash(chain_payload)
    permit = {
        "id": next_chain_permit_id(root),
        "kind": "chain_permit",
        "version": 1,
        "mode": mode,
        "action_kind": normalized_kind,
        "chain_hash": chain_hash_value,
        "signed_chain": signed_chain_summary(chain_payload),
        "valid_for": decision_payload.get("valid_for", []),
        "hypothesis_refs": decision_payload.get("hypothesis_refs", []),
        "exploration_context_refs": decision_payload.get("exploration_context_refs", []),
        "workspace_ref": current_workspace_ref(root),
        "project_ref": current_project_ref(root),
        "task_ref": task_ref,
        "context_fingerprint": compute_context_fingerprint(root),
        "issued_at": issued.isoformat(timespec="seconds"),
        "expires_at": (issued + timedelta(seconds=safe_ttl)).isoformat(timespec="seconds"),
    }
    write_json_file(chain_permits_dir(root) / f"{permit['id']}.json", permit)
    append_chain_permit_event(root, "chain_permit_issued", permit=permit, mode=mode, action_kind=normalized_kind)
    return permit, None


def append_chain_permit_event(
    root: Path,
    access_kind: str,
    *,
    permit: dict[str, Any] | None = None,
    mode: str,
    action_kind: str | None,
    reason: str = "",
    channel: str = "cli",
    tool: str = "validate-decision",
) -> None:
    payload = {
        "channel": channel,
        "tool": tool,
        "access_kind": access_kind,
        "permit_reason": "chain-permit-gate",
        "mode": mode,
        "action_kind": (action_kind or "").strip(),
        "workspace_ref": current_workspace_ref(root),
        "project_ref": current_project_ref(root),
        "task_ref": current_task_ref(root),
        "access_is_proof": False,
    }
    if permit:
        payload["permit_ref"] = str(permit.get("id", "")).strip()
    if reason:
        payload["failure_reason"] = reason
    try:
        append_access_event(root, payload)
    except OSError:
        return


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
    chain_hash_value: str | None = None,
    context_fingerprint: str | None = None,
    telemetry: dict[str, str] | None = None,
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
        if chain_hash_value and str(permit.get("chain_hash", "")).strip() != chain_hash_value:
            failures.append(f"{permit_id}: chain hash mismatch")
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
        if telemetry:
            append_chain_permit_event(
                root,
                "chain_permit_used",
                permit=permit,
                mode=mode,
                action_kind=normalized_kind,
                channel=telemetry.get("channel", "cli"),
                tool=telemetry.get("tool", "validate-chain-permit"),
            )
        return {"ok": True, "permit": permit, "reason": ""}

    reason = "no chain permits found" if not candidates else failures[0] if failures else "no matching chain permit"
    if telemetry:
        if "expired" in reason:
            access_kind = "chain_permit_expired"
        elif "no chain permits" in reason or "no matching" in reason:
            access_kind = "chain_permit_missing"
        else:
            access_kind = "chain_permit_rejected"
        append_chain_permit_event(
            root,
            access_kind,
            mode=mode,
            action_kind=normalized_kind,
            reason=reason,
            channel=telemetry.get("channel", "cli"),
            tool=telemetry.get("tool", "validate-chain-permit"),
        )
    return {
        "ok": False,
        "permit": None,
        "reason": reason,
        "checked_count": len(candidates),
    }


def chain_permit_text_lines(permit: dict[str, Any]) -> list[str]:
    lines = [
        "## Chain Permit",
        f"- permit: `{permit.get('id')}`",
        f"- mode: `{permit.get('mode')}`",
        f"- action_kind: `{permit.get('action_kind') or 'none'}`",
        f"- expires_at: `{permit.get('expires_at')}`",
        f"- chain_hash: `{str(permit.get('chain_hash') or '')[:16]}`",
    ]
    signed_chain = permit.get("signed_chain")
    if isinstance(signed_chain, dict):
        lines.extend(
            [
                "",
                "## Signed Chain",
                f"- task: `{signed_chain.get('task') or 'none'}`",
                f"- nodes: `{signed_chain.get('node_count', 0)}` edges: `{signed_chain.get('edge_count', 0)}`",
            ]
        )
        for node in signed_chain.get("nodes", []):
            if not isinstance(node, dict):
                continue
            role = node.get("role") or "node"
            ref = node.get("ref") or "no-ref"
            quote = node.get("quote") or ""
            lines.append(f"- {role} `{ref}`: \"{quote}\"")
        if int(signed_chain.get("truncated_node_count") or 0) > 0:
            lines.append(f"- ... {signed_chain.get('truncated_node_count')} more node(s)")
    return lines
