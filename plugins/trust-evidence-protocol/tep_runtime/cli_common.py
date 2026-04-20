"""Shared CLI helpers for context commands."""

from __future__ import annotations

from pathlib import Path

from .generated_views import (
    build_index,
    write_attention_report,
    write_backlog,
    write_flows_report,
    write_hypotheses_report,
    write_models_report,
    write_resolved_report,
    write_stale_report,
)
from .conflicts import write_conflicts_report
from .hydration import invalidate_hydration_state
from .io import write_json_file
from .notes import append_note
from .paths import record_path
from .reports import write_validation_report
from .scopes import workspace_refs_for_write
from .state_validation import collect_validation_errors, validate_candidate_record, validate_records_state

TEP_ICON = "🛡️"

MUTATING_COMMANDS = {
    "review-context",
    "reindex-context",
    "scan-conflicts",
    "change-strictness",
    "request-strictness-change",
    "record-workspace",
    "set-current-workspace",
    "assign-workspace",
    "init-anchor",
    "record-project",
    "set-current-project",
    "assign-project",
    "assign-task",
    "record-restriction",
    "record-guideline",
    "record-proposal",
    "configure-runtime",
    "start-task",
    "complete-task",
    "pause-task",
    "resume-task",
    "switch-task",
    "stop-task",
    "promote-model-to-domain",
    "promote-flow-to-domain",
    "mark-stale-from-claim",
    "resolve-claim",
    "archive-claim",
    "restore-claim",
    "record-permission",
    "record-action",
    "record-input",
    "record-source",
    "record-claim",
    "record-link",
    "record-plan",
    "record-debt",
    "record-feedback",
    "record-model",
    "record-flow",
    "record-open-question",
    "record-artifact",
    "init-code-index",
    "index-code",
    "code-refresh",
    "code-entry",
    "annotate-code",
    "link-code",
    "assign-code-index",
    "tap-record",
    "attention-index",
}

MUTATING_HYPOTHESIS_COMMANDS = {"add", "close", "reopen", "remove", "sync"}
MUTATING_TOPIC_INDEX_COMMANDS = {"build"}
MUTATING_ATTENTION_INDEX_COMMANDS = {"build"}
MUTATING_LOGIC_INDEX_COMMANDS = {"build"}
MUTATING_WORKING_CONTEXT_COMMANDS = {"create", "fork", "close"}


def print_errors(errors) -> None:
    for error in errors:
        print(f"{error.path}: {error.message}")


def refresh_generated_outputs(root: Path, records: dict[str, dict]) -> list[str]:
    write_stale_report(root, records)
    conflict_lines = write_conflicts_report(root, records)
    write_models_report(root, records)
    write_flows_report(root, records)
    write_hypotheses_report(root, records)
    write_resolved_report(root, records)
    write_attention_report(root, records)
    build_index(root, records)
    write_backlog(root, records)
    return conflict_lines


def load_clean_context(root: Path, allowed_freedom: str | None = None) -> tuple[dict[str, dict], int]:
    records, errors = collect_validation_errors(root, allowed_freedom=allowed_freedom)
    write_validation_report(root, errors)
    refresh_generated_outputs(root, records)
    if errors:
        print_errors(errors)
        return records, 1
    return records, 0


def persist_candidate(
    root: Path,
    records: dict[str, dict],
    payload: dict,
    record_type: str,
    allowed_freedom: str | None = None,
) -> int:
    if payload.get("record_type") != "workspace" and not payload.get("workspace_refs"):
        refs = workspace_refs_for_write(root, [])
        if refs:
            payload = dict(payload)
            payload["workspace_refs"] = refs
    candidate, candidate_errors = validate_candidate_record(
        root,
        records,
        payload,
        allowed_freedom=allowed_freedom,
    )
    if candidate_errors:
        print_errors(candidate_errors)
        return 1

    write_json_file(record_path(root, record_type, payload["id"]), payload)
    updated_records = dict(records)
    updated_records[payload["id"]] = candidate
    write_validation_report(root, [])
    refresh_generated_outputs(root, updated_records)
    invalidate_hydration_state(root, f"recorded {record_type} {payload['id']}")
    print(f"Recorded {record_type} {payload['id']} at {record_path(root, record_type, payload['id'])}")
    return 0


def parse_csv_refs(value: str | None) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def sanitize_artifact_name(name: str) -> str:
    cleaned = "".join(ch if ch.isalnum() or ch in {".", "_", "-"} else "_" for ch in name.strip())
    cleaned = cleaned.strip("._-")
    return cleaned or "artifact"


def public_record_payload(data: dict) -> dict:
    return {key: value for key, value in data.items() if not str(key).startswith("_")}


def candidate_record_payload(root: Path, payload: dict) -> dict:
    candidate = dict(payload)
    candidate["_folder"] = candidate["record_type"]
    candidate["_path"] = record_path(root, candidate["record_type"], candidate["id"])
    return candidate


def validate_mutated_records(
    root: Path,
    records: dict[str, dict],
    updates: dict[str, dict],
    allowed_freedom: str | None = None,
) -> tuple[dict[str, dict], list]:
    merged = dict(records)
    for record_id, payload in updates.items():
        merged[record_id] = candidate_record_payload(root, payload)
    errors = validate_records_state(root, merged, allowed_freedom=allowed_freedom)
    return merged, errors


def persist_mutated_records(
    root: Path,
    merged_records: dict[str, dict],
    changed_ids: list[str],
    reason: str,
) -> int:
    for record_id in changed_ids:
        write_json_file(
            record_path(root, merged_records[record_id]["record_type"], record_id),
            public_record_payload(merged_records[record_id]),
        )
    write_validation_report(root, [])
    refresh_generated_outputs(root, merged_records)
    invalidate_hydration_state(root, reason)
    print(reason)
    return 0


def refresh_with_existing_records(root: Path) -> tuple[dict[str, dict], int]:
    records, exit_code = load_clean_context(root)
    if exit_code:
        return records, exit_code
    return records, 0


def load_valid_context_readonly(root: Path) -> tuple[dict[str, dict], int]:
    records, errors = collect_validation_errors(root)
    if errors:
        print_errors(errors)
        return records, 1
    return records, 0


def command_requires_write_lock(args) -> bool:
    if args.command == "cleanup-archive":
        return bool(getattr(args, "apply", False))
    if args.command == "cleanup-restore":
        return bool(getattr(args, "apply", False))
    if args.command == "code-feedback":
        return bool(getattr(args, "apply", False))
    if args.command in MUTATING_COMMANDS:
        return True
    if args.command == "hypothesis" and args.hypothesis_command in MUTATING_HYPOTHESIS_COMMANDS:
        return True
    if args.command == "topic-index" and args.topic_index_command in MUTATING_TOPIC_INDEX_COMMANDS:
        return True
    if args.command == "logic-index" and args.logic_index_command in MUTATING_LOGIC_INDEX_COMMANDS:
        return True
    return args.command == "working-context" and args.working_context_command in MUTATING_WORKING_CONTEXT_COMMANDS
