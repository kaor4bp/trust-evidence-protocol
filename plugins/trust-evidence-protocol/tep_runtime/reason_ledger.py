"""Append-only reasoning ledger for protected action access."""

from __future__ import annotations

import hashlib
import json
import secrets
from collections import Counter, defaultdict, deque
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from .agent_identity import AgentIdentityRequiredError, current_agent_private_key, current_bound_agent_ref, ensure_local_agent_identity, local_agent_owns_working_context, require_agent_private_key
from .claim_relations import PROOF_RELATION_KINDS, NAVIGATION_RELATION_KINDS, relation_connects, relation_shape_for_claim
from .claims import claim_is_archived
from .errors import ValidationError
from .hydration import compute_context_fingerprint
from .io import write_json_file
from .paths import reasoning_runtime_dir, reasons_ledger_path
from .policy import is_mutating_action_kind
from .records import load_records
from .reasoning import PROOF_DECISION_MODES, UNCERTAIN_DECISION_MODES
from .scopes import current_project_ref, current_task_ref, current_workspace_ref
from .settings import chain_permit_ttl_seconds, load_effective_settings
from .validation import safe_list
from .telemetry import append_access_event


CLAIM_STEP_ENTRY_VERSION = 3
ZERO_LEDGER_HASH = "sha256:0"
LEDGER_ID_PREFIXES = {"STEP", "GRANT"}
GRANT_ENTRY_TYPES = {"grant"}
POW_ALGORITHM = "sha256-leading-zero-bits"


@dataclass(frozen=True)
class LedgerScope:
    agent_ref: str
    path: Path


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
        if key not in {"entry_hash", "ledger_hash", "seal"} and not str(key).startswith("_")
    }


def _entry_hash(entry: dict[str, Any]) -> str:
    return _sha256_text(_canonical_json(_entry_material(entry)))


def _pow_material(entry: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in entry.items()
        if key not in {"entry_hash", "ledger_hash", "seal", "pow"} and not str(key).startswith("_")
    }


def _pow_settings(root: Path) -> dict[str, Any]:
    settings = load_effective_settings(root).get("reasoning", {})
    pow_settings = settings.get("pow", {}) if isinstance(settings, dict) else {}
    if not isinstance(pow_settings, dict):
        pow_settings = {}
    return {
        "enabled": bool(pow_settings.get("enabled", True)),
        "difficulty_bits": int(pow_settings.get("difficulty_bits", 12) or 0),
        "max_attempts": int(pow_settings.get("max_attempts", 1_000_000) or 1_000_000),
    }


def _has_leading_zero_bits(hex_digest: str, bits: int) -> bool:
    if bits <= 0:
        return True
    full_nibbles = bits // 4
    remainder = bits % 4
    if len(hex_digest) < full_nibbles + (1 if remainder else 0):
        return False
    if full_nibbles and hex_digest[:full_nibbles] != "0" * full_nibbles:
        return False
    if not remainder:
        return True
    nibble = int(hex_digest[full_nibbles], 16)
    return nibble >> (4 - remainder) == 0


def _pow_digest(material: dict[str, Any], nonce: str) -> str:
    return hashlib.sha256(f"{_canonical_json(material)}\n{nonce}".encode("utf-8")).hexdigest()


def _mine_pow(root: Path, entry: dict[str, Any]) -> dict[str, Any]:
    settings = _pow_settings(root)
    difficulty = max(0, int(settings["difficulty_bits"]))
    if not settings["enabled"] or difficulty <= 0:
        return {
            "algorithm": POW_ALGORITHM,
            "difficulty_bits": 0,
            "nonce": "",
            "digest": "",
        }
    max_attempts = max(1, int(settings["max_attempts"]))
    material = _pow_material(entry)
    seed = secrets.token_hex(8)
    for attempt in range(max_attempts):
        nonce = f"{seed}:{attempt}"
        digest = _pow_digest(material, nonce)
        if _has_leading_zero_bits(digest, difficulty):
            return {
                "algorithm": POW_ALGORITHM,
                "difficulty_bits": difficulty,
                "nonce": nonce,
                "digest": digest,
            }
    raise RuntimeError(f"could not mine reason ledger PoW at difficulty_bits={difficulty}")


def _validate_pow(entry: dict[str, Any]) -> str | None:
    pow_payload = entry.get("pow")
    if pow_payload is None and int(entry.get("version", 1) or 1) < 2:
        return None
    if not isinstance(pow_payload, dict):
        return "missing pow"
    algorithm = str(pow_payload.get("algorithm", "")).strip()
    if algorithm != POW_ALGORITHM:
        return "unsupported pow algorithm"
    difficulty = int(pow_payload.get("difficulty_bits", 0) or 0)
    nonce = str(pow_payload.get("nonce", ""))
    digest = str(pow_payload.get("digest", "")).strip()
    if difficulty <= 0:
        return None
    expected = _pow_digest(_pow_material(entry), nonce)
    if digest != expected:
        return "pow digest mismatch"
    if not _has_leading_zero_bits(digest, difficulty):
        return "pow difficulty mismatch"
    return None


def _ledger_hash(prev_ledger_hash: str, entry_hash: str, seal: str) -> str:
    return _sha256_text(f"{prev_ledger_hash}\n{entry_hash}\n{seal}")


def command_hash(command: str) -> str:
    return hashlib.sha256(str(command or "").encode("utf-8")).hexdigest()


def normalize_cwd(cwd: str | Path | None) -> str:
    value = str(cwd or "").strip()
    if not value:
        return ""
    try:
        return str(Path(value).expanduser().resolve())
    except OSError:
        return value


def _current_agent_metadata(root: Path, *, create: bool) -> dict[str, str]:
    if create:
        records, _ = load_records(root)
        agent_record, private_key = ensure_local_agent_identity(root, records, _now().isoformat(timespec="seconds"))
        return {
            "agent_identity_ref": str(agent_record.get("id", "")).strip(),
            "agent_key_fingerprint": str(agent_record.get("key_fingerprint", "")).strip(),
            "agent_private_key": require_agent_private_key(private_key),
        }
    agent_ref = current_bound_agent_ref(root)
    if not agent_ref:
        return {}
    records, _ = load_records(root)
    agent_record = records.get(agent_ref, {})
    if agent_record.get("record_type") != "agent_identity":
        return {}
    return {
        "agent_identity_ref": agent_ref,
        "agent_key_fingerprint": str(agent_record.get("key_fingerprint", "")).strip(),
    }


def current_reasoning_agent_ref(root: Path, *, create: bool = False) -> str:
    return str(_current_agent_metadata(root, create=create).get("agent_identity_ref", "")).strip()


def current_reasons_ledger_path(root: Path, *, create_agent: bool = False) -> Path | None:
    agent_ref = current_reasoning_agent_ref(root, create=create_agent)
    if not agent_ref:
        return None
    return reasons_ledger_path(root, agent_ref)


def _seal_payload(private_key: str, entry_hash: str) -> str:
    from .agent_identity import _sign_hash  # local import to avoid broad API export

    return _sign_hash(private_key, entry_hash)


def _active_wctx_ref_for_task(root: Path, records: dict[str, dict], task_ref: str) -> str:
    project_ref = current_project_ref(root)
    candidates: list[dict[str, Any]] = []
    task = records.get(task_ref) if task_ref else None
    task_wctx_refs = safe_list(task, "working_context_refs") if isinstance(task, dict) else []
    for ref in task_wctx_refs:
        context = records.get(ref)
        if isinstance(context, dict):
            candidates.append(context)
    for record in records.values():
        if record.get("record_type") == "working_context":
            candidates.append(record)
    seen: set[str] = set()
    usable: list[dict[str, Any]] = []
    for context in candidates:
        context_id = str(context.get("id", "")).strip()
        if not context_id or context_id in seen:
            continue
        seen.add(context_id)
        if str(context.get("status", "")).strip() != "active":
            continue
        if project_ref and safe_list(context, "project_refs") and project_ref not in safe_list(context, "project_refs"):
            continue
        if task_ref and safe_list(context, "task_refs") and task_ref not in safe_list(context, "task_refs"):
            continue
        if not local_agent_owns_working_context(root, context):
            continue
        usable.append(context)
    if not usable:
        return ""
    return str(sorted(usable, key=lambda item: str(item.get("updated_at", "")), reverse=True)[0].get("id", "")).strip()


def _claim_is_tentative(record: dict[str, Any] | None) -> bool:
    return bool(record and str(record.get("status", "")).strip() == "tentative")


def _claim_is_decisive(record: dict[str, Any] | None) -> bool:
    return bool(
        record
        and record.get("record_type") == "claim"
        and str(record.get("status", "")).strip() in {"supported", "corroborated"}
        and not claim_is_archived(record)
    )


def validate_claim_step_transition(
    records: dict[str, dict],
    *,
    claim_ref: str,
    prev_claim_ref: str,
    relation_claim_ref: str,
    mode: str,
) -> dict[str, Any]:
    blockers: list[str] = []
    hypothesis_refs: list[str] = []
    claim = records.get(claim_ref)
    previous_claim = records.get(prev_claim_ref) if prev_claim_ref else None
    relation_claim = records.get(relation_claim_ref) if relation_claim_ref else None

    if not claim or claim.get("record_type") != "claim":
        blockers.append(f"claim_ref must reference CLM-*: {claim_ref or 'none'}")
    elif claim_is_archived(claim):
        blockers.append(f"claim_ref is archived/fallback: {claim_ref}")
    if previous_claim and previous_claim.get("record_type") != "claim":
        blockers.append(f"prev_claim_ref must reference CLM-*: {prev_claim_ref}")
    if previous_claim and claim_is_archived(previous_claim):
        blockers.append(f"prev_claim_ref is archived/fallback: {prev_claim_ref}")

    relation_shape = None
    relation_kind = ""
    if prev_claim_ref:
        if not relation_claim or relation_claim.get("record_type") != "claim":
            blockers.append(f"relation_claim_ref must reference relation CLM-*: {relation_claim_ref or 'none'}")
        else:
            relation_shape = relation_shape_for_claim(relation_claim)
            if relation_shape is None:
                blockers.append(f"relation_claim_ref is not a valid relation CLM-*: {relation_claim_ref}")
            else:
                relation_kind = relation_shape.kind
                if not relation_connects(relation_shape, prev_claim_ref, claim_ref):
                    blockers.append(f"relation_claim_ref {relation_claim_ref} does not connect {prev_claim_ref} -> {claim_ref}")
    elif relation_claim_ref:
        blockers.append("relation_claim_ref requires prev_claim_ref")

    status_records = [
        (prev_claim_ref, previous_claim),
        (relation_claim_ref, relation_claim),
        (claim_ref, claim),
    ]
    for ref, record in status_records:
        if ref and _claim_is_tentative(record):
            hypothesis_refs.append(ref)

    normalized_mode = mode if mode else "planning"
    if normalized_mode in PROOF_DECISION_MODES:
        for ref, record in status_records:
            if ref and not _claim_is_decisive(record):
                blockers.append(f"{ref} is not supported/corroborated for mode={normalized_mode}")
        if relation_kind in NAVIGATION_RELATION_KINDS:
            blockers.append(f"relation kind {relation_kind} is navigation-only and cannot authorize mode={normalized_mode}")
        if relation_kind and relation_kind not in PROOF_RELATION_KINDS:
            blockers.append(f"relation kind {relation_kind} is not proof-capable")
        if relation_shape and (len(relation_shape.subject_refs) != 1 or len(relation_shape.object_refs) != 1):
            blockers.append("proof/action modes require one-to-one relation CLM edges")
    elif normalized_mode in UNCERTAIN_DECISION_MODES:
        if len(hypothesis_refs) > 1:
            blockers.append("planning/debugging/curiosity claim steps allow at most one tentative hop")
        if _claim_is_tentative(previous_claim) and _claim_is_tentative(relation_claim):
            blockers.append("claim step cannot place two tentative hypotheses consecutively")
        if _claim_is_tentative(relation_claim) and _claim_is_tentative(claim):
            blockers.append("claim step cannot place two tentative hypotheses consecutively")
    valid = not blockers
    return {
        "valid": valid,
        "decision_chain_valid": valid,
        "justification_valid": valid,
        "valid_for": [normalized_mode] if valid else [],
        "blockers": blockers,
        "hypothesis_refs": sorted(set(hypothesis_refs)),
        "relation_kind": relation_kind,
    }


def _claim_step_lineage(
    entries: list[dict[str, Any]],
    *,
    prev_step_ref: str,
    task_ref: str,
) -> tuple[list[dict[str, Any]], list[str]]:
    by_id = {str(entry.get("id", "")).strip(): entry for entry in entries if str(entry.get("id", "")).strip()}
    lineage: list[dict[str, Any]] = []
    errors: list[str] = []
    seen: set[str] = set()
    current_ref = prev_step_ref.strip()
    while current_ref:
        if current_ref in seen:
            errors.append(f"claim-step lineage cycle at {current_ref}")
            break
        seen.add(current_ref)
        step = by_id.get(current_ref)
        if not step:
            errors.append(f"missing previous claim step {current_ref}")
            break
        if str(step.get("entry_type", "")).strip() != "claim_step":
            errors.append(f"lineage entry must be STEP-* claim_step: {current_ref}")
            break
        if str(step.get("task_ref", "")).strip() != task_ref:
            errors.append(f"lineage entry {current_ref} belongs to another TASK-*")
            break
        lineage.append(step)
        current_ref = str(step.get("prev_step_ref", "")).strip()
    return list(reversed(lineage)), errors


def _relation_pairs(shape) -> set[tuple[str, str]]:
    return {(subject, obj) for subject in shape.subject_refs for obj in shape.object_refs}


def _claim_step_repair_hint(
    *,
    relation_kind: str,
    candidate_relation_ref: str,
    subject_ref: str,
    object_ref: str,
    existing_path_refs: list[str],
    existing_relation_refs: list[str],
    existing_step_refs: list[str],
) -> dict[str, Any]:
    return {
        "error_code": "claim_step_relation_cycle",
        "relation_kind": relation_kind,
        "candidate_relation_ref": candidate_relation_ref,
        "candidate_edge": {"subject_ref": subject_ref, "object_ref": object_ref},
        "existing_path_refs": existing_path_refs,
        "existing_relation_refs": existing_relation_refs,
        "existing_step_refs": existing_step_refs,
        "repair": {
            "type": "fork_step_chain",
            "start_claim_ref": subject_ref,
            "target_claim_ref": object_ref,
            "relation_claim_ref": candidate_relation_ref,
            "suggested_commands": [
                f"reason-step --claim {subject_ref} ...",
                (
                    f"reason-step --prev-claim {subject_ref} "
                    f"--relation-claim {candidate_relation_ref} --claim {object_ref} ..."
                ),
            ],
            "alternative": (
                "If the cycle is a real higher-level fact, create or reuse an aggregate relation CLM "
                "and start a separate STEP branch from that claim."
            ),
        },
    }


def _relation_graph_edges(
    records: dict[str, dict],
    lineage: list[dict[str, Any]],
    *,
    relation_kind: str,
) -> dict[str, list[tuple[str, str, str]]]:
    graph: dict[str, list[tuple[str, str, str]]] = defaultdict(list)
    for step in lineage:
        relation_ref = str(step.get("relation_claim_ref", "")).strip()
        if not relation_ref:
            continue
        shape = relation_shape_for_claim(records.get(relation_ref, {}))
        if shape is None or shape.kind != relation_kind or shape.kind not in PROOF_RELATION_KINDS:
            continue
        step_ref = str(step.get("id", "")).strip()
        for subject_ref, object_ref in sorted(_relation_pairs(shape)):
            graph[subject_ref].append((object_ref, relation_ref, step_ref))
    return graph


def _find_relation_path(
    graph: dict[str, list[tuple[str, str, str]]],
    *,
    start_ref: str,
    target_ref: str,
) -> tuple[list[str], list[str], list[str]] | None:
    queue: deque[tuple[str, list[str], list[str], list[str]]] = deque([(start_ref, [start_ref], [], [])])
    seen = {start_ref}
    while queue:
        current_ref, path_refs, relation_refs, step_refs = queue.popleft()
        for next_ref, relation_ref, step_ref in graph.get(current_ref, []):
            next_path = [*path_refs, next_ref]
            next_relations = [*relation_refs, relation_ref]
            next_steps = [*step_refs, step_ref]
            if next_ref == target_ref:
                return next_path, next_relations, next_steps
            if next_ref in seen:
                continue
            seen.add(next_ref)
            queue.append((next_ref, next_path, next_relations, next_steps))
    return None


def _claim_step_relation_cycle_violations(
    records: dict[str, dict],
    lineage: list[dict[str, Any]],
    *,
    relation_claim_ref: str,
) -> list[dict[str, Any]]:
    relation_claim = records.get(relation_claim_ref)
    candidate_shape = relation_shape_for_claim(relation_claim or {})
    if candidate_shape is None or candidate_shape.kind not in PROOF_RELATION_KINDS:
        return []
    graph = _relation_graph_edges(records, lineage, relation_kind=candidate_shape.kind)
    violations: list[dict[str, Any]] = []
    for subject_ref, object_ref in sorted(_relation_pairs(candidate_shape)):
        existing_path = _find_relation_path(graph, start_ref=object_ref, target_ref=subject_ref)
        if existing_path is None:
            continue
        path_refs, relation_refs, step_refs = existing_path
        path_text = " -> ".join(path_refs)
        violations.append(
            {
                "error_code": "claim_step_relation_cycle",
                "message": (
                    "claim-step relation cycle would be created: "
                    f"existing {candidate_shape.kind} path {path_text} via {', '.join(relation_refs)}; "
                    f"candidate {relation_claim_ref} would add {subject_ref} {candidate_shape.kind} {object_ref}."
                ),
                "repair_hint": _claim_step_repair_hint(
                    relation_kind=candidate_shape.kind,
                    candidate_relation_ref=relation_claim_ref,
                    subject_ref=subject_ref,
                    object_ref=object_ref,
                    existing_path_refs=path_refs,
                    existing_relation_refs=relation_refs,
                    existing_step_refs=step_refs,
                ),
            }
        )
    return violations


def _claim_step_relation_cycle_messages(
    records: dict[str, dict],
    lineage: list[dict[str, Any]],
    *,
    relation_claim_ref: str,
) -> list[str]:
    return [
        str(violation.get("message", "")).strip()
        for violation in _claim_step_relation_cycle_violations(records, lineage, relation_claim_ref=relation_claim_ref)
        if str(violation.get("message", "")).strip()
    ]


def _claim_step_error_payload(error: str, decision: dict[str, Any]) -> dict[str, Any]:
    repair_hints = [hint for hint in decision.get("repair_hints", []) if isinstance(hint, dict)]
    return {
        "ok": False,
        "error": error,
        "error_code": (
            str(repair_hints[0].get("error_code", "")).strip()
            if repair_hints
            else "claim_step_invalid_transition"
        ),
        "blockers": decision.get("blockers", []),
        "repair_hints": repair_hints,
        "decision": decision,
    }


def validate_claim_step_lineage_relations(
    records: dict[str, dict],
    entries: list[dict[str, Any]],
) -> list[str]:
    errors: list[str] = []
    for entry in entries:
        if str(entry.get("entry_type", "")).strip() != "claim_step":
            continue
        entry_id = str(entry.get("id", "")).strip()
        prev_step_ref = str(entry.get("prev_step_ref", "")).strip()
        relation_claim_ref = str(entry.get("relation_claim_ref", "")).strip()
        task_ref = str(entry.get("task_ref", "")).strip()
        if not (prev_step_ref and relation_claim_ref and task_ref):
            continue
        lineage, lineage_errors = _claim_step_lineage(entries, prev_step_ref=prev_step_ref, task_ref=task_ref)
        errors.extend(f"{entry_id}: {message}" for message in lineage_errors)
        errors.extend(
            f"{entry_id}: {message}"
            for message in _claim_step_relation_cycle_messages(records, lineage, relation_claim_ref=relation_claim_ref)
        )
    return errors


def _read_reason_entries_file(path: Path) -> tuple[list[dict[str, Any]], list[str]]:
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
        payload["_ledger_path"] = str(path)
        entries.append(payload)
    return entries, errors


def _read_reason_entries_for_scope(scope: LedgerScope) -> tuple[list[dict[str, Any]], list[str]]:
    entries, errors = _read_reason_entries_file(scope.path)
    for entry in entries:
        entry["_ledger_agent_ref"] = scope.agent_ref
    return entries, errors


def _read_only_ledger_scopes(root: Path) -> list[LedgerScope]:
    scopes: list[LedgerScope] = []
    current_agent = current_reasoning_agent_ref(root, create=False)
    if current_agent:
        path = reasons_ledger_path(root, current_agent)
        if path.exists():
            scopes.append(LedgerScope(current_agent, path))
        return scopes
    agents_root = reasoning_runtime_dir(root) / "agents"
    if not agents_root.exists():
        return scopes
    for path in sorted(agents_root.glob("*/reasons.jsonl")):
        agent_ref = path.parent.name.strip()
        if agent_ref:
            scopes.append(LedgerScope(agent_ref, path))
    return scopes


def _write_ledger_scope(root: Path, agent_ref: str | None = None) -> LedgerScope | None:
    if not agent_ref:
        agent_ref = current_reasoning_agent_ref(root, create=True)
    if not agent_ref:
        return None
    path = reasons_ledger_path(root, agent_ref)
    path.parent.mkdir(parents=True, exist_ok=True)
    return LedgerScope(agent_ref, path)


def _ledger_scopes(root: Path, *, create_secret: bool, agent_ref: str | None = None) -> list[LedgerScope]:
    if create_secret:
        scope = _write_ledger_scope(root, agent_ref)
        return [scope] if scope else []
    if agent_ref:
        return [LedgerScope(agent_ref, reasons_ledger_path(root, agent_ref))]
    return _read_only_ledger_scopes(root)


def read_reason_entries(root: Path, *, agent_ref: str | None = None) -> tuple[list[dict[str, Any]], list[str]]:
    scopes = _ledger_scopes(root, create_secret=False, agent_ref=agent_ref)
    if not scopes:
        return [], []
    entries: list[dict[str, Any]] = []
    errors: list[str] = []
    for scope in scopes:
        scope_entries, scope_errors = _read_reason_entries_for_scope(scope)
        entries.extend(scope_entries)
        errors.extend(scope_errors)
    return entries, errors


def validate_reason_ledger(root: Path, *, create_secret: bool = False, agent_ref: str | None = None) -> dict[str, Any]:
    scopes = _ledger_scopes(root, create_secret=create_secret, agent_ref=agent_ref)
    if not scopes:
        return {"ok": True, "entries": [], "errors": [], "head_hash": ZERO_LEDGER_HASH}
    all_entries: list[dict[str, Any]] = []
    errors: list[str] = []
    head_hash = ZERO_LEDGER_HASH
    global_ids: set[str] = set()
    for scope in scopes:
        entries, read_errors = _read_reason_entries_for_scope(scope)
        errors.extend(read_errors)
        all_entries.extend(entries)
        scope_errors, head_hash = _validate_reason_ledger_scope(root, scope, entries, global_ids)
        errors.extend(scope_errors)
    return {
        "ok": not errors,
        "entries": all_entries,
        "errors": errors,
        "head_hash": head_hash,
    }


def _validate_reason_ledger_scope(
    root: Path,
    scope: LedgerScope,
    entries: list[dict[str, Any]],
    global_ids: set[str],
) -> tuple[list[str], str]:
    errors: list[str] = []
    previous = ZERO_LEDGER_HASH
    for index, entry in enumerate(entries, start=1):
        entry_id = str(entry.get("id", "")).strip()
        prefix = entry_id.split("-", 1)[0] if "-" in entry_id else ""
        if prefix not in LEDGER_ID_PREFIXES:
            errors.append(f"entry {index}: missing STEP-/GRANT-* id")
        elif entry_id in global_ids:
            errors.append(f"{entry_id}: duplicate id")
        global_ids.add(entry_id)
        entry_agent_ref = str(entry.get("agent_identity_ref", "")).strip()
        if int(entry.get("version", 1) or 1) >= 2:
            if not entry_agent_ref:
                errors.append(f"{entry_id or index}: missing agent_identity_ref")
            elif entry_agent_ref != scope.agent_ref:
                errors.append(f"{entry_id or index}: agent_identity_ref mismatch for ledger {scope.agent_ref}")
        if str(entry.get("prev_ledger_hash", "")).strip() != previous:
            errors.append(f"{entry_id or index}: prev_ledger_hash mismatch")
        expected_entry_hash = _entry_hash(entry)
        if str(entry.get("entry_hash", "")).strip() != expected_entry_hash:
            errors.append(f"{entry_id or index}: entry_hash mismatch; ledger appears tampered")
        pow_error = _validate_pow(entry)
        if pow_error:
            errors.append(f"{entry_id or index}: {pow_error}; ledger appears tampered")
        current_key = current_agent_private_key()
        if current_key and current_reasoning_agent_ref(root, create=False) == scope.agent_ref:
            expected_seal = _seal_payload(current_key, expected_entry_hash)
            if str(entry.get("seal", "")).strip() != expected_seal:
                errors.append(f"{entry_id or index}: seal mismatch; ledger appears tampered")
        expected_ledger_hash = _ledger_hash(previous, expected_entry_hash, str(entry.get("seal", "")).strip())
        if str(entry.get("ledger_hash", "")).strip() != expected_ledger_hash:
            errors.append(f"{entry_id or index}: ledger_hash mismatch; ledger appears tampered")
        entry_type = str(entry.get("entry_type", "")).strip()
        if entry_type not in {"claim_step", "grant"}:
            errors.append(f"{entry_id or index}: unsupported reason ledger entry_type {entry_type or 'none'}")
        if entry_type == "claim_step":
            if prefix != "STEP":
                errors.append(f"{entry_id or index}: claim_step entries must use STEP-* ids")
            if int(entry.get("version", 1) or 1) < CLAIM_STEP_ENTRY_VERSION:
                errors.append(f"{entry_id or index}: claim_step entries require version {CLAIM_STEP_ENTRY_VERSION}")
            if not str(entry.get("task_ref", "")).strip().startswith("TASK-"):
                errors.append(f"{entry_id or index}: claim_step missing task_ref")
            if not str(entry.get("wctx_ref", "")).strip().startswith("WCTX-"):
                errors.append(f"{entry_id or index}: claim_step missing wctx_ref")
            if not str(entry.get("claim_ref", "")).strip().startswith("CLM-"):
                errors.append(f"{entry_id or index}: claim_step missing claim_ref")
            if str(entry.get("prev_claim_ref", "")).strip() and not str(entry.get("relation_claim_ref", "")).strip().startswith("CLM-"):
                errors.append(f"{entry_id or index}: claim_step with prev_claim_ref requires relation_claim_ref")
        if entry_type == "grant" and prefix != "GRANT":
            errors.append(f"{entry_id or index}: grant entries must use GRANT-* ids")
        previous = str(entry.get("ledger_hash", "")).strip()
    return errors, previous


def validate_reason_ledger_state(root: Path) -> list[ValidationError]:
    """Read-only state/preflight validation for the append-only reason ledger."""

    validation = validate_reason_ledger(root, create_secret=False)
    ledger_path = next((str(entry.get("_ledger_path", "")).strip() for entry in validation.get("entries", [])), "")
    path = Path(ledger_path) if ledger_path else reasoning_runtime_dir(root)
    errors = [ValidationError(path, message) for message in validation["errors"]]
    if not validation["ok"]:
        return errors
    records, record_errors = load_records(root)
    if record_errors:
        return errors
    for entry in validation["entries"]:
        agent_ref = str(entry.get("agent_identity_ref", "")).strip()
        if not agent_ref:
            continue
        agent = records.get(agent_ref)
        if not agent or agent.get("record_type") != "agent_identity":
            errors.append(ValidationError(path, f"{str(entry.get('id', '')).strip() or 'entry'} missing agent_identity record {agent_ref}"))
            continue
        if str(entry.get("agent_key_fingerprint", "")).strip() != str(agent.get("key_fingerprint", "")).strip():
            errors.append(ValidationError(path, f"{str(entry.get('id', '')).strip() or 'entry'} agent_key_fingerprint mismatch"))
    errors.extend(ValidationError(path, message) for message in validate_claim_step_lineage_relations(records, validation["entries"]))
    return errors


def _record_path(record: dict) -> Path:
    value = record.get("_path")
    return value if isinstance(value, Path) else Path(str(value or "."))


def _ledger_grants(entries: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {
        str(entry.get("id", "")).strip(): entry
        for entry in entries
        if str(entry.get("id", "")).strip().startswith("GRANT-")
        or str(entry.get("entry_type", "")).strip() in GRANT_ENTRY_TYPES
    }


def _grant_is_current_v2(grant: dict[str, Any]) -> bool:
    return str(grant.get("entry_type", "")).strip() == "grant" and int(grant.get("version", 1) or 1) >= 2


def _justification_valid(payload: dict[str, Any]) -> bool:
    return bool(payload.get("justification_valid")) and bool(payload.get("decision_chain_valid"))


def _record_grant_ref(record: dict) -> str:
    return str(record.get("grant_ref") or record.get("reason_use_ref") or "").strip()


def _record_action_kind(record: dict) -> str:
    record_type = str(record.get("record_type", "")).strip()
    if record_type == "run":
        return str(record.get("action_kind", "")).strip()
    if record_type == "action":
        return str(record.get("kind", "")).strip()
    return str(record.get("action_kind", "")).strip()


def _grant_matches_record_scope(grant: dict[str, Any], record: dict) -> str | None:
    grant_workspace = str(grant.get("workspace_ref", "")).strip()
    workspace_refs = safe_list(record, "workspace_refs")
    if grant_workspace and workspace_refs and grant_workspace not in workspace_refs:
        return "workspace_ref mismatch"
    grant_project = str(grant.get("project_ref", "")).strip()
    project_refs = safe_list(record, "project_refs")
    if grant_project and project_refs and grant_project not in project_refs:
        return "project_ref mismatch"
    grant_task = str(grant.get("task_ref", "")).strip()
    task_refs = safe_list(record, "task_refs")
    if grant_task and task_refs and grant_task not in task_refs:
        return "task_ref mismatch"
    return None


def _grant_matches_run_command(grant: dict[str, Any], run: dict) -> str | None:
    grant_command_hash = str(grant.get("command_sha256", "")).strip()
    if not grant_command_hash:
        return None
    if command_hash(str(run.get("command", "")).strip()) != grant_command_hash:
        return "command hash mismatch"
    grant_cwd = normalize_cwd(str(grant.get("cwd", "")).strip())
    if grant_cwd and normalize_cwd(str(run.get("cwd", "")).strip()) != grant_cwd:
        return "cwd mismatch"
    grant_tool = str(grant.get("tool", "")).strip()
    if grant_tool and grant_tool != "*" and str(run.get("tool", "")).strip() != grant_tool:
        return "tool mismatch"
    return None


def _grant_matches_run_time(grant: dict[str, Any], run: dict) -> str | None:
    captured = _parse_timestamp(str(run.get("captured_at", "")).strip())
    if captured is None:
        return None
    valid_from = _parse_timestamp(str(grant.get("valid_from", "")).strip())
    expires_at = _parse_timestamp(str(grant.get("expires_at", "")).strip())
    if valid_from and captured < valid_from:
        return "captured before grant valid_from"
    if expires_at and captured > expires_at:
        return "captured after grant expires_at"
    return None


def validate_grant_run_lifecycle(root: Path, records: dict[str, dict]) -> list[ValidationError]:
    """Validate durable GRANT-* consumption by RUN-* and protected records."""

    validation = validate_reason_ledger(root, create_secret=False)
    if not validation["ok"]:
        return []
    grants = _ledger_grants(validation["entries"])
    errors: list[ValidationError] = []
    use_counts: Counter[str] = Counter()
    use_paths: dict[str, Path] = {}
    for record in records.values():
        grant_ref = _record_grant_ref(record)
        if not grant_ref:
            continue
        path = _record_path(record)
        if not grant_ref.startswith("GRANT-"):
            errors.append(ValidationError(path, f"grant_ref must reference GRANT-*: {grant_ref}"))
            continue
        grant = grants.get(grant_ref)
        if not grant:
            errors.append(ValidationError(path, f"grant_ref missing reason ledger grant: {grant_ref}"))
            continue
        if not _grant_is_current_v2(grant):
            errors.append(ValidationError(path, f"grant_ref {grant_ref} references legacy/revoked grant"))
            continue
        use_counts[grant_ref] += 1
        use_paths.setdefault(grant_ref, path)

        record_kind = _record_action_kind(record)
        grant_kind = str(grant.get("action_kind", "")).strip()
        if record_kind and grant_kind and grant_kind not in {record_kind, "*"}:
            errors.append(ValidationError(path, f"grant_ref {grant_ref} action_kind mismatch"))
        if str(record.get("record_type", "")).strip() == "action" and is_mutating_action_kind(record_kind):
            if str(grant.get("mode", "")).strip() != "edit":
                errors.append(ValidationError(path, f"grant_ref {grant_ref} must authorize edit mode"))
        scope_error = _grant_matches_record_scope(grant, record)
        if scope_error:
            errors.append(ValidationError(path, f"grant_ref {grant_ref} {scope_error}"))
        if str(record.get("record_type", "")).strip() == "run":
            command_error = _grant_matches_run_command(grant, record)
            if command_error:
                errors.append(ValidationError(path, f"grant_ref {grant_ref} {command_error}"))
            time_error = _grant_matches_run_time(grant, record)
            if time_error:
                errors.append(ValidationError(path, f"grant_ref {grant_ref} {time_error}"))

    for grant_ref, grant in grants.items():
        if not _grant_is_current_v2(grant):
            continue
        max_runs = int(grant.get("max_runs", grant.get("max_uses", 1)) or 1)
        use_count = use_counts.get(grant_ref, 0)
        if max_runs > 0 and use_count > max_runs:
            grant_path = Path(str(grant.get("_ledger_path", "")).strip()) if str(grant.get("_ledger_path", "")).strip() else reasoning_runtime_dir(root)
            errors.append(
                ValidationError(
                    use_paths.get(grant_ref, grant_path),
                    f"grant_ref {grant_ref} consumed {use_count} times; max_runs={max_runs}",
                )
            )
    return errors


def _next_ledger_id(entries: list[dict[str, Any]], prefix: str) -> str:
    normalized_prefix = prefix.strip().upper()
    if normalized_prefix not in LEDGER_ID_PREFIXES:
        raise ValueError(f"unsupported reason ledger prefix: {prefix!r}")
    today = _now().strftime("%Y%m%d")
    existing = {str(entry.get("id", "")).strip() for entry in entries}
    for _ in range(32):
        candidate = f"{normalized_prefix}-{today}-{secrets.token_hex(4)}"
        if candidate not in existing:
            return candidate
    raise RuntimeError(f"could not allocate collision-free reason id for {normalized_prefix}-{today}")


def append_reason_entry(
    root: Path,
    payload: dict[str, Any],
    *,
    id_prefix: str = "STEP",
) -> tuple[dict[str, Any] | None, str | None]:
    validation = validate_reason_ledger(root)
    if not validation["ok"]:
        return None, "; ".join(validation["errors"])
    entries = validation["entries"]
    try:
        agent = _current_agent_metadata(root, create=True)
    except AgentIdentityRequiredError as exc:
        return None, str(exc)
    agent_ref = str(agent.get("agent_identity_ref", "")).strip()
    if not agent_ref:
        return None, "local agent identity is required for reason ledger entries"
    private_key = str(agent.get("agent_private_key", "")).strip()
    if not private_key:
        return None, "agent private key is required for reason ledger entries"
    entry = {
        "id": _next_ledger_id(entries, id_prefix),
        "record_type": "reason",
        "version": int(payload.get("version", 2) or 2),
        "created_at": _now().isoformat(timespec="seconds"),
        "prev_ledger_hash": validation["head_hash"],
        **payload,
    }
    entry["agent_identity_ref"] = agent_ref
    entry["agent_key_fingerprint"] = str(agent.get("agent_key_fingerprint", "")).strip()
    try:
        entry["pow"] = _mine_pow(root, entry)
    except RuntimeError as exc:
        return None, str(exc)
    entry_hash = _entry_hash(entry)
    seal = _seal_payload(private_key, entry_hash)
    entry["entry_hash"] = entry_hash
    entry["seal"] = seal
    entry["ledger_hash"] = _ledger_hash(str(entry["prev_ledger_hash"]), entry_hash, seal)
    path = reasons_ledger_path(root, agent_ref)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(_canonical_json(entry) + "\n")
    return entry, None


def reason_by_id(entries: list[dict[str, Any]], reason_ref: str) -> dict[str, Any] | None:
    return next((entry for entry in entries if str(entry.get("id", "")).strip() == reason_ref), None)


def latest_reason_step(entries: list[dict[str, Any]], task_ref: str | None = None) -> dict[str, Any] | None:
    for entry in reversed(entries):
        if str(entry.get("entry_type", "")).strip() != "claim_step":
            continue
        if task_ref and str(entry.get("task_ref", "")).strip() != task_ref:
            continue
        return entry
    return None


def latest_final_reason_step(
    entries: list[dict[str, Any]],
    *,
    task_ref: str,
    context_fingerprint: str | None = None,
) -> dict[str, Any] | None:
    for entry in reversed(entries):
        if str(entry.get("entry_type", "")).strip() != "claim_step":
            continue
        if str(entry.get("task_ref", "")).strip() != task_ref:
            continue
        if str(entry.get("mode", "")).strip() != "final":
            continue
        if not _justification_valid(entry):
            continue
        if "final" not in entry.get("valid_for", []):
            continue
        if context_fingerprint and str(entry.get("context_fingerprint", "")).strip() != context_fingerprint:
            continue
        return entry
    return None


def latest_decision_reason_step(
    entries: list[dict[str, Any]],
    *,
    task_ref: str,
    mode: str,
    context_fingerprint: str | None = None,
) -> dict[str, Any] | None:
    for entry in reversed(entries):
        if str(entry.get("entry_type", "")).strip() != "claim_step":
            continue
        if str(entry.get("task_ref", "")).strip() != task_ref:
            continue
        if not _justification_valid(entry):
            continue
        if mode not in entry.get("valid_for", []):
            continue
        if context_fingerprint and str(entry.get("context_fingerprint", "")).strip() != context_fingerprint:
            continue
        return entry
    return None


def decision_reason_status(root: Path, *, mode: str, context_fingerprint: str | None = None) -> dict[str, Any]:
    task_ref = current_task_ref(root)
    if not task_ref:
        return {"ok": True, "required": False, "reason": None, "message": "no active TASK-*"}
    validation = validate_reason_ledger(root)
    if not validation["ok"]:
        return {
            "ok": False,
            "required": True,
            "reason": None,
            "message": "; ".join(validation["errors"]),
        }
    fingerprint = context_fingerprint or compute_context_fingerprint(root)
    reason = latest_decision_reason_step(
        validation["entries"],
        task_ref=task_ref,
        mode=mode,
        context_fingerprint=fingerprint,
    )
    if not reason:
        return {
            "ok": False,
            "required": True,
            "reason": None,
            "message": (
                f"missing reviewed STEP-* valid_for={mode}, current TASK-* node, "
                "and current context fingerprint"
            ),
        }
    records, record_errors = load_records(root)
    if record_errors:
        return {
            "ok": False,
            "required": True,
            "reason": reason,
            "message": "; ".join(f"{error.path}: {error.message}" for error in record_errors),
        }
    decision = validate_claim_step_transition(
        records,
        claim_ref=str(reason.get("claim_ref", "")).strip(),
        prev_claim_ref=str(reason.get("prev_claim_ref", "")).strip(),
        relation_claim_ref=str(reason.get("relation_claim_ref", "")).strip(),
        mode=mode,
    )
    if not _justification_valid(decision):
        blockers = decision.get("blockers", [])
        return {
            "ok": False,
            "required": True,
            "reason": reason,
            "message": f"reason chain no longer validates for mode={mode}: "
            + "; ".join(str(item) for item in blockers),
        }
    return {"ok": True, "required": True, "reason": reason, "message": ""}


def final_reason_status(root: Path, *, context_fingerprint: str | None = None) -> dict[str, Any]:
    task_ref = current_task_ref(root)
    if not task_ref:
        return {"ok": True, "required": False, "reason": None, "message": "no active TASK-*"}
    validation = validate_reason_ledger(root)
    if not validation["ok"]:
        return {
            "ok": False,
            "required": True,
            "reason": None,
            "message": "; ".join(validation["errors"]),
        }
    fingerprint = context_fingerprint or compute_context_fingerprint(root)
    reason = latest_final_reason_step(validation["entries"], task_ref=task_ref, context_fingerprint=fingerprint)
    if reason:
        records, record_errors = load_records(root)
        if record_errors:
            return {
                "ok": False,
                "required": True,
                "reason": reason,
                "message": "; ".join(f"{error.path}: {error.message}" for error in record_errors),
            }
        decision = validate_claim_step_transition(
            records,
            claim_ref=str(reason.get("claim_ref", "")).strip(),
            prev_claim_ref=str(reason.get("prev_claim_ref", "")).strip(),
            relation_claim_ref=str(reason.get("relation_claim_ref", "")).strip(),
            mode="final",
        )
        if not _justification_valid(decision):
            blockers = decision.get("blockers", [])
            return {
                "ok": False,
                "required": True,
                "reason": reason,
                "message": "final reason chain no longer validates: " + "; ".join(str(item) for item in blockers),
            }
        return {"ok": True, "required": True, "reason": reason, "message": ""}
    return {
        "ok": False,
        "required": True,
        "reason": None,
        "message": (
            "missing reviewed STEP-* with mode=final, current TASK-* node, "
            "valid_for=final, and current context fingerprint"
        ),
    }


def create_claim_step(
    root: Path,
    records: dict[str, dict],
    *,
    claim_ref: str,
    prev_claim_ref: str | None = None,
    relation_claim_ref: str | None = None,
    intent: str,
    mode: str,
    action_kind: str | None,
    reason: str,
    prev_step_ref: str | None = None,
    branch: str = "main",
    wctx_ref: str | None = None,
) -> tuple[dict[str, Any] | None, str | None]:
    task_ref = current_task_ref(root)
    if not task_ref:
        return None, "claim steps require an active TASK-*"
    validation = validate_reason_ledger(root)
    if not validation["ok"]:
        return None, "; ".join(validation["errors"])
    entries = validation["entries"]
    normalized_claim_ref = claim_ref.strip()
    normalized_prev_claim_ref = (prev_claim_ref or "").strip()
    normalized_relation_ref = (relation_claim_ref or "").strip()
    normalized_prev_step_ref = (prev_step_ref or "").strip()
    normalized_branch = branch.strip() or "main"
    task_steps = [
        entry
        for entry in entries
        if str(entry.get("entry_type", "")).strip() == "claim_step"
        and str(entry.get("task_ref", "")).strip() == task_ref
        and (str(entry.get("branch", "main")).strip() or "main") == normalized_branch
    ]
    if task_steps and not normalized_prev_step_ref:
        latest = task_steps[-1]
        normalized_prev_step_ref = str(latest.get("id", "")).strip()
        if not normalized_prev_claim_ref:
            normalized_prev_claim_ref = str(latest.get("claim_ref", "")).strip()
    if normalized_prev_step_ref:
        previous_step = reason_by_id(entries, normalized_prev_step_ref)
        if not previous_step:
            return None, f"missing previous claim step {normalized_prev_step_ref}"
        if str(previous_step.get("entry_type", "")).strip() != "claim_step":
            return None, f"previous step must be STEP-* claim_step: {normalized_prev_step_ref}"
        if str(previous_step.get("task_ref", "")).strip() != task_ref:
            return None, f"previous step {normalized_prev_step_ref} belongs to another TASK-*"
        previous_step_claim = str(previous_step.get("claim_ref", "")).strip()
        if normalized_prev_claim_ref and previous_step_claim and normalized_prev_claim_ref != previous_step_claim:
            return None, f"prev_claim_ref must match previous step claim_ref {previous_step_claim}"
        normalized_prev_claim_ref = normalized_prev_claim_ref or previous_step_claim

    decision = validate_claim_step_transition(
        records,
        claim_ref=normalized_claim_ref,
        prev_claim_ref=normalized_prev_claim_ref,
        relation_claim_ref=normalized_relation_ref,
        mode=mode,
    )
    if normalized_prev_step_ref and normalized_relation_ref:
        lineage, lineage_errors = _claim_step_lineage(entries, prev_step_ref=normalized_prev_step_ref, task_ref=task_ref)
        cycle_violations = _claim_step_relation_cycle_violations(
            records,
            lineage,
            relation_claim_ref=normalized_relation_ref,
        )
        cycle_errors = [
            str(violation.get("message", "")).strip()
            for violation in cycle_violations
            if str(violation.get("message", "")).strip()
        ]
        repair_hints = [
            violation["repair_hint"]
            for violation in cycle_violations
            if isinstance(violation.get("repair_hint"), dict)
        ]
        if lineage_errors or cycle_errors:
            decision["blockers"] = [*decision.get("blockers", []), *lineage_errors, *cycle_errors]
            if repair_hints:
                decision["repair_hints"] = [*decision.get("repair_hints", []), *repair_hints]
            decision["justification_valid"] = False
            decision["decision_chain_valid"] = False
            decision["decision_valid"] = False
    if not decision["justification_valid"]:
        blockers = "; ".join(str(item) for item in decision.get("blockers", []) if str(item).strip())
        suffix = f": {blockers}" if blockers else ""
        error = f"STEP-* claim_step requires a connected CLM transition for mode={mode}{suffix}"
        return _claim_step_error_payload(error, decision), error
    resolved_wctx_ref = str(wctx_ref or "").strip() or _active_wctx_ref_for_task(root, records, task_ref)
    if not resolved_wctx_ref:
        return None, "claim steps require an active owner-bound WCTX-* for the current TASK-*"
    if normalized_prev_step_ref and not normalized_relation_ref:
        return None, "continuing a claim-step chain requires relation_claim_ref"
    claim_step_hash = chain_payload_hash(
        {
            "task_ref": task_ref,
            "prev_step_ref": normalized_prev_step_ref,
            "prev_claim_ref": normalized_prev_claim_ref,
            "claim_ref": normalized_claim_ref,
            "relation_claim_ref": normalized_relation_ref,
            "mode": mode,
            "reason": reason.strip(),
        }
    )
    return append_reason_entry(
        root,
        {
            "version": CLAIM_STEP_ENTRY_VERSION,
            "entry_type": "claim_step",
            "status": "reviewed",
            "workspace_ref": current_workspace_ref(root),
            "project_ref": current_project_ref(root),
            "task_ref": task_ref,
            "wctx_ref": resolved_wctx_ref,
            "prev_step_ref": normalized_prev_step_ref,
            "prev_claim_ref": normalized_prev_claim_ref,
            "claim_ref": normalized_claim_ref,
            "relation_claim_ref": normalized_relation_ref,
            "branch": normalized_branch,
            "intent": intent.strip() or mode,
            "mode": mode,
            "action_kind": (action_kind or "").strip(),
            "reason": reason.strip(),
            "justification_valid": True,
            "decision_chain_valid": True,
            "decision_valid": True,
            "valid_for": decision.get("valid_for", []),
            "blockers": [],
            "hypothesis_refs": decision.get("hypothesis_refs", []),
            "relation_kind": decision.get("relation_kind", ""),
            "claim_step_hash": claim_step_hash,
            "context_fingerprint": compute_context_fingerprint(root),
        },
        id_prefix="STEP",
    )


def grant_reason_access(
    root: Path,
    *,
    reason_ref: str,
    mode: str,
    action_kind: str | None,
    ttl_seconds: int | None,
    command: str | None = None,
    cwd: str | Path | None = None,
    tool: str = "bash",
) -> tuple[dict[str, Any] | None, str | None]:
    validation = validate_reason_ledger(root)
    if not validation["ok"]:
        return None, "; ".join(validation["errors"])
    entries = validation["entries"]
    reason = reason_by_id(entries, reason_ref)
    if not reason:
        return None, f"missing reason {reason_ref}"
    try:
        agent = _current_agent_metadata(root, create=True)
    except AgentIdentityRequiredError as exc:
        return None, str(exc)
    current_agent_ref = str(agent.get("agent_identity_ref", "")).strip()
    reason_agent_ref = str(reason.get("agent_identity_ref", "")).strip()
    if not current_agent_ref:
        return None, "agent_identity_required: reason grants require the current per-agent identity"
    if reason_agent_ref and reason_agent_ref != current_agent_ref:
        return None, f"{reason_ref} belongs to another agent identity {reason_agent_ref}"
    reason_entry_type = str(reason.get("entry_type", "")).strip()
    if reason_entry_type != "claim_step":
        return None, f"{reason_ref} is not a STEP-* claim_step"
    if not _justification_valid(reason):
        return None, f"{reason_ref} has not passed decision validation"
    task_ref = current_task_ref(root)
    if not task_ref or str(reason.get("task_ref", "")).strip() != task_ref:
        return None, f"{reason_ref} does not match current TASK-* {task_ref or 'none'}"
    records, record_errors = load_records(root)
    if record_errors:
        return None, "; ".join(f"{error.path}: {error.message}" for error in record_errors)
    decision = validate_claim_step_transition(
        records,
        claim_ref=str(reason.get("claim_ref", "")).strip(),
        prev_claim_ref=str(reason.get("prev_claim_ref", "")).strip(),
        relation_claim_ref=str(reason.get("relation_claim_ref", "")).strip(),
        mode=mode,
    )
    if not decision.get("justification_valid"):
        return None, f"{reason_ref} claim-step chain no longer validates: " + "; ".join(decision.get("blockers", []))
    normalized_kind = (action_kind or "").strip()
    if mode == "edit" and not normalized_kind:
        return None, "edit grant requires action kind"
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
    normalized_command = str(command or "").strip()
    normalized_cwd = normalize_cwd(cwd)
    grant_type = "exact_command" if normalized_command else "action_kind"
    payload = {
        "entry_type": "grant",
        "status": "active",
        "grant_type": grant_type,
        "reason_ref": reason_ref,
        "reason_head_hash": validation["head_hash"],
        "workspace_ref": current_workspace_ref(root),
        "project_ref": current_project_ref(root),
        "task_ref": task_ref,
        "mode": mode,
        "action_kind": normalized_kind,
        "chain_hash": str(reason.get("chain_hash") or reason.get("claim_step_hash", "")).strip(),
        "claim_step_ref": reason_ref,
        "claim_ref": str(reason.get("claim_ref", "")).strip(),
        "relation_claim_ref": str(reason.get("relation_claim_ref", "")).strip(),
        "context_fingerprint": compute_context_fingerprint(root),
        "max_runs": 1,
        "issued_at": issued.isoformat(timespec="seconds"),
        "valid_from": issued.isoformat(timespec="seconds"),
        "expires_at": (issued + timedelta(seconds=safe_ttl)).isoformat(timespec="seconds"),
    }
    if normalized_command:
        payload["tool"] = tool.strip() or "bash"
        payload["command"] = normalized_command
        payload["command_sha256"] = command_hash(normalized_command)
        payload["cwd"] = normalized_cwd
    grant, error = append_reason_entry(
        root,
        payload,
        id_prefix="GRANT",
    )
    if grant:
        append_reason_access_event(root, "reason_grant_authorized", access=grant, mode=mode, action_kind=normalized_kind)
    return grant, error


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
        payload["grant_ref"] = str(access.get("id", "")).strip()
        payload["reason_ref"] = str(access.get("reason_ref", "")).strip()
    if reason:
        payload["failure_reason"] = reason
    try:
        append_access_event(root, payload)
    except OSError:
        return


def grant_use_count(root: Path, grant_ref: str) -> int:
    records, _ = load_records(root)
    count = 0
    for record in records.values():
        if str(record.get("grant_ref", "")).strip() == grant_ref:
            count += 1
        elif str(record.get("reason_use_ref", "")).strip() == grant_ref:
            count += 1
    return count


def validate_reason_access(
    root: Path,
    *,
    mode: str,
    action_kind: str | None,
    chain_hash_value: str | None = None,
    context_fingerprint: str | None = None,
    command: str | None = None,
    cwd: str | Path | None = None,
    tool: str | None = None,
    telemetry: dict[str, str] | None = None,
) -> dict[str, Any]:
    validation = validate_reason_ledger(root)
    if not validation["ok"]:
        reason = "; ".join(validation["errors"])
        if telemetry:
            append_reason_access_event(
                root,
                "reason_grant_rejected",
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
    normalized_command = str(command or "").strip()
    normalized_command_hash = command_hash(normalized_command) if normalized_command else ""
    normalized_cwd = normalize_cwd(cwd)
    normalized_tool = str(tool or "").strip()
    failures: list[str] = []
    candidates = [
        entry
        for entry in entries
        if str(entry.get("entry_type", "")).strip() in GRANT_ENTRY_TYPES
    ]
    current_agent = current_reasoning_agent_ref(root, create=False)
    if not current_agent:
        reason = "agent_identity_required: provide the current per-agent token before using a reason grant"
        if telemetry:
            append_reason_access_event(
                root,
                "reason_grant_rejected",
                mode=mode,
                action_kind=action_kind,
                reason=reason,
                channel=telemetry.get("channel", "cli"),
                tool=telemetry.get("tool", "validate-reason-access"),
            )
        return {"ok": False, "access": None, "reason": reason, "checked_count": len(candidates)}
    for access in reversed(candidates):
        access_id = str(access.get("id", "")).strip() or "unknown"
        if current_agent and str(access.get("agent_identity_ref", "")).strip() != current_agent:
            failures.append(f"{access_id}: agent identity mismatch")
            continue
        if str(access.get("mode", "")).strip() != mode:
            failures.append(f"{access_id}: mode mismatch")
            continue
        access_kind = str(access.get("action_kind", "")).strip()
        if normalized_kind and access_kind not in {normalized_kind, "*"}:
            failures.append(f"{access_id}: action kind mismatch")
            continue
        max_runs = int(access.get("max_runs", access.get("max_uses", 1)) or 1)
        use_count = grant_use_count(root, access_id)
        if max_runs > 0 and use_count >= max_runs:
            failures.append(f"{access_id}: already used")
            continue
        if normalized_command:
            access_command_hash = str(access.get("command_sha256", "")).strip()
            if not access_command_hash:
                failures.append(f"{access_id}: command hash missing")
                continue
            if access_command_hash != normalized_command_hash:
                failures.append(f"{access_id}: command hash mismatch")
                continue
            access_cwd = normalize_cwd(str(access.get("cwd", "")).strip())
            if access_cwd != normalized_cwd:
                failures.append(f"{access_id}: cwd mismatch")
                continue
            if normalized_tool and str(access.get("tool", "")).strip() not in {normalized_tool, "*"}:
                failures.append(f"{access_id}: tool mismatch")
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
                "reason_grant_authorized",
                access=access,
                mode=mode,
                action_kind=normalized_kind,
                channel=telemetry.get("channel", "cli"),
                tool=telemetry.get("tool", "validate-reason-access"),
            )
        return {"ok": True, "access": access, "reason": "", "checked_count": len(candidates)}
    reason = "no reason grants found" if not candidates else failures[0] if failures else "no matching reason grant"
    if telemetry:
        access_kind = "reason_grant_missing"
        if "expired" in reason:
            access_kind = "reason_grant_expired"
        elif "used" in reason:
            access_kind = "reason_grant_used_rejected"
        elif candidates:
            access_kind = "reason_grant_rejected"
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


def reserve_reason_access(
    root: Path,
    *,
    mode: str,
    action_kind: str | None,
    command: str,
    cwd: str | Path | None,
    tool: str = "bash",
) -> tuple[dict[str, Any] | None, str | None]:
    normalized_command = command.strip()
    if not normalized_command:
        return None, "grant check requires a command"
    validation = validate_reason_access(
        root,
        mode=mode,
        action_kind=action_kind,
        command=normalized_command,
        cwd=cwd,
        tool=tool,
        telemetry={"channel": "runtime", "tool": "reason-check-grant"},
    )
    if not validation.get("ok"):
        return None, str(validation.get("reason", "missing grant"))
    return validation["access"], None


def latest_reason_use_for_command(
    root: Path,
    *,
    mode: str,
    action_kind: str | None,
    command: str,
    cwd: str | Path | None,
    tool: str = "bash",
) -> dict[str, Any] | None:
    validation = validate_reason_access(
        root,
        mode=mode,
        action_kind=action_kind,
        command=command,
        cwd=cwd,
        tool=tool,
    )
    if not validation.get("ok"):
        return None
    return validation.get("access")


def reason_access_text_lines(access: dict[str, Any]) -> list[str]:
    lines = [
        "## Reason Grant",
        f"- grant: `{access.get('id')}`",
        f"- reason: `{access.get('reason_ref')}`",
        f"- mode: `{access.get('mode')}`",
        f"- action_kind: `{access.get('action_kind') or 'none'}`",
        f"- grant_type: `{access.get('grant_type') or 'action_kind'}`",
        f"- command_sha256: `{access.get('command_sha256') or 'none'}`",
        f"- expires_at: `{access.get('expires_at')}`",
        f"- max_runs: `{access.get('max_runs', access.get('max_uses', 1))}`",
    ]
    return lines


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
        if str(entry.get("entry_type", "")).strip() in GRANT_ENTRY_TYPES
        and (not task_ref or str(entry.get("task_ref", "")).strip() == task_ref)
    ]
    lines = ["# Claim-Step Ledger", f"- entries: `{len(entries)}`", f"- current_task: `{task_ref or 'none'}`"]
    if step:
        lines.extend(
            [
                f"- current_step: `{step.get('id')}`",
                f"- intent: `{step.get('intent')}` mode=`{step.get('mode')}` kind=`{step.get('action_kind') or 'none'}`",
                f"- why: {step.get('why')}",
            ]
        )
    else:
        lines.append("- current_step: `none`")
    final_status = final_reason_status(root)
    final_reason = final_status.get("reason")
    if isinstance(final_reason, dict):
        lines.append(f"- final_reason: `{final_reason.get('id')}`")
    elif final_status.get("required"):
        lines.append(f"- final_reason: `none` ({final_status.get('message')})")
    recent_steps = [
        entry
        for entry in entries
        if str(entry.get("entry_type", "")).strip() == "claim_step"
        and (not task_ref or str(entry.get("task_ref", "")).strip() == task_ref)
    ]
    if recent_steps:
        lines.append("## Recent Claim Steps")
        for reason in recent_steps[-5:]:
            lines.append(
                f"- step `{reason.get('id')}` branch=`{reason.get('branch') or 'main'}` "
                f"prev=`{reason.get('prev_step_ref') or 'none'}` claim=`{reason.get('claim_ref') or 'none'}` "
                f"relation=`{reason.get('relation_claim_ref') or 'none'}` mode=`{reason.get('mode')}` "
                f"kind=`{reason.get('action_kind') or 'none'}` reason={reason.get('reason')}"
            )
    for access in accesses[-5:]:
        grant_ref = str(access.get("id", "")).strip()
        use_count = grant_use_count(root, grant_ref)
        status = "used" if use_count >= int(access.get("max_runs", access.get("max_uses", 1)) or 1) else str(access.get("status", "active"))
        lines.append(
            f"- grant `{access.get('id')}` reason=`{access.get('reason_ref')}` mode=`{access.get('mode')}` kind=`{access.get('action_kind') or 'none'}` status=`{status}` runs=`{use_count}` command_sha256=`{access.get('command_sha256') or 'none'}`"
        )
    return lines, 0
