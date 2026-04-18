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
DEFAULT_HALF_LIFE_DAYS = 7.0


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


def decayed_weight(timestamp: str, kind: str, generated_at: str, half_life_days: float = DEFAULT_HALF_LIFE_DAYS) -> float:
    base = TAP_WEIGHTS.get(kind, 0.5)
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


def build_attention_index(records: dict[str, dict], topic_payload: dict, taps: list[dict], *, probe_limit: int = 20) -> dict:
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

    record_items = {}
    for record_id, data in records.items():
        topic_item = topic_records.get(record_id, {}) if isinstance(topic_records.get(record_id, {}), dict) else {}
        record_items[record_id] = {
            "id": record_id,
            "summary": public_record_summary(data),
            "activity_score": round(tap_scores.get(record_id, 0.0), 4),
            "tap_count": tap_counts.get(record_id, 0),
            "top_topic_id": top_topic_id(topic_item),
            "top_topic_term": top_topic_term(topic_item),
            "attention_index_is_proof": False,
        }

    clusters = {}
    for topic_id, topic in topics.items():
        members = by_topic.get(topic_id, []) if isinstance(by_topic.get(topic_id, []), list) else []
        member_ids = [str(member.get("id", "")) for member in members if isinstance(member, dict) and str(member.get("id", "")) in records]
        activity = sum(tap_scores.get(record_id, 0.0) for record_id in member_ids)
        clusters[topic_id] = {
            "id": topic_id,
            "term": topic.get("term", ""),
            "record_count": len(member_ids),
            "activity_score": round(activity, 4),
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
    probes = []
    for zone in cold_zones:
        topic_id = zone["topic_id"]
        member_ids = [record_id for record_id in clusters.get(topic_id, {}).get("top_records", []) if record_id in records]
        for index, left in enumerate(member_ids):
            for right in member_ids[index + 1 :]:
                pair = tuple(sorted([left, right]))
                if pair in established_pairs:
                    continue
                probes.append(
                    {
                        "record_refs": [left, right],
                        "cluster_refs": [topic_id],
                        "sampling_method": "deterministic-cold-zone-pair",
                        "reason": "records share a cold semantic cluster but no established direct link",
                        "link_state": "candidate",
                        "attention_index_is_proof": False,
                    }
                )
            if len(probes) >= probe_limit:
                break
        if len(probes) >= probe_limit:
            break

    return {
        "attention_index_is_proof": False,
        "generated_at": generated_at,
        "tap_count": len(taps),
        "record_count": len(record_items),
        "cluster_count": len(clusters),
        "records": record_items,
        "clusters": clusters,
        "bridges": bridges[: max(1, probe_limit)],
        "cold_zones": cold_zones[: max(1, probe_limit)],
        "probes": probes[: max(1, probe_limit)],
        "note": "Generated attention/curiosity navigation data. Not proof.",
    }


def write_attention_index_reports(root: Path, payload: dict) -> None:
    paths = attention_index_paths(root)
    write_json_file(paths["records"], payload["records"])
    write_json_file(paths["clusters"], payload["clusters"])
    write_json_file(paths["bridges"], {"attention_index_is_proof": False, "bridges": payload["bridges"]})
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
        bridges = json.loads(paths["bridges"].read_text(encoding="utf-8")).get("bridges", [])
        cold_zones = json.loads(paths["cold_zones"].read_text(encoding="utf-8")).get("cold_zones", [])
        probes = json.loads(paths["probes"].read_text(encoding="utf-8")).get("probes", [])
    except (OSError, json.JSONDecodeError):
        return {}
    return {
        "attention_index_is_proof": False,
        "records": records if isinstance(records, dict) else {},
        "clusters": clusters if isinstance(clusters, dict) else {},
        "bridges": bridges if isinstance(bridges, list) else [],
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
        f"records: `{payload.get('record_count', len(payload.get('records', {})))}` clusters: `{payload.get('cluster_count', len(payload.get('clusters', {})))}` taps: `{payload.get('tap_count', 0)}`",
        "",
        "## Active Clusters",
    ]
    for cluster in clusters[: max(1, limit)]:
        lines.append(
            f"- `{cluster.get('id')}` term=`{cluster.get('term')}` records=`{cluster.get('record_count')}` activity=`{cluster.get('activity_score')}`"
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


def curiosity_probe_text_lines(payload: dict, *, limit: int) -> list[str]:
    probes = payload.get("probes", [])
    lines = [
        "# Curiosity Probes",
        "",
        "Mode: generated questions for bounded inspection. Not proof.",
        "",
    ]
    for probe in probes[: max(1, limit)]:
        refs = ", ".join(f"`{ref}`" for ref in probe.get("record_refs", []))
        lines.append(f"- {refs}: {probe.get('reason')} link_state=`{probe.get('link_state')}`")
    if not probes:
        lines.append("- none")
    return lines
