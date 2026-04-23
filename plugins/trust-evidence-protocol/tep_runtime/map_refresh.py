"""Durable MAP-* refresh service."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .attention import curiosity_map_payload, filter_attention_payload, load_attention_payload
from .cli_common import public_record_payload, refresh_generated_outputs, validate_mutated_records
from .contracts import MapRecord
from .hydration import invalidate_hydration_state
from .ids import next_record_id, now_timestamp
from .io import context_write_lock, write_json_file
from .paths import record_path
from .reports import write_validation_report
from .scopes import current_project_ref, current_task_ref, current_workspace_ref
from .search import concise


MAP_REFRESH_GENERATOR = "map_refresh"


def _canonical_json(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha256_payload(payload: Any) -> str:
    return "sha256:" + hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()


def _map_scope(mode: str, scope: str) -> str:
    return f"map_refresh.{mode}.{scope}"


def _scope_refs(root: Path) -> dict[str, list[str]]:
    workspace_ref = current_workspace_ref(root)
    project_ref = current_project_ref(root)
    task_ref = current_task_ref(root)
    return {
        "workspace_refs": [workspace_ref] if workspace_ref else [],
        "project_refs": [project_ref] if project_ref else [],
        "task_refs": [task_ref] if task_ref else [],
        "wctx_refs": [],
    }


def _scoped_attention_payload(root: Path, payload: dict, scope: str, mode: str) -> dict:
    return filter_attention_payload(
        payload,
        scope=scope,
        mode=mode,
        workspace_ref=current_workspace_ref(root),
        project_ref=current_project_ref(root),
        task_ref=current_task_ref(root),
    )


def _record_summary(records: dict[str, dict], record_ref: str) -> str:
    record = records.get(record_ref, {})
    return concise(
        str(record.get("statement") or record.get("summary") or record.get("title") or record.get("note") or record_ref),
        140,
    )


def _proof_route(record_refs: list[str]) -> dict[str, Any]:
    return {
        "route_kind": "curiosity_probe_records",
        "route_refs": record_refs,
        "required_drilldown": True,
    }


def map_candidate_from_prompt(
    root: Path,
    records: dict[str, dict],
    prompt: dict,
    *,
    mode: str,
    scope: str,
    timestamp: str,
) -> dict | None:
    record_refs = [str(ref).strip() for ref in prompt.get("record_refs", []) if str(ref).strip() in records]
    if len(record_refs) < 2:
        return None
    source_material = {
        "level": "L1",
        "map_kind": "evidence_patch",
        "mode": mode,
        "scope": scope,
        "record_refs": record_refs,
        "route_kind": "curiosity_probe_records",
    }
    fingerprint = _sha256_payload(source_material)
    summary = str(prompt.get("question") or "").strip()
    if not summary:
        summary = "Curiosity route over " + ", ".join(_record_summary(records, ref) for ref in record_refs[:2])
    signals = {
        "curiosity": {
            "score": prompt.get("score", 0),
            "link_state": str(prompt.get("link_state") or "candidate"),
            "cluster_refs": [str(ref) for ref in prompt.get("cluster_refs", []) if str(ref)],
        },
        "tap_smell": {
            "score": 0.0,
            "half_life_days": 7.0,
        },
        "source_prompt_index": prompt.get("probe_index", 0),
    }
    scope_refs = _scope_refs(root)
    payload = MapRecord(
        id="",
        scope=_map_scope(mode, scope),
        level="L1",
        map_kind="evidence_patch",
        status="active",
        summary=concise(summary, 260),
        scope_refs=scope_refs,
        anchor_refs=record_refs[:2],
        derived_from_refs=record_refs,
        source_set_fingerprint=fingerprint,
        proof_routes=(_proof_route(record_refs),),
        signals=signals,
        generated_by=MAP_REFRESH_GENERATOR,
        generated_at=timestamp,
        updated_at=timestamp,
        stale_policy="source_set_changed",
    ).to_payload()
    for key in ("workspace_refs", "project_refs", "task_refs"):
        values = [str(ref) for ref in scope_refs.get(key, []) if str(ref)]
        if values:
            payload[key] = values
    return payload


def _same_anchor_key(record: dict) -> tuple[str, str, str, tuple[str, ...]]:
    return (
        str(record.get("level", "")),
        str(record.get("map_kind", "")),
        str(record.get("scope", "")),
        tuple(str(ref) for ref in record.get("anchor_refs", [])),
    )


def _existing_maps(records: dict[str, dict]) -> list[dict]:
    return [record for record in records.values() if record.get("record_type") == "map"]


def _active_matching_fingerprint(records: dict[str, dict], candidate: dict) -> dict | None:
    for record in _existing_maps(records):
        if str(record.get("status", "")) != "active":
            continue
        if _same_anchor_key(record) == _same_anchor_key(candidate) and record.get("source_set_fingerprint") == candidate.get("source_set_fingerprint"):
            return record
    return None


def _active_same_anchor(records: dict[str, dict], candidate: dict) -> dict | None:
    for record in _existing_maps(records):
        if str(record.get("status", "")) == "active" and _same_anchor_key(record) == _same_anchor_key(candidate):
            return record
    return None


def build_map_refresh_plan(
    root: Path,
    records: dict[str, dict],
    *,
    scope: str = "current",
    mode: str = "general",
    volume: str = "compact",
    limit: int = 5,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    attention_payload = load_attention_payload(root)
    if not attention_payload:
        return {}, [{"path": "", "reason": "attention_index_missing", "detail": "run attention-index build first"}]
    scoped = _scoped_attention_payload(root, attention_payload, scope, mode)
    visual_map = curiosity_map_payload(scoped, volume=volume)
    timestamp = now_timestamp()
    candidates: list[dict] = []
    for prompt in visual_map.get("curiosity_prompts", []):
        if len(candidates) >= limit:
            break
        if not isinstance(prompt, dict):
            continue
        candidate = map_candidate_from_prompt(root, records, prompt, mode=mode, scope=scope, timestamp=timestamp)
        if candidate:
            candidates.append(candidate)

    created_refs: list[str] = []
    updated_refs: list[str] = []
    stale_refs: list[str] = []
    planned_actions: list[dict[str, Any]] = []
    mutations: dict[str, dict] = {}
    working_records = dict(records)

    for candidate in candidates:
        existing = _active_matching_fingerprint(working_records, candidate)
        if existing:
            record_id = str(existing["id"])
            updated = public_record_payload(existing)
            updated["signals"] = candidate.get("signals", {})
            updated["updated_at"] = timestamp
            mutations[record_id] = updated
            working_records[record_id] = updated
            updated_refs.append(record_id)
            planned_actions.append({"action": "update_map_signals", "record_id": record_id})
            continue

        replaced = _active_same_anchor(working_records, candidate)
        supersedes_refs: list[str] = []
        if replaced:
            old_id = str(replaced["id"])
            stale = public_record_payload(replaced)
            stale["status"] = "stale"
            stale["updated_at"] = timestamp
            mutations[old_id] = stale
            working_records[old_id] = stale
            stale_refs.append(old_id)
            supersedes_refs.append(old_id)
            planned_actions.append({"action": "mark_map_stale", "record_id": old_id})

        record_id = next_record_id(working_records, "MAP-")
        created = dict(candidate)
        created["id"] = record_id
        created["supersedes_refs"] = supersedes_refs
        created["refines_map_refs"] = supersedes_refs
        mutations[record_id] = created
        working_records[record_id] = created
        created_refs.append(record_id)
        planned_actions.append(
            {
                "action": "create_map_cell",
                "record_id": record_id,
                "level": created["level"],
                "map_kind": created["map_kind"],
                "anchor_refs": created["anchor_refs"],
            }
        )

    return (
        {
            "map_refresh_is_proof": False,
            "attention_index_is_proof": False,
            "mode": mode,
            "scope": scope,
            "volume": volume,
            "limit": limit,
            "planned_actions": planned_actions,
            "created_refs": created_refs,
            "updated_refs": updated_refs,
            "stale_refs": stale_refs,
            "candidate_count": len(candidates),
            "mutations": mutations,
            "note": "MAP-* cells are durable navigation records. Drill down through proof_routes before citing support.",
        },
        [],
    )


def map_refresh_service(
    root: Path,
    records: dict[str, dict],
    *,
    scope: str = "current",
    mode: str = "general",
    volume: str = "compact",
    limit: int = 5,
    apply: bool = True,
) -> tuple[dict[str, Any] | None, str | None]:
    payload, issues = build_map_refresh_plan(root, records, scope=scope, mode=mode, volume=volume, limit=limit)
    if issues:
        return None, "; ".join(f"{issue.get('reason')}: {issue.get('detail', '')}".rstrip() for issue in issues)
    mutations = payload.pop("mutations", {})
    payload["applied"] = bool(apply)
    if apply:
        with context_write_lock(root):
            merged, errors = validate_mutated_records(root, records, mutations)
            if errors:
                return None, "; ".join(f"{error.path}: {error.message}" for error in errors)
            if mutations:
                for record_id, record in mutations.items():
                    write_json_file(record_path(root, str(record.get("record_type", "")), record_id), record)
                write_validation_report(root, [])
                refresh_generated_outputs(root, merged)
                invalidate_hydration_state(root, f"map_refresh {len(mutations)} records")
    else:
        _, errors = validate_mutated_records(root, records, mutations)
        if errors:
            return None, "; ".join(f"{error.path}: {error.message}" for error in errors)
    return payload, None


def map_refresh_text_lines(payload: dict[str, Any]) -> list[str]:
    lines = [
        "# MAP Refresh",
        "",
        "Mode: durable MAP-* refresh. Navigation only; not proof.",
        f"scope: `{payload.get('scope')}` mode: `{payload.get('mode')}` volume: `{payload.get('volume')}` applied=`{payload.get('applied')}`",
        f"candidates: `{payload.get('candidate_count', 0)}` created=`{len(payload.get('created_refs', []))}` updated=`{len(payload.get('updated_refs', []))}` stale=`{len(payload.get('stale_refs', []))}`",
        "",
        "## Actions",
    ]
    for action in payload.get("planned_actions", []):
        lines.append(f"- {action.get('action')}: `{action.get('record_id')}`")
    if not payload.get("planned_actions"):
        lines.append("- none")
    lines.extend(["", str(payload.get("note", ""))])
    return lines
