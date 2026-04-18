from __future__ import annotations


def default_independence_group(source_kind: str, timestamp: str) -> str:
    return f"{source_kind}-ingest-{timestamp.replace(':', '').replace('+', '_')}"


def build_source_payload(
    record_id: str,
    source_kind: str,
    scope: str,
    critique_status: str,
    origin_kind: str,
    origin_ref: str,
    quote: str,
    artifact_refs: list[str],
    confidence: str | None,
    independence_group: str | None,
    captured_at: str | None,
    captured_timestamp: str,
    independence_timestamp: str,
    project_refs: list[str],
    task_refs: list[str],
    tags: list[str],
    red_flags: list[str],
    note: str,
) -> dict:
    payload = {
        "id": record_id,
        "record_type": "source",
        "source_kind": source_kind,
        "scope": scope.strip(),
        "captured_at": (captured_at or captured_timestamp).strip(),
        "critique_status": critique_status,
        "independence_group": (
            independence_group or default_independence_group(source_kind, independence_timestamp)
        ).strip(),
        "origin": {
            "kind": origin_kind.strip(),
            "ref": origin_ref.strip(),
        },
        "project_refs": project_refs,
        "task_refs": task_refs,
        "artifact_refs": artifact_refs,
        "quote": quote.strip(),
        "tags": tags,
        "red_flags": red_flags,
        "note": note.strip(),
    }
    if confidence:
        payload["confidence"] = confidence
    return payload
