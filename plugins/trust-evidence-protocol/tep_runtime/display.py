"""Deterministic public text renderers for record summaries."""

from __future__ import annotations

from .claims import claim_attention, claim_lifecycle_state
from .search import concise


def project_summary_line(project: dict) -> str:
    return (
        f"`{project.get('id')}` status=`{project.get('status')}` key=`{project.get('project_key')}` "
        f"title=\"{concise(project.get('title', ''), 160)}\""
    )


def restriction_summary_line(restriction: dict) -> str:
    return (
        f"`{restriction.get('id')}` status=`{restriction.get('status')}` "
        f"applies_to=`{restriction.get('applies_to')}` severity=`{restriction.get('severity')}` "
        f"title=\"{concise(restriction.get('title', ''), 160)}\""
    )


def guideline_summary_line(guideline: dict) -> str:
    return (
        f"`{guideline.get('id')}` status=`{guideline.get('status')}` domain=`{guideline.get('domain')}` "
        f"applies_to=`{guideline.get('applies_to')}` priority=`{guideline.get('priority')}` "
        f"rule=\"{concise(guideline.get('rule', ''), 180)}\""
    )


def claim_line(claim: dict) -> str:
    confidence = f" confidence={claim.get('confidence')}" if claim.get("confidence") else ""
    lifecycle = ""
    if claim.get("record_type") == "claim":
        state = claim_lifecycle_state(claim)
        attention = claim_attention(claim)
        if state != "active" or attention != "normal":
            lifecycle = f" lifecycle=`{state}` attention=`{attention}`"
    return (
        f"- `{claim.get('id')}` status=`{claim.get('status')}` plane=`{claim.get('plane')}`{confidence}{lifecycle}: "
        f"{concise(claim.get('statement', ''))}"
    )


def source_line(source: dict) -> str:
    quote = source.get("quote") or ", ".join(source.get("artifact_refs", []))
    return (
        f"  - `{source.get('id')}` kind=`{source.get('source_kind')}` "
        f"critique=`{source.get('critique_status')}` quote=`{concise(quote, 220)}`"
    )
