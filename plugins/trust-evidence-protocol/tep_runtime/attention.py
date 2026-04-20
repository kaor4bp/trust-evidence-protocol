"""Generated attention-map and curiosity helpers.

Attention data is navigation only. It helps an agent decide what to inspect
next; it must not support claims or justify actions.
"""

from __future__ import annotations

import json
import math
from datetime import datetime
from html import escape
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
ATTENTION_MODES = {"general", "research", "theory", "code"}
CURIOSITY_MAP_VOLUMES = {"compact", "normal", "wide"}
MAP_GRAPH_VERSION = "tep.map_graph.v1"
CURIOSITY_MAP_BUDGETS = {
    "compact": {"clusters": 4, "records_per_cluster": 2, "bridges": 4, "probes": 3, "cold_zones": 4},
    "normal": {"clusters": 8, "records_per_cluster": 3, "bridges": 8, "probes": 6, "cold_zones": 8},
    "wide": {"clusters": 14, "records_per_cluster": 4, "bridges": 14, "probes": 10, "cold_zones": 14},
}
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
ATTENTION_MODE_DESCRIPTIONS = {
    "general": "balanced navigation across all record types",
    "research": "investigation view; hides policy records that rarely help exploration",
    "theory": "theory-building view over claims, models, flows, open questions, and proposals",
    "code": "code-navigation view; hides raw inputs and source/claim proof noise unless records are code-linked",
}
ATTENTION_MODE_EXCLUDED_TYPES = {
    "general": set(),
    "research": {"guideline", "permission", "restriction"},
    "theory": {
        "input",
        "source",
        "guideline",
        "permission",
        "restriction",
        "action",
        "task",
        "plan",
        "debt",
        "workspace",
        "project",
        "working_context",
    },
    "code": {"input", "source", "claim", "permission", "restriction"},
}
ATTENTION_CODE_OPERATIONAL_TYPES = {"guideline", "proposal", "plan", "debt", "open_question", "model", "flow", "action", "task", "working_context"}
MAP_RELATION_WEIGHTS = {
    "supports": 1.0,
    "contradicts": 1.0,
    "derived_from": 0.9,
    "depends_on": 0.8,
    "implemented_by": 0.75,
    "cites": 0.7,
    "same_topic": 0.35,
    "mentions": 0.2,
    "candidate_link": 0.1,
    "no_known_link": 0.0,
    "rejected_link": -0.2,
}
TOPOLOGY_ESTABLISHED_RELATIONS = {"supports", "contradicts", "derived_from", "depends_on", "implemented_by", "cites"}


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


def map_edge_relation(fields: list[str]) -> str:
    joined = " ".join(str(field) for field in fields)
    if "contradiction_refs" in joined or "conflict_refs" in joined:
        return "contradicts"
    if "support_refs" in joined or "source_refs" in joined or "evidence_refs" in joined:
        return "supports" if "support_refs" in joined else "cites"
    if "derived_from" in joined or "supersedes_refs" in joined or "promoted_from_refs" in joined:
        return "derived_from"
    if "code_index_refs" in joined:
        return "implemented_by"
    if "model_refs" in joined or "flow_refs" in joined or "claim_refs" in joined or "justified_by" in joined:
        return "depends_on"
    return "mentions"


def map_graph_nodes(records: dict[str, dict]) -> list[dict]:
    nodes = []
    for record_id, record in sorted(records.items()):
        nodes.append(
            {
                "id": record_id,
                "kind": str(record.get("record_type", "") or "record"),
                "label": record_id,
                "summary": record_diagram_summary(record),
                "status": record.get("status", ""),
                "topic_ref": record.get("top_topic_id", ""),
                "scores": {
                    "heat": float(record.get("activity_score", 0.0) or 0.0),
                    "tap_count": int(record.get("tap_count", 0) or 0),
                    "access_count": int(record.get("access_count", 0) or 0),
                },
                "not_proof": True,
            }
        )
    return nodes


def map_graph_edges(link_edges: list[dict], selected_record_ids: set[str]) -> list[dict]:
    edges = []
    seen: set[tuple[str, str, str, tuple[str, ...]]] = set()
    for index, edge in enumerate(link_edges, start=1):
        left = str(edge.get("from", ""))
        right = str(edge.get("to", ""))
        if left not in selected_record_ids or right not in selected_record_ids:
            continue
        fields = [str(field) for field in edge.get("fields", [])]
        relation = map_edge_relation(fields)
        key = (left, right, relation, tuple(fields))
        if key in seen:
            continue
        seen.add(key)
        edges.append(
            {
                "id": f"MEDGE-{index:04d}",
                "from": left,
                "to": right,
                "relation": relation,
                "status": "established",
                "weight": MAP_RELATION_WEIGHTS.get(relation, 0.2),
                "fields": fields,
                "not_proof": True,
            }
        )
    return edges


def topology_clusters(nodes: list[dict], edges: list[dict]) -> list[dict]:
    node_ids = {str(node.get("id", "")) for node in nodes if str(node.get("id", ""))}
    adjacency: dict[str, set[str]] = {node_id: set() for node_id in node_ids}
    edge_ids_by_pair: dict[tuple[str, str], list[str]] = {}
    for edge in edges:
        relation = str(edge.get("relation", ""))
        if relation not in TOPOLOGY_ESTABLISHED_RELATIONS or float(edge.get("weight", 0.0) or 0.0) < 0.35:
            continue
        left = str(edge.get("from", ""))
        right = str(edge.get("to", ""))
        if left not in node_ids or right not in node_ids:
            continue
        adjacency[left].add(right)
        adjacency[right].add(left)
        edge_ids_by_pair.setdefault(tuple(sorted([left, right])), []).append(str(edge.get("id", "")))

    clusters = []
    seen: set[str] = set()
    for node_id in sorted(node_ids):
        if node_id in seen:
            continue
        stack = [node_id]
        component: set[str] = set()
        while stack:
            current = stack.pop()
            if current in component:
                continue
            component.add(current)
            stack.extend(sorted(adjacency.get(current, set()) - component))
        seen.update(component)
        if len(component) < 2:
            continue
        internal_edges = []
        bridge_nodes = []
        for left in sorted(component):
            external_degree = len(adjacency.get(left, set()) - component)
            if external_degree:
                bridge_nodes.append(left)
            for right in sorted(adjacency.get(left, set()) & component):
                if left < right:
                    internal_edges.extend(edge_ids_by_pair.get((left, right), []))
        possible_edges = max(1, len(component) * (len(component) - 1) / 2)
        density = round(len(internal_edges) / possible_edges, 4)
        clusters.append(
            {
                "id": f"MCL-topology-{len(clusters) + 1:03d}",
                "kind": "topology",
                "label": f"Topology component {len(clusters) + 1}",
                "algorithm": "connected_components",
                "status": "generated",
                "node_refs": sorted(component),
                "edge_refs": sorted(internal_edges),
                "scores": {
                    "density": density,
                    "heat": round(
                        sum(float(node.get("scores", {}).get("heat", 0.0) or 0.0) for node in nodes if node.get("id") in component),
                        4,
                    ),
                    "bridge_score": round(len(bridge_nodes) / max(1, len(component)), 4),
                },
                "boundary": {
                    "internal_edge_refs": sorted(internal_edges),
                    "external_edge_refs": [],
                    "bridge_node_refs": sorted(bridge_nodes),
                    "orphan_node_refs": [],
                },
                "explanation": "Generated from established TEP record links using connected components.",
                "not_proof": True,
            }
        )
    return clusters


def topic_map_clusters(clusters: list[dict]) -> list[dict]:
    result = []
    for index, cluster in enumerate(clusters, start=1):
        cluster_id = str(cluster.get("id", ""))
        result.append(
            {
                "id": f"MCL-topic-{index:03d}",
                "kind": "topic",
                "label": str(cluster.get("term", "") or cluster_id),
                "algorithm": "lexical",
                "status": "generated",
                "source_cluster_ref": cluster_id,
                "node_refs": [str(ref) for ref in cluster.get("top_records", [])],
                "edge_refs": [],
                "centroid": {"terms": [str(cluster.get("term", "") or cluster_id)], "embedding_ref": None},
                "scores": {
                    "cohesion": None,
                    "heat": float(cluster.get("activity_score", 0.0) or 0.0),
                    "coldness": 1.0 if float(cluster.get("activity_score", 0.0) or 0.0) < 1.0 else 0.0,
                    "curiosity": 0.0,
                },
                "explanation": "Generated from lexical topic index membership.",
                "not_proof": True,
            }
        )
    return result


def build_map_graph(link_edges: list[dict], selected_records: dict[str, dict], clusters: list[dict], probes: list[dict]) -> dict:
    nodes = map_graph_nodes(selected_records)
    node_ids = {str(node.get("id", "")) for node in nodes if str(node.get("id", ""))}
    edges = map_graph_edges(link_edges, node_ids)
    topic_clusters = topic_map_clusters(clusters)
    topology = topology_clusters(nodes, edges)
    cluster_layers = [
        {
            "id": "layer:topic",
            "kind": "topic",
            "algorithm": "lexical",
            "edge_policy": {"include_relations": ["same_topic"], "exclude_relations": [], "min_weight": 0.0},
            "cluster_refs": [cluster["id"] for cluster in topic_clusters],
            "not_proof": True,
        },
        {
            "id": "layer:topology",
            "kind": "topology",
            "algorithm": "connected_components",
            "edge_policy": {
                "include_relations": sorted(TOPOLOGY_ESTABLISHED_RELATIONS),
                "exclude_relations": ["candidate_link", "no_known_link", "rejected_link"],
                "min_weight": 0.35,
            },
            "cluster_refs": [cluster["id"] for cluster in topology],
            "not_proof": True,
        },
    ]
    return {
        "format": MAP_GRAPH_VERSION,
        "graph_is_proof": False,
        "node_count": len(nodes),
        "edge_count": len(edges),
        "cluster_count": len(topic_clusters) + len(topology),
        "nodes": nodes,
        "edges": edges,
        "clusters": topic_clusters + topology,
        "cluster_layers": cluster_layers,
        "probes": [
            {
                "id": f"PROBE-{index:03d}",
                "record_refs": probe.get("record_refs", []),
                "cluster_refs": probe.get("cluster_refs", []),
                "score": probe.get("score", 0),
                "link_state": probe.get("link_state", "candidate"),
                "reason": probe.get("explanation") or probe.get("reason", ""),
                "not_proof": True,
            }
            for index, probe in enumerate(probes, start=1)
        ],
        "relation_weights": MAP_RELATION_WEIGHTS,
        "note": "Typed generated map graph. Navigation only; not proof.",
    }


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


def record_matches_attention_mode(record: dict, mode: str) -> bool:
    mode = mode if mode in ATTENTION_MODES else "general"
    record_type = str(record.get("record_type", "")).strip()
    if mode == "code":
        if record.get("has_code_index_refs"):
            return True
        return record_type in ATTENTION_CODE_OPERATIONAL_TYPES
    return record_type not in ATTENTION_MODE_EXCLUDED_TYPES.get(mode, set())


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
            "status": str(data.get("status", "")).strip(),
            "activity_score": round(tap_scores.get(record_id, 0.0) + access_scores.get(record_id, 0.0), 4),
            "tap_count": tap_counts.get(record_id, 0),
            "access_count": access_counts.get(record_id, 0),
            "top_topic_id": top_topic_id(topic_item),
            "top_topic_term": top_topic_term(topic_item),
            "workspace_refs": list_refs(data, "workspace_refs"),
            "project_refs": list_refs(data, "project_refs"),
            "task_refs": list_refs(data, "task_refs"),
            "has_code_index_refs": bool(list_refs(data, "code_index_refs")),
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

    link_edges = collect_link_edges(records)
    bridges = []
    for edge in link_edges:
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
        "record_access_count": sum(access_counts.values()),
        "record_count": len(record_items),
        "cluster_count": len(clusters),
        "records": record_items,
        "clusters": clusters,
        "link_edges": link_edges,
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
    mode: str = "general",
    workspace_ref: str = "",
    project_ref: str = "",
    task_ref: str = "",
) -> dict:
    mode = mode if mode in ATTENTION_MODES else "general"
    focus_all = scope == "all" or not any([workspace_ref, project_ref, task_ref])

    records = payload.get("records", {}) if isinstance(payload.get("records"), dict) else {}
    kept_records = {
        record_id: {
            **record,
            "focus_score": 0
            if focus_all
            else record_focus_score(record, workspace_ref=workspace_ref, project_ref=project_ref, task_ref=task_ref),
        }
        for record_id, record in records.items()
        if isinstance(record, dict)
        and (focus_all or record_matches_focus(record, workspace_ref=workspace_ref, project_ref=project_ref, task_ref=task_ref))
        and record_matches_attention_mode(record, mode)
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
    link_edges = [
        edge
        for edge in payload.get("link_edges", [])
        if isinstance(edge, dict) and str(edge.get("from", "")) in kept_ids and str(edge.get("to", "")) in kept_ids
    ]

    return {
        **payload,
        "scope": "all" if focus_all else "current",
        "mode": mode,
        "mode_description": ATTENTION_MODE_DESCRIPTIONS.get(mode, ""),
        "workspace_ref": "" if focus_all else workspace_ref,
        "project_ref": "" if focus_all else project_ref,
        "task_ref": "" if focus_all else task_ref,
        "records": kept_records,
        "clusters": clusters,
        "record_count": len(kept_records),
        "cluster_count": len(clusters),
        "tap_count": sum(int(record.get("tap_count", 0)) for record in kept_records.values()),
        "access_event_count": payload.get("access_event_count", 0),
        "record_access_count": sum(int(record.get("access_count", 0)) for record in kept_records.values()),
        "link_edges": link_edges,
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
            "access_event_count": payload.get("access_event_count", 0),
            "record_access_count": payload.get("record_access_count", 0),
            "link_edges": payload.get("link_edges", []),
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
        link_edges = bridge_payload.get("link_edges", [])
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
        "access_event_count": int(bridge_payload.get("access_event_count", 0) or 0),
        "record_access_count": sum(int(item.get("access_count", 0)) for item in records.values() if isinstance(item, dict))
        if isinstance(records, dict)
        else 0,
        "link_edges": link_edges if isinstance(link_edges, list) else [],
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
        f"scope: `{payload.get('scope', 'all')}` mode: `{payload.get('mode', 'general')}` workspace: `{payload.get('workspace_ref', '')}` project: `{payload.get('project_ref', '')}` task: `{payload.get('task_ref', '')}`",
        f"records: `{payload.get('record_count', len(payload.get('records', {})))}` clusters: `{payload.get('cluster_count', len(payload.get('clusters', {})))}` taps: `{payload.get('tap_count', 0)}` access_events: `{payload.get('access_event_count', 0)}` record_accesses: `{payload.get('record_access_count', 0)}`",
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
        "mode": payload.get("mode", "general"),
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
        f"scope: `{payload.get('scope', 'all')}` mode: `{payload.get('mode', 'general')}` workspace: `{payload.get('workspace_ref', '')}` project: `{payload.get('project_ref', '')}` task: `{payload.get('task_ref', '')}`",
        f"detail: `{detail}` metrics_are_proof=`{metrics['metrics_are_proof']}` omitted=`{', '.join(metrics['omitted_fields']) or 'none'}` payload_chars=`{metrics['payload_char_count']}`",
        "",
        "```mermaid",
    ]
    lines.extend(mermaid.splitlines())
    lines.extend(["```", "", "Inspect canonical records before citing any diagram relationship."])
    return lines


def curiosity_map_budget(volume: str) -> dict[str, int]:
    return CURIOSITY_MAP_BUDGETS.get(volume, CURIOSITY_MAP_BUDGETS["normal"])


def curiosity_map_payload(payload: dict, *, volume: str = "normal") -> dict:
    budget = curiosity_map_budget(volume)
    active_clusters = sorted(
        payload.get("clusters", {}).values(),
        key=lambda item: (-float(item.get("activity_score", 0)), -int(item.get("record_count", 0)), str(item.get("term", ""))),
    )
    cold_topic_ids = [
        str(zone.get("topic_id", ""))
        for zone in payload.get("cold_zones", [])
        if isinstance(zone, dict) and str(zone.get("topic_id", ""))
    ]
    clusters_by_id = {
        str(cluster.get("id", "")): cluster
        for cluster in active_clusters
        if str(cluster.get("id", ""))
    }
    clusters = []
    seen_cluster_ids: set[str] = set()
    cold_quota = max(1, budget["clusters"] // 2)
    for topic_id in cold_topic_ids[:cold_quota]:
        cluster = clusters_by_id.get(topic_id)
        if cluster is not None and topic_id not in seen_cluster_ids:
            clusters.append(cluster)
            seen_cluster_ids.add(topic_id)
    for cluster in active_clusters:
        cluster_id = str(cluster.get("id", ""))
        if cluster_id in seen_cluster_ids:
            continue
        clusters.append(cluster)
        seen_cluster_ids.add(cluster_id)
        if len(clusters) >= budget["clusters"]:
            break
    clusters = clusters[: budget["clusters"]]
    cluster_ids = {str(cluster.get("id", "")) for cluster in clusters}
    records = payload.get("records", {}) if isinstance(payload.get("records"), dict) else {}
    selected_record_ids: set[str] = set()
    for cluster in clusters:
        selected_record_ids.update(
            str(record_id)
            for record_id in cluster.get("top_records", [])[: budget["records_per_cluster"]]
            if str(record_id) in records
        )

    bridges = [
        bridge
        for bridge in payload.get("bridges", [])
        if isinstance(bridge, dict)
        and str(bridge.get("from_topic", "")) in cluster_ids
        and str(bridge.get("to_topic", "")) in cluster_ids
    ][: budget["bridges"]]
    probes = [
        probe
        for probe in payload.get("probes", [])
        if isinstance(probe, dict) and any(str(cluster_ref) in cluster_ids for cluster_ref in probe.get("cluster_refs", []))
    ][: budget["probes"]]
    for probe in probes:
        selected_record_ids.update(str(record_id) for record_id in probe.get("record_refs", []) if str(record_id) in records)

    selected_records = {
        record_id: {
            "id": record.get("id", record_id),
            "record_type": record.get("record_type", ""),
            "status": record.get("status", ""),
            "summary": record.get("summary", ""),
            "activity_score": record.get("activity_score", 0.0),
            "tap_count": record.get("tap_count", 0),
            "access_count": record.get("access_count", 0),
            "top_topic_id": record.get("top_topic_id", ""),
            "top_topic_term": record.get("top_topic_term", ""),
            "attention_index_is_proof": False,
        }
        for record_id, record in sorted(records.items())
        if record_id in selected_record_ids
    }
    cold_zones = [
        zone
        for zone in payload.get("cold_zones", [])
        if isinstance(zone, dict) and str(zone.get("topic_id", "")) in cluster_ids
    ][: budget["cold_zones"]]

    visual_payload = {
        "map_is_proof": False,
        "map_graph_version": MAP_GRAPH_VERSION,
        "attention_index_is_proof": False,
        "scope": payload.get("scope", "all"),
        "mode": payload.get("mode", "general"),
        "workspace_ref": payload.get("workspace_ref", ""),
        "project_ref": payload.get("project_ref", ""),
        "task_ref": payload.get("task_ref", ""),
        "volume": volume,
        "budget": budget,
        "clusters": clusters,
        "records": selected_records,
        "bridges": bridges,
        "cold_zones": cold_zones,
        "probes": probes,
        "map_graph": build_map_graph(payload.get("link_edges", []), selected_records, clusters, probes),
        "curiosity_prompts": [
            {
                "probe_index": index,
                "record_refs": probe.get("record_refs", []),
                "cluster_refs": probe.get("cluster_refs", []),
                "score": probe.get("score", 0),
                "question": probe.get("explanation") or probe.get("reason", ""),
                "link_state": probe.get("link_state", "candidate"),
                "prompt_is_proof": False,
            }
            for index, probe in enumerate(probes, start=1)
        ],
        "recommended_commands": [
            f"probe-route --index {index} --scope {payload.get('scope', 'current')}"
            for index, _probe in enumerate(probes[:3], start=1)
        ],
        "note": "Generated visual-thinking curiosity map. Navigation only; not proof.",
    }
    visual_payload["mermaid"] = "\n".join(curiosity_map_mermaid_lines(visual_payload))
    visual_payload["metrics"] = curiosity_map_metrics(visual_payload)
    return visual_payload


def curiosity_map_mermaid_lines(payload: dict) -> list[str]:
    lines = [
        "%% TEP curiosity map. Generated navigation only; not proof.",
        "graph TD",
        '  meta["Not proof: use this map to choose inspection, then cite canonical records"]',
    ]
    records = payload.get("records", {}) if isinstance(payload.get("records"), dict) else {}
    declared_records: set[str] = set()
    cold_topic_ids = {str(zone.get("topic_id", "")) for zone in payload.get("cold_zones", []) if isinstance(zone, dict)}
    for cluster in payload.get("clusters", []):
        cluster_id = str(cluster.get("id", ""))
        node_id = mermaid_node_id("cluster", cluster_id)
        heat = float(cluster.get("activity_score", 0.0))
        label = mermaid_label(
            f"{cluster.get('term', '')}\\nrecords={cluster.get('record_count', 0)} heat={heat} taps/access={cluster.get('access_count', 0)}"
        )
        style = "cold" if cluster_id in cold_topic_ids else "active"
        lines.append(f'  {node_id}["{label}"]')
        lines.append(f"  {node_id}:::cluster_{style}")
        for record_ref in cluster.get("top_records", [])[: int(payload.get("budget", {}).get("records_per_cluster", 3))]:
            record_ref = str(record_ref)
            if record_ref not in records:
                continue
            record_node = mermaid_node_id("record", record_ref)
            if record_ref not in declared_records:
                record = records[record_ref]
                label = mermaid_label(
                    f"{record_ref}\\n{record.get('record_type', '')} heat={record.get('activity_score', 0)}\\n{record_diagram_summary(record)}",
                    limit=100,
                )
                lines.append(f'  {record_node}["{label}"]')
                lines.append(f"  {record_node}:::record")
                declared_records.add(record_ref)
            lines.append(f"  {node_id} --> {record_node}")
    for record_ref, record in records.items():
        if record_ref in declared_records:
            continue
        record_node = mermaid_node_id("record", record_ref)
        label = mermaid_label(
            f"{record_ref}\\n{record.get('record_type', '')} heat={record.get('activity_score', 0)}\\n{record_diagram_summary(record)}",
            limit=100,
        )
        lines.append(f'  {record_node}["{label}"]')
        lines.append(f"  {record_node}:::record")
        declared_records.add(record_ref)
    for bridge in payload.get("bridges", []):
        from_node = mermaid_node_id("cluster", str(bridge.get("from_topic", "")))
        to_node = mermaid_node_id("cluster", str(bridge.get("to_topic", "")))
        lines.append(f"  {from_node} == established ==> {to_node}")
    for probe in payload.get("probes", []):
        refs = [str(record_ref) for record_ref in probe.get("record_refs", []) if str(record_ref) in records]
        if len(refs) != 2:
            continue
        left = mermaid_node_id("record", refs[0])
        right = mermaid_node_id("record", refs[1])
        lines.append(f"  {left} -. curiosity? score={probe.get('score', 0)} .- {right}")
    lines.extend(
        [
            "  classDef cluster_active fill:#d7ecff,stroke:#2862a8,color:#111",
            "  classDef cluster_cold fill:#fff3bf,stroke:#b7791f,color:#111",
            "  classDef record fill:#f8f9fa,stroke:#495057,color:#111",
        ]
    )
    return lines


def curiosity_map_metrics(payload: dict) -> dict:
    payload_without_metrics = {key: value for key, value in payload.items() if key != "metrics"}
    return {
        "metrics_are_proof": False,
        "cluster_count": len(payload.get("clusters", [])),
        "record_count": len(payload.get("records", {})),
        "bridge_count": len(payload.get("bridges", [])),
        "cold_zone_count": len(payload.get("cold_zones", [])),
        "probe_count": len(payload.get("probes", [])),
        "mermaid_char_count": len(str(payload.get("mermaid", ""))),
        "payload_char_count": len(json.dumps(payload_without_metrics, ensure_ascii=False, sort_keys=True)),
    }


def curiosity_map_text_lines(payload: dict) -> list[str]:
    metrics = payload.get("metrics", {})
    lines = [
        "# Curiosity Map",
        "",
        "Mode: generated visual-thinking map for bounded curiosity. Not proof.",
        f"scope: `{payload.get('scope')}` mode: `{payload.get('mode', 'general')}` workspace: `{payload.get('workspace_ref', '')}` project: `{payload.get('project_ref', '')}` task: `{payload.get('task_ref', '')}`",
        f"volume: `{payload.get('volume')}` clusters=`{metrics.get('cluster_count', 0)}` records=`{metrics.get('record_count', 0)}` cold_zones=`{metrics.get('cold_zone_count', 0)}` probes=`{metrics.get('probe_count', 0)}` payload_chars=`{metrics.get('payload_char_count', 0)}`",
        "",
        "```mermaid",
    ]
    lines.extend(str(payload.get("mermaid", "")).splitlines())
    lines.extend(["```", "", "## Curiosity Prompts"])
    for prompt in payload.get("curiosity_prompts", []):
        refs = ", ".join(f"`{ref}`" for ref in prompt.get("record_refs", []))
        lines.append(
            f"- probe `{prompt.get('probe_index')}` score=`{prompt.get('score')}` refs={refs}: {prompt.get('question')}"
        )
    if not payload.get("curiosity_prompts"):
        lines.append("- none")
    lines.extend(["", "## Recommended Next Commands"])
    for command in payload.get("recommended_commands", []):
        lines.append(f"- `{command}`")
    if not payload.get("recommended_commands"):
        lines.append("- none")
    lines.extend(
        [
            "",
            "Use the map to decide what to inspect next; do not cite map links, heat, cold zones, or probes as proof.",
        ]
    )
    return lines


def curiosity_map_html(payload: dict) -> str:
    """Render a standalone HTML curiosity graph backed by vis-network.

    The HTML view is for human orientation only. It embeds the same non-proof
    payload metadata and uses a CDN graph library for interaction.
    """

    clusters = payload.get("clusters", []) if isinstance(payload.get("clusters"), list) else []
    records = payload.get("records", {}) if isinstance(payload.get("records"), dict) else {}
    bridges = payload.get("bridges", []) if isinstance(payload.get("bridges"), list) else []
    probes = payload.get("probes", []) if isinstance(payload.get("probes"), list) else []
    cold_topic_ids = {str(zone.get("topic_id", "")) for zone in payload.get("cold_zones", []) if isinstance(zone, dict)}

    nodes: list[dict] = []
    edges: list[dict] = []
    record_to_clusters: dict[str, set[str]] = {}
    for cluster in clusters:
        cluster_id = str(cluster.get("id", ""))
        if not cluster_id:
            continue
        label = str(cluster.get("term", "") or cluster_id)
        heat = float(cluster.get("activity_score", 0.0) or 0.0)
        is_cold = cluster_id in cold_topic_ids
        nodes.append(
            {
                "id": f"cluster:{cluster_id}",
                "label": label,
                "title": f"{cluster_id}\\nrecords={cluster.get('record_count', 0)} heat={heat}",
                "group": "coldCluster" if is_cold else "cluster",
                "value": max(20, 18 + int(cluster.get("record_count", 0) or 0) * 2 + min(heat, 10)),
                "shape": "dot",
                "kind": "cluster",
                "record_ref": cluster_id,
                "meta": {
                    "id": cluster_id,
                    "term": label,
                    "record_count": cluster.get("record_count", 0),
                    "activity_score": heat,
                    "cold": is_cold,
                    "top_records": cluster.get("top_records", []),
                },
            }
        )
        for record_ref in cluster.get("top_records", []):
            record_ref = str(record_ref)
            if record_ref not in records:
                continue
            record_to_clusters.setdefault(record_ref, set()).add(cluster_id)
            edges.append(
                {
                    "id": f"membership:{cluster_id}:{record_ref}",
                    "from": f"cluster:{cluster_id}",
                    "to": f"record:{record_ref}",
                    "label": "contains",
                    "kind": "membership",
                    "color": {"color": "#9aa7b4", "opacity": 0.45},
                    "width": 1,
                }
            )

    for record_ref, record in records.items():
        summary = record_diagram_summary(record)
        record_type = str(record.get("record_type", "") or "record")
        heat = float(record.get("activity_score", 0.0) or 0.0)
        cluster_terms = ", ".join(sorted(record_to_clusters.get(record_ref, set()))) or "unclustered"
        label = f"{record_ref}\\n{record_type}"
        nodes.append(
            {
                "id": f"record:{record_ref}",
                "label": label,
                "title": f"{record_ref}\\n{record_type}\\nheat={heat}\\n{summary}",
                "group": "record",
                "shape": "box",
                "value": max(8, 8 + min(heat, 12)),
                "kind": "record",
                "record_ref": record_ref,
                "meta": {
                    "id": record_ref,
                    "record_type": record_type,
                    "status": record.get("status", ""),
                    "summary": summary,
                    "activity_score": heat,
                    "tap_count": record.get("tap_count", 0),
                    "access_count": record.get("access_count", 0),
                    "clusters": sorted(record_to_clusters.get(record_ref, set())),
                    "cluster_terms": cluster_terms,
                },
            }
        )

    for bridge in bridges:
        left = str(bridge.get("from_topic", ""))
        right = str(bridge.get("to_topic", ""))
        if left and right:
            edges.append(
                {
                    "id": f"bridge:{left}:{right}",
                    "from": f"cluster:{left}",
                    "to": f"cluster:{right}",
                    "label": "bridge",
                    "kind": "bridge",
                    "color": {"color": "#2b8a3e", "opacity": 0.86},
                    "width": 4,
                    "dashes": False,
                }
            )
    for index, probe in enumerate(probes, start=1):
        refs = [str(ref) for ref in probe.get("record_refs", []) if str(ref) in records]
        if len(refs) == 2:
            edges.append(
                {
                    "id": f"probe:{index}:{refs[0]}:{refs[1]}",
                    "from": f"record:{refs[0]}",
                    "to": f"record:{refs[1]}",
                    "label": f"probe {index}",
                    "kind": "probe",
                    "color": {"color": "#b83280", "opacity": 0.9},
                    "width": 3,
                    "dashes": [8, 8],
                    "title": str(probe.get("explanation") or probe.get("reason") or ""),
                    "meta": {
                        "probe_index": index,
                        "score": probe.get("score", 0),
                        "record_refs": refs,
                        "cluster_refs": probe.get("cluster_refs", []),
                        "reason": probe.get("explanation") or probe.get("reason", ""),
                    },
                }
            )

    prompt_items = []
    for prompt in payload.get("curiosity_prompts", []):
        refs = ", ".join(str(ref) for ref in prompt.get("record_refs", []))
        prompt_items.append(
            "<li>"
            f"<strong>probe {escape(str(prompt.get('probe_index', '')))}</strong> "
            f"score={escape(str(prompt.get('score', 0)))} refs={escape(refs)}: "
            f"{escape(str(prompt.get('question', '')))}"
            "</li>"
        )
    prompt_html = "\n".join(prompt_items) or "<li>none</li>"
    title = f"TEP Curiosity Map - {payload.get('mode', 'general')} / {payload.get('volume', 'normal')}"
    metadata = (
        f"scope={payload.get('scope', '')} workspace={payload.get('workspace_ref', '')} "
        f"project={payload.get('project_ref', '')} task={payload.get('task_ref', '')}"
    )
    graph_payload = {
        "nodes": nodes,
        "edges": edges,
        "payload": payload,
        "coldNodeIds": [f"cluster:{topic_id}" for topic_id in sorted(cold_topic_ids)],
        "probeEdgeIds": [edge["id"] for edge in edges if edge.get("kind") == "probe"],
    }
    graph_json = json.dumps(graph_payload, ensure_ascii=False, sort_keys=True).replace("<", "\\u003c")
    payload_json = escape(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True))
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{escape(title)}</title>
  <script src="https://unpkg.com/vis-network@10.0.2/standalone/umd/vis-network.min.js"></script>
  <style>
    :root {{ color-scheme: light; --ink:#17202a; --muted:#5c6773; --panel:#fffdf8; --line:#9aa7b4; --cold:#fff1a8; --cluster:#d7ecff; --record:#f8f9fa; --probe:#b83280; --bridge:#2b8a3e; }}
    * {{ box-sizing:border-box; }}
    body {{ margin:0; font:14px/1.45 ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; color:var(--ink); background:#f4f2ed; }}
    header {{ padding:18px 24px 12px; background:var(--panel); border-bottom:1px solid #ded8cc; }}
    h1 {{ margin:0 0 6px; font-size:22px; }}
    .meta {{ color:var(--muted); }}
    .warning {{ margin-top:10px; padding:9px 12px; background:#fff7db; border:1px solid #e3c76b; border-radius:8px; }}
    .app {{ display:grid; grid-template-columns:minmax(240px, 320px) minmax(500px, 1fr) minmax(280px, 360px); gap:14px; padding:14px; height:calc(100vh - 116px); min-height:620px; }}
    aside,.main {{ background:var(--panel); border:1px solid #d9d1c2; border-radius:16px; box-shadow:0 14px 28px rgba(30,25,15,.08); overflow:hidden; }}
    aside {{ display:flex; flex-direction:column; min-height:0; }}
    .panel-header {{ padding:12px 14px; border-bottom:1px solid #e5dece; font-weight:700; }}
    .panel-body {{ padding:12px 14px; overflow:auto; min-height:0; }}
    .main {{ position:relative; min-height:0; }}
    #network {{ width:100%; height:100%; background:radial-gradient(circle at center, #fffdf9, #ece7dd); }}
    .toolbar {{ position:absolute; z-index:5; left:14px; top:14px; display:flex; flex-wrap:wrap; gap:8px; max-width:calc(100% - 28px); }}
    button,input,select {{ font:inherit; }}
    button {{ border:1px solid #c8bdab; background:#fffaf0; border-radius:999px; padding:7px 10px; cursor:pointer; }}
    button:hover {{ background:#fff1cc; }}
    input {{ width:100%; border:1px solid #c8bdab; border-radius:10px; padding:8px 10px; background:white; }}
    .legend {{ display:grid; gap:8px; }}
    .legend span {{ display:inline-flex; align-items:center; gap:8px; }}
    .dot {{ width:12px; height:12px; border-radius:50%; display:inline-block; border:1px solid #53606d; }}
    .dot.cluster {{ background:var(--cluster); }}
    .dot.cold {{ background:var(--cold); }}
    .dot.record {{ background:var(--record); }}
    .dot.probe {{ background:var(--probe); }}
    .dot.bridge {{ background:var(--bridge); }}
    .node-list,.prompt-list {{ list-style:none; margin:0; padding:0; display:grid; gap:8px; }}
    .node-list button {{ width:100%; text-align:left; border-radius:10px; background:#fff; }}
    .node-list small,.prompt-list small {{ color:var(--muted); display:block; margin-top:2px; }}
    .details-card {{ border:1px solid #e1d8c7; background:#fff; border-radius:12px; padding:10px; margin-bottom:10px; }}
    .details-card strong {{ display:block; margin-bottom:4px; }}
    .details-card code {{ word-break:break-word; }}
    .fallback {{ display:none; margin:14px; padding:12px; border:1px solid #c2410c; background:#fff4ed; border-radius:10px; }}
    body.library-missing .fallback {{ display:block; }}
    body.library-missing #network {{ display:none; }}
    li {{ margin:8px 0; }}
    details {{ margin-top:18px; }}
    pre {{ overflow:auto; background:#161b22; color:#d6deeb; padding:14px; border-radius:10px; }}
    @media (max-width: 980px) {{
      .app {{ grid-template-columns:1fr; height:auto; }}
      .main {{ height:70vh; min-height:520px; }}
    }}
  </style>
</head>
<body>
  <header>
    <h1>{escape(title)}</h1>
    <div class="meta">{escape(metadata)}</div>
    <div class="warning">Generated navigation view only. Inspect canonical records before citing any link, heat, cold zone, or probe as proof.</div>
  </header>
  <div class="app">
    <aside>
      <div class="panel-header">Navigation</div>
      <div class="panel-body">
        <input id="search" placeholder="Filter records or clusters" />
        <h3>Legend</h3>
        <div class="legend">
          <span><i class="dot cluster"></i>Active cluster</span>
          <span><i class="dot cold"></i>Cold cluster</span>
          <span><i class="dot record"></i>Record</span>
          <span><i class="dot bridge"></i>Established bridge</span>
          <span><i class="dot probe"></i>Curiosity probe</span>
        </div>
        <h3>Clusters</h3>
        <ul id="cluster-list" class="node-list"></ul>
      </div>
    </aside>
    <main class="main">
      <div class="toolbar">
        <button id="fit">Fit</button>
        <button id="stabilize">Stabilize</button>
        <button id="cold">Focus cold zones</button>
        <button id="probes">Focus probes</button>
        <button id="reset">Reset filter</button>
      </div>
      <div id="network"></div>
      <div class="fallback">The vis-network library did not load. Check network access or open the embedded payload below.</div>
    </main>
    <aside>
      <div class="panel-header">Selection</div>
      <div class="panel-body">
        <div id="details" class="details-card">Select a node or edge.</div>
        <h3>Curiosity Prompts</h3>
        <ol class="prompt-list">{prompt_html}</ol>
        <details>
          <summary>Embedded non-proof payload</summary>
          <pre>{payload_json}</pre>
        </details>
      </div>
    </aside>
  </div>
  <script id="graph-data" type="application/json">{graph_json}</script>
  <script>
  (function () {{
    const raw = document.getElementById("graph-data").textContent;
    const graph = JSON.parse(raw);
    if (!window.vis || !window.vis.Network) {{
      document.body.classList.add("library-missing");
      return;
    }}
    const nodes = new vis.DataSet(graph.nodes);
    const edges = new vis.DataSet(graph.edges);
    const container = document.getElementById("network");
    const options = {{
      autoResize: true,
      layout: {{ improvedLayout: true }},
      interaction: {{
        hover: true,
        navigationButtons: true,
        keyboard: true,
        multiselect: true,
        tooltipDelay: 120,
      }},
      physics: {{
        enabled: true,
        solver: "forceAtlas2Based",
        stabilization: {{ iterations: 180, fit: true }},
        forceAtlas2Based: {{
          gravitationalConstant: -85,
          centralGravity: 0.015,
          springLength: 125,
          springConstant: 0.08,
          damping: 0.55,
          avoidOverlap: 0.75,
        }},
      }},
      groups: {{
        cluster: {{ color: {{ background: "#d7ecff", border: "#2862a8" }}, font: {{ color: "#17202a", size: 15 }}, borderWidth: 2 }},
        coldCluster: {{ color: {{ background: "#fff1a8", border: "#b7791f" }}, font: {{ color: "#17202a", size: 15 }}, borderWidth: 3 }},
        record: {{ color: {{ background: "#f8f9fa", border: "#68737f" }}, font: {{ color: "#17202a", size: 12, multi: true }}, margin: 10, borderWidth: 1 }},
      }},
      edges: {{
        smooth: {{ type: "dynamic" }},
        font: {{ size: 10, align: "middle", strokeWidth: 3, strokeColor: "#fffdf8" }},
        arrows: {{ to: {{ enabled: false }} }},
      }},
    }};
    const network = new vis.Network(container, {{ nodes, edges }}, options);
    let physicsFrozen = false;
    const details = document.getElementById("details");
    const clusterList = document.getElementById("cluster-list");
    const allNodeIds = nodes.getIds();
    const allEdgeIds = edges.getIds();

    function freezePhysics() {{
      if (physicsFrozen) return;
      physicsFrozen = true;
      network.setOptions({{ physics: false }});
    }}
    function html(text) {{
      return String(text ?? "").replace(/[&<>"']/g, ch => ({{ "&": "&amp;", "<": "&lt;", ">": "&gt;", "\\"": "&quot;", "'": "&#39;" }}[ch]));
    }}
    function renderDetails(item) {{
      if (!item) {{
        details.innerHTML = "Select a node or edge.";
        return;
      }}
      if (item.kind === "cluster") {{
        details.innerHTML = `<strong>${{html(item.meta.term)}}</strong><code>${{html(item.meta.id)}}</code><p>records=${{html(item.meta.record_count)}} heat=${{html(item.meta.activity_score)}} cold=${{html(item.meta.cold)}}</p>`;
        return;
      }}
      if (item.kind === "record") {{
        details.innerHTML = `<strong>${{html(item.record_ref)}}</strong><p>${{html(item.meta.record_type)}} status=${{html(item.meta.status)}} heat=${{html(item.meta.activity_score)}}</p><p>${{html(item.meta.summary)}}</p><p><small>clusters: ${{html(item.meta.cluster_terms)}}</small></p>`;
        return;
      }}
      if (item.kind === "probe") {{
        details.innerHTML = `<strong>Curiosity probe ${{html(item.meta.probe_index)}}</strong><p>score=${{html(item.meta.score)}} refs=${{html(item.meta.record_refs.join(", "))}}</p><p>${{html(item.meta.reason)}}</p>`;
        return;
      }}
      details.innerHTML = `<strong>${{html(item.kind || "edge")}}</strong><pre>${{html(JSON.stringify(item.meta || item, null, 2))}}</pre>`;
    }}
    function focusNodes(ids) {{
      const existing = ids.filter(id => nodes.get(id));
      if (!existing.length) return;
      network.selectNodes(existing);
      network.fit({{ nodes: existing, animation: {{ duration: 450, easingFunction: "easeInOutQuad" }} }});
    }}
    function resetVisibility() {{
      nodes.update(allNodeIds.map(id => ({{ id, hidden: false }})));
      edges.update(allEdgeIds.map(id => ({{ id, hidden: false }})));
      network.fit({{ animation: true }});
    }}
    function filterGraph(term) {{
      const query = term.trim().toLowerCase();
      if (!query) {{
        resetVisibility();
        return;
      }}
      const visible = new Set();
      nodes.forEach(node => {{
        const haystack = JSON.stringify(node).toLowerCase();
        if (haystack.includes(query)) visible.add(node.id);
      }});
      edges.forEach(edge => {{
        if (visible.has(edge.from) || visible.has(edge.to)) {{
          visible.add(edge.from);
          visible.add(edge.to);
        }}
      }});
      nodes.update(allNodeIds.map(id => ({{ id, hidden: !visible.has(id) }})));
      edges.update(allEdgeIds.map(id => {{
        const edge = edges.get(id);
        return {{ id, hidden: !(visible.has(edge.from) && visible.has(edge.to)) }};
      }}));
      focusNodes(Array.from(visible).slice(0, 40));
    }}
    function renderClusterList() {{
      const clusters = nodes.get().filter(node => node.kind === "cluster");
      clusterList.innerHTML = clusters.map(node => `<li><button data-node="${{html(node.id)}}">${{html(node.meta.term)}}<small>${{html(node.meta.id)}} records=${{html(node.meta.record_count)}} heat=${{html(node.meta.activity_score)}}</small></button></li>`).join("") || "<li>none</li>";
      clusterList.querySelectorAll("button[data-node]").forEach(button => {{
        button.addEventListener("click", () => focusNodes([button.getAttribute("data-node")]));
      }});
    }}
    network.on("selectNode", params => renderDetails(nodes.get(params.nodes[0])));
    network.on("selectEdge", params => renderDetails(edges.get(params.edges[0])));
    document.getElementById("fit").addEventListener("click", () => network.fit({{ animation: true }}));
    document.getElementById("stabilize").addEventListener("click", () => {{
      physicsFrozen = false;
      network.setOptions({{ physics: {{ enabled: true }} }});
      network.stabilize(120);
    }});
    document.getElementById("cold").addEventListener("click", () => focusNodes(graph.coldNodeIds || []));
    document.getElementById("probes").addEventListener("click", () => {{
      const edgeIds = graph.probeEdgeIds || [];
      const ids = new Set();
      edgeIds.forEach(edgeId => {{
        const edge = edges.get(edgeId);
        if (edge) {{ ids.add(edge.from); ids.add(edge.to); }}
      }});
      network.selectEdges(edgeIds);
      focusNodes(Array.from(ids));
    }});
    document.getElementById("reset").addEventListener("click", resetVisibility);
    document.getElementById("search").addEventListener("input", event => filterGraph(event.target.value));
    renderClusterList();
    network.on("stabilizationIterationsDone", () => {{
      freezePhysics();
      network.fit({{ animation: true }});
    }});
    setTimeout(freezePhysics, 1800);
  }})();
  </script>
</body>
</html>
"""


def curiosity_probe_text_lines(payload: dict, *, limit: int) -> list[str]:
    probes = payload.get("probes", [])
    lines = [
        "# Curiosity Probes",
        "",
        "Mode: generated questions for bounded inspection. Not proof.",
        f"scope: `{payload.get('scope', 'all')}` mode: `{payload.get('mode', 'general')}` workspace: `{payload.get('workspace_ref', '')}` project: `{payload.get('project_ref', '')}` task: `{payload.get('task_ref', '')}`",
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
