"""Generated attention-map and curiosity helpers.

Attention data is navigation only. It helps an agent decide what to inspect
next; it must not support claims or justify actions.
"""

from __future__ import annotations

import json
import math
from datetime import datetime
from pathlib import Path

from .ids import now_timestamp
from .io import write_json_file, write_text_file
from .links import collect_link_edges
from .search import public_record_summary


TAP_KINDS = {"retrieved", "opened", "cited", "decisive", "updated", "challenged", "contradicted"}
TAP_WEIGHTS = {
    "retrieved": 0.5,
    "opened": 1.0,
    "cited": 2.0,
    "decisive": 3.0,
    "updated": 2.0,
    "challenged": 2.5,
    "contradicted": 3.0,
}
ACCESS_WEIGHTS = {
    "record_search": 0.2,
    "claim_graph": 0.6,
    "record_detail": 1.0,
    "linked_records": 0.8,
    "raw_claim_read": 2.0,
}
DEFAULT_HALF_LIFE_DAYS = 7.0
ATTENTION_SCOPES = {"current", "all"}
PROBE_RECORD_TYPE_WEIGHTS = {
    "claim": 5,
    "model": 4,
    "flow": 4,
    "open_question": 3,
    "proposal": 3,
    "plan": 2,
    "debt": 2,
}
PROBE_RECORD_TYPES = set(PROBE_RECORD_TYPE_WEIGHTS)


def activity_root(root: Path) -> Path:
    return root / "activity"


def tap_log_path(root: Path) -> Path:
    return activity_root(root) / "taps.jsonl"


def attention_index_root(root: Path) -> Path:
    return root / "attention_index"


def attention_index_paths(root: Path) -> dict[str, Path]:
    base = attention_index_root(root)
    return {
        "records": base / "records.json",
        "clusters": base / "clusters.json",
        "bridges": base / "bridges.json",
        "cold_zones": base / "cold_zones.json",
        "probes": base / "probes.json",
        "summary": base / "summary.md",
    }


def parse_timestamp(value: str) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def decayed_weight(
    timestamp: str,
    kind: str,
    generated_at: str,
    half_life_days: float = DEFAULT_HALF_LIFE_DAYS,
    weights: dict[str, float] | None = None,
) -> float:
    base = (weights or TAP_WEIGHTS).get(kind, 0.5)
    event_time = parse_timestamp(timestamp)
    current_time = parse_timestamp(generated_at)
    if event_time is None or current_time is None:
        return base
    age_days = max(0.0, (current_time - event_time).total_seconds() / 86400.0)
    return base * math.exp(-age_days / max(0.1, half_life_days))


def load_tap_events(root: Path) -> tuple[list[dict], list[str]]:
    path = tap_log_path(root)
    if not path.exists():
        return [], []
    events: list[dict] = []
    errors: list[str] = []
    with path.open(encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                item = json.loads(stripped)
            except json.JSONDecodeError as exc:
                errors.append(f"{path}: line {line_no}: invalid JSON: {exc}")
                continue
            if not isinstance(item, dict):
                errors.append(f"{path}: line {line_no}: tap event must be an object")
                continue
            events.append(item)
    return events, errors


def append_tap_event(root: Path, event: dict) -> None:
    path = tap_log_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False, sort_keys=True))
        handle.write("\n")


def top_topic_id(topic_item: dict) -> str:
    topics = topic_item.get("topics", [])
    if not isinstance(topics, list) or not topics:
        return ""
    return str(topics[0].get("topic_id", "")).strip() if isinstance(topics[0], dict) else ""


def top_topic_term(topic_item: dict) -> str:
    topics = topic_item.get("topics", [])
    if not isinstance(topics, list) or not topics:
        return ""
    return str(topics[0].get("term", "")).strip() if isinstance(topics[0], dict) else ""


def link_pairs(records: dict[str, dict]) -> set[tuple[str, str]]:
    pairs: set[tuple[str, str]] = set()
    for edge in collect_link_edges(records):
        left, right = sorted([str(edge.get("from", "")), str(edge.get("to", ""))])
        if left and right:
            pairs.add((left, right))
    return pairs


def sorted_pair(left: str, right: str) -> tuple[str, str]:
    return tuple(sorted([left, right]))


def list_refs(data: dict, key: str) -> list[str]:
    return [str(ref).strip() for ref in data.get(key, []) if str(ref).strip()]


def record_focus_score(data: dict, *, workspace_ref: str = "", project_ref: str = "", task_ref: str = "") -> int:
    score = 0
    record_id = str(data.get("id", "")).strip()
    if workspace_ref and (record_id == workspace_ref or workspace_ref in list_refs(data, "workspace_refs")):
        score += 2
    if project_ref and (record_id == project_ref or project_ref in list_refs(data, "project_refs")):
        score += 3
    if task_ref and (record_id == task_ref or task_ref in list_refs(data, "task_refs")):
        score += 4
    return score


def record_matches_focus(data: dict, *, workspace_ref: str = "", project_ref: str = "", task_ref: str = "") -> bool:
    record_id = str(data.get("id", "")).strip()
    if task_ref and (record_id == task_ref or task_ref in list_refs(data, "task_refs")):
        return True
    if project_ref:
        return record_id == project_ref or project_ref in list_refs(data, "project_refs")
    if workspace_ref:
        return record_id == workspace_ref or workspace_ref in list_refs(data, "workspace_refs")
    return True


def probe_record_weight(record: dict) -> int:
    return PROBE_RECORD_TYPE_WEIGHTS.get(str(record.get("record_type", "")).strip(), 1)


def probe_candidate(record: dict) -> bool:
    return str(record.get("record_type", "")).strip() in PROBE_RECORD_TYPES


def probe_score(left: dict, right: dict, cluster: dict) -> float:
    type_score = probe_record_weight(left) + probe_record_weight(right)
    focus_score = int(left.get("focus_score", 0)) + int(right.get("focus_score", 0))
    activity_score = float(left.get("activity_score", 0.0)) + float(right.get("activity_score", 0.0))
    cold_bonus = 2.0 if float(cluster.get("activity_score", 0.0)) < 1.0 else 0.0
    return round(type_score + focus_score + cold_bonus + min(activity_score, 3.0), 4)


def build_probe(left_id: str, right_id: str, topic_id: str, cluster: dict, record_items: dict[str, dict]) -> dict:
    left = record_items[left_id]
    right = record_items[right_id]
    score = probe_score(left, right, cluster)
    is_cold = float(cluster.get("activity_score", 0.0)) < 1.0
    reason = (
        "records share a cold semantic cluster but no established direct link"
        if is_cold
        else "records share a focused semantic cluster but no established direct link"
    )
    return {
        "record_refs": [left_id, right_id],
        "cluster_refs": [topic_id],
        "sampling_method": "deterministic-cold-zone-pair",
        "score": score,
        "score_is_proof": False,
        "reason": reason,
        "explanation": (
            f"Inspect whether `{left_id}` and `{right_id}` should be linked: "
            f"topic=`{cluster.get('term', '')}`, pair_score={score}, navigation_only=true."
        ),
        "link_state": "candidate",
        "attention_index_is_proof": False,
    }


def generate_cluster_probes(
    clusters: dict[str, dict],
    record_items: dict[str, dict],
    established_pairs: set[tuple[str, str]],
    *,
    probe_limit: int,
) -> list[dict]:
    candidates = []
    seen_pairs: set[tuple[str, str]] = set()
    ordered_clusters = sorted(
        clusters.values(),
        key=lambda item: (float(item.get("activity_score", 0.0)), -int(item.get("record_count", 0)), str(item.get("term", ""))),
    )
    for cluster in ordered_clusters:
        topic_id = str(cluster.get("id", ""))
        member_ids = [
            record_id
            for record_id in cluster.get("top_records", [])
            if record_id in record_items and probe_candidate(record_items[record_id])
        ]
        for index, left in enumerate(member_ids):
            for right in member_ids[index + 1 :]:
                pair = sorted_pair(left, right)
                if pair in established_pairs or pair in seen_pairs:
                    continue
                seen_pairs.add(pair)
                candidates.append(build_probe(left, right, topic_id, cluster, record_items))
    candidates.sort(key=lambda item: (-float(item.get("score", 0.0)), item.get("record_refs", [])))
    return candidates[: max(1, probe_limit)]


def build_attention_index(
    records: dict[str, dict],
    topic_payload: dict,
    taps: list[dict],
    *,
    access_events: list[dict] | None = None,
    probe_limit: int = 20,
) -> dict:
    generated_at = now_timestamp()
    topic_records = topic_payload.get("records", {}) if isinstance(topic_payload.get("records"), dict) else {}
    topics = topic_payload.get("topics", {}) if isinstance(topic_payload.get("topics"), dict) else {}
    by_topic = topic_payload.get("by_topic", {}) if isinstance(topic_payload.get("by_topic"), dict) else {}

    tap_scores: dict[str, float] = {}
    tap_counts: dict[str, int] = {}
    for tap in taps:
        record_ref = str(tap.get("record_ref", "")).strip()
        if record_ref not in records:
            continue
        kind = str(tap.get("kind", "")).strip()
        tap_scores[record_ref] = tap_scores.get(record_ref, 0.0) + decayed_weight(str(tap.get("tapped_at", "")), kind, generated_at)
        tap_counts[record_ref] = tap_counts.get(record_ref, 0) + 1

    access_scores: dict[str, float] = {}
    access_counts: dict[str, int] = {}
    for event in access_events or []:
        refs = event.get("record_refs", [])
        if not isinstance(refs, list):
            refs = []
        kind = str(event.get("access_kind", "")).strip()
        accessed_at = str(event.get("accessed_at", ""))
        base_kind = kind if kind in ACCESS_WEIGHTS else "record_detail"
        for record_ref in sorted({str(ref).strip() for ref in refs if str(ref).strip()}):
            if record_ref not in records:
                continue
            access_scores[record_ref] = access_scores.get(record_ref, 0.0) + decayed_weight(
                accessed_at,
                base_kind,
                generated_at,
                weights=ACCESS_WEIGHTS,
            )
            access_counts[record_ref] = access_counts.get(record_ref, 0) + 1

    record_items = {}
    for record_id, data in records.items():
        topic_item = topic_records.get(record_id, {}) if isinstance(topic_records.get(record_id, {}), dict) else {}
        record_items[record_id] = {
            "id": record_id,
            "record_type": str(data.get("record_type", "")).strip(),
            "summary": public_record_summary(data),
            "activity_score": round(tap_scores.get(record_id, 0.0) + access_scores.get(record_id, 0.0), 4),
            "tap_count": tap_counts.get(record_id, 0),
            "access_count": access_counts.get(record_id, 0),
            "top_topic_id": top_topic_id(topic_item),
            "top_topic_term": top_topic_term(topic_item),
            "workspace_refs": list_refs(data, "workspace_refs"),
            "project_refs": list_refs(data, "project_refs"),
            "task_refs": list_refs(data, "task_refs"),
            "attention_index_is_proof": False,
        }

    clusters = {}
    for topic_id, topic in topics.items():
        members = by_topic.get(topic_id, []) if isinstance(by_topic.get(topic_id, []), list) else []
        member_ids = [str(member.get("id", "")) for member in members if isinstance(member, dict) and str(member.get("id", "")) in records]
        activity = sum(tap_scores.get(record_id, 0.0) + access_scores.get(record_id, 0.0) for record_id in member_ids)
        access_count = sum(access_counts.get(record_id, 0) for record_id in member_ids)
        clusters[topic_id] = {
            "id": topic_id,
            "term": topic.get("term", ""),
            "record_count": len(member_ids),
            "activity_score": round(activity, 4),
            "access_count": access_count,
            "record_refs": member_ids,
            "top_records": member_ids[:8],
            "attention_index_is_proof": False,
        }

    cold_zones = sorted(
        [
            {
                "topic_id": cluster["id"],
                "term": cluster["term"],
                "record_count": cluster["record_count"],
                "activity_score": cluster["activity_score"],
                "reason": "cluster has multiple semantically grouped records but little or no tap activity",
                "attention_index_is_proof": False,
            }
            for cluster in clusters.values()
            if cluster["record_count"] >= 2 and cluster["activity_score"] < 1.0
        ],
        key=lambda item: (-item["record_count"], item["term"], item["topic_id"]),
    )

    bridges = []
    for edge in collect_link_edges(records):
        left = str(edge.get("from", ""))
        right = str(edge.get("to", ""))
        left_topic = record_items.get(left, {}).get("top_topic_id", "")
        right_topic = record_items.get(right, {}).get("top_topic_id", "")
        if not left_topic or not right_topic or left_topic == right_topic:
            continue
        bridges.append(
            {
                "from": left,
                "to": right,
                "from_topic": left_topic,
                "to_topic": right_topic,
                "fields": edge.get("fields", []),
                "link_state": "established",
                "attention_index_is_proof": False,
            }
        )

    established_pairs = link_pairs(records)
    cold_clusters = {zone["topic_id"]: clusters[zone["topic_id"]] for zone in cold_zones if zone["topic_id"] in clusters}
    probes = generate_cluster_probes(cold_clusters, record_items, established_pairs, probe_limit=probe_limit)

    return {
        "attention_index_is_proof": False,
        "generated_at": generated_at,
        "tap_count": len(taps),
        "access_event_count": len(access_events or []),
        "record_count": len(record_items),
        "cluster_count": len(clusters),
        "records": record_items,
        "clusters": clusters,
        "bridges": bridges[: max(1, probe_limit)],
        "established_pairs": [list(pair) for pair in sorted(established_pairs)],
        "cold_zones": cold_zones[: max(1, probe_limit)],
        "probes": probes[: max(1, probe_limit)],
        "note": "Generated attention/curiosity navigation data. Not proof.",
    }


def filter_attention_payload(
    payload: dict,
    *,
    scope: str = "current",
    workspace_ref: str = "",
    project_ref: str = "",
    task_ref: str = "",
) -> dict:
    if scope == "all" or not any([workspace_ref, project_ref, task_ref]):
        return {**payload, "scope": "all"}

    records = payload.get("records", {}) if isinstance(payload.get("records"), dict) else {}
    kept_records = {
        record_id: {**record, "focus_score": record_focus_score(record, workspace_ref=workspace_ref, project_ref=project_ref, task_ref=task_ref)}
        for record_id, record in records.items()
        if isinstance(record, dict)
        and record_matches_focus(record, workspace_ref=workspace_ref, project_ref=project_ref, task_ref=task_ref)
    }
    kept_ids = set(kept_records)

    clusters = {}
    for topic_id, cluster in (payload.get("clusters", {}) or {}).items():
        if not isinstance(cluster, dict):
            continue
        source_refs = cluster.get("record_refs") or cluster.get("top_records") or []
        member_ids = [str(record_id) for record_id in source_refs if str(record_id) in kept_ids]
        if not member_ids:
            continue
        activity = sum(float(kept_records[record_id].get("activity_score", 0.0)) for record_id in member_ids)
        clusters[topic_id] = {
            **cluster,
            "record_refs": member_ids,
            "top_records": member_ids[:8],
            "record_count": len(member_ids),
            "activity_score": round(activity, 4),
            "attention_index_is_proof": False,
        }

    cold_zones = [
        {**zone, "record_count": clusters[zone["topic_id"]]["record_count"], "activity_score": clusters[zone["topic_id"]]["activity_score"]}
        for zone in payload.get("cold_zones", [])
        if isinstance(zone, dict) and zone.get("topic_id") in clusters and clusters[zone["topic_id"]]["record_count"] >= 2
    ]
    probes = [
        probe
        for probe in payload.get("probes", [])
        if isinstance(probe, dict) and all(str(record_ref) in kept_ids for record_ref in probe.get("record_refs", []))
    ]
    if not probes:
        established_pairs = {
            tuple(pair)
            for pair in payload.get("established_pairs", [])
            if isinstance(pair, list) and len(pair) == 2
        }
        fallback_clusters = {
            topic_id: cluster
            for topic_id, cluster in clusters.items()
            if isinstance(cluster, dict) and int(cluster.get("record_count", 0)) >= 2
        }
        probes = generate_cluster_probes(fallback_clusters, kept_records, established_pairs, probe_limit=20)
    bridges = [
        bridge
        for bridge in payload.get("bridges", [])
        if isinstance(bridge, dict) and str(bridge.get("from", "")) in kept_ids and str(bridge.get("to", "")) in kept_ids
    ]

    return {
        **payload,
        "scope": "current",
        "workspace_ref": workspace_ref,
        "project_ref": project_ref,
        "task_ref": task_ref,
        "records": kept_records,
        "clusters": clusters,
        "record_count": len(kept_records),
        "cluster_count": len(clusters),
        "tap_count": sum(int(record.get("tap_count", 0)) for record in kept_records.values()),
        "access_event_count": sum(int(record.get("access_count", 0)) for record in kept_records.values()),
        "bridges": bridges,
        "established_pairs": payload.get("established_pairs", []),
        "cold_zones": cold_zones,
        "probes": probes,
    }


def write_attention_index_reports(root: Path, payload: dict) -> None:
    paths = attention_index_paths(root)
    write_json_file(paths["records"], payload["records"])
    write_json_file(paths["clusters"], payload["clusters"])
    write_json_file(
        paths["bridges"],
        {
            "attention_index_is_proof": False,
            "bridges": payload["bridges"],
            "established_pairs": payload.get("established_pairs", []),
        },
    )
    write_json_file(paths["cold_zones"], {"attention_index_is_proof": False, "cold_zones": payload["cold_zones"]})
    write_json_file(paths["probes"], {"attention_index_is_proof": False, "probes": payload["probes"]})
    write_text_file(paths["summary"], "\n".join(attention_map_text_lines(payload, limit=12)) + "\n")


def load_attention_payload(root: Path) -> dict:
    paths = attention_index_paths(root)
    if not paths["records"].exists() or not paths["clusters"].exists():
        return {}
    try:
        records = json.loads(paths["records"].read_text(encoding="utf-8"))
        clusters = json.loads(paths["clusters"].read_text(encoding="utf-8"))
        bridge_payload = json.loads(paths["bridges"].read_text(encoding="utf-8"))
        bridges = bridge_payload.get("bridges", [])
        established_pairs = bridge_payload.get("established_pairs", [])
        cold_zones = json.loads(paths["cold_zones"].read_text(encoding="utf-8")).get("cold_zones", [])
        probes = json.loads(paths["probes"].read_text(encoding="utf-8")).get("probes", [])
    except (OSError, json.JSONDecodeError):
        return {}
    return {
        "attention_index_is_proof": False,
        "records": records if isinstance(records, dict) else {},
        "clusters": clusters if isinstance(clusters, dict) else {},
        "record_count": len(records) if isinstance(records, dict) else 0,
        "cluster_count": len(clusters) if isinstance(clusters, dict) else 0,
        "tap_count": sum(int(item.get("tap_count", 0)) for item in records.values() if isinstance(item, dict))
        if isinstance(records, dict)
        else 0,
        "access_event_count": sum(int(item.get("access_count", 0)) for item in records.values() if isinstance(item, dict))
        if isinstance(records, dict)
        else 0,
        "bridges": bridges if isinstance(bridges, list) else [],
        "established_pairs": established_pairs if isinstance(established_pairs, list) else [],
        "cold_zones": cold_zones if isinstance(cold_zones, list) else [],
        "probes": probes if isinstance(probes, list) else [],
    }


def attention_map_text_lines(payload: dict, *, limit: int) -> list[str]:
    clusters = sorted(payload.get("clusters", {}).values(), key=lambda item: (-item.get("activity_score", 0), -item.get("record_count", 0), item.get("term", "")))
    cold_zones = payload.get("cold_zones", [])
    lines = [
        "# Attention Map",
        "",
        "Mode: generated attention/navigation map. Not proof.",
        f"scope: `{payload.get('scope', 'all')}` workspace: `{payload.get('workspace_ref', '')}` project: `{payload.get('project_ref', '')}` task: `{payload.get('task_ref', '')}`",
        f"records: `{payload.get('record_count', len(payload.get('records', {})))}` clusters: `{payload.get('cluster_count', len(payload.get('clusters', {})))}` taps: `{payload.get('tap_count', 0)}` access_events: `{payload.get('access_event_count', 0)}`",
        "",
        "## Active Clusters",
    ]
    for cluster in clusters[: max(1, limit)]:
        lines.append(
            f"- `{cluster.get('id')}` term=`{cluster.get('term')}` records=`{cluster.get('record_count')}` activity=`{cluster.get('activity_score')}` access=`{cluster.get('access_count', 0)}`"
        )
    if not clusters:
        lines.append("- none")
    lines.extend(["", "## Cold Zones"])
    for zone in cold_zones[: max(1, limit)]:
        lines.append(
            f"- `{zone.get('topic_id')}` term=`{zone.get('term')}` records=`{zone.get('record_count')}` reason=\"{zone.get('reason')}\""
        )
    if not cold_zones:
        lines.append("- none")
    return lines


def mermaid_node_id(prefix: str, value: str) -> str:
    safe = "".join(character if character.isalnum() else "_" for character in str(value))
    return f"{prefix}_{safe}".strip("_") or f"{prefix}_unknown"


def mermaid_label(value: str, *, limit: int = 72) -> str:
    text = " ".join(str(value).replace('"', "'").split())
    return text[: limit - 1] + "…" if len(text) > limit else text


def record_diagram_summary(record: dict) -> str:
    summary = record.get("summary", "")
    if isinstance(summary, dict):
        return str(summary.get("summary") or summary.get("statement") or summary.get("title") or summary.get("id") or "")
    return str(summary)


def attention_diagram_metrics(payload: dict, *, mermaid: str, detail: str) -> dict:
    return {
        "detail": detail,
        "cluster_count": len(payload.get("clusters", [])),
        "record_count": len(payload.get("records", {})),
        "bridge_count": len(payload.get("bridges", [])),
        "probe_count": len(payload.get("probes", [])),
        "payload_char_count": len(json.dumps({**payload, "mermaid": mermaid}, ensure_ascii=False, sort_keys=True)),
        "omitted_fields": [] if detail == "full" else ["record_summaries"],
        "metrics_are_proof": False,
    }


def attention_diagram_payload(payload: dict, *, limit: int, detail: str = "compact") -> dict:
    clusters = sorted(
        payload.get("clusters", {}).values(),
        key=lambda item: (-item.get("activity_score", 0), -item.get("record_count", 0), item.get("term", "")),
    )[: max(1, limit)]
    cluster_ids = {str(cluster.get("id", "")) for cluster in clusters}
    records = payload.get("records", {}) if isinstance(payload.get("records"), dict) else {}
    record_ids: set[str] = set()
    for cluster in clusters:
        record_ids.update(str(record_id) for record_id in cluster.get("top_records", [])[:3] if str(record_id) in records)
    bridges = [
        bridge
        for bridge in payload.get("bridges", [])
        if isinstance(bridge, dict)
        and str(bridge.get("from_topic", "")) in cluster_ids
        and str(bridge.get("to_topic", "")) in cluster_ids
    ][: max(1, limit)]
    probes = [
        probe
        for probe in payload.get("probes", [])
        if isinstance(probe, dict) and any(str(cluster_ref) in cluster_ids for cluster_ref in probe.get("cluster_refs", []))
    ][: max(1, limit)]
    for probe in probes:
        record_ids.update(str(record_id) for record_id in probe.get("record_refs", []) if str(record_id) in records)
    selected_records = {record_id: records[record_id] for record_id in sorted(record_ids)}
    if detail != "full":
        selected_records = {
            record_id: {
                "id": record.get("id", record_id),
                "record_type": record.get("record_type", ""),
                "status": record.get("status", ""),
                "activity_score": record.get("activity_score", 0.0),
                "tap_count": record.get("tap_count", 0),
                "top_topic_id": record.get("top_topic_id", ""),
                "top_topic_term": record.get("top_topic_term", ""),
                "attention_index_is_proof": False,
            }
            for record_id, record in selected_records.items()
        }
    return {
        "diagram_is_proof": False,
        "attention_index_is_proof": False,
        "detail": detail,
        "scope": payload.get("scope", "all"),
        "workspace_ref": payload.get("workspace_ref", ""),
        "project_ref": payload.get("project_ref", ""),
        "task_ref": payload.get("task_ref", ""),
        "clusters": clusters,
        "records": selected_records,
        "bridges": bridges,
        "probes": probes,
        "note": "Generated Mermaid attention diagram data. Navigation only; not proof.",
    }


def attention_diagram_mermaid_lines(payload: dict, *, limit: int, detail: str = "compact") -> list[str]:
    diagram = attention_diagram_payload(payload, limit=limit, detail=detail)
    records = diagram["records"]
    lines = [
        "%% TEP attention diagram. Generated navigation only; not proof.",
        "graph TD",
        '  meta["Not proof: inspect canonical records before citing"]',
    ]
    declared_records: set[str] = set()
    for cluster in diagram["clusters"]:
        cluster_id = str(cluster.get("id", ""))
        node_id = mermaid_node_id("cluster", cluster_id)
        label = mermaid_label(
            f"{cluster.get('term', '')}\\nrecords={cluster.get('record_count', 0)} activity={cluster.get('activity_score', 0)}"
        )
        lines.append(f'  {node_id}["{label}"]')
        for record_ref in cluster.get("top_records", [])[:3]:
            record_ref = str(record_ref)
            if record_ref not in records:
                continue
            record_node = mermaid_node_id("record", record_ref)
            if record_ref not in declared_records:
                record_label = (
                    mermaid_label(f"{record_ref}\\n{record_diagram_summary(records[record_ref])}", limit=90)
                    if detail == "full"
                    else mermaid_label(record_ref, limit=90)
                )
                lines.append(f'  {record_node}["{record_label}"]')
                declared_records.add(record_ref)
            lines.append(f"  {node_id} --> {record_node}")
    for bridge in diagram["bridges"]:
        from_node = mermaid_node_id("cluster", str(bridge.get("from_topic", "")))
        to_node = mermaid_node_id("cluster", str(bridge.get("to_topic", "")))
        lines.append(f"  {from_node} == established bridge ==> {to_node}")
    for probe in diagram["probes"]:
        refs = [str(record_ref) for record_ref in probe.get("record_refs", []) if str(record_ref) in records]
        if len(refs) != 2:
            continue
        left = mermaid_node_id("record", refs[0])
        right = mermaid_node_id("record", refs[1])
        lines.append(f"  {left} -. candidate probe score={probe.get('score', 0)} .- {right}")
    return lines


def attention_diagram_text_lines(payload: dict, *, limit: int, detail: str = "compact") -> list[str]:
    diagram = attention_diagram_payload(payload, limit=limit, detail=detail)
    mermaid = "\n".join(attention_diagram_mermaid_lines(payload, limit=limit, detail=detail))
    metrics = attention_diagram_metrics(diagram, mermaid=mermaid, detail=detail)
    lines = [
        "# Attention Diagram",
        "",
        "Mode: generated Mermaid attention/navigation diagram. Not proof.",
        f"scope: `{payload.get('scope', 'all')}` workspace: `{payload.get('workspace_ref', '')}` project: `{payload.get('project_ref', '')}` task: `{payload.get('task_ref', '')}`",
        f"detail: `{detail}` metrics_are_proof=`{metrics['metrics_are_proof']}` omitted=`{', '.join(metrics['omitted_fields']) or 'none'}` payload_chars=`{metrics['payload_char_count']}`",
        "",
        "```mermaid",
    ]
    lines.extend(mermaid.splitlines())
    lines.extend(["```", "", "Inspect canonical records before citing any diagram relationship."])
    return lines


def curiosity_probe_text_lines(payload: dict, *, limit: int) -> list[str]:
    probes = payload.get("probes", [])
    lines = [
        "# Curiosity Probes",
        "",
        "Mode: generated questions for bounded inspection. Not proof.",
        f"scope: `{payload.get('scope', 'all')}` workspace: `{payload.get('workspace_ref', '')}` project: `{payload.get('project_ref', '')}` task: `{payload.get('task_ref', '')}`",
        "",
    ]
    for probe in probes[: max(1, limit)]:
        refs = ", ".join(f"`{ref}`" for ref in probe.get("record_refs", []))
        lines.append(
            f"- score=`{probe.get('score', 0)}` {refs}: {probe.get('reason')} link_state=`{probe.get('link_state')}`"
        )
        if probe.get("explanation"):
            lines.append(f"  explanation: {probe.get('explanation')}")
    if not probes:
        lines.append("- none")
    return lines
