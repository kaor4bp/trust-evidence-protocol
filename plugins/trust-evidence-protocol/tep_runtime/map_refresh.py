"""Durable MAP-* refresh service."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
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
MAP_REFRESH_TRIGGER_TYPES = {"claim", "model", "flow"}
MAP_REFRESH_TRIGGER_CLAIM_KINDS = {"", "factual", "implied", "statistical"}
MAP_REFRESH_TRIGGER_STATUSES = {
    "claim": {"supported", "corroborated", "contested", "tentative"},
    "model": {"working", "stable"},
    "flow": {"working", "stable"},
}
TERMINAL_ANCHOR_STATUSES = {"archived", "rejected", "superseded", "stale"}
TERMINAL_CLAIM_LIFECYCLE_STATES = {"archived", "resolved", "historical"}


def _canonical_json(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha256_payload(payload: Any) -> str:
    return "sha256:" + hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()


def _map_scope(mode: str, scope: str) -> str:
    return f"map_refresh.{mode}.{scope}"


def _safe_list(record: dict, key: str) -> list[str]:
    values = record.get(key, [])
    if not isinstance(values, list):
        return []
    return [str(value).strip() for value in values if str(value).strip()]


def _parse_timestamp(value: str) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def _record_change_timestamp(record: dict) -> datetime | None:
    for key in ("updated_at", "recorded_at", "captured_timestamp", "created_at"):
        parsed = _parse_timestamp(str(record.get(key, "")).strip())
        if parsed is not None:
            return parsed
    return None


def _record_change_timestamp_text(record: dict) -> str:
    for key in ("updated_at", "recorded_at", "captured_timestamp", "created_at"):
        value = str(record.get(key, "")).strip()
        if value:
            return value
    return ""


def _map_updated_timestamp(record: dict) -> datetime | None:
    return _parse_timestamp(str(record.get("updated_at", "")).strip())


def _mode_scope_from_map_scope(value: str) -> tuple[str, str] | None:
    prefix = "map_refresh."
    scope_value = str(value or "").strip()
    if not scope_value.startswith(prefix):
        return None
    remainder = scope_value.removeprefix(prefix)
    mode, separator, scope = remainder.partition(".")
    if not separator or not mode or not scope:
        return None
    return mode, scope


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


def _map_record_scope_matches(root: Path, map_record: dict, *, mode: str, scope: str) -> bool:
    if str(map_record.get("scope", "")) != _map_scope(mode, scope):
        return False
    if scope == "all":
        return True
    scope_refs = map_record.get("scope_refs", {})
    if not isinstance(scope_refs, dict):
        scope_refs = {}
    current_refs = {
        "workspace_refs": current_workspace_ref(root),
        "project_refs": current_project_ref(root),
        "task_refs": current_task_ref(root),
    }
    for key, current_ref in current_refs.items():
        if not current_ref:
            continue
        values = [*_safe_list(map_record, key), *[str(ref) for ref in scope_refs.get(key, []) if str(ref)]]
        if values and current_ref not in values:
            return False
    return True


def _source_record_scope_matches(root: Path, record: dict, *, scope: str) -> bool:
    if scope == "all":
        return True
    for key, current_ref in (
        ("workspace_refs", current_workspace_ref(root)),
        ("project_refs", current_project_ref(root)),
        ("task_refs", current_task_ref(root)),
    ):
        if not current_ref:
            continue
        refs = _safe_list(record, key)
        if refs and current_ref not in refs:
            return False
    return True


def _mapworthy_record(record: dict) -> bool:
    record_type = str(record.get("record_type", "")).strip()
    if record_type not in MAP_REFRESH_TRIGGER_TYPES:
        return False
    status = str(record.get("status", "")).strip() or "tentative"
    if status not in MAP_REFRESH_TRIGGER_STATUSES[record_type]:
        return False
    if record_type == "claim":
        claim_kind = str(record.get("claim_kind", "")).strip()
        if claim_kind not in MAP_REFRESH_TRIGGER_CLAIM_KINDS:
            return False
    return True


def _terminal_anchor_reason(record: dict) -> str:
    status = str(record.get("status", "")).strip()
    if status in TERMINAL_ANCHOR_STATUSES:
        return f"anchor_{status}"
    if record.get("record_type") == "claim":
        lifecycle = record.get("lifecycle", {})
        lifecycle_state = str(lifecycle.get("state", "")).strip() if isinstance(lifecycle, dict) else ""
        if lifecycle_state in TERMINAL_CLAIM_LIFECYCLE_STATES:
            return f"anchor_lifecycle_{lifecycle_state}"
    return ""


def _map_source_set_fingerprint(record: dict) -> str:
    parsed = _mode_scope_from_map_scope(str(record.get("scope", "")))
    if not parsed:
        return ""
    mode, scope = parsed
    record_refs = _safe_list(record, "derived_from_refs")
    if not record_refs:
        record_refs = _safe_list(record, "anchor_refs")
    if not record_refs:
        return ""
    source_material = {
        "level": str(record.get("level", "")),
        "map_kind": str(record.get("map_kind", "")),
        "mode": mode,
        "scope": scope,
        "record_refs": record_refs,
        "route_kind": "curiosity_probe_records",
    }
    return _sha256_payload(source_material)


def map_cell_refresh_triggers(records: dict[str, dict], active_maps: list[dict], *, limit: int) -> list[dict[str, Any]]:
    triggers: list[dict[str, Any]] = []
    for map_record in active_maps:
        map_ref = str(map_record.get("id", "")).strip()
        terminal_refs = []
        for ref in sorted({*_safe_list(map_record, "anchor_refs"), *_safe_list(map_record, "derived_from_refs")}):
            record = records.get(ref)
            if not record:
                continue
            reason = _terminal_anchor_reason(record)
            if reason:
                terminal_refs.append({"record_ref": ref, "reason": reason, "status": str(record.get("status", ""))})
        if terminal_refs:
            reasons = sorted({item["reason"] for item in terminal_refs})
            triggers.append(
                {
                    "record_ref": map_ref,
                    "record_type": "map",
                    "status": str(map_record.get("status", "")),
                    "reason": "map_has_terminal_anchor",
                    "anchor_refs": [item["record_ref"] for item in terminal_refs],
                    "anchor_reasons": reasons,
                    "map_refs": [map_ref],
                    "summary": _record_summary(records, map_ref),
                    "trigger_is_proof": False,
                }
            )
        expected_fingerprint = _map_source_set_fingerprint(map_record)
        if expected_fingerprint and expected_fingerprint != str(map_record.get("source_set_fingerprint", "")).strip():
            triggers.append(
                {
                    "record_ref": map_ref,
                    "record_type": "map",
                    "status": str(map_record.get("status", "")),
                    "reason": "source_set_fingerprint_changed",
                    "expected_source_set_fingerprint": expected_fingerprint,
                    "actual_source_set_fingerprint": str(map_record.get("source_set_fingerprint", "")),
                    "map_refs": [map_ref],
                    "summary": _record_summary(records, map_ref),
                    "trigger_is_proof": False,
                }
            )
        if len(triggers) >= limit:
            break
    return triggers[:limit]


def map_refresh_triggers(
    root: Path,
    records: dict[str, dict],
    *,
    scope: str = "current",
    mode: str = "general",
    limit: int = 12,
) -> list[dict[str, Any]]:
    """Return navigation-only reasons why durable MAP cells should be refreshed."""

    active_maps = [
        record
        for record in _existing_maps(records)
        if str(record.get("status", "active")).strip() == "active"
        and _map_record_scope_matches(root, record, mode=mode, scope=scope)
    ]
    triggers = map_cell_refresh_triggers(records, active_maps, limit=limit)
    covered_refs: dict[str, list[dict[str, Any]]] = {}
    for map_record in active_maps:
        map_ref = str(map_record.get("id", "")).strip()
        map_updated = _map_updated_timestamp(map_record)
        for ref in sorted({*_safe_list(map_record, "anchor_refs"), *_safe_list(map_record, "derived_from_refs")}):
            covered_refs.setdefault(ref, []).append({"map_ref": map_ref, "map_updated_at": map_updated})

    for record_id, record in sorted(records.items()):
        if len(triggers) >= limit:
            break
        if not _mapworthy_record(record) or not _source_record_scope_matches(root, record, scope=scope):
            continue
        record_timestamp = _record_change_timestamp(record)
        covering_maps = covered_refs.get(record_id, [])
        reason = ""
        map_refs: list[str] = []
        if not covering_maps:
            reason = "uncovered_mapworthy_record"
        elif record_timestamp is not None:
            stale_maps = [
                item["map_ref"]
                for item in covering_maps
                if item.get("map_updated_at") is not None and item["map_updated_at"] < record_timestamp
            ]
            if stale_maps:
                reason = "covered_record_newer_than_map"
                map_refs = stale_maps
        if not reason:
            continue
        triggers.append(
            {
                "record_ref": record_id,
                "record_type": str(record.get("record_type", "")),
                "claim_kind": str(record.get("claim_kind", "")),
                "status": str(record.get("status", "")),
                "reason": reason,
                "changed_at": _record_change_timestamp_text(record),
                "map_refs": map_refs,
                "summary": _record_summary(records, record_id),
                "trigger_is_proof": False,
            }
        )
    return triggers


def map_refresh_recommended_commands(*, scope: str, mode: str, dry_run_first: bool = True) -> list[str]:
    commands = ["attention-index build"]
    if dry_run_first:
        commands.append(f"map-refresh --mode {mode} --scope {scope} --dry-run --format json")
    commands.append(f"map-refresh --mode {mode} --scope {scope} --format json")
    return commands


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


def _active_l1_maps_for_l2(records: dict[str, dict], *, mode: str, scope: str) -> list[dict]:
    expected_scope = _map_scope(mode, scope)
    return [
        record
        for record in _existing_maps(records)
        if str(record.get("status", "")).strip() == "active"
        and str(record.get("scope", "")).strip() == expected_scope
        and str(record.get("level", "")).strip() == "L1"
        and str(record.get("map_kind", "")).strip() == "evidence_patch"
    ]


def _l2_anchor_refs(records: dict[str, dict], map_record: dict) -> list[str]:
    refs = [*_safe_list(map_record, "anchor_refs"), *_safe_list(map_record, "derived_from_refs")]
    allowed_types = {"claim", "model", "flow"}
    return [
        ref
        for ref in refs
        if ref in records and records[ref].get("record_type") in allowed_types and not _terminal_anchor_reason(records[ref])
    ]


def l2_candidate_from_l1_group(
    root: Path,
    records: dict[str, dict],
    shared_ref: str,
    l1_maps: list[dict],
    *,
    mode: str,
    scope: str,
    timestamp: str,
) -> dict | None:
    if len(l1_maps) < 2:
        return None
    down_refs = sorted(str(record.get("id", "")).strip() for record in l1_maps if str(record.get("id", "")).strip())[:4]
    if len(down_refs) < 2:
        return None
    source_material = {
        "level": "L2",
        "map_kind": "mechanism_cell",
        "mode": mode,
        "scope": scope,
        "shared_ref": shared_ref,
        "down_refs": down_refs,
        "route_kind": "map_l2_mechanism",
    }
    shared_summary = _record_summary(records, shared_ref)
    l1_summaries = [_record_summary(records, ref) for ref in down_refs[:2]]
    summary = concise(
        "Mechanism candidate around "
        + shared_summary
        + ": "
        + " | ".join(summary for summary in l1_summaries if summary),
        260,
    )
    scope_refs = _scope_refs(root)
    payload = MapRecord(
        id="",
        scope=_map_scope(mode, scope),
        level="L2",
        map_kind="mechanism_cell",
        status="active",
        summary=summary,
        scope_refs=scope_refs,
        anchor_refs=(shared_ref,),
        derived_from_refs=(*down_refs, shared_ref),
        source_set_fingerprint=_sha256_payload(source_material),
        down_refs=down_refs,
        proof_routes=(
            {
                "route_kind": "map_l2_mechanism",
                "route_refs": [*down_refs, shared_ref],
                "required_drilldown": True,
            },
        ),
        signals={
            "inquiry_pressure": {"score": float(len(down_refs)), "source_signal": "shared_l1_anchor"},
            "promotion_pressure": {"score": 0.2, "target": "MODEL/FLOW only after proof drill-down and user-confirmed theory"},
        },
        generated_by=MAP_REFRESH_GENERATOR,
        generated_at=timestamp,
        updated_at=timestamp,
        stale_policy="source_set_changed",
        note="Navigation-only L2 mechanism cell derived from L1 evidence patches.",
    ).to_payload()
    for key in ("workspace_refs", "project_refs", "task_refs"):
        values = [str(ref) for ref in scope_refs.get(key, []) if str(ref)]
        if values:
            payload[key] = values
    return payload


def l2_candidates_from_existing_l1(
    root: Path,
    records: dict[str, dict],
    *,
    mode: str,
    scope: str,
    timestamp: str,
    limit: int,
) -> list[dict]:
    refs_to_maps: dict[str, list[dict]] = {}
    for map_record in _active_l1_maps_for_l2(records, mode=mode, scope=scope):
        for ref in sorted(set(_l2_anchor_refs(records, map_record))):
            refs_to_maps.setdefault(ref, []).append(map_record)
    candidates = []
    for shared_ref, l1_maps in sorted(refs_to_maps.items(), key=lambda item: (-len(item[1]), item[0])):
        if len(candidates) >= limit:
            break
        candidate = l2_candidate_from_l1_group(root, records, shared_ref, l1_maps, mode=mode, scope=scope, timestamp=timestamp)
        if candidate:
            candidates.append(candidate)
    return candidates


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


def _triggered_stale_map_refs(refresh_triggers: list[dict[str, Any]]) -> dict[str, list[str]]:
    reasons_by_ref: dict[str, list[str]] = {}
    for trigger in refresh_triggers:
        if str(trigger.get("record_type", "")) != "map":
            continue
        reason = str(trigger.get("reason", "")).strip()
        if reason not in {"map_has_terminal_anchor", "source_set_fingerprint_changed"}:
            continue
        record_ref = str(trigger.get("record_ref", "")).strip()
        if not record_ref:
            continue
        reasons_by_ref.setdefault(record_ref, []).append(reason)
    return {record_ref: sorted(set(reasons)) for record_ref, reasons in reasons_by_ref.items()}


def _link_l1_maps_to_l2(
    working_records: dict[str, dict],
    mutations: dict[str, dict],
    l2_record_id: str,
    down_refs: list[str],
    timestamp: str,
) -> list[str]:
    linked_refs = []
    for down_ref in down_refs:
        l1_record = working_records.get(down_ref)
        if not l1_record or l1_record.get("record_type") != "map":
            continue
        if str(l1_record.get("level", "")).strip() != "L1":
            continue
        existing_up_refs = _safe_list(l1_record, "up_refs")
        if l2_record_id in existing_up_refs:
            continue
        updated = public_record_payload(l1_record)
        updated["up_refs"] = sorted({*existing_up_refs, l2_record_id})
        updated["updated_at"] = timestamp
        mutations[down_ref] = updated
        working_records[down_ref] = updated
        linked_refs.append(down_ref)
    return linked_refs


def build_map_refresh_plan(
    root: Path,
    records: dict[str, dict],
    *,
    scope: str = "current",
    mode: str = "general",
    volume: str = "compact",
    limit: int = 5,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    refresh_triggers = map_refresh_triggers(root, records, scope=scope, mode=mode)
    attention_payload = load_attention_payload(root)
    if not attention_payload:
        return (
            {
                "map_refresh_is_proof": False,
                "attention_index_is_proof": False,
                "mode": mode,
                "scope": scope,
                "volume": volume,
                "limit": limit,
                "refresh_triggers": refresh_triggers,
                "refresh_trigger_count": len(refresh_triggers),
                "refresh_required": bool(refresh_triggers),
                "refresh_triggers_are_proof": False,
                "recommended_commands": map_refresh_recommended_commands(scope=scope, mode=mode),
            },
            [{"path": "", "reason": "attention_index_missing", "detail": "run attention-index build first"}],
        )
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
    candidates.extend(
        l2_candidates_from_existing_l1(
            root,
            records,
            mode=mode,
            scope=scope,
            timestamp=timestamp,
            limit=max(1, limit),
        )
    )

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
            if str(updated.get("level", "")).strip() == "L2":
                linked_refs = _link_l1_maps_to_l2(working_records, mutations, record_id, _safe_list(updated, "down_refs"), timestamp)
                if linked_refs:
                    updated_refs.extend(ref for ref in linked_refs if ref not in updated_refs)
                    planned_actions.append({"action": "link_l1_to_l2", "record_id": record_id, "down_refs": linked_refs})
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
        linked_down_refs = []
        if str(created.get("level", "")).strip() == "L2":
            linked_down_refs = _link_l1_maps_to_l2(working_records, mutations, record_id, _safe_list(created, "down_refs"), timestamp)
            updated_refs.extend(ref for ref in linked_down_refs if ref not in updated_refs)
        planned_actions.append(
            {
                "action": "create_map_cell",
                "record_id": record_id,
                "level": created["level"],
                "map_kind": created["map_kind"],
                "anchor_refs": created["anchor_refs"],
                **({"down_refs": linked_down_refs} if linked_down_refs else {}),
            }
        )

    for record_id, reasons in _triggered_stale_map_refs(refresh_triggers).items():
        existing = working_records.get(record_id)
        if not existing or existing.get("record_type") != "map":
            continue
        if str(existing.get("status", "")).strip() == "stale":
            continue
        stale = public_record_payload(existing)
        stale["status"] = "stale"
        stale["updated_at"] = timestamp
        mutations[record_id] = stale
        working_records[record_id] = stale
        if record_id in updated_refs:
            updated_refs.remove(record_id)
        if record_id not in stale_refs:
            stale_refs.append(record_id)
        if not any(action.get("action") == "mark_map_stale" and action.get("record_id") == record_id for action in planned_actions):
            planned_actions.append(
                {
                    "action": "mark_map_stale",
                    "record_id": record_id,
                    "trigger_reasons": reasons,
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
            "refresh_triggers": refresh_triggers,
            "refresh_trigger_count": len(refresh_triggers),
            "refresh_required": bool(refresh_triggers),
            "refresh_triggers_are_proof": False,
            "recommended_commands": map_refresh_recommended_commands(scope=scope, mode=mode),
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
        f"refresh triggers: `{payload.get('refresh_trigger_count', 0)}` required=`{payload.get('refresh_required', False)}`",
        "",
        "## Actions",
    ]
    for action in payload.get("planned_actions", []):
        lines.append(f"- {action.get('action')}: `{action.get('record_id')}`")
    if not payload.get("planned_actions"):
        lines.append("- none")
    triggers = payload.get("refresh_triggers", [])
    if triggers:
        lines.extend(["", "## Refresh Triggers"])
        for trigger in triggers[:8]:
            lines.append(f"- `{trigger.get('record_ref')}` {trigger.get('reason')}: {trigger.get('summary', '')}")
    lines.extend(["", str(payload.get("note", ""))])
    return lines
