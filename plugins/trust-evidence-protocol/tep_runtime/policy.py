"""Runtime policy helpers shared by CLI and hook gates."""

from __future__ import annotations

from pathlib import Path

from .errors import ValidationError


ACTION_MUTATION_MARKERS = {
    "edit",
    "write",
    "create",
    "delete",
    "remove",
    "rename",
    "move",
    "refactor",
    "patch",
    "update",
    "modify",
}


def is_mutating_action_kind(kind: str) -> bool:
    normalized = kind.strip().lower().replace("_", "-")
    return any(marker in normalized for marker in ACTION_MUTATION_MARKERS)


def validate_runtime_policy(
    root: Path,
    records: dict[str, dict],
    allowed_freedom: str | None = None,
) -> list[ValidationError]:
    return []
