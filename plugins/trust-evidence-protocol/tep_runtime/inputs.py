"""Input-provenance record helpers."""

from __future__ import annotations

from .search import concise


def build_input_payload(
    *,
    record_id: str,
    scope: str,
    input_kind: str,
    origin_kind: str,
    origin_ref: str,
    text: str,
    artifact_refs: list[str],
    session_ref: str | None,
    derived_record_refs: list[str],
    captured_at: str | None,
    captured_timestamp: str,
    project_refs: list[str],
    task_refs: list[str],
    tags: list[str],
    note: str,
) -> dict:
    payload = {
        "id": record_id,
        "record_type": "input",
        "input_kind": input_kind,
        "scope": scope.strip(),
        "captured_at": (captured_at or captured_timestamp).strip(),
        "origin": {
            "kind": origin_kind.strip(),
            "ref": origin_ref.strip(),
        },
        "project_refs": project_refs,
        "task_refs": task_refs,
        "artifact_refs": artifact_refs,
        "text": text,
        "derived_record_refs": derived_record_refs,
        "tags": tags,
        "note": note.strip(),
    }
    if session_ref and session_ref.strip():
        payload["session_ref"] = session_ref.strip()
    return payload


def input_classification_refs(data: dict, records: dict[str, dict]) -> list[str]:
    refs: list[str] = []
    for ref in data.get("derived_record_refs", []):
        ref_id = str(ref).strip()
        if ref_id in records:
            refs.append(ref_id)
    input_ref = str(data.get("id", "")).strip()
    if not input_ref:
        return sorted(set(refs))
    for record_id, record in records.items():
        if record_id == input_ref:
            continue
        if input_ref in [str(ref).strip() for ref in record.get("input_refs", [])]:
            refs.append(record_id)
    return sorted(set(refs))


def input_is_classified(data: dict, records: dict[str, dict]) -> bool:
    if data.get("record_type") != "input":
        return True
    return bool(input_classification_refs(data, records))


def unclassified_input_items(records: dict[str, dict]) -> list[dict]:
    items: list[dict] = []
    for record_id, data in sorted(records.items()):
        if data.get("record_type") != "input":
            continue
        if input_is_classified(data, records):
            continue
        items.append(
            {
                "id": record_id,
                "summary": concise(str(data.get("text") or data.get("note") or ""), 180),
                "project_refs": data.get("project_refs", []),
                "task_refs": data.get("task_refs", []),
                "workspace_refs": data.get("workspace_refs", []),
            }
        )
    return items


def input_items_for_task(records: dict[str, dict], task_ref: str | None = None) -> list[dict]:
    items = unclassified_input_items(records)
    if not task_ref:
        return items
    return [
        item
        for item in items
        if task_ref in [str(ref).strip() for ref in item.get("task_refs", [])]
    ]
