"""Service wrapper for autonomous task outcome checks."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .scopes import current_task_ref
from .tasks import task_outcome_check_payload, task_outcome_check_text_lines


def task_outcome_check_service(
    root: Path,
    records: dict[str, dict],
    *,
    task_ref: str | None,
    outcome: str,
) -> tuple[dict[str, Any] | None, str | None]:
    """Return the mechanical terminal-outcome check for a task."""

    target_ref = str(task_ref or "").strip() or current_task_ref(root)
    if not target_ref:
        return None, "No current task. Pass task_ref to check a specific task."
    return task_outcome_check_payload(records, target_ref, outcome), None


def task_outcome_check_text(payload: dict[str, Any]) -> str:
    return "\n".join(task_outcome_check_text_lines(payload))
