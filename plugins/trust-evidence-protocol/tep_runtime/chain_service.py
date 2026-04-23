"""Evidence-chain service wrappers shared by CLI and MCP adapters."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .contracts.chain import ChainValidationResponse
from .hypotheses import active_hypothesis_entry_by_claim
from .reasoning import (
    EvidenceChainValidation,
    augment_evidence_chain_payload,
    augmented_evidence_chain_text_lines,
    evidence_chain_report_lines,
    validate_evidence_chain_payload,
)


def read_chain_payload_file(chain_file: Path) -> tuple[dict[str, Any] | None, str | None]:
    try:
        payload = json.loads(chain_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return None, f"{chain_file}: {exc}"
    if not isinstance(payload, dict):
        return None, f"{chain_file}: evidence chain must be a JSON object"
    return payload, None


def validate_chain_service(
    root: Path,
    records: dict[str, dict],
    *,
    chain_payload: dict[str, Any],
) -> dict[str, Any]:
    hypothesis_entries = active_hypothesis_entry_by_claim(root, records)
    validation = validate_evidence_chain_payload(records, hypothesis_entries, chain_payload)
    augmented = augment_evidence_chain_payload(records, hypothesis_entries, chain_payload)
    missing_links = [
        {"message": error}
        for error in validation.errors
        if "missing" in error or "unknown" in error
    ]
    repair = [{"message": _repair_hint(error)} for error in validation.errors]
    return ChainValidationResponse(
        valid=validation.ok,
        proof_allowed=validation.ok,
        augmented_nodes=augmented.get("chain", {}).get("nodes", []),
        missing_links=missing_links,
        gaps=[{"message": warning} for warning in validation.warnings],
        repair=repair,
    ).to_payload() | {
        "validate_chain_is_proof": False,
        "validation": {
            "ok": validation.ok,
            "error_count": len(validation.errors),
            "warning_count": len(validation.warnings),
            "errors": validation.errors,
            "warnings": validation.warnings,
        },
        "user_facing_chain": [
            {
                "role": node.get("role", ""),
                "ref": node.get("ref", ""),
                "quote": node.get("quote", ""),
            }
            for node in validation.display_nodes
        ],
    }


def validate_chain_text(payload: dict[str, Any], chain_payload: dict[str, Any], icon: str) -> str:
    validation_payload = payload.get("validation", {})
    validation = _validation_from_report(
        chain_payload,
        errors=validation_payload.get("errors", []),
        warnings=validation_payload.get("warnings", []),
    )
    return "\n".join(evidence_chain_report_lines(validation, chain_payload, icon))


def augment_chain_service(
    root: Path,
    records: dict[str, dict],
    *,
    chain_payload: dict[str, Any],
) -> dict[str, Any]:
    hypothesis_entries = active_hypothesis_entry_by_claim(root, records)
    return augment_evidence_chain_payload(records, hypothesis_entries, chain_payload)


def augment_chain_text(payload: dict[str, Any], icon: str) -> str:
    return "\n".join(augmented_evidence_chain_text_lines(payload, icon))


def _validation_from_report(
    chain_payload: dict[str, Any],
    *,
    errors: Any,
    warnings: Any,
) -> EvidenceChainValidation:
    nodes = chain_payload.get("nodes", [])
    edges = chain_payload.get("edges", [])
    safe_nodes = nodes if isinstance(nodes, list) else []
    return EvidenceChainValidation(
        nodes=safe_nodes,
        edges=edges if isinstance(edges, list) else [],
        display_nodes=[node for node in safe_nodes if isinstance(node, dict) and str(node.get("ref", "")).strip()],
        roles_by_ref={
            str(node.get("ref", "")).strip(): str(node.get("role", "")).strip()
            for node in safe_nodes
            if isinstance(node, dict) and str(node.get("ref", "")).strip()
        },
        errors=[str(error) for error in errors if str(error).strip()] if isinstance(errors, list) else [],
        warnings=[str(warning) for warning in warnings if str(warning).strip()] if isinstance(warnings, list) else [],
    )


def _repair_hint(error: str) -> str:
    if "missing quote" in error:
        return f"{error}; run augment_chain to surface canonical quotes"
    if "requires an active hypothesis index entry" in error:
        return f"{error}; add or close the hypothesis index entry before proof use"
    if "missing record" in error or "unknown" in error:
        return f"{error}; rerun lookup and rebuild the chain from canonical refs"
    return error
