"""Input-provenance record helpers."""

from __future__ import annotations


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
