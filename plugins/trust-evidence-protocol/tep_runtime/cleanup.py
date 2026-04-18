"""Read-only cleanup candidate diagnostics."""

from __future__ import annotations

import hashlib
import json
import os
import secrets
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path

from .claims import claim_attention, claim_is_fallback, claim_lifecycle_state, parse_timestamp
from .hydration import compute_context_fingerprint
from .hypotheses import load_hypotheses_index
from .ids import now_timestamp
from .io import write_json_file
from .links import dependency_refs_for_record
from .reports import rel_display
from .records import RECORD_DIRS
from .search import public_record_summary
from .settings import load_settings
from .state_validation import collect_validation_errors

ARCHIVABLE_CANDIDATE_KINDS = {"orphan_input_stale"}


def next_cleanup_archive_id(root: Path) -> str:
    today = datetime.now().astimezone().strftime("%Y%m%d")
    archive_root = root / "archives"
    for _ in range(32):
        candidate = f"ARC-{today}-{secrets.token_hex(4)}"
        if not (archive_root / f"{candidate}.zip").exists() and not (archive_root / f"{candidate}.manifest.json").exists():
            return candidate
    raise RuntimeError(f"could not allocate collision-free archive id for ARC-{today}")


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _archive_zip_path(root: Path, archive_ref: str) -> Path:
    raw_ref = archive_ref.strip()
    if not raw_ref:
        raise ValueError("archive ref is required")
    root_resolved = root.resolve()
    if raw_ref.endswith(".zip"):
        candidate = Path(raw_ref)
        if not candidate.is_absolute():
            candidate = root / candidate
        resolved = candidate.resolve()
        if not resolved.is_relative_to(root_resolved):
            raise ValueError(f"archive path is outside context root: {archive_ref}")
        return resolved
    if not raw_ref.startswith("ARC-"):
        raise ValueError("archive ref must be an ARC-* id or a zip path under the context root")
    return root / "archives" / f"{raw_ref}.zip"


def _safe_restore_target(root: Path, rel_path: str) -> Path:
    if not rel_path.strip():
        raise ValueError("archive manifest item has empty path")
    rel = Path(rel_path)
    if rel.is_absolute():
        raise ValueError(f"archive manifest path is absolute: {rel_path}")
    target = (root / rel).resolve()
    if not target.is_relative_to(root.resolve()):
        raise ValueError(f"archive manifest path escapes context root: {rel_path}")
    return target


def _read_archive_manifest(root: Path, archive_ref: str) -> tuple[Path, dict]:
    archive_path = _archive_zip_path(root, archive_ref)
    if not archive_path.exists():
        raise FileNotFoundError(f"cleanup archive not found: {rel_display(root, archive_path)}")
    with zipfile.ZipFile(archive_path) as archive:
        try:
            raw_manifest = archive.read("manifest.json")
        except KeyError as exc:
            raise ValueError(f"cleanup archive is missing manifest.json: {rel_display(root, archive_path)}") from exc
    manifest = json.loads(raw_manifest.decode("utf-8"))
    if not isinstance(manifest, dict):
        raise ValueError(f"cleanup archive manifest is not an object: {rel_display(root, archive_path)}")
    return archive_path, manifest


def _incoming_refs(records: dict[str, dict]) -> dict[str, list[str]]:
    incoming: dict[str, list[str]] = {}
    for source_id, data in records.items():
        for target_id in dependency_refs_for_record(data):
            if target_id in records and target_id != source_id:
                incoming.setdefault(target_id, []).append(source_id)
    return {record_id: sorted(refs) for record_id, refs in incoming.items()}


def _record_age_days(data: dict, now: datetime) -> int | None:
    timestamp = parse_timestamp(str(data.get("captured_at", "")).strip())
    if timestamp is None:
        return None
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=now.tzinfo)
    else:
        timestamp = timestamp.astimezone(now.tzinfo)
    return max(0, int((now - timestamp).total_seconds() // 86400))


def _record_path_for_payload(root: Path, data: dict) -> str:
    raw_path = data.get("_path")
    if raw_path:
        return rel_display(root, Path(raw_path))
    record_type = str(data.get("record_type", "")).strip()
    record_id = str(data.get("id", "")).strip()
    directory = RECORD_DIRS.get(record_type, record_type)
    return f"records/{directory}/{record_id}.json"


def cleanup_candidate_items(root: Path, records: dict[str, dict]) -> tuple[list[dict], list]:
    _, validation_errors = collect_validation_errors(root)
    items: list[dict] = []
    settings = load_settings(root)
    cleanup_settings = settings.get("cleanup", {}) if isinstance(settings.get("cleanup"), dict) else {}
    orphan_input_stale_after_days = int(cleanup_settings.get("orphan_input_stale_after_days", 30))
    incoming_refs = _incoming_refs(records)
    now = datetime.now().astimezone()
    fallback_claim_refs = {
        record_id
        for record_id, data in records.items()
        if data.get("record_type") == "claim" and claim_is_fallback(data)
    }
    for record_id, data in sorted(records.items()):
        record_type = data.get("record_type")
        if record_type == "input":
            incoming = incoming_refs.get(record_id, [])
            raw_derived_refs = data.get("derived_record_refs", [])
            derived_record_refs = {
                str(ref).strip()
                for ref in raw_derived_refs
                if str(ref).strip() in records
            } if isinstance(raw_derived_refs, list) else set()
            if not incoming and not derived_record_refs:
                age_days = _record_age_days(data, now)
                if age_days is not None and age_days >= orphan_input_stale_after_days:
                    items.append(
                        {
                            "kind": "orphan_input_stale",
                            "record": public_record_summary(data),
                            "age_days": age_days,
                            "threshold_days": orphan_input_stale_after_days,
                            "suggestion": "archive the stale unlinked INP-* into a restorable zip before any deletion",
                        }
                    )
        if record_type == "claim":
            lifecycle_state = claim_lifecycle_state(data)
            attention = claim_attention(data)
            if lifecycle_state in {"resolved", "historical"} and attention not in {"fallback-only", "explicit-only"}:
                items.append(
                    {
                        "kind": "claim_lifecycle_attention_mismatch",
                        "record": public_record_summary(data),
                        "suggestion": "set attention=fallback-only or restore lifecycle.state=active",
                    }
                )
            if lifecycle_state == "archived" and attention != "explicit-only":
                items.append(
                    {
                        "kind": "archived_claim_visible_in_retrieval",
                        "record": public_record_summary(data),
                        "suggestion": "set attention=explicit-only or restore lifecycle.state=active",
                    }
                )
        if record_type in {"model", "flow"} and str(data.get("status", "")).strip() in {"working", "stable"}:
            stale_deps = sorted(fallback_claim_refs.intersection(dependency_refs_for_record(data)))
            if stale_deps:
                items.append(
                    {
                        "kind": f"{record_type}_depends_on_fallback_claim",
                        "record": public_record_summary(data),
                        "refs": stale_deps,
                        "suggestion": "refresh the model/flow with active claims or mark it stale",
                    }
                )

    hypothesis_entries, hypothesis_errors = load_hypotheses_index(root)
    validation_errors.extend(hypothesis_errors)
    for entry in hypothesis_entries:
        if str(entry.get("status", "")).strip() != "active":
            continue
        claim_ref = str(entry.get("claim_ref", "")).strip()
        claim = records.get(claim_ref)
        if claim and claim_is_fallback(claim):
            items.append(
                {
                    "kind": "active_hypothesis_points_to_fallback_claim",
                    "record": public_record_summary(claim),
                    "hypothesis": entry,
                    "suggestion": "close/remove the hypothesis entry or restore the claim to active",
                }
            )
    return items, validation_errors


def cleanup_archive_plan_payload(root: Path, records: dict[str, dict], limit: int) -> tuple[dict, list]:
    items, validation_errors = cleanup_candidate_items(root, records)
    settings = load_settings(root)
    cleanup_settings = settings.get("cleanup", {}) if isinstance(settings.get("cleanup"), dict) else {}
    archive_format = str(cleanup_settings.get("archive_format") or "zip")
    archivable_items = [item for item in items if item.get("kind") in ARCHIVABLE_CANDIDATE_KINDS]
    limited_items = archivable_items[: max(1, limit)]
    manifest_items = []
    for item in limited_items:
        record = item.get("record", {})
        record_id = str(record.get("id", "")).strip()
        data = records.get(record_id, {})
        manifest_items.append(
            {
                "record_id": record_id,
                "record_type": record.get("record_type", ""),
                "path": _record_path_for_payload(root, data),
                "reason": item.get("kind", ""),
                "summary": record.get("summary", ""),
                "age_days": item.get("age_days"),
                "threshold_days": item.get("threshold_days"),
            }
        )
    payload = {
        "cleanup_is_read_only": True,
        "archive_plan_is_dry_run": True,
        "archive_format": archive_format,
        "validation_error_count": len(validation_errors),
        "candidate_count": len(items),
        "archivable_candidate_count": len(archivable_items),
        "items": manifest_items,
    }
    return payload, validation_errors


def cleanup_archive_apply_payload(root: Path, records: dict[str, dict], limit: int) -> tuple[dict, list]:
    plan, validation_errors = cleanup_archive_plan_payload(root, records, limit=limit)
    items = list(plan.get("items", []))
    if not items:
        payload = dict(plan)
        payload["archive_plan_is_dry_run"] = False
        payload["archive_written"] = False
        payload["records_mutated"] = False
        payload["records_deleted"] = False
        return payload, validation_errors

    archive_id = next_cleanup_archive_id(root)
    archive_root = root / "archives"
    archive_root.mkdir(parents=True, exist_ok=True)
    archive_path = archive_root / f"{archive_id}.zip"
    manifest_path = archive_root / f"{archive_id}.manifest.json"

    manifest_items = []
    for item in items:
        rel_path = str(item.get("path", "")).strip()
        source_path = (root / rel_path).resolve()
        if not source_path.is_file() or not source_path.is_relative_to(root.resolve()):
            raise FileNotFoundError(f"archive source is missing or outside context root: {rel_path}")
        manifest_item = dict(item)
        manifest_item["sha256"] = _sha256_file(source_path)
        manifest_item["bytes"] = source_path.stat().st_size
        manifest_items.append(manifest_item)

    manifest = {
        "archive_id": archive_id,
        "created_at": now_timestamp(),
        "archive_format": "zip",
        "context_fingerprint": compute_context_fingerprint(root),
        "item_count": len(manifest_items),
        "items": manifest_items,
        "records_mutated": False,
        "records_deleted": False,
        "restore_hint": f"unzip archives/{archive_id}.zip from the TEP context root",
    }

    with tempfile.NamedTemporaryFile(
        "wb",
        dir=archive_root,
        prefix=f".{archive_id}.",
        suffix=".zip.tmp",
        delete=False,
    ) as handle:
        tmp_path = Path(handle.name)
    try:
        with zipfile.ZipFile(tmp_path, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("manifest.json", json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
            for item in manifest_items:
                archive.write(root / item["path"], arcname=item["path"])
        os.replace(tmp_path, archive_path)
    except Exception:
        tmp_path.unlink(missing_ok=True)
        raise
    write_json_file(manifest_path, manifest)

    payload = dict(plan)
    payload.update(
        {
            "archive_plan_is_dry_run": False,
            "archive_written": True,
            "archive_id": archive_id,
            "archive_path": rel_display(root, archive_path),
            "manifest_path": rel_display(root, manifest_path),
            "records_mutated": False,
            "records_deleted": False,
            "items": manifest_items,
        }
    )
    return payload, validation_errors


def cleanup_restore_plan_payload(root: Path, archive_ref: str) -> dict:
    archive_path, manifest = _read_archive_manifest(root, archive_ref)
    manifest_items = manifest.get("items", [])
    if not isinstance(manifest_items, list):
        raise ValueError("cleanup archive manifest items must be a list")

    items = []
    with zipfile.ZipFile(archive_path) as archive:
        archive_names = set(archive.namelist())
        for raw_item in manifest_items:
            if not isinstance(raw_item, dict):
                raise ValueError("cleanup archive manifest item must be an object")
            item = dict(raw_item)
            rel_path = str(item.get("path", "")).strip()
            target_path = _safe_restore_target(root, rel_path)
            expected_sha256 = str(item.get("sha256", "")).strip()
            archive_entry_exists = rel_path in archive_names
            archive_entry_sha256 = None
            sha256_verified = False
            if archive_entry_exists:
                archive_entry_sha256 = _sha256_bytes(archive.read(rel_path))
                sha256_verified = not expected_sha256 or expected_sha256 == archive_entry_sha256

            target_exists = target_path.exists()
            target_sha256 = _sha256_file(target_path) if target_path.is_file() else None
            if not archive_entry_exists:
                status = "missing-archive-entry"
            elif not sha256_verified:
                status = "sha256-mismatch"
            elif target_exists and target_sha256 == archive_entry_sha256:
                status = "already-present"
            elif target_exists:
                status = "target-conflict"
            else:
                status = "restore-ready"

            item.update(
                {
                    "archive_entry": rel_path,
                    "archive_entry_exists": archive_entry_exists,
                    "archive_entry_sha256": archive_entry_sha256,
                    "sha256_verified": sha256_verified,
                    "target_path": rel_display(root, target_path),
                    "target_exists": target_exists,
                    "target_sha256": target_sha256,
                    "status": status,
                    "restorable": status == "restore-ready",
                    "blocking": status in {"missing-archive-entry", "sha256-mismatch", "target-conflict"},
                }
            )
            items.append(item)

    payload = {
        "restore_plan_is_dry_run": True,
        "archive_id": manifest.get("archive_id", archive_path.stem),
        "archive_ref": archive_ref,
        "archive_path": rel_display(root, archive_path),
        "manifest_item_count": len(manifest_items),
        "item_count": len(items),
        "restorable_count": sum(1 for item in items if item.get("restorable")),
        "already_present_count": sum(1 for item in items if item.get("status") == "already-present"),
        "blocking_count": sum(1 for item in items if item.get("blocking")),
        "items": items,
    }
    return payload


def cleanup_restore_apply_payload(root: Path, archive_ref: str) -> dict:
    plan = cleanup_restore_plan_payload(root, archive_ref)
    blocking_items = [item for item in plan["items"] if item.get("blocking")]
    payload = dict(plan)
    payload["restore_plan_is_dry_run"] = False
    payload["restore_applied"] = False
    payload["restored_count"] = 0
    if blocking_items:
        payload["restore_blocked"] = True
        payload["blocked_items"] = blocking_items
        return payload

    archive_path = root / str(plan["archive_path"])
    restored_items = []
    with zipfile.ZipFile(archive_path) as archive:
        for item in plan["items"]:
            if not item.get("restorable"):
                continue
            rel_path = str(item["archive_entry"])
            target_path = _safe_restore_target(root, rel_path)
            payload_bytes = archive.read(rel_path)
            target_path.parent.mkdir(parents=True, exist_ok=True)
            with target_path.open("xb") as handle:
                handle.write(payload_bytes)
            restored_items.append(item)

    payload["restore_applied"] = True
    payload["restore_blocked"] = False
    payload["restored_count"] = len(restored_items)
    payload["restored_items"] = restored_items
    return payload


def cleanup_archives_payload(root: Path, archive_ref: str | None = None, limit: int = 50) -> dict:
    if archive_ref:
        archive_path, manifest = _read_archive_manifest(root, archive_ref)
        return {
            "cleanup_archives_is_read_only": True,
            "archive_id": manifest.get("archive_id", archive_path.stem),
            "archive_path": rel_display(root, archive_path),
            "manifest_path": rel_display(root, archive_path.with_suffix(".manifest.json")),
            "created_at": manifest.get("created_at", ""),
            "archive_format": manifest.get("archive_format", "zip"),
            "context_fingerprint": manifest.get("context_fingerprint", ""),
            "item_count": int(manifest.get("item_count") or len(manifest.get("items", []))),
            "records_mutated": bool(manifest.get("records_mutated", False)),
            "records_deleted": bool(manifest.get("records_deleted", False)),
            "items": list(manifest.get("items", [])) if isinstance(manifest.get("items", []), list) else [],
        }

    archive_root = root / "archives"
    archive_ids: set[str] = set()
    if archive_root.exists():
        for manifest_path in archive_root.glob("ARC-*.manifest.json"):
            archive_ids.add(manifest_path.name.removesuffix(".manifest.json"))
        for archive_path in archive_root.glob("ARC-*.zip"):
            archive_ids.add(archive_path.stem)

    archives = []
    errors = []
    for archive_id in sorted(archive_ids, reverse=True)[: max(1, limit)]:
        try:
            archive_path, manifest = _read_archive_manifest(root, archive_id)
        except (OSError, ValueError, json.JSONDecodeError, zipfile.BadZipFile) as exc:
            errors.append({"archive_id": archive_id, "error": str(exc)})
            archives.append(
                {
                    "archive_id": archive_id,
                    "status": "invalid",
                    "archive_path": f"archives/{archive_id}.zip",
                    "error": str(exc),
                }
            )
            continue
        archives.append(
            {
                "archive_id": manifest.get("archive_id", archive_id),
                "status": "ok",
                "archive_path": rel_display(root, archive_path),
                "manifest_path": rel_display(root, archive_path.with_suffix(".manifest.json")),
                "created_at": manifest.get("created_at", ""),
                "archive_format": manifest.get("archive_format", "zip"),
                "item_count": int(manifest.get("item_count") or len(manifest.get("items", []))),
                "records_mutated": bool(manifest.get("records_mutated", False)),
                "records_deleted": bool(manifest.get("records_deleted", False)),
            }
        )

    return {
        "cleanup_archives_is_read_only": True,
        "archive_count": len(archives),
        "error_count": len(errors),
        "archives": archives,
        "errors": errors,
    }


def cleanup_archive_plan_text_lines(payload: dict) -> list[str]:
    dry_run = bool(payload.get("archive_plan_is_dry_run", True))
    mode_line = (
        "Mode: dry-run. No archive was written and no records were changed."
        if dry_run
        else "Mode: apply. Archive was written; records were not changed or deleted."
    )
    lines = [
        "# Cleanup Archive Plan",
        "",
        mode_line,
        f"Archive format: `{payload.get('archive_format')}`",
        f"Validation errors observed: {payload.get('validation_error_count')}",
        f"Cleanup candidate count: {payload.get('candidate_count')}",
        f"Archivable candidate count: {payload.get('archivable_candidate_count')}",
    ]
    if payload.get("archive_written"):
        lines.extend(
            [
                f"Archive id: `{payload.get('archive_id')}`",
                f"Archive path: `{payload.get('archive_path')}`",
                f"Manifest path: `{payload.get('manifest_path')}`",
            ]
        )
    lines.append("")
    items = payload.get("items", [])
    if not items:
        lines.append("- no archivable cleanup candidates found")
        return lines
    for item in items:
        lines.append(
            f"- `{item.get('record_id')}` type=`{item.get('record_type')}` "
            f"reason=`{item.get('reason')}` path=`{item.get('path')}` "
            f"age_days={item.get('age_days')} threshold_days={item.get('threshold_days')}"
        )
    return lines


def cleanup_restore_plan_text_lines(payload: dict) -> list[str]:
    dry_run = bool(payload.get("restore_plan_is_dry_run", True))
    mode_line = (
        "Mode: dry-run. No files were restored."
        if dry_run
        else "Mode: apply. Missing archive files were restored without overwriting existing files."
    )
    lines = [
        "# Cleanup Restore Plan",
        "",
        mode_line,
        f"Archive id: `{payload.get('archive_id')}`",
        f"Archive path: `{payload.get('archive_path')}`",
        f"Manifest item count: {payload.get('manifest_item_count')}",
        f"Restorable count: {payload.get('restorable_count')}",
        f"Already present count: {payload.get('already_present_count')}",
        f"Blocking count: {payload.get('blocking_count')}",
    ]
    if payload.get("restore_blocked"):
        lines.append("Restore blocked: at least one archive item cannot be restored safely.")
    if payload.get("restored_count") is not None:
        lines.append(f"Restored count: {payload.get('restored_count')}")
    lines.append("")
    items = payload.get("items", [])
    if not items:
        lines.append("- no archive items found")
        return lines
    for item in items:
        lines.append(
            f"- `{item.get('record_id')}` type=`{item.get('record_type')}` "
            f"status=`{item.get('status')}` path=`{item.get('path')}` "
            f"target=`{item.get('target_path')}`"
        )
    return lines


def cleanup_archives_text_lines(payload: dict) -> list[str]:
    lines = [
        "# Cleanup Archives",
        "",
        "Mode: read-only archive catalog. No files were changed.",
    ]
    if "archives" in payload:
        lines.extend(
            [
                f"Archive count: {payload.get('archive_count')}",
                f"Error count: {payload.get('error_count')}",
                "",
            ]
        )
        archives = payload.get("archives", [])
        if not archives:
            lines.append("- no cleanup archives found")
            return lines
        for archive in archives:
            line = (
                f"- `{archive.get('archive_id')}` status=`{archive.get('status')}` "
                f"items={archive.get('item_count')} path=`{archive.get('archive_path')}`"
            )
            if archive.get("error"):
                line += f" error=`{archive.get('error')}`"
            lines.append(line)
        return lines

    lines.extend(
        [
            f"Archive id: `{payload.get('archive_id')}`",
            f"Archive path: `{payload.get('archive_path')}`",
            f"Manifest path: `{payload.get('manifest_path')}`",
            f"Created at: {payload.get('created_at')}",
            f"Item count: {payload.get('item_count')}",
            "",
        ]
    )
    items = payload.get("items", [])
    if not items:
        lines.append("- no archive items found")
        return lines
    for item in items:
        lines.append(
            f"- `{item.get('record_id')}` type=`{item.get('record_type')}` "
            f"reason=`{item.get('reason')}` path=`{item.get('path')}`"
        )
    return lines
