"""Local agent identity and WCTX owner-signature helpers."""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
from pathlib import Path
from typing import Any

from .contracts import AgentIdentityRecord
from .ids import next_record_id, now_timestamp
from .io import parse_json_file, write_json_file
from .paths import runtime_dir


LOCAL_AGENT_SECRET_VERSION = 1
WCTX_SIGNED_FIELDS = (
    "id",
    "record_type",
    "contract_version",
    "record_version",
    "scope",
    "title",
    "status",
    "context_kind",
    "agent_identity_ref",
    "agent_key_fingerprint",
    "ownership_mode",
    "handoff_policy",
    "pinned_refs",
    "focus_paths",
    "topic_terms",
    "topic_seed_refs",
    "assumptions",
    "concerns",
    "parent_context_ref",
    "supersedes_refs",
    "project_refs",
    "task_refs",
    "tags",
    "note",
    "created_at",
    "updated_at",
)


def _canonical_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha256_text(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def local_agent_secret_path(root: Path) -> Path:
    return runtime_dir(root) / "agent_identity" / "local_agent_key.json"


def agent_key_fingerprint(secret: str) -> str:
    return _sha256_text(secret)


def _public_record(record: dict) -> dict:
    return {key: value for key, value in record.items() if not str(key).startswith("_")}


def _local_agent_name() -> str:
    return str(os.environ.get("TEP_AGENT_NAME") or os.environ.get("USER") or "local-agent").strip() or "local-agent"


def _new_secret_payload(records: dict[str, dict], timestamp: str) -> dict[str, str | int]:
    secret = secrets.token_hex(32)
    return {
        "version": LOCAL_AGENT_SECRET_VERSION,
        "agent_identity_ref": next_record_id(records, "AGENT-"),
        "agent_name": _local_agent_name(),
        "key_algorithm": "hmac-sha256",
        "key_scope": "local-agent",
        "secret": secret,
        "key_fingerprint": agent_key_fingerprint(secret),
        "created_at": timestamp,
    }


def load_or_create_local_agent_secret(root: Path, records: dict[str, dict], timestamp: str | None = None) -> dict:
    path = local_agent_secret_path(root)
    if path.exists():
        try:
            payload = parse_json_file(path)
        except (OSError, json.JSONDecodeError, ValueError):
            payload = {}
        if (
            int(payload.get("version", 0) or 0) == LOCAL_AGENT_SECRET_VERSION
            and str(payload.get("agent_identity_ref", "")).startswith("AGENT-")
            and str(payload.get("secret", "")).strip()
        ):
            return payload

    payload = _new_secret_payload(records, timestamp or now_timestamp())
    write_json_file(path, payload)
    try:
        path.chmod(0o600)
    except OSError:
        pass
    return payload


def load_local_agent_secret(root: Path) -> dict:
    path = local_agent_secret_path(root)
    if not path.exists():
        return {}
    try:
        payload = parse_json_file(path)
    except (OSError, json.JSONDecodeError, ValueError):
        return {}
    if (
        int(payload.get("version", 0) or 0) != LOCAL_AGENT_SECRET_VERSION
        or not str(payload.get("agent_identity_ref", "")).startswith("AGENT-")
        or not str(payload.get("secret", "")).strip()
    ):
        return {}
    return payload


def local_agent_identity_record(secret_payload: dict) -> dict:
    timestamp = str(secret_payload.get("created_at") or now_timestamp())
    return AgentIdentityRecord(
        id=str(secret_payload["agent_identity_ref"]),
        scope="agent.local",
        agent_name=str(secret_payload.get("agent_name") or _local_agent_name()),
        key_fingerprint=str(secret_payload.get("key_fingerprint") or agent_key_fingerprint(str(secret_payload["secret"]))),
        created_at=timestamp,
        note="Public local-agent identity metadata only. Private key material is runtime-private.",
    ).to_payload()


def ensure_local_agent_identity(root: Path, records: dict[str, dict], timestamp: str | None = None) -> tuple[dict, str]:
    secret_payload = load_or_create_local_agent_secret(root, records, timestamp)
    agent_ref = str(secret_payload["agent_identity_ref"])
    existing = records.get(agent_ref)
    secret = str(secret_payload["secret"])
    fingerprint = str(secret_payload.get("key_fingerprint") or agent_key_fingerprint(secret))
    if existing and existing.get("record_type") == "agent_identity" and str(existing.get("key_fingerprint", "")) == fingerprint:
        return _public_record(existing), secret
    return local_agent_identity_record({**secret_payload, "key_fingerprint": fingerprint}), secret


def signed_wctx_payload_hash(payload: dict) -> str:
    signed_payload = {field: payload.get(field) for field in WCTX_SIGNED_FIELDS if field in payload}
    return _sha256_text(_canonical_json(signed_payload))


def local_agent_owns_working_context(root: Path, payload: dict) -> bool:
    secret_payload = load_local_agent_secret(root)
    if not secret_payload:
        return False
    secret = str(secret_payload.get("secret", ""))
    fingerprint = str(secret_payload.get("key_fingerprint") or agent_key_fingerprint(secret))
    return (
        str(secret_payload.get("agent_identity_ref", "")).strip()
        == str(payload.get("agent_identity_ref", "")).strip()
        and fingerprint == str(payload.get("agent_key_fingerprint", "")).strip()
    )


def verify_working_context_signature(root: Path, payload: dict) -> list[str]:
    signature = payload.get("owner_signature")
    if not isinstance(signature, dict):
        return []
    errors: list[str] = []
    expected_hash = signed_wctx_payload_hash(payload)
    actual_hash = str(signature.get("signed_payload_hash", "")).strip()
    if actual_hash.startswith("sha256:") and actual_hash != expected_hash:
        errors.append("WCTX owner_signature.signed_payload_hash mismatch")

    secret_payload = load_local_agent_secret(root)
    if not secret_payload:
        return errors
    if str(secret_payload.get("agent_identity_ref", "")).strip() != str(payload.get("agent_identity_ref", "")).strip():
        return errors

    secret = str(secret_payload.get("secret", ""))
    fingerprint = str(secret_payload.get("key_fingerprint") or agent_key_fingerprint(secret))
    if fingerprint != str(payload.get("agent_key_fingerprint", "")).strip():
        errors.append("WCTX local agent secret fingerprint mismatch")
        return errors

    expected_signature = "hmac-sha256:" + hmac.new(secret.encode("utf-8"), expected_hash.encode("utf-8"), hashlib.sha256).hexdigest()
    actual_signature = str(signature.get("signature", "")).strip()
    if actual_signature.startswith("hmac-sha256:") and not hmac.compare_digest(actual_signature, expected_signature):
        errors.append("WCTX owner_signature.signature mismatch")
    return errors


def sign_working_context_payload(root: Path, records: dict[str, dict], payload: dict, timestamp: str | None = None) -> tuple[dict, dict]:
    agent_record, secret = ensure_local_agent_identity(root, records, timestamp)
    signed = dict(payload)
    signed["contract_version"] = "0.4"
    signed["record_version"] = 1
    signed["agent_identity_ref"] = agent_record["id"]
    signed["agent_key_fingerprint"] = agent_record["key_fingerprint"]
    signed["ownership_mode"] = "owner-only"
    signed["handoff_policy"] = "fork-required"
    payload_hash = signed_wctx_payload_hash(signed)
    digest = hmac.new(secret.encode("utf-8"), payload_hash.encode("utf-8"), hashlib.sha256).hexdigest()
    signed["owner_signature"] = {
        "algorithm": "hmac-sha256",
        "signed_payload_hash": payload_hash,
        "signature": "hmac-sha256:" + digest,
        "signed_fields": list(WCTX_SIGNED_FIELDS),
    }
    return signed, agent_record
