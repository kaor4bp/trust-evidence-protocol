"""Record dependency and link-graph helpers."""

from __future__ import annotations

from .claims import claim_attention, claim_lifecycle, claim_lifecycle_state
from .search import concise, public_record_summary


def _safe_list(data: dict, key: str) -> list[str]:
    value = data.get(key, [])
    if value in (None, ""):
        return []
    if not isinstance(value, list):
        return []
    return [str(item) for item in value]


def _clean_items(values) -> list[str]:
    if not isinstance(values, list):
        return []
    return [str(item).strip() for item in values if str(item).strip()]


def dependency_refs_for_record(data: dict) -> set[str]:
    refs: set[str] = set()
    record_type = str(data.get("record_type", "")).strip()
    refs.update(_safe_list(data, "project_refs"))
    refs.update(_safe_list(data, "task_refs"))
    refs.update(_safe_list(data, "restriction_refs"))
    refs.update(_safe_list(data, "related_project_refs"))
    refs.update(_safe_list(data, "input_refs"))
    refs.update(_safe_list(data, "file_refs"))
    refs.update(_safe_list(data, "run_refs"))

    if record_type == "input":
        refs.update(_safe_list(data, "derived_record_refs"))
    elif record_type == "claim":
        refs.update(_safe_list(data, "source_refs"))
        refs.update(_safe_list(data, "support_refs"))
        refs.update(_safe_list(data, "contradiction_refs"))
        refs.update(_safe_list(data, "derived_from"))
        lifecycle = claim_lifecycle(data)
        refs.update(_safe_list(lifecycle, "resolved_by_claim_refs"))
        refs.update(_safe_list(lifecycle, "resolved_by_action_refs"))
    elif record_type == "restriction":
        refs.update(_safe_list(data, "related_claim_refs"))
        refs.update(_safe_list(data, "supersedes_refs"))
    elif record_type == "guideline":
        refs.update(_safe_list(data, "source_refs"))
        refs.update(_safe_list(data, "related_claim_refs"))
        refs.update(_safe_list(data, "conflict_refs"))
        refs.update(_safe_list(data, "supersedes_refs"))
    elif record_type == "proposal":
        refs.update(_safe_list(data, "claim_refs"))
        refs.update(_safe_list(data, "guideline_refs"))
        refs.update(_safe_list(data, "model_refs"))
        refs.update(_safe_list(data, "flow_refs"))
        refs.update(_safe_list(data, "open_question_refs"))
        refs.update(_safe_list(data, "supersedes_refs"))
    elif record_type == "action":
        refs.update(_safe_list(data, "justified_by"))
        refs.update(_safe_list(data, "hypothesis_refs"))
    elif record_type == "task":
        refs.update(_safe_list(data, "related_claim_refs"))
        refs.update(_safe_list(data, "related_model_refs"))
        refs.update(_safe_list(data, "related_flow_refs"))
        refs.update(_safe_list(data, "open_question_refs"))
        refs.update(_safe_list(data, "plan_refs"))
        refs.update(_safe_list(data, "debt_refs"))
        refs.update(_safe_list(data, "action_refs"))
        refs.update(_safe_list(data, "working_context_refs"))
    elif record_type == "working_context":
        refs.update(ref for ref in _safe_list(data, "pinned_refs") if not str(ref).startswith("CIX-"))
        refs.update(_safe_list(data, "topic_seed_refs"))
        refs.update(_safe_list(data, "supersedes_refs"))
        assumptions = data.get("assumptions", [])
        if isinstance(assumptions, list):
            for assumption in assumptions:
                if isinstance(assumption, dict):
                    refs.update(_safe_list(assumption, "support_refs"))
        parent_ref = str(data.get("parent_context_ref", "")).strip()
        if parent_ref:
            refs.add(parent_ref)
    elif record_type == "plan":
        refs.update(_safe_list(data, "justified_by"))
        refs.update(_safe_list(data, "blocked_by"))
    elif record_type == "debt":
        refs.update(_safe_list(data, "evidence_refs"))
        refs.update(_safe_list(data, "plan_refs"))
    elif record_type == "model":
        refs.update(_safe_list(data, "claim_refs"))
        refs.update(_safe_list(data, "open_question_refs"))
        refs.update(_safe_list(data, "hypothesis_refs"))
        refs.update(_safe_list(data, "related_model_refs"))
        refs.update(_safe_list(data, "supersedes_refs"))
        refs.update(_safe_list(data, "promoted_from_refs"))
    elif record_type == "flow":
        refs.update(_safe_list(data, "model_refs"))
        refs.update(_safe_list(data, "open_question_refs"))
        refs.update(_safe_list(data, "supersedes_refs"))
        refs.update(_safe_list(data, "promoted_from_refs"))
        for block_name in ("preconditions", "oracle"):
            block = data.get(block_name)
            if isinstance(block, dict):
                for key in ("claim_refs", "success_claim_refs", "failure_claim_refs", "hypothesis_refs"):
                    refs.update(_clean_items(block.get(key, [])))
        steps = data.get("steps", [])
        if isinstance(steps, list):
            for step in steps:
                if not isinstance(step, dict):
                    continue
                refs.update(_clean_items(step.get("claim_refs", [])))
                refs.update(_clean_items(step.get("open_question_refs", [])))
                refs.update(_clean_items(step.get("accepted_deviation_refs", [])))
    elif record_type == "open_question":
        refs.update(_safe_list(data, "related_claim_refs"))
        refs.update(_safe_list(data, "related_model_refs"))
        refs.update(_safe_list(data, "related_flow_refs"))
        refs.update(_safe_list(data, "resolved_by_claim_refs"))

    return refs


def ref_paths(value, target_ref: str, prefix: str = "") -> list[str]:
    paths: list[str] = []
    if isinstance(value, dict):
        for key, nested in value.items():
            if str(key).startswith("_"):
                continue
            nested_prefix = f"{prefix}.{key}" if prefix else str(key)
            paths.extend(ref_paths(nested, target_ref, nested_prefix))
    elif isinstance(value, list):
        for index, nested in enumerate(value):
            nested_prefix = f"{prefix}[{index}]"
            if nested == target_ref:
                paths.append(prefix)
            else:
                paths.extend(ref_paths(nested, target_ref, nested_prefix))
    elif value == target_ref:
        paths.append(prefix)
    return sorted({path for path in paths if path})


def collect_link_edges(records: dict[str, dict]) -> list[dict]:
    edges: list[dict] = []
    for source_id, data in sorted(records.items()):
        for target_id in sorted(dependency_refs_for_record(data)):
            if target_id not in records:
                continue
            fields = ref_paths(data, target_id)
            edges.append(
                {
                    "from": source_id,
                    "to": target_id,
                    "fields": fields or ["<unknown>"],
                }
            )
    return edges


def linked_records_payload(records: dict[str, dict], record_ref: str, direction: str, depth: int) -> dict:
    depth = max(1, depth)
    edges = collect_link_edges(records)
    outgoing_by_ref: dict[str, list[dict]] = {}
    incoming_by_ref: dict[str, list[dict]] = {}
    for edge in edges:
        outgoing_by_ref.setdefault(edge["from"], []).append(edge)
        incoming_by_ref.setdefault(edge["to"], []).append(edge)

    selected_edges: list[dict] = []
    records_by_distance: dict[int, set[str]] = {0: {record_ref}}
    seen = {record_ref}
    frontier = {record_ref}
    for distance in range(1, depth + 1):
        next_frontier: set[str] = set()
        frontier_edges: list[dict] = []
        for current in sorted(frontier):
            if direction in {"outgoing", "both"}:
                frontier_edges.extend(outgoing_by_ref.get(current, []))
            if direction in {"incoming", "both"}:
                frontier_edges.extend(incoming_by_ref.get(current, []))
        for edge in frontier_edges:
            neighbor = edge["to"] if edge["from"] in frontier else edge["from"]
            if neighbor not in records:
                continue
            selected_edges.append(edge)
            if neighbor not in seen:
                seen.add(neighbor)
                next_frontier.add(neighbor)
        if not next_frontier:
            break
        records_by_distance[distance] = next_frontier
        frontier = next_frontier

    def edge_key(edge: dict) -> tuple:
        return edge["from"], edge["to"], tuple(edge["fields"])

    selected_edges = sorted({edge_key(edge): edge for edge in selected_edges}.values(), key=edge_key)
    return {
        "anchor": public_record_summary(records[record_ref]),
        "direction": direction,
        "depth": depth,
        "records": [public_record_summary(records[record_id]) for record_id in sorted(seen - {record_ref})],
        "records_by_distance": {
            str(distance): sorted(ids)
            for distance, ids in sorted(records_by_distance.items())
            if distance > 0
        },
        "edges": selected_edges,
        "_outgoing_by_ref": outgoing_by_ref,
        "_incoming_by_ref": incoming_by_ref,
    }


def _public_record_payload(data: dict) -> dict:
    return {key: value for key, value in data.items() if not str(key).startswith("_")}


def record_detail_payload(records: dict[str, dict], record_ref: str, depth: int = 1) -> dict:
    graph = linked_records_payload(records, record_ref, "both", depth)
    graph = {key: value for key, value in graph.items() if not key.startswith("_")}
    data = records[record_ref]
    source_quotes = []
    for source_ref in data.get("source_refs", []):
        source = records.get(source_ref)
        if source and source.get("record_type") == "source":
            source_quotes.append(
                {
                    "id": source_ref,
                    "source_kind": source.get("source_kind", ""),
                    "critique_status": source.get("critique_status", ""),
                    "quote": source.get("quote", ""),
                    "artifact_refs": source.get("artifact_refs", []),
                }
            )
    return {
        "record": _public_record_payload(data),
        "summary": public_record_summary(data),
        "source_quotes": source_quotes,
        "links": graph,
    }


def record_detail_text_lines(payload: dict) -> list[str]:
    record = payload["record"]
    record_id = record.get("id")
    lines = [
        "# Record Detail",
        "",
        f"ID: `{record_id}`",
        f"Type: `{record.get('record_type')}`",
        f"Scope: `{record.get('scope', '')}`",
    ]
    status = record.get("status", record.get("critique_status", ""))
    if status:
        lines.append(f"Status: `{status}`")
    if record.get("record_type") == "claim":
        lines.append(f"Lifecycle: `{claim_lifecycle_state(record)}` attention=`{claim_attention(record)}`")
    for key in ("project_refs", "task_refs", "tags"):
        values = record.get(key, [])
        if values:
            lines.append(f"{key}: {values}")
    lines.extend([f"Summary: {payload['summary']['summary']}", ""])

    if payload["source_quotes"]:
        lines.append("## Source Quotes")
        for source in payload["source_quotes"]:
            quote = concise(str(source.get("quote", "")) or ", ".join(source.get("artifact_refs", [])), 260)
            lines.append(
                f"- `{source['id']}` kind=`{source.get('source_kind')}` "
                f"critique=`{source.get('critique_status')}` quote=\"{quote}\""
            )
        lines.append("")

    links = payload["links"]
    lines.append("## Direct Links")
    direct_edges = [edge for edge in links["edges"] if edge["from"] == record_id or edge["to"] == record_id]
    if direct_edges:
        for edge in direct_edges:
            direction = "out" if edge["from"] == record_id else "in"
            other_ref = edge["to"] if direction == "out" else edge["from"]
            lines.append(f"- {direction}: `{other_ref}` via `{', '.join(edge['fields'])}`")
    else:
        lines.append("- none")
    return lines
