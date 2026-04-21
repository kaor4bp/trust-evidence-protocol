"""Append-only navigation telemetry for TEP lookup activity."""

from __future__ import annotations

import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


CLAIM_JSON_PATTERN = re.compile(r"(?P<ref>CLM-\d{8}-[0-9a-f]{8})\.json")


def now_utc_timestamp() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def activity_root(root: Path) -> Path:
    return root / "activity"


def access_log_path(root: Path) -> Path:
    return activity_root(root) / "access.jsonl"


def append_access_event(root: Path, event: dict) -> None:
    payload = dict(event)
    payload.setdefault("accessed_at", now_utc_timestamp())
    payload.setdefault("access_is_proof", False)
    path = access_log_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False, sort_keys=True))
        handle.write("\n")


def load_access_events(root: Path) -> tuple[list[dict], list[str]]:
    path = access_log_path(root)
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
                errors.append(f"{path}: line {line_no}: access event must be an object")
                continue
            events.append(item)
    return events, errors


def claim_refs_from_text(value: str) -> list[str]:
    return sorted({match.group("ref") for match in CLAIM_JSON_PATTERN.finditer(value)})


def command_reads_raw_claims(command: str) -> bool:
    return "records/claim" in command or bool(CLAIM_JSON_PATTERN.search(command))


def access_event_record_refs(event: dict) -> list[str]:
    refs = event.get("record_refs", [])
    if isinstance(refs, list):
        return [str(ref) for ref in refs if str(ref).strip()]
    ref = str(event.get("record_ref") or "").strip()
    return [ref] if ref else []


def access_report_payload(events: Iterable[dict], *, limit: int = 10) -> dict:
    event_list = list(events)
    by_channel = Counter(str(event.get("channel") or "unknown") for event in event_list)
    by_tool = Counter(str(event.get("tool") or "unknown") for event in event_list)
    by_kind = Counter(str(event.get("access_kind") or "unknown") for event in event_list)
    by_reason = Counter(str(event.get("reason") or "unspecified") for event in event_list)
    by_wctx = Counter(str(event.get("working_context_ref") or "none") for event in event_list)
    record_counter: Counter[str] = Counter()
    record_by_reason: Counter[tuple[str, str]] = Counter()
    for event in event_list:
        for record_ref in access_event_record_refs(event):
            record_counter[record_ref] += 1
            record_by_reason[(str(event.get("reason") or "unspecified"), record_ref)] += 1
    raw_events = [
        event
        for event in event_list
        if str(event.get("access_kind") or "").startswith("raw_") or int(event.get("raw_path_count") or 0) > 0
    ]
    top_tool, top_tool_count = by_tool.most_common(1)[0] if by_tool else ("", 0)
    top_record, top_record_count = record_counter.most_common(1)[0] if record_counter else ("", 0)
    anomalies: list[dict] = []
    if raw_events:
        anomalies.append(
            {
                "kind": "raw-record-read",
                "severity": "warning",
                "count": len(raw_events),
                "message": "Raw record reads bypass compact MCP/CLI projections; prefer record_detail, claim_graph, or linked_records.",
                "recommended_tools": ["record_detail", "claim_graph", "linked_records"],
                "next_action": "Replace raw file reads with compact MCP/CLI record projections before expanding full records.",
            }
        )
    if event_list and top_tool_count / max(1, len(event_list)) >= 0.5 and len(event_list) >= 10:
        anomalies.append(
            {
                "kind": "tool-concentration",
                "severity": "info",
                "tool": top_tool,
                "count": top_tool_count,
                "message": "One lookup tool dominates recent telemetry; consider a more targeted route or generated view.",
                "recommended_tools": ["next_step", "brief_context", "claim_graph"],
                "next_action": "Ask for a route or compact brief before repeating broad lookup commands.",
            }
        )
    if event_list and by_channel.get("cli", 0) > by_channel.get("mcp", 0) * 2 and len(event_list) >= 10:
        anomalies.append(
            {
                "kind": "low-mcp-ratio",
                "severity": "info",
                "cli_count": by_channel.get("cli", 0),
                "mcp_count": by_channel.get("mcp", 0),
                "message": "CLI lookup dominates MCP lookup; prefer MCP for read-only context retrieval when available.",
                "recommended_tools": ["telemetry_report", "record_detail", "code_search"],
                "next_action": "Use MCP read-only tools for compact context retrieval when available; keep CLI for mutations and diagnostics.",
            }
        )
    if top_record_count >= 5:
        anomalies.append(
            {
                "kind": "hot-record",
                "severity": "info",
                "record_ref": top_record,
                "count": top_record_count,
                "message": "One record is repeatedly accessed; consider linking it from a model, flow, WCTX, or guideline if it is a recurring anchor.",
                "recommended_tools": ["linked_records", "record_detail", "working_contexts"],
                "next_action": "Promote recurring anchors into a model, flow, WCTX, or guideline link instead of repeatedly rediscovering them.",
            }
        )
    return {
        "telemetry_is_proof": False,
        "event_count": len(event_list),
        "raw_event_count": len(raw_events),
        "raw_path_count": sum(int(event.get("raw_path_count") or 0) for event in raw_events),
        "by_channel": dict(sorted(by_channel.items())),
        "by_tool": dict(sorted(by_tool.items())),
        "by_access_kind": dict(sorted(by_kind.items())),
        "by_reason": dict(sorted(by_reason.items())),
        "by_working_context": dict(sorted(by_wctx.items())),
        "top_records": [
            {"record_ref": record_ref, "access_count": count}
            for record_ref, count in record_counter.most_common(max(1, limit))
        ],
        "top_records_by_reason": [
            {"reason": reason, "record_ref": record_ref, "access_count": count}
            for (reason, record_ref), count in record_by_reason.most_common(max(1, limit))
        ],
        "recent_raw_events": raw_events[-max(1, limit) :],
        "anomalies": anomalies,
    }


def access_report_text_lines(payload: dict) -> list[str]:
    lines = [
        "# TEP Telemetry Report",
        "",
        "Telemetry is navigation data only. It is not proof.",
        f"events: `{payload.get('event_count', 0)}` raw_events: `{payload.get('raw_event_count', 0)}` raw_paths: `{payload.get('raw_path_count', 0)}`",
        "",
        "## By Tool",
    ]
    for tool, count in payload.get("by_tool", {}).items():
        lines.append(f"- `{tool}`: `{count}`")
    if not payload.get("by_tool"):
        lines.append("- none")
    lines.append("")
    lines.append("## By Access Kind")
    for kind, count in payload.get("by_access_kind", {}).items():
        lines.append(f"- `{kind}`: `{count}`")
    if not payload.get("by_access_kind"):
        lines.append("- none")
    lines.append("")
    lines.append("## By Reason")
    for reason, count in payload.get("by_reason", {}).items():
        lines.append(f"- `{reason}`: `{count}`")
    if not payload.get("by_reason"):
        lines.append("- none")
    lines.append("")
    lines.append("## By Working Context")
    for context_ref, count in payload.get("by_working_context", {}).items():
        lines.append(f"- `{context_ref}`: `{count}`")
    if not payload.get("by_working_context"):
        lines.append("- none")
    lines.append("")
    lines.append("## Top Records")
    for item in payload.get("top_records", []):
        lines.append(f"- `{item.get('record_ref')}` accesses=`{item.get('access_count')}`")
    if not payload.get("top_records"):
        lines.append("- none")
    lines.append("")
    lines.append("## Anomalies")
    for item in payload.get("anomalies", []):
        prefix = f"- `{item.get('kind')}` severity=`{item.get('severity')}`"
        detail = str(item.get("message") or "").strip()
        lines.append(f"{prefix}: {detail}" if detail else prefix)
        recommended_tools = item.get("recommended_tools") or []
        if recommended_tools:
            rendered_tools = ", ".join(f"`{tool}`" for tool in recommended_tools)
            lines.append(f"  suggested tools: {rendered_tools}")
        next_action = str(item.get("next_action") or "").strip()
        if next_action:
            lines.append(f"  next action: {next_action}")
    if not payload.get("anomalies"):
        lines.append("- none")
    return lines
