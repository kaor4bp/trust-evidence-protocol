#!/usr/bin/env python3
"""Migrate a legacy markdown-ledger .codex_context into the strict JSON layout."""

from __future__ import annotations

import argparse
import json
import re
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from bootstrap_codex_context import bootstrap
from context_lib import next_record_id, now_timestamp, write_hypotheses_index, write_json_file


OLD_ID_PATTERN = re.compile(r"\bPRAY-(?:USR|ART|FACT|DEBT|DBG-(?:FACT|OBS|HYP|EVID|CNF))-\d+\b")
SECTION_PATTERN = re.compile(r"^###\s+([^\n]+)\n", re.MULTILINE)
OPEN_SECTION_PATTERN = re.compile(r"^##\s+([^\n]+)\n", re.MULTILINE)


@dataclass
class LegacySection:
    legacy_id: str
    title: str
    path: Path
    fields: dict[str, str]
    body: str


def slugify(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "-", value.strip()).strip("-") or "artifact"


def parse_bullet_fields(body: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    current_key: str | None = None
    current_lines: list[str] = []
    for raw_line in body.splitlines():
        line = raw_line.rstrip()
        match = re.match(r"^- ([^:]+):\s*(.*)$", line)
        if match:
            if current_key is not None:
                fields[current_key] = "\n".join(current_lines).strip()
            current_key = match.group(1).strip()
            current_lines = [match.group(2).strip()]
            continue
        if current_key is not None and (line.startswith("  - ") or line.startswith("    ") or line.startswith("- ")):
            current_lines.append(line.strip())
    if current_key is not None:
        fields[current_key] = "\n".join(current_lines).strip()
    return fields


def parse_sections(path: Path) -> list[LegacySection]:
    text = path.read_text(encoding="utf-8")
    matches = list(SECTION_PATTERN.finditer(text))
    sections: list[LegacySection] = []
    for index, match in enumerate(matches):
        title = match.group(1).strip()
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        body = text[start:end].strip()
        legacy_id = title.split()[0].strip()
        sections.append(
            LegacySection(
                legacy_id=legacy_id,
                title=title,
                path=path,
                fields=parse_bullet_fields(body),
                body=body,
            )
        )
    return sections


def parse_open_questions(path: Path) -> list[LegacySection]:
    text = path.read_text(encoding="utf-8")
    matches = list(OPEN_SECTION_PATTERN.finditer(text))
    sections: list[LegacySection] = []
    for index, match in enumerate(matches):
        title = match.group(1).strip()
        if not re.match(r"Q\d+\.", title):
            continue
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        body = text[start:end].strip()
        legacy_id = title.split()[0].rstrip(".")
        sections.append(
            LegacySection(
                legacy_id=legacy_id,
                title=title,
                path=path,
                fields={},
                body=body,
            )
        )
    return sections


def copy_tree(src: Path, dst: Path) -> None:
    for path in src.rglob("*"):
        relative = path.relative_to(src)
        target = dst / relative
        if path.is_dir():
            target.mkdir(parents=True, exist_ok=True)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)


def note_with_legacy(section: LegacySection, extra: str | None = None) -> str:
    parts = [
        f"legacy_id={section.legacy_id}",
        f"legacy_file={section.path.name}",
    ]
    if extra:
        parts.append(extra.strip())
    why = section.fields.get("Why it matters")
    if why:
        parts.append(f"why_it_matters={why}")
    return "\n\n".join(parts)


def source_kind_from_section(section: LegacySection, default: str = "theory") -> str:
    source = section.fields.get("Source", "")
    trust = section.fields.get("Trust level", "").strip()
    if "command run" in source or "running command" in source or trust == "evidence":
        return "runtime"
    if "/Users/" in source or "worktree" in source or trust in {"bridge-code", "repo-code"}:
        return "code"
    return default


def critique_status_from_section(section: LegacySection) -> str:
    origin_kind = origin_kind_for_source(section, "legacy-source")
    if origin_kind in {"legacy-command", "legacy-code-inspection"}:
        return "accepted"
    trust = section.fields.get("Trust level", "").strip()
    if trust in {"trusted", "evidence", "bridge-code"}:
        return "accepted"
    return "audited"


def claim_status_from_section(section: LegacySection, record_group: str) -> str:
    trust = section.fields.get("Trust level", "").strip()
    if record_group == "hypothesis":
        return "tentative"
    if record_group == "conflict":
        return "contested"
    if record_group == "evidence":
        return "corroborated"
    if record_group == "observation":
        return "supported"
    if trust in {"trusted", "evidence", "bridge-code"}:
        return "supported"
    return "tentative"


def plane_from_section(section: LegacySection, record_group: str) -> str:
    source_kind = source_kind_from_section(section)
    if source_kind == "runtime" or record_group in {"observation", "evidence"}:
        return "runtime"
    if source_kind == "code":
        return "code"
    return "theory"


def origin_kind_for_source(section: LegacySection, default: str) -> str:
    source = section.fields.get("Source", "")
    legacy_file = section.path.name
    if legacy_file.startswith("user-statements"):
        return "user-statement"
    if legacy_file.startswith("reference-artifacts"):
        return "reference-artifact"
    if "command run" in source or "running command" in source:
        return "legacy-command"
    if "/Users/" in source or "worktree" in source:
        return "legacy-code-inspection"
    return default


def rel_artifact_ref(artifacts_root: Path, path: Path) -> str:
    return f"artifacts/{path.relative_to(artifacts_root.parent).as_posix().split('artifacts/', 1)[1]}"


def collect_refs(text: str) -> list[str]:
    return sorted(set(OLD_ID_PATTERN.findall(text)))


def migrate(source_root: Path) -> None:
    timestamp = datetime.now().astimezone().strftime("%Y%m%d-%H%M%S")
    backup_root = source_root.with_name(f"{source_root.name}.legacy-pre-json-migration-{timestamp}")
    if backup_root.exists():
        raise RuntimeError(f"backup path already exists: {backup_root}")

    shutil.move(str(source_root), str(backup_root))
    bootstrap(source_root, force=True)

    artifacts_root = source_root / "artifacts"
    legacy_artifacts_root = artifacts_root / "legacy-context"
    copy_tree(backup_root, legacy_artifacts_root)

    records: dict[str, dict] = {}
    legacy_to_new: dict[str, str] = {}
    hypothesis_entries: list[dict] = []
    migration_notes: list[str] = []

    def add_record(record_type: str, payload: dict, legacy_id: str | None = None) -> str:
        record_id = next_record_id(records, {
            "source": "SRC-",
            "claim": "CLM-",
            "debt": "DEBT-",
            "open_question": "OPEN-",
        }[record_type])
        payload["id"] = record_id
        payload["record_type"] = record_type
        records[record_id] = payload
        write_json_file(source_root / "records" / record_type / f"{record_id}.json", payload)
        if legacy_id:
            legacy_to_new[legacy_id] = record_id
        return record_id

    # 1. Source objects from user statements and reference artifacts.
    for file_name in (
        "user-statements-current-thread-2026-04-14.md",
        "user-statements-smartpick-debug-wave-2026-04-14.md",
        "user-statements-smartpick-debug-wave-2026-04-15.md",
        "reference-artifacts-smartpick-2026-04-14.md",
    ):
        path = backup_root / "domains" / file_name
        if not path.exists():
            continue
        for section in parse_sections(path):
            scope = section.fields.get("Scope", "").strip() or "legacy-import"
            quote = section.fields.get("Quote", "").strip()
            source_kind = source_kind_from_section(section)
            origin_ref = section.fields.get("Source", "").strip() or f"legacy markdown section {section.legacy_id}"
            source_id = add_record(
                "source",
                {
                    "source_kind": source_kind,
                    "scope": scope,
                    "captured_at": now_timestamp(),
                    "critique_status": critique_status_from_section(section),
                    "independence_group": f"legacy-import-{slugify(file_name)}",
                    "origin": {
                        "kind": origin_kind_for_source(section, "legacy-source-object"),
                        "ref": origin_ref,
                    },
                    "artifact_refs": [f"artifacts/legacy-context/domains/{file_name}"],
                    "quote": quote or section.fields.get("Claim", "").strip(),
                    "tags": ["legacy-import", slugify(file_name.removesuffix('.md'))],
                    "note": note_with_legacy(section),
                },
                legacy_id=section.legacy_id,
            )
            migration_notes.append(f"{section.legacy_id} -> {source_id} (source)")

    # 2. Grouped criteria source for approved-facts.md
    approved_facts_path = backup_root / "domains" / "approved-facts.md"
    grouped_criteria_source_id: str | None = None
    if approved_facts_path.exists():
        grouped_criteria_source_id = add_record(
            "source",
            {
                "source_kind": "theory",
                "scope": "pray-and-run-tests legacy approved criteria",
                "captured_at": now_timestamp(),
                "critique_status": "accepted",
                "independence_group": "legacy-import-approved-facts",
                "origin": {
                    "kind": "legacy-grouped-criteria-ledger",
                    "ref": "legacy grouped approved-facts.md criteria set",
                },
                "artifact_refs": ["artifacts/legacy-context/domains/approved-facts.md"],
                "quote": "Legacy grouped criterion set from approved-facts.md",
                "tags": ["legacy-import", "approved-facts", "criteria"],
                "note": "Grouped source for legacy approved facts; original file stored criteria as a single markdown ledger.",
            },
        )

    def source_refs_for_section(section: LegacySection) -> list[str]:
        refs = collect_refs(section.fields.get("Source", ""))
        mapped = [legacy_to_new[ref] for ref in refs if ref in legacy_to_new]
        if mapped:
            return sorted(set(mapped))

        source_kind = source_kind_from_section(section)
        inline_source_id = add_record(
            "source",
            {
                "source_kind": source_kind,
                "scope": section.fields.get("Scope", "").strip() or "legacy-import",
                "captured_at": now_timestamp(),
                "critique_status": critique_status_from_section(section),
                "independence_group": f"legacy-inline-{slugify(section.path.name)}",
                "origin": {
                    "kind": origin_kind_for_source(section, "legacy-inline-source"),
                    "ref": section.fields.get("Source", "").strip() or section.legacy_id,
                },
                "artifact_refs": [f"artifacts/legacy-context/domains/{section.path.name}"],
                "quote": section.fields.get("Quote", "").strip() or section.fields.get("Claim", "").strip(),
                "tags": ["legacy-import", slugify(section.path.stem)],
                "note": note_with_legacy(section, "Inline source created because the legacy section did not reference a first-class source object."),
            },
        )
        return [inline_source_id]

    # 3. Claims from facts/observations/evidence/hypotheses/conflicts and approved facts.
    file_groups = [
        ("smartpick-facts.md", "fact"),
        ("smartpick-observations.md", "observation"),
        ("smartpick-evidence.md", "evidence"),
        ("smartpick-hypotheses.md", "hypothesis"),
        ("smartpick-conflicts.md", "conflict"),
        ("approved-facts.md", "fact"),
    ]
    for file_name, record_group in file_groups:
        path = backup_root / "domains" / file_name
        if not path.exists():
            continue
        for section in parse_sections(path):
            source_refs = source_refs_for_section(section)
            if file_name == "approved-facts.md" and grouped_criteria_source_id:
                source_refs = [grouped_criteria_source_id]

            support_refs = [legacy_to_new[ref] for ref in collect_refs(section.fields.get("Source", "")) if ref in legacy_to_new and records[legacy_to_new[ref]]["record_type"] == "claim"]
            claim_payload = {
                "plane": plane_from_section(section, record_group),
                "status": claim_status_from_section(section, record_group),
                "scope": section.fields.get("Scope", "").strip() or "legacy-import",
                "statement": section.fields.get("Claim", "").strip() or section.title,
                "source_refs": sorted(set(source_refs)),
                "support_refs": sorted(set(support_refs)),
                "contradiction_refs": [],
                "derived_from": [],
                "recorded_at": now_timestamp(),
                "tags": ["legacy-import", slugify(file_name.removesuffix(".md")), slugify(section.legacy_id)],
                "note": note_with_legacy(section),
            }
            if record_group == "conflict":
                claim_payload["status"] = "contested"
                claim_payload["contradiction_refs"] = sorted(set(support_refs))
            if record_group == "hypothesis":
                claim_payload["status"] = "tentative"

            claim_id = add_record("claim", claim_payload, legacy_id=section.legacy_id)
            migration_notes.append(f"{section.legacy_id} -> {claim_id} (claim:{record_group})")
            if record_group == "hypothesis":
                hypothesis_entries.append(
                    {
                        "claim_ref": claim_id,
                        "scope": claim_payload["scope"],
                        "status": "active",
                        "created_at": now_timestamp(),
                        "updated_at": now_timestamp(),
                        "note": f"legacy hypothesis index entry for {section.legacy_id}",
                    }
                )

    # 4. Debts.
    known_debts_path = backup_root / "domains" / "known-debts.md"
    if known_debts_path.exists():
        for section in parse_sections(known_debts_path):
            evidence_refs = []
            for ref in collect_refs(section.fields.get("Source", "")):
                mapped = legacy_to_new.get(ref)
                if mapped:
                    evidence_refs.append(mapped)
            if not evidence_refs:
                evidence_refs = source_refs_for_section(section)
            debt_id = add_record(
                "debt",
                {
                    "scope": section.fields.get("Scope", "").strip() or "legacy-import",
                    "title": section.fields.get("Claim", "").strip()[:180],
                    "status": "open",
                    "priority": "medium",
                    "evidence_refs": sorted(set(evidence_refs)),
                    "plan_refs": [],
                    "created_at": now_timestamp(),
                    "updated_at": now_timestamp(),
                    "tags": ["legacy-import", "known-debt"],
                    "note": note_with_legacy(section),
                },
                legacy_id=section.legacy_id,
            )
            migration_notes.append(f"{section.legacy_id} -> {debt_id} (debt)")

    # 5. Open questions.
    open_questions_path = backup_root / "domains" / "smartpick-open-questions.md"
    if open_questions_path.exists():
        for section in parse_open_questions(open_questions_path):
            related_claim_refs = [legacy_to_new[ref] for ref in collect_refs(section.body) if ref in legacy_to_new and records[legacy_to_new[ref]]["record_type"] == "claim"]
            status = "resolved" if "[resolved" in section.title.lower() else "open"
            open_id = add_record(
                "open_question",
                {
                    "domain": "smartpick",
                    "scope": "tests/e2e/smartpick legacy migration",
                    "aspect": "legacy-open-question",
                    "status": status,
                    "question": re.sub(r"\s*\[resolved.*\]$", "", section.title).strip(),
                    "related_claim_refs": sorted(set(related_claim_refs)),
                    "related_model_refs": [],
                    "related_flow_refs": [],
                    "resolved_by_claim_refs": [],
                    "created_at": now_timestamp(),
                    "note": f"legacy_id={section.legacy_id}\n\nlegacy_file={section.path.name}\n\n{section.body}",
                },
                legacy_id=section.legacy_id,
            )
            migration_notes.append(f"{section.legacy_id} -> {open_id} (open_question)")

    if hypothesis_entries:
        write_hypotheses_index(source_root, hypothesis_entries)

    # 6. Migration artifacts/report.
    (source_root / "review" / "migration.md").write_text(
        "# Legacy Migration Report\n\n"
        f"Legacy backup: `{backup_root}`\n\n"
        "This migration was conservative. Legacy markdown ledgers were backed up and copied under `artifacts/legacy-context/`.\n"
        "Only records with an explicit typed structure were promoted into canonical JSON records.\n\n"
        "## Legacy Mapping\n\n"
        + "\n".join(f"- {line}" for line in migration_notes)
        + "\n",
        encoding="utf-8",
    )
    write_json_file(
        source_root / "artifacts" / "legacy-id-map.json",
        {
            "generated_at": now_timestamp(),
            "legacy_backup_path": str(backup_root),
            "mapping": legacy_to_new,
        },
    )

    print(f"Backed up legacy context to {backup_root}")
    print(f"Migrated legacy context into {source_root}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Migrate a legacy markdown-ledger .codex_context.")
    parser.add_argument("path", help="Path to the legacy .codex_context directory")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    source_root = Path(args.path).expanduser().resolve()
    if not source_root.is_dir():
        raise SystemExit(f"legacy context directory not found: {source_root}")
    migrate(source_root)


if __name__ == "__main__":
    main()
