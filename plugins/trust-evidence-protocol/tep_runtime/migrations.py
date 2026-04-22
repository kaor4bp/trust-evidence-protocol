from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .contracts import MigrationReport
from .io import parse_json_file
from .paths import reasons_ledger_path


def legacy_record_files(root: Path) -> list[Path]:
    records_root = root / "records"
    if not records_root.is_dir():
        return []
    return sorted(path for path in records_root.rglob("*.json") if path.is_file())


def legacy_batch_key(path: Path, root: Path) -> str:
    try:
        relative = path.relative_to(root)
    except ValueError:
        relative = path
    return relative.as_posix()


def collect_legacy_record_refs(root: Path) -> tuple[list[str], list[dict[str, Any]]]:
    refs: list[str] = []
    unresolved: list[dict[str, Any]] = []

    for path in legacy_record_files(root):
        try:
            record = parse_json_file(path)
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            unresolved.append(
                {
                    "path": legacy_batch_key(path, root),
                    "reason": "invalid_json_record",
                    "detail": str(exc),
                }
            )
            continue
        record_id = str(record.get("id") or "").strip()
        if record_id:
            refs.append(record_id)
        else:
            unresolved.append(
                {
                    "path": legacy_batch_key(path, root),
                    "reason": "missing_record_id",
                }
            )

    return sorted(set(refs)), unresolved


def collect_legacy_grant_refs(root: Path) -> tuple[list[str], list[dict[str, Any]]]:
    ledger = reasons_ledger_path(root)
    if not ledger.is_file():
        return [], []

    grants: list[str] = []
    unresolved: list[dict[str, Any]] = []
    for line_number, raw_line in enumerate(ledger.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw_line.strip()
        if not line:
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError as exc:
            unresolved.append(
                {
                    "path": legacy_batch_key(ledger, root),
                    "line": line_number,
                    "reason": "invalid_reason_ledger_json",
                    "detail": str(exc),
                }
            )
            continue
        if not isinstance(entry, dict):
            unresolved.append(
                {
                    "path": legacy_batch_key(ledger, root),
                    "line": line_number,
                    "reason": "non_object_reason_ledger_entry",
                }
            )
            continue
        entry_id = str(entry.get("id") or "").strip()
        entry_type = str(entry.get("entry_type") or "").strip()
        if entry_id.startswith("GRANT-") or entry_type in {"grant", "access_granted", "auth_granted"}:
            if entry_id.startswith("GRANT-"):
                grants.append(entry_id)
            else:
                unresolved.append(
                    {
                        "path": legacy_batch_key(ledger, root),
                        "line": line_number,
                        "reason": "legacy_non_grant_authorization_entry",
                        "legacy_id": entry_id,
                    }
                )

    return sorted(set(grants)), unresolved


def migration_batch_actions(root: Path) -> list[dict[str, Any]]:
    actions: list[dict[str, Any]] = []
    for path in legacy_record_files(root):
        actions.append(
            {
                "action": "create_migration_input",
                "input_kind": "migration_batch",
                "origin": {
                    "kind": "legacy_context",
                    "ref": legacy_batch_key(path, root),
                },
            }
        )
    return actions


def build_migration_dry_run_report(source_root: str | Path, target_root: str | Path) -> MigrationReport:
    source = Path(source_root).expanduser().resolve()
    target = Path(target_root).expanduser().resolve()
    planned_actions: list[dict[str, Any]] = []
    unresolved: list[dict[str, Any]] = []

    if not source.is_dir():
        unresolved.append({"path": str(source), "reason": "source_context_missing"})
    else:
        planned_actions.extend(migration_batch_actions(source))

    preserved_refs, record_issues = collect_legacy_record_refs(source)
    revoked_grants, grant_issues = collect_legacy_grant_refs(source)
    unresolved.extend(record_issues)
    unresolved.extend(grant_issues)

    if target.exists():
        planned_actions.append({"action": "backup_existing_target", "target": str(target)})
    planned_actions.append({"action": "validate_after_migration", "target": str(target)})

    return MigrationReport(
        mode="dry-run",
        source=str(source),
        target=str(target),
        planned_actions=planned_actions,
        created_refs=(),
        preserved_refs=preserved_refs,
        revoked_grants=revoked_grants,
        unresolved=unresolved,
        applied=False,
    )
