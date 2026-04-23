"""Owner-bound WCTX map-session service."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .agent_identity import local_agent_owns_working_context, sign_working_context_payload
from .cli_common import public_record_payload, refresh_generated_outputs, validate_mutated_records
from .contracts import MapViewResponse
from .hydration import invalidate_hydration_state
from .ids import next_record_id, now_timestamp
from .io import context_write_lock, write_json_file
from .lookup_service import active_working_context_for_lookup, current_active_task_ref
from .notes import append_note
from .paths import record_path
from .reports import write_validation_report
from .scopes import current_project_ref, current_workspace_ref, project_refs_for_write, task_refs_for_write
from .search import concise
from .working_contexts import build_working_context_payload


DEFAULT_MAP_SESSION_KEY = "default"
MAP_SESSION_SUFFIX = "#map-session"


def _safe_list(data: dict, key: str) -> list[str]:
    values = data.get(key, [])
    if not isinstance(values, list):
        return []
    return [str(value).strip() for value in values if str(value).strip()]


def _map_session_ref(wctx_ref: str) -> str:
    return f"{wctx_ref}{MAP_SESSION_SUFFIX}"


def _parse_map_session_ref(session_ref: str) -> str:
    value = str(session_ref or "").strip()
    if not value:
        return ""
    if value.endswith(MAP_SESSION_SUFFIX):
        return value[: -len(MAP_SESSION_SUFFIX)]
    return value


def _tokenize(text: str) -> set[str]:
    return {token for token in re.findall(r"[a-z0-9]+", text.lower()) if len(token) >= 3}


def _record_summary(records: dict[str, dict], record_ref: str) -> str:
    record = records.get(record_ref, {})
    return concise(
        str(record.get("statement") or record.get("summary") or record.get("title") or record.get("note") or record_ref),
        180,
    )


def _record_item(records: dict[str, dict], record_ref: str, *, reason: str = "") -> dict[str, Any]:
    record = records.get(record_ref, {})
    return {
        "ref": record_ref,
        "record_type": str(record.get("record_type") or "unknown"),
        "summary": _record_summary(records, record_ref),
        "status": str(record.get("status") or record.get("critique_status") or ""),
        "reason": reason,
    }


def _scope_refs(record: dict) -> dict[str, list[str]]:
    scope_refs = record.get("scope_refs", {})
    if not isinstance(scope_refs, dict):
        scope_refs = {}
    return {
        "workspace_refs": sorted({*_safe_list(record, "workspace_refs"), *[str(ref) for ref in scope_refs.get("workspace_refs", []) if str(ref)]}),
        "project_refs": sorted({*_safe_list(record, "project_refs"), *[str(ref) for ref in scope_refs.get("project_refs", []) if str(ref)]}),
        "task_refs": sorted({*_safe_list(record, "task_refs"), *[str(ref) for ref in scope_refs.get("task_refs", []) if str(ref)]}),
        "wctx_refs": sorted({str(ref) for ref in scope_refs.get("wctx_refs", []) if str(ref)}),
    }


def _matches_current_focus(root: Path, records: dict[str, dict], record: dict, scope: str) -> bool:
    if scope == "all":
        return True
    refs = _scope_refs(record)
    workspace_ref = current_workspace_ref(root)
    project_ref = current_project_ref(root)
    task_ref = current_active_task_ref(root, records)
    if workspace_ref and refs["workspace_refs"] and workspace_ref not in refs["workspace_refs"]:
        return False
    if project_ref and refs["project_refs"] and project_ref not in refs["project_refs"]:
        return False
    if task_ref and refs["task_refs"] and task_ref not in refs["task_refs"]:
        return False
    return True


def _active_map_records(root: Path, records: dict[str, dict], *, scope: str) -> list[dict]:
    maps = [
        record
        for record in records.values()
        if record.get("record_type") == "map"
        and str(record.get("status", "active")).strip() == "active"
        and _matches_current_focus(root, records, record, scope)
    ]
    return sorted(maps, key=lambda item: str(item.get("updated_at", "")), reverse=True)


def _map_relevance(records: dict[str, dict], map_record: dict, query: str) -> int:
    tokens = _tokenize(query)
    text = " ".join(
        [
            str(map_record.get("summary", "")),
            str(map_record.get("map_kind", "")),
            " ".join(_record_summary(records, ref) for ref in _safe_list(map_record, "anchor_refs")),
            " ".join(_record_summary(records, ref) for ref in _safe_list(map_record, "derived_from_refs")[:5]),
            " ".join(_record_summary(records, ref) for ref in _safe_list(map_record, "down_refs")[:6]),
            " ".join(_record_summary(records, ref) for ref in _safe_list(map_record, "up_refs")[:4]),
        ]
    ).lower()
    score = sum(1 for token in tokens if token in text) if tokens else 0
    level = str(map_record.get("level") or "")
    if level == "L2" and _safe_list(map_record, "down_refs"):
        score += 3
    elif level == "L3":
        score += 2
    elif level == "L1" and _safe_list(map_record, "up_refs"):
        score += 1
    return score


def _zone_id(map_ref: str) -> str:
    return f"MZONE-{map_ref}"


def _map_ref_from_zone(target: str) -> str:
    value = str(target or "").strip()
    if value.startswith("MZONE-MAP-"):
        return value.removeprefix("MZONE-")
    return value


def _select_map_ref(root: Path, records: dict[str, dict], query: str, scope: str, preferred_ref: str = "") -> str:
    maps = _active_map_records(root, records, scope=scope)
    if preferred_ref and any(record.get("id") == preferred_ref for record in maps):
        return preferred_ref
    if not maps:
        return ""
    ranked = sorted(
        maps,
        key=lambda record: (_map_relevance(records, record, query), str(record.get("updated_at", ""))),
        reverse=True,
    )
    return str(ranked[0].get("id", ""))


def _session_for_wctx(wctx: dict) -> dict[str, Any] | None:
    sessions = wctx.get("map_sessions", {})
    if not isinstance(sessions, dict):
        return None
    session = sessions.get(DEFAULT_MAP_SESSION_KEY)
    return session if isinstance(session, dict) else None


def _with_session(wctx: dict, session: dict[str, Any], timestamp: str) -> dict:
    payload = public_record_payload(wctx)
    sessions = payload.get("map_sessions", {})
    if not isinstance(sessions, dict):
        sessions = {}
    sessions[DEFAULT_MAP_SESSION_KEY] = session
    payload["map_sessions"] = sessions
    payload["updated_at"] = timestamp
    return payload


def _persist_wctx(root: Path, records: dict[str, dict], wctx_payload: dict, *, reason: str, timestamp: str) -> tuple[dict | None, str | None]:
    if not wctx_payload.get("workspace_refs"):
        workspace_ref = current_workspace_ref(root)
        if workspace_ref:
            wctx_payload["workspace_refs"] = [workspace_ref]
    signed, agent_record = sign_working_context_payload(root, records, wctx_payload, timestamp=timestamp)
    mutations: dict[str, dict] = {str(signed["id"]): signed, str(agent_record["id"]): agent_record}
    for task_ref in _safe_list(signed, "task_refs"):
        task = records.get(task_ref)
        if not task or task.get("record_type") != "task":
            continue
        task_payload = public_record_payload(task)
        task_payload["working_context_refs"] = sorted({*_safe_list(task_payload, "working_context_refs"), str(signed["id"])})
        task_payload["updated_at"] = timestamp
        task_payload["note"] = append_note(str(task_payload.get("note", "")), f"[{timestamp}] linked working_context {signed['id']}")
        mutations[task_ref] = task_payload

    with context_write_lock(root):
        merged, errors = validate_mutated_records(root, records, mutations)
        if errors:
            return None, "; ".join(f"{error.path}: {error.message}" for error in errors)
        for record_id, record_payload in mutations.items():
            record_type = str(record_payload.get("record_type", "")).strip()
            write_json_file(record_path(root, record_type, record_id), record_payload)
        write_validation_report(root, [])
        refresh_generated_outputs(root, merged)
        invalidate_hydration_state(root, reason)
    return signed, None


def _current_or_new_wctx(root: Path, records: dict[str, dict], query: str, mode: str, timestamp: str) -> tuple[dict | None, str | None]:
    project_ref = current_project_ref(root)
    task_ref = current_active_task_ref(root, records)
    existing = active_working_context_for_lookup(root, records, project_ref, task_ref)
    if existing:
        return public_record_payload(existing), None
    workspace_ref = current_workspace_ref(root)
    if not workspace_ref:
        return None, "map_open requires an active workspace before creating a WCTX map session"
    payload = build_working_context_payload(
        record_id=next_record_id(records, "WCTX-"),
        timestamp=timestamp,
        scope="map.session",
        title=concise(f"Map session: {query or mode}", 120),
        context_kind="investigation",
        pinned_refs=[],
        focus_paths=[],
        topic_terms=sorted(_tokenize(query))[:12],
        topic_seed_refs=[],
        assumptions=[],
        concerns=["MAP session is navigation only; proof requires drill-down."],
        project_refs=project_refs_for_write(root, []),
        task_refs=task_refs_for_write(root, []) if task_ref else [],
        tags=["map-session"],
        note="Auto-created owner-bound WCTX map session.",
    )
    payload["workspace_refs"] = [workspace_ref]
    return payload, None


def _new_session(wctx_ref: str, query: str, mode: str, scope: str, selected_map_ref: str, timestamp: str) -> dict[str, Any]:
    return {
        "session_ref": _map_session_ref(wctx_ref),
        "session_key": DEFAULT_MAP_SESSION_KEY,
        "query": query,
        "mode": mode,
        "scope": scope,
        "current_zone_id": _zone_id(selected_map_ref) if selected_map_ref else "MZONE-scope",
        "selected_map_ref": selected_map_ref,
        "visited_map_refs": [selected_map_ref] if selected_map_ref else [],
        "inspected_refs": [],
        "dismissed_refs": [],
        "deferred_refs": [],
        "checkpoints": [],
        "opened_at": timestamp,
        "updated_at": timestamp,
        "map_session_is_proof": False,
    }


def _zone_for_map(records: dict[str, dict], map_record: dict | None, session: dict) -> dict[str, Any]:
    if not map_record:
        return {
            "id": "MZONE-scope",
            "kind": "scope",
            "summary": "No durable MAP-* cell selected. Run map_refresh to materialize navigation cells.",
        }
    return {
        "id": _zone_id(str(map_record.get("id", ""))),
        "kind": str(map_record.get("map_kind") or "topic"),
        "level": str(map_record.get("level") or ""),
        "map_ref": str(map_record.get("id") or ""),
        "summary": concise(str(map_record.get("summary") or ""), 260),
        "status": str(map_record.get("status") or ""),
        "source_set_fingerprint": str(map_record.get("source_set_fingerprint") or ""),
    }


def _signal_lists(records: dict[str, dict], map_record: dict | None, ignored: list[dict]) -> dict[str, list[dict[str, Any]]]:
    if not map_record:
        return {"tap_smell": [], "neglect_pressure": ignored[:5], "inquiry_pressure": [], "promotion_pressure": []}
    signals = map_record.get("signals", {})
    if not isinstance(signals, dict):
        signals = {}
    anchors = _safe_list(map_record, "anchor_refs")
    tap = signals.get("tap_smell", {}) if isinstance(signals.get("tap_smell"), dict) else {}
    curiosity = signals.get("curiosity", {}) if isinstance(signals.get("curiosity"), dict) else {}
    return {
        "tap_smell": [
            {"ref": ref, "score": float(tap.get("score", 0.0) or 0.0), "summary": _record_summary(records, ref)}
            for ref in anchors
            if tap or anchors
        ][:5],
        "neglect_pressure": ignored[:5],
        "inquiry_pressure": [
            {"ref": ref, "score": float(curiosity.get("score", 0.0) or 0.0), "summary": _record_summary(records, ref)}
            for ref in anchors
            if curiosity
        ][:5],
        "promotion_pressure": [
            {"ref": str(map_record.get("id")), "score": 0.2, "summary": "L1 map cell may be promoted into L2/MODEL/FLOW if repeatedly useful."}
        ]
        if str(map_record.get("level")) == "L1"
        else [],
    }


def _map_cell_item(records: dict[str, dict], map_record: dict, *, reason: str) -> dict[str, Any]:
    return {
        "ref": str(map_record.get("id") or ""),
        "level": str(map_record.get("level") or ""),
        "map_kind": str(map_record.get("map_kind") or ""),
        "summary": concise(str(map_record.get("summary") or ""), 180),
        "status": str(map_record.get("status") or ""),
        "reason": reason,
        "map_is_proof": False,
    }


def build_map_view_payload(root: Path, records: dict[str, dict], wctx: dict, session: dict[str, Any]) -> dict[str, Any]:
    scope = str(session.get("scope") or "current")
    selected_map_ref = str(session.get("selected_map_ref") or "")
    map_records = {str(record.get("id")): record for record in _active_map_records(root, records, scope=scope)}
    current_map = map_records.get(selected_map_ref)
    anchor_refs = _safe_list(current_map or {}, "anchor_refs")
    derived_refs = [ref for ref in _safe_list(current_map or {}, "derived_from_refs") if ref not in anchor_refs]
    bridge_refs = []
    if current_map:
        for key in ("adjacent_map_refs", "up_refs", "down_refs", "refines_map_refs"):
            bridge_refs.extend(_safe_list(current_map, key))
    up_cells = [
        _map_cell_item(records, map_records[ref], reason="higher abstraction")
        for ref in _safe_list(current_map or {}, "up_refs")
        if ref in map_records
    ][:6]
    down_cells = [
        _map_cell_item(records, map_records[ref], reason="lower evidence patch")
        for ref in _safe_list(current_map or {}, "down_refs")
        if ref in map_records
    ][:6]
    ignored_refs = []
    for record in map_records.values():
        if record.get("id") == selected_map_ref:
            continue
        ignored_refs.extend([ref for ref in _safe_list(record, "anchor_refs") if ref not in anchor_refs])
    ignored = [_record_item(records, ref, reason="connected low-focus map anchor") for ref in ignored_refs[:8]]
    allowed_moves = [
        {
            "move": "zone",
            "target": _zone_id(str(record.get("id"))),
            "map_ref": str(record.get("id")),
            "summary": concise(str(record.get("summary") or ""), 160),
        }
        for record in list(map_records.values())[:8]
        if str(record.get("id")) != selected_map_ref
    ]
    allowed_moves.extend(
        {"move": "drilldown", "target": ref, "tool": "map_drilldown", "summary": _record_summary(records, ref)}
        for ref in anchor_refs[:6]
    )
    allowed_moves.append({"move": "checkpoint", "target": str(session.get("current_zone_id") or ""), "tool": "map_checkpoint"})
    if not map_records:
        allowed_moves.append({"move": "refresh", "tool": "map_refresh", "summary": "Materialize durable MAP-* cells."})

    view = MapViewResponse(
        map_session_ref=str(session.get("session_ref") or _map_session_ref(str(wctx.get("id")))),
        zone=_zone_for_map(records, current_map, session),
        anchor_facts=[_record_item(records, ref, reason="map anchor") for ref in anchor_refs],
        ignored_but_relevant=ignored,
        bridge_facts=[_record_item(records, ref, reason="map bridge") for ref in [*derived_refs[:4], *bridge_refs[:4]]],
        tension_facts=[_record_item(records, ref, reason="map tension") for ref in _safe_list(current_map or {}, "tension_refs")],
        signals=_signal_lists(records, current_map, ignored),
        allowed_moves=allowed_moves,
        proof_routes=list((current_map or {}).get("proof_routes", [])) if isinstance((current_map or {}).get("proof_routes", []), list) else [],
    ).to_payload()
    view["mode"] = str(session.get("mode") or "general")
    view["scope"] = scope
    view["query"] = str(session.get("query") or "")
    view["wctx_ref"] = str(wctx.get("id") or "")
    view["visited_map_refs"] = _safe_list(session, "visited_map_refs")
    view["checkpoint_count"] = len(session.get("checkpoints", [])) if isinstance(session.get("checkpoints"), list) else 0
    view["hierarchy"] = {
        "hierarchy_is_proof": False,
        "up_cells": up_cells,
        "down_cells": down_cells,
    }
    view["recommended_next"] = ["map_drilldown"] if anchor_refs else ["map_refresh"]
    return view


def map_open_service(
    root: Path,
    records: dict[str, dict],
    *,
    query: str,
    mode: str = "general",
    scope: str = "current",
) -> tuple[dict[str, Any] | None, str | None]:
    timestamp = now_timestamp()
    wctx, error = _current_or_new_wctx(root, records, query, mode, timestamp)
    if error:
        return None, error
    assert wctx is not None
    if wctx.get("id") in records and not local_agent_owns_working_context(root, wctx):
        return None, f"{wctx.get('id')} is owned by another local agent; fork/adopt before using its map session"
    selected = _select_map_ref(root, records, query, scope)
    session = _new_session(str(wctx["id"]), query, mode, scope, selected, timestamp)
    payload = _with_session(wctx, session, timestamp)
    signed, error = _persist_wctx(root, records, payload, reason=f"opened map session {wctx['id']}", timestamp=timestamp)
    if error:
        return None, error
    assert signed is not None
    view_records = dict(records)
    view_records[str(signed["id"])] = signed
    return build_map_view_payload(root, view_records, signed, session), None


def map_view_service(
    root: Path,
    records: dict[str, dict],
    *,
    session_ref: str = "",
) -> tuple[dict[str, Any] | None, str | None]:
    wctx_ref = _parse_map_session_ref(session_ref)
    wctx = records.get(wctx_ref) if wctx_ref else None
    if not wctx:
        project_ref = current_project_ref(root)
        task_ref = current_active_task_ref(root, records)
        wctx = active_working_context_for_lookup(root, records, project_ref, task_ref)
    if not wctx or wctx.get("record_type") != "working_context":
        return None, "map_view requires an existing owner-bound WCTX map session; run map_open first"
    if not local_agent_owns_working_context(root, wctx):
        return None, f"{wctx.get('id')} is owned by another local agent; fork/adopt before using its map session"
    session = _session_for_wctx(wctx)
    if not session:
        return None, f"{wctx.get('id')} has no map session; run map_open first"
    return build_map_view_payload(root, records, wctx, session), None


def map_move_service(
    root: Path,
    records: dict[str, dict],
    *,
    session_ref: str,
    target: str,
) -> tuple[dict[str, Any] | None, str | None]:
    wctx_ref = _parse_map_session_ref(session_ref)
    wctx = records.get(wctx_ref)
    if not wctx or wctx.get("record_type") != "working_context":
        return None, f"missing working_context map session {session_ref}"
    if not local_agent_owns_working_context(root, wctx):
        return None, f"{wctx_ref} is owned by another local agent; fork/adopt before using its map session"
    session = _session_for_wctx(wctx)
    if not session:
        return None, f"{wctx_ref} has no map session; run map_open first"
    map_ref = _map_ref_from_zone(target)
    if map_ref not in records or records[map_ref].get("record_type") != "map":
        return None, f"map_move target must be a MAP-* ref or MZONE-MAP-* zone: {target}"
    timestamp = now_timestamp()
    moved = dict(session)
    moved["selected_map_ref"] = map_ref
    moved["current_zone_id"] = _zone_id(map_ref)
    moved["visited_map_refs"] = sorted({*_safe_list(moved, "visited_map_refs"), map_ref})
    moved["updated_at"] = timestamp
    payload = _with_session(wctx, moved, timestamp)
    signed, error = _persist_wctx(root, records, payload, reason=f"moved map session {wctx_ref}", timestamp=timestamp)
    if error:
        return None, error
    assert signed is not None
    view_records = dict(records)
    view_records[str(signed["id"])] = signed
    return build_map_view_payload(root, view_records, signed, moved), None


def _map_proof_routes(record: dict, *, source_map_ref: str, via_map_refs: list[str] | None = None) -> list[dict[str, Any]]:
    routes = record.get("proof_routes", []) if isinstance(record.get("proof_routes"), list) else []
    enriched = []
    for route in routes:
        if not isinstance(route, dict):
            continue
        payload = dict(route)
        payload["source_map_ref"] = source_map_ref
        payload["via_map_refs"] = list(via_map_refs or [])
        payload["route_is_proof"] = False
        enriched.append(payload)
    return enriched


def _expanded_map_proof_routes(
    records: dict[str, dict],
    map_record: dict,
    *,
    visited: set[str] | None = None,
    depth: int = 0,
) -> list[dict[str, Any]]:
    map_ref = str(map_record.get("id", "")).strip()
    if not map_ref:
        return []
    visited = set(visited or set())
    if map_ref in visited or depth > 3:
        return []
    visited.add(map_ref)
    routes = _map_proof_routes(map_record, source_map_ref=map_ref)
    for down_ref in _safe_list(map_record, "down_refs"):
        child = records.get(down_ref)
        if not child or child.get("record_type") != "map":
            continue
        routes.append(
            {
                "route_kind": "map_down_ref",
                "route_refs": [map_ref, down_ref],
                "source_map_ref": map_ref,
                "via_map_refs": [down_ref],
                "required_drilldown": True,
                "route_is_proof": False,
            }
        )
        for child_route in _expanded_map_proof_routes(records, child, visited=visited, depth=depth + 1):
            expanded = dict(child_route)
            expanded["via_map_refs"] = [down_ref, *[ref for ref in child_route.get("via_map_refs", []) if ref != down_ref]]
            expanded["expanded_from_map_ref"] = map_ref
            expanded["route_is_proof"] = False
            routes.append(expanded)
    return routes


def _map_hierarchy_payload(records: dict[str, dict], map_record: dict) -> dict[str, Any]:
    return {
        "hierarchy_is_proof": False,
        "up_cells": [
            _map_cell_item(records, records[ref], reason="higher abstraction")
            for ref in _safe_list(map_record, "up_refs")
            if ref in records and records[ref].get("record_type") == "map"
        ][:8],
        "down_cells": [
            _map_cell_item(records, records[ref], reason="lower evidence patch")
            for ref in _safe_list(map_record, "down_refs")
            if ref in records and records[ref].get("record_type") == "map"
        ][:8],
    }


def map_drilldown_service(
    root: Path,
    records: dict[str, dict],
    *,
    session_ref: str,
    record_ref: str,
) -> tuple[dict[str, Any] | None, str | None]:
    view, error = map_view_service(root, records, session_ref=session_ref)
    if error:
        return None, error
    assert view is not None
    ref = str(record_ref or "").strip()
    if not ref:
        return None, "map_drilldown requires a record ref"
    record = records.get(ref)
    if not record:
        return None, f"missing record {ref}"
    routes: list[dict[str, Any]] = []
    hierarchy = {"hierarchy_is_proof": False, "up_cells": [], "down_cells": []}
    if record.get("record_type") == "map":
        routes = _expanded_map_proof_routes(records, record)
        hierarchy = _map_hierarchy_payload(records, record)
    else:
        for map_record in _active_map_records(root, records, scope=str(view.get("scope") or "current")):
            route_refs = []
            for route in map_record.get("proof_routes", []) if isinstance(map_record.get("proof_routes"), list) else []:
                if ref in [str(item) for item in route.get("route_refs", [])]:
                    enriched = dict(route)
                    enriched["source_map_ref"] = str(map_record.get("id") or "")
                    enriched["via_map_refs"] = []
                    enriched["route_is_proof"] = False
                    routes.append(enriched)
                    route_refs.extend([str(item) for item in route.get("route_refs", [])])
            if ref in _safe_list(map_record, "anchor_refs") or ref in route_refs:
                routes.append(
                    {
                        "route_kind": "map_cell_anchor",
                        "route_refs": [str(map_record.get("id")), ref],
                        "source_map_ref": str(map_record.get("id")),
                        "via_map_refs": [],
                        "required_drilldown": True,
                        "route_is_proof": False,
                    }
                )
    return (
        {
            "contract_version": "0.4",
            "drilldown_is_proof": False,
            "map_is_proof": False,
            "map_session_ref": str(view.get("map_session_ref") or ""),
            "ref": ref,
            "record": _record_item(records, ref, reason="map drilldown target"),
            "proof_routes": routes,
            "hierarchy": hierarchy,
            "required_next": ["record_detail", "augment_chain", "validate_chain"],
            "note": "Drilldown routes are navigation only until chain validation succeeds.",
        },
        None,
    )


def map_checkpoint_service(
    root: Path,
    records: dict[str, dict],
    *,
    session_ref: str,
    note: str = "",
) -> tuple[dict[str, Any] | None, str | None]:
    wctx_ref = _parse_map_session_ref(session_ref)
    wctx = records.get(wctx_ref)
    if not wctx or wctx.get("record_type") != "working_context":
        return None, f"missing working_context map session {session_ref}"
    if not local_agent_owns_working_context(root, wctx):
        return None, f"{wctx_ref} is owned by another local agent; fork/adopt before using its map session"
    session = _session_for_wctx(wctx)
    if not session:
        return None, f"{wctx_ref} has no map session; run map_open first"
    timestamp = now_timestamp()
    checkpoint = {
        "timestamp": timestamp,
        "zone_id": str(session.get("current_zone_id") or ""),
        "selected_map_ref": str(session.get("selected_map_ref") or ""),
        "note": note.strip(),
        "checkpoint_is_proof": False,
    }
    updated = dict(session)
    checkpoints = updated.get("checkpoints", [])
    if not isinstance(checkpoints, list):
        checkpoints = []
    updated["checkpoints"] = [*checkpoints, checkpoint]
    updated["updated_at"] = timestamp
    payload = _with_session(wctx, updated, timestamp)
    signed, error = _persist_wctx(root, records, payload, reason=f"checkpointed map session {wctx_ref}", timestamp=timestamp)
    if error:
        return None, error
    assert signed is not None
    view_records = dict(records)
    view_records[str(signed["id"])] = signed
    view = build_map_view_payload(root, view_records, signed, updated)
    view["checkpoint"] = checkpoint
    return view, None


def map_view_text_lines(payload: dict[str, Any]) -> list[str]:
    zone = payload.get("zone", {}) if isinstance(payload.get("zone"), dict) else {}
    lines = [
        "# MAP View",
        "",
        "Mode: owner-bound WCTX map session. Navigation only; not proof.",
        f"session: `{payload.get('map_session_ref', '')}` zone: `{zone.get('id', '')}` kind: `{zone.get('kind', '')}`",
        f"summary: {zone.get('summary', '')}",
        "",
        "## Anchor Facts",
    ]
    for item in payload.get("anchor_facts", [])[:8]:
        lines.append(f"- `{item.get('ref')}` {item.get('summary')}")
    if not payload.get("anchor_facts"):
        lines.append("- none")
    lines.append("")
    lines.append("## Allowed Moves")
    for move in payload.get("allowed_moves", [])[:10]:
        lines.append(f"- {move.get('move')}: `{move.get('target', move.get('tool', ''))}` {move.get('summary', '')}")
    return lines


def map_drilldown_text_lines(payload: dict[str, Any]) -> list[str]:
    record = payload.get("record", {}) if isinstance(payload.get("record"), dict) else {}
    lines = [
        "# MAP Drilldown",
        "",
        "Mode: route discovery only. Not proof.",
        f"session: `{payload.get('map_session_ref', '')}` ref: `{payload.get('ref', '')}`",
        f"record: `{record.get('record_type', '')}` {record.get('summary', '')}",
        "",
        "## Proof Routes",
    ]
    for route in payload.get("proof_routes", []):
        lines.append(f"- {route.get('route_kind')}: {route.get('route_refs', [])}")
    if not payload.get("proof_routes"):
        lines.append("- none")
    lines.append("")
    lines.append(str(payload.get("note", "")))
    return lines
