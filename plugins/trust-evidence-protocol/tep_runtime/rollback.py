"""Rollback and impact report helpers."""

from __future__ import annotations


def build_impact_graph_payload(claim_ref: str, impact: dict) -> dict:
    return {
        "claim_ref": claim_ref,
        "direct": impact.get("direct", []),
        "direct_by_type": impact.get("direct_by_type", {}),
        "transitive_only_by_type": impact.get("transitive_only_by_type", {}),
    }


def impact_graph_text_lines(payload: dict) -> list[str]:
    lines = [
        f"Anchor claim: {payload.get('claim_ref', '')}",
        "",
        "Directly affected:",
    ]
    direct_by_type = payload.get("direct_by_type", {})
    if not payload.get("direct"):
        lines.append("- none")
    else:
        for record_type, ids in sorted(direct_by_type.items()):
            lines.append(f"- {record_type}: {', '.join(ids)}")

    lines.extend(["", "Transitively affected:"])
    transitive_only_by_type = payload.get("transitive_only_by_type", {})
    if not transitive_only_by_type:
        lines.append("- none")
    else:
        for record_type, ids in sorted(transitive_only_by_type.items()):
            lines.append(f"- {record_type}: {', '.join(ids)}")
    return lines


def build_rollback_report_payload(
    records: dict[str, dict],
    claim_ref: str,
    impact: dict,
    hypothesis_entries: list[dict],
) -> dict:
    matching_entries = [
        entry
        for entry in hypothesis_entries
        if str(entry.get("claim_ref", "")).strip() == claim_ref
    ]
    stale_candidates = [
        record_id
        for record_id in impact.get("transitive", [])
        if record_id in records and records[record_id].get("record_type") in {"model", "flow"}
    ]
    return {
        "claim_ref": claim_ref,
        "direct_by_type": impact.get("direct_by_type", {}),
        "transitive_only_by_type": impact.get("transitive_only_by_type", {}),
        "stale_candidates": stale_candidates,
        "hypothesis_entries": matching_entries,
    }


def rollback_report_text_lines(payload: dict) -> list[str]:
    lines = [
        f"Rollback report for {payload.get('claim_ref', '')}",
        "",
        "Directly affected:",
    ]
    direct_by_type = payload.get("direct_by_type", {})
    if not direct_by_type:
        lines.append("- none")
    else:
        for record_type, ids in sorted(direct_by_type.items()):
            lines.append(f"- {record_type}: {', '.join(ids)}")

    lines.extend(["", "Transitively affected:"])
    transitive_only_by_type = payload.get("transitive_only_by_type", {})
    if not transitive_only_by_type:
        lines.append("- none")
    else:
        for record_type, ids in sorted(transitive_only_by_type.items()):
            lines.append(f"- {record_type}: {', '.join(ids)}")

    lines.extend(["", "Stale candidates:"])
    stale_candidates = payload.get("stale_candidates", [])
    if not stale_candidates:
        lines.append("- none")
    else:
        lines.append(f"- {', '.join(stale_candidates)}")

    lines.extend(["", "Hypothesis index entries:"])
    hypothesis_entries = payload.get("hypothesis_entries", [])
    if not hypothesis_entries:
        lines.append("- none")
    else:
        for entry in hypothesis_entries:
            used_by = entry.get("used_by", {})
            rollback_refs = entry.get("rollback_refs", [])
            lines.append(
                f"- status={entry.get('status', '')} scope={entry.get('scope', '')} "
                f"used_by={used_by} rollback_refs={rollback_refs}"
            )
    return lines
