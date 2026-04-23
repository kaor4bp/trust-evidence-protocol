from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .contracts import MigrationReport
from .io import context_write_lock, parse_json_file, write_json_file
from .paths import reasons_ledger_path
from .schema_migrations import registered_schema_migrations
from .schemas import validate_record


def legacy_record_files(root: Path) -> list[Path]:
    records_root = root / "records"
    if not records_root.is_dir():
        return []
    return sorted(path for path in records_root.rglob("*.json") if path.is_file())


def record_files(root: Path) -> list[Path]:
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


def _selected_schema_migrations(migration_ids: list[str] | tuple[str, ...] | None) -> tuple[Any, list[dict[str, Any]]]:
    migrations = registered_schema_migrations()
    if not migration_ids:
        return migrations, []
    by_id = {migration.id: migration for migration in migrations}
    selected = []
    unresolved = []
    for migration_id in migration_ids:
        migration_id = str(migration_id).strip()
        if not migration_id:
            continue
        migration = by_id.get(migration_id)
        if migration is None:
            unresolved.append({"path": "", "reason": "unknown_schema_migration", "migration_id": migration_id})
            continue
        selected.append(migration)
    return tuple(selected), unresolved


def _record_validation_payload(path: Path, record: dict) -> dict:
    payload = dict(record)
    payload["_path"] = path
    payload["_folder"] = path.parent.name
    return payload


def build_schema_migration_report(
    root: str | Path,
    *,
    apply: bool = False,
    migration_ids: list[str] | tuple[str, ...] | None = None,
) -> MigrationReport:
    context_root = Path(root).expanduser().resolve()
    mode = "apply" if apply else "dry-run"
    planned_actions: list[dict[str, Any]] = []
    migrated_refs: list[str] = []
    unresolved: list[dict[str, Any]] = []
    pending_writes: list[tuple[Path, dict[str, Any]]] = []

    migrations, selection_issues = _selected_schema_migrations(migration_ids)
    unresolved.extend(selection_issues)

    if not context_root.is_dir():
        unresolved.append({"path": str(context_root), "reason": "context_root_missing"})
    else:
        for path in record_files(context_root):
            try:
                original = parse_json_file(path)
            except (OSError, json.JSONDecodeError, ValueError) as exc:
                unresolved.append(
                    {
                        "path": legacy_batch_key(path, context_root),
                        "reason": "invalid_json_record",
                        "detail": str(exc),
                    }
                )
                continue

            current = dict(original)
            path_actions: list[dict[str, Any]] = []
            path_issues: list[dict[str, Any]] = []
            relative_path = legacy_batch_key(path, context_root)

            for migration in migrations:
                if not migration.applies_to(path, current):
                    continue
                record_id = str(current.get("id", "")).strip()
                action = {
                    "action": "migrate_record_schema",
                    "migration_id": migration.id,
                    "description": migration.description,
                    "path": relative_path,
                    "record_id": record_id,
                    "record_type": str(current.get("record_type", "")).strip() or path.parent.name,
                }
                path_actions.append(action)
                result = migration.migrate(path, current, relative_path=relative_path)
                current = dict(result.record)
                path_issues.extend(issue.to_payload() for issue in result.issues)

            if not path_actions:
                continue

            record_id = str(current.get("id", "")).strip()
            if not record_id:
                path_issues.append({"path": relative_path, "reason": "missing_record_id"})
            else:
                validation_payload = _record_validation_payload(path, current)
                for message in validate_record(record_id, validation_payload):
                    path_issues.append(
                        {
                            "path": relative_path,
                            "reason": "post_migration_validation_failed",
                            "detail": message,
                            "record_id": record_id,
                        }
                    )

            planned_actions.extend(path_actions)
            if path_issues:
                unresolved.extend(path_issues)
                continue
            if current != original:
                migrated_refs.append(record_id or relative_path)
                pending_writes.append((path, current))

    if apply and pending_writes and not unresolved:
        with context_write_lock(context_root):
            for path, payload in pending_writes:
                write_json_file(path, payload)

    return MigrationReport(
        mode=mode,
        source=str(context_root),
        target=str(context_root),
        planned_actions=planned_actions,
        created_refs=(),
        preserved_refs=tuple(sorted(set(migrated_refs))),
        revoked_grants=(),
        unresolved=unresolved,
        applied=bool(apply and not unresolved),
    )


def migration_report_text_lines(report: dict[str, Any]) -> list[str]:
    mode = str(report.get("mode") or "dry-run")
    is_schema_migration = report.get("source") == report.get("target")
    title = "TEP 0.4 Schema Migration Report" if is_schema_migration else "TEP 0.4 Migration Report"
    lines = [
        title,
        f"mode: {mode}",
        f"source: {report['source']}",
        f"target: {report['target']}",
        f"preserved_refs: {len(report['preserved_refs'])}",
        f"revoked_grants: {len(report['revoked_grants'])}",
        f"planned_actions: {len(report['planned_actions'])}",
        f"unresolved: {len(report['unresolved'])}",
        f"applied: {str(bool(report.get('applied'))).lower()}",
    ]
    if report["unresolved"]:
        lines.append("unresolved_items:")
        for item in report["unresolved"][:8]:
            reason = item.get("reason", "unknown")
            path = item.get("path", "")
            lines.append(f"- {reason}: {path}".rstrip())
    return lines
