"""Proposal record parsing and display helpers."""

from __future__ import annotations

from .search import concise


def parse_proposal_option(raw: str) -> dict:
    parts = [part.strip() for part in raw.split("|")]
    if len(parts) < 2:
        raise ValueError("--proposal must be shaped as title|why[|tradeoff1;tradeoff2][|recommended]")
    title = parts[0]
    why = parts[1]
    tradeoffs = [item.strip() for item in parts[2].split(";") if item.strip()] if len(parts) >= 3 else []
    recommended = False
    if len(parts) >= 4:
        token = parts[3].strip().lower()
        if token in {"true", "yes", "1", "recommended"}:
            recommended = True
        elif token in {"false", "no", "0", ""}:
            recommended = False
        else:
            raise ValueError("--proposal recommended flag must be true/false/recommended")
    return {
        "title": title,
        "why": why,
        "tradeoffs": tradeoffs,
        "recommended": recommended,
    }


def proposal_summary_line(proposal: dict) -> str:
    recommended = ""
    for option in proposal.get("proposals", []):
        if isinstance(option, dict) and option.get("recommended") is True:
            recommended = str(option.get("title", "")).strip()
            break
    suffix = f" recommended=\"{concise(recommended, 140)}\"" if recommended else ""
    return (
        f"`{proposal.get('id')}` status=`{proposal.get('status')}` confidence=`{proposal.get('confidence', '')}` "
        f"subject=\"{concise(proposal.get('subject', ''), 140)}\"{suffix}"
    )


def build_proposal_payload(
    record_id: str,
    timestamp: str,
    scope: str,
    status: str,
    subject: str,
    position: str,
    claim_refs: list[str],
    guideline_refs: list[str],
    model_refs: list[str],
    flow_refs: list[str],
    open_question_refs: list[str],
    assumptions: list[str],
    concerns: list[str],
    proposals: list[dict],
    risks: list[str],
    stop_conditions: list[str],
    confidence: str,
    created_by: str,
    project_refs: list[str],
    task_refs: list[str],
    supersedes_refs: list[str],
    tags: list[str],
    note: str,
) -> dict:
    return {
        "id": record_id,
        "record_type": "proposal",
        "scope": scope.strip(),
        "status": status,
        "subject": subject.strip(),
        "position": position.strip(),
        "claim_refs": claim_refs,
        "guideline_refs": guideline_refs,
        "model_refs": model_refs,
        "flow_refs": flow_refs,
        "open_question_refs": open_question_refs,
        "assumptions": assumptions,
        "concerns": concerns,
        "proposals": proposals,
        "risks": risks,
        "stop_conditions": stop_conditions,
        "confidence": confidence,
        "created_by": created_by.strip(),
        "project_refs": project_refs,
        "task_refs": task_refs,
        "supersedes_refs": supersedes_refs,
        "created_at": timestamp,
        "updated_at": timestamp,
        "tags": tags,
        "note": note.strip(),
    }
