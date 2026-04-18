from __future__ import annotations

import json
from pathlib import Path

from tep_runtime.claims import claim_is_fallback
from tep_runtime.reports import rel_display, write_report
from tep_runtime.validation import ensure_list


CLAIM_COMPARATORS = {"exact", "boolean"}
CLAIM_POLARITIES = {"affirmed", "denied"}


def _comparison_arg(args, name: str):
    return getattr(args, f"comparison_{name}", None)


def _parse_boolean_comparison_value(value: str | bool) -> bool:
    if isinstance(value, bool):
        return value
    normalized = str(value).strip().lower()
    if normalized == "true":
        return True
    if normalized == "false":
        return False
    raise ValueError("boolean comparison values must be true or false")


def build_comparison_payload(args) -> dict | None:
    raw_values = {
        "key": _comparison_arg(args, "key"),
        "subject": _comparison_arg(args, "subject"),
        "aspect": _comparison_arg(args, "aspect"),
        "comparator": _comparison_arg(args, "comparator"),
        "value": _comparison_arg(args, "value"),
        "polarity": _comparison_arg(args, "polarity"),
        "context_scope": _comparison_arg(args, "context_scope"),
    }
    if not any(value is not None for value in raw_values.values()):
        return None

    required = {
        "comparison.key": raw_values["key"],
        "comparison.subject": raw_values["subject"],
        "comparison.aspect": raw_values["aspect"],
        "comparison.comparator": raw_values["comparator"],
        "comparison.value": raw_values["value"],
        "comparison.polarity": raw_values["polarity"],
    }
    missing = [label for label, value in required.items() if value in ("", None)]
    if missing:
        raise ValueError(f"incomplete comparison payload; missing {', '.join(missing)}")

    value: str | bool = raw_values["value"]
    if raw_values["comparator"] == "boolean":
        value = _parse_boolean_comparison_value(value)

    comparison = {
        "key": str(raw_values["key"]).strip(),
        "subject": str(raw_values["subject"]).strip(),
        "aspect": str(raw_values["aspect"]).strip(),
        "comparator": raw_values["comparator"],
        "value": value,
        "polarity": raw_values["polarity"],
    }
    if raw_values["context_scope"]:
        comparison["context_scope"] = str(raw_values["context_scope"]).strip()
    return comparison


def validate_claim_comparison(comparison: dict) -> list[str]:
    errors: list[str] = []
    key = str(comparison.get("key", "")).strip()
    subject = str(comparison.get("subject", "")).strip()
    aspect = str(comparison.get("aspect", "")).strip()
    comparator = str(comparison.get("comparator", "")).strip()
    polarity = str(comparison.get("polarity", "")).strip()

    if not key:
        errors.append("comparison.key is required")
    if not subject:
        errors.append("comparison.subject is required")
    if not aspect:
        errors.append("comparison.aspect is required")
    if comparator not in CLAIM_COMPARATORS:
        errors.append("comparison.comparator must be exact or boolean")
    if polarity not in CLAIM_POLARITIES:
        errors.append("comparison.polarity must be affirmed or denied")
    if "value" not in comparison:
        errors.append("comparison.value is required")
    else:
        value = comparison.get("value")
        if comparator == "boolean" and not isinstance(value, bool):
            errors.append("comparison.value must be boolean when comparator=boolean")
        if comparator == "exact" and (isinstance(value, (dict, list)) or value is None):
            errors.append("comparison.value must be a scalar when comparator=exact")
    context_scope = comparison.get("context_scope")
    if context_scope is not None and not isinstance(context_scope, str):
        errors.append("comparison.context_scope must be a string when provided")
    return errors


def comparison_signature(comparison: dict) -> str:
    comparator = str(comparison.get("comparator", "")).strip()
    polarity = str(comparison.get("polarity", "")).strip()
    value = comparison.get("value")
    if comparator == "boolean":
        rendered = "true" if value else "false"
    else:
        rendered = json.dumps(value, ensure_ascii=False, sort_keys=True)
    return f"{polarity}:{rendered}"


def collect_conflict_lines(root: Path, records: dict[str, dict]) -> list[str]:
    lines: list[str] = []
    comparable_claims: dict[tuple[str, str, str], list[tuple[str, str, dict]]] = {}

    for record_id, data in sorted(records.items()):
        if data.get("record_type") != "claim":
            continue

        claim_status = str(data.get("status", "")).strip()
        try:
            contradiction_refs = ensure_list(data, "contradiction_refs")
        except ValueError:
            contradiction_refs = []
        if claim_is_fallback(data):
            continue
        if claim_status == "contested" and not contradiction_refs:
            lines.append(
                f"- `{rel_display(root, Path(data['_path']))}`: contested claim missing contradiction_refs\n"
            )
        if contradiction_refs and claim_status not in {"contested", "rejected"}:
            lines.append(
                f"- `{rel_display(root, Path(data['_path']))}`: contradiction_refs present but status is {claim_status}\n"
            )

        if claim_status not in {"supported", "corroborated"}:
            continue
        comparison = data.get("comparison")
        if not isinstance(comparison, dict) or not comparison:
            continue
        if validate_claim_comparison(comparison):
            continue

        key = str(comparison.get("key", "")).strip()
        comparator = str(comparison.get("comparator", "")).strip()
        context_scope = str(comparison.get("context_scope", "")).strip()
        if not key or comparator not in CLAIM_COMPARATORS:
            continue

        bucket = (key, context_scope, comparator)
        comparable_claims.setdefault(bucket, []).append((record_id, comparison_signature(comparison), data))

    for (key, context_scope, comparator), entries in sorted(comparable_claims.items()):
        signatures: dict[str, list[tuple[str, dict]]] = {}
        for record_id, signature, data in entries:
            signatures.setdefault(signature, []).append((record_id, data))
        if len(signatures) < 2:
            continue

        group_label = f"key `{key}`"
        if context_scope:
            group_label += f", context `{context_scope}`"
        group_label += f", comparator `{comparator}`"

        rendered_entries: list[str] = []
        for signature, grouped in sorted(signatures.items()):
            for record_id, data in grouped:
                rendered_entries.append(
                    f"{record_id} ({data.get('status', '')}; {signature}; {rel_display(root, Path(data['_path']))})"
                )
        lines.append(f"- comparable claims disagree for {group_label}: {', '.join(rendered_entries)}\n")

    return lines


def write_conflicts_report(root: Path, records: dict[str, dict]) -> list[str]:
    lines = collect_conflict_lines(root, records)
    write_report(
        root / "review" / "conflicts.md",
        "Generated Conflict Review",
        "Generated conflict diagnostics. Do not treat this file as a source of truth.",
        lines,
    )
    return lines
