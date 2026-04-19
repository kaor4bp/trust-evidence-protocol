"""Candidate fact validation backends for TEP records.

The functions in this module intentionally produce navigation/diagnostic
candidates. They never create proof and never replace source-backed records.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .backends import BACKEND_IS_PROOF, backend_status_payload, select_backend_status
from .records import load_records


TEP_CONTEXT = {
    "tep": "https://trust-evidence-protocol.local/vocab#",
    "id": "@id",
    "type": "@type",
    "status": "tep:status",
    "recordType": "tep:recordType",
    "plane": "tep:plane",
    "lifecycleState": "tep:lifecycleState",
    "supportedBy": {"@id": "tep:supportedBy", "@type": "@id"},
    "contradicts": {"@id": "tep:contradicts", "@type": "@id"},
    "scopedTo": {"@id": "tep:scopedTo", "@type": "@id"},
}
RDF_EXPORT_IS_PROOF = False


def _candidate(
    *,
    backend: str,
    record_ref: str,
    shape_ref: str,
    message: str,
    severity: str = "violation",
    source_refs: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "candidate_kind": "validation_candidate",
        "candidate_is_proof": False,
        "backend": backend,
        "backend_output_is_proof": BACKEND_IS_PROOF,
        "record_ref": record_ref,
        "shape_ref": shape_ref,
        "message": message,
        "severity": severity,
        "source_refs": source_refs or [],
    }


def _record_workspace_refs(record: dict) -> list[str]:
    refs = record.get("workspace_refs", [])
    if not isinstance(refs, list):
        return []
    return [str(ref).strip() for ref in refs if str(ref).strip()]


def _claim_source_refs(record: dict) -> list[str]:
    refs = record.get("source_refs", [])
    if not isinstance(refs, list):
        return []
    return [str(ref).strip() for ref in refs if str(ref).strip()]


def _logic_symbols(record: dict) -> list[dict]:
    logic = record.get("logic", {})
    if not isinstance(logic, dict):
        return []
    symbols = logic.get("symbols", [])
    if not isinstance(symbols, list):
        return []
    return [symbol for symbol in symbols if isinstance(symbol, dict)]


def fake_rdf_shacl_candidates(records: dict[str, dict], *, backend: str = "rdf_shacl") -> list[dict[str, Any]]:
    """Run deterministic SHACL-shaped checks without pySHACL.

    This is deliberately small and conservative. It exercises the adapter
    contract and validates the first high-value constraints while real pySHACL
    integration remains optional.
    """

    candidates: list[dict[str, Any]] = []
    for record_id, record in sorted(records.items()):
        record_type = str(record.get("record_type", "")).strip()
        status = str(record.get("status", "")).strip()
        if record_type == "claim":
            source_refs = _claim_source_refs(record)
            if status in {"supported", "corroborated"} and not source_refs:
                candidates.append(
                    _candidate(
                        backend=backend,
                        record_ref=record_id,
                        shape_ref="tep:SupportedClaimHasSource",
                        message="supported/corroborated CLM-* must cite at least one SRC-*",
                        source_refs=[],
                    )
                )
            contradiction_refs = record.get("contradiction_refs", [])
            if status == "corroborated" and isinstance(contradiction_refs, list) and contradiction_refs:
                candidates.append(
                    _candidate(
                        backend=backend,
                        record_ref=record_id,
                        shape_ref="tep:CorroboratedClaimHasNoContradictions",
                        message="corroborated CLM-* must not keep unresolved contradiction_refs",
                        source_refs=source_refs,
                    )
                )
            for index, symbol in enumerate(_logic_symbols(record), start=1):
                if not str(symbol.get("meaning", "")).strip():
                    candidates.append(
                        _candidate(
                            backend=backend,
                            record_ref=record_id,
                            shape_ref="tep:LogicSymbolHasMeaning",
                            message=f"CLM.logic.symbols[{index}] must explain semantic meaning",
                            source_refs=source_refs,
                        )
                    )

        for workspace_ref in _record_workspace_refs(record):
            workspace = records.get(workspace_ref)
            if not workspace or workspace.get("record_type") != "workspace":
                candidates.append(
                    _candidate(
                        backend=backend,
                        record_ref=record_id,
                        shape_ref="tep:WorkspaceRefExists",
                        message=f"workspace_ref `{workspace_ref}` must reference a WSP-* workspace record",
                        severity="violation",
                        source_refs=_claim_source_refs(record),
                    )
                )
    return candidates


def _record_iri(record_ref: str) -> str:
    return f"urn:tep:record:{record_ref}"


def _record_type_iri(record_type: str) -> str:
    normalized = "".join(part.capitalize() for part in str(record_type).split("_") if part)
    return f"tep:{normalized or 'Record'}"


def _list_refs(record: dict, key: str) -> list[str]:
    refs = record.get(key, [])
    if not isinstance(refs, list):
        return []
    return [str(ref).strip() for ref in refs if str(ref).strip()]


def _scoped_refs(record: dict) -> list[str]:
    refs: list[str] = []
    for key in ("workspace_refs", "project_refs", "task_refs"):
        refs.extend(_list_refs(record, key))
    return refs


def rdf_jsonld_payload(root: Path) -> dict[str, Any]:
    records, load_errors = load_records(root)
    graph: list[dict[str, Any]] = []
    for record_id, record in sorted(records.items()):
        record_type = str(record.get("record_type") or "record")
        lifecycle = record.get("lifecycle", {}) if isinstance(record.get("lifecycle"), dict) else {}
        node: dict[str, Any] = {
            "id": _record_iri(record_id),
            "type": _record_type_iri(record_type),
            "recordType": record_type,
        }
        for key, output_key in (("status", "status"), ("plane", "plane")):
            value = str(record.get(key, "")).strip()
            if value:
                node[output_key] = value
        lifecycle_state = str(lifecycle.get("state", "")).strip()
        if lifecycle_state:
            node["lifecycleState"] = lifecycle_state
        source_refs = _list_refs(record, "source_refs")
        if source_refs:
            node["supportedBy"] = [_record_iri(ref) for ref in source_refs]
        contradiction_refs = _list_refs(record, "contradiction_refs")
        if contradiction_refs:
            node["contradicts"] = [_record_iri(ref) for ref in contradiction_refs]
        scoped_refs = _scoped_refs(record)
        if scoped_refs:
            node["scopedTo"] = [_record_iri(ref) for ref in scoped_refs]
        graph.append(node)
    return {
        "export_is_proof": RDF_EXPORT_IS_PROOF,
        "format": "jsonld",
        "context": str(root),
        "load_error_count": len(load_errors),
        "@context": TEP_CONTEXT,
        "@graph": graph,
    }


def _turtle_literal(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def rdf_turtle_text(root: Path) -> str:
    payload = rdf_jsonld_payload(root)
    lines = [
        "@prefix tep: <https://trust-evidence-protocol.local/vocab#> .",
        "@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .",
        "",
        "# export_is_proof=false",
    ]
    for node in payload["@graph"]:
        subject = f"<{node['id']}>"
        lines.append(f"{subject} a {node['type']} ;")
        predicates: list[str] = [f"  tep:recordType {_turtle_literal(str(node.get('recordType', '')))}"]
        for key, predicate in (("status", "tep:status"), ("plane", "tep:plane"), ("lifecycleState", "tep:lifecycleState")):
            if node.get(key):
                predicates.append(f"  {predicate} {_turtle_literal(str(node[key]))}")
        for key, predicate in (("supportedBy", "tep:supportedBy"), ("contradicts", "tep:contradicts"), ("scopedTo", "tep:scopedTo")):
            refs = node.get(key, [])
            if isinstance(refs, list) and refs:
                objects = ", ".join(f"<{ref}>" for ref in refs)
                predicates.append(f"  {predicate} {objects}")
        for index, predicate_line in enumerate(predicates):
            suffix = " ." if index == len(predicates) - 1 else " ;"
            lines.append(predicate_line + suffix)
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def export_rdf_text(root: Path, *, output_format: str) -> str:
    if output_format == "jsonld":
        return json.dumps(rdf_jsonld_payload(root), indent=2, ensure_ascii=False) + "\n"
    if output_format == "turtle":
        return rdf_turtle_text(root)
    raise ValueError(f"unsupported RDF export format: {output_format}")


def validate_facts_payload(root: Path, *, backend: str = "rdf_shacl") -> dict[str, Any]:
    records, load_errors = load_records(root)
    status_payload = backend_status_payload(root)
    status_matches = select_backend_status(status_payload, f"fact_validation.{backend}")
    if not status_matches:
        status_matches = select_backend_status(status_payload, backend)
    backend_status = status_matches[0] if status_matches else {}
    mode = str(backend_status.get("mode") or "fake")

    warnings = [str(warning) for warning in backend_status.get("warnings", [])]
    setup_hint = str(backend_status.get("setup_hint") or "")
    available = bool(backend_status.get("available"))
    if mode == "fake":
        available = True
        if "fake backend returns deterministic validation candidates only" not in warnings:
            warnings.append("fake backend returns deterministic validation candidates only")

    candidates: list[dict[str, Any]] = []
    if backend in {"rdf_shacl", "builtin"} and available:
        candidates = fake_rdf_shacl_candidates(records, backend=backend)
    elif not available and setup_hint:
        warnings.append(setup_hint)

    for error in load_errors:
        candidates.append(
            _candidate(
                backend=backend,
                record_ref=str(error.path),
                shape_ref="tep:RecordLoadable",
                message=error.message,
                severity="violation",
            )
        )

    return {
        "validation_is_proof": False,
        "backend_output_is_proof": BACKEND_IS_PROOF,
        "backend": backend,
        "mode": mode,
        "available": available,
        "setup_hint": setup_hint,
        "warnings": warnings,
        "candidate_count": len(candidates),
        "candidates": candidates,
    }


def validate_facts_text_lines(payload: dict[str, Any]) -> list[str]:
    lines = [
        "# TEP Fact Validation",
        "",
        "Validation output is diagnostic/navigation data only. It is not proof.",
        f"backend=`{payload.get('backend')}` mode=`{payload.get('mode')}` available=`{str(payload.get('available')).lower()}`",
        f"candidates={payload.get('candidate_count', 0)}",
    ]
    warnings = payload.get("warnings", [])
    if warnings:
        lines.append("")
        lines.append("## Warnings")
        for warning in warnings:
            lines.append(f"- {warning}")
    candidates = payload.get("candidates", [])
    if candidates:
        lines.append("")
        lines.append("## Candidates")
        for candidate in candidates:
            lines.append(
                f"- {candidate.get('severity')} `{candidate.get('record_ref')}` "
                f"{candidate.get('shape_ref')}: {candidate.get('message')}"
            )
    return lines
