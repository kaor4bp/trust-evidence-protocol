"""Pure evidence-chain reasoning validation helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .claims import claim_is_fallback
from .evidence import quote_matches_record
from .search import concise


VALID_CHAIN_ROLES = {
    "fact",
    "observation",
    "hypothesis",
    "exploration_context",
    "permission",
    "requested_permission",
    "restriction",
    "guideline",
    "proposal",
    "task",
    "working_context",
    "project",
    "model",
    "flow",
    "open_question",
}
DECISION_MODES = {
    "planning",
    "permission",
    "edit",
    "model",
    "flow",
    "proposal",
    "final",
    "curiosity",
    "debugging",
}
PROOF_DECISION_MODES = {"permission", "edit", "model", "flow", "final"}
UNCERTAIN_DECISION_MODES = {"planning", "proposal", "curiosity", "debugging"}

CONTROL_CHAIN_ROLES = {"permission", "requested_permission", "restriction", "guideline", "proposal"}
CONTEXT_CHAIN_ROLES = {"exploration_context", "project", "working_context"}
TRUTH_CHAIN_ROLES = {"fact", "observation", "hypothesis"}
NON_PROOF_REF_PREFIXES = ("BCK-", "BACKEND-", "CIX-")
NON_PROOF_REF_SCHEMES = ("backend:", "candidate:", "generated:", "topic_index:", "logic_index:", "attention_index:")


def _default_chain_quote(record: dict) -> str:
    for key in ("statement", "rule", "quote", "summary", "question", "position", "title", "subject", "note"):
        value = str(record.get(key, "")).strip()
        if value:
            return value
    for key in ("grants", "rules", "examples", "assumptions", "concerns"):
        values = record.get(key, [])
        if isinstance(values, list):
            for value in values:
                if isinstance(value, dict):
                    text = str(value.get("text", "")).strip()
                else:
                    text = str(value).strip()
                if text:
                    return text
    return ""


def _record_public_summary(record: dict) -> dict[str, Any]:
    lifecycle = record.get("lifecycle", {}) if isinstance(record.get("lifecycle"), dict) else {}
    payload = {
        "id": record.get("id", ""),
        "record_type": record.get("record_type", ""),
        "status": record.get("status", ""),
        "summary": concise(
            str(
                record.get("statement")
                or record.get("rule")
                or record.get("summary")
                or record.get("question")
                or record.get("title")
                or record.get("subject")
                or record.get("position")
                or record.get("note")
                or ""
            ),
            220,
        ),
    }
    if record.get("plane"):
        payload["plane"] = record.get("plane")
    if lifecycle:
        payload["lifecycle"] = {
            key: lifecycle.get(key)
            for key in ("state", "attention", "resolved_at", "archived_at", "historical_at")
            if lifecycle.get(key)
        }
    return payload


def _source_quote_items(records: dict[str, dict], record: dict) -> list[dict[str, str]]:
    items = []
    for source_ref in record.get("source_refs", []):
        source = records.get(str(source_ref), {})
        if not source:
            continue
        items.append(
            {
                "ref": str(source_ref),
                "quote": concise(str(source.get("quote") or source.get("note") or ""), 260),
            }
        )
    return items


@dataclass(frozen=True)
class EvidenceChainValidation:
    nodes: list[dict[str, Any]]
    edges: list[dict[str, Any]]
    display_nodes: list[dict[str, Any]]
    roles_by_ref: dict[str, str]
    errors: list[str]
    warnings: list[str]

    @property
    def ok(self) -> bool:
        return not self.errors


def validate_chain_node(
    records: dict[str, dict],
    hypothesis_entries: dict[str, dict],
    node: dict,
    index: int,
) -> tuple[str | None, list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    role = str(node.get("role", "")).strip()
    ref = str(node.get("ref", "")).strip()
    quote = str(node.get("quote", "")).strip()
    if role not in VALID_CHAIN_ROLES:
        errors.append(f"node[{index}] has invalid role `{role}`")
    if not ref:
        if role == "hypothesis":
            errors.append(
                f"node[{index}] hypothesis missing ref; record it as CLM(status=tentative) and add it with `hypothesis add`"
            )
        else:
            errors.append(f"node[{index}] missing ref")
        return None, errors, warnings
    if ref.startswith(NON_PROOF_REF_PREFIXES) or ref.startswith(NON_PROOF_REF_SCHEMES):
        errors.append(f"node[{index}] `{ref}` is generated/backend/navigation output and cannot be used as proof")
        return ref, errors, warnings
    if role == "requested_permission":
        if not quote:
            errors.append(f"node[{index}] requested_permission `{ref}` missing requested grant quote")
        return ref, errors, warnings
    record = records.get(ref)
    if record is None:
        errors.append(f"node[{index}] missing record `{ref}`")
        return ref, errors, warnings
    if not quote:
        errors.append(f"node[{index}] `{ref}` missing quote")
    elif not quote_matches_record(records, record, quote):
        errors.append(f"node[{index}] quote does not match `{ref}` or its source quotes")

    record_type = record.get("record_type")
    status = str(record.get("status", "")).strip()
    if role == "fact":
        if record_type != "claim":
            errors.append(f"node[{index}] fact `{ref}` must reference claim")
        elif status not in {"supported", "corroborated"}:
            errors.append(f"node[{index}] fact `{ref}` must be supported/corroborated, got `{status}`")
        elif claim_is_fallback(record):
            errors.append(f"node[{index}] fact `{ref}` is lifecycle fallback/archived and cannot be decisive proof")
    elif role == "observation":
        if record_type != "claim":
            errors.append(f"node[{index}] observation `{ref}` must reference claim")
        elif record.get("plane") != "runtime":
            errors.append(f"node[{index}] observation `{ref}` must be runtime-plane claim")
        elif claim_is_fallback(record):
            errors.append(f"node[{index}] observation `{ref}` is lifecycle fallback/archived and cannot be decisive proof")
    elif role == "hypothesis":
        if record_type != "claim":
            errors.append(f"node[{index}] hypothesis `{ref}` must reference claim")
        elif status != "tentative":
            errors.append(f"node[{index}] hypothesis `{ref}` must be tentative, got `{status}`")
        elif claim_is_fallback(record):
            errors.append(f"node[{index}] hypothesis `{ref}` is lifecycle fallback/archived and cannot be decisive proof")
        entry = hypothesis_entries.get(ref, {})
        if not entry:
            errors.append(
                f"node[{index}] hypothesis `{ref}` requires an active hypothesis index entry; "
                f"run `hypothesis add --claim {ref}`"
            )
        if entry.get("mode") == "exploration" or entry.get("based_on_hypotheses"):
            errors.append(
                f"node[{index}] `{ref}` is an exploration or hypothesis-derived hypothesis; "
                "evidence chains cannot use unconfirmed exploration hypotheses as proof"
            )
    elif role == "exploration_context":
        if record_type != "claim":
            errors.append(f"node[{index}] exploration_context `{ref}` must reference claim")
        elif status != "tentative":
            errors.append(f"node[{index}] exploration_context `{ref}` must be tentative, got `{status}`")
    elif role in {
        "permission",
        "restriction",
        "guideline",
        "proposal",
        "task",
        "working_context",
        "project",
        "model",
        "flow",
        "open_question",
    } and record_type != role:
        errors.append(f"node[{index}] {role} `{ref}` must reference {role} record")
    if status in {"superseded", "stale", "contested", "rejected"}:
        warnings.append(f"node[{index}] `{ref}` has status `{status}`")
    return ref, errors, warnings


def validate_evidence_chain_payload(
    records: dict[str, dict],
    hypothesis_entries: dict[str, dict],
    payload: dict,
) -> EvidenceChainValidation:
    nodes = payload.get("nodes", [])
    edges = payload.get("edges", [])
    errors: list[str] = []
    warnings: list[str] = []
    if not isinstance(nodes, list) or not nodes:
        errors.append("evidence chain must define non-empty nodes")
        nodes = []
    if not isinstance(edges, list) or not edges:
        errors.append("evidence chain must define non-empty edges")
        edges = []

    known_node_refs: set[str] = set()
    roles_by_ref: dict[str, str] = {}
    display_nodes: list[dict[str, Any]] = []
    for index, node in enumerate(nodes):
        if not isinstance(node, dict):
            errors.append(f"node[{index}] must be an object")
            continue
        ref, node_errors, node_warnings = validate_chain_node(records, hypothesis_entries, node, index)
        errors.extend(node_errors)
        warnings.extend(node_warnings)
        if ref:
            known_node_refs.add(ref)
            roles_by_ref[ref] = str(node.get("role", "")).strip()
            display_nodes.append(node)

    for index, edge in enumerate(edges):
        if not isinstance(edge, dict):
            errors.append(f"edge[{index}] must be an object")
            continue
        source = str(edge.get("from", "")).strip()
        target = str(edge.get("to", "")).strip()
        if source not in known_node_refs:
            errors.append(f"edge[{index}] references unknown from `{source}`")
        if target not in known_node_refs:
            errors.append(f"edge[{index}] references unknown to `{target}`")
        if roles_by_ref.get(source) in CONTROL_CHAIN_ROLES and roles_by_ref.get(target) in TRUTH_CHAIN_ROLES:
            errors.append(f"edge[{index}] uses authorization/control `{source}` as truth support for `{target}`")
        if roles_by_ref.get(source) in CONTEXT_CHAIN_ROLES and roles_by_ref.get(target) in TRUTH_CHAIN_ROLES:
            errors.append(f"edge[{index}] uses context `{source}` as proof support for `{target}`")
        if roles_by_ref.get(source) == "task" and roles_by_ref.get(target) in TRUTH_CHAIN_ROLES:
            errors.append(f"edge[{index}] uses task `{source}` as truth support for `{target}`")

    has_fact = any(role == "fact" for role in roles_by_ref.values())
    if not has_fact:
        errors.append("evidence chain must include at least one fact node")

    return EvidenceChainValidation(
        nodes=nodes,
        edges=edges,
        display_nodes=display_nodes,
        roles_by_ref=roles_by_ref,
        errors=errors,
        warnings=warnings,
    )


def decision_validation_payload(
    records: dict[str, dict],
    hypothesis_entries: dict[str, dict],
    payload: dict,
    mode: str,
) -> dict[str, Any]:
    validation = validate_evidence_chain_payload(records, hypothesis_entries, payload)
    mode = mode if mode in DECISION_MODES else "planning"
    hypothesis_refs = [
        ref
        for ref, role in sorted(validation.roles_by_ref.items())
        if role == "hypothesis"
    ]
    exploration_refs = [
        ref
        for ref, role in sorted(validation.roles_by_ref.items())
        if role == "exploration_context"
    ]
    hypothesis_modes = {
        ref: str(hypothesis_entries.get(ref, {}).get("mode") or "missing")
        for ref in hypothesis_refs
    }
    blockers = list(validation.errors)
    warnings = list(validation.warnings)
    if hypothesis_refs:
        warnings.append(
            "decision chain contains tentative hypotheses; they express uncertainty and are not proof"
        )
    if exploration_refs:
        warnings.append(
            "decision chain contains exploration_context nodes; they may motivate probes but are not proof"
        )
    if mode in PROOF_DECISION_MODES and hypothesis_refs:
        blockers.append(
            f"mode `{mode}` cannot use hypothesis nodes as decisive proof: {', '.join(hypothesis_refs)}"
        )
    if mode in PROOF_DECISION_MODES and exploration_refs:
        blockers.append(
            f"mode `{mode}` cannot use exploration_context nodes as decisive proof: {', '.join(exploration_refs)}"
        )
    if mode == "permission" and "requested_permission" not in set(validation.roles_by_ref.values()):
        blockers.append("mode `permission` requires a requested_permission node")

    if blockers:
        valid_for = [item for item in sorted(UNCERTAIN_DECISION_MODES) if item != mode]
        if validation.errors:
            valid_for = []
    elif hypothesis_refs:
        valid_for = sorted(UNCERTAIN_DECISION_MODES)
    elif exploration_refs:
        valid_for = ["curiosity", "debugging", "planning"]
    else:
        valid_for = sorted(DECISION_MODES)
    invalid_for = [item for item in sorted(DECISION_MODES) if item not in valid_for]
    recommended_commands = []
    for ref in hypothesis_refs:
        if ref not in hypothesis_entries:
            recommended_commands.append(
                f"hypothesis add --claim {ref} --mode durable "
                f"--note 'used by validate-decision mode={mode}'"
            )
    return {
        "decision_validation_is_proof": False,
        "mode": mode,
        "decision_valid": not blockers and mode in valid_for,
        "valid_for": valid_for,
        "invalid_for": invalid_for,
        "hypothesis_refs": hypothesis_refs,
        "hypothesis_modes": hypothesis_modes,
        "exploration_context_refs": exploration_refs,
        "validation": {
            "ok": validation.ok,
            "error_count": len(validation.errors),
            "warning_count": len(validation.warnings),
            "errors": validation.errors,
            "warnings": validation.warnings,
        },
        "blockers": blockers,
        "warnings": warnings,
        "recommended_commands": recommended_commands,
    }


def decision_validation_text_lines(payload: dict, icon: str) -> list[str]:
    lines = [
        f"# {icon} Decision Chain Check",
        "",
        f"mode: `{payload.get('mode')}` decision_valid=`{payload.get('decision_valid')}` proof=`{payload.get('decision_validation_is_proof')}`",
        f"valid_for: `{', '.join(payload.get('valid_for', [])) or 'none'}`",
        f"invalid_for: `{', '.join(payload.get('invalid_for', [])) or 'none'}`",
        "",
    ]
    if payload.get("hypothesis_refs"):
        lines.append("## Hypotheses")
        for ref in payload.get("hypothesis_refs", []):
            mode = payload.get("hypothesis_modes", {}).get(ref, "")
            lines.append(f"- `{ref}` mode=`{mode}`")
        lines.append("")
    if payload.get("exploration_context_refs"):
        lines.append("## Exploration Context")
        for ref in payload.get("exploration_context_refs", []):
            lines.append(f"- `{ref}`")
        lines.append("")
    if payload.get("warnings"):
        lines.append("## Warnings")
        for warning in payload.get("warnings", []):
            lines.append(f"- {warning}")
        lines.append("")
    if payload.get("blockers"):
        lines.append("## Blockers")
        for blocker in payload.get("blockers", []):
            lines.append(f"- {blocker}")
        lines.append("")
    if payload.get("recommended_commands"):
        lines.append("## Recommended Commands")
        for command in payload.get("recommended_commands", []):
            lines.append(f"- `{command}`")
        lines.append("")
    if payload.get("decision_valid"):
        lines.append("## Result")
        lines.append("- OK: decision chain is valid for the requested mode")
    return lines


def augment_evidence_chain_payload(
    records: dict[str, dict],
    hypothesis_entries: dict[str, dict],
    payload: dict,
) -> dict[str, Any]:
    nodes = payload.get("nodes", [])
    augmented_payload = dict(payload)
    augmented_nodes: list[Any] = []
    if isinstance(nodes, list):
        for node in nodes:
            if not isinstance(node, dict):
                augmented_nodes.append(node)
                continue
            augmented_node = dict(node)
            ref = str(augmented_node.get("ref", "")).strip()
            record = records.get(ref)
            if record:
                if not str(augmented_node.get("quote", "")).strip():
                    default_quote = _default_chain_quote(record)
                    if default_quote:
                        augmented_node["quote"] = default_quote
                        augmented_node["quote_source"] = "record"
                else:
                    augmented_node["quote_source"] = "input"
                augmented_node["record"] = _record_public_summary(record)
                source_quotes = _source_quote_items(records, record)
                if source_quotes:
                    augmented_node["source_quotes"] = source_quotes
                if ref in hypothesis_entries:
                    entry = {
                        key: value
                        for key, value in hypothesis_entries[ref].items()
                        if not str(key).startswith("_")
                    }
                    augmented_node["hypothesis_entry"] = entry
            augmented_nodes.append(augmented_node)
    augmented_payload["nodes"] = augmented_nodes
    validation = validate_evidence_chain_payload(records, hypothesis_entries, augmented_payload)
    return {
        "augment_is_read_only": True,
        "chain": augmented_payload,
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


def evidence_chain_report_lines(validation: EvidenceChainValidation, payload: dict, icon: str) -> list[str]:
    lines = [
        f"# {icon} Evidence Chain Check",
        "",
        f"Task: {payload.get('task', '')}",
        f"Chain: {len(validation.nodes)} node(s), {len(validation.edges)} edge(s)",
        "",
    ]
    if validation.display_nodes:
        lines.append("## User-Facing Chain")
        for index, node in enumerate(validation.display_nodes):
            arrow = " ->" if index < len(validation.display_nodes) - 1 else ""
            lines.append(
                f"- {node.get('role')} `{node.get('ref')}`: "
                f"\"{concise(str(node.get('quote', '')), 220)}\"{arrow}"
            )
        lines.append("")
    if validation.warnings:
        lines.append("## Warnings")
        for warning in validation.warnings:
            lines.append(f"- {warning}")
        lines.append("")
    if validation.errors:
        lines.append("## Blockers")
        for error in validation.errors:
            lines.append(f"- {error}")
        return lines
    lines.extend(
        [
            "## Result",
            "- OK: evidence chain is mechanically valid",
            "- OK: quotes match referenced records or their sources",
            "- OK: role/status constraints passed",
        ]
    )
    return lines


def augmented_evidence_chain_text_lines(payload: dict, icon: str) -> list[str]:
    chain = payload.get("chain", {})
    validation_payload = payload.get("validation", {})
    validation = EvidenceChainValidation(
        nodes=chain.get("nodes", []) if isinstance(chain.get("nodes", []), list) else [],
        edges=chain.get("edges", []) if isinstance(chain.get("edges", []), list) else [],
        display_nodes=[
            node
            for node in chain.get("nodes", [])
            if isinstance(node, dict) and str(node.get("ref", "")).strip()
        ]
        if isinstance(chain.get("nodes", []), list)
        else [],
        roles_by_ref={
            str(node.get("ref", "")).strip(): str(node.get("role", "")).strip()
            for node in chain.get("nodes", [])
            if isinstance(node, dict) and str(node.get("ref", "")).strip()
        }
        if isinstance(chain.get("nodes", []), list)
        else {},
        errors=list(validation_payload.get("errors", [])),
        warnings=list(validation_payload.get("warnings", [])),
    )
    lines = [
        f"# {icon} Augmented Evidence Chain",
        "",
        "Mode: read-only augmentation. No records were changed.",
        "",
    ]
    lines.extend(evidence_chain_report_lines(validation, chain, icon))
    return lines
