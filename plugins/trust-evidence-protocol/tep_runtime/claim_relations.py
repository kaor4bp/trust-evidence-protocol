"""CLM-to-CLM relation claim helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .claims import claim_is_archived


RELATION_CLAIM_KIND = "relation"
RELATION_KINDS = {"supports", "causes", "depends_on", "implies", "refines", "co_relevant"}
PROOF_RELATION_KINDS = {"supports", "causes", "depends_on", "implies", "refines"}
NAVIGATION_RELATION_KINDS = {"co_relevant"}


@dataclass(frozen=True)
class RelationShape:
    kind: str
    subject_refs: tuple[str, ...]
    object_refs: tuple[str, ...]

    @property
    def is_structural(self) -> bool:
        return bool(self.kind and self.subject_refs and self.object_refs)


def _as_refs(payload: dict[str, Any], singular_key: str, plural_key: str) -> tuple[list[str], list[str]]:
    singular = str(payload.get(singular_key, "")).strip()
    raw_plural = payload.get(plural_key, [])
    if raw_plural is None:
        raw_plural = []
    if not isinstance(raw_plural, list):
        return [], [f"relation.{plural_key} must be a list"]
    plural = [str(item).strip() for item in raw_plural if str(item).strip()]
    if singular and plural:
        return [], [f"relation must use either {singular_key} or {plural_key}, not both"]
    refs = [singular] if singular else plural
    return refs, []


def normalize_relation_payload(payload: dict[str, Any]) -> tuple[RelationShape | None, list[str]]:
    """Normalize a relation object and return schema-level validation errors."""

    if not isinstance(payload, dict):
        return None, ["relation must be an object"]
    errors: list[str] = []
    kind = str(payload.get("kind", "")).strip()
    if kind not in RELATION_KINDS:
        errors.append("relation.kind must be supports, causes, depends_on, implies, refines, or co_relevant")
    if "scope_refs" in payload:
        errors.append("relation.scope_refs is not allowed; relation CLM-* records are general facts")

    subject_refs, subject_errors = _as_refs(payload, "subject_ref", "subject_refs")
    object_refs, object_errors = _as_refs(payload, "object_ref", "object_refs")
    errors.extend(subject_errors)
    errors.extend(object_errors)
    if not subject_refs:
        errors.append("relation requires subject_ref or subject_refs")
    if not object_refs:
        errors.append("relation requires object_ref or object_refs")
    for ref in subject_refs + object_refs:
        if not ref.startswith("CLM-"):
            errors.append(f"relation ref must be CLM-*: {ref}")
    if set(subject_refs).intersection(object_refs):
        errors.append("relation subject and object refs must not overlap")
    if len(subject_refs) != len(set(subject_refs)):
        errors.append("relation subject refs must be unique")
    if len(object_refs) != len(set(object_refs)):
        errors.append("relation object refs must be unique")
    if len(subject_refs) > 1 and len(object_refs) > 1:
        errors.append("relation may aggregate only one side; use separate one-to-one relations or an explicit aggregate CLM")
    if errors:
        return None, errors
    return RelationShape(kind, tuple(sorted(subject_refs)), tuple(sorted(object_refs))), []


def relation_shape_for_claim(record: dict[str, Any]) -> RelationShape | None:
    if record.get("record_type") != "claim" or record.get("claim_kind") != RELATION_CLAIM_KIND:
        return None
    shape, errors = normalize_relation_payload(record.get("relation", {}))
    if errors:
        return None
    return shape


def relation_claim_overlaps(records: dict[str, dict], candidate: dict[str, Any]) -> list[str]:
    """Return active relation overlap errors for a candidate relation claim.

    The validator is intentionally strict only for single-subject relations. It
    blocks accidental duplicate/partial appends such as A causes B followed by
    A causes C. Multi-subject tentative aggregates stay possible, but they are
    not proof-capable in the STEP validator.
    """

    if candidate.get("claim_kind") != RELATION_CLAIM_KIND:
        return []
    candidate_shape = relation_shape_for_claim(candidate)
    if candidate_shape is None:
        return []
    errors: list[str] = []
    candidate_id = str(candidate.get("id", "")).strip()
    candidate_status = str(candidate.get("status", "")).strip()
    candidate_confidence = str(candidate.get("confidence", "")).strip()
    candidate_plane = str(candidate.get("plane", "")).strip()
    for record in records.values():
        record_id = str(record.get("id", "")).strip()
        if record_id == candidate_id or claim_is_archived(record):
            continue
        shape = relation_shape_for_claim(record)
        if shape is None or shape.kind != candidate_shape.kind:
            continue
        if shape.subject_refs == candidate_shape.subject_refs and shape.object_refs == candidate_shape.object_refs:
            errors.append(f"relation duplicates active claim {record_id}")
            continue
        if len(shape.subject_refs) == 1 and shape.subject_refs == candidate_shape.subject_refs:
            existing_objects = set(shape.object_refs)
            candidate_objects = set(candidate_shape.object_refs)
            if existing_objects.intersection(candidate_objects) or existing_objects != candidate_objects:
                same_trust = (
                    str(record.get("status", "")).strip() == candidate_status
                    and str(record.get("confidence", "")).strip() == candidate_confidence
                    and str(record.get("plane", "")).strip() == candidate_plane
                )
                if same_trust:
                    errors.append(
                        f"relation overlaps active claim {record_id}; archive it or record one merged relation "
                        "with the full object_refs set"
                    )
                else:
                    errors.append(
                        f"relation overlaps active claim {record_id} with different trust/status; review before merging"
                    )
    return errors


def relation_connects(shape: RelationShape, previous_claim_ref: str, next_claim_ref: str) -> bool:
    return previous_claim_ref in shape.subject_refs and next_claim_ref in shape.object_refs
