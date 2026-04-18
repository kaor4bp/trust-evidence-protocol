"""Hypothesis index IO and retrieval helpers."""

from __future__ import annotations

import json
from pathlib import Path

from .claims import claim_is_fallback
from .errors import ValidationError
from .io import write_text_file
from .paths import hypotheses_index_path
from .scopes import record_belongs_to_project, record_belongs_to_task
from .search import score_record


def validate_hypothesis_claim(records: dict[str, dict], claim_ref: str) -> str | None:
    if claim_ref not in records:
        return f"missing claim_ref {claim_ref}"
    claim = records[claim_ref]
    if claim.get("record_type") != "claim":
        return f"{claim_ref} must reference a claim record"
    if str(claim.get("status", "")).strip() != "tentative":
        return f"{claim_ref} must reference a tentative claim"
    if claim_is_fallback(claim):
        return f"{claim_ref} must reference an active lifecycle claim"
    return None


def build_hypothesis_entry(
    claim: dict,
    claim_ref: str,
    timestamp: str,
    domain: str | None,
    scope: str | None,
    model_refs: list[str],
    flow_refs: list[str],
    action_refs: list[str],
    plan_refs: list[str],
    rollback_refs: list[str],
    mode: str,
    based_on_hypotheses: list[str],
    note: str,
) -> dict:
    return {
        "claim_ref": claim_ref,
        "domain": (domain or str(claim.get("domain", "")) or "").strip(),
        "scope": (scope or str(claim.get("scope", "")) or "").strip(),
        "status": "active",
        "mode": mode,
        "based_on_hypotheses": based_on_hypotheses,
        "used_by": {
            "models": model_refs,
            "flows": flow_refs,
            "actions": action_refs,
            "plans": plan_refs,
        },
        "rollback_refs": rollback_refs,
        "created_at": timestamp,
        "updated_at": timestamp,
        "note": note.strip(),
    }


def hypothesis_active_entry_exists(entries: list[dict], claim_ref: str) -> bool:
    return any(
        str(entry.get("claim_ref", "")).strip() == claim_ref
        and str(entry.get("status", "")).strip() == "active"
        for entry in entries
    )


def close_hypothesis_entries(
    entries: list[dict],
    claim_ref: str,
    status: str,
    timestamp: str,
    note: str | None,
) -> tuple[list[dict], bool]:
    updated_entries: list[dict] = []
    updated = False
    for entry in entries:
        next_entry = dict(entry)
        if (
            str(next_entry.get("claim_ref", "")).strip() == claim_ref
            and str(next_entry.get("status", "")).strip() == "active"
        ):
            next_entry["status"] = status
            next_entry["updated_at"] = timestamp
            if note:
                next_entry["note"] = note.strip()
            updated = True
        updated_entries.append(next_entry)
    return updated_entries, updated


def reopen_hypothesis_entry(
    entries: list[dict],
    claim_ref: str,
    timestamp: str,
    note: str | None,
) -> tuple[list[dict], str]:
    updated_entries: list[dict] = []
    reopened = False
    active_exists = False
    for entry in entries:
        next_entry = dict(entry)
        if str(next_entry.get("claim_ref", "")).strip() != claim_ref:
            updated_entries.append(next_entry)
            continue
        if str(next_entry.get("status", "")).strip() == "active":
            active_exists = True
            updated_entries.append(next_entry)
            continue
        if not reopened:
            next_entry["status"] = "active"
            next_entry["updated_at"] = timestamp
            if note:
                next_entry["note"] = note.strip()
            reopened = True
        updated_entries.append(next_entry)
    if active_exists:
        return updated_entries, "active-exists"
    if not reopened:
        return updated_entries, "missing"
    return updated_entries, "reopened"


def remove_hypothesis_entries(entries: list[dict], claim_ref: str) -> tuple[list[dict], bool]:
    remaining = [entry for entry in entries if str(entry.get("claim_ref", "")).strip() != claim_ref]
    return remaining, len(remaining) != len(entries)


def sync_hypothesis_entries(
    entries: list[dict],
    records: dict[str, dict],
    drop_closed: bool,
) -> tuple[list[dict], list[str]]:
    kept: list[dict] = []
    removed: list[str] = []
    for entry in entries:
        claim_ref = str(entry.get("claim_ref", "")).strip()
        status = str(entry.get("status", "")).strip()
        claim = records.get(claim_ref)

        if claim is None or claim.get("record_type") != "claim":
            removed.append(f"{claim_ref}: missing-claim")
            continue
        if str(claim.get("status", "")).strip() != "tentative":
            removed.append(f"{claim_ref}: claim-no-longer-tentative")
            continue
        if drop_closed and status != "active":
            removed.append(f"{claim_ref}: dropped-closed-status={status}")
            continue
        kept.append(entry)
    return kept, removed


def load_hypotheses_index(root: Path) -> tuple[list[dict], list[ValidationError]]:
    path = hypotheses_index_path(root)
    if not path.exists():
        return [], []
    entries: list[dict] = []
    errors: list[ValidationError] = []
    for lineno, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw_line.strip()
        if not line:
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError as exc:
            errors.append(ValidationError(path, f"line {lineno}: invalid JSON ({exc.msg})"))
            continue
        if not isinstance(payload, dict):
            errors.append(ValidationError(path, f"line {lineno}: hypothesis entry must be a JSON object"))
            continue
        payload["_line"] = lineno
        entries.append(payload)
    return entries, errors


def write_hypotheses_index(root: Path, entries: list[dict]) -> None:
    path = hypotheses_index_path(root)
    lines: list[str] = []
    for entry in entries:
        payload = {key: value for key, value in entry.items() if not key.startswith("_")}
        lines.append(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")
    write_text_file(path, "".join(lines))


def collect_claim_refs_from_models_flows(models: list[dict], flows: list[dict]) -> set[str]:
    refs: set[str] = set()
    for model in models:
        refs.update(model.get("claim_refs", []))
        refs.update(model.get("hypothesis_refs", []))
    for flow in flows:
        for block_name in ("preconditions", "oracle"):
            block = flow.get(block_name, {})
            if isinstance(block, dict):
                refs.update(block.get("claim_refs", []))
                refs.update(block.get("success_claim_refs", []))
                refs.update(block.get("failure_claim_refs", []))
                refs.update(block.get("hypothesis_refs", []))
        for step in flow.get("steps", []):
            if isinstance(step, dict):
                refs.update(step.get("claim_refs", []))
    return {ref for ref in refs if str(ref).startswith("CLM-")}


def active_hypotheses_for(
    records: dict[str, dict],
    root: Path,
    terms: set[str],
    claim_refs: set[str],
    project_ref: str | None = None,
    task_ref: str | None = None,
) -> list[dict]:
    entries, _ = load_hypotheses_index(root)
    result = []
    for entry in entries:
        if str(entry.get("status", "")).strip() != "active":
            continue
        claim_ref = str(entry.get("claim_ref", "")).strip()
        claim = records.get(claim_ref, {})
        if project_ref and not record_belongs_to_project(claim, project_ref):
            continue
        if not record_belongs_to_task(claim, task_ref):
            continue
        if claim_is_fallback(claim):
            continue
        if claim_ref in claim_refs or score_record(claim, terms) > 1 or score_record(entry, terms) > 1:
            enriched = dict(entry)
            enriched["_claim"] = claim
            result.append(enriched)
    return result


def active_hypothesis_entry_by_claim(root: Path, records: dict[str, dict]) -> dict[str, dict]:
    entries, _ = load_hypotheses_index(root)
    return {
        str(entry.get("claim_ref", "")).strip(): entry
        for entry in entries
        if str(entry.get("status", "")).strip() == "active"
        and str(entry.get("claim_ref", "")).strip()
        and not claim_is_fallback(records.get(str(entry.get("claim_ref", "")).strip(), {}))
    }


def validate_hypotheses_index(root: Path, records: dict[str, dict]) -> list[ValidationError]:
    entries, errors = load_hypotheses_index(root)
    active_by_scope: dict[str, list[str]] = {}
    for entry in entries:
        line = int(entry.get("_line", 0))
        path = hypotheses_index_path(root)
        claim_ref = str(entry.get("claim_ref", "")).strip()
        if not claim_ref:
            errors.append(ValidationError(path, f"line {line}: claim_ref is required"))
            continue
        if claim_ref not in records:
            errors.append(ValidationError(path, f"line {line}: missing claim_ref {claim_ref}"))
            continue
        claim = records[claim_ref]
        if claim.get("record_type") != "claim":
            errors.append(ValidationError(path, f"line {line}: claim_ref {claim_ref} must reference a claim"))
            continue
        if str(claim.get("status", "")).strip() != "tentative":
            errors.append(ValidationError(path, f"line {line}: hypothesis index may reference only tentative claims"))
        status = str(entry.get("status", "")).strip()
        if status not in {"active", "confirmed", "falsified", "abandoned"}:
            errors.append(ValidationError(path, f"line {line}: invalid hypothesis status"))
        if status == "active" and claim_is_fallback(claim):
            errors.append(ValidationError(path, f"line {line}: active hypothesis index may reference only active lifecycle claims"))
        mode = str(entry.get("mode", "durable")).strip() or "durable"
        if mode not in {"durable", "exploration"}:
            errors.append(ValidationError(path, f"line {line}: invalid hypothesis mode"))
        based_on_hypotheses = entry.get("based_on_hypotheses", [])
        if not isinstance(based_on_hypotheses, list):
            errors.append(ValidationError(path, f"line {line}: based_on_hypotheses must be a list"))
            based_on_hypotheses = []
        for ref in based_on_hypotheses:
            if ref not in records:
                errors.append(ValidationError(path, f"line {line}: missing based_on_hypothesis {ref}"))
            elif records[ref].get("record_type") != "claim" or str(records[ref].get("status", "")).strip() != "tentative":
                errors.append(ValidationError(path, f"line {line}: based_on_hypothesis {ref} must reference tentative claim"))
            elif status == "active" and claim_is_fallback(records[ref]):
                errors.append(ValidationError(path, f"line {line}: based_on_hypothesis {ref} must reference active lifecycle claim"))
        if based_on_hypotheses and mode != "exploration":
            errors.append(ValidationError(path, f"line {line}: based_on_hypotheses requires mode=exploration"))
        used_by = entry.get("used_by", {})
        if used_by is not None and not isinstance(used_by, dict):
            errors.append(ValidationError(path, f"line {line}: used_by must be an object"))
        if status == "active":
            scope = str(entry.get("scope", "")).strip() or str(claim.get("scope", "")).strip()
            active_by_scope.setdefault(scope, []).append(claim_ref)

    for scope, claim_refs in sorted(active_by_scope.items()):
        if len(claim_refs) > 5:
            errors.append(
                ValidationError(
                    hypotheses_index_path(root),
                    f"scope {scope!r} has too many active hypotheses ({len(claim_refs)}): {', '.join(claim_refs)}",
                )
            )
    return errors
