"""Agent identity, secret-hash ownership, and thread binding helpers."""

from __future__ import annotations

import hashlib
import hmac
import json
import os
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from pathlib import Path
from typing import Any

from .contracts import AgentIdentityRecord
from .ids import next_record_id, now_timestamp
from .io import parse_json_file, write_json_file
from .paths import record_path, runtime_dir


AGENT_PRIVATE_KEY_ENV = "TEP_AGENT_PRIVATE_KEY"
CODEX_THREAD_ID_ENV = "CODEX_THREAD_ID"
_AGENT_PRIVATE_KEY: ContextVar[str] = ContextVar("tep_agent_private_key", default="")
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
    "map_sessions",
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


def agent_key_fingerprint(secret: str) -> str:
    return _sha256_text(str(secret))


def _runtime_identity_dir(root: Path) -> Path:
    return runtime_dir(root) / "agent_identity"


def _agents_dir(root: Path) -> Path:
    return _runtime_identity_dir(root) / "agents"


def _thread_bindings_dir(root: Path) -> Path:
    return _runtime_identity_dir(root) / "thread_bindings"


def _key_bindings_dir(root: Path) -> Path:
    return _runtime_identity_dir(root) / "key_bindings"


def _binding_path(directory: Path, key: str) -> Path:
    return directory / f"{hashlib.sha256(key.encode('utf-8')).hexdigest()}.json"


def agent_secret_path(root: Path, private_key: str | None = None) -> Path:
    secret = require_agent_private_key(private_key)
    return _binding_path(_agents_dir(root), agent_key_fingerprint(secret))


def current_codex_thread_id() -> str:
    return str(os.environ.get(CODEX_THREAD_ID_ENV) or "").strip()


def _normalize_private_key(private_key: str | None) -> str:
    return str(private_key or "").strip()


def current_agent_private_key() -> str:
    return _normalize_private_key(_AGENT_PRIVATE_KEY.get() or os.environ.get(AGENT_PRIVATE_KEY_ENV))


class AgentIdentityRequiredError(RuntimeError):
    def __init__(self) -> None:
        super().__init__(
            "agent_identity_required: provide a per-agent private key with "
            "agent_private_key or TEP_AGENT_PRIVATE_KEY before WCTX/STEP/GRANT mutations"
        )


def require_agent_private_key(private_key: str | None = None) -> str:
    normalized = _normalize_private_key(private_key if private_key is not None else current_agent_private_key())
    if not normalized:
        raise AgentIdentityRequiredError()
    return normalized


@contextmanager
def agent_identity_scope(private_key: str | None) -> Iterator[None]:
    normalized = _normalize_private_key(private_key)
    if not normalized:
        yield
        return
    reset_token = _AGENT_PRIVATE_KEY.set(normalized)
    try:
        yield
    finally:
        _AGENT_PRIVATE_KEY.reset(reset_token)


def _read_binding(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return parse_json_file(path)
    except (OSError, json.JSONDecodeError, ValueError):
        return {}


def _write_binding(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    write_json_file(path, payload)
    try:
        path.chmod(0o600)
    except OSError:
        pass


def _thread_binding(root: Path) -> dict[str, Any]:
    thread_id = current_codex_thread_id()
    if not thread_id:
        return {}
    return _read_binding(_binding_path(_thread_bindings_dir(root), thread_id))


def _key_binding(root: Path, fingerprint: str) -> dict[str, Any]:
    if not fingerprint:
        return {}
    return _read_binding(_binding_path(_key_bindings_dir(root), fingerprint))


def _bind_thread(root: Path, *, agent_ref: str, fingerprint: str) -> None:
    thread_id = current_codex_thread_id()
    if not thread_id:
        return
    _write_binding(
        _binding_path(_thread_bindings_dir(root), thread_id),
        {
            "version": 1,
            "thread_id_sha256": hashlib.sha256(thread_id.encode("utf-8")).hexdigest(),
            "agent_identity_ref": agent_ref,
            "key_fingerprint": fingerprint,
            "bound_at": now_timestamp(),
        },
    )


def _bind_key(root: Path, *, agent_ref: str, fingerprint: str) -> None:
    _write_binding(
        _binding_path(_key_bindings_dir(root), fingerprint),
        {
            "version": 1,
            "agent_identity_ref": agent_ref,
            "key_fingerprint": fingerprint,
            "bound_at": now_timestamp(),
        },
    )


def _write_agent_binding(root: Path, *, agent_ref: str, fingerprint: str) -> None:
    _write_binding(
        _binding_path(_agents_dir(root), fingerprint),
        {
            "version": 1,
            "agent_identity_ref": agent_ref,
            "key_fingerprint": fingerprint,
            "bound_at": now_timestamp(),
        },
    )


def _persist_agent_record(root: Path, payload: dict[str, Any]) -> None:
    write_json_file(record_path(root, "agent_identity", str(payload.get("id", "")).strip()), payload)


def _public_record(record: dict) -> dict:
    return {key: value for key, value in record.items() if not str(key).startswith("_")}


def _local_agent_name() -> str:
    return str(os.environ.get("TEP_AGENT_NAME") or os.environ.get("USER") or "local-agent").strip() or "local-agent"


def _agent_record(agent_ref: str, *, fingerprint: str, created_at: str) -> dict:
    return AgentIdentityRecord(
        id=agent_ref,
        scope="agent.local",
        agent_name=_local_agent_name(),
        key_fingerprint=fingerprint,
        created_at=created_at,
        key_algorithm="hmac-sha256",
        key_scope="agent-owned",
        note="Public agent identity metadata only. Private key material remains agent-held.",
    ).to_payload()


def current_bound_agent_ref(root: Path) -> str:
    thread_binding = _thread_binding(root)
    if str(thread_binding.get("agent_identity_ref", "")).startswith("AGENT-"):
        return str(thread_binding.get("agent_identity_ref", "")).strip()
    private_key = current_agent_private_key()
    if not private_key:
        return ""
    binding = _key_binding(root, agent_key_fingerprint(private_key))
    return str(binding.get("agent_identity_ref", "")).strip() if str(binding.get("agent_identity_ref", "")).startswith("AGENT-") else ""


def ensure_local_agent_identity(root: Path, records: dict[str, dict], timestamp: str | None = None) -> tuple[dict, str]:
    private_key = require_agent_private_key()
    fingerprint = agent_key_fingerprint(private_key)
    created_at = timestamp or now_timestamp()

    thread_binding = _thread_binding(root)
    thread_agent_ref = str(thread_binding.get("agent_identity_ref", "")).strip()
    if thread_agent_ref:
        existing = records.get(thread_agent_ref)
        if not existing or existing.get("record_type") != "agent_identity":
            raise AgentIdentityRequiredError()
        if str(existing.get("key_fingerprint", "")).strip() != fingerprint:
            raise RuntimeError(f"agent identity isolation error: thread is already bound to {thread_agent_ref} with another key")
        _bind_thread(root, agent_ref=thread_agent_ref, fingerprint=fingerprint)
        _bind_key(root, agent_ref=thread_agent_ref, fingerprint=fingerprint)
        _write_agent_binding(root, agent_ref=thread_agent_ref, fingerprint=fingerprint)
        _persist_agent_record(root, _public_record(existing))
        return _public_record(existing), private_key

    key_binding = _key_binding(root, fingerprint)
    bound_agent_ref = str(key_binding.get("agent_identity_ref", "")).strip()
    if bound_agent_ref:
        existing = records.get(bound_agent_ref)
        if existing and existing.get("record_type") == "agent_identity":
            _bind_key(root, agent_ref=bound_agent_ref, fingerprint=fingerprint)
            _bind_thread(root, agent_ref=bound_agent_ref, fingerprint=fingerprint)
            _write_agent_binding(root, agent_ref=bound_agent_ref, fingerprint=fingerprint)
            _persist_agent_record(root, _public_record(existing))
            return _public_record(existing), private_key

    existing = next(
        (
            _public_record(record)
            for record in records.values()
            if record.get("record_type") == "agent_identity"
            and str(record.get("key_fingerprint", "")).strip() == fingerprint
        ),
        None,
    )
    if existing:
        agent_ref = str(existing["id"])
        _bind_key(root, agent_ref=agent_ref, fingerprint=fingerprint)
        _bind_thread(root, agent_ref=agent_ref, fingerprint=fingerprint)
        _write_agent_binding(root, agent_ref=agent_ref, fingerprint=fingerprint)
        _persist_agent_record(root, existing)
        return existing, private_key

    agent_ref = next_record_id(records, "AGENT-")
    created = _agent_record(agent_ref, fingerprint=fingerprint, created_at=created_at)
    _bind_key(root, agent_ref=agent_ref, fingerprint=fingerprint)
    _bind_thread(root, agent_ref=agent_ref, fingerprint=fingerprint)
    _write_agent_binding(root, agent_ref=agent_ref, fingerprint=fingerprint)
    _persist_agent_record(root, created)
    return created, private_key


def signed_wctx_payload_hash(payload: dict) -> str:
    signed_payload = {field: payload.get(field) for field in WCTX_SIGNED_FIELDS if field in payload}
    return _sha256_text(_canonical_json(signed_payload))


def _sign_hash(private_key: str, payload_hash: str) -> str:
    digest = hmac.new(private_key.encode("utf-8"), payload_hash.encode("utf-8"), hashlib.sha256).hexdigest()
    return "hmac-sha256:" + digest


def local_agent_owns_working_context(root: Path, payload: dict) -> bool:
    agent_ref = current_bound_agent_ref(root)
    return bool(agent_ref and agent_ref == str(payload.get("agent_identity_ref", "")).strip())


def verify_working_context_signature(root: Path, payload: dict, agent_record: dict) -> list[str]:
    signature = payload.get("owner_signature")
    if not isinstance(signature, dict):
        return []
    errors: list[str] = []
    expected_hash = signed_wctx_payload_hash(payload)
    actual_hash = str(signature.get("signed_payload_hash", "")).strip()
    if actual_hash != expected_hash:
        errors.append("WCTX owner_signature.signed_payload_hash mismatch")

    current_key = current_agent_private_key()
    record_fingerprint = str(agent_record.get("key_fingerprint", "")).strip()
    if current_key and agent_key_fingerprint(current_key) == record_fingerprint:
        expected_signature = _sign_hash(current_key, expected_hash)
        if not hmac.compare_digest(str(signature.get("signature", "")).strip(), expected_signature):
            errors.append("WCTX owner_signature.signature mismatch")
    return errors


def sign_working_context_payload(root: Path, records: dict[str, dict], payload: dict, timestamp: str | None = None) -> tuple[dict, dict]:
    agent_record, private_key = ensure_local_agent_identity(root, records, timestamp)
    signed = dict(payload)
    signed["contract_version"] = "0.4"
    signed["record_version"] = 1
    signed["agent_identity_ref"] = agent_record["id"]
    signed["agent_key_fingerprint"] = agent_record["key_fingerprint"]
    signed["ownership_mode"] = "owner-only"
    signed["handoff_policy"] = "fork-required"
    payload_hash = signed_wctx_payload_hash(signed)
    signed["owner_signature"] = {
        "algorithm": "hmac-sha256",
        "signed_payload_hash": payload_hash,
        "signature": _sign_hash(private_key, payload_hash),
        "signed_fields": list(WCTX_SIGNED_FIELDS),
    }
    return signed, agent_record
