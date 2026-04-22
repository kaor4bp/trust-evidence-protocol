#!/usr/bin/env python3
"""Explicit .codex_context commands for the trust-evidence-protocol plugin."""

from __future__ import annotations

import argparse
import copy
import json
import os
import re
import secrets
import shlex
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path

from context_lib import (
    ALLOWED_FREEDOM,
    ACTION_STATUSES,
    ACTION_SAFETY_CLASSES,
    ATTENTION_MODES,
    ANALYSIS_INSTALL_POLICIES,
    ANALYSIS_MISSING_DEPENDENCY_POLICIES,
    BACKEND_MODES,
    CLAIM_COMPARATORS,
    CLAIM_KINDS,
    CLAIM_PLANES,
    CLAIM_POLARITIES,
    CLAIM_STATUSES,
    COCOINDEX_SCOPES,
    CODE_INDEX_ALLOWED_RECORD_TYPES,
    CODE_INDEX_ANNOTATION_KINDS,
    CODE_INDEX_ANNOTATION_STATUSES,
    CODE_INDEX_ID_PATTERN,
    CODE_INDEX_LINK_KEYS,
    CODE_INDEX_STATUSES,
    CODE_INDEX_TARGET_KINDS,
    CODE_INTELLIGENCE_BACKENDS,
    CODE_SMELL_CATEGORIES,
    CODE_SMELL_SEVERITIES,
    CONFIDENCE_LEVELS,
    CONTEXT_BUDGET_KEYS,
    CONTEXT_BUDGET_VALUES,
    CRITIQUE_STATUSES,
    DEBT_STATUSES,
    DERIVATION_BACKENDS,
    DEFAULT_BACKEND_SETTINGS,
    FACT_VALIDATION_BACKENDS,
    GUIDELINE_APPLIES_TO,
    GUIDELINE_DOMAINS,
    GUIDELINE_PRIORITIES,
    GUIDELINE_STATUSES,
    INPUT_CAPTURE_MODES,
    INPUT_FILE_MENTION_MODES,
    INPUT_KINDS,
    LOGIC_SOLVER_BACKENDS,
    LOGIC_SOLVER_MODES,
    LOGIC_SOLVER_OPTIONAL_BACKENDS,
    MODEL_FLOW_AUTHORITY_STATUSES,
    MODEL_KNOWLEDGE_CLASSES,
    MODEL_STATUSES,
    NEXT_STEP_INTENTS,
    OPEN_QUESTION_STATUSES,
    PERMISSION_REQUIRED_FREEDOMS,
    PERMISSION_APPLIES_TO,
    PLAN_STATUSES,
    PRIORITY_LEVELS,
    PROPOSAL_STATUSES,
    PROJECT_STATUSES,
    RESTRICTION_APPLIES_TO,
    RESTRICTION_SEVERITIES,
    RESTRICTION_STATUSES,
    SOURCE_KINDS,
    ATTENTION_SCOPES,
    CURIOSITY_MAP_VOLUMES,
    TAP_KINDS,
    TASK_STATUSES,
    TASK_EXECUTION_MODES,
    TASK_TYPES,
    TASK_TERMINAL_OUTCOMES,
    TOPIC_PREFILTER_BACKENDS,
    TOPIC_PREFILTER_OPTIONAL_BACKENDS,
    TOPIC_PREFILTER_REBUILD_MODES,
    WORKING_CONTEXT_KINDS,
    WORKING_CONTEXT_STATUSES,
    WORKSPACE_STATUSES,
    claim_is_user_confirmed_theory,
    add_remove_values,
    access_report_payload,
    access_report_text_lines,
    append_access_event,
    append_tap_event,
    attention_map_text_lines,
    backend_status_payload,
    backend_status_text_lines,
    build_attention_index,
    curiosity_map_html,
    curiosity_map_payload,
    curiosity_map_text_lines,
    map_brief_payload,
    map_brief_text_lines,
    build_action_payload,
    apply_atomic_plan_decomposition,
    apply_atomic_task_decomposition,
    apply_decomposed_plan_decomposition,
    apply_decomposed_task_decomposition,
    build_claim_payload,
    build_comparison_payload,
    build_context_brief_payload,
    build_next_step_payload,
    build_flow_oracle,
    build_flow_payload,
    build_flow_preconditions,
    build_flow_step,
    promote_flow_to_domain_payloads,
    build_debt_payload,
    build_guideline_payload,
    build_input_payload,
    build_logic_payload,
    build_manual_code_index_entry,
    build_model_payload,
    promote_model_to_domain_payloads,
    build_open_question_payload,
    build_index,
    build_plan_payload,
    build_permission_payload,
    build_precedent_review_payload,
    build_project_payload,
    build_workspace_payload,
    build_proposal_payload,
    build_restriction_payload,
    build_impact_graph_payload,
    build_reasoning_case_payload,
    build_rollback_report_payload,
    build_source_payload,
    build_task_drift_payload,
    build_task_payload,
    build_working_context_payload,
    claim_attention,
    claim_line,
    claim_is_archived,
    claim_is_fallback,
    claim_lifecycle,
    claim_lifecycle_state,
    claim_retrieval_tier,
    mutate_claim_lifecycle_payload,
    cleanup_archive_apply_payload,
    cleanup_archive_plan_payload,
    cleanup_archive_plan_text_lines,
    cleanup_archives_payload,
    cleanup_archives_text_lines,
    cleanup_restore_apply_payload,
    cleanup_restore_plan_payload,
    cleanup_restore_plan_text_lines,
    cleanup_candidate_items,
    collect_claim_refs_from_models_flows,
    concise,
    close_working_context_payload,
    collect_validation_errors,
    collect_dependency_impact,
    collect_link_edges,
    context_write_lock,
    context_brief_text_lines,
    next_step_text_lines,
    code_index_entries_root,
    code_index_entry_path,
    cocoindex_index_payload,
    cocoindex_index_text_lines,
    cocoindex_search_payload,
    cocoindex_search_text_lines,
    enrich_backend_results_with_cix,
    active_restrictions_for,
    attention_diagram_mermaid_lines,
    attention_diagram_metrics,
    attention_diagram_payload,
    attention_diagram_text_lines,
    augment_evidence_chain_payload,
    augmented_evidence_chain_text_lines,
    DEFAULT_CHAIN_PERMIT_TTL_SECONDS,
    chain_permit_text_lines,
    create_chain_permit,
    current_project_ref,
    current_task_ref,
    curiosity_probe_text_lines,
    current_workspace_ref,
    decision_validation_payload,
    decision_validation_text_lines,
    dependency_refs_for_record,
    evidence_chain_report_lines,
    effective_logic_solver,
    export_rdf_text,
    file_metadata,
    guideline_detail_lines,
    guideline_summary_line,
    invalidate_hydration_state,
    is_strictness_escalation,
    filter_attention_payload,
    input_items_for_task,
    join_quote_items,
    linked_records_payload,
    load_attention_payload,
    load_access_events,
    load_strictness_requests,
    load_tap_events,
    mark_knowledge_records_stale_payloads,
    next_record_id,
    next_artifact_id,
    next_strictness_request_id,
    normalize_quote,
    now_timestamp,
    parse_proposal_option,
    permission_allows_strictness,
    project_detail_lines,
    project_refs_for_write,
    project_summary_line,
    proposal_summary_line,
    public_record_summary,
    ranked_record_search,
    record_detail_payload,
    record_detail_text_lines,
    record_summary,
    ref_paths,
    record_path,
    active_guidelines_for,
    active_hypotheses_for,
    active_hypothesis_entry_by_claim,
    active_permissions_for,
    ANCHOR_FILENAME,
    anchor_context_root,
    anchor_task_ref,
    assign_project_payload,
    assign_workspace_payload,
    assign_task_payload,
    build_file_payload,
    build_hypothesis_entry,
    build_run_payload,
    close_hypothesis_entries,
    record_belongs_to_project,
    record_belongs_to_task,
    resolve_context_root,
    restriction_detail_lines,
    resolve_guideline_scope,
    resolve_permission_scope,
    resolve_restriction_scope,
    restriction_summary_line,
    impact_graph_text_lines,
    rollback_report_text_lines,
    select_fallback_claims,
    select_backend_status,
    select_records,
    safe_list,
    stale_knowledge_target_ids,
    logic_solver_settings,
    structural_logic_check_payload,
    structural_logic_check_text_lines,
    finish_task_payload,
    fork_working_context_payload,
    infer_file_kind,
    strictness_request_allows_change,
    task_refs_for_write,
    workspace_refs_for_write,
    task_detail_lines,
    pause_task_for_switch_payload,
    parse_working_context_assumptions,
    precedent_review_text_lines,
    resume_task_payload,
    reasoning_case_text_lines,
    score_record,
    select_precedent_tasks,
    validate_evidence_chain_payload,
    is_mutating_action_kind,
    hypothesis_active_entry_exists,
    validate_records_state,
    validate_candidate_record,
    remove_hypothesis_entries,
    reopen_hypothesis_entry,
    sync_hypothesis_entries,
    validate_facts_payload,
    validate_facts_text_lines,
    validate_hypothesis_claim,
    write_json_file,
    write_text_file,
    write_backlog,
    write_conflicts_report,
    write_flows_report,
    write_hypotheses_report,
    write_attention_report,
    write_attention_index_reports,
    write_models_report,
    write_resolved_report,
    write_settings,
    source_line,
    write_strictness_requests,
    write_stale_report,
    write_validation_report,
    z3_logic_check_text_lines,
    working_context_detail_lines,
    working_context_show_payload,
    load_settings,
    load_records,
    load_code_index_entries,
    find_anchor,
    find_anchor_path,
    load_hypotheses_index,
    load_anchor,
    write_hypotheses_index,
    task_drift_text_lines,
    task_decomposition_text_lines,
    task_identity_text,
    task_outcome_check_payload,
    task_outcome_check_text_lines,
    task_related_counts,
    task_summary_line,
    plan_decomposition_text_lines,
    unclassified_input_items,
    validate_plan_decomposition_payload,
    validate_task_decomposition_payload,
)
from logic_z3 import analyze_logic_payload_with_z3
from tep_runtime.cli_common import (
    TEP_ICON,
    append_note,
    candidate_record_payload,
    command_requires_write_lock,
    load_clean_context,
    load_valid_context_readonly,
    parse_csv_refs,
    persist_candidate,
    persist_mutated_records,
    print_errors,
    public_record_payload,
    refresh_generated_outputs,
    refresh_with_existing_records,
    sanitize_artifact_name,
    validate_mutated_records,
)
from tep_runtime.code_index import (
    annotation_snapshot,
    code_entry_freshness,
    code_entry_matching_annotations,
    code_entries_text_lines,
    code_index_entry_for_file,
    code_index_path_matches,
    code_index_rel_path,
    code_smell_report_payload,
    code_smell_report_text_lines,
    code_smell_rows,
    discover_files,
    next_code_index_id,
    normalize_smell_categories,
    parse_code_fields,
    persist_code_index_entries,
    project_code_entry,
    public_code_index_entry,
    resolve_code_entry,
)

RECORD_LINK_RELATIONS = {
    "related": "is related to",
    "supports": "supports",
    "contradicts": "contradicts",
    "depends-on": "depends on",
    "derived-from": "is derived from",
    "no-known-link": "has no known established link to",
    "rejected-link": "does not have the proposed link to",
}
from tep_runtime.repo_scope import (
    code_entry_matches_repo_scope,
    normalize_root_refs,
    path_contains,
    repo_scope_for_root,
    repo_scope_payload,
    resolve_code_repo_root,
)
from tep_runtime.logic_index import (
    build_logic_index_payload,
    load_logic_index_payload,
    load_logic_vocabulary_graph,
    logic_conflict_candidates_from_payload,
    write_logic_index_reports,
)
from tep_runtime.topic_index import (
    build_lexical_topic_index,
    infer_topic_terms_from_refs,
    load_topic_records,
    task_terms,
    topic_conflict_candidates,
    topic_index_paths,
    topic_search_matches,
    topic_tokenize,
    write_topic_index_reports,
)


FEEDBACK_KINDS = {
    "bug",
    "friction",
    "false-positive",
    "false-negative",
    "docs-gap",
    "performance",
    "missing-tool",
    "policy-conflict",
    "migration-issue",
    "other",
}
FEEDBACK_SURFACES = {
    "cli",
    "hook",
    "mcp",
    "skill",
    "docs",
    "context-merge",
    "code-index",
    "reasoning",
    "runtime",
    "other",
}
FEEDBACK_SEVERITY_TO_PRIORITY = {
    "critical": "critical",
    "high": "high",
    "medium": "medium",
    "low": "low",
}


def cmd_hypothesis_add(
    root: Path,
    claim_ref: str,
    domain: str | None,
    scope: str | None,
    model_refs: list[str],
    flow_refs: list[str],
    action_refs: list[str],
    plan_refs: list[str],
    rollback_refs: list[str],
    mode: str,
    based_on_hypotheses: list[str],
    note: str,
) -> int:
    records, exit_code = refresh_with_existing_records(root)
    if exit_code:
        return 1
    error = validate_hypothesis_claim(records, claim_ref)
    if error:
        print(error)
        return 1
    for ref in based_on_hypotheses:
        parent_error = validate_hypothesis_claim(records, ref)
        if parent_error:
            print(f"based_on_hypothesis {ref}: {parent_error}")
            return 1
    if based_on_hypotheses and mode != "exploration":
        print("based_on_hypotheses is allowed only with mode=exploration")
        return 1

    entries, parse_errors = load_hypotheses_index(root)
    if parse_errors:
        print_errors(parse_errors)
        return 1
    if hypothesis_active_entry_exists(entries, claim_ref):
        print(f"active hypothesis entry already exists for {claim_ref}")
        return 1

    claim = records[claim_ref]
    timestamp = now_timestamp()
    entry = build_hypothesis_entry(
        claim=claim,
        claim_ref=claim_ref,
        timestamp=timestamp,
        domain=domain,
        scope=scope,
        model_refs=model_refs,
        flow_refs=flow_refs,
        action_refs=action_refs,
        plan_refs=plan_refs,
        rollback_refs=rollback_refs,
        mode=mode,
        based_on_hypotheses=based_on_hypotheses,
        note=note,
    )
    entries.append(entry)
    write_hypotheses_index(root, entries)
    refresh_generated_outputs(root, records)
    invalidate_hydration_state(root, f"added hypothesis index entry for {claim_ref}")
    print(f"Added hypothesis index entry for {claim_ref}")
    return 0


def cmd_hypothesis_list(root: Path, status: str | None) -> int:
    records, _ = load_records(root)
    entries, parse_errors = load_hypotheses_index(root)
    if parse_errors:
        print_errors(parse_errors)
        return 1
    filtered = entries
    if status:
        filtered = [entry for entry in entries if str(entry.get("status", "")).strip() == status]
    if not filtered:
        print("No hypothesis entries found.")
        return 0
    for entry in filtered:
        claim_ref = str(entry.get("claim_ref", "")).strip()
        claim = records.get(claim_ref, {})
        scope = str(entry.get("scope", "")).strip()
        entry_status = str(entry.get("status", "")).strip()
        statement = str(claim.get("statement", "")).strip()
        print(f"{claim_ref}\t{entry_status}\t{scope}\t{statement}")
    return 0


def cmd_hypothesis_close(root: Path, claim_ref: str, status: str, note: str | None) -> int:
    records, exit_code = refresh_with_existing_records(root)
    if exit_code:
        return 1
    entries, parse_errors = load_hypotheses_index(root)
    if parse_errors:
        print_errors(parse_errors)
        return 1
    entries, updated = close_hypothesis_entries(entries, claim_ref, status, now_timestamp(), note)
    if not updated:
        print(f"no active hypothesis entry found for {claim_ref}")
        return 1
    write_hypotheses_index(root, entries)
    refresh_generated_outputs(root, records)
    invalidate_hydration_state(root, f"closed hypothesis index entry for {claim_ref} as {status}")
    print(f"Closed hypothesis index entry for {claim_ref} as {status}")
    return 0


def cmd_hypothesis_reopen(root: Path, claim_ref: str, note: str | None) -> int:
    records, exit_code = refresh_with_existing_records(root)
    if exit_code:
        return 1
    error = validate_hypothesis_claim(records, claim_ref)
    if error:
        print(error)
        return 1
    entries, parse_errors = load_hypotheses_index(root)
    if parse_errors:
        print_errors(parse_errors)
        return 1

    entries, reopen_status = reopen_hypothesis_entry(entries, claim_ref, now_timestamp(), note)
    if reopen_status == "active-exists":
        print(f"active hypothesis entry already exists for {claim_ref}")
        return 1
    if reopen_status == "missing":
        print(f"no closed hypothesis entry found for {claim_ref}")
        return 1

    write_hypotheses_index(root, entries)
    refresh_generated_outputs(root, records)
    invalidate_hydration_state(root, f"reopened hypothesis index entry for {claim_ref}")
    print(f"Reopened hypothesis index entry for {claim_ref}")
    return 0


def cmd_hypothesis_remove(root: Path, claim_ref: str) -> int:
    records, exit_code = refresh_with_existing_records(root)
    if exit_code:
        return 1
    entries, parse_errors = load_hypotheses_index(root)
    if parse_errors:
        print_errors(parse_errors)
        return 1
    remaining, removed = remove_hypothesis_entries(entries, claim_ref)
    if not removed:
        print(f"no hypothesis entry found for {claim_ref}")
        return 1
    write_hypotheses_index(root, remaining)
    refresh_generated_outputs(root, records)
    invalidate_hydration_state(root, f"removed hypothesis index entry for {claim_ref}")
    print(f"Removed hypothesis index entry for {claim_ref}")
    return 0


def cmd_hypothesis_sync(root: Path, drop_closed: bool) -> int:
    records, record_errors = load_records(root)
    structural_errors = [error for error in record_errors if error.path.name != "hypotheses.jsonl"]
    if structural_errors:
        print_errors(structural_errors)
        return 1
    entries, parse_errors = load_hypotheses_index(root)
    if parse_errors:
        print_errors(parse_errors)
        return 1

    kept, removed = sync_hypothesis_entries(entries, records, drop_closed)

    write_hypotheses_index(root, kept)
    refreshed_records, _ = load_records(root)
    write_validation_report(root, [])
    refresh_generated_outputs(root, refreshed_records)
    invalidate_hydration_state(root, "synced hypothesis index")
    if not removed:
        print("Hypothesis index already in sync.")
        return 0
    print("Removed hypothesis entries:")
    for item in removed:
        print(f"- {item}")
    return 0


def print_project_detail(project: dict) -> None:
    for line in project_detail_lines(project):
        print(line)


def workspace_detail_lines(workspace: dict) -> list[str]:
    lines = [
        f"- `{workspace.get('id')}` status=`{workspace.get('status')}` "
        f"key=`{workspace.get('workspace_key')}` title=\"{workspace.get('title', '')}\""
    ]
    context_root = str(workspace.get("context_root", "")).strip()
    if context_root:
        lines.append(f"  context_root: {context_root}")
    for key in ("root_refs", "project_refs"):
        values = workspace.get(key, [])
        if values:
            lines.append(f"  {key}: {values}")
    return lines


def print_workspace_detail(workspace: dict) -> None:
    for line in workspace_detail_lines(workspace):
        print(line)


def anchor_path_for(directory: str | None) -> Path:
    base = Path(directory).expanduser() if directory else Path.cwd()
    return base.resolve() / ANCHOR_FILENAME


def cmd_init_anchor(
    root: Path,
    directory: str | None,
    workspace_ref: str,
    project_ref: str | None,
    task_ref: str | None,
    allowed_freedom: str | None,
    hook_verbosity: str | None,
    force: bool,
    note: str,
) -> int:
    records, exit_code = load_valid_context_readonly(root)
    if exit_code:
        return exit_code
    if workspace_ref not in records or records[workspace_ref].get("record_type") != "workspace":
        print(f"{workspace_ref} must reference a workspace record")
        return 1
    if project_ref:
        if project_ref not in records or records[project_ref].get("record_type") != "project":
            print(f"{project_ref} must reference a project record")
            return 1
        workspace_projects = records[workspace_ref].get("project_refs", [])
        if project_ref not in workspace_projects:
            print(f"{project_ref} is not listed in {workspace_ref}.project_refs")
            return 1
    if task_ref:
        if task_ref not in records or records[task_ref].get("record_type") != "task":
            print(f"{task_ref} must reference a task record")
            return 1
        task_workspaces = records[task_ref].get("workspace_refs", [])
        if task_workspaces and workspace_ref not in task_workspaces:
            print(f"{task_ref} is not scoped to {workspace_ref}")
            return 1
        task_projects = records[task_ref].get("project_refs", [])
        if project_ref and task_projects and project_ref not in task_projects:
            print(f"{task_ref} is not scoped to {project_ref}")
            return 1

    path = anchor_path_for(directory)
    if path.exists() and not force:
        print(f"{path} already exists; use --force to overwrite")
        return 1
    payload: dict[str, object] = {
        "schema_version": 1,
        "context_root": str(root),
        "workspace_ref": workspace_ref,
        "project_ref": project_ref,
        "task_ref": task_ref,
        "settings": {},
        "note": note,
    }
    settings: dict[str, object] = {}
    if allowed_freedom:
        settings["allowed_freedom"] = allowed_freedom
    if hook_verbosity:
        settings["hooks"] = {"verbosity": hook_verbosity}
    payload["settings"] = settings
    write_json_file(path, payload)
    print(f"Wrote local TEP anchor: {path}")
    return 0


def cmd_show_anchor(start: str | None) -> int:
    anchor = find_anchor(start or Path.cwd())
    if not anchor:
        print("No .tep anchor found.")
        return 0
    path = anchor.get("_path", "")
    print(f"Anchor: {path}")
    print(f"context_root={anchor_context_root(anchor) or ''}")
    print(f"workspace_ref={anchor.get('workspace_ref') or ''}")
    print(f"project_ref={anchor.get('project_ref') or ''}")
    print(f"task_ref={anchor_task_ref(anchor)}")
    settings = anchor.get("settings", {})
    if isinstance(settings, dict) and settings:
        print(f"settings={json.dumps(settings, sort_keys=True)}")
    return 0


def cmd_validate_anchor(root: Path, start: str | None) -> int:
    anchor_path = find_anchor_path(start or Path.cwd())
    if anchor_path is None:
        print("No .tep anchor found.")
        return 1
    anchor = load_anchor(anchor_path)
    anchor_root = anchor_context_root(anchor)
    if anchor_root != root.resolve():
        print(f"{anchor_path}: context_root does not resolve to active context {root}")
        return 1

    records, exit_code = load_valid_context_readonly(root)
    if exit_code:
        return exit_code
    workspace_ref = str(anchor.get("workspace_ref") or "").strip()
    project_ref = str(anchor.get("project_ref") or "").strip()
    task_ref = str(anchor.get("task_ref") or "").strip()
    if workspace_ref not in records or records[workspace_ref].get("record_type") != "workspace":
        print(f"{anchor_path}: workspace_ref must reference a workspace record")
        return 1
    if project_ref:
        if project_ref not in records or records[project_ref].get("record_type") != "project":
            print(f"{anchor_path}: project_ref must reference a project record")
            return 1
        if project_ref not in records[workspace_ref].get("project_refs", []):
            print(f"{anchor_path}: project_ref is not listed in workspace.project_refs")
            return 1
    if task_ref:
        if task_ref not in records or records[task_ref].get("record_type") != "task":
            print(f"{anchor_path}: task_ref must reference a task record")
            return 1
        task_workspaces = records[task_ref].get("workspace_refs", [])
        if task_workspaces and workspace_ref not in task_workspaces:
            print(f"{anchor_path}: task_ref is not scoped to workspace_ref")
            return 1
        task_projects = records[task_ref].get("project_refs", [])
        if project_ref and task_projects and project_ref not in task_projects:
            print(f"{anchor_path}: task_ref is not scoped to project_ref")
            return 1
    print(f"Validated local TEP anchor: {anchor_path}")
    return 0


def print_restriction_detail(restriction: dict) -> None:
    for line in restriction_detail_lines(restriction):
        print(line)


def print_guideline_detail(guideline: dict) -> None:
    for line in guideline_detail_lines(guideline):
        print(line)


def cmd_record_workspace(
    root: Path,
    workspace_key: str,
    title: str,
    context_root: str | None,
    root_refs: list[str],
    project_refs: list[str],
    status: str,
    tags: list[str],
    note: str,
) -> int:
    records, exit_code = load_clean_context(root)
    if exit_code:
        return 1
    for project_ref in project_refs:
        if project_ref not in records or records[project_ref].get("record_type") != "project":
            print(f"{project_ref} must reference a project record")
            return 1

    timestamp = now_timestamp()
    payload = build_workspace_payload(
        record_id=next_record_id(records, "WSP-"),
        timestamp=timestamp,
        workspace_key=workspace_key,
        title=title,
        status=status,
        context_root=context_root or str(root),
        root_refs=normalize_root_refs(root_refs),
        project_refs=project_refs,
        tags=tags,
        note=note,
    )
    return persist_candidate(root, records, payload, "workspace")


def cmd_show_workspace(root: Path, show_all: bool) -> int:
    records, exit_code = load_valid_context_readonly(root)
    if exit_code:
        return exit_code
    workspaces = [data for data in records.values() if data.get("record_type") == "workspace"]
    if show_all:
        if not workspaces:
            print("No workspace records found.")
            return 0
        for workspace in sorted(workspaces, key=lambda item: str(item.get("workspace_key", ""))):
            print_workspace_detail(workspace)
        return 0

    ref = current_workspace_ref(root)
    if not ref:
        print("No current workspace.")
        return 0
    workspace = records.get(ref)
    if not workspace:
        print(f"Current workspace ref is missing: {ref}")
        return 1
    print("Current workspace:")
    print_workspace_detail(workspace)
    return 0


def cmd_set_current_workspace(root: Path, workspace_ref: str | None, clear: bool) -> int:
    records, exit_code = load_clean_context(root)
    if exit_code:
        return 1
    if clear:
        write_settings(root, current_workspace_ref=None)
        refresh_generated_outputs(root, records)
        invalidate_hydration_state(root, "cleared current workspace")
        print("Cleared current workspace")
        return 0
    if not workspace_ref:
        print("set-current-workspace requires --workspace or --clear")
        return 1
    workspace = records.get(workspace_ref)
    if not workspace or workspace.get("record_type") != "workspace":
        print(f"{workspace_ref} must reference a workspace record")
        return 1
    write_settings(root, current_workspace_ref=workspace_ref)
    refresh_generated_outputs(root, records)
    invalidate_hydration_state(root, f"set current workspace {workspace_ref}")
    print(f"Set current workspace {workspace_ref}")
    return 0


def cmd_assign_workspace(
    root: Path,
    workspace_ref: str,
    record_refs: list[str],
    records_file: str | None,
    all_unassigned: bool,
    note: str | None,
) -> int:
    records, exit_code = load_clean_context(root)
    if exit_code:
        return 1
    if workspace_ref not in records or records[workspace_ref].get("record_type") != "workspace":
        print(f"{workspace_ref} must reference a workspace record")
        return 1
    if records_file:
        try:
            record_refs.extend(
                line.strip()
                for line in Path(records_file).expanduser().read_text(encoding="utf-8").splitlines()
                if line.strip()
            )
        except OSError as exc:
            print(f"{records_file}: {exc}")
            return 1
    if not record_refs and not all_unassigned:
        print("assign-workspace requires --record, --records-file, or --all-unassigned")
        return 1

    timestamp = now_timestamp()
    if all_unassigned:
        targets = [
            record_id
            for record_id, data in records.items()
            if data.get("record_type") != "workspace" and not data.get("workspace_refs")
        ]
    else:
        targets = []
        for record_ref in record_refs:
            if record_ref not in records:
                print(f"missing record {record_ref}")
                return 1
            if records[record_ref].get("record_type") == "workspace":
                print("assign-workspace target must not be a workspace record")
                return 1
            targets.append(record_ref)

    updates = {
        target: assign_workspace_payload(public_record_payload(records[target]), timestamp, workspace_ref, note)
        for target in targets
    }
    project_targets = [
        target
        for target in targets
        if records[target].get("record_type") == "project"
        and target not in records[workspace_ref].get("project_refs", [])
    ]
    if project_targets:
        workspace_payload = public_record_payload(records[workspace_ref])
        workspace_payload["project_refs"] = sorted({*workspace_payload.get("project_refs", []), *project_targets})
        workspace_payload["updated_at"] = timestamp
        workspace_payload["note"] = append_note(
            str(workspace_payload.get("note", "")),
            f"[{timestamp}] linked projects through assign-workspace: {', '.join(project_targets)}",
        )
        updates[workspace_ref] = workspace_payload
    merged_records, errors = validate_mutated_records(root, records, updates)
    if errors:
        print_errors(errors)
        return 1
    reason = (
        f"Assigned {len(targets)} unassigned record(s) to workspace {workspace_ref}"
        if all_unassigned
        else f"Assigned {len(targets)} record(s) to workspace {workspace_ref}"
    )
    changed_ids = [*targets]
    if workspace_ref in updates:
        changed_ids.append(workspace_ref)
    return persist_mutated_records(root, merged_records, changed_ids, reason)


def resolve_code_repo_root_or_exit(root: Path, requested_root: str | Path | None, *, fallback_to_cwd: bool = True) -> tuple[Path, str]:
    repo_root, repo_root_source = resolve_code_repo_root(root, requested_root, fallback_to_cwd=fallback_to_cwd)
    if repo_root is None:
        print("missing repository root")
        raise SystemExit(1)
    return repo_root, repo_root_source


def workspace_admission_payload(root: Path, records: dict[str, dict], repo: Path) -> dict:
    current_workspace = current_workspace_ref(root)
    current_project = current_project_ref(root)
    target = repo.expanduser().resolve()
    projects = [
        public_record_payload(record)
        for record in records.values()
        if record.get("record_type") == "project" and str(record.get("status", "active")) == "active"
    ]
    workspaces = [
        public_record_payload(record)
        for record in records.values()
        if record.get("record_type") == "workspace" and str(record.get("status", "active")) == "active"
    ]
    matching_projects = [
        {"id": project.get("id"), "root_refs": project.get("root_refs", [])}
        for project in projects
        if any(path_contains(str(root_ref), target) for root_ref in project.get("root_refs", []))
    ]
    matching_workspaces = [
        {"id": workspace.get("id"), "root_refs": workspace.get("root_refs", []), "project_refs": workspace.get("project_refs", [])}
        for workspace in workspaces
        if any(path_contains(str(root_ref), target) for root_ref in workspace.get("root_refs", []))
        or any(project.get("id") in workspace.get("project_refs", []) for project in matching_projects)
    ]
    known = bool(matching_projects or matching_workspaces)
    in_current_workspace = bool(
        current_workspace
        and any(workspace.get("id") == current_workspace for workspace in matching_workspaces)
    )
    in_current_project = bool(
        current_project
        and any(project.get("id") == current_project for project in matching_projects)
    )
    requires_user_decision = not (in_current_project or in_current_workspace)
    recommendation = "known-current-project" if in_current_project else "known-current-workspace" if in_current_workspace else "ask-user"
    return {
        "workspace_admission_is_proof": False,
        "repo": str(target),
        "current_workspace_ref": current_workspace,
        "current_project_ref": current_project,
        "known": known,
        "in_current_workspace": in_current_workspace,
        "in_current_project": in_current_project,
        "requires_user_decision": requires_user_decision,
        "recommendation": recommendation,
        "matching_projects": matching_projects,
        "matching_workspaces": matching_workspaces,
        "options": [
            "create-new-workspace",
            "add-project-to-current-workspace",
            "inspect-readonly-without-persisting",
        ]
        if requires_user_decision
        else [],
    }


def workspace_admission_text_lines(payload: dict) -> list[str]:
    lines = [
        f"Workspace admission for: {payload.get('repo')}",
        f"Known: {'yes' if payload.get('known') else 'no'}",
        f"Current workspace: {payload.get('current_workspace_ref') or '<none>'}",
        f"Current project: {payload.get('current_project_ref') or '<none>'}",
        f"Requires user decision: {'yes' if payload.get('requires_user_decision') else 'no'}",
        f"Recommendation: {payload.get('recommendation')}",
    ]
    if payload.get("requires_user_decision"):
        lines.append("Ask the user whether this repo starts a new workspace, becomes a project in the current workspace, or should be inspected read-only without persistence.")
    return lines


def cmd_workspace_admission_check(root: Path, repo: Path, output_format: str) -> int:
    records, exit_code = load_valid_context_readonly(root)
    if exit_code:
        return exit_code
    payload = workspace_admission_payload(root, records, repo)
    if output_format == "json":
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        for line in workspace_admission_text_lines(payload):
            print(line)
    return 0


def cmd_record_project(
    root: Path,
    project_key: str,
    title: str,
    root_refs: list[str],
    workspace_refs: list[str],
    status: str,
    related_project_refs: list[str],
    tags: list[str],
    note: str,
) -> int:
    records, exit_code = load_clean_context(root)
    if exit_code:
        return 1

    timestamp = now_timestamp()
    resolved_workspace_refs = workspace_refs_for_write(root, workspace_refs)
    payload = build_project_payload(
        record_id=next_record_id(records, "PRJ-"),
        timestamp=timestamp,
        project_key=project_key,
        title=title,
        status=status,
        root_refs=normalize_root_refs(root_refs),
        related_project_refs=related_project_refs,
        workspace_refs=resolved_workspace_refs,
        tags=tags,
        note=note,
    )
    updates = {payload["id"]: payload}
    for workspace_ref in resolved_workspace_refs:
        workspace = records.get(workspace_ref)
        if not workspace or workspace.get("record_type") != "workspace":
            print(f"{workspace_ref} must reference a workspace record")
            return 1
        workspace_payload = public_record_payload(workspace)
        workspace_payload["project_refs"] = sorted({*workspace_payload.get("project_refs", []), payload["id"]})
        workspace_payload["updated_at"] = timestamp
        workspace_payload["note"] = append_note(
            str(workspace_payload.get("note", "")),
            f"[{timestamp}] linked project {payload['id']}",
        )
        updates[workspace_ref] = workspace_payload

    if len(updates) == 1:
        return persist_candidate(root, records, payload, "project")
    merged_records, errors = validate_mutated_records(root, records, updates)
    if errors:
        print_errors(errors)
        return 1
    return persist_mutated_records(
        root,
        merged_records,
        list(updates),
        f"Recorded project {payload['id']} and linked {len(resolved_workspace_refs)} workspace(s)",
    )


def cmd_show_project(root: Path, show_all: bool) -> int:
    records, exit_code = load_valid_context_readonly(root)
    if exit_code:
        return exit_code
    projects = [data for data in records.values() if data.get("record_type") == "project"]
    if show_all:
        if not projects:
            print("No project records found.")
            return 0
        for project in sorted(projects, key=lambda item: str(item.get("project_key", ""))):
            print_project_detail(project)
        return 0

    ref = current_project_ref(root)
    if not ref:
        print("No current project.")
        return 0
    project = records.get(ref)
    if not project:
        print(f"Current project ref is missing: {ref}")
        return 1
    print("Current project:")
    print_project_detail(project)
    return 0


def cmd_set_current_project(root: Path, project_ref: str | None, clear: bool) -> int:
    records, exit_code = load_clean_context(root)
    if exit_code:
        return 1
    if clear:
        write_settings(root, current_project_ref=None)
        refresh_generated_outputs(root, records)
        invalidate_hydration_state(root, "cleared current project")
        print("Cleared current project")
        return 0
    if not project_ref:
        print("set-current-project requires --project or --clear")
        return 1
    project = records.get(project_ref)
    if not project or project.get("record_type") != "project":
        print(f"{project_ref} must reference a project record")
        return 1
    write_settings(root, current_project_ref=project_ref)
    refresh_generated_outputs(root, records)
    invalidate_hydration_state(root, f"set current project {project_ref}")
    print(f"Set current project {project_ref}")
    return 0


def cmd_assign_project(root: Path, project_ref: str, record_ref: str, note: str | None) -> int:
    records, exit_code = load_clean_context(root)
    if exit_code:
        return 1
    if project_ref not in records or records[project_ref].get("record_type") != "project":
        print(f"{project_ref} must reference a project record")
        return 1
    if record_ref not in records:
        print(f"missing record {record_ref}")
        return 1
    if records[record_ref].get("record_type") == "project":
        print("assign-project target must not be a project record")
        return 1

    timestamp = now_timestamp()
    payload = assign_project_payload(public_record_payload(records[record_ref]), timestamp, project_ref, note)

    merged_records, errors = validate_mutated_records(root, records, {record_ref: payload})
    if errors:
        print_errors(errors)
        return 1
    return persist_mutated_records(root, merged_records, [record_ref], f"Assigned {record_ref} to project {project_ref}")


def cmd_assign_task(root: Path, task_ref: str, record_ref: str, note: str | None) -> int:
    records, exit_code = load_clean_context(root)
    if exit_code:
        return 1
    if task_ref not in records or records[task_ref].get("record_type") != "task":
        print(f"{task_ref} must reference a task record")
        return 1
    if record_ref not in records:
        print(f"missing record {record_ref}")
        return 1
    if records[record_ref].get("record_type") == "task":
        print("assign-task target must not be a task record")
        return 1

    timestamp = now_timestamp()
    payload = assign_task_payload(public_record_payload(records[record_ref]), timestamp, task_ref, note)

    merged_records, errors = validate_mutated_records(root, records, {record_ref: payload})
    if errors:
        print_errors(errors)
        return 1
    return persist_mutated_records(root, merged_records, [record_ref], f"Assigned {record_ref} to task {task_ref}")


def cmd_record_restriction(
    root: Path,
    scope: str,
    title: str,
    applies_to: str,
    severity: str,
    rules: list[str],
    project_refs: list[str],
    task_refs: list[str],
    related_claim_refs: list[str],
    supersedes_refs: list[str],
    imposed_by: str,
    imposed_at: str | None,
    tags: list[str],
    note: str,
) -> int:
    records, exit_code = load_clean_context(root)
    if exit_code:
        return 1

    timestamp = now_timestamp()
    resolved_project_refs, resolved_task_refs = resolve_restriction_scope(
        applies_to=applies_to,
        project_refs=project_refs,
        task_refs=task_refs,
        current_project=current_project_ref(root),
        current_task=current_task_ref(root),
    )
    payload = build_restriction_payload(
        record_id=next_record_id(records, "RST-"),
        timestamp=timestamp,
        scope=scope,
        title=title,
        applies_to=applies_to,
        severity=severity,
        rules=rules,
        project_refs=resolved_project_refs,
        task_refs=resolved_task_refs,
        related_claim_refs=related_claim_refs,
        supersedes_refs=supersedes_refs,
        imposed_by=imposed_by,
        imposed_at=imposed_at,
        tags=tags,
        note=note,
    )
    return persist_candidate(root, records, payload, "restriction")


def cmd_show_restrictions(root: Path, show_all: bool) -> int:
    records, exit_code = load_valid_context_readonly(root)
    if exit_code:
        return exit_code
    if show_all:
        restrictions = [data for data in records.values() if data.get("record_type") == "restriction"]
    else:
        restrictions = active_restrictions_for(records, current_project_ref(root), current_task_ref(root))
    if not restrictions:
        print("No restrictions found." if show_all else "No active restrictions for current project/task.")
        return 0
    for restriction in restrictions:
        print_restriction_detail(restriction)
    return 0


def cmd_record_guideline(
    root: Path,
    scope: str,
    domain: str,
    applies_to: str,
    priority: str,
    rule: str,
    source_refs: list[str],
    project_refs: list[str],
    task_refs: list[str],
    related_claim_refs: list[str],
    conflict_refs: list[str],
    supersedes_refs: list[str],
    examples: list[str],
    rationale: str | None,
    tags: list[str],
    note: str,
) -> int:
    records, exit_code = load_clean_context(root)
    if exit_code:
        return 1

    timestamp = now_timestamp()
    resolved_project_refs, resolved_task_refs = resolve_guideline_scope(
        applies_to=applies_to,
        project_refs=project_refs,
        task_refs=task_refs,
        current_project=current_project_ref(root),
        current_task=current_task_ref(root),
    )

    payload = build_guideline_payload(
        record_id=next_record_id(records, "GLD-"),
        timestamp=timestamp,
        scope=scope,
        domain=domain,
        applies_to=applies_to,
        priority=priority,
        rule=rule,
        source_refs=source_refs,
        project_refs=resolved_project_refs,
        task_refs=resolved_task_refs,
        related_claim_refs=related_claim_refs,
        conflict_refs=conflict_refs,
        supersedes_refs=supersedes_refs,
        examples=examples,
        rationale=rationale,
        tags=tags,
        note=note,
    )
    return persist_candidate(root, records, payload, "guideline")


def cmd_record_proposal(
    root: Path,
    scope: str,
    status: str,
    subject: str,
    position: str,
    proposal_options: list[str],
    claim_refs: list[str],
    guideline_refs: list[str],
    model_refs: list[str],
    flow_refs: list[str],
    open_question_refs: list[str],
    assumptions: list[str],
    concerns: list[str],
    risks: list[str],
    stop_conditions: list[str],
    confidence: str,
    created_by: str,
    project_refs: list[str],
    task_refs: list[str],
    supersedes_refs: list[str],
    tags: list[str],
    note: str,
) -> int:
    records, exit_code = load_clean_context(root)
    if exit_code:
        return 1
    try:
        proposals = [parse_proposal_option(raw) for raw in proposal_options]
    except ValueError as exc:
        print(exc)
        return 1
    if proposals and not any(option.get("recommended") is True for option in proposals):
        proposals[0]["recommended"] = True

    timestamp = now_timestamp()
    payload = build_proposal_payload(
        record_id=next_record_id(records, "PRP-"),
        timestamp=timestamp,
        scope=scope,
        status=status,
        subject=subject,
        position=position,
        claim_refs=claim_refs,
        guideline_refs=guideline_refs,
        model_refs=model_refs,
        flow_refs=flow_refs,
        open_question_refs=open_question_refs,
        assumptions=assumptions,
        concerns=concerns,
        proposals=proposals,
        risks=risks,
        stop_conditions=stop_conditions,
        confidence=confidence,
        created_by=created_by,
        project_refs=project_refs_for_write(root, project_refs),
        task_refs=task_refs_for_write(root, task_refs),
        supersedes_refs=supersedes_refs,
        tags=tags,
        note=note,
    )
    return persist_candidate(root, records, payload, "proposal")


def cmd_show_guidelines(root: Path, show_all: bool, domain: str | None) -> int:
    records, exit_code = load_valid_context_readonly(root)
    if exit_code:
        return exit_code
    if show_all:
        guidelines = [data for data in records.values() if data.get("record_type") == "guideline"]
    else:
        guidelines = active_guidelines_for(records, set(), current_project_ref(root), current_task_ref(root), limit=200)
    if domain:
        guidelines = [item for item in guidelines if str(item.get("domain", "")).strip() == domain]
    if not guidelines:
        print("No guidelines found." if show_all else "No active guidelines for current project/task.")
        return 0
    for guideline in guidelines:
        print_guideline_detail(guideline)
    return 0


def print_task_detail(task: dict) -> None:
    for line in task_detail_lines(task):
        print(line)


def cmd_start_task(
    root: Path,
    scope: str,
    title: str,
    task_type: str,
    execution_mode: str,
    description: str | None,
    related_claim_refs: list[str],
    related_model_refs: list[str],
    related_flow_refs: list[str],
    open_question_refs: list[str],
    plan_refs: list[str],
    debt_refs: list[str],
    action_refs: list[str],
    project_refs: list[str],
    tags: list[str],
    note: str,
) -> int:
    records, exit_code = load_clean_context(root)
    if exit_code:
        return 1

    current_ref = current_task_ref(root)
    current = records.get(current_ref)
    if current_ref and current and str(current.get("status", "")).strip() == "active":
        print(f"current task already active: {current_ref}; pause-task, complete-task, or stop-task before starting a new task")
        return 1

    timestamp = now_timestamp()
    payload = build_task_payload(
        record_id=next_record_id(records, "TASK-"),
        timestamp=timestamp,
        scope=scope,
        title=title,
        task_type=task_type,
        execution_mode=execution_mode,
        description=description,
        related_claim_refs=related_claim_refs,
        related_model_refs=related_model_refs,
        related_flow_refs=related_flow_refs,
        open_question_refs=open_question_refs,
        plan_refs=plan_refs,
        debt_refs=debt_refs,
        action_refs=action_refs,
        project_refs=project_refs_for_write(root, project_refs),
        tags=tags,
        note=note,
    )
    candidate, candidate_errors = validate_candidate_record(root, records, payload)
    if candidate_errors:
        print_errors(candidate_errors)
        return 1

    write_json_file(record_path(root, "task", payload["id"]), payload)
    updated_records = dict(records)
    updated_records[payload["id"]] = candidate
    write_settings(root, current_task_ref=payload["id"])
    write_validation_report(root, [])
    refresh_generated_outputs(root, updated_records)
    invalidate_hydration_state(root, f"started task {payload['id']}")
    print(f"Started task {payload['id']}: {payload['title']}")
    return 0


def cmd_show_task(root: Path, show_all: bool) -> int:
    records, exit_code = load_valid_context_readonly(root)
    if exit_code:
        return exit_code
    tasks = [data for data in records.values() if data.get("record_type") == "task"]
    if show_all:
        if not tasks:
            print("No task records found.")
            return 0
        for task in sorted(tasks, key=lambda item: str(item.get("updated_at", "")), reverse=True):
            print_task_detail(task)
        return 0

    ref = current_task_ref(root)
    if not ref:
        print("No current task.")
        return 0
    task = records.get(ref)
    if not task:
        print(f"Current task ref is missing: {ref}")
        return 1
    print("Current task:")
    print_task_detail(task)
    return 0


def cmd_validate_task_decomposition(root: Path, task_ref: str, output_format: str) -> int:
    records, exit_code = load_valid_context_readonly(root)
    if exit_code:
        return exit_code
    payload = validate_task_decomposition_payload(records, task_ref)
    if output_format == "json":
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        print("\n".join(task_decomposition_text_lines(payload)))
    return 0 if payload.get("accepted") else 1


def cmd_confirm_atomic_task(
    root: Path,
    task_ref: str,
    deliverable: str,
    done_criteria: list[str],
    verification: list[str],
    scope_boundary: str,
    blocker_policy: str,
    no_verification_needed: str | None,
    note: str | None,
) -> int:
    records, exit_code = load_clean_context(root)
    if exit_code:
        return 1
    task = records.get(task_ref)
    if not task or task.get("record_type") != "task":
        print(f"missing task record {task_ref}")
        return 1
    timestamp = now_timestamp()
    payload = apply_atomic_task_decomposition(
        public_record_payload(task),
        timestamp=timestamp,
        deliverable=deliverable,
        done_criteria=done_criteria,
        verification=verification,
        scope_boundary=scope_boundary,
        blocker_policy=blocker_policy,
        no_verification_needed=no_verification_needed,
        note=note,
    )
    merged_records, errors = validate_mutated_records(root, records, {task_ref: payload})
    if errors:
        print_errors(errors)
        return 1
    return persist_mutated_records(root, merged_records, [task_ref], f"Confirmed atomic task {task_ref}")


def parse_subtask_spec(spec: str) -> dict:
    parts = [part.strip() for part in spec.split("|")]
    if len(parts) < 6:
        raise ValueError("subtask must be shaped as scope|title|deliverable|done|verify|boundary[|blocker_policy]")
    scope, title, deliverable, done, verify, boundary = parts[:6]
    blocker_policy = parts[6] if len(parts) > 6 else "Record OPEN-* for blockers or user decisions."
    if not all((scope, title, deliverable, done, boundary)):
        raise ValueError("subtask scope, title, deliverable, done, and boundary must be non-empty")
    return {
        "scope": scope,
        "title": title,
        "deliverable": deliverable,
        "done_criteria": [done],
        "verification": [verify] if verify else [],
        "scope_boundary": boundary,
        "blocker_policy": blocker_policy,
    }


def cmd_decompose_task(root: Path, task_ref: str, subtask_specs: list[str], note: str | None) -> int:
    records, exit_code = load_clean_context(root)
    if exit_code:
        return 1
    parent = records.get(task_ref)
    if not parent or parent.get("record_type") != "task":
        print(f"missing task record {task_ref}")
        return 1
    specs: list[dict] = []
    for spec in subtask_specs:
        try:
            specs.append(parse_subtask_spec(spec))
        except ValueError as exc:
            print(exc)
            return 1
    timestamp = now_timestamp()
    updates: dict[str, dict] = {}
    child_refs: list[str] = []
    id_pool = dict(records)
    for spec in specs:
        child_id = next_record_id(id_pool, "TASK-")
        id_pool[child_id] = {"id": child_id}
        child_refs.append(child_id)
        updates[child_id] = build_task_payload(
            record_id=child_id,
            timestamp=timestamp,
            scope=spec["scope"],
            title=spec["title"],
            task_type=str(parent.get("task_type", "general")).strip() or "general",
            execution_mode=str(parent.get("execution_mode", "manual")).strip() or "manual",
            description=f"Subtask of {task_ref}",
            related_claim_refs=safe_list(parent, "related_claim_refs"),
            related_model_refs=safe_list(parent, "related_model_refs"),
            related_flow_refs=safe_list(parent, "related_flow_refs"),
            open_question_refs=[],
            plan_refs=[],
            debt_refs=[],
            action_refs=[],
            project_refs=safe_list(parent, "project_refs"),
            tags=safe_list(parent, "tags"),
            note=f"Subtask of {task_ref}",
            parent_task_refs=[task_ref],
            decomposition={
                "status": "atomic",
                "one_pass": True,
                "deliverable": spec["deliverable"],
                "done_criteria": spec["done_criteria"],
                "verification": spec["verification"],
                "scope_boundary": spec["scope_boundary"],
                "blocker_policy": spec["blocker_policy"],
            },
        )
    existing_children = safe_list(parent.get("decomposition", {}), "subtask_refs") if isinstance(parent.get("decomposition"), dict) else []
    parent_payload = apply_decomposed_task_decomposition(
        public_record_payload(parent),
        timestamp=timestamp,
        subtask_refs=[*existing_children, *child_refs],
        note=note,
    )
    updates[task_ref] = parent_payload
    merged_records, errors = validate_mutated_records(root, records, updates)
    if errors:
        print_errors(errors)
        return 1
    return persist_mutated_records(root, merged_records, [*child_refs, task_ref], f"Decomposed task {task_ref}; Started task {child_refs[0]}: {updates[child_refs[0]]['title']}")


def cmd_validate_plan_decomposition(root: Path, plan_ref: str, output_format: str) -> int:
    records, exit_code = load_valid_context_readonly(root)
    if exit_code:
        return exit_code
    payload = validate_plan_decomposition_payload(records, plan_ref)
    if output_format == "json":
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        print("\n".join(plan_decomposition_text_lines(payload)))
    return 0 if payload.get("accepted") else 1


def cmd_confirm_atomic_plan(root: Path, plan_ref: str, task_ref: str | None, note: str | None) -> int:
    records, exit_code = load_clean_context(root)
    if exit_code:
        return 1
    plan = records.get(plan_ref)
    if not plan or plan.get("record_type") != "plan":
        print(f"missing plan record {plan_ref}")
        return 1
    timestamp = now_timestamp()
    payload = apply_atomic_plan_decomposition(
        public_record_payload(plan),
        timestamp=timestamp,
        task_ref=task_ref,
        note=note,
    )
    merged_records, errors = validate_mutated_records(root, records, {plan_ref: payload})
    if errors:
        print_errors(errors)
        return 1
    return persist_mutated_records(root, merged_records, [plan_ref], f"Confirmed atomic plan {plan_ref}")


def parse_subplan_spec(spec: str) -> dict:
    parts = [part.strip() for part in spec.split("|")]
    if len(parts) < 5:
        raise ValueError("subplan must be shaped as scope|title|step|success|justified_by[,justified_by...]")
    scope, title, step, success, justified = parts[:5]
    if not all((scope, title, step, success, justified)):
        raise ValueError("subplan scope, title, step, success, and justified_by must be non-empty")
    return {
        "scope": scope,
        "title": title,
        "steps": [step],
        "success_criteria": [success],
        "justified_by": parse_csv_refs(justified),
    }


def cmd_decompose_plan(root: Path, plan_ref: str, subplan_specs: list[str], note: str | None) -> int:
    records, exit_code = load_clean_context(root)
    if exit_code:
        return 1
    parent = records.get(plan_ref)
    if not parent or parent.get("record_type") != "plan":
        print(f"missing plan record {plan_ref}")
        return 1
    specs: list[dict] = []
    for spec in subplan_specs:
        try:
            specs.append(parse_subplan_spec(spec))
        except ValueError as exc:
            print(exc)
            return 1
    timestamp = now_timestamp()
    updates: dict[str, dict] = {}
    child_refs: list[str] = []
    id_pool = dict(records)
    for spec in specs:
        child_id = next_record_id(id_pool, "PLN-")
        id_pool[child_id] = {"id": child_id}
        child_refs.append(child_id)
        updates[child_id] = build_plan_payload(
            record_id=child_id,
            timestamp=timestamp,
            scope=spec["scope"],
            title=spec["title"],
            priority=str(parent.get("priority", "medium")).strip() or "medium",
            status="proposed",
            justified_by=spec["justified_by"],
            steps=spec["steps"],
            success_criteria=spec["success_criteria"],
            blocked_by=[],
            project_refs=safe_list(parent, "project_refs"),
            task_refs=safe_list(parent, "task_refs"),
            tags=safe_list(parent, "tags"),
            note=f"Subplan of {plan_ref}",
            decomposition={
                "status": "atomic",
                "one_pass": True,
                "task_ref": "",
            },
            parent_plan_refs=[plan_ref],
        )
    existing_children = safe_list(parent.get("decomposition", {}), "subplan_refs") if isinstance(parent.get("decomposition"), dict) else []
    parent_payload = apply_decomposed_plan_decomposition(
        public_record_payload(parent),
        timestamp=timestamp,
        subplan_refs=[*existing_children, *child_refs],
        task_refs=safe_list(parent, "task_refs"),
        note=note,
    )
    updates[plan_ref] = parent_payload
    merged_records, errors = validate_mutated_records(root, records, updates)
    if errors:
        print_errors(errors)
        return 1
    return persist_mutated_records(root, merged_records, [*child_refs, plan_ref], f"Decomposed plan {plan_ref}; Recorded plan {child_refs[0]} at {record_path(root, 'plan', child_refs[0])}")


def cmd_finish_task(root: Path, task_ref: str | None, final_status: str, note: str | None) -> int:
    records, exit_code = load_clean_context(root)
    if exit_code:
        return 1
    target_ref = (task_ref or current_task_ref(root)).strip()
    if not target_ref:
        print("No current task. Pass --task TASK-* to finish a specific task.")
        return 1
    if target_ref not in records:
        print(f"missing task record {target_ref}")
        return 1
    task = records[target_ref]
    if task.get("record_type") != "task":
        print(f"{target_ref} must reference a task record")
        return 1
    if str(task.get("status", "")).strip() != "active":
        print(f"{target_ref} is not active; current status is {task.get('status', '')}")
        return 1
    if str(task.get("execution_mode", "manual")).strip() == "autonomous" and final_status == "completed":
        outcome_payload = task_outcome_check_payload(records, target_ref, "done")
        if not outcome_payload.get("accepted"):
            print("\n".join(task_outcome_check_text_lines(outcome_payload)))
            print("Autonomous task cannot be completed until task-outcome-check accepts outcome=done.")
            return 1

    timestamp = now_timestamp()
    payload = finish_task_payload(public_record_payload(task), timestamp, final_status, note)

    merged_records, errors = validate_mutated_records(root, records, {target_ref: payload})
    if errors:
        print_errors(errors)
        return 1

    write_json_file(record_path(root, "task", target_ref), payload)
    if current_task_ref(root) == target_ref:
        write_settings(root, current_task_ref=None)
    write_validation_report(root, [])
    refresh_generated_outputs(root, merged_records)
    invalidate_hydration_state(root, f"{final_status} task {target_ref}")
    print(f"{final_status.capitalize()} task {target_ref}")
    return 0


def cmd_task_outcome_check(root: Path, task_ref: str | None, outcome: str, output_format: str) -> int:
    records, exit_code = load_valid_context_readonly(root)
    if exit_code:
        return exit_code
    target_ref = (task_ref or current_task_ref(root)).strip()
    if not target_ref:
        print("No current task. Pass --task TASK-* to check a specific task.")
        return 1
    payload = task_outcome_check_payload(records, target_ref, outcome)
    if output_format == "json":
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        print("\n".join(task_outcome_check_text_lines(payload)))
    return 0 if payload.get("accepted") else 1


def cmd_resume_task(root: Path, task_ref: str, note: str | None) -> int:
    records, exit_code = load_clean_context(root)
    if exit_code:
        return 1
    current_ref = current_task_ref(root)
    current = records.get(current_ref)
    if current_ref and current_ref != task_ref and current and str(current.get("status", "")).strip() == "active":
        print(f"current task already active: {current_ref}; use switch-task or pause-task first")
        return 1
    task = records.get(task_ref)
    if not task or task.get("record_type") != "task":
        print(f"missing task record {task_ref}")
        return 1
    if str(task.get("status", "")).strip() != "paused":
        print(f"{task_ref} is not paused; current status is {task.get('status', '')}")
        return 1

    timestamp = now_timestamp()
    payload = resume_task_payload(public_record_payload(task), timestamp, note)

    merged_records, errors = validate_mutated_records(root, records, {task_ref: payload})
    if errors:
        print_errors(errors)
        return 1
    write_json_file(record_path(root, "task", task_ref), payload)
    write_settings(root, current_task_ref=task_ref)
    write_validation_report(root, [])
    refresh_generated_outputs(root, merged_records)
    invalidate_hydration_state(root, f"resumed task {task_ref}")
    print(f"Resumed task {task_ref}")
    return 0


def cmd_switch_task(root: Path, task_ref: str, note: str | None) -> int:
    records, exit_code = load_clean_context(root)
    if exit_code:
        return 1
    target = records.get(task_ref)
    if not target or target.get("record_type") != "task":
        print(f"missing task record {task_ref}")
        return 1
    target_status = str(target.get("status", "")).strip()
    if target_status in {"completed", "stopped"}:
        print(f"{task_ref} is terminal; current status is {target_status}")
        return 1

    timestamp = now_timestamp()
    mutations: dict[str, dict] = {}
    current_ref = current_task_ref(root)
    if current_ref and current_ref != task_ref:
        current = records.get(current_ref)
        if current and current.get("record_type") == "task" and str(current.get("status", "")).strip() == "active":
            current_payload = pause_task_for_switch_payload(public_record_payload(current), timestamp, task_ref, note)
            mutations[current_ref] = current_payload

    target_payload = resume_task_payload(public_record_payload(target), timestamp, note)
    mutations[task_ref] = target_payload

    merged_records, errors = validate_mutated_records(root, records, mutations)
    if errors:
        print_errors(errors)
        return 1
    for ref, payload in mutations.items():
        write_json_file(record_path(root, "task", ref), payload)
    write_settings(root, current_task_ref=task_ref)
    write_validation_report(root, [])
    refresh_generated_outputs(root, merged_records)
    invalidate_hydration_state(root, f"switched task to {task_ref}")
    if current_ref and current_ref != task_ref and current_ref in mutations:
        print(f"Paused task {current_ref}")
    print(f"Switched current task to {task_ref}")
    return 0


def print_working_context_detail(context: dict) -> None:
    for line in working_context_detail_lines(context):
        print(line)


def _text_tokens(*values: object) -> set[str]:
    text = " ".join(str(value or "") for value in values)
    return {token for token in re.findall(r"[a-zA-Z0-9_./-]{3,}", text.lower())}


def _working_context_score(context: dict, task_text: str) -> int:
    task_tokens = _text_tokens(task_text)
    context_tokens = _text_tokens(
        context.get("scope", ""),
        context.get("title", ""),
        context.get("note", ""),
        " ".join(str(item) for item in context.get("topic_terms", [])),
        " ".join(str(item) for item in context.get("focus_paths", [])),
        " ".join(str(item) for item in context.get("concerns", [])),
    )
    return len(task_tokens & context_tokens)


def working_context_drift_payload(root: Path, records: dict[str, dict], task_text: str) -> dict:
    project_ref = current_project_ref(root) or None
    task_ref = current_task_ref(root) or None
    contexts = [
        data
        for data in records.values()
        if data.get("record_type") == "working_context"
        and str(data.get("status", "")).strip() == "active"
        and record_belongs_to_project(data, project_ref)
    ]
    scored = sorted(
        (
            {
                "id": context.get("id"),
                "score": _working_context_score(context, task_text),
                "title": context.get("title", ""),
                "scope": context.get("scope", ""),
                "task_refs": context.get("task_refs", []),
                "project_refs": context.get("project_refs", []),
            }
            for context in contexts
        ),
        key=lambda item: (item["score"], item["id"] or ""),
        reverse=True,
    )
    current_candidates = [
        item
        for item in scored
        if not item.get("task_refs") or (task_ref and task_ref in item.get("task_refs", []))
    ]
    best_current = current_candidates[0] if current_candidates else None
    best_any = scored[0] if scored else None
    if best_current and best_current["score"] > 0:
        recommendation = "keep-current-working-context"
        drift_detected = False
    elif best_any and best_any["score"] > 0:
        recommendation = "switch-or-fork-working-context"
        drift_detected = True
    else:
        recommendation = "create-working-context"
        drift_detected = True
    return {
        "working_context_drift_is_proof": False,
        "task_text": task_text,
        "current_workspace_ref": current_workspace_ref(root),
        "current_project_ref": project_ref or "",
        "current_task_ref": task_ref or "",
        "drift_detected": drift_detected,
        "recommendation": recommendation,
        "best_current_context": best_current,
        "best_matching_context": best_any,
        "candidates": scored[:8],
    }


def working_context_drift_text_lines(payload: dict) -> list[str]:
    lines = [
        f"Working-context drift: {'yes' if payload.get('drift_detected') else 'no'}",
        f"Recommendation: {payload.get('recommendation')}",
        f"Current workspace: {payload.get('current_workspace_ref') or '<none>'}",
        f"Current project: {payload.get('current_project_ref') or '<none>'}",
        f"Current task: {payload.get('current_task_ref') or '<none>'}",
    ]
    best = payload.get("best_matching_context") if isinstance(payload.get("best_matching_context"), dict) else None
    if best:
        lines.append(f"Best WCTX: {best.get('id')} score={best.get('score')} title=\"{best.get('title')}\"")
    if payload.get("drift_detected"):
        lines.append("Action: switch/fork an existing WCTX or create a new WCTX before persisting task-specific conclusions.")
    return lines


def cmd_working_context_check_drift(root: Path, task_text: str, output_format: str) -> int:
    records, exit_code = load_valid_context_readonly(root)
    if exit_code:
        return exit_code
    payload = working_context_drift_payload(root, records, task_text)
    if output_format == "json":
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        for line in working_context_drift_text_lines(payload):
            print(line)
    return 0


def persist_working_context_with_task_links(root: Path, records: dict[str, dict], payload: dict, *, quiet: bool = False) -> int:
    if not payload.get("workspace_refs"):
        refs = workspace_refs_for_write(root, [])
        if refs:
            payload = dict(payload)
            payload["workspace_refs"] = refs
    timestamp = now_timestamp()
    mutations: dict[str, dict] = {payload["id"]: payload}
    for task_ref in payload.get("task_refs", []) if isinstance(payload.get("task_refs"), list) else []:
        task = records.get(str(task_ref))
        if not task or task.get("record_type") != "task":
            continue
        task_payload = public_record_payload(task)
        refs = sorted({*task_payload.get("working_context_refs", []), payload["id"]})
        task_payload["working_context_refs"] = refs
        task_payload["updated_at"] = timestamp
        task_payload["note"] = append_note(
            str(task_payload.get("note", "")),
            f"[{timestamp}] linked working_context {payload['id']}",
        )
        mutations[str(task_ref)] = task_payload

    merged, errors = validate_mutated_records(root, records, mutations)
    if errors:
        print_errors(errors)
        return 1

    write_json_file(record_path(root, "working_context", payload["id"]), payload)
    for task_ref, task_payload in mutations.items():
        if task_ref == payload["id"]:
            continue
        write_json_file(record_path(root, "task", task_ref), task_payload)
    write_validation_report(root, [])
    refresh_generated_outputs(root, merged)
    invalidate_hydration_state(root, f"recorded working_context {payload['id']}")
    if not quiet:
        print(f"Recorded working_context {payload['id']} at {record_path(root, 'working_context', payload['id'])}")
    return 0


def cmd_working_context_create(
    root: Path,
    scope: str,
    title: str,
    context_kind: str,
    pinned_refs: list[str],
    focus_paths: list[str],
    topic_terms: list[str],
    topic_seed_refs: list[str],
    assumption_values: list[str],
    concerns: list[str],
    project_refs: list[str],
    task_refs: list[str],
    tags: list[str],
    note: str,
) -> int:
    records, exit_code = load_clean_context(root)
    if exit_code:
        return 1
    try:
        assumptions = parse_working_context_assumptions(assumption_values)
    except ValueError as exc:
        print(exc)
        return 1
    resolved_topic_terms = topic_terms or infer_topic_terms_from_refs(root, records, topic_seed_refs + pinned_refs)
    timestamp = now_timestamp()
    payload = build_working_context_payload(
        record_id=next_record_id(records, "WCTX-"),
        timestamp=timestamp,
        scope=scope,
        title=title,
        context_kind=context_kind,
        pinned_refs=pinned_refs,
        focus_paths=focus_paths,
        topic_terms=resolved_topic_terms,
        topic_seed_refs=topic_seed_refs,
        assumptions=assumptions,
        concerns=concerns,
        project_refs=project_refs_for_write(root, project_refs),
        task_refs=task_refs_for_write(root, task_refs),
        tags=tags,
        note=note,
    )
    return persist_working_context_with_task_links(root, records, payload)


def cmd_working_context_show(root: Path, context_ref: str | None, show_all: bool, output_format: str) -> int:
    records, exit_code = load_valid_context_readonly(root)
    if exit_code:
        return exit_code
    if context_ref:
        contexts = [records[context_ref]] if context_ref in records else []
        if not contexts or contexts[0].get("record_type") != "working_context":
            print(f"missing working_context record {context_ref}")
            return 1
    else:
        contexts = [data for data in records.values() if data.get("record_type") == "working_context"]
        if not show_all:
            project_ref = current_project_ref(root) or None
            task_ref = current_task_ref(root) or None
            contexts = [
                data
                for data in contexts
                if str(data.get("status", "")).strip() == "active"
                and record_belongs_to_project(data, project_ref)
                and record_belongs_to_task(data, task_ref)
            ]
    contexts = sorted(contexts, key=lambda item: str(item.get("updated_at", "")), reverse=True)
    if output_format == "json":
        print(json.dumps(working_context_show_payload([public_record_payload(context) for context in contexts]), indent=2, ensure_ascii=False))
        return 0
    if not contexts:
        print("No working contexts found.")
        return 0
    for context in contexts:
        print_working_context_detail(context)
    return 0


def cmd_working_context_fork(
    root: Path,
    context_ref: str,
    title: str | None,
    context_kind: str | None,
    add_pinned_refs: list[str],
    remove_pinned_refs: list[str],
    add_focus_paths: list[str],
    remove_focus_paths: list[str],
    add_topic_terms: list[str],
    remove_topic_terms: list[str],
    add_topic_seed_refs: list[str],
    remove_topic_seed_refs: list[str],
    add_assumption_values: list[str],
    add_concerns: list[str],
    project_refs: list[str],
    task_refs: list[str],
    tags: list[str],
    note: str,
) -> int:
    records, exit_code = load_clean_context(root)
    if exit_code:
        return 1
    source = records.get(context_ref)
    if not source or source.get("record_type") != "working_context":
        print(f"missing working_context record {context_ref}")
        return 1
    try:
        added_assumptions = parse_working_context_assumptions(add_assumption_values)
    except ValueError as exc:
        print(exc)
        return 1

    timestamp = now_timestamp()
    source_payload = public_record_payload(source)
    provisional_topic_terms = add_remove_values(source_payload.get("topic_terms", []), add_topic_terms, remove_topic_terms)
    provisional_topic_seed_refs = add_remove_values(source_payload.get("topic_seed_refs", []), add_topic_seed_refs, remove_topic_seed_refs)
    provisional_pinned_refs = add_remove_values(source_payload.get("pinned_refs", []), add_pinned_refs, remove_pinned_refs)
    inferred_topic_terms = (
        []
        if provisional_topic_terms
        else infer_topic_terms_from_refs(root, records, provisional_topic_seed_refs + provisional_pinned_refs)
    )
    payload = fork_working_context_payload(
        source_payload=source_payload,
        record_id=next_record_id(records, "WCTX-"),
        timestamp=timestamp,
        context_ref=context_ref,
        title=title,
        context_kind=context_kind,
        add_pinned_refs=add_pinned_refs,
        remove_pinned_refs=remove_pinned_refs,
        add_focus_paths=add_focus_paths,
        remove_focus_paths=remove_focus_paths,
        add_topic_terms=add_topic_terms,
        remove_topic_terms=remove_topic_terms,
        add_topic_seed_refs=add_topic_seed_refs,
        remove_topic_seed_refs=remove_topic_seed_refs,
        added_assumptions=added_assumptions,
        add_concerns=add_concerns,
        inferred_topic_terms=inferred_topic_terms,
        project_refs=project_refs_for_write(root, project_refs) if project_refs else [],
        task_refs=task_refs_for_write(root, task_refs) if task_refs else [],
        tags=tags,
        note=note,
    )
    return persist_working_context_with_task_links(root, records, payload)


def cmd_working_context_close(root: Path, context_ref: str, status: str, note: str | None) -> int:
    records, exit_code = load_clean_context(root)
    if exit_code:
        return 1
    context = records.get(context_ref)
    if not context or context.get("record_type") != "working_context":
        print(f"missing working_context record {context_ref}")
        return 1
    if str(context.get("status", "")).strip() not in {"active", "superseded"}:
        print(f"{context_ref} is not active/superseded; current status is {context.get('status', '')}")
        return 1
    timestamp = now_timestamp()
    payload = close_working_context_payload(public_record_payload(context), timestamp, status, note)
    merged_records, errors = validate_mutated_records(root, records, {context_ref: payload})
    if errors:
        print_errors(errors)
        return 1
    return persist_mutated_records(root, merged_records, [context_ref], f"Closed working_context {context_ref} as {status}")


def cmd_validate_evidence_chain(root: Path, chain_file: Path) -> int:
    records, exit_code = load_valid_context_readonly(root)
    if exit_code:
        return exit_code
    try:
        payload = json.loads(chain_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"{chain_file}: {exc}")
        return 1
    hypothesis_entries = active_hypothesis_entry_by_claim(root, records)
    validation = validate_evidence_chain_payload(records, hypothesis_entries, payload)
    for line in evidence_chain_report_lines(validation, payload, TEP_ICON):
        print(line)
    return 1 if validation.errors else 0


def cmd_validate_decision(
    root: Path,
    mode: str,
    chain_file: Path,
    output_format: str,
    emit_permit: bool,
    action_kind: str | None,
    ttl_seconds: int,
) -> int:
    records, exit_code = load_valid_context_readonly(root)
    if exit_code:
        return exit_code
    try:
        payload = json.loads(chain_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"{chain_file}: {exc}")
        return 1
    hypothesis_entries = active_hypothesis_entry_by_claim(root, records)
    decision = decision_validation_payload(records, hypothesis_entries, payload, mode)
    if emit_permit:
        permit, error = create_chain_permit(
            root,
            payload,
            decision,
            mode=mode,
            action_kind=action_kind,
            ttl_seconds=ttl_seconds,
        )
        if error:
            decision = dict(decision)
            decision.setdefault("blockers", []).append(error)
            decision["decision_valid"] = False
        elif permit:
            decision = dict(decision)
            decision["permit"] = permit
    if output_format == "json":
        print(json.dumps(decision, indent=2, ensure_ascii=False))
    else:
        lines = decision_validation_text_lines(decision, TEP_ICON)
        if decision.get("permit"):
            lines.extend(["", *chain_permit_text_lines(decision["permit"])])
        print("\n".join(lines))
    return 0 if decision["decision_valid"] else 1


def cmd_augment_chain(root: Path, chain_file: Path, output_format: str) -> int:
    records, exit_code = load_valid_context_readonly(root)
    if exit_code:
        return exit_code
    try:
        payload = json.loads(chain_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"{chain_file}: {exc}")
        return 1
    hypothesis_entries = active_hypothesis_entry_by_claim(root, records)
    augmented = augment_evidence_chain_payload(records, hypothesis_entries, payload)
    if output_format == "json":
        print(json.dumps(augmented, indent=2, ensure_ascii=False))
    else:
        print("\n".join(augmented_evidence_chain_text_lines(augmented, TEP_ICON)))
    return 1 if augmented["validation"]["error_count"] else 0


def cmd_brief_context(root: Path, task: str, limit: int, detail: str) -> int:
    records, exit_code = load_valid_context_readonly(root)
    if exit_code:
        return exit_code
    payload = build_context_brief_payload(
        records,
        root,
        task,
        current_task_ref(root),
        current_workspace_ref(root),
        current_project_ref(root),
        limit,
    )
    for line in context_brief_text_lines(payload, TEP_ICON, detail=detail):
        print(line)
    return 0


def cmd_next_step(root: Path, intent: str, task: str, detail: str, output_format: str) -> int:
    records, exit_code = load_valid_context_readonly(root)
    if exit_code:
        return exit_code
    payload = build_next_step_payload(records, root, intent=intent, task=task)
    if output_format == "json":
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0
    for line in next_step_text_lines(payload, TEP_ICON, detail=detail):
        print(line)
    return 0


ANALYSIS_SETTING_SPECS = {
    "logic_solver.enabled": ("bool", None),
    "logic_solver.backend": ("choice", LOGIC_SOLVER_BACKENDS),
    "logic_solver.optional_backends": ("list", LOGIC_SOLVER_OPTIONAL_BACKENDS),
    "logic_solver.missing_dependency": ("choice", ANALYSIS_MISSING_DEPENDENCY_POLICIES),
    "logic_solver.install_policy": ("choice", ANALYSIS_INSTALL_POLICIES),
    "logic_solver.mode": ("choice", LOGIC_SOLVER_MODES),
    "logic_solver.timeout_ms": ("int", (100, 60000)),
    "logic_solver.max_symbols": ("int", (1, 100000)),
    "logic_solver.max_rules": ("int", (0, 100000)),
    "logic_solver.use_unsat_core": ("bool", None),
    "topic_prefilter.enabled": ("bool", None),
    "topic_prefilter.backend": ("choice", TOPIC_PREFILTER_BACKENDS),
    "topic_prefilter.optional_backends": ("list", TOPIC_PREFILTER_OPTIONAL_BACKENDS),
    "topic_prefilter.missing_dependency": ("choice", ANALYSIS_MISSING_DEPENDENCY_POLICIES),
    "topic_prefilter.install_policy": ("choice", ANALYSIS_INSTALL_POLICIES),
    "topic_prefilter.rebuild": ("choice", TOPIC_PREFILTER_REBUILD_MODES),
    "topic_prefilter.max_records": ("int", (1, 1000000)),
}

INPUT_CAPTURE_SETTING_SPECS = {
    "user_prompts": ("choice", INPUT_CAPTURE_MODES),
    "file_mentions": ("choice", INPUT_FILE_MENTION_MODES),
    "session_linking": ("bool", None),
}


def parse_bool_setting(value: str) -> bool | None:
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    return None


def apply_input_capture_setting_items(input_capture: dict, items: list[str]) -> tuple[bool, str | None]:
    changed = False
    for item in items:
        if "=" not in item:
            return changed, f"input capture setting must be key=value: {item}"
        key, raw_value = [part.strip() for part in item.split("=", 1)]
        spec = INPUT_CAPTURE_SETTING_SPECS.get(key)
        if not spec:
            return changed, f"unknown input_capture setting: {key}"
        kind, allowed = spec
        if kind == "bool":
            parsed_bool = parse_bool_setting(raw_value)
            if parsed_bool is None:
                return changed, f"invalid boolean for input_capture.{key}: {raw_value}"
            input_capture[key] = parsed_bool
        elif kind == "choice":
            if raw_value not in allowed:
                return changed, f"invalid value for input_capture.{key}: {raw_value}"
            input_capture[key] = raw_value
        else:
            return changed, f"unsupported input_capture setting type for {key}"
        changed = True
    return changed, None


def parse_analysis_setting(key: str, value: str) -> tuple[object | None, str | None]:
    spec = ANALYSIS_SETTING_SPECS.get(key)
    if not spec:
        return None, f"unknown analysis setting: {key}"
    kind, allowed = spec
    if kind == "bool":
        parsed_bool = parse_bool_setting(value)
        if parsed_bool is None:
            return None, f"invalid boolean for analysis.{key}: {value}"
        return parsed_bool, None
    if kind == "choice":
        if value not in allowed:
            return None, f"invalid value for analysis.{key}: {value}"
        return value, None
    if kind == "list":
        values = [item.strip() for item in value.split(",") if item.strip()]
        invalid = [item for item in values if item not in allowed]
        if invalid:
            return None, f"invalid value for analysis.{key}: {','.join(invalid)}"
        deduped: list[str] = []
        for item in values:
            if item not in deduped:
                deduped.append(item)
        return deduped, None
    if kind == "int":
        try:
            parsed_int = int(value)
        except ValueError:
            return None, f"invalid integer for analysis.{key}: {value}"
        minimum, maximum = allowed
        if parsed_int < minimum or parsed_int > maximum:
            return None, f"analysis.{key} must be between {minimum} and {maximum}"
        return parsed_int, None
    return None, f"unsupported analysis setting type for {key}"


def apply_analysis_setting_items(analysis: dict, items: list[str]) -> tuple[bool, str | None]:
    changed = False
    for item in items:
        if "=" not in item:
            return changed, f"analysis setting must be key=value: {item}"
        key, raw_value = [part.strip() for part in item.split("=", 1)]
        if "." not in key:
            return changed, f"analysis setting must be section.key=value: {item}"
        section, name = key.split(".", 1)
        if section not in {"logic_solver", "topic_prefilter"}:
            return changed, f"unknown analysis setting section: {section}"
        parsed, error = parse_analysis_setting(key, raw_value)
        if error:
            return changed, error
        analysis.setdefault(section, {})[name] = parsed
        changed = True
    return changed, None


def parse_backend_setting(key: str, value: str) -> tuple[object | None, str | None]:
    parsed_bool = parse_bool_setting(value)
    if parsed_bool is not None:
        return parsed_bool, None
    if key.endswith(".max_results"):
        try:
            return int(value), None
        except ValueError:
            return None, f"invalid integer for backends.{key}: {value}"
    return value.strip(), None


def apply_backend_setting_items(backends: dict, items: list[str]) -> tuple[bool, str | None]:
    changed = False
    for item in items:
        if "=" not in item:
            return changed, f"backend setting must be key=value: {item}"
        key, raw_value = [part.strip() for part in item.split("=", 1)]
        parts = key.split(".")
        if len(parts) < 2:
            return changed, f"backend setting must be section.key=value: {item}"
        section = parts[0]
        if section not in {"fact_validation", "code_intelligence", "derivation"}:
            return changed, f"unknown backend setting section: {section}"
        parsed, error = parse_backend_setting(key, raw_value)
        if error:
            return changed, error

        if section == "fact_validation":
            if parts == ["fact_validation", "backend"]:
                if parsed not in FACT_VALIDATION_BACKENDS:
                    return changed, "backends.fact_validation.backend has invalid value"
                backends.setdefault(section, {})["backend"] = parsed
            elif len(parts) == 3 and parts[1] == "rdf_shacl":
                if parts[2] == "enabled" and not isinstance(parsed, bool):
                    return changed, "backends.fact_validation.rdf_shacl.enabled must be boolean"
                if parts[2] == "mode" and parsed not in BACKEND_MODES:
                    return changed, "backends.fact_validation.rdf_shacl.mode has invalid value"
                if parts[2] == "strict" and not isinstance(parsed, bool):
                    return changed, "backends.fact_validation.rdf_shacl.strict must be boolean"
                if parts[2] not in {"enabled", "mode", "strict"}:
                    return changed, f"unknown backend setting key: {key}"
                backends.setdefault(section, {}).setdefault("rdf_shacl", {})[parts[2]] = parsed
            else:
                return changed, f"unknown backend setting key: {key}"
        elif section == "code_intelligence":
            if parts == ["code_intelligence", "backend"]:
                if parsed not in CODE_INTELLIGENCE_BACKENDS:
                    return changed, "backends.code_intelligence.backend has invalid value"
                backends.setdefault(section, {})["backend"] = parsed
            elif len(parts) == 3 and parts[1] in {"serena", "cocoindex"}:
                if parts[2] == "enabled" and not isinstance(parsed, bool):
                    return changed, f"backends.code_intelligence.{parts[1]}.enabled must be boolean"
                if parts[2] == "mode" and parsed not in BACKEND_MODES:
                    return changed, f"backends.code_intelligence.{parts[1]}.mode has invalid value"
                if parts[2] == "max_results" and (isinstance(parsed, bool) or not isinstance(parsed, int)):
                    return changed, f"backends.code_intelligence.{parts[1]}.max_results has invalid value"
                if parts[2] == "max_results" and not 1 <= parsed <= 100:
                    return changed, f"backends.code_intelligence.{parts[1]}.max_results has invalid value"
                if parts[2] == "import_into_cix" and (parts[1] != "cocoindex" or not isinstance(parsed, bool)):
                    return changed, "backends.code_intelligence.cocoindex.import_into_cix must be boolean"
                if parts[2] in {"default_scope", "storage_root", "workspace_glance"} and parts[1] != "cocoindex":
                    return changed, f"unknown backend setting key: {key}"
                if parts[1] == "cocoindex":
                    if parts[2] == "default_scope" and parsed not in COCOINDEX_SCOPES:
                        return changed, "backends.code_intelligence.cocoindex.default_scope has invalid value"
                    if parts[2] == "storage_root" and (not isinstance(parsed, str) or not parsed.strip()):
                        return changed, "backends.code_intelligence.cocoindex.storage_root must be non-empty string"
                    if parts[2] == "workspace_glance" and not isinstance(parsed, bool):
                        return changed, "backends.code_intelligence.cocoindex.workspace_glance must be boolean"
                if parts[2] not in {"enabled", "mode", "max_results", "import_into_cix", "default_scope", "storage_root", "workspace_glance"}:
                    return changed, f"unknown backend setting key: {key}"
                backends.setdefault(section, {}).setdefault(parts[1], {})[parts[2]] = parsed
            else:
                return changed, f"unknown backend setting key: {key}"
        elif section == "derivation":
            if parts == ["derivation", "backend"]:
                if parsed not in DERIVATION_BACKENDS:
                    return changed, "backends.derivation.backend has invalid value"
                backends.setdefault(section, {})["backend"] = parsed
            elif len(parts) == 3 and parts[1] == "datalog":
                if parts[2] == "enabled" and not isinstance(parsed, bool):
                    return changed, "backends.derivation.datalog.enabled must be boolean"
                if parts[2] == "mode" and parsed not in BACKEND_MODES:
                    return changed, "backends.derivation.datalog.mode has invalid value"
                if parts[2] not in {"enabled", "mode"}:
                    return changed, f"unknown backend setting key: {key}"
                backends.setdefault(section, {}).setdefault("datalog", {})[parts[2]] = parsed
            else:
                return changed, f"unknown backend setting key: {key}"
        changed = True
    return changed, None


def backend_preset_payload(name: str) -> dict:
    backends = copy.deepcopy(DEFAULT_BACKEND_SETTINGS)
    if name == "minimal":
        return backends
    if name == "recommended":
        backends["code_intelligence"]["backend"] = "serena"
        backends["code_intelligence"]["serena"]["enabled"] = True
        backends["code_intelligence"]["serena"]["mode"] = "mcp"
        backends["code_intelligence"]["serena"]["max_results"] = 12
        backends["code_intelligence"]["cocoindex"]["enabled"] = True
        backends["code_intelligence"]["cocoindex"]["mode"] = "cli"
        backends["code_intelligence"]["cocoindex"]["max_results"] = 8
        backends["code_intelligence"]["cocoindex"]["import_into_cix"] = False
        backends["code_intelligence"]["cocoindex"]["default_scope"] = "project"
        backends["code_intelligence"]["cocoindex"]["storage_root"] = "<context>/backends/cocoindex"
        backends["code_intelligence"]["cocoindex"]["workspace_glance"] = True
        return backends
    raise ValueError(f"unknown backend preset: {name}")


def cmd_configure_runtime(
    root: Path,
    hook_verbosity: str | None,
    hook_run_capture: str | None,
    backend_preset: str | None,
    budget_items: list[str],
    input_capture_items: list[str],
    analysis_items: list[str],
    backend_items: list[str],
    show: bool,
) -> int:
    settings = load_settings(root)
    hooks = dict(settings.get("hooks", {}))
    context_budget = dict(settings.get("context_budget", {}))
    input_capture = dict(settings.get("input_capture", {}))
    analysis = dict(settings.get("analysis", {}))
    backends = dict(settings.get("backends", {}))
    changed = False
    if backend_preset:
        backends = backend_preset_payload(backend_preset)
        changed = True
    if hook_verbosity:
        hooks["verbosity"] = hook_verbosity
        changed = True
    if hook_run_capture:
        hooks["run_capture"] = hook_run_capture
        changed = True
    for item in budget_items:
        if "=" not in item:
            print(f"context budget item must be key=value: {item}")
            return 1
        key, value = [part.strip() for part in item.split("=", 1)]
        if key not in CONTEXT_BUDGET_KEYS:
            print(f"unknown context_budget key: {key}")
            return 1
        if value not in CONTEXT_BUDGET_VALUES:
            print(f"invalid context_budget value for {key}: {value}")
            return 1
        context_budget[key] = value
        changed = True
    input_capture_changed, input_capture_error = apply_input_capture_setting_items(input_capture, input_capture_items)
    if input_capture_error:
        print(input_capture_error)
        return 1
    changed = changed or input_capture_changed
    analysis_changed, analysis_error = apply_analysis_setting_items(analysis, analysis_items)
    if analysis_error:
        print(analysis_error)
        return 1
    changed = changed or analysis_changed
    backend_changed, backend_error = apply_backend_setting_items(backends, backend_items)
    if backend_error:
        print(backend_error)
        return 1
    changed = changed or backend_changed
    if changed:
        write_settings(root, hooks=hooks, context_budget=context_budget, input_capture=input_capture, analysis=analysis, backends=backends)
        invalidate_hydration_state(root, "updated runtime configuration")
    settings = load_settings(root)
    if show or changed:
        print(f"# {TEP_ICON} Runtime Configuration")
        print(f"hooks.verbosity={settings.get('hooks', {}).get('verbosity', 'normal')}")
        print(f"hooks.run_capture={settings.get('hooks', {}).get('run_capture', 'mutating')}")
        for key, value in sorted(settings.get("context_budget", {}).items()):
            print(f"context_budget.{key}={value}")
        for key, value in sorted(settings.get("input_capture", {}).items()):
            if isinstance(value, bool):
                value = str(value).lower()
            print(f"input_capture.{key}={value}")
        for section, values in sorted(settings.get("analysis", {}).items()):
            if not isinstance(values, dict):
                continue
            for key, value in sorted(values.items()):
                if isinstance(value, list):
                    value = ",".join(value)
                elif isinstance(value, bool):
                    value = str(value).lower()
                print(f"analysis.{section}.{key}={value}")
        for section, values in sorted(settings.get("backends", {}).items()):
            if not isinstance(values, dict):
                continue
            for key, value in sorted(values.items()):
                if isinstance(value, dict):
                    for nested_key, nested_value in sorted(value.items()):
                        if isinstance(nested_value, bool):
                            nested_value = str(nested_value).lower()
                        print(f"backends.{section}.{key}.{nested_key}={nested_value}")
                else:
                    if isinstance(value, bool):
                        value = str(value).lower()
                    print(f"backends.{section}.{key}={value}")
    return 0


def append_backend_access_event(root: Path, tool: str, access_kind: str, backend: str | None = None) -> None:
    event = {
        "channel": "cli",
        "tool": tool,
        "access_kind": access_kind,
        "access_is_proof": False,
        "workspace_ref": current_workspace_ref(root),
        "project_ref": current_project_ref(root),
        "task_ref": current_task_ref(root),
    }
    if backend:
        event["backend"] = backend
    append_access_event(root, event)


def cmd_backend_status(root: Path, output_format: str, repo_root: Path | None = None, scope: str | None = None) -> int:
    payload = backend_status_payload(root, repo_root=repo_root, scope=scope)
    append_backend_access_event(root, "backend-status", "backend_status")
    if output_format == "json":
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        for line in backend_status_text_lines(payload):
            print(line)
    return 0


def cmd_backend_check(
    root: Path,
    backend: str,
    output_format: str,
    repo_root: Path | None = None,
    scope: str | None = None,
) -> int:
    payload = backend_status_payload(root, repo_root=repo_root, scope=scope)
    selected = select_backend_status(payload, backend)
    append_backend_access_event(root, "backend-check", "backend_check", backend=backend)
    if output_format == "json":
        print(json.dumps({"backend_status_is_proof": False, "query": backend, "matches": selected}, indent=2, ensure_ascii=False))
    else:
        for line in backend_status_text_lines(payload, selected=selected):
            print(line)
    return 0


def cmd_validate_facts(root: Path, backend: str, output_format: str) -> int:
    payload = validate_facts_payload(root, backend=backend)
    append_backend_access_event(root, "validate-facts", "backend_validation", backend=backend)
    if output_format == "json":
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        for line in validate_facts_text_lines(payload):
            print(line)
    return 0


def cmd_export_rdf(root: Path, output_format: str, output: Path | None) -> int:
    text = export_rdf_text(root, output_format=output_format)
    append_backend_access_event(root, "export-rdf", "backend_export", backend="rdf")
    if output:
        write_text_file(output, text)
        print(f"Exported RDF projection to {output}")
    else:
        print(text, end="")
    return 0


def cmd_help(topic: str) -> int:
    topics = {
        "modes": [
            "hydration: refresh generated views and current project/task summaries",
            "lookup: one front door for facts, code, theory, visual curiosity, and policy lookup routes",
            "review context: validate records, references, and structured contradictions",
            "type graph: inspect allowed record chains and WCTX/CIX scope pressure",
            "reindex context: rebuild generated views, indexes, backlog, and reports",
            "claim graph: keyword lookup over current CLM-* records plus compact linked edges; navigation only",
            "task control: start, pause, resume, switch, complete, or stop TASK-* focus",
            "precedent review: inspect previous TASK-* records of the same task_type before repeating work",
            "evidence chain: validate agent-supplied proof chains and keep context/proof separate",
            "working context: pin WCTX-* focus/context snapshots for retrospective and handoff",
            "workspace admission: check unknown repos before attaching them to the current workspace/project",
            "topic index: generated lexical prefilter for navigation and candidate review",
            "attention index: generated tap-aware map, cold zones, and curiosity probes",
            "telemetry: non-proof MCP/CLI/hook lookup stats, raw claim read counts, and heatmap inputs",
            "probe inspect: mechanically expand one curiosity probe into record details and link status",
            "probe chain draft: mechanically draft an evidence-chain skeleton from one curiosity probe",
            "probe pack: compact mechanical probe, inspection, and chain-draft bundle",
            "next step: compact action route and --format json route_graph for mechanical branch selection",
            "logic index: generated predicate atom/rule projection over CLM.logic blocks",
            "code index: index files/symbols/areas and attach navigation-only CIX annotations",
            "backend registry: inspect optional helper availability without treating helper output as proof",
            "fact validation: backend-produced validation candidates over canonical records; navigation only",
            "strictness: inspect or change allowed_freedom through user-backed requests",
            "runtime budget: tune hook verbosity, context budget, optional analysis policy, and external backend policy through settings",
        ],
        "commands": [
            "review-context | reindex-context | scan-conflicts | type-graph --check",
            "next-step --intent answer|plan|edit|test|persist|permission|debug --task ... [--format json]",
            "lookup --query ... --reason orientation|planning|answering|permission|editing|debugging|retrospective|curiosity|migration --kind facts|code|theory|research|policy|auto [--format json]",
            "brief-context --task ... | search-records --query ... | claim-graph --query ... | record-detail --record ... | linked-records --record ...",
            "guidelines-for --task ... | code-search [--query ...] [--fields target,symbols] | telemetry-report [--format json]",
            "build-reasoning-case --task ... | augment-chain --file evidence-chain.json | validate-evidence-chain --file evidence-chain.json | validate-decision --mode planning|permission|edit|model|flow|proposal|final --chain evidence-chain.json",
            "record-input ... | record-run --command ... | record-support --thought ... --kind file-line|command-output|user-confirmation | classify-input --input INP-* --derived-record REF",
            "cleanup-candidates | cleanup-archives [--archive ARC-*] | cleanup-archive --dry-run|--apply | cleanup-restore --archive ARC-* --dry-run|--apply",
            "start-task --type investigation --scope ... --title ... --note ...",
            "validate-task-decomposition --task TASK-* | confirm-atomic-task --task TASK-* ... | decompose-task --task TASK-* --subtask scope|title|deliverable|done|verify|boundary",
            "validate-plan-decomposition --plan PLN-* | confirm-atomic-plan --plan PLN-* | decompose-plan --plan PLN-* --subplan scope|title|step|success|claim1,claim2",
            "task-outcome-check --task TASK-* --outcome done|blocked|user-question [--format json]",
            "pause-task | resume-task --task TASK-* | switch-task --task TASK-*",
            "review-precedents --task-type investigation --query ...",
            "task-drift-check --intent ... [--type investigation]",
            "record-input --input-kind user_prompt --origin-kind user --origin-ref ... --text ...",
            "working-context create|fork|show|close|check-drift",
            "workspace-admission check --repo path [--format json]",
            "topic-index build --method lexical | topic-search --query ...",
            "tap-record --record CLM-* --kind cited --intent support | telemetry-report | attention-index build | curiosity-map --mode research|theory|code [--html] | curiosity-probes --mode theory --budget 5 | probe-pack --mode theory --budget 3",
            "probe-route --index N --scope current|all | record-link --probe-index N --quote ... --note ...",
            "logic-index build | logic-search --predicate ... | logic-graph --symbol ... | logic-check",
            "backend-status [--format json] | backend-check --backend derivation.datalog [--format json]",
            "validate-facts --backend rdf_shacl [--format json]",
            "export-rdf --format turtle|jsonld [--output path]",
            "configure-runtime --backend-preset minimal|recommended",
            "configure-runtime --hook-verbosity quiet --hook-run-capture mutating --context-budget hydration=compact --input-capture user_prompts=metadata-only --analysis logic_solver.backend=z3 --backend derivation.backend=datalog",
        ],
        "records": [
            "INP-* preserves prompt/input provenance; it is not proof until classified into source-backed records",
            "FILE-* preserves file metadata and optional ART-* snapshots for file-line support",
            "RUN-* preserves Bash/tool execution metadata; runtime CLM-* in graph-v2 must trace through RUN-*",
            "CLM-* is the only truth record; fact/evidence/hypothesis are claim roles",
            "SRC-* carries raw information or artifacts that support claims",
            "PRM-*/RST-*/GLD-* authorize, constrain, or guide action but do not prove truth",
            "TASK-* captures execution focus and task_type for precedent review",
            "WCTX-* captures pinned operational context, assumptions, and focus; it is not proof",
            "CLM.logic captures typed predicate atoms/rules as a machine-checkable claim projection",
            "PRP-*/PLN-*/DEBT-* preserve critique, intended work, and unresolved obligations",
            "topic_index/*.json is generated navigation/prefilter data only",
            "attention_index/*.json, activity/taps.jsonl, and activity/access.jsonl are generated navigation/curiosity data only",
            "logic_index/*.json is generated checking/navigation data only",
            "CIX-* is navigation/code-map metadata only, never proof",
        ],
        "workflows": [
            "Before planning/editing: hydrate, check task alignment, lookup context, cite decisive ids",
            "During investigation: use hypotheses locally but do not make proof from unconfirmed claims",
            "After actions: record durable ACT/SRC/CLM/DEBT/CIX updates only when future agents need them",
            "When switching work type: pause/switch tasks and run precedent review when similar tasks exist",
        ],
    }
    selected = topics if topic == "all" else {topic: topics[topic]}
    print(f"# {TEP_ICON} TEP Runtime Help")
    for title, lines in selected.items():
        print(f"\n## {title.title()}")
        for line in lines:
            print(f"- {line}")
    return 0


LOOKUP_KINDS = {"auto", "facts", "code", "theory", "research", "policy"}
LOOKUP_REASONS = {
    "orientation",
    "planning",
    "answering",
    "permission",
    "editing",
    "debugging",
    "retrospective",
    "curiosity",
    "migration",
}
LOOKUP_REASON_CONTEXT_KIND = {
    "planning": "planning",
    "editing": "edit",
    "permission": "permission",
    "retrospective": "handoff",
    "curiosity": "investigation",
    "debugging": "investigation",
}


def infer_lookup_kind(query: str, requested_kind: str) -> str:
    if requested_kind in LOOKUP_KINDS and requested_kind != "auto":
        return requested_kind
    lowered = query.lower()
    code_terms = {"code", "file", "function", "class", "import", "symbol", "test", "pytest", "src", "module"}
    policy_terms = {"guideline", "permission", "restriction", "rule", "policy", "allowed", "forbidden"}
    theory_terms = {"model", "flow", "theory", "hypothesis", "why", "cause", "relationship", "contradiction"}
    if any(term in lowered for term in code_terms):
        return "code"
    if any(term in lowered for term in policy_terms):
        return "policy"
    if any(term in lowered for term in theory_terms):
        return "theory"
    return "facts"


def active_working_context_for_lookup(records: dict[str, dict], project_ref: str, task_ref: str) -> dict | None:
    task = records.get(task_ref) if task_ref else None
    if task and task.get("record_type") == "task":
        for ref in task.get("working_context_refs", []):
            context = records.get(str(ref))
            if context and context.get("record_type") == "working_context" and str(context.get("status", "")).strip() == "active":
                return context
    candidates = [
        data
        for data in records.values()
        if data.get("record_type") == "working_context"
        and str(data.get("status", "")).strip() == "active"
        and record_belongs_to_project(data, project_ref or None)
        and record_belongs_to_task(data, task_ref or None)
    ]
    return sorted(candidates, key=lambda item: str(item.get("updated_at", "")), reverse=True)[0] if candidates else None


def ensure_lookup_working_context(root: Path, records: dict[str, dict], query: str, reason: str) -> tuple[str, dict | None, str | None]:
    workspace_ref = current_workspace_ref(root)
    project_ref = current_project_ref(root)
    task_ref = current_task_ref(root)
    existing = active_working_context_for_lookup(records, project_ref, task_ref)
    if existing:
        return str(existing.get("id", "")), None, None
    if not workspace_ref:
        return "", None, "lookup requires an active workspace before creating WCTX; run workspace-admission for this repository"

    timestamp = now_timestamp()
    payload = build_working_context_payload(
        record_id=next_record_id(records, "WCTX-"),
        timestamp=timestamp,
        scope=f"lookup.{reason}",
        title=f"Lookup {reason}: {concise(query, 80)}",
        context_kind=LOOKUP_REASON_CONTEXT_KIND.get(reason, "general"),
        pinned_refs=[],
        focus_paths=[],
        topic_terms=sorted(task_terms(query))[:8],
        topic_seed_refs=[],
        assumptions=[],
        concerns=[],
        project_refs=project_refs_for_write(root, []),
        task_refs=task_refs_for_write(root, []),
        tags=["auto-wctx", f"lookup-reason:{reason}"],
        note="Auto-created by lookup to keep agent operational context explicit. Not proof and not authorization.",
    )
    exit_code = persist_working_context_with_task_links(root, records, payload, quiet=True)
    if exit_code:
        return "", None, "failed to auto-create WCTX for lookup"
    return str(payload["id"]), payload, None


def lookup_payload(query: str, kind: str, root_path: str, scope: str, mode: str, reason: str, wctx_ref: str, auto_wctx: dict | None) -> dict:
    selected_kind = infer_lookup_kind(query, kind)
    query_arg = shlex.quote(query)
    root_arg = shlex.quote(root_path)
    route_commands: dict[str, list[str]] = {
        "facts": [
            f"claim-graph --query {query_arg} --format json",
            f"search-records --query {query_arg} --type claim --format json",
            "record-detail --record CLM-* --format json",
            "linked-records --record CLM-* --format json",
        ],
        "code": [
            f"code-search --query {query_arg} --root {root_arg} --fields target,symbols,features,freshness --format json",
            f"code-feedback --query {query_arg} --root {root_arg} --format json",
            "code-info --entry CIX-* --fields target,symbols,features,freshness --format json",
            f"curiosity-map --mode code --scope {scope} --volume compact",
        ],
        "theory": [
            f"claim-graph --query {query_arg} --format json",
            f"search-records --query {query_arg} --type model --type flow --type open_question --type proposal --format json",
            f"curiosity-map --mode theory --scope {scope} --volume compact",
            f"probe-pack --mode theory --scope {scope} --budget 3 --format json",
        ],
        "research": [
            f"brief-context --task {query_arg} --detail compact",
            f"search-records --query {query_arg} --include-fallback --format json",
            f"curiosity-map --mode research --scope {scope} --volume compact",
            f"probe-pack --mode research --scope {scope} --budget 3 --format json",
        ],
        "policy": [
            f"guidelines-for --task {query_arg} --format json",
            f"search-records --query {query_arg} --type guideline --type permission --type restriction --type proposal --format json",
            "record-detail --record GLD-* --format json",
        ],
    }
    primary_tool = {
        "facts": "claim-graph",
        "code": "code-search",
        "theory": "curiosity-map",
        "research": "brief-context",
        "policy": "guidelines-for",
    }[selected_kind]
    inferred_mode = {"code": "code", "theory": "theory", "research": "research"}.get(selected_kind, "general")
    selected_mode = mode if mode in ATTENTION_MODES and mode != "general" else inferred_mode
    evidence_profile = {
        "lookup_is_proof": False,
        "raw_claim_reads": "blocked-in-normal-mode",
        "normal_entrypoint": "lookup",
        "drill_down_tools": ["search-records", "claim-graph", "record-detail", "linked-records"],
        "preferred_read_order": [
            "MODEL/FLOW summaries for integrated picture",
            "active corroborated/supported CLM through claim-graph",
            "record-detail/linked-records for proof quotes",
            "tentative hypotheses for exploration only",
            "resolved/historical fallback only after active records fail",
        ],
        "model_flow_priority": "MODEL-* and FLOW-* rank high because they are compact derivative pictures over source-backed claims.",
        "model_flow_write_boundary": "MODEL/FLOW must be based on user-confirmed theory claims, not tentative/runtime-only observations.",
    }
    output_contract = {
        "contract_version": 1,
        "agent_role": "choose and justify a route; API validates proof boundaries and allowed writes",
        "if_answering": "open record-detail or linked-records before citing a record as proof",
        "if_new_support_found": "use record-support/record-evidence so FILE/RUN/SRC/CLM links are created mechanically",
        "if_chain_needed": "draft ids/quotes, run augment-chain, then validate-evidence-chain or validate-decision",
        "if_theory_should_rank_high": "promote supported/user-confirmed theory into MODEL/FLOW through validated write paths",
        "if_uncertain": "record a tentative CLM, OPEN-*, or PRP-* instead of silently relying on a guess",
    }
    return {
        "api_contract_version": 1,
        "lookup_is_proof": False,
        "query": query,
        "reason": reason,
        "requested_kind": kind,
        "kind": selected_kind,
        "scope": scope,
        "mode": selected_mode,
        "root": root_path,
        "focus": {
            "workspace_ref": "",
            "project_ref": "",
            "task_ref": "",
            "working_context_ref": wctx_ref,
            "auto_created_working_context": bool(auto_wctx),
        },
        "primary_tool": primary_tool,
        "route": route_commands[selected_kind],
        "next_allowed_commands": route_commands[selected_kind],
        "fallback_route": [
            f"search-records --query {query_arg} --format json",
            f"curiosity-map --mode {selected_mode} --scope {scope} --volume compact",
            "telemetry-report --format json",
        ],
        "route_graph": {
            "graph_version": 1,
            "entrypoint": "lookup",
            "branches": [
                {"if": "candidate record found", "then": "record-detail|linked-records"},
                {"if": "new source support found", "then": "record-support|record-evidence"},
                {"if": "chain needed", "then": "augment-chain|validate-evidence-chain"},
                {"if": "integrated theory needed", "then": "record-model|record-flow after user-confirmed theory support"},
                {"if": "route underdetermined", "then": "record-open-question|record-proposal"},
            ],
        },
        "evidence_profile": evidence_profile,
        "output_contract": output_contract,
        "rules": [
            "Use lookup first when unsure where to search.",
            "Treat lookup and generated maps as navigation only, not proof.",
            "Open record-detail or linked-records before citing a canonical record.",
            "When new support is found, prefer record-support or record-evidence over separate manual record-source/record-claim calls.",
            "Use code-search through TEP; do not call external code backends directly in normal work.",
        ],
    }


def lookup_text_lines(payload: dict) -> list[str]:
    lines = [
        "# TEP Lookup Route",
        "",
        "Mode: one front door for facts, code, theory, research, and policy lookup. Not proof.",
        f"query: `{payload.get('query', '')}` reason: `{payload.get('reason')}` kind: `{payload.get('kind')}` primary_tool: `{payload.get('primary_tool')}` scope: `{payload.get('scope')}` mode: `{payload.get('mode')}`",
        f"focus: workspace=`{payload.get('focus', {}).get('workspace_ref', '')}` project=`{payload.get('focus', {}).get('project_ref', '')}` task=`{payload.get('focus', {}).get('task_ref', '')}` wctx=`{payload.get('focus', {}).get('working_context_ref', '')}`",
        "",
        "## Route",
    ]
    for command in payload.get("route", []):
        lines.append(f"- `{command}`")
    lines.extend(["", "## Fallback"])
    for command in payload.get("fallback_route", []):
        lines.append(f"- `{command}`")
    lines.extend(["", "## Rules"])
    for rule in payload.get("rules", []):
        lines.append(f"- {rule}")
    contract = payload.get("output_contract") or {}
    if contract:
        lines.extend(["", "## Output Contract"])
        lines.append(f"- agent_role: {contract.get('agent_role')}")
        lines.append(f"- if_chain_needed: {contract.get('if_chain_needed')}")
    return lines


def cmd_lookup(root: Path, query: str, kind: str, root_path: str | None, scope: str, mode: str, reason: str, output_format: str) -> int:
    if not query.strip():
        print("lookup query must not be empty")
        return 1
    if reason not in LOOKUP_REASONS:
        print(f"lookup --reason is required and must be one of: {', '.join(sorted(LOOKUP_REASONS))}")
        return 1
    records, exit_code = load_valid_context_readonly(root)
    if exit_code:
        return exit_code
    wctx_ref, auto_wctx, error = ensure_lookup_working_context(root, records, query, reason)
    if error:
        print(error)
        return 1
    payload = lookup_payload(
        query=query,
        kind=kind,
        root_path=str(root_path or Path.cwd()),
        scope=scope,
        mode=mode,
        reason=reason,
        wctx_ref=wctx_ref,
        auto_wctx=auto_wctx,
    )
    payload["focus"]["workspace_ref"] = current_workspace_ref(root)
    payload["focus"]["project_ref"] = current_project_ref(root)
    payload["focus"]["task_ref"] = current_task_ref(root)
    if auto_wctx:
        payload["auto_created_working_context"] = {
            "id": auto_wctx.get("id", ""),
            "scope": auto_wctx.get("scope", ""),
            "title": auto_wctx.get("title", ""),
            "context_kind": auto_wctx.get("context_kind", ""),
            "not_proof": True,
        }
    append_lookup_access_event(
        root,
        channel="cli",
        tool="lookup",
        access_kind="record_search",
        record_refs=[],
        query=query,
        reason=reason,
        working_context_ref=wctx_ref,
        note=f"lookup route kind={payload['kind']} primary_tool={payload['primary_tool']} reason={reason} wctx={wctx_ref}",
    )
    if output_format == "json":
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        print("\n".join(lookup_text_lines(payload)))
    return 0


def cmd_task_drift_check(root: Path, intent: str, task_ref: str | None, task_type: str | None) -> int:
    records, exit_code = load_valid_context_readonly(root)
    if exit_code:
        return exit_code
    ref = (task_ref or current_task_ref(root)).strip()
    task = records.get(ref) if ref else None
    payload = build_task_drift_payload(ref, task, intent, task_type)
    for line in task_drift_text_lines(payload):
        print(line)
    return int(payload.get("exit_code", 0))


def cmd_review_precedents(
    root: Path,
    task_ref: str | None,
    task_type: str | None,
    query: str | None,
    limit: int,
) -> int:
    records, exit_code = load_valid_context_readonly(root)
    if exit_code:
        return exit_code
    current_ref = (task_ref or current_task_ref(root)).strip()
    current_task = records.get(current_ref) if current_ref else None
    resolved_type = task_type or (
        str(current_task.get("task_type", "general")).strip() if current_task and current_task.get("record_type") == "task" else "general"
    )
    resolved_type = resolved_type or "general"
    search_text = query or (task_identity_text(current_task) if current_task else resolved_type)
    tasks = select_precedent_tasks(
        records,
        current_ref,
        resolved_type,
        search_text,
        current_project_ref(root) or None,
        query,
        limit,
    )
    payload = build_precedent_review_payload(current_task, resolved_type, query, tasks)
    for line in precedent_review_text_lines(payload):
        print(line)
    return 0


def cmd_build_reasoning_case(
    root: Path,
    task: str,
    claim_refs: list[str],
    model_refs: list[str],
    flow_refs: list[str],
    limit: int,
) -> int:
    records, exit_code = load_valid_context_readonly(root)
    if exit_code:
        return exit_code
    payload = build_reasoning_case_payload(
        records,
        task,
        claim_refs,
        model_refs,
        flow_refs,
        current_task_ref(root),
        current_project_ref(root),
        limit,
    )
    for line in reasoning_case_text_lines(payload):
        print(line)
    return 0


def unclassified_input_review_lines(records: dict[str, dict]) -> list[str]:
    lines = [
        "# Generated Input Classification Review",
        "",
        "INP-* records are prompt provenance only. They are not facts, rules, permissions, "
        "restrictions, or proof until classified into canonical records.",
        "",
    ]
    for item in unclassified_input_items(records):
        lines.append(
            f"- `{item['id']}` has no valid `derived_record_refs` and no incoming `input_refs`: {item['summary']}"
        )
    if len(lines) == 4:
        lines.append("- No unclassified inputs detected.")
    return lines


def input_triage_payload(records: dict[str, dict], task_ref: str | None, limit: int) -> dict:
    items = input_items_for_task(records, task_ref)
    return {
        "input_triage_is_proof": False,
        "task_ref": task_ref or "",
        "count": len(items),
        "items": items[: max(0, limit)],
        "omitted": max(0, len(items) - max(0, limit)),
    }


def input_triage_text_lines(payload: dict) -> list[str]:
    lines = [
        "# Input Triage",
        "",
        "INP-* is prompt provenance only. Triage links operational prompts to WCTX/TASK; it is not proof and does not create facts.",
        f"task_ref: `{payload.get('task_ref') or 'all'}`",
        f"unclassified_count: `{payload.get('count', 0)}`",
        "",
    ]
    for item in payload.get("items", []):
        task_refs = ",".join(item.get("task_refs", [])) or "none"
        lines.append(f"- `{item['id']}` task_refs=`{task_refs}`: {item['summary']}")
    if payload.get("omitted"):
        lines.append(f"- ... {payload['omitted']} more")
    return lines


def cmd_input_triage_report(root: Path, task_ref: str | None, limit: int, output_format: str) -> int:
    records, exit_code = load_valid_context_readonly(root)
    if exit_code:
        return exit_code
    payload = input_triage_payload(records, task_ref, limit)
    if output_format == "json":
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        print("\n".join(input_triage_text_lines(payload)))
    return 0


def cmd_input_triage_link_operational(root: Path, task_ref: str, input_refs: list[str], note: str | None) -> int:
    records, exit_code = load_clean_context(root)
    if exit_code:
        return 1
    task = records.get(task_ref)
    if not task or task.get("record_type") != "task":
        print(f"{task_ref} must reference a task record")
        return 1
    refs = [ref.strip() for ref in input_refs if ref.strip()]
    if not refs:
        refs = [item["id"] for item in input_items_for_task(records, task_ref)]
    if not refs:
        print(f"No unclassified inputs found for task {task_ref}")
        return 0
    missing = [ref for ref in refs if ref not in records or records[ref].get("record_type") != "input"]
    if missing:
        print("missing input record(s): " + ", ".join(missing))
        return 1

    timestamp = now_timestamp()
    payload = build_working_context_payload(
        record_id=next_record_id(records, "WCTX-"),
        timestamp=timestamp,
        scope=str(task.get("scope") or "input-triage"),
        title=f"Operational input triage for {task_ref}",
        context_kind="handoff",
        pinned_refs=[],
        focus_paths=[],
        topic_terms=["input-triage", "operational-provenance"],
        topic_seed_refs=[task_ref],
        assumptions=[],
        concerns=[],
        project_refs=project_refs_for_write(root, []),
        task_refs=[task_ref],
        tags=["input-triage", "operational"],
        note=append_note(
            f"Operational prompts acknowledged for {task_ref}. This WCTX is not proof.",
            note or "",
        ),
    )
    payload["input_refs"] = refs
    result = persist_working_context_with_task_links(root, records, payload, quiet=False)
    if result:
        return result
    print(f"Linked {len(refs)} operational input(s) to {payload['id']} for task {task_ref}")
    return 0


def cmd_review_context(root: Path) -> int:
    records, errors = collect_validation_errors(root)
    write_validation_report(root, errors)
    conflict_lines = refresh_generated_outputs(root, records)
    input_lines = unclassified_input_review_lines(records)
    write_text_file(root / "review" / "inputs.md", "\n".join(input_lines) + "\n")
    if errors:
        print_errors(errors)
        return 1
    issue_count = sum(1 for line in input_lines if line.startswith("- `INP-"))
    if issue_count:
        print(f"{root / 'review' / 'inputs.md'}: {issue_count} unclassified input(s)")
        print("INP-* is prompt provenance only; classify into SRC/CLM/GLD/etc before calling it fact or rule.")
    if conflict_lines:
        print(f"{root / 'review' / 'conflicts.md'}: {len(conflict_lines)} conflict issue(s)")
        print("Reviewed context with conflict issues; flow may continue, but conflict-aware preflight may still block planning or mutation.")
        return 0
    print(f"Reviewed context: {root}")
    return 0


def cmd_reindex_context(root: Path) -> int:
    records, errors = collect_validation_errors(root)
    write_validation_report(root, errors)
    conflict_lines = refresh_generated_outputs(root, records)
    if errors:
        print_errors(errors)
        return 1
    if conflict_lines:
        print(f"{root / 'review' / 'conflicts.md'}: {len(conflict_lines)} conflict issue(s)")
        print("Reindexed context with conflict issues; generated views were refreshed.")
        return 0
    print(f"Reindexed context: {root}")
    return 0


def cmd_request_strictness_change(
    root: Path,
    value: str,
    permission_ref: str | None,
    reason: str,
    scope: str | None,
) -> int:
    if value not in ALLOWED_FREEDOM:
        print(f"Unsupported strictness: {value}")
        return 1
    records, exit_code = load_clean_context(root, allowed_freedom=value)
    if exit_code:
        return 1
    current_value = load_settings(root).get("allowed_freedom", "proof-only")
    if not is_strictness_escalation(current_value, value):
        print(f"No approval request required for {current_value} -> {value}; use change-strictness directly.")
        return 0
    if value in PERMISSION_REQUIRED_FREEDOMS:
        if not permission_ref:
            print(f"request-strictness-change {value} requires --permission PRM-* with explicit allowed_freedom grant")
            return 1
        if not permission_allows_strictness(records, permission_ref, value):
            print(f"permission {permission_ref} does not grant allowed_freedom {value}")
            return 1

    entries, errors = load_strictness_requests(root)
    if errors:
        for error in errors:
            print(error)
        return 1
    request_id = next_strictness_request_id()
    timestamp = now_timestamp()
    entry = {
        "id": request_id,
        "status": "pending",
        "from": current_value,
        "to": value,
        "permission_ref": permission_ref,
        "task_ref": current_task_ref(root),
        "project_ref": current_project_ref(root),
        "scope": (scope or "").strip(),
        "reason": reason.strip(),
        "created_at": timestamp,
        "updated_at": timestamp,
    }
    entries.append(entry)
    write_strictness_requests(root, entries)
    invalidate_hydration_state(root, f"requested strictness change {request_id}")
    print("Strictness change approval required.")
    print(f"request: {request_id}")
    print(f"from: {current_value}")
    print(f"to: {value}")
    if permission_ref:
        print(f"permission: {permission_ref}")
    if entry["task_ref"]:
        print(f"task: {entry['task_ref']}")
    if entry["project_ref"]:
        print(f"project: {entry['project_ref']}")
    if entry["scope"]:
        print(f"scope: {entry['scope']}")
    print(f"reason: {entry['reason']}")
    print("")
    print("Ask the user to reply exactly:")
    print(f"TEP-APPROVE {request_id}")
    return 0


def cmd_change_strictness(
    root: Path,
    value: str,
    permission_ref: str | None,
    request_ref: str | None,
    approval_source_ref: str | None,
) -> int:
    if value not in ALLOWED_FREEDOM:
        print(f"Unsupported strictness: {value}")
        return 1
    records, exit_code = load_clean_context(root, allowed_freedom=value)
    if exit_code:
        return 1
    current_value = load_settings(root).get("allowed_freedom", "proof-only")
    request_to_mark_used = None
    strictness_entries: list[dict] = []
    if is_strictness_escalation(current_value, value):
        strictness_entries, request_errors = load_strictness_requests(root)
        if request_errors:
            for error in request_errors:
                print(error)
            return 1
        request_to_mark_used, request_error = strictness_request_allows_change(
            records,
            strictness_entries,
            request_ref=request_ref,
            approval_source_ref=approval_source_ref,
            current_value=current_value,
            value=value,
            permission_ref=permission_ref,
        )
        if request_error:
            print(request_error)
            return 1
    if value in PERMISSION_REQUIRED_FREEDOMS and value != current_value:
        if not permission_ref:
            print(f"change-strictness {value} requires --permission PRM-* with explicit user-backed allowed_freedom grant")
            return 1
        if not permission_allows_strictness(records, permission_ref, value):
            print(f"permission {permission_ref} does not grant allowed_freedom {value}")
            return 1
    if request_to_mark_used is not None:
        timestamp = now_timestamp()
        request_to_mark_used["status"] = "used"
        request_to_mark_used["used_at"] = timestamp
        request_to_mark_used["updated_at"] = timestamp
        request_to_mark_used["approval_source_ref"] = approval_source_ref
        write_strictness_requests(root, strictness_entries)
    write_settings(root, value)
    build_index(root, records)
    write_backlog(root, records)
    invalidate_hydration_state(root, f"changed strictness to {value}")
    print(f"Changed strictness to {value} for {root}")
    return 0


def cmd_scan_conflicts(root: Path) -> int:
    records, errors = collect_validation_errors(root)
    conflict_lines = refresh_generated_outputs(root, records)
    if errors:
        print_errors(errors)
        return 1
    if conflict_lines:
        print(f"{root / 'review' / 'conflicts.md'}: {len(conflict_lines)} conflict issue(s)")
        return 0
    print(f"No structured conflicts found in {root}")
    return 0


def cmd_impact_graph(root: Path, claim_ref: str) -> int:
    records, exit_code = load_clean_context(root)
    if exit_code:
        return 1
    if claim_ref not in records:
        print(f"missing record {claim_ref}")
        return 1
    if records[claim_ref].get("record_type") != "claim":
        print(f"{claim_ref} must reference a claim record")
        return 1

    impact = collect_dependency_impact(root, records, claim_ref)
    payload = build_impact_graph_payload(claim_ref, impact)
    for line in impact_graph_text_lines(payload):
        print(line)
    return 0


def cmd_linked_records(root: Path, record_ref: str, direction: str, depth: int, output_format: str) -> int:
    records, exit_code = load_valid_context_readonly(root)
    if exit_code:
        return exit_code
    if record_ref not in records:
        print(f"missing record {record_ref}")
        return 1

    payload = linked_records_payload(records, record_ref, direction, depth)
    outgoing_by_ref = payload["_outgoing_by_ref"]
    incoming_by_ref = payload["_incoming_by_ref"]
    append_lookup_access_event(
        root,
        channel="cli",
        tool="linked-records",
        access_kind="linked_records",
        record_refs=[str(record.get("id") or "") for record in payload.get("records", [])] + [record_ref],
        note=f"direction={direction} depth={depth}",
    )

    def edge_key(edge: dict) -> tuple:
        return edge["from"], edge["to"], tuple(edge["fields"])

    if output_format == "json":
        public_payload = {key: value for key, value in payload.items() if not key.startswith("_")}
        print(
            json.dumps(
                public_payload,
                indent=2,
                ensure_ascii=False,
            )
        )
        return 0

    print("# Linked Records\n")
    anchor = records[record_ref]
    print(
        f"Anchor: `{record_ref}` type=`{anchor.get('record_type')}` "
        f"status=`{anchor.get('status', anchor.get('critique_status', ''))}`"
    )
    print(f"Direction: `{direction}`")
    print(f"Depth: `{depth}`\n")
    direct_outgoing = outgoing_by_ref.get(record_ref, [])
    direct_incoming = incoming_by_ref.get(record_ref, [])
    if direction in {"outgoing", "both"}:
        print("## Direct Outgoing")
        if direct_outgoing:
            for edge in sorted(direct_outgoing, key=edge_key):
                target = records[edge["to"]]
                print(
                    f"- `{edge['to']}` type=`{target.get('record_type')}` via `{', '.join(edge['fields'])}`: "
                    f"{record_summary(target)}"
                )
        else:
            print("- none")
        print()
    if direction in {"incoming", "both"}:
        print("## Direct Incoming")
        if direct_incoming:
            for edge in sorted(direct_incoming, key=edge_key):
                source = records[edge["from"]]
                print(
                    f"- `{edge['from']}` type=`{source.get('record_type')}` via `{', '.join(edge['fields'])}`: "
                    f"{record_summary(source)}"
                )
        else:
            print("- none")
        print()
    print("## Linked Records By Distance")
    if payload["records_by_distance"]:
        for distance, ids in sorted(payload["records_by_distance"].items(), key=lambda item: int(item[0])):
            print(f"### Distance {distance}")
            for record_id in sorted(ids):
                data = records[record_id]
                print(f"- `{record_id}` type=`{data.get('record_type')}`: {record_summary(data)}")
    else:
        print("- none")
    return 0


def print_record_detail_text(payload: dict) -> None:
    for line in record_detail_text_lines(payload):
        print(line)


def cmd_record_detail(root: Path, record_ref: str, output_format: str) -> int:
    records, exit_code = load_valid_context_readonly(root)
    if exit_code:
        return exit_code
    if record_ref not in records:
        print(f"missing record {record_ref}")
        return 1

    payload = record_detail_payload(records, record_ref)
    append_lookup_access_event(
        root,
        channel="cli",
        tool="record-detail",
        access_kind="record_detail",
        record_refs=[record_ref],
        note="record detail lookup",
    )
    if output_format == "json":
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        print_record_detail_text(payload)
    return 0


def cmd_record_neighborhood(root: Path, record_ref: str, depth: int, output_format: str) -> int:
    records, exit_code = load_valid_context_readonly(root)
    if exit_code:
        return exit_code
    if record_ref not in records:
        print(f"missing record {record_ref}")
        return 1

    payload = record_detail_payload(records, record_ref, depth=max(1, depth))
    if output_format == "json":
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return 0

    print_record_detail_text(payload)
    print("\n## Neighborhood")
    records_by_distance = payload["links"]["records_by_distance"]
    if not records_by_distance:
        print("- none")
        return 0
    for distance, ids in sorted(records_by_distance.items(), key=lambda item: int(item[0])):
        print(f"### Distance {distance}")
        for linked_id in ids:
            linked = records[linked_id]
            print(f"- `{linked_id}` type=`{linked.get('record_type')}`: {record_summary(linked)}")
    return 0


def cmd_guidelines_for(
    root: Path,
    task: str,
    domain: str | None,
    limit: int,
    all_projects: bool,
    include_task_local: bool,
    output_format: str,
) -> int:
    records, exit_code = load_valid_context_readonly(root)
    if exit_code:
        return exit_code
    terms = task_terms(task)
    project_ref = None if all_projects else current_project_ref(root) or None
    task_ref = None if include_task_local else current_task_ref(root) or None
    guidelines = active_guidelines_for(records, terms, project_ref, task_ref, limit=max(1, limit * 3))
    if domain:
        guidelines = [guideline for guideline in guidelines if str(guideline.get("domain", "")).strip() == domain]
    guidelines = guidelines[: max(1, limit)]

    if output_format == "json":
        print(
            json.dumps(
                {
                    "task": task,
                    "terms": sorted(terms),
                    "domain_filter": domain,
                    "project_filter": project_ref or None,
                    "task_filter": task_ref or None,
                    "guidelines": [public_record_payload(guideline) for guideline in guidelines],
                },
                indent=2,
                ensure_ascii=False,
            )
        )
        return 0

    print("# Guidelines For Task\n")
    print(f"Task: {task}")
    if domain:
        print(f"Domain filter: `{domain}`")
    if project_ref:
        print(f"Project filter: `{project_ref}`")
    if task_ref:
        print(f"Task filter: `{task_ref}`")
    print()
    if not guidelines:
        print("- no matching active guidelines")
        return 0
    for guideline in guidelines:
        print_guideline_detail(guideline)
    return 0


def cmd_cleanup_candidates(root: Path, limit: int, output_format: str) -> int:
    records, load_errors = load_records(root)
    if load_errors:
        print_errors(load_errors)
        return 1
    items, validation_errors = cleanup_candidate_items(root, records)
    limited_items = items[: max(1, limit)]

    if output_format == "json":
        print(
            json.dumps(
                {
                    "cleanup_is_read_only": True,
                    "validation_error_count": len(validation_errors),
                    "candidate_count": len(items),
                    "candidates": limited_items,
                },
                indent=2,
                ensure_ascii=False,
            )
        )
        return 0

    print("# Cleanup Candidates\n")
    print("Mode: read-only report. No records were changed.")
    print(f"Validation errors observed: {len(validation_errors)}")
    print(f"Candidate count: {len(items)}\n")
    if not limited_items:
        print("- no cleanup candidates found")
        return 0
    for item in limited_items:
        record = item.get("record", {})
        refs = item.get("refs", [])
        refs_suffix = f" refs={refs}" if refs else ""
        print(
            f"- kind=`{item.get('kind')}` record=`{record.get('id')}` "
            f"type=`{record.get('record_type')}`{refs_suffix}: {item.get('suggestion')}"
        )
    if len(items) > len(limited_items):
        print(f"\n... {len(items) - len(limited_items)} more candidate(s) omitted by --limit")
    return 0


def cmd_cleanup_archive(root: Path, dry_run: bool, apply: bool, limit: int, output_format: str) -> int:
    if dry_run == apply:
        print("cleanup-archive requires exactly one of --dry-run or --apply")
        return 1
    records, load_errors = load_records(root)
    if load_errors:
        print_errors(load_errors)
        return 1
    if apply:
        try:
            payload, _validation_errors = cleanup_archive_apply_payload(root, records, limit=limit)
        except OSError as exc:
            print(exc)
            return 1
    else:
        payload, _validation_errors = cleanup_archive_plan_payload(root, records, limit=limit)
    if output_format == "json":
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return 0
    print("\n".join(cleanup_archive_plan_text_lines(payload)))
    return 0


def cmd_cleanup_archives(root: Path, archive_ref: str | None, limit: int, output_format: str) -> int:
    try:
        payload = cleanup_archives_payload(root, archive_ref=archive_ref, limit=limit)
    except (OSError, ValueError, json.JSONDecodeError, zipfile.BadZipFile) as exc:
        print(exc)
        return 1
    if output_format == "json":
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return 0
    print("\n".join(cleanup_archives_text_lines(payload)))
    return 0


def cmd_cleanup_restore(root: Path, archive_ref: str, dry_run: bool, apply: bool, output_format: str) -> int:
    if dry_run == apply:
        print("cleanup-restore requires exactly one of --dry-run or --apply")
        return 1
    try:
        if apply:
            payload = cleanup_restore_apply_payload(root, archive_ref=archive_ref)
            if int(payload.get("restored_count") or 0) > 0:
                records, validation_errors = collect_validation_errors(root)
                write_validation_report(root, validation_errors)
                refresh_generated_outputs(root, records)
                invalidate_hydration_state(root, f"restored cleanup archive {payload.get('archive_id')}")
                payload["validation_error_count"] = len(validation_errors)
        else:
            payload = cleanup_restore_plan_payload(root, archive_ref=archive_ref)
    except (OSError, ValueError, json.JSONDecodeError, zipfile.BadZipFile) as exc:
        print(exc)
        return 1
    if output_format == "json":
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        print("\n".join(cleanup_restore_plan_text_lines(payload)))
    return 1 if payload.get("restore_blocked") else 0


def cmd_topic_index_build(
    root: Path,
    method: str,
    terms_per_record: int,
    topic_limit: int,
    candidate_limit: int,
) -> int:
    if method != "lexical":
        print("only lexical topic indexing is currently supported")
        return 1
    records, exit_code = load_clean_context(root)
    if exit_code:
        return 1
    payload = build_lexical_topic_index(records, terms_per_record=terms_per_record, topic_limit=topic_limit)
    candidates = topic_conflict_candidates(records, payload["records"], limit=candidate_limit)
    write_topic_index_reports(root, payload, candidates)
    invalidate_hydration_state(root, "rebuilt topic index")
    print(
        f"Built lexical topic index: records={payload['record_count']} "
        f"topics={payload['topic_count']} candidates={len(candidates)}"
    )
    print("Topic index is navigation/prefilter data only; it is not proof.")
    return 0


def cmd_topic_search(
    root: Path,
    query: str,
    limit: int,
    record_types: list[str],
    output_format: str,
) -> int:
    records, exit_code = load_valid_context_readonly(root)
    if exit_code:
        return exit_code
    topic_records = load_topic_records(root)
    if not topic_records:
        print("topic index is missing or empty; run `topic-index build --method lexical` first")
        return 1
    terms = set(topic_tokenize(query))
    if not terms:
        print("topic search query must contain at least one searchable token with 3+ characters")
        return 1
    allowed_types = {item.strip() for item in record_types if item.strip()}
    ranked = []
    for record_id, item in topic_records.items():
        if record_id not in records:
            continue
        if allowed_types and str(item.get("record_type", "")).strip() not in allowed_types:
            continue
        score, matched = topic_search_matches(item, terms)
        if score <= 0:
            continue
        ranked.append((score, record_id, item, matched))
    ranked = sorted(ranked, key=lambda entry: (-entry[0], entry[1]))[: max(1, limit)]

    if output_format == "json":
        print(
            json.dumps(
                {
                    "query": query,
                    "terms": sorted(terms),
                    "topic_index_is_proof": False,
                    "results": [
                        {
                            "score": score,
                            "matched_terms": matched,
                            **item,
                        }
                        for score, _, item, matched in ranked
                    ],
                },
                indent=2,
                ensure_ascii=False,
            )
        )
        return 0

    print("# Topic Search\n")
    print("Mode: lexical topic prefilter. Results are navigation candidates, not proof.")
    print(f"Query: {query}")
    print(f"Terms: {', '.join(sorted(terms))}\n")
    if not ranked:
        print("- no topic matches")
        return 0
    for score, record_id, item, matched in ranked:
        print(
            f"- `{record_id}` type=`{item.get('record_type')}` status=`{item.get('status')}` "
            f"score={score:.4f} matched={', '.join(matched)}"
        )
        print(f"  summary: {item.get('summary', '')}")
    return 0


def cmd_topic_info(root: Path, record_ref: str, limit: int, output_format: str) -> int:
    records, exit_code = load_valid_context_readonly(root)
    if exit_code:
        return exit_code
    topic_records = load_topic_records(root)
    if not topic_records:
        print("topic index is missing or empty; run `topic-index build --method lexical` first")
        return 1
    item = topic_records.get(record_ref)
    if not item:
        print(f"{record_ref} is not present in topic index")
        return 1

    terms = {term_info["term"] for term_info in item.get("terms", []) if isinstance(term_info, dict) and term_info.get("term")}
    similar = []
    for other_ref, other in topic_records.items():
        if other_ref == record_ref or other_ref not in records:
            continue
        other_terms = {term_info["term"] for term_info in other.get("terms", []) if isinstance(term_info, dict) and term_info.get("term")}
        shared = sorted(terms & other_terms)
        if not shared:
            continue
        similar.append((len(shared), other_ref, other, shared))
    similar = sorted(similar, key=lambda entry: (-entry[0], entry[1]))[: max(1, limit)]

    if output_format == "json":
        print(
            json.dumps(
                {
                    "record": item,
                    "topic_index_is_proof": False,
                    "similar": [
                        {
                            "shared_count": shared_count,
                            "shared_terms": shared,
                            **other,
                        }
                        for shared_count, _, other, shared in similar
                    ],
                },
                indent=2,
                ensure_ascii=False,
            )
        )
        return 0

    print("# Topic Info\n")
    print("Mode: lexical topic metadata. Not proof.")
    print(f"Record: `{record_ref}` type=`{item.get('record_type')}` status=`{item.get('status')}`")
    print(f"Summary: {item.get('summary', '')}\n")
    print("## Terms")
    for term in item.get("terms", []):
        print(f"- {term.get('term')} score={term.get('score')}")
    print("\n## Similar Records")
    if not similar:
        print("- none")
        return 0
    for shared_count, other_ref, other, shared in similar:
        print(f"- `{other_ref}` type=`{other.get('record_type')}` shared={shared_count}: {', '.join(shared)}")
        print(f"  summary: {other.get('summary', '')}")
    return 0


def cmd_topic_conflict_candidates(root: Path, limit: int, output_format: str) -> int:
    records, exit_code = load_valid_context_readonly(root)
    if exit_code:
        return exit_code
    topic_records = load_topic_records(root)
    if not topic_records:
        print("topic index is missing or empty; run `topic-index build --method lexical` first")
        return 1
    candidates = topic_conflict_candidates(records, topic_records, limit=limit)
    if output_format == "json":
        print(
            json.dumps(
                {
                    "topic_index_is_proof": False,
                    "candidate_count": len(candidates),
                    "candidates": candidates,
                },
                indent=2,
                ensure_ascii=False,
            )
        )
        return 0

    print("# Topic Conflict Candidates\n")
    print("Mode: lexical prefilter. Candidates require normal claim comparison before they become conflicts.\n")
    if not candidates:
        print("- no candidates")
        return 0
    for item in candidates:
        print(
            f"- score={item['score']} `{item['left']['id']}` <-> `{item['right']['id']}` "
            f"shared_terms={', '.join(item['shared_terms'])}"
        )
        print(f"  left: {item['left']['summary']}")
        print(f"  right: {item['right']['summary']}")
    return 0


def load_or_build_topic_payload(root: Path, records: dict[str, dict]) -> dict:
    paths = topic_index_paths(root)
    try:
        if paths["records"].exists() and paths["topics"].exists() and paths["by_topic"].exists() and paths["by_record"].exists():
            payload = {
                "records": json.loads(paths["records"].read_text(encoding="utf-8")),
                "topics": json.loads(paths["topics"].read_text(encoding="utf-8")),
                "by_topic": json.loads(paths["by_topic"].read_text(encoding="utf-8")),
                "by_record": json.loads(paths["by_record"].read_text(encoding="utf-8")),
            }
            if payload["records"] and payload["topics"]:
                return payload
    except (OSError, json.JSONDecodeError):
        pass
    payload = build_lexical_topic_index(records, terms_per_record=8, topic_limit=80)
    candidates = topic_conflict_candidates(records, payload["records"], limit=50)
    write_topic_index_reports(root, payload, candidates)
    return payload


def cmd_tap_record(root: Path, record_ref: str, kind: str, intent: str, note: str) -> int:
    records, exit_code = load_valid_context_readonly(root)
    if exit_code:
        return exit_code
    if record_ref not in records:
        print(f"missing record {record_ref}")
        return 1
    if kind not in TAP_KINDS:
        print(f"invalid tap kind: {kind}")
        return 1
    event = {
        "tapped_at": now_timestamp(),
        "record_ref": record_ref,
        "kind": kind,
        "intent": intent,
        "workspace_ref": current_workspace_ref(root),
        "project_ref": current_project_ref(root),
        "task_ref": current_task_ref(root),
        "note": note,
        "tap_is_proof": False,
    }
    append_tap_event(root, event)
    invalidate_hydration_state(root, "record tap")
    print(f"Recorded tap for {record_ref}: kind={kind} intent={intent}")
    print("Tap activity is navigation data only; it is not proof.")
    return 0


def cmd_telemetry_report(root: Path, limit: int, output_format: str) -> int:
    events, errors = load_access_events(root)
    if errors:
        print_errors(errors)
        return 1
    payload = access_report_payload(events, limit=limit)
    if output_format == "json":
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        for line in access_report_text_lines(payload):
            print(line)
    return 0


def cmd_attention_index_build(root: Path, probe_limit: int) -> int:
    records, exit_code = load_clean_context(root)
    if exit_code:
        return 1
    taps, errors = load_tap_events(root)
    if errors:
        print_errors(errors)
        return 1
    access_events, access_errors = load_access_events(root)
    if access_errors:
        print_errors(access_errors)
        return 1
    topic_payload = load_or_build_topic_payload(root, records)
    payload = build_attention_index(records, topic_payload, taps, access_events=access_events, probe_limit=probe_limit)
    write_attention_index_reports(root, payload)
    invalidate_hydration_state(root, "rebuilt attention index")
    print(
        f"Built attention index: records={payload['record_count']} clusters={payload['cluster_count']} "
        f"taps={payload['tap_count']} access_events={payload['access_event_count']} probes={len(payload['probes'])}"
    )
    print("Attention index is navigation/curiosity data only; it is not proof.")
    return 0


def scoped_attention_payload(root: Path, payload: dict, scope: str, mode: str = "general") -> dict:
    return filter_attention_payload(
        payload,
        scope=scope,
        mode=mode,
        workspace_ref=current_workspace_ref(root),
        project_ref=current_project_ref(root),
        task_ref=current_task_ref(root),
    )


def cmd_attention_map(root: Path, limit: int, output_format: str, scope: str, mode: str) -> int:
    payload = load_attention_payload(root)
    if not payload:
        print("attention index is missing or empty; run `attention-index build` first")
        return 1
    payload = scoped_attention_payload(root, payload, scope, mode)
    if output_format == "json":
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return 0
    print("\n".join(attention_map_text_lines(payload, limit=limit)))
    return 0


def cmd_attention_diagram(root: Path, limit: int, output_format: str, scope: str, detail: str, mode: str) -> int:
    _, exit_code = load_valid_context_readonly(root)
    if exit_code:
        return exit_code
    payload = load_attention_payload(root)
    if not payload:
        print("attention index is missing or empty; run `attention-index build` first")
        return 1
    payload = scoped_attention_payload(root, payload, scope, mode)
    if output_format == "json":
        diagram = attention_diagram_payload(payload, limit=limit, detail=detail)
        mermaid = "\n".join(attention_diagram_mermaid_lines(payload, limit=limit, detail=detail))
        diagram["mermaid"] = mermaid
        diagram["metrics"] = attention_diagram_metrics(diagram, mermaid=mermaid, detail=detail)
        print(json.dumps(diagram, indent=2, ensure_ascii=False))
        return 0
    print("\n".join(attention_diagram_text_lines(payload, limit=limit, detail=detail)))
    return 0


def attention_diagram_compare_payload(scoped_payload: dict, *, limit: int) -> dict:
    compact = attention_diagram_payload(scoped_payload, limit=limit, detail="compact")
    compact_mermaid = "\n".join(attention_diagram_mermaid_lines(scoped_payload, limit=limit, detail="compact"))
    compact_metrics = attention_diagram_metrics(compact, mermaid=compact_mermaid, detail="compact")
    full = attention_diagram_payload(scoped_payload, limit=limit, detail="full")
    full_mermaid = "\n".join(attention_diagram_mermaid_lines(scoped_payload, limit=limit, detail="full"))
    full_metrics = attention_diagram_metrics(full, mermaid=full_mermaid, detail="full")
    delta = {
        "payload_char_count": full_metrics.get("payload_char_count", 0) - compact_metrics.get("payload_char_count", 0),
        "record_summary_count": full_metrics.get("record_count", 0) - compact_metrics.get("record_count", 0),
        "mermaid_char_count": len(full_mermaid) - len(compact_mermaid),
        "omitted_fields_compact": compact_metrics.get("omitted_fields", []),
    }
    return {
        "comparison_is_proof": False,
        "attention_index_is_proof": False,
        "metrics_are_proof": False,
        "scope": scoped_payload.get("scope", "all"),
        "workspace_ref": scoped_payload.get("workspace_ref", ""),
        "project_ref": scoped_payload.get("project_ref", ""),
        "task_ref": scoped_payload.get("task_ref", ""),
        "limit": limit,
        "compact": compact_metrics,
        "full": full_metrics,
        "delta": delta,
        "recommendation": (
            "Use compact first; request full only when record-summary labels are needed "
            "for diagram orientation."
        ),
    }


def attention_diagram_compare_text_lines(payload: dict) -> list[str]:
    compact = payload.get("compact", {})
    full = payload.get("full", {})
    delta = payload.get("delta", {})
    return [
        "# Attention Diagram Detail Comparison",
        "",
        "Mode: mechanical compact/full diagram comparison. Not proof.",
        f"scope: `{payload.get('scope')}` workspace: `{payload.get('workspace_ref', '')}` project: `{payload.get('project_ref', '')}` task: `{payload.get('task_ref', '')}`",
        f"limit: `{payload.get('limit')}` comparison_is_proof=`{payload.get('comparison_is_proof')}` metrics_are_proof=`{payload.get('metrics_are_proof')}`",
        "",
        f"- compact: chars=`{compact.get('payload_char_count', 0)}` records=`{compact.get('record_count', 0)}` omitted=`{', '.join(compact.get('omitted_fields', [])) or 'none'}`",
        f"- full: chars=`{full.get('payload_char_count', 0)}` records=`{full.get('record_count', 0)}` omitted=`{', '.join(full.get('omitted_fields', [])) or 'none'}`",
        f"- delta: chars=`{delta.get('payload_char_count', 0)}` mermaid_chars=`{delta.get('mermaid_char_count', 0)}`",
        "",
        f"Recommendation: {payload.get('recommendation', '')}",
    ]


def cmd_attention_diagram_compare(root: Path, limit: int, output_format: str, scope: str, mode: str) -> int:
    _, exit_code = load_valid_context_readonly(root)
    if exit_code:
        return exit_code
    payload = load_attention_payload(root)
    if not payload:
        print("attention index is missing or empty; run `attention-index build` first")
        return 1
    scoped_payload = scoped_attention_payload(root, payload, scope, mode)
    comparison = attention_diagram_compare_payload(scoped_payload, limit=limit)
    if output_format == "json":
        print(json.dumps(comparison, indent=2, ensure_ascii=False))
        return 0
    print("\n".join(attention_diagram_compare_text_lines(comparison)))
    return 0


def curiosity_map_html_path(root: Path, *, scope: str, mode: str, volume: str) -> Path:
    safe = "-".join(part for part in (scope, mode, volume) if part)
    safe = re.sub(r"[^A-Za-z0-9_.-]+", "-", safe).strip("-") or "current-general-normal"
    return root / "views" / "curiosity" / f"curiosity-map-{safe}.html"


def cmd_curiosity_map(root: Path, volume: str, output_format: str, scope: str, mode: str, html: bool) -> int:
    _, exit_code = load_valid_context_readonly(root)
    if exit_code:
        return exit_code
    payload = load_attention_payload(root)
    if not payload:
        print("attention index is missing or empty; run `attention-index build` first")
        return 1
    scoped_payload = scoped_attention_payload(root, payload, scope, mode)
    map_payload = curiosity_map_payload(scoped_payload, volume=volume)
    if html:
        output_path = curiosity_map_html_path(root, scope=scope, mode=mode, volume=volume)
        write_text_file(output_path, curiosity_map_html(map_payload))
        map_payload["html_path"] = str(output_path)
    if output_format == "json":
        print(json.dumps(map_payload, indent=2, ensure_ascii=False))
        return 0
    if html:
        print(f"Wrote curiosity HTML map: {output_path}")
    print("\n".join(curiosity_map_text_lines(map_payload)))
    return 0


def cmd_map_brief(root: Path, volume: str, output_format: str, scope: str, mode: str, limit: int) -> int:
    _, exit_code = load_valid_context_readonly(root)
    if exit_code:
        return exit_code
    payload = load_attention_payload(root)
    if not payload:
        print("attention index is missing or empty; run `attention-index build` first")
        return 1
    scoped_payload = scoped_attention_payload(root, payload, scope, mode)
    map_payload = curiosity_map_payload(scoped_payload, volume=volume)
    brief = map_brief_payload(map_payload, limit=limit)
    if output_format == "json":
        print(json.dumps(brief, indent=2, ensure_ascii=False))
        return 0
    print("\n".join(map_brief_text_lines(brief)))
    return 0


def cmd_curiosity_probes(root: Path, budget: int, output_format: str, scope: str, mode: str) -> int:
    payload = load_attention_payload(root)
    if not payload:
        print("attention index is missing or empty; run `attention-index build` first")
        return 1
    payload = scoped_attention_payload(root, payload, scope, mode)
    limited_payload = {**payload, "probes": payload.get("probes", [])[: max(1, budget)]}
    if output_format == "json":
        print(
            json.dumps(
                {
                    "attention_index_is_proof": False,
                    "scope": limited_payload.get("scope", scope),
                    "mode": limited_payload.get("mode", mode),
                    "workspace_ref": limited_payload.get("workspace_ref", ""),
                    "project_ref": limited_payload.get("project_ref", ""),
                    "task_ref": limited_payload.get("task_ref", ""),
                    "budget": budget,
                    "probes": limited_payload["probes"],
                },
                indent=2,
                ensure_ascii=False,
            )
        )
        return 0
    print("\n".join(curiosity_probe_text_lines(limited_payload, limit=budget)))
    return 0


def direct_probe_edges(records: dict[str, dict], record_refs: list[str]) -> list[dict]:
    wanted = {tuple(sorted([left, right])) for left in record_refs for right in record_refs if left < right}
    return [
        edge
        for edge in collect_link_edges(records)
        if tuple(sorted([str(edge.get("from", "")), str(edge.get("to", ""))])) in wanted
    ]


def probe_inspect_text_lines(payload: dict) -> list[str]:
    probe = payload["probe"]
    refs = probe.get("record_refs", [])
    lines = [
        "# Curiosity Probe Inspection",
        "",
        "Mode: mechanical navigation context. Not proof.",
        f"scope: `{payload.get('scope')}` mode: `{payload.get('mode', 'general')}` workspace: `{payload.get('workspace_ref', '')}` project: `{payload.get('project_ref', '')}` task: `{payload.get('task_ref', '')}`",
        f"probe_index: `{payload.get('probe_index')}` score: `{probe.get('score', 0)}` score_is_proof=`{probe.get('score_is_proof', False)}`",
        f"record_refs: {', '.join(f'`{ref}`' for ref in refs)}",
        f"reason: {probe.get('reason', '')}",
        "",
        "## Direct Link Status",
    ]
    if payload["direct_edges"]:
        for edge in payload["direct_edges"]:
            lines.append(f"- established `{edge['from']}` -> `{edge['to']}` via `{', '.join(edge.get('fields', []))}`")
    else:
        lines.append("- no direct canonical link found between probe records")
    lines.extend(["", "## Records"])
    for detail in payload["record_details"]:
        summary = detail["summary"]
        lines.append(
            f"- `{summary.get('id')}` type=`{summary.get('record_type')}` status=`{summary.get('status')}`: {summary.get('summary')}"
        )
        for source in detail.get("source_quotes", [])[:2]:
            quote = concise(str(source.get("quote", "")), 160)
            lines.append(f"  source `{source.get('id')}` kind=`{source.get('source_kind')}` critique=`{source.get('critique_status')}`: {quote}")
    lines.extend(["", "## Suggested Follow-Up"])
    for command in payload["suggested_commands"]:
        lines.append(f"- `{command}`")
    lines.append("")
    lines.append("Do not cite this inspection as proof; cite canonical `SRC-*` / `CLM-*` records after inspection.")
    return lines


def probe_record_chain_role(record: dict) -> str:
    record_type = str(record.get("record_type", "")).strip()
    if record_type == "claim":
        if str(record.get("status", "")).strip() == "tentative":
            return "hypothesis"
        return "fact"
    return {
        "model": "model",
        "flow": "flow",
        "open_question": "open_question",
        "proposal": "proposal",
        "task": "task",
        "working_context": "working_context",
        "project": "project",
        "guideline": "guideline",
        "permission": "permission",
        "restriction": "restriction",
    }.get(record_type, "exploration_context")


def probe_record_chain_quote(record: dict) -> str:
    for key in ("statement", "summary", "question", "position", "title", "subject", "rule", "note"):
        value = str(record.get(key, "")).strip()
        if value:
            return value
    return record_summary(record)


def build_probe_chain_draft_payload(root: Path, records: dict[str, dict], scoped_payload: dict, probe_index: int) -> dict:
    probes = scoped_payload.get("probes", [])
    index = max(1, probe_index) - 1
    if not probes:
        raise ValueError("no curiosity probes available for this scope")
    if index >= len(probes):
        raise ValueError(f"probe index out of range: {probe_index}; available={len(probes)}")
    probe = probes[index]
    record_refs = [str(ref) for ref in probe.get("record_refs", []) if str(ref) in records]
    nodes = [
        {
            "role": probe_record_chain_role(records[record_ref]),
            "ref": record_ref,
            "quote": probe_record_chain_quote(records[record_ref]),
        }
        for record_ref in record_refs
    ]
    edges = [
        {
            "from": record_refs[0],
            "to": record_refs[1],
            "relation": "candidate_relation_to_inspect",
        }
    ] if len(record_refs) >= 2 else []
    chain = {
        "task": "Inspect whether selected curiosity-probe records should be linked",
        "draft_is_proof": False,
        "attention_index_is_proof": False,
        "probe_index": probe_index,
        "probe": probe,
        "scope": scoped_payload.get("scope", ""),
        "mode": scoped_payload.get("mode", "general"),
        "workspace_ref": scoped_payload.get("workspace_ref", ""),
        "project_ref": scoped_payload.get("project_ref", ""),
        "task_ref": scoped_payload.get("task_ref", ""),
        "nodes": nodes,
        "edges": edges,
        "notes": [
            "This is a mechanical draft for inspection, not proof.",
            "Validate and augment before presenting it as an evidence chain.",
            "Do not treat the curiosity probe score or explanation as support.",
        ],
    }
    hypothesis_entries = active_hypothesis_entry_by_claim(root, records)
    augmented = augment_evidence_chain_payload(records, hypothesis_entries, chain)
    return {
        "draft_is_proof": False,
        "attention_index_is_proof": False,
        "inspection_is_proof": False,
        "chain": chain,
        "augmented": augmented,
    }


def build_probe_inspection_payload(records: dict[str, dict], scoped_payload: dict, probe_index: int) -> dict:
    probes = scoped_payload.get("probes", [])
    index = max(1, probe_index) - 1
    if not probes:
        raise ValueError("no curiosity probes available for this scope")
    if index >= len(probes):
        raise ValueError(f"probe index out of range: {probe_index}; available={len(probes)}")
    probe = probes[index]
    record_refs = [str(ref) for ref in probe.get("record_refs", []) if str(ref) in records]
    return {
        "attention_index_is_proof": False,
        "inspection_is_proof": False,
        "scope": scoped_payload.get("scope", ""),
        "mode": scoped_payload.get("mode", "general"),
        "workspace_ref": scoped_payload.get("workspace_ref", ""),
        "project_ref": scoped_payload.get("project_ref", ""),
        "task_ref": scoped_payload.get("task_ref", ""),
        "probe_index": probe_index,
        "probe": probe,
        "direct_edges": direct_probe_edges(records, record_refs),
        "record_details": [record_detail_payload(records, record_ref) for record_ref in record_refs],
        "suggested_commands": [
            *(f"record-detail --record {record_ref}" for record_ref in record_refs),
            *(f"linked-records --record {record_ref} --depth 1" for record_ref in record_refs),
            "build-reasoning-case --task \"inspect whether the probed records should be linked\"",
        ],
    }


def probe_chain_draft_text_lines(payload: dict) -> list[str]:
    validation = payload["augmented"]["validation"]
    chain = payload["chain"]
    lines = [
        "# Probe Evidence-Chain Draft",
        "",
        "Mode: mechanical draft. Draft is not proof.",
        f"probe_index: `{chain.get('probe_index')}` draft_is_proof=`{payload.get('draft_is_proof')}`",
        f"validation_ok: `{validation.get('ok')}` errors=`{validation.get('error_count')}` warnings=`{validation.get('warning_count')}`",
        "",
        "## Nodes",
    ]
    for node in chain.get("nodes", []):
        lines.append(f"- `{node.get('ref')}` role=`{node.get('role')}` quote=\"{concise(str(node.get('quote', '')), 180)}\"")
    lines.extend(["", "## Edges"])
    for edge in chain.get("edges", []):
        lines.append(f"- `{edge.get('from')}` -> `{edge.get('to')}` relation=`{edge.get('relation')}`")
    if not chain.get("edges"):
        lines.append("- none")
    lines.extend(["", "## Required Next Step"])
    lines.append("- Run `augment-chain` / `validate-evidence-chain` on this draft before user-facing proof.")
    lines.append("- If the draft is used for a conclusion, cite canonical source-backed records, not the probe.")
    return lines


def cmd_probe_inspect(root: Path, probe_index: int, output_format: str, scope: str, mode: str) -> int:
    records, exit_code = load_valid_context_readonly(root)
    if exit_code:
        return exit_code
    attention_payload = load_attention_payload(root)
    if not attention_payload:
        print("attention index is missing or empty; run `attention-index build` first")
        return 1
    scoped_payload = scoped_attention_payload(root, attention_payload, scope, mode)
    try:
        payload = build_probe_inspection_payload(records, scoped_payload, probe_index)
    except ValueError as exc:
        print(str(exc))
        return 1
    if output_format == "json":
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return 0
    print("\n".join(probe_inspect_text_lines(payload)))
    return 0


def probe_pack_text_lines(payload: dict) -> list[str]:
    metrics = payload.get("metrics", {})
    lines = [
        "# Curiosity Reasoning Pack",
        "",
        "Mode: compact mechanical pack. Not proof.",
        f"scope: `{payload.get('scope')}` mode: `{payload.get('mode', 'general')}` workspace: `{payload.get('workspace_ref', '')}` project: `{payload.get('project_ref', '')}` task: `{payload.get('task_ref', '')}`",
        f"budget: `{payload.get('budget')}` detail: `{payload.get('detail', 'compact')}` pack_is_proof=`{payload.get('pack_is_proof')}`",
        f"metrics: returned=`{metrics.get('returned_items', 0)}` available=`{metrics.get('available_probes', 0)}` records=`{metrics.get('record_summary_count', 0)}` omitted=`{', '.join(metrics.get('omitted_fields', [])) or 'none'}` payload_chars=`{metrics.get('payload_char_count', 0)}`",
        "",
    ]
    for item in payload.get("items", []):
        probe = item["probe"]
        validation = item["chain_validation"]
        refs = ", ".join(f"`{ref}`" for ref in probe.get("record_refs", []))
        lines.append(
            f"- probe `{item['probe_index']}` score=`{probe.get('score', 0)}` validation_ok=`{validation.get('ok')}` refs={refs}"
        )
        lines.append(f"  reason: {probe.get('reason', '')}")
        if item.get("direct_edges"):
            lines.append(f"  direct_links: `{len(item['direct_edges'])}`")
        else:
            lines.append("  direct_links: `0`")
        for record in item.get("records", []):
            lines.append(
                f"  record `{record.get('id')}` type=`{record.get('record_type')}` status=`{record.get('status')}`: {record.get('summary')}"
            )
    if not payload.get("items"):
        lines.append("- none")
    lines.extend(["", "Do not cite this pack as proof; cite canonical source-backed records after inspection."])
    return lines


def probe_pack_metrics(payload: dict, available_probes: int, detail: str) -> dict:
    items = payload.get("items", [])
    source_quote_count = 0
    chain_node_count = 0
    for item in items:
        for quotes in item.get("source_quotes", {}).values():
            if isinstance(quotes, list):
                source_quote_count += len(quotes)
        chain = item.get("chain", {})
        if isinstance(chain, dict):
            nodes = chain.get("nodes", [])
            if isinstance(nodes, list):
                chain_node_count += len(nodes)
    omitted_fields = [] if detail == "full" else ["source_quotes", "chain"]
    metrics = {
        "detail": detail,
        "available_probes": available_probes,
        "returned_items": len(items),
        "record_summary_count": sum(len(item.get("records", [])) for item in items),
        "direct_edge_count": sum(len(item.get("direct_edges", [])) for item in items),
        "source_quote_count": source_quote_count,
        "chain_node_count": chain_node_count,
        "omitted_fields": omitted_fields,
        "metrics_are_proof": False,
    }
    payload_without_metrics = {key: value for key, value in payload.items() if key != "metrics"}
    metrics["payload_char_count"] = len(json.dumps(payload_without_metrics, ensure_ascii=False, sort_keys=True))
    return metrics


def build_probe_pack_payload(root: Path, records: dict, scoped_payload: dict, budget: int, detail: str) -> dict:
    probes = scoped_payload.get("probes", [])
    items = []
    for probe_index in range(1, min(max(1, budget), len(probes)) + 1):
        inspection = build_probe_inspection_payload(records, scoped_payload, probe_index)
        draft = build_probe_chain_draft_payload(root, records, scoped_payload, probe_index)
        item = {
            "probe_index": probe_index,
            "probe": inspection["probe"],
            "direct_edges": inspection["direct_edges"],
            "records": [record_detail["summary"] for record_detail in inspection["record_details"]],
            "chain_validation": draft["augmented"]["validation"],
        }
        if detail == "full":
            item["source_quotes"] = {
                record_detail["summary"]["id"]: record_detail.get("source_quotes", [])[:2]
                for record_detail in inspection["record_details"]
            }
            item["chain"] = draft["chain"]
        items.append(item)
    payload = {
        "pack_is_proof": False,
        "attention_index_is_proof": False,
        "inspection_is_proof": False,
        "draft_is_proof": False,
        "scope": scoped_payload.get("scope", ""),
        "mode": scoped_payload.get("mode", "general"),
        "workspace_ref": scoped_payload.get("workspace_ref", ""),
        "project_ref": scoped_payload.get("project_ref", ""),
        "task_ref": scoped_payload.get("task_ref", ""),
        "budget": budget,
        "detail": detail,
        "items": items,
    }
    payload["metrics"] = probe_pack_metrics(payload, len(probes), detail)
    return payload


def probe_pack_compare_payload(compact_payload: dict, full_payload: dict) -> dict:
    compact_metrics = compact_payload.get("metrics", {})
    full_metrics = full_payload.get("metrics", {})
    delta = {
        "payload_char_count": full_metrics.get("payload_char_count", 0) - compact_metrics.get("payload_char_count", 0),
        "source_quote_count": full_metrics.get("source_quote_count", 0) - compact_metrics.get("source_quote_count", 0),
        "chain_node_count": full_metrics.get("chain_node_count", 0) - compact_metrics.get("chain_node_count", 0),
        "record_summary_count": full_metrics.get("record_summary_count", 0) - compact_metrics.get("record_summary_count", 0),
        "omitted_fields_compact": compact_metrics.get("omitted_fields", []),
    }
    return {
        "comparison_is_proof": False,
        "attention_index_is_proof": False,
        "metrics_are_proof": False,
        "scope": compact_payload.get("scope", ""),
        "workspace_ref": compact_payload.get("workspace_ref", ""),
        "project_ref": compact_payload.get("project_ref", ""),
        "task_ref": compact_payload.get("task_ref", ""),
        "mode": compact_payload.get("mode", "general"),
        "budget": compact_payload.get("budget", 0),
        "compact": compact_metrics,
        "full": full_metrics,
        "delta": delta,
        "recommendation": (
            "Use compact first; request full only when selected probes need source quotes "
            "or full chain payload for follow-up inspection."
        ),
    }


def probe_pack_compare_text_lines(payload: dict) -> list[str]:
    compact = payload.get("compact", {})
    full = payload.get("full", {})
    delta = payload.get("delta", {})
    lines = [
        "# Probe Pack Detail Comparison",
        "",
        "Mode: mechanical compact/full comparison. Not proof.",
        f"scope: `{payload.get('scope')}` mode: `{payload.get('mode', 'general')}` workspace: `{payload.get('workspace_ref', '')}` project: `{payload.get('project_ref', '')}` task: `{payload.get('task_ref', '')}`",
        f"budget: `{payload.get('budget')}` comparison_is_proof=`{payload.get('comparison_is_proof')}` metrics_are_proof=`{payload.get('metrics_are_proof')}`",
        "",
        f"- compact: chars=`{compact.get('payload_char_count', 0)}` quotes=`{compact.get('source_quote_count', 0)}` chain_nodes=`{compact.get('chain_node_count', 0)}` omitted=`{', '.join(compact.get('omitted_fields', [])) or 'none'}`",
        f"- full: chars=`{full.get('payload_char_count', 0)}` quotes=`{full.get('source_quote_count', 0)}` chain_nodes=`{full.get('chain_node_count', 0)}` omitted=`{', '.join(full.get('omitted_fields', [])) or 'none'}`",
        f"- delta: chars=`{delta.get('payload_char_count', 0)}` quotes=`{delta.get('source_quote_count', 0)}` chain_nodes=`{delta.get('chain_node_count', 0)}`",
        "",
        f"Recommendation: {payload.get('recommendation', '')}",
    ]
    return lines


def cmd_probe_pack(root: Path, budget: int, output_format: str, scope: str, detail: str, mode: str) -> int:
    records, exit_code = load_valid_context_readonly(root)
    if exit_code:
        return exit_code
    attention_payload = load_attention_payload(root)
    if not attention_payload:
        print("attention index is missing or empty; run `attention-index build` first")
        return 1
    scoped_payload = scoped_attention_payload(root, attention_payload, scope, mode)
    payload = build_probe_pack_payload(root, records, scoped_payload, budget, detail)
    if output_format == "json":
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return 0
    print("\n".join(probe_pack_text_lines(payload)))
    return 0


def cmd_probe_pack_compare(root: Path, budget: int, output_format: str, scope: str, mode: str) -> int:
    records, exit_code = load_valid_context_readonly(root)
    if exit_code:
        return exit_code
    attention_payload = load_attention_payload(root)
    if not attention_payload:
        print("attention index is missing or empty; run `attention-index build` first")
        return 1
    scoped_payload = scoped_attention_payload(root, attention_payload, scope, mode)
    compact_payload = build_probe_pack_payload(root, records, scoped_payload, budget, "compact")
    full_payload = build_probe_pack_payload(root, records, scoped_payload, budget, "full")
    payload = probe_pack_compare_payload(compact_payload, full_payload)
    if output_format == "json":
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return 0
    print("\n".join(probe_pack_compare_text_lines(payload)))
    return 0


def build_probe_route_payload(root: Path, records: dict, scoped_payload: dict, probe_index: int) -> dict:
    inspection = build_probe_inspection_payload(records, scoped_payload, probe_index)
    draft = build_probe_chain_draft_payload(root, records, scoped_payload, probe_index)
    compact_pack = build_probe_pack_payload(root, records, scoped_payload, max(1, probe_index), "compact")
    full_pack = build_probe_pack_payload(root, records, scoped_payload, max(1, probe_index), "full")
    comparison = probe_pack_compare_payload(compact_pack, full_pack)
    diagram_comparison = attention_diagram_compare_payload(scoped_payload, limit=8)
    scope = scoped_payload.get("scope", "current")
    mode = scoped_payload.get("mode", "general")
    probe = inspection["probe"]
    refs = [str(ref) for ref in probe.get("record_refs", [])]
    commands = [
        f"attention-diagram --scope {scope} --mode {mode} --limit 8 --detail compact",
        f"attention-diagram-compare --scope {scope} --mode {mode} --limit 8",
        f"probe-inspect --index {probe_index} --scope {scope} --mode {mode}",
        f"probe-chain-draft --index {probe_index} --scope {scope} --mode {mode} --format json",
        f"probe-pack-compare --budget {max(1, probe_index)} --scope {scope} --mode {mode}",
        *(f"record-detail --record {record_ref}" for record_ref in refs),
        *(f"linked-records --record {record_ref} --depth 1" for record_ref in refs),
        'build-reasoning-case --task "inspect whether the probed records should be linked"',
    ]
    if len(refs) == 2:
        commands.append(
            f'record-link --probe-index {probe_index} --probe-scope {scope} --mode {mode} '
            f'--scope {scope} '
            '--relation related --quote "<canonical inspection quote>" --note "<why this reviewed link should be persisted>"'
        )
    if diagram_comparison["delta"].get("payload_char_count", 0) > 0:
        commands.append(f"attention-diagram --scope {scope} --mode {mode} --limit 8 --detail full")
    if comparison["delta"].get("source_quote_count", 0) > 0:
        commands.append(f"probe-pack --budget {max(1, probe_index)} --scope {scope} --mode {mode} --detail full")
    return {
        "route_is_proof": False,
        "attention_index_is_proof": False,
        "inspection_is_proof": False,
        "draft_is_proof": False,
        "comparison_is_proof": False,
        "scope": scope,
        "mode": mode,
        "workspace_ref": scoped_payload.get("workspace_ref", ""),
        "project_ref": scoped_payload.get("project_ref", ""),
        "task_ref": scoped_payload.get("task_ref", ""),
        "probe_index": probe_index,
        "probe": probe,
        "record_refs": refs,
        "direct_link_count": len(inspection["direct_edges"]),
        "chain_validation": draft["augmented"]["validation"],
        "diagram_delta": diagram_comparison["delta"],
        "context_delta": comparison["delta"],
        "recommended_commands": commands,
        "next_steps": [
            "Inspect canonical record details and direct links before making a claim.",
            "Use the draft chain only as a mechanical skeleton; validate/augment before user-facing proof.",
            "If support exists, persist it with record-link; otherwise record an open question or leave the probe unresolved.",
        ],
        "note": "Generated inspection route. Navigation only; not proof.",
    }


def probe_route_text_lines(payload: dict) -> list[str]:
    probe = payload.get("probe", {})
    diagram_delta = payload.get("diagram_delta", {})
    delta = payload.get("context_delta", {})
    validation = payload.get("chain_validation", {})
    lines = [
        "# Probe Inspection Route",
        "",
        "Mode: generated route for bounded probe inspection. Not proof.",
        f"scope: `{payload.get('scope')}` mode: `{payload.get('mode', 'general')}` workspace: `{payload.get('workspace_ref', '')}` project: `{payload.get('project_ref', '')}` task: `{payload.get('task_ref', '')}`",
        f"probe_index: `{payload.get('probe_index')}` route_is_proof=`{payload.get('route_is_proof')}` score=`{probe.get('score', 0)}` score_is_proof=`{probe.get('score_is_proof', False)}`",
        f"record_refs: {', '.join(f'`{ref}`' for ref in payload.get('record_refs', []))}",
        f"direct_links: `{payload.get('direct_link_count', 0)}` chain_validation_ok: `{validation.get('ok')}`",
        f"diagram_delta_if_full: chars=`{diagram_delta.get('payload_char_count', 0)}` mermaid_chars=`{diagram_delta.get('mermaid_char_count', 0)}`",
        f"context_delta_if_full: chars=`{delta.get('payload_char_count', 0)}` quotes=`{delta.get('source_quote_count', 0)}` chain_nodes=`{delta.get('chain_node_count', 0)}`",
        "",
        "## Recommended Commands",
    ]
    for command in payload.get("recommended_commands", []):
        lines.append(f"- `{command}`")
    lines.extend(["", "## Next Steps"])
    for step in payload.get("next_steps", []):
        lines.append(f"- {step}")
    lines.append("")
    lines.append("Do not cite this route as proof; cite canonical source-backed records after inspection.")
    return lines


def cmd_probe_route(root: Path, probe_index: int, output_format: str, scope: str, mode: str) -> int:
    records, exit_code = load_valid_context_readonly(root)
    if exit_code:
        return exit_code
    attention_payload = load_attention_payload(root)
    if not attention_payload:
        print("attention index is missing or empty; run `attention-index build` first")
        return 1
    scoped_payload = scoped_attention_payload(root, attention_payload, scope, mode)
    try:
        payload = build_probe_route_payload(root, records, scoped_payload, probe_index)
    except ValueError as exc:
        print(str(exc))
        return 1
    if output_format == "json":
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return 0
    print("\n".join(probe_route_text_lines(payload)))
    return 0


def cmd_probe_chain_draft(root: Path, probe_index: int, output_format: str, scope: str, mode: str) -> int:
    records, exit_code = load_valid_context_readonly(root)
    if exit_code:
        return exit_code
    attention_payload = load_attention_payload(root)
    if not attention_payload:
        print("attention index is missing or empty; run `attention-index build` first")
        return 1
    scoped_payload = scoped_attention_payload(root, attention_payload, scope, mode)
    try:
        payload = build_probe_chain_draft_payload(root, records, scoped_payload, probe_index)
    except ValueError as exc:
        print(str(exc))
        return 1
    if output_format == "json":
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return 0
    print("\n".join(probe_chain_draft_text_lines(payload)))
    return 0


def cmd_logic_index_build(root: Path, candidate_limit: int) -> int:
    records, exit_code = load_clean_context(root)
    if exit_code:
        return 1
    payload = build_logic_index_payload(records)
    candidates = logic_conflict_candidates_from_payload(payload, limit=candidate_limit)
    write_logic_index_reports(root, payload, candidates)
    invalidate_hydration_state(root, "rebuilt logic index")
    print(
        f"Built logic index: atoms={len(payload['atoms'])} symbols={len(payload['symbols'])} "
        f"rules={len(payload['rules'])} candidates={len(candidates)}"
    )
    print("Logic index is generated checking/navigation data only; CLM-* remains the truth record.")
    return 0


def cmd_logic_graph(
    root: Path,
    symbol: str | None,
    predicate: str | None,
    smells_only: bool,
    limit: int,
    output_format: str,
) -> int:
    records, exit_code = load_valid_context_readonly(root)
    if exit_code:
        return exit_code
    del records
    graph = load_logic_vocabulary_graph(root)
    if not graph:
        print("logic vocabulary graph is missing; run `logic-index build` first")
        return 1

    symbols = graph.get("symbols", {}) if isinstance(graph.get("symbols", {}), dict) else {}
    predicates = graph.get("predicates", {}) if isinstance(graph.get("predicates", {}), dict) else {}
    smells = graph.get("smells", []) if isinstance(graph.get("smells", []), list) else []
    if symbol:
        symbols = {symbol: symbols[symbol]} if symbol in symbols else {}
        smells = [
            item
            for item in smells
            if item.get("symbol") == symbol or symbol in item.get("symbols", []) or symbol in json.dumps(item, ensure_ascii=False)
        ]
    if predicate:
        predicates = {predicate: predicates[predicate]} if predicate in predicates else {}
        smells = [item for item in smells if item.get("predicate") == predicate or predicate in json.dumps(item, ensure_ascii=False)]
    if smells_only:
        symbols = {}
        predicates = {}

    if output_format == "json":
        print(
            json.dumps(
                {
                    "logic_graph_is_proof": False,
                    "symbols": symbols,
                    "predicates": predicates,
                    "rules": graph.get("rules", {}),
                    "components": graph.get("components", [])[: max(1, limit)],
                    "smells": smells[: max(1, limit)],
                },
                indent=2,
                ensure_ascii=False,
            )
        )
        return 0

    print(f"# {TEP_ICON} Logic Vocabulary Graph\n")
    print("Mode: generated vocabulary pressure graph. Not proof.\n")
    if not smells_only:
        print("## Symbols")
        if not symbols:
            print("- none")
        for _, item in sorted(symbols.items())[: max(1, limit)]:
            meanings = "; ".join(item.get("meanings", []))
            print(
                f"- `{item.get('symbol')}` kind=`{item.get('kind')}` uses={item.get('use_count')} "
                f"defs={item.get('definition_count')} meaning=\"{concise(meanings, 180)}\""
            )
        print("\n## Predicates")
        if not predicates:
            print("- none")
        for _, item in sorted(predicates.items())[: max(1, limit)]:
            ref_count = len(item.get("atom_refs", [])) + len(item.get("rule_refs", []))
            print(f"- `{item.get('predicate')}` refs={ref_count} claims={item.get('claim_refs', [])}")
    print("\n## Smells")
    if not smells:
        print("- none")
    for smell in smells[: max(1, limit)]:
        target = smell.get("symbol") or smell.get("predicate") or smell.get("rule_ref") or ",".join(smell.get("symbols", []))
        print(f"- `{smell.get('kind')}` severity=`{smell.get('severity')}` target=`{target}`: {smell.get('message')}")
    return 0


def cmd_logic_search(
    root: Path,
    predicate: str | None,
    symbol: str | None,
    claim_ref: str | None,
    limit: int,
    output_format: str,
) -> int:
    records, exit_code = load_valid_context_readonly(root)
    if exit_code:
        return exit_code
    payload = load_logic_index_payload(root)
    atoms = payload.get("atoms", [])
    rules = payload.get("rules", [])
    if not atoms and not rules:
        print("logic index is missing or empty; run `logic-index build` first")
        return 1

    matched_atoms = []
    for atom in atoms if isinstance(atoms, list) else []:
        if not isinstance(atom, dict):
            continue
        if predicate and str(atom.get("predicate", "")).strip() != predicate:
            continue
        if symbol and symbol not in [str(arg).strip() for arg in atom.get("args", [])]:
            continue
        if claim_ref and str(atom.get("claim_ref", "")).strip() != claim_ref:
            continue
        matched_atoms.append(atom)
    matched_rules = []
    for rule in rules if isinstance(rules, list) else []:
        if not isinstance(rule, dict):
            continue
        if claim_ref and str(rule.get("claim_ref", "")).strip() != claim_ref:
            continue
        if predicate:
            head = rule.get("head", {}) if isinstance(rule.get("head", {}), dict) else {}
            body = rule.get("body", []) if isinstance(rule.get("body", []), list) else []
            predicates = [str(head.get("predicate", "")).strip()]
            predicates.extend(str(atom.get("predicate", "")).strip() for atom in body if isinstance(atom, dict))
            if predicate not in predicates:
                continue
        if symbol and symbol not in json.dumps(rule, ensure_ascii=False):
            continue
        matched_rules.append(rule)
    matched_atoms = matched_atoms[: max(1, limit)]
    matched_rules = matched_rules[: max(1, limit)]

    if output_format == "json":
        print(
            json.dumps(
                {
                    "logic_index_is_proof": False,
                    "atoms": matched_atoms,
                    "rules": matched_rules,
                },
                indent=2,
                ensure_ascii=False,
            )
        )
        return 0

    print(f"# {TEP_ICON} Logic Search\n")
    print("Mode: generated predicate index. Not proof.\n")
    print("## Atoms")
    if not matched_atoms:
        print("- none")
    for atom in matched_atoms:
        value = f" value={atom.get('value')!r}" if "value" in atom else ""
        print(
            f"- `{atom.get('claim_ref')}` {atom.get('predicate')}({', '.join(atom.get('args', []))}) "
            f"polarity=`{atom.get('polarity')}`{value}"
        )
    print("\n## Rules")
    if not matched_rules:
        print("- none")
    for rule in matched_rules:
        print(f"- `{rule.get('claim_ref')}` rule=`{rule.get('name')}`")
    return 0


def cmd_logic_check(root: Path, limit: int, output_format: str, solver: str | None, closure: str) -> int:
    records, exit_code = load_valid_context_readonly(root)
    if exit_code:
        return exit_code
    payload = build_logic_index_payload(records)
    candidates = logic_conflict_candidates_from_payload(payload, limit=limit)
    selected_solver = effective_logic_solver(root, solver)
    solver_policy = logic_solver_settings(root)
    if selected_solver in {"z3", "auto"}:
        z3_result = analyze_logic_payload_with_z3(
            payload,
            limit=limit,
            closure=closure,
            timeout_ms=int(solver_policy.get("timeout_ms", 2000)),
            max_rules=int(solver_policy.get("max_rules", 100)),
            max_symbols=int(solver_policy.get("max_symbols", 500)),
            use_unsat_core=bool(solver_policy.get("use_unsat_core", True)),
        )
        if not z3_result.get("available"):
            if selected_solver == "z3" and str(solver_policy.get("missing_dependency", "warn")) == "error":
                if output_format == "json":
                    print(json.dumps(z3_result, indent=2, ensure_ascii=False))
                else:
                    for line in z3_logic_check_text_lines(z3_result, candidates, TEP_ICON):
                        print(line)
                return 1
            if selected_solver == "z3":
                if output_format == "json":
                    print(json.dumps(z3_result, indent=2, ensure_ascii=False))
                else:
                    for line in z3_logic_check_text_lines(z3_result, candidates, TEP_ICON):
                        print(line)
                return 0
        else:
            if output_format == "json":
                print(json.dumps(z3_result, indent=2, ensure_ascii=False))
            else:
                for line in z3_logic_check_text_lines(z3_result, candidates, TEP_ICON):
                    print(line)
            return 0

    if output_format == "json":
        print(json.dumps(structural_logic_check_payload(payload, candidates, selected_solver), indent=2, ensure_ascii=False))
        return 0
    for line in structural_logic_check_text_lines(payload, candidates, selected_solver, TEP_ICON):
        print(line)
    return 0


def cmd_logic_conflict_candidates(root: Path, limit: int, output_format: str) -> int:
    records, exit_code = load_valid_context_readonly(root)
    if exit_code:
        return exit_code
    payload = build_logic_index_payload(records)
    candidates = logic_conflict_candidates_from_payload(payload, limit=limit)
    if output_format == "json":
        print(json.dumps({"logic_index_is_proof": False, "candidates": candidates}, indent=2, ensure_ascii=False))
        return 0
    print(f"# {TEP_ICON} Logic Conflict Candidates\n")
    print("Mode: predicate-level prefilter. Candidates are not proof.\n")
    if not candidates:
        print("- no candidates")
        return 0
    for item in candidates:
        print(
            f"- `{item['predicate']}`({', '.join(item['args'])}) "
            f"`{item['left']['claim_ref']}` <-> `{item['right']['claim_ref']}`: {item['reason']}"
        )
    return 0


def cmd_search_records(
    root: Path,
    query: str,
    limit: int,
    record_types: list[str],
    all_projects: bool,
    include_task_local: bool,
    include_fallback: bool,
    include_archived: bool,
    output_format: str,
) -> int:
    records, exit_code = load_valid_context_readonly(root)
    if exit_code:
        return exit_code
    terms = task_terms(query)
    if not terms:
        print("search query must contain at least one searchable token with 3+ characters")
        return 1

    project_ref = None if all_projects else current_project_ref(root) or None
    task_ref = None if include_task_local else current_task_ref(root) or None
    ranked = ranked_record_search(
        records,
        terms,
        limit,
        record_types,
        project_ref,
        task_ref,
        include_fallback,
        include_archived,
    )
    append_lookup_access_event(
        root,
        channel="cli",
        tool="search-records",
        access_kind="record_search",
        record_refs=[str(item["record"].get("id") or "") for item in ranked],
        query=query,
        note="keyword record search",
    )

    if output_format == "json":
        print(
            json.dumps(
                {
                    "query": query,
                    "terms": sorted(terms),
                    "project_filter": project_ref or None,
                    "task_filter": task_ref or None,
                    "results": [
                        {
                            "score": item["score"],
                            "matched_terms": item["matched_terms"],
                            **public_record_summary(item["record"]),
                        }
                        for item in ranked
                    ],
                },
                indent=2,
                ensure_ascii=False,
            )
        )
        return 0

    print("# Record Search\n")
    print(f"Query: {query}")
    print(f"Terms: {', '.join(sorted(terms))}")
    if project_ref:
        print(f"Project filter: `{project_ref}`")
    if task_ref:
        print(f"Task filter: `{task_ref}`")
    if include_fallback:
        print("Includes fallback historical claims.")
    if include_archived:
        print("Includes archived explicit-only claims.")
    print()
    if not ranked:
        print("- no matching records")
        return 0
    for item in ranked:
        score = item["score"]
        data = item["record"]
        matched = item["matched_terms"]
        lifecycle = ""
        if data.get("record_type") == "claim":
            state = claim_lifecycle_state(data)
            attention = claim_attention(data)
            if state != "active" or attention != "normal":
                lifecycle = f" lifecycle=`{state}` attention=`{attention}`"
        print(
            f"- `{data.get('id')}` type=`{data.get('record_type')}` "
            f"status=`{data.get('status', data.get('critique_status', ''))}` score={score}{lifecycle}"
        )
        print(f"  matched: {', '.join(matched)}")
        print(f"  summary: {record_summary(data)}")
    return 0


def append_lookup_access_event(
    root: Path,
    *,
    channel: str,
    tool: str,
    access_kind: str,
    record_refs: list[str] | None = None,
    query: str = "",
    reason: str = "",
    working_context_ref: str = "",
    raw_path_count: int = 0,
    note: str = "",
) -> None:
    channel = os.environ.get("TEP_ACCESS_CHANNEL", "").strip() or channel
    append_access_event(
        root,
        {
            "channel": channel,
            "tool": tool,
            "access_kind": access_kind,
            "record_refs": sorted({ref for ref in (record_refs or []) if ref}),
            "query": query,
            "reason": reason,
            "working_context_ref": working_context_ref,
            "raw_path_count": raw_path_count,
            "workspace_ref": current_workspace_ref(root),
            "project_ref": current_project_ref(root),
            "task_ref": current_task_ref(root),
            "note": note,
            "access_is_proof": False,
        },
    )


def cmd_claim_graph(
    root: Path,
    query: str,
    limit: int,
    depth: int,
    all_projects: bool,
    include_task_local: bool,
    include_fallback: bool,
    include_archived: bool,
    output_format: str,
) -> int:
    records, exit_code = load_valid_context_readonly(root)
    if exit_code:
        return exit_code
    terms = task_terms(query)
    if not terms:
        print("claim graph query must contain at least one searchable token with 3+ characters")
        return 1

    project_ref = None if all_projects else current_project_ref(root) or None
    task_ref = None if include_task_local else current_task_ref(root) or None
    ranked = ranked_record_search(
        records,
        terms,
        max(1, limit),
        ["claim"],
        project_ref,
        task_ref,
        include_fallback,
        include_archived,
    )

    record_summaries: dict[str, dict] = {}
    edges_by_key: dict[tuple[str, str, tuple[str, ...]], dict] = {}
    anchors: list[dict] = []
    safe_depth = max(1, min(depth, 4))

    def include_linked_record(record_ref: str) -> bool:
        data = records.get(record_ref)
        if not data or data.get("record_type") != "claim":
            return True
        lifecycle_state = claim_lifecycle_state(data)
        attention = claim_attention(data)
        if lifecycle_state != "active" and not include_fallback:
            return False
        if attention == "fallback-only" and not include_fallback:
            return False
        if attention == "explicit-only" and not include_archived:
            return False
        return True

    for item in ranked:
        claim = item["record"]
        claim_ref = str(claim.get("id") or "")
        if not claim_ref:
            continue
        summary = public_record_summary(claim)
        anchors.append({"score": item["score"], "matched_terms": item["matched_terms"], **summary})
        record_summaries[claim_ref] = summary

        graph = linked_records_payload(records, claim_ref, "both", safe_depth)
        for linked_summary in graph.get("records", []):
            linked_ref = str(linked_summary.get("id") or "")
            if linked_ref and include_linked_record(linked_ref):
                record_summaries[linked_ref] = linked_summary
        for edge in graph.get("edges", []):
            fields = tuple(str(field) for field in edge.get("fields", []))
            key = (str(edge.get("from") or ""), str(edge.get("to") or ""), fields)
            if not include_linked_record(key[0]) or not include_linked_record(key[1]):
                continue
            edges_by_key[key] = {"from": key[0], "to": key[1], "fields": list(key[2])}

    payload = {
        "query": query,
        "terms": sorted(terms),
        "project_filter": project_ref or None,
        "task_filter": task_ref or None,
        "depth": safe_depth,
        "claim_graph_is_proof": False,
        "result_count": len(anchors),
        "anchors": anchors,
        "records": [record_summaries[record_ref] for record_ref in sorted(record_summaries)],
        "edges": [edges_by_key[key] for key in sorted(edges_by_key)],
    }
    append_lookup_access_event(
        root,
        channel="cli",
        tool="claim-graph",
        access_kind="claim_graph",
        record_refs=[str(record.get("id") or "") for record in payload["records"]],
        query=query,
        note="compact claim graph lookup",
    )

    if output_format == "json":
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return 0

    print("# Claim Graph\n")
    print(f"Query: {query}")
    print(f"Terms: {', '.join(payload['terms'])}")
    print(f"Depth: `{safe_depth}`")
    print("Mode: keyword-backed claim graph. Navigation only, not proof.")
    if project_ref:
        print(f"Project filter: `{project_ref}`")
    if task_ref:
        print(f"Task filter: `{task_ref}`")
    if include_fallback:
        print("Includes fallback historical claims.")
    if include_archived:
        print("Includes archived explicit-only claims.")
    print()
    if not anchors:
        print("- no matching claims")
        return 0

    print("## Anchor Claims")
    for anchor in anchors:
        print(
            f"- `{anchor.get('id')}` status=`{anchor.get('status', '')}` "
            f"score={anchor.get('score')} matched=`{', '.join(anchor.get('matched_terms', []))}`"
        )
        print(f"  summary: {anchor.get('summary', '')}")

    print("\n## Linked Edges")
    if payload["edges"]:
        for edge in payload["edges"]:
            print(f"- `{edge['from']}` -> `{edge['to']}` via `{', '.join(edge['fields'])}`")
    else:
        print("- none")
    return 0


def claim_record_for_lifecycle(records: dict[str, dict], claim_ref: str) -> tuple[dict | None, int]:
    if claim_ref not in records:
        print(f"missing record {claim_ref}")
        return None, 1
    claim = records[claim_ref]
    if claim.get("record_type") != "claim":
        print(f"{claim_ref} must reference a claim record")
        return None, 1
    return claim, 0


def cmd_show_claim_lifecycle(root: Path, claim_ref: str) -> int:
    records, exit_code = load_valid_context_readonly(root)
    if exit_code:
        return exit_code
    claim, claim_error = claim_record_for_lifecycle(records, claim_ref)
    if claim_error or claim is None:
        return 1

    lifecycle = claim_lifecycle(claim)
    state = claim_lifecycle_state(claim)
    attention = claim_attention(claim)
    print(f"Claim: {claim_ref}")
    print(f"status: {claim.get('status', '')}")
    print(f"lifecycle.state: {state}")
    print(f"lifecycle.attention: {attention}")
    for key in (
        "resolved_at",
        "archived_at",
        "restored_at",
        "reason",
        "resolved_by_claim_refs",
        "resolved_by_action_refs",
        "reactivation_conditions",
    ):
        if key in lifecycle and lifecycle[key]:
            print(f"{key}: {lifecycle[key]}")
    history = lifecycle.get("history", [])
    if history:
        print("history:")
        for item in history:
            if isinstance(item, dict):
                print(
                    f"- {item.get('at', '')}: state={item.get('state', '')} "
                    f"attention={item.get('attention', '')} note={item.get('note', '')}"
                )
    return 0


def mutate_claim_lifecycle(
    root: Path,
    claim_ref: str,
    state: str,
    attention: str,
    note: str,
    resolved_by_claim_refs: list[str] | None = None,
    resolved_by_action_refs: list[str] | None = None,
    reactivation_conditions: list[str] | None = None,
) -> int:
    records, exit_code = load_clean_context(root)
    if exit_code:
        return 1
    claim, claim_error = claim_record_for_lifecycle(records, claim_ref)
    if claim_error or claim is None:
        return 1

    timestamp = now_timestamp()
    payload = mutate_claim_lifecycle_payload(
        claim_payload=public_record_payload(claim),
        timestamp=timestamp,
        state=state,
        attention=attention,
        note=note,
        current_project_ref=current_project_ref(root),
        resolved_by_claim_refs=resolved_by_claim_refs,
        resolved_by_action_refs=resolved_by_action_refs,
        reactivation_conditions=reactivation_conditions,
    )

    merged_records, errors = validate_mutated_records(root, records, {claim_ref: payload})
    if errors:
        print_errors(errors)
        return 1
    return persist_mutated_records(root, merged_records, [claim_ref], f"Updated claim lifecycle {claim_ref}: {state}/{attention}")


def cmd_resolve_claim(
    root: Path,
    claim_ref: str,
    note: str,
    resolved_by_claim_refs: list[str],
    resolved_by_action_refs: list[str],
    reactivation_conditions: list[str],
) -> int:
    return mutate_claim_lifecycle(
        root,
        claim_ref,
        state="resolved",
        attention="fallback-only",
        note=note,
        resolved_by_claim_refs=resolved_by_claim_refs,
        resolved_by_action_refs=resolved_by_action_refs,
        reactivation_conditions=reactivation_conditions,
    )


def cmd_archive_claim(root: Path, claim_ref: str, note: str) -> int:
    return mutate_claim_lifecycle(root, claim_ref, state="archived", attention="explicit-only", note=note)


def cmd_restore_claim(root: Path, claim_ref: str, note: str) -> int:
    return mutate_claim_lifecycle(root, claim_ref, state="active", attention="normal", note=note)


def copy_artifact_file(root: Path, path: Path) -> tuple[str, str]:
    target_root = root / "artifacts"
    target_root.mkdir(parents=True, exist_ok=True)
    artifact_id = next_artifact_id(root)
    suffix = sanitize_artifact_name(path.name)
    target = target_root / f"{artifact_id}__{suffix}"
    with tempfile.NamedTemporaryFile(
        "wb",
        dir=target_root,
        prefix=f".{target.name}.",
        suffix=".tmp",
        delete=False,
    ) as handle:
        tmp_path = Path(handle.name)
    shutil.copy2(path, tmp_path)
    os.replace(tmp_path, target)
    return artifact_id, f"artifacts/{target.name}"


def cmd_record_artifact(root: Path, path: Path) -> int:
    if not path.exists():
        print(f"missing artifact source file: {path}")
        return 1
    if not path.is_file():
        print(f"artifact source must be a file: {path}")
        return 1

    artifact_id, artifact_ref = copy_artifact_file(root, path)
    invalidate_hydration_state(root, f"recorded artifact {artifact_id}")
    print(f"Recorded artifact {artifact_id} at {artifact_ref}")
    return 0


def maybe_index_code_backends(
    root: Path,
    repo_root: Path,
    *,
    backend_index: str,
    workspace_ref: str,
    project_ref: str,
) -> None:
    payload = cocoindex_index_payload(
        root,
        repo_root,
        scope_mode=backend_index,
        workspace_ref=workspace_ref,
        project_ref=project_ref,
    )
    for line in cocoindex_index_text_lines(payload):
        print(line)


def cmd_init_code_index(
    root: Path,
    repo_root: Path,
    max_files: int,
    max_bytes: int,
    include_untracked: bool,
    backend_index: str,
) -> int:
    entries, errors = load_code_index_entries(root)
    if errors:
        print_errors(errors)
        return 1
    workspace_ref, project_ref = repo_scope_for_root(root, repo_root)
    try:
        files = discover_files(repo_root, [], [], git_tracked=not include_untracked, max_files=max_files)
    except RuntimeError as exc:
        print(str(exc))
        return 1
    changed = []
    seen_paths = {code_index_rel_path(repo_root, path) for path in files}
    for path in files:
        entry, _ = code_index_entry_for_file(root, entries, repo_root, path, max_bytes, workspace_ref=workspace_ref, project_ref=project_ref)
        changed.append(entry)
        entries[entry["id"]] = entry
    for entry in entries.values():
        if not code_entry_matches_repo_scope(entry, workspace_ref, project_ref):
            continue
        target = entry.get("target", {})
        if isinstance(target, dict) and target.get("kind") == "file" and target.get("path") not in seen_paths and entry.get("target_state") == "present":
            payload = public_code_index_entry(entry)
            payload["target_state"] = "missing"
            payload["status"] = "missing"
            payload["updated_at"] = now_timestamp()
            changed.append(payload)
    result = persist_code_index_entries(root, entries, changed, f"Indexed {len(files)} git-tracked code file(s)")
    if result == 0:
        maybe_index_code_backends(root, repo_root, backend_index=backend_index, workspace_ref=workspace_ref, project_ref=project_ref)
    return result


def cmd_index_code(
    root: Path,
    repo_root: Path,
    includes: list[str],
    excludes: list[str],
    max_files: int,
    max_bytes: int,
    backend_index: str,
) -> int:
    entries, errors = load_code_index_entries(root)
    if errors:
        print_errors(errors)
        return 1
    workspace_ref, project_ref = repo_scope_for_root(root, repo_root)
    try:
        files = discover_files(repo_root, includes, excludes, git_tracked=False, max_files=max_files)
    except RuntimeError as exc:
        print(str(exc))
        return 1
    changed = []
    for path in files:
        entry, _ = code_index_entry_for_file(root, entries, repo_root, path, max_bytes, workspace_ref=workspace_ref, project_ref=project_ref)
        changed.append(entry)
        entries[entry["id"]] = entry
    result = persist_code_index_entries(root, entries, changed, f"Indexed {len(files)} code file(s)")
    if result == 0:
        maybe_index_code_backends(root, repo_root, backend_index=backend_index, workspace_ref=workspace_ref, project_ref=project_ref)
    return result


def cmd_code_refresh(root: Path, repo_root: Path, paths: list[str], max_bytes: int, backend_index: str) -> int:
    entries, errors = load_code_index_entries(root)
    if errors:
        print_errors(errors)
        return 1
    workspace_ref, project_ref = repo_scope_for_root(root, repo_root)
    patterns = paths or ["**/*"]
    changed = []
    for entry in list(entries.values()):
        if not code_entry_matches_repo_scope(entry, workspace_ref, project_ref):
            continue
        target = entry.get("target", {})
        if not isinstance(target, dict) or target.get("kind") != "file":
            continue
        rel = str(target.get("path", ""))
        if not code_index_path_matches(rel, patterns):
            continue
        file_path = repo_root / rel
        if file_path.exists() and file_path.is_file():
            entry_payload, created = code_index_entry_for_file(root, entries, repo_root, file_path, max_bytes, workspace_ref=workspace_ref, project_ref=project_ref)
            changed.append(entry_payload)
            entries[entry_payload["id"]] = entry_payload
            if created:
                old_payload = public_code_index_entry(entry)
                old_payload["status"] = "superseded"
                old_payload["updated_at"] = now_timestamp()
                changed.append(old_payload)
                entries[old_payload["id"]] = old_payload
        elif entry.get("target_state") != "missing":
            payload = public_code_index_entry(entry)
            payload["target_state"] = "missing"
            payload["status"] = "missing"
            payload["updated_at"] = now_timestamp()
            changed.append(payload)
            entries[payload["id"]] = payload
    result = persist_code_index_entries(root, entries, changed, f"Refreshed {len(changed)} code index entry update(s)")
    if result == 0:
        maybe_index_code_backends(root, repo_root, backend_index=backend_index, workspace_ref=workspace_ref, project_ref=project_ref)
    return result


def print_code_entries(entries: list[dict], fields: list[str], repo_root: Path) -> None:
    for line in code_entries_text_lines(entries, fields, repo_root):
        print(line)


def cmd_code_info(root: Path, repo_root: Path, entry_ref: str | None, path: str | None, fields_value: str | None, output_format: str) -> int:
    entries, errors = load_code_index_entries(root)
    if errors:
        print_errors(errors)
        return 1
    workspace_ref, project_ref = repo_scope_for_root(root, repo_root)
    scoped_entries = {key: entry for key, entry in entries.items() if code_entry_matches_repo_scope(entry, workspace_ref, project_ref)}
    entry = resolve_code_entry(scoped_entries, entry_ref, path)
    if not entry:
        print("missing code index entry")
        return 1
    try:
        fields = parse_code_fields(fields_value)
    except ValueError as exc:
        print(str(exc))
        return 1
    projected = project_code_entry(entry, fields, repo_root)
    if output_format == "json":
        print(json.dumps(projected, indent=2, ensure_ascii=False))
    else:
        print_code_entries([entry], fields, repo_root)
    return 0


def cmd_code_search(
    root: Path,
    repo_root: Path,
    repo_root_source: str,
    query: str | None,
    path_patterns: list[str],
    language: str | None,
    code_kind: str | None,
    imports: list[str],
    symbols: list[str],
    features: list[str],
    refs: list[str],
    link_candidate_refs: list[str],
    annotation_kind: str | None,
    annotation_categories: list[str],
    annotation_status: str | None,
    include_stale_annotations: bool,
    stale: str | None,
    include_missing: bool,
    include_superseded: bool,
    include_archived: bool,
    fields_value: str | None,
    limit: int,
    scope: str | None,
    output_format: str,
) -> int:
    entries, errors = load_code_index_entries(root)
    if errors:
        print_errors(errors)
        return 1
    workspace_ref, project_ref = repo_scope_for_root(root, repo_root)
    try:
        fields = parse_code_fields(fields_value)
    except ValueError as exc:
        print(str(exc))
        return 1
    cix_filter_present = any(
        [
            path_patterns,
            language,
            code_kind,
            imports,
            symbols,
            features,
            refs,
            annotation_kind,
            annotation_categories,
            annotation_status,
            stale,
            include_missing,
            include_superseded,
            include_archived,
        ]
    )
    results = []
    if not (query and not cix_filter_present):
        for entry in entries.values():
            if not code_entry_matches_repo_scope(entry, workspace_ref, project_ref):
                continue
            status = str(entry.get("status", ""))
            if status == "missing" and not include_missing:
                continue
            if status == "superseded" and not include_superseded:
                continue
            if status == "archived" and not include_archived:
                continue
            target = entry.get("target", {}) if isinstance(entry.get("target"), dict) else {}
            target_path = str(target.get("path", ""))
            if path_patterns and not code_index_path_matches(target_path, path_patterns):
                continue
            metadata = entry.get("metadata") or {}
            if language and str(entry.get("language", "")) != language:
                continue
            if code_kind and str(entry.get("code_kind", "")) != code_kind:
                continue
            if imports and not set(imports).issubset(set(metadata.get("imports", []))):
                continue
            all_symbols = set(metadata.get("classes", []) + metadata.get("functions", []) + metadata.get("tests", []))
            if symbols and not set(symbols).issubset(all_symbols):
                continue
            all_features = set(entry.get("detected_features", []) + entry.get("manual_features", []))
            if features and not set(features).issubset(all_features):
                continue
            entry_refs = set()
            for ref_values in (entry.get("manual_links") or {}).values():
                if isinstance(ref_values, list):
                    entry_refs.update(str(ref) for ref in ref_values)
            for link in entry.get("links", []) if isinstance(entry.get("links"), list) else []:
                if isinstance(link, dict):
                    entry_refs.add(str(link.get("ref", "")))
            if refs and not set(refs).issubset(entry_refs):
                continue
            if annotation_kind or annotation_categories or annotation_status:
                if not code_entry_matching_annotations(
                    repo_root,
                    entry,
                    annotation_kind,
                    annotation_categories,
                    annotation_status,
                    include_stale_annotations,
                ):
                    continue
            freshness = code_entry_freshness(repo_root, entry)
            if stale == "true" and not freshness.get("stale"):
                continue
            if stale == "false" and freshness.get("stale"):
                continue
            results.append(entry)
    results = sorted(results, key=lambda item: (str(item.get("status", "")), str((item.get("target") or {}).get("path", ""))))[: max(1, limit)]
    backend_payload = None
    link_candidates: dict[str, list[str]] = {}
    if link_candidate_refs:
        records, record_errors = load_records(root)
        if record_errors:
            print_errors(record_errors)
            return 1
        record_type_to_link_key = {record_type: key for key, record_type in CODE_INDEX_LINK_KEYS.items()}
        for ref in link_candidate_refs:
            record = records.get(ref)
            if not record:
                print(f"missing link candidate ref: {ref}")
                return 1
            ref_key = record_type_to_link_key.get(str(record.get("record_type", "")))
            if not ref_key:
                print(f"{ref} cannot be linked from CIX entries")
                return 1
            link_candidates.setdefault(ref_key, [])
            if ref not in link_candidates[ref_key]:
                link_candidates[ref_key].append(ref)
    if query:
        scoped_entries = {key: entry for key, entry in entries.items() if code_entry_matches_repo_scope(entry, workspace_ref, project_ref)}
        backend_payload = cocoindex_search_payload(
            root,
            repo_root,
            query=query,
            language=language,
            path_patterns=path_patterns,
            limit=limit,
            scope=scope,
            workspace_ref=workspace_ref or None,
            project_ref=project_ref or None,
        )
        backend_payload = enrich_backend_results_with_cix(
            backend_payload,
            scoped_entries,
            repo_root,
            link_candidates=link_candidates,
        )
        append_backend_access_event(root, "code-search", "backend_code_search", backend="cocoindex")
    append_lookup_access_event(
        root,
        channel="cli",
        tool="code-search",
        access_kind="code_index_search",
        record_refs=[str(entry.get("id", "")) for entry in results],
        query=query or " ".join(path_patterns + imports + symbols + features + refs),
        note="CIX search via TEP entrypoint",
    )
    if output_format == "json":
        payload = {
            "repo_scope": repo_scope_payload(root, repo_root, repo_root_source),
            "results": [project_code_entry(entry, fields, repo_root) for entry in results],
        }
        if backend_payload is not None:
            payload["backend_results"] = backend_payload
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        scope_payload = repo_scope_payload(root, repo_root, repo_root_source)
        print(
            "# Repository Scope\n\n"
            f"- repo_root: `{scope_payload['repo_root']}`\n"
            f"- repo_root_source: `{scope_payload['repo_root_source']}`\n"
            f"- workspace_ref: `{scope_payload['workspace_ref'] or 'none'}`\n"
            f"- project_ref: `{scope_payload['project_ref'] or 'none'}`\n"
        )
        print_code_entries(results, fields, repo_root)
        if backend_payload is not None:
            print()
            for line in cocoindex_search_text_lines(backend_payload):
                print(line)
    return 0


def code_link_candidates_for_refs(root: Path, refs: list[str]) -> tuple[dict[str, list[str]] | None, int]:
    if not refs:
        return {}, 0
    records, record_errors = load_records(root)
    if record_errors:
        print_errors(record_errors)
        return None, 1
    record_type_to_link_key = {record_type: key for key, record_type in CODE_INDEX_LINK_KEYS.items()}
    link_candidates: dict[str, list[str]] = {}
    for ref in refs:
        record = records.get(ref)
        if not record:
            print(f"missing link candidate ref: {ref}")
            return None, 1
        ref_key = record_type_to_link_key.get(str(record.get("record_type", "")))
        if not ref_key:
            print(f"{ref} cannot be linked from CIX entries")
            return None, 1
        link_candidates.setdefault(ref_key, [])
        if ref not in link_candidates[ref_key]:
            link_candidates[ref_key].append(ref)
    return link_candidates, 0


def code_feedback_review_payload(
    root: Path,
    repo_root: Path,
    *,
    query: str,
    path_patterns: list[str],
    language: str | None,
    link_candidate_refs: list[str],
    limit: int,
) -> tuple[dict | None, int]:
    entries, errors = load_code_index_entries(root)
    if errors:
        print_errors(errors)
        return None, 1
    workspace_ref, project_ref = repo_scope_for_root(root, repo_root)
    link_candidates, exit_code = code_link_candidates_for_refs(root, link_candidate_refs)
    if exit_code or link_candidates is None:
        return None, 1
    backend_payload = cocoindex_search_payload(
        root,
        repo_root,
        query=query,
        language=language,
        path_patterns=path_patterns,
        limit=limit,
        workspace_ref=workspace_ref or None,
        project_ref=project_ref or None,
    )
    scoped_entries = {key: entry for key, entry in entries.items() if code_entry_matches_repo_scope(entry, workspace_ref, project_ref)}
    backend_payload = enrich_backend_results_with_cix(
        backend_payload,
        scoped_entries,
        repo_root,
        link_candidates=link_candidates,
    )
    items = []
    for result in backend_payload.get("results") or []:
        if not isinstance(result, dict):
            continue
        target = result.get("target") if isinstance(result.get("target"), dict) else {}
        items.append(
            {
                "rank": result.get("rank"),
                "score": result.get("score"),
                "target": target,
                "cix_candidates": result.get("cix_candidates", []),
                "link_suggestions": result.get("link_suggestions", []),
                "index_suggestion": result.get("index_suggestion"),
                "snippet": result.get("snippet", ""),
                "feedback_is_proof": False,
            }
        )
    append_backend_access_event(root, "code-feedback", "backend_code_feedback", backend="cocoindex")
    return {
        "feedback_is_proof": False,
        "mode": "review",
        "query": query,
        "backend_results": backend_payload,
        "items": items,
    }, 0


def code_feedback_text_lines(payload: dict) -> list[str]:
    lines = [
        "# Code Backend Feedback",
        "",
        "Mode: review. Backend feedback is navigation only, not proof.",
        f"Query: `{payload.get('query', '')}`",
        "",
    ]
    for item in payload.get("items") or []:
        target = item.get("target") if isinstance(item.get("target"), dict) else {}
        location = str(target.get("path", ""))
        if target.get("line_start"):
            location = f"{location}:{target.get('line_start')}-{target.get('line_end', target.get('line_start'))}"
        lines.append(f"- rank={item.get('rank')} score={item.get('score')} target=`{location}`")
        cix_candidates = item.get("cix_candidates") or []
        if cix_candidates:
            lines.append("  cix_candidates: " + ", ".join(str(candidate.get("id")) for candidate in cix_candidates))
        index_suggestion = item.get("index_suggestion")
        if isinstance(index_suggestion, dict):
            lines.append(f"  index_suggestion: {index_suggestion.get('command')}")
        for suggestion in item.get("link_suggestions") or []:
            lines.append(f"  link_suggestion: {suggestion.get('command')}")
    return lines


def cmd_code_feedback(
    root: Path,
    repo_root: Path,
    query: str | None,
    path_patterns: list[str],
    language: str | None,
    link_candidate_refs: list[str],
    entry_ref: str | None,
    path: str | None,
    apply: bool,
    note: str | None,
    limit: int,
    output_format: str,
) -> int:
    if apply:
        if not link_candidate_refs:
            print("--apply requires at least one --link-candidate")
            return 1
        if not (entry_ref or path):
            print("--apply requires --entry or --path")
            return 1
        if not note:
            print("--apply requires --note")
            return 1
        link_candidates, exit_code = code_link_candidates_for_refs(root, link_candidate_refs)
        if exit_code or link_candidates is None:
            return 1
        return cmd_link_code(root, entry_ref=entry_ref, path=path, link_refs=link_candidates, note=note)

    if not query:
        print("review mode requires --query")
        return 1
    payload, exit_code = code_feedback_review_payload(
        root,
        repo_root,
        query=query,
        path_patterns=path_patterns,
        language=language,
        link_candidate_refs=link_candidate_refs,
        limit=limit,
    )
    if exit_code or payload is None:
        return 1
    if output_format == "json":
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        for line in code_feedback_text_lines(payload):
            print(line)
    return 0


def cmd_code_smell_report(
    root: Path,
    repo_root: Path,
    categories: list[str],
    severities: list[str],
    include_stale: bool,
    limit: int,
    output_format: str,
) -> int:
    entries, errors = load_code_index_entries(root)
    if errors:
        print_errors(errors)
        return 1
    invalid_categories = [
        category
        for category in categories
        if category not in CODE_SMELL_CATEGORIES and not re.match(r"^custom:[a-z0-9][a-z0-9-]{1,63}$", category)
    ]
    if invalid_categories:
        print(f"invalid smell category: {invalid_categories[0]}")
        return 1
    invalid_severities = [severity for severity in severities if severity not in CODE_SMELL_SEVERITIES]
    if invalid_severities:
        print(f"invalid smell severity: {invalid_severities[0]}")
        return 1
    workspace_ref, project_ref = repo_scope_for_root(root, repo_root)
    scoped_entries = {key: entry for key, entry in entries.items() if code_entry_matches_repo_scope(entry, workspace_ref, project_ref)}
    rows = code_smell_rows(repo_root, scoped_entries, categories, severities, include_stale)[: max(1, limit)]
    if output_format == "json":
        print(json.dumps(code_smell_report_payload(rows, categories, severities, include_stale), indent=2, ensure_ascii=False))
        return 0

    for line in code_smell_report_text_lines(rows):
        print(line)
    return 0


def cmd_code_entry_create(root: Path, target_kind: str, path: str | None, name: str | None, symbol_name: str | None, summary: str, manual_features: list[str], note: str) -> int:
    if target_kind not in CODE_INDEX_TARGET_KINDS:
        print(f"invalid target kind: {target_kind}")
        return 1
    entries, errors = load_code_index_entries(root)
    if errors:
        print_errors(errors)
        return 1
    entry_id = next_code_index_id(entries)
    timestamp = now_timestamp()
    payload = build_manual_code_index_entry(
        entry_id=entry_id,
        timestamp=timestamp,
        target_kind=target_kind,
        path=path,
        name=name,
        symbol_name=symbol_name,
        summary=summary,
        manual_features=manual_features,
        note=note,
    )
    workspace_ref = current_workspace_ref(root)
    project_ref = current_project_ref(root)
    if workspace_ref:
        payload["workspace_ref"] = workspace_ref
    if project_ref:
        payload["project_ref"] = project_ref
    return persist_code_index_entries(root, entries, [payload], f"Created code index entry {entry_id}")


def validate_code_annotation_refs(root: Path, source_refs: list[str], claim_refs: list[str], proposal_refs: list[str]) -> int:
    records, record_errors = load_records(root)
    if record_errors:
        print_errors(record_errors)
        return 1
    expected = {
        "source": source_refs,
        "claim": claim_refs,
        "proposal": proposal_refs,
    }
    for expected_type, refs in expected.items():
        for ref in refs:
            if ref not in records:
                print(f"missing {expected_type} ref: {ref}")
                return 1
            if records[ref].get("record_type") != expected_type:
                print(f"{ref} must reference {expected_type}")
                return 1
    return 0


def cmd_annotate_code(
    root: Path,
    entry_ref: str | None,
    path: str | None,
    kind: str,
    text: str,
    confidence: str,
    supersedes: list[str],
    categories: list[str],
    severity: str | None,
    suggestions: list[str],
    source_refs: list[str],
    claim_refs: list[str],
    proposal_refs: list[str],
) -> int:
    entries, errors = load_code_index_entries(root)
    if errors:
        print_errors(errors)
        return 1
    if kind not in CODE_INDEX_ANNOTATION_KINDS:
        print(f"invalid annotation kind: {kind}")
        return 1
    if validate_code_annotation_refs(root, source_refs, claim_refs, proposal_refs):
        return 1
    entry = resolve_code_entry(entries, entry_ref, path)
    if not entry:
        print("missing code index entry")
        return 1
    payload = public_code_index_entry(entry)
    annotation = {
        "id": f"ANN-{secrets.token_hex(4)}",
        "kind": kind,
        "status": "active",
        "text": text.strip(),
        "confidence": confidence,
        "supersedes_refs": supersedes,
        "created_at": now_timestamp(),
        **annotation_snapshot(entry),
    }
    if source_refs:
        annotation["source_refs"] = source_refs
    if claim_refs:
        annotation["claim_refs"] = claim_refs
    if proposal_refs:
        annotation["proposal_refs"] = proposal_refs
    cleaned_suggestions = [suggestion.strip() for suggestion in suggestions if suggestion.strip()]
    if cleaned_suggestions:
        annotation["suggestions"] = cleaned_suggestions
    if kind == "smell":
        normalized_categories, category_error = normalize_smell_categories(categories)
        if category_error:
            print(category_error)
            return 1
        smell_severity = severity or "medium"
        if smell_severity not in CODE_SMELL_SEVERITIES:
            print("smell severity must be low, medium, high, or critical")
            return 1
        if smell_severity == "critical" and not claim_refs:
            print("critical smell annotations require at least one --claim CLM-* support ref")
            return 1
        annotation["categories"] = normalized_categories
        annotation["severity"] = smell_severity
    payload.setdefault("annotations", []).append(annotation)
    payload["updated_at"] = now_timestamp()
    return persist_code_index_entries(root, entries, [payload], f"Annotated code index entry {payload['id']} with {annotation['id']}")


def cmd_link_code(root: Path, entry_ref: str | None, path: str | None, link_refs: dict[str, list[str]], note: str) -> int:
    records, record_errors = load_records(root)
    if record_errors:
        print_errors(record_errors)
        return 1
    entries, errors = load_code_index_entries(root)
    if errors:
        print_errors(errors)
        return 1
    entry = resolve_code_entry(entries, entry_ref, path)
    if not entry:
        print("missing code index entry")
        return 1
    payload = public_code_index_entry(entry)
    links = payload.setdefault("links", [])
    manual_links = payload.setdefault("manual_links", {})
    for ref_key, refs in link_refs.items():
        expected_type = CODE_INDEX_LINK_KEYS[ref_key]
        for ref in refs:
            if ref not in records or records[ref].get("record_type") != expected_type:
                print(f"{ref_key} ref {ref} must reference {expected_type}")
                return 1
            manual_links.setdefault(ref_key, [])
            if ref not in manual_links[ref_key]:
                manual_links[ref_key].append(ref)
            links.append(
                {
                    "id": f"LNK-{secrets.token_hex(4)}",
                    "status": "active",
                    "ref_key": ref_key,
                    "ref": ref,
                    "note": note.strip(),
                    "created_at": now_timestamp(),
                    **annotation_snapshot(entry),
                }
            )
    payload["updated_at"] = now_timestamp()
    return persist_code_index_entries(root, entries, [payload], f"Linked code index entry {payload['id']}")


def cmd_assign_code_index(root: Path, record_ref: str, entry_refs: list[str], note: str | None) -> int:
    records, exit_code = load_clean_context(root)
    if exit_code:
        return 1
    entries, errors = load_code_index_entries(root)
    if errors:
        print_errors(errors)
        return 1
    if record_ref not in records:
        print(f"missing record {record_ref}")
        return 1
    record = records[record_ref]
    if record.get("record_type") not in CODE_INDEX_ALLOWED_RECORD_TYPES:
        print(f"record type {record.get('record_type')} cannot reference CIX entries")
        return 1
    for entry_ref in entry_refs:
        if entry_ref not in entries:
            print(f"missing code index entry {entry_ref}")
            return 1
    payload = public_record_payload(record)
    refs = payload.setdefault("code_index_refs", [])
    for entry_ref in entry_refs:
        if entry_ref not in refs:
            refs.append(entry_ref)
    if note:
        payload["note"] = append_note(str(payload.get("note", "")), note)
    payload["updated_at"] = now_timestamp()
    merged_records, validation_errors = validate_mutated_records(root, records, {record_ref: payload})
    if validation_errors:
        print_errors(validation_errors)
        return 1
    return persist_mutated_records(root, merged_records, [record_ref], f"Assigned code index refs to {record_ref}")


def cmd_code_entry_archive_unscoped(root: Path, statuses: list[str], apply: bool, output_format: str) -> int:
    entries, errors = load_code_index_entries(root)
    if errors:
        print_errors(errors)
        return 1
    selected_statuses = set(statuses or ["missing"])
    invalid_statuses = selected_statuses - CODE_INDEX_STATUSES
    if invalid_statuses:
        print(f"invalid status: {sorted(invalid_statuses)[0]}")
        return 1
    targets = []
    for entry in entries.values():
        target = entry.get("target") if isinstance(entry.get("target"), dict) else {}
        if str(target.get("kind", "")) not in {"file", "directory", "glob", "symbol"}:
            continue
        if str(entry.get("project_ref", "") or "").strip():
            continue
        if str(entry.get("status", "")).strip() not in selected_statuses:
            continue
        targets.append(entry)
    payload = {
        "archive_unscoped_is_dry_run": not apply,
        "selected_statuses": sorted(selected_statuses),
        "count": len(targets),
        "items": [
            {
                "id": entry.get("id"),
                "status": entry.get("status"),
                "target": entry.get("target", {}),
            }
            for entry in targets[:100]
        ],
    }
    if not apply:
        if output_format == "json":
            print(json.dumps(payload, indent=2, ensure_ascii=False))
        else:
            print(f"Would archive {len(targets)} unscoped CIX entr{'y' if len(targets) == 1 else 'ies'}")
            for item in payload["items"]:
                target = item.get("target", {})
                print(f"- `{item.get('id')}` status=`{item.get('status')}` target=`{target.get('path') or target.get('name') or ''}`")
        return 0
    timestamp = now_timestamp()
    changed = []
    for entry in targets:
        payload_entry = public_code_index_entry(entry)
        payload_entry["status"] = "archived"
        payload_entry["updated_at"] = timestamp
        payload_entry["note"] = append_note(
            str(payload_entry.get("note", "")),
            f"[{timestamp}] archived by code-entry archive-unscoped because CIX has no project_ref",
        )
        changed.append(payload_entry)
        entries[payload_entry["id"]] = payload_entry
    persist_code_index_entries(root, entries, changed, f"Archived {len(changed)} unscoped code index entr{'y' if len(changed) == 1 else 'ies'}")
    payload["archive_unscoped_is_dry_run"] = False
    if output_format == "json":
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


def cmd_code_entry_attach_unscoped(root: Path, repo_root: str, statuses: list[str] | None, apply: bool, output_format: str) -> int:
    resolved_repo = Path(repo_root).expanduser().resolve()
    workspace_ref, project_ref = repo_scope_for_root(root, resolved_repo)
    if not workspace_ref or not project_ref:
        print(f"{resolved_repo}: must match an active workspace and project root_refs before attaching unscoped CIX")
        return 1
    entries, errors = load_code_index_entries(root)
    if errors:
        print_errors(errors)
        return 1
    selected_statuses = set(statuses or ["active"])
    invalid_statuses = selected_statuses - CODE_INDEX_STATUSES
    if invalid_statuses:
        print(f"invalid status: {sorted(invalid_statuses)[0]}")
        return 1
    targets = []
    skipped = {"already_scoped": 0, "status": 0, "unsupported_target": 0, "not_present_under_root": 0}
    for entry in entries.values():
        if str(entry.get("project_ref", "") or "").strip():
            skipped["already_scoped"] += 1
            continue
        if str(entry.get("status", "")).strip() not in selected_statuses:
            skipped["status"] += 1
            continue
        target = entry.get("target") if isinstance(entry.get("target"), dict) else {}
        target_kind = str(target.get("kind", ""))
        target_path = str(target.get("path", "") or "").strip()
        if target_kind not in {"file", "directory"} or not target_path:
            skipped["unsupported_target"] += 1
            continue
        candidate = (resolved_repo / target_path).resolve()
        if target_kind == "file" and not candidate.is_file():
            skipped["not_present_under_root"] += 1
            continue
        if target_kind == "directory" and not candidate.is_dir():
            skipped["not_present_under_root"] += 1
            continue
        targets.append(entry)
    payload = {
        "attach_unscoped_is_dry_run": not apply,
        "repo_root": str(resolved_repo),
        "workspace_ref": workspace_ref,
        "project_ref": project_ref,
        "selected_statuses": sorted(selected_statuses),
        "count": len(targets),
        "skipped": skipped,
        "items": [
            {
                "id": entry.get("id"),
                "status": entry.get("status"),
                "target": entry.get("target", {}),
            }
            for entry in targets[:100]
        ],
    }
    if not apply:
        if output_format == "json":
            print(json.dumps(payload, indent=2, ensure_ascii=False))
        else:
            print(
                f"Would attach {len(targets)} unscoped CIX entr{'y' if len(targets) == 1 else 'ies'} "
                f"to project `{project_ref}` workspace `{workspace_ref}`"
            )
            for item in payload["items"]:
                target = item.get("target", {})
                print(f"- `{item.get('id')}` status=`{item.get('status')}` target=`{target.get('path') or ''}`")
        return 0
    timestamp = now_timestamp()
    changed = []
    for entry in targets:
        payload_entry = public_code_index_entry(entry)
        payload_entry["workspace_ref"] = workspace_ref
        payload_entry["project_ref"] = project_ref
        payload_entry["updated_at"] = timestamp
        payload_entry["note"] = append_note(
            str(payload_entry.get("note", "")),
            f"[{timestamp}] attached by code-entry attach-unscoped to workspace {workspace_ref} project {project_ref}",
        )
        changed.append(payload_entry)
        entries[payload_entry["id"]] = payload_entry
    persist_code_index_entries(root, entries, changed, f"Attached {len(changed)} unscoped code index entr{'y' if len(changed) == 1 else 'ies'}")
    payload["attach_unscoped_is_dry_run"] = False
    if output_format == "json":
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


TYPE_GRAPH_CHAINS = [
    {
        "name": "scope",
        "chains": [
            "WSP -> PRJ",
            "WSP -> TASK",
            "PRJ -> TASK",
            "WSP/PRJ/TASK -> WCTX",
            "WSP/PRJ -> CIX",
        ],
    },
    {
        "name": "input provenance",
        "chains": [
            "INP -> derived_record_refs -> SRC|CLM|GLD|PRM|RST|TASK|...",
            "derived record -> input_refs -> INP",
            "INP -/-> proof",
        ],
    },
    {
        "name": "truth",
        "chains": [
            "SRC -> CLM",
            "CLM -> CLM via support_refs",
            "CLM -> CLM via contradiction_refs",
            "CLM -> CLM via lifecycle.resolved_by_claim_refs",
            "CLM.logic -> logic_index",
        ],
    },
    {
        "name": "understanding",
        "chains": [
            "CLM -> MODEL",
            "MODEL -> MODEL via related_model_refs|supersedes_refs|promoted_from_refs",
            "MODEL -> FLOW",
            "CLM -> FLOW via preconditions|oracle|steps",
            "OPEN -> CLM|MODEL|FLOW",
        ],
    },
    {
        "name": "code navigation",
        "chains": [
            "WSP/PRJ -> CIX",
            "CIX -> code target",
            "CIX -> CIX via related_entry_refs|supersedes_refs|child_entry_refs",
            "CIX -> records via manual_links|links",
            "records -> CIX via code_index_refs",
            "CIX -> code target -> SRC -> CLM",
            "CIX -/-> proof",
        ],
    },
    {
        "name": "execution",
        "chains": [
            "TASK -> WCTX",
            "TASK -> PLN|DEBT|ACT|OPEN",
            "TASK -> CLM|MODEL|FLOW",
            "PLN -> justified_by|blocked_by",
            "DEBT -> evidence_refs|plan_refs",
            "ACT -> justified_by",
        ],
    },
    {
        "name": "policy",
        "chains": [
            "INP/SRC -> GLD",
            "GLD -> CLM via related_claim_refs",
            "RST -> CLM via related_claim_refs",
            "PRM/RST/GLD -> WSP/PRJ/TASK scope",
            "PRP -> CLM|GLD|MODEL|FLOW|OPEN",
        ],
    },
]


def _type_graph_record_type(records: dict[str, dict], ref: str) -> str:
    record = records.get(ref)
    if not record:
        return ""
    return str(record.get("record_type", "") or "")


def build_type_graph_report(root: Path) -> tuple[dict, int]:
    records, record_errors = load_records(root)
    entries, code_errors = load_code_index_entries(root)
    issues: list[dict] = []
    warnings: list[dict] = []

    def add_issue(kind: str, ref: str, message: str, field: str = "") -> None:
        issues.append({"kind": kind, "ref": ref, "field": field, "message": message})

    def add_warning(kind: str, ref: str, message: str, field: str = "") -> None:
        warnings.append({"kind": kind, "ref": ref, "field": field, "message": message})

    if record_errors:
        for error in record_errors:
            add_issue("record-load-error", str(error.path), error.message)
    if code_errors:
        for error in code_errors:
            add_issue("code-index-load-error", str(error.path), error.message)

    workspace_project_refs: dict[str, set[str]] = {
        ref: set(str(item) for item in data.get("project_refs", []) if str(item).strip())
        for ref, data in records.items()
        if data.get("record_type") == "workspace"
    }
    project_workspace_refs: dict[str, set[str]] = {}
    for project_ref, data in records.items():
        if data.get("record_type") != "project":
            continue
        refs = set(str(item) for item in data.get("workspace_refs", []) if str(item).strip())
        refs.update(workspace_ref for workspace_ref, project_refs in workspace_project_refs.items() if project_ref in project_refs)
        project_workspace_refs[project_ref] = refs

    for workspace_ref, project_refs in workspace_project_refs.items():
        for project_ref in sorted(project_refs):
            if _type_graph_record_type(records, project_ref) != "project":
                add_issue("workspace-project-ref", workspace_ref, f"{project_ref} is not a project", "project_refs")
            elif workspace_ref not in project_workspace_refs.get(project_ref, set()):
                add_warning("workspace-project-reciprocity", project_ref, f"{project_ref} is listed in {workspace_ref} but does not link back", "workspace_refs")

    for record_ref, data in records.items():
        record_type = str(data.get("record_type", "") or "")
        if record_type != "workspace" and not data.get("workspace_refs"):
            add_warning("missing-workspace-scope", record_ref, "record has no workspace_refs", "workspace_refs")
        for project_ref in data.get("project_refs", []) if isinstance(data.get("project_refs"), list) else []:
            if _type_graph_record_type(records, str(project_ref)) != "project":
                add_issue("project-scope-type", record_ref, f"{project_ref} is not a project", "project_refs")
                continue
            record_workspaces = set(str(item) for item in data.get("workspace_refs", []) if str(item).strip())
            project_workspaces = project_workspace_refs.get(str(project_ref), set())
            if record_workspaces and project_workspaces and record_workspaces.isdisjoint(project_workspaces):
                add_issue(
                    "project-workspace-scope-mismatch",
                    record_ref,
                    f"{project_ref} belongs to {sorted(project_workspaces)}, record is scoped to {sorted(record_workspaces)}",
                    "project_refs",
                )
        if record_type in {"claim", "source"} and data.get("code_index_refs"):
            add_issue("code-index-proof-boundary", record_ref, "claim/source must not use CIX as proof support", "code_index_refs")
        if record_type == "model" and data.get("status") in {"working", "stable"} and not data.get("claim_refs"):
            add_warning("model-without-claims", record_ref, "working/stable model has no claim_refs", "claim_refs")
        if record_type == "flow" and data.get("status") in {"working", "stable"} and not data.get("model_refs"):
            add_warning("flow-without-models", record_ref, "working/stable flow has no model_refs", "model_refs")

    active_wctx_by_task: dict[str, list[str]] = {}
    for record_ref, data in records.items():
        if data.get("record_type") != "working_context" or data.get("status") != "active":
            continue
        for task_ref in data.get("task_refs", []) if isinstance(data.get("task_refs"), list) else []:
            active_wctx_by_task.setdefault(str(task_ref), []).append(record_ref)
            if _type_graph_record_type(records, str(task_ref)) != "task":
                add_issue("working-context-task-ref", record_ref, f"{task_ref} is not a task", "task_refs")
        task_refs = data.get("task_refs", []) if isinstance(data.get("task_refs"), list) else []
        if not task_refs:
            add_warning("active-working-context-without-task", record_ref, "active WCTX has no task_refs", "task_refs")

    for task_ref, data in records.items():
        if data.get("record_type") != "task" or data.get("status") != "active":
            continue
        active_wctx = active_wctx_by_task.get(task_ref, [])
        if not active_wctx:
            add_warning("active-task-without-active-wctx", task_ref, "active task has no active WCTX; create or fork WCTX before persisting task-local conclusions", "working_context_refs")
        elif not data.get("working_context_refs"):
            add_warning("active-task-missing-working-context-ref", task_ref, f"active WCTX exists {active_wctx}, but task.working_context_refs is empty", "working_context_refs")

    for entry_ref, entry in entries.items():
        status = str(entry.get("status", "") or "")
        workspace_ref = str(entry.get("workspace_ref", "") or "").strip()
        project_ref = str(entry.get("project_ref", "") or "").strip()
        if status == "active":
            if not workspace_ref:
                add_issue("active-cix-without-workspace", entry_ref, "active CIX has no workspace_ref", "workspace_ref")
            if not project_ref:
                add_issue("active-cix-without-project", entry_ref, "active CIX has no project_ref", "project_ref")
        if workspace_ref and _type_graph_record_type(records, workspace_ref) != "workspace":
            add_issue("cix-workspace-ref", entry_ref, f"{workspace_ref} is not a workspace", "workspace_ref")
        if project_ref and _type_graph_record_type(records, project_ref) != "project":
            add_issue("cix-project-ref", entry_ref, f"{project_ref} is not a project", "project_ref")
        if workspace_ref and project_ref and project_ref not in workspace_project_refs.get(workspace_ref, set()):
            add_issue("cix-project-workspace-mismatch", entry_ref, f"{project_ref} is not listed in {workspace_ref}.project_refs", "project_ref")

    record_counts: dict[str, int] = {}
    for data in records.values():
        record_type = str(data.get("record_type", "") or "unknown")
        record_counts[record_type] = record_counts.get(record_type, 0) + 1
    cix_counts: dict[str, int] = {}
    for entry in entries.values():
        status = str(entry.get("status", "") or "unknown")
        cix_counts[status] = cix_counts.get(status, 0) + 1

    payload = {
        "type_graph_is_proof": False,
        "chains": TYPE_GRAPH_CHAINS,
        "counts": {
            "records": dict(sorted(record_counts.items())),
            "cix": dict(sorted(cix_counts.items())),
        },
        "issues": issues,
        "warnings": warnings,
        "issue_count": len(issues),
        "warning_count": len(warnings),
    }
    return payload, 1 if issues else 0


def type_graph_text_lines(payload: dict, *, include_check: bool) -> list[str]:
    lines = ["# TEP Type Graph\n", "\n"]
    lines.append("Navigation/typing map only; proof still requires `SRC-* -> CLM-*` evidence.\n\n")
    for group in payload.get("chains", []):
        lines.append(f"## {group.get('name', '')}\n")
        for chain in group.get("chains", []):
            lines.append(f"- `{chain}`\n")
        lines.append("\n")
    counts = payload.get("counts", {})
    lines.append("## Counts\n")
    record_counts = counts.get("records", {})
    lines.append("- records: " + ", ".join(f"{key}={value}" for key, value in record_counts.items()) + "\n")
    cix_counts = counts.get("cix", {})
    lines.append("- CIX: " + ", ".join(f"{key}={value}" for key, value in cix_counts.items()) + "\n")
    if include_check:
        lines.append("\n## Check\n")
        lines.append(f"- issues: `{payload.get('issue_count', 0)}`\n")
        lines.append(f"- warnings: `{payload.get('warning_count', 0)}`\n")
        for item in payload.get("issues", [])[:50]:
            lines.append(f"- ISSUE `{item.get('kind')}` `{item.get('ref')}` {item.get('field')}: {item.get('message')}\n")
        for item in payload.get("warnings", [])[:50]:
            lines.append(f"- WARNING `{item.get('kind')}` `{item.get('ref')}` {item.get('field')}: {item.get('message')}\n")
    return lines


def cmd_type_graph(root: Path, check: bool, output_format: str) -> int:
    payload, exit_code = build_type_graph_report(root)
    if output_format == "json":
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        for line in type_graph_text_lines(payload, include_check=check):
            print(line, end="")
    return exit_code if check else 0


def cmd_promote_model_to_domain(root: Path, model_ref: str, note: str | None) -> int:
    records, exit_code = load_clean_context(root)
    if exit_code:
        return 1
    if model_ref not in records:
        print(f"missing record {model_ref}")
        return 1
    source = records[model_ref]
    if source.get("record_type") != "model":
        print(f"{model_ref} must reference a model record")
        return 1
    if str(source.get("knowledge_class", "")).strip() != "investigation":
        print(f"{model_ref} is not an investigation model")
        return 1
    if str(source.get("status", "")).strip() != "stable":
        print(f"{model_ref} must be stable before promotion to domain knowledge")
        return 1
    if public_record_payload(source).get("hypothesis_refs"):
        print(f"{model_ref} cannot be promoted while it still depends on hypothesis_refs")
        return 1

    scope = str(source.get("scope", "")).strip()
    aspect = str(source.get("aspect", "")).strip()
    if source.get("is_primary") is True:
        for other_id, other in records.items():
            if other_id == model_ref or other.get("record_type") != "model":
                continue
            if str(other.get("scope", "")).strip() != scope or str(other.get("aspect", "")).strip() != aspect:
                continue
            if other.get("is_primary") is True and str(other.get("status", "")).strip() != "superseded":
                print(f"cannot promote {model_ref}: another primary model already exists for scope={scope} aspect={aspect}: {other_id}")
                return 1

    timestamp = now_timestamp()
    promoted_id = next_record_id(records, "MODEL-")
    source_payload, promoted_payload = promote_model_to_domain_payloads(
        source_payload=public_record_payload(source),
        timestamp=timestamp,
        source_model_ref=model_ref,
        promoted_model_id=promoted_id,
        note=note,
    )

    merged_records, errors = validate_mutated_records(
        root,
        records,
        {
            model_ref: source_payload,
            promoted_id: promoted_payload,
        },
    )
    if errors:
        print_errors(errors)
        return 1
    return persist_mutated_records(
        root,
        merged_records,
        [model_ref, promoted_id],
        f"Promoted model {model_ref} to domain knowledge as {promoted_id}",
    )


def cmd_promote_flow_to_domain(root: Path, flow_ref: str, note: str | None) -> int:
    records, exit_code = load_clean_context(root)
    if exit_code:
        return 1
    if flow_ref not in records:
        print(f"missing record {flow_ref}")
        return 1
    source = records[flow_ref]
    if source.get("record_type") != "flow":
        print(f"{flow_ref} must reference a flow record")
        return 1
    if str(source.get("knowledge_class", "")).strip() != "investigation":
        print(f"{flow_ref} is not an investigation flow")
        return 1
    if str(source.get("status", "")).strip() != "stable":
        print(f"{flow_ref} must be stable before promotion to domain knowledge")
        return 1

    preconditions = source.get("preconditions", {})
    oracle = source.get("oracle", {})
    if isinstance(preconditions, dict) and preconditions.get("hypothesis_refs"):
        print(f"{flow_ref} cannot be promoted while preconditions still depend on hypothesis_refs")
        return 1
    if isinstance(oracle, dict) and oracle.get("hypothesis_refs"):
        print(f"{flow_ref} cannot be promoted while oracle still depends on hypothesis_refs")
        return 1

    scope = str(source.get("scope", "")).strip()
    if source.get("is_primary") is True:
        for other_id, other in records.items():
            if other_id == flow_ref or other.get("record_type") != "flow":
                continue
            if str(other.get("scope", "")).strip() != scope:
                continue
            if other.get("is_primary") is True and str(other.get("status", "")).strip() != "superseded":
                print(f"cannot promote {flow_ref}: another primary flow already exists for scope={scope}: {other_id}")
                return 1

    timestamp = now_timestamp()
    promoted_id = next_record_id(records, "FLOW-")
    source_payload, promoted_payload = promote_flow_to_domain_payloads(
        source_payload=public_record_payload(source),
        timestamp=timestamp,
        source_flow_ref=flow_ref,
        promoted_flow_id=promoted_id,
        note=note,
    )

    merged_records, errors = validate_mutated_records(
        root,
        records,
        {
            flow_ref: source_payload,
            promoted_id: promoted_payload,
        },
    )
    if errors:
        print_errors(errors)
        return 1
    return persist_mutated_records(
        root,
        merged_records,
        [flow_ref, promoted_id],
        f"Promoted flow {flow_ref} to domain knowledge as {promoted_id}",
    )


def cmd_mark_stale_from_claim(root: Path, claim_ref: str, note: str | None) -> int:
    records, exit_code = load_clean_context(root)
    if exit_code:
        return 1
    if claim_ref not in records:
        print(f"missing record {claim_ref}")
        return 1
    if records[claim_ref].get("record_type") != "claim":
        print(f"{claim_ref} must reference a claim record")
        return 1

    impact = collect_dependency_impact(root, records, claim_ref)
    target_ids = stale_knowledge_target_ids(records, impact["transitive"])
    if not target_ids:
        print(f"No model/flow records need stale marking from {claim_ref}")
        return 0

    timestamp = now_timestamp()
    updates = mark_knowledge_records_stale_payloads(records, target_ids, timestamp, claim_ref, note)

    merged_records, errors = validate_mutated_records(root, records, updates)
    if errors:
        print_errors(errors)
        return 1
    return persist_mutated_records(
        root,
        merged_records,
        target_ids,
        f"Marked stale from {claim_ref}: {', '.join(target_ids)}",
    )


def cmd_rollback_report(root: Path, claim_ref: str) -> int:
    records, exit_code = load_clean_context(root)
    if exit_code:
        return 1
    if claim_ref not in records:
        print(f"missing record {claim_ref}")
        return 1
    if records[claim_ref].get("record_type") != "claim":
        print(f"{claim_ref} must reference a claim record")
        return 1

    impact = collect_dependency_impact(root, records, claim_ref)
    hypothesis_entries, _ = load_hypotheses_index(root)
    payload = build_rollback_report_payload(records, claim_ref, impact, hypothesis_entries)
    for line in rollback_report_text_lines(payload):
        print(line)
    return 0


def cmd_record_plan(
    root: Path,
    scope: str,
    title: str,
    priority: str,
    status: str,
    justified_by: list[str],
    steps: list[str],
    success_criteria: list[str],
    blocked_by: list[str],
    project_refs: list[str],
    task_refs: list[str],
    tags: list[str],
    note: str,
) -> int:
    records, exit_code = load_clean_context(root)
    if exit_code:
        return 1

    timestamp = now_timestamp()
    payload = build_plan_payload(
        record_id=next_record_id(records, "PLN-"),
        timestamp=timestamp,
        scope=scope,
        title=title,
        priority=priority,
        status=status,
        justified_by=justified_by,
        steps=steps,
        success_criteria=success_criteria,
        blocked_by=blocked_by,
        project_refs=project_refs_for_write(root, project_refs),
        task_refs=task_refs,
        tags=tags,
        note=note,
    )
    return persist_candidate(root, records, payload, "plan")


def cmd_record_debt(
    root: Path,
    scope: str,
    title: str,
    priority: str,
    status: str,
    evidence_refs: list[str],
    plan_refs: list[str],
    project_refs: list[str],
    task_refs: list[str],
    tags: list[str],
    note: str,
) -> int:
    records, exit_code = load_clean_context(root)
    if exit_code:
        return 1

    timestamp = now_timestamp()
    payload = build_debt_payload(
        record_id=next_record_id(records, "DEBT-"),
        timestamp=timestamp,
        scope=scope,
        title=title,
        priority=priority,
        status=status,
        evidence_refs=evidence_refs,
        plan_refs=plan_refs,
        project_refs=project_refs_for_write(root, project_refs),
        task_refs=task_refs,
        tags=tags,
        note=note,
    )
    return persist_candidate(root, records, payload, "debt")


def cmd_record_feedback(
    root: Path,
    scope: str,
    kind: str,
    severity: str,
    surface: str,
    title: str,
    actual: str,
    expected: str | None,
    repro_steps: list[str],
    suggestions: list[str],
    evidence_refs: list[str],
    project_refs: list[str],
    task_refs: list[str],
    tags: list[str],
    note: str,
    origin_ref: str,
    created_by: str,
) -> int:
    records, exit_code = load_clean_context(root)
    if exit_code:
        return 1

    timestamp = now_timestamp()
    resolved_project_refs = project_refs_for_write(root, project_refs)
    resolved_task_refs = task_refs_for_write(root, task_refs)
    feedback_tags = sorted({*tags, "feedback", f"feedback:{kind}", f"surface:{surface}"})

    source_id = next_record_id(records, "SRC-")
    quote_parts = [f"{title.strip()}: {actual.strip()}"]
    if expected and expected.strip():
        quote_parts.append(f"Expected: {expected.strip()}")
    source_payload = build_source_payload(
        record_id=source_id,
        source_kind="memory",
        scope=scope,
        critique_status="audited",
        origin_kind="agent-feedback",
        origin_ref=origin_ref,
        quote=" ".join(quote_parts),
        artifact_refs=[],
        confidence=None,
        independence_group=f"agent-feedback-{created_by}-{timestamp}",
        captured_at=timestamp,
        captured_timestamp=timestamp,
        independence_timestamp=timestamp,
        project_refs=resolved_project_refs,
        task_refs=resolved_task_refs,
        tags=feedback_tags,
        red_flags=[],
        note=f"Agent feedback source created_by={created_by}.",
    )
    source_candidate, source_errors = validate_candidate_record(root, records, source_payload)
    if source_errors:
        print_errors(source_errors)
        return 1

    note_lines = [
        f"kind={kind}",
        f"surface={surface}",
        f"severity={severity}",
        f"created_by={created_by}",
        "",
        "Actual:",
        actual.strip(),
    ]
    if expected and expected.strip():
        note_lines.extend(["", "Expected:", expected.strip()])
    if repro_steps:
        note_lines.extend(["", "Reproduction:"])
        note_lines.extend(f"- {step.strip()}" for step in repro_steps if step.strip())
    if suggestions:
        note_lines.extend(["", "Suggested fixes:"])
        note_lines.extend(f"- {suggestion.strip()}" for suggestion in suggestions if suggestion.strip())
    if note.strip():
        note_lines.extend(["", "Note:", note.strip()])

    records_with_source = dict(records)
    records_with_source[source_id] = source_candidate
    debt_payload = build_debt_payload(
        record_id=next_record_id(records_with_source, "DEBT-"),
        timestamp=timestamp,
        scope=scope,
        title=f"[feedback:{kind}] {title.strip()}",
        priority=FEEDBACK_SEVERITY_TO_PRIORITY[severity],
        status="open",
        evidence_refs=[source_id, *evidence_refs],
        plan_refs=[],
        project_refs=resolved_project_refs,
        task_refs=resolved_task_refs,
        tags=feedback_tags,
        note="\n".join(note_lines).strip(),
    )
    debt_candidate, debt_errors = validate_candidate_record(root, records_with_source, debt_payload)
    if debt_errors:
        print_errors(debt_errors)
        return 1

    write_json_file(record_path(root, "source", source_payload["id"]), source_payload)
    write_json_file(record_path(root, "debt", debt_payload["id"]), debt_payload)
    updated_records = dict(records_with_source)
    updated_records[debt_payload["id"]] = debt_candidate
    refresh_generated_outputs(root, updated_records)
    invalidate_hydration_state(root, f"recorded feedback {debt_payload['id']}")
    print(f"Recorded source {source_payload['id']} at {record_path(root, 'source', source_payload['id'])}")
    print(f"Recorded feedback debt {debt_payload['id']} at {record_path(root, 'debt', debt_payload['id'])}")
    return 0


def cmd_record_source(
    root: Path,
    scope: str,
    source_kind: str,
    critique_status: str,
    origin_kind: str,
    origin_ref: str,
    quote: str,
    artifact_refs: list[str],
    confidence: str | None,
    independence_group: str | None,
    captured_at: str | None,
    project_refs: list[str],
    task_refs: list[str],
    tags: list[str],
    red_flags: list[str],
    note: str,
) -> int:
    records, exit_code = load_clean_context(root)
    if exit_code:
        return 1

    payload = build_source_payload(
        record_id=next_record_id(records, "SRC-"),
        source_kind=source_kind,
        scope=scope,
        critique_status=critique_status,
        origin_kind=origin_kind,
        origin_ref=origin_ref,
        quote=quote,
        artifact_refs=artifact_refs,
        confidence=confidence,
        independence_group=independence_group,
        captured_at=captured_at,
        captured_timestamp=now_timestamp(),
        independence_timestamp=now_timestamp(),
        project_refs=project_refs_for_write(root, project_refs),
        task_refs=task_refs,
        tags=tags,
        red_flags=red_flags,
        note=note,
    )
    return persist_candidate(root, records, payload, "source")


EVIDENCE_KIND_DEFAULTS = {
    "file-line": ("code", "file"),
    "command-output": ("runtime", "command"),
    "user-confirmation": ("theory", "user_prompt"),
    "artifact": ("runtime", "artifact"),
}


MAX_AUTO_FILE_ARTIFACT_BYTES = 1024 * 1024


def resolve_evidence_file_path(path_value: str | None) -> Path | None:
    if not path_value or not path_value.strip():
        return None
    path = Path(path_value).expanduser()
    if not path.is_absolute():
        path = Path.cwd() / path
    return path.resolve()


def cix_refs_for_path(root: Path, resolved_path: Path | None) -> list[str]:
    if resolved_path is None:
        return []
    entries, _ = load_code_index_entries(root)
    records, _ = load_records(root)
    refs: list[str] = []
    for entry_id, entry in entries.items():
        target = entry.get("target", {})
        if not isinstance(target, dict) or target.get("kind") != "file":
            continue
        target_path = str(target.get("path", "")).strip()
        if not target_path:
            continue
        candidates = [Path(target_path)]
        project_ref = str(entry.get("project_ref", "")).strip()
        project = records.get(project_ref) if project_ref else None
        if project and isinstance(project.get("root_refs"), list):
            for root_ref in project.get("root_refs", []):
                root_path = Path(str(root_ref)).expanduser()
                candidates.append(root_path / target_path)
        for candidate in candidates:
            try:
                if candidate.expanduser().resolve() == resolved_path:
                    refs.append(entry_id)
                    break
            except OSError:
                continue
    return sorted(set(refs))


def build_file_support_record(
    root: Path,
    records: dict[str, dict],
    scope: str,
    path_value: str,
    timestamp: str,
    artifact_refs: list[str],
    project_refs: list[str],
    task_refs: list[str],
    workspace_refs: list[str],
    tags: list[str],
    note: str,
) -> tuple[dict, list[str]]:
    resolved_path = resolve_evidence_file_path(path_value)
    metadata = file_metadata(resolved_path)
    auto_artifacts = list(artifact_refs)
    if resolved_path and metadata.get("exists") and int(metadata.get("size_bytes") or 0) <= MAX_AUTO_FILE_ARTIFACT_BYTES:
        _, artifact_ref = copy_artifact_file(root, resolved_path)
        auto_artifacts.append(artifact_ref)
    cix_refs = cix_refs_for_path(root, resolved_path)
    payload = build_file_payload(
        record_id=next_record_id(records, "FILE-"),
        scope=scope,
        captured_at=timestamp,
        original_ref=path_value,
        resolved_path=str(resolved_path or ""),
        file_kind=infer_file_kind(resolved_path, auto_artifacts),
        metadata=metadata,
        artifact_refs=sorted(set(auto_artifacts)),
        cix_refs=cix_refs,
        workspace_refs=workspace_refs,
        project_refs=project_refs,
        task_refs=task_refs,
        tags=[*tags, "graph-v2"],
        note=note or "file support metadata",
    )
    return payload, auto_artifacts


def build_run_support_record(
    records: dict[str, dict],
    scope: str,
    command: str,
    timestamp: str,
    cwd: str,
    exit_code: int | None,
    stdout_quote: str,
    stderr_quote: str,
    action_kind: str | None,
    artifact_refs: list[str],
    project_refs: list[str],
    task_refs: list[str],
    workspace_refs: list[str],
    tags: list[str],
    note: str,
) -> dict:
    return build_run_payload(
        record_id=next_record_id(records, "RUN-"),
        scope=scope,
        captured_at=timestamp,
        tool="bash",
        command=command,
        cwd=cwd,
        exit_code=exit_code,
        stdout_quote=stdout_quote,
        stderr_quote=stderr_quote,
        action_kind=action_kind,
        artifact_refs=artifact_refs,
        workspace_refs=workspace_refs,
        project_refs=project_refs,
        task_refs=task_refs,
        tags=[*tags, "graph-v2"],
        note=note or "bash run support metadata",
    )


def resolve_record_evidence_origin(
    kind: str,
    path_value: str | None,
    line: int | None,
    end_line: int | None,
    command: str | None,
    input_refs: list[str],
    artifact_refs: list[str],
    origin_ref: str | None,
) -> tuple[str, str, str, list[str]]:
    source_kind, origin_kind = EVIDENCE_KIND_DEFAULTS[kind]
    errors: list[str] = []
    if origin_ref and origin_ref.strip():
        return source_kind, origin_kind, origin_ref.strip(), errors

    if kind == "file-line":
        if not path_value or not path_value.strip():
            errors.append("record-evidence --kind file-line requires --path")
        if line is None:
            errors.append("record-evidence --kind file-line requires --line")
        if line is not None and line <= 0:
            errors.append("--line must be positive")
        if end_line is not None and end_line <= 0:
            errors.append("--end-line must be positive")
        if line is not None and end_line is not None and end_line < line:
            errors.append("--end-line must be greater than or equal to --line")
        if errors:
            return source_kind, origin_kind, "", errors
        if end_line and end_line != line:
            return source_kind, origin_kind, f"{path_value.strip()}:{line}-{end_line}", errors
        return source_kind, origin_kind, f"{path_value.strip()}:{line}", errors

    if kind == "command-output":
        if not command or not command.strip():
            errors.append("record-evidence --kind command-output requires --command")
            return source_kind, origin_kind, "", errors
        return source_kind, origin_kind, command.strip(), errors

    if kind == "user-confirmation":
        if input_refs:
            return source_kind, origin_kind, "inputs:" + ",".join(input_refs), errors
        return source_kind, origin_kind, "user-confirmation", errors

    if kind == "artifact":
        if not artifact_refs:
            errors.append("record-evidence --kind artifact requires at least one --artifact-ref")
            return source_kind, origin_kind, "", errors
        return source_kind, origin_kind, artifact_refs[0], errors

    errors.append(f"unsupported evidence kind: {kind}")
    return source_kind, origin_kind, "", errors


def cmd_record_evidence(
    root: Path,
    scope: str,
    kind: str,
    quote: str,
    path_value: str | None,
    line: int | None,
    end_line: int | None,
    command: str | None,
    cwd: str | None,
    exit_code: int | None,
    stdout_quote: str | None,
    stderr_quote: str | None,
    action_kind: str | None,
    input_refs: list[str],
    artifact_refs: list[str],
    origin_ref: str | None,
    critique_status: str,
    confidence: str | None,
    project_refs: list[str],
    task_refs: list[str],
    tags: list[str],
    red_flags: list[str],
    note: str,
    claim_statement: str | None,
    claim_plane: str | None,
    claim_status: str,
    claim_kind: str | None,
    support_refs: list[str],
    contradiction_refs: list[str],
    derived_from: list[str],
    recorded_at: str | None,
) -> int:
    records, exit_code = load_clean_context(root)
    if exit_code:
        return 1

    resolved_input_refs = list(dict.fromkeys(ref.strip() for ref in input_refs if ref.strip()))
    for input_ref in resolved_input_refs:
        record = records.get(input_ref)
        if not record or record.get("record_type") != "input":
            print(f"{input_ref} must reference an input record")
            return 1

    source_kind, origin_kind, resolved_origin_ref, origin_errors = resolve_record_evidence_origin(
        kind,
        path_value,
        line,
        end_line,
        command,
        resolved_input_refs,
        artifact_refs,
        origin_ref,
    )
    if origin_errors:
        for error in origin_errors:
            print(error)
        return 1

    timestamp = now_timestamp()
    resolved_project_refs = project_refs_for_write(root, project_refs)
    resolved_task_refs = task_refs_for_write(root, task_refs)
    resolved_workspace_refs = workspace_refs_for_write(root, [])
    updates: dict[str, dict] = {}
    changed_ids: list[str] = []
    resolved_artifact_refs = list(dict.fromkeys(ref.strip() for ref in artifact_refs if ref.strip()))
    file_ref = ""
    run_ref = ""

    if kind == "file-line" and path_value:
        file_payload, auto_artifacts = build_file_support_record(
            root,
            records,
            scope,
            path_value,
            timestamp,
            resolved_artifact_refs,
            resolved_project_refs,
            resolved_task_refs,
            resolved_workspace_refs,
            tags,
            "file evidence support",
        )
        file_ref = str(file_payload["id"])
        resolved_artifact_refs = sorted(set(auto_artifacts))
        updates[file_ref] = file_payload
        changed_ids.append(file_ref)

    if kind == "command-output" and command:
        run_payload = build_run_support_record(
            {**records, **updates},
            scope,
            command,
            timestamp,
            cwd or str(Path.cwd()),
            exit_code,
            stdout_quote if stdout_quote is not None else quote,
            stderr_quote or "",
            action_kind,
            resolved_artifact_refs,
            resolved_project_refs,
            resolved_task_refs,
            resolved_workspace_refs,
            tags,
            "command-output evidence support",
        )
        run_ref = str(run_payload["id"])
        updates[run_ref] = run_payload
        changed_ids.append(run_ref)

    source_id = next_record_id(records, "SRC-")
    source_payload = build_source_payload(
        record_id=source_id,
        source_kind=source_kind,
        scope=scope,
        critique_status=critique_status,
        origin_kind=origin_kind,
        origin_ref=resolved_origin_ref,
        quote=quote,
        artifact_refs=resolved_artifact_refs,
        confidence=confidence,
        independence_group=None,
        captured_at=None,
        captured_timestamp=timestamp,
        independence_timestamp=timestamp,
        project_refs=resolved_project_refs,
        task_refs=resolved_task_refs,
        tags=[*tags, "graph-v2", f"evidence-kind:{kind}"],
        red_flags=red_flags,
        note=note.strip() or f"record-evidence source from {kind}",
    )
    if resolved_input_refs:
        source_payload["input_refs"] = resolved_input_refs
    if resolved_workspace_refs:
        source_payload["workspace_refs"] = resolved_workspace_refs
    if file_ref:
        source_payload["file_refs"] = [file_ref]
        cix_refs = safe_list(updates[file_ref], "cix_refs")
        if cix_refs:
            source_payload["cix_refs"] = cix_refs
    if run_ref:
        source_payload["run_refs"] = [run_ref]

    updates[source_id] = source_payload
    changed_ids.append(source_id)
    claim_id = ""
    if claim_statement and claim_statement.strip():
        resolved_claim_plane = claim_plane or {
            "code": "code",
            "runtime": "runtime",
            "theory": "theory",
            "memory": "theory",
        }.get(source_kind, "theory")
        claim_id = next_record_id({**records, source_id: source_payload}, "CLM-")
        claim_payload = build_claim_payload(
            record_id=claim_id,
            timestamp=timestamp,
            scope=scope,
            plane=resolved_claim_plane,
            status=claim_status,
            statement=claim_statement,
            source_refs=[source_id],
            support_refs=support_refs,
            contradiction_refs=contradiction_refs,
            derived_from=derived_from,
            claim_kind=claim_kind,
            confidence=confidence,
            comparison=None,
            logic=None,
            recorded_at=recorded_at,
            project_refs=resolved_project_refs,
            task_refs=resolved_task_refs,
            tags=[*tags, "graph-v2", f"evidence-kind:{kind}"],
            red_flags=red_flags,
            note=note.strip() or f"record-evidence claim from {kind}",
        )
        if resolved_input_refs:
            claim_payload["input_refs"] = resolved_input_refs
        if resolved_workspace_refs:
            claim_payload["workspace_refs"] = resolved_workspace_refs
        if file_ref:
            claim_payload["file_refs"] = [file_ref]
        if run_ref:
            claim_payload["run_refs"] = [run_ref]
        updates[claim_id] = claim_payload
        changed_ids.append(claim_id)

    derived_refs = [source_id]
    if claim_id:
        derived_refs.append(claim_id)
    for input_ref in resolved_input_refs:
        input_payload = public_record_payload(records[input_ref])
        existing = [str(ref).strip() for ref in input_payload.get("derived_record_refs", []) if str(ref).strip()]
        input_payload["derived_record_refs"] = sorted(set(existing + derived_refs))
        input_payload["note"] = append_note(
            str(input_payload.get("note", "")),
            f"record-evidence linked derived records: {', '.join(derived_refs)}",
        )
        updates[input_ref] = input_payload
        changed_ids.append(input_ref)

    merged_records, errors = validate_mutated_records(root, records, updates)
    if errors:
        print_errors(errors)
        return 1
    result = persist_mutated_records(
        root,
        merged_records,
        changed_ids,
        f"Recorded evidence {source_id}{f' and claim {claim_id}' if claim_id else ''}",
    )
    if result:
        return result
    print(f"Recorded source {source_id} at {record_path(root, 'source', source_id)}")
    if claim_id:
        print(f"Recorded claim {claim_id} at {record_path(root, 'claim', claim_id)}")
    if resolved_input_refs:
        print(f"Classified input(s) {', '.join(resolved_input_refs)} with derived record(s): {', '.join(derived_refs)}")
    return 0


def cmd_record_input(
    root: Path,
    scope: str,
    input_kind: str,
    origin_kind: str,
    origin_ref: str,
    text: str,
    artifact_refs: list[str],
    session_ref: str | None,
    derived_record_refs: list[str],
    captured_at: str | None,
    project_refs: list[str],
    task_refs: list[str],
    tags: list[str],
    note: str,
) -> int:
    records, exit_code = load_clean_context(root)
    if exit_code:
        return 1

    payload = build_input_payload(
        record_id=next_record_id(records, "INP-"),
        scope=scope,
        input_kind=input_kind,
        origin_kind=origin_kind,
        origin_ref=origin_ref,
        text=text,
        artifact_refs=artifact_refs,
        session_ref=session_ref,
        derived_record_refs=derived_record_refs,
        captured_at=captured_at,
        captured_timestamp=now_timestamp(),
        project_refs=project_refs_for_write(root, project_refs),
        task_refs=task_refs_for_write(root, task_refs),
        tags=tags,
        note=note,
    )
    return persist_candidate(root, records, payload, "input")


def cmd_record_run(
    root: Path,
    scope: str,
    command: str,
    cwd: str | None,
    exit_code: int | None,
    stdout_quote: str | None,
    stderr_quote: str | None,
    action_kind: str | None,
    artifact_refs: list[str],
    project_refs: list[str],
    task_refs: list[str],
    tags: list[str],
    note: str,
) -> int:
    records, exit_code_load = load_clean_context(root)
    if exit_code_load:
        return 1
    if not command.strip():
        print("record-run requires --command")
        return 1
    timestamp = now_timestamp()
    payload = build_run_support_record(
        records,
        scope,
        command,
        timestamp,
        cwd or str(Path.cwd()),
        exit_code,
        stdout_quote or "",
        stderr_quote or "",
        action_kind,
        [ref.strip() for ref in artifact_refs if ref.strip()],
        project_refs_for_write(root, project_refs),
        task_refs_for_write(root, task_refs),
        workspace_refs_for_write(root, []),
        tags,
        note or "bash run captured by hook/API",
    )
    return persist_candidate(root, records, payload, "run")


def cmd_classify_input(root: Path, input_ref: str, derived_record_refs: list[str], note: str | None) -> int:
    records, exit_code = load_clean_context(root)
    if exit_code:
        return 1
    input_record = records.get(input_ref)
    if not input_record or input_record.get("record_type") != "input":
        print(f"{input_ref} must reference an input record")
        return 1
    refs = [ref.strip() for ref in derived_record_refs if ref.strip()]
    if not refs:
        print("classify-input requires at least one --derived-record")
        return 1
    missing = [ref for ref in refs if ref not in records]
    if missing:
        print("missing derived record(s): " + ", ".join(missing))
        return 1
    existing_refs = [
        str(ref).strip()
        for ref in input_record.get("derived_record_refs", [])
        if str(ref).strip()
    ]
    payload = public_record_payload(input_record)
    payload["derived_record_refs"] = sorted(set(existing_refs + refs))
    if note:
        payload["note"] = append_note(str(payload.get("note", "")), f"classification: {note}")

    merged_records, errors = validate_mutated_records(root, records, {input_ref: payload})
    if errors:
        print_errors(errors)
        return 1
    return persist_mutated_records(
        root,
        merged_records,
        [input_ref],
        f"Classified input {input_ref} with derived record(s): {', '.join(refs)}",
    )


def cmd_record_claim(
    root: Path,
    scope: str,
    plane: str,
    status: str,
    statement: str,
    source_refs: list[str],
    support_refs: list[str],
    contradiction_refs: list[str],
    derived_from: list[str],
    claim_kind: str | None,
    confidence: str | None,
    comparison: dict | None,
    logic: dict | None,
    recorded_at: str | None,
    project_refs: list[str],
    task_refs: list[str],
    tags: list[str],
    red_flags: list[str],
    note: str,
) -> int:
    records, exit_code = load_clean_context(root)
    if exit_code:
        return 1

    payload = build_claim_payload(
        record_id=next_record_id(records, "CLM-"),
        timestamp=now_timestamp(),
        scope=scope,
        plane=plane,
        status=status,
        statement=statement,
        source_refs=source_refs,
        support_refs=support_refs,
        contradiction_refs=contradiction_refs,
        derived_from=derived_from,
        claim_kind=claim_kind,
        confidence=confidence,
        comparison=comparison,
        logic=logic,
        recorded_at=recorded_at,
        project_refs=project_refs_for_write(root, project_refs),
        task_refs=task_refs,
        tags=tags,
        red_flags=red_flags,
        note=note,
    )
    return persist_candidate(root, records, payload, "claim")


def resolve_record_link_refs(
    records: dict[str, dict],
    scoped_payload: dict | None,
    left_ref: str | None,
    right_ref: str | None,
    probe_index: int | None,
) -> tuple[list[str], str | None]:
    if probe_index is not None:
        if left_ref or right_ref:
            return [], "use either --probe-index or --left/--right, not both"
        if not scoped_payload:
            return [], "attention index is missing or empty; run `attention-index build` first"
        probes = scoped_payload.get("probes", [])
        index = max(1, probe_index) - 1
        if not probes:
            return [], "no curiosity probes available for this scope"
        if index >= len(probes):
            return [], f"probe index out of range: {probe_index}; available={len(probes)}"
        refs = [str(ref) for ref in probes[index].get("record_refs", []) if str(ref) in records]
        if len(refs) != 2:
            return [], "selected probe must contain exactly two existing record refs"
        return refs, None
    if not left_ref or not right_ref:
        return [], "record-link requires --probe-index or both --left and --right"
    refs = [left_ref, right_ref]
    for ref in refs:
        if ref not in records:
            return [], f"missing record {ref}"
        if records[ref].get("record_type") != "claim":
            return [], f"{ref} must reference a claim record"
    if left_ref == right_ref:
        return [], "left and right records must be different"
    return refs, None


def cmd_record_link(
    root: Path,
    scope: str,
    left_ref: str | None,
    right_ref: str | None,
    probe_index: int | None,
    probe_scope: str,
    mode: str,
    relation: str,
    quote: str,
    confidence: str | None,
    project_refs: list[str],
    task_refs: list[str],
    tags: list[str],
    note: str,
) -> int:
    records, exit_code = load_clean_context(root)
    if exit_code:
        return 1
    scoped_payload = None
    if probe_index is not None:
        attention_payload = load_attention_payload(root)
        if attention_payload:
            scoped_payload = scoped_attention_payload(root, attention_payload, probe_scope, mode)
    refs, error = resolve_record_link_refs(records, scoped_payload, left_ref, right_ref, probe_index)
    if error:
        print(error)
        return 1
    if relation not in RECORD_LINK_RELATIONS:
        print(f"invalid relation: {relation}")
        return 1
    timestamp = now_timestamp()
    source_id = next_record_id(records, "SRC-")
    source_payload = build_source_payload(
        record_id=source_id,
        source_kind="runtime",
        scope=scope,
        critique_status="accepted",
        origin_kind="agent_review",
        origin_ref=f"record-link:{relation}",
        quote=quote,
        artifact_refs=[],
        confidence=confidence,
        independence_group=None,
        captured_at=None,
        captured_timestamp=timestamp,
        independence_timestamp=timestamp,
        project_refs=project_refs_for_write(root, project_refs),
        task_refs=task_refs_for_write(root, task_refs),
        tags=[*tags, "record-link", f"relation:{relation}"],
        red_flags=[],
        note=f"Source for reviewed record link: {note.strip()}",
    )
    verb = RECORD_LINK_RELATIONS[relation]
    claim_id = next_record_id({**records, source_id: source_payload}, "CLM-")
    statement = f"Reviewed records {refs[0]} and {refs[1]} {verb}."
    claim_payload = build_claim_payload(
        record_id=claim_id,
        timestamp=timestamp,
        scope=scope,
        plane="runtime",
        status="supported",
        statement=statement,
        source_refs=[source_id],
        support_refs=refs,
        contradiction_refs=[],
        derived_from=[],
        claim_kind="factual",
        confidence=confidence,
        comparison=None,
        logic=None,
        recorded_at=None,
        project_refs=project_refs_for_write(root, project_refs),
        task_refs=task_refs_for_write(root, task_refs),
        tags=[*tags, "record-link", f"relation:{relation}"],
        red_flags=[],
        note=note,
    )
    merged_records, errors = validate_mutated_records(root, records, {source_id: source_payload, claim_id: claim_payload})
    if errors:
        print_errors(errors)
        return 1
    taps, tap_errors = load_tap_events(root)
    if tap_errors:
        print_errors(tap_errors)
        return 1
    access_events, access_errors = load_access_events(root)
    if access_errors:
        print_errors(access_errors)
        return 1
    topic_payload = load_or_build_topic_payload(root, merged_records)
    attention_payload = build_attention_index(merged_records, topic_payload, taps, access_events=access_events)
    result = persist_mutated_records(
        root,
        merged_records,
        [source_id, claim_id],
        f"Recorded link claim {claim_id} with source {source_id}",
    )
    if result:
        return result
    write_attention_index_reports(root, attention_payload)
    invalidate_hydration_state(root, f"recorded link claim {claim_id} and rebuilt attention index")
    print(
        f"Rebuilt attention index: records={attention_payload['record_count']} "
        f"clusters={attention_payload['cluster_count']} probes={len(attention_payload['probes'])}"
    )
    return 0


def cmd_record_permission(
    root: Path,
    scope: str,
    applies_to: str | None,
    granted_by: str,
    grants: list[str],
    project_refs: list[str],
    task_refs: list[str],
    granted_at: str | None,
    tags: list[str],
    note: str,
) -> int:
    records, exit_code = load_clean_context(root)
    if exit_code:
        return 1
    timestamp = now_timestamp()
    resolved_applies_to, resolved_project_refs, resolved_task_refs = resolve_permission_scope(
        applies_to=applies_to,
        project_refs=project_refs,
        task_refs=task_refs,
        current_project=current_project_ref(root),
        current_task=current_task_ref(root),
    )
    payload = build_permission_payload(
        record_id=next_record_id(records, "PRM-"),
        timestamp=timestamp,
        scope=scope,
        applies_to=resolved_applies_to,
        granted_by=granted_by,
        grants=grants,
        project_refs=resolved_project_refs,
        task_refs=resolved_task_refs,
        granted_at=granted_at,
        tags=tags,
        note=note,
    )
    return persist_candidate(root, records, payload, "permission")


def cmd_record_action(
    root: Path,
    kind: str,
    scope: str,
    justified_by: list[str],
    safety_class: str,
    status: str,
    planned_at: str | None,
    executed_at: str | None,
    project_refs: list[str],
    task_refs: list[str],
    evidence_chain: Path | None,
    tags: list[str],
    note: str,
) -> int:
    records, exit_code = load_clean_context(root)
    if exit_code:
        return 1
    strictness = load_settings(root).get("allowed_freedom", "proof-only")
    if strictness == "proof-only" and is_mutating_action_kind(kind):
        print(f"record-action kind {kind!r} requires implementation-choice strictness")
        return 1
    if strictness == "evidence-authorized" and is_mutating_action_kind(kind):
        if safety_class == "unsafe":
            print("evidence-authorized cannot record unsafe mutating actions")
            return 1
        if not current_task_ref(root):
            print("evidence-authorized mutating actions require an active TASK-*")
            return 1
        if not evidence_chain:
            print("evidence-authorized mutating actions require --evidence-chain")
            return 1
        if cmd_validate_evidence_chain(root, evidence_chain) != 0:
            print("evidence-authorized mutating action blocked by invalid evidence chain")
            return 1

    timestamp = now_timestamp()
    payload = build_action_payload(
        record_id=next_record_id(records, "ACT-"),
        timestamp=timestamp,
        kind=kind,
        scope=scope,
        justified_by=justified_by,
        safety_class=safety_class,
        status=status,
        planned_at=planned_at,
        executed_at=executed_at,
        project_refs=project_refs_for_write(root, project_refs),
        task_refs=task_refs,
        tags=tags,
        note=note,
    )
    return persist_candidate(root, records, payload, "action")


def cmd_record_model(
    root: Path,
    knowledge_class: str,
    domain: str,
    scope: str,
    aspect: str,
    status: str,
    is_primary: bool,
    summary: str,
    claim_refs: list[str],
    open_question_refs: list[str],
    hypothesis_refs: list[str],
    related_model_refs: list[str],
    supersedes_refs: list[str],
    promoted_from_refs: list[str],
    project_refs: list[str],
    task_refs: list[str],
    note: str,
) -> int:
    records, exit_code = load_clean_context(root)
    if exit_code:
        return 1
    authority_errors = model_authority_errors(records, status, claim_refs, hypothesis_refs)
    if authority_errors:
        for message in authority_errors:
            print(message)
        return 1

    payload = build_model_payload(
        record_id=next_record_id(records, "MODEL-"),
        timestamp=now_timestamp(),
        knowledge_class=knowledge_class,
        domain=domain,
        scope=scope,
        aspect=aspect,
        status=status,
        is_primary=is_primary,
        summary=summary,
        claim_refs=claim_refs,
        open_question_refs=open_question_refs,
        hypothesis_refs=hypothesis_refs,
        related_model_refs=related_model_refs,
        supersedes_refs=supersedes_refs,
        promoted_from_refs=promoted_from_refs,
        project_refs=project_refs_for_write(root, project_refs),
        task_refs=task_refs,
        note=note,
    )
    return persist_candidate(root, records, payload, "model")


def model_authority_errors(
    records: dict[str, dict],
    status: str,
    claim_refs: list[str],
    hypothesis_refs: list[str],
) -> list[str]:
    if status not in MODEL_FLOW_AUTHORITY_STATUSES:
        return []
    errors = []
    fallback_refs = [ref for ref in claim_refs if ref in records and claim_is_fallback(records[ref])]
    if fallback_refs:
        errors.append("lifecycle fallback claim(s) cannot anchor active models: " + ", ".join(fallback_refs))
    non_authoritative = [
        ref
        for ref in claim_refs
        if ref in records and not claim_is_user_confirmed_theory(records, ref)
    ]
    if non_authoritative:
        errors.append(
            "active model must depend only on user-confirmed theory claim(s): "
            + ", ".join(non_authoritative)
        )
    if [ref for ref in hypothesis_refs if str(ref).strip()]:
        errors.append("active model cannot rely on tentative hypothesis_refs")
    return errors


def flow_authority_errors(
    records: dict[str, dict],
    status: str,
    preconditions: dict,
    oracle: dict,
    steps: list[dict],
) -> list[str]:
    if status not in MODEL_FLOW_AUTHORITY_STATUSES:
        return []
    errors = []
    for field_name, block in (("preconditions", preconditions), ("oracle", oracle)):
        for key in ("claim_refs", "success_claim_refs", "failure_claim_refs"):
            refs = block.get(key, [])
            if not isinstance(refs, list):
                continue
            non_authoritative = [
                ref
                for ref in refs
                if ref in records and not claim_is_user_confirmed_theory(records, ref)
            ]
            if non_authoritative:
                errors.append(
                    f"active flow {field_name} must depend only on user-confirmed theory claim(s): "
                    + ", ".join(sorted(set(non_authoritative)))
                )
        if [ref for ref in block.get("hypothesis_refs", []) if str(ref).strip()]:
            errors.append(f"active flow {field_name} cannot rely on tentative hypothesis_refs")
    for step in steps:
        non_authoritative = [
            ref
            for ref in step.get("claim_refs", [])
            if ref in records and not claim_is_user_confirmed_theory(records, ref)
        ]
        if non_authoritative:
            errors.append(
                "active flow step must depend only on user-confirmed theory claim(s): "
                + ", ".join(non_authoritative)
            )
    return errors


def cmd_record_flow(
    root: Path,
    knowledge_class: str,
    domain: str,
    scope: str,
    status: str,
    is_primary: bool,
    summary: str,
    model_refs: list[str],
    open_question_refs: list[str],
    precondition_claim_refs: list[str],
    precondition_hypothesis_refs: list[str],
    precondition_note: str | None,
    oracle_success_claim_refs: list[str],
    oracle_failure_claim_refs: list[str],
    oracle_hypothesis_refs: list[str],
    oracle_note: str | None,
    steps: list[dict],
    supersedes_refs: list[str],
    promoted_from_refs: list[str],
    project_refs: list[str],
    task_refs: list[str],
    note: str,
) -> int:
    records, exit_code = load_clean_context(root)
    if exit_code:
        return 1

    preconditions = build_flow_preconditions(
        precondition_claim_refs,
        precondition_hypothesis_refs,
        precondition_note,
    )
    oracle = build_flow_oracle(
        oracle_success_claim_refs,
        oracle_failure_claim_refs,
        oracle_hypothesis_refs,
        oracle_note,
    )
    authority_errors = flow_authority_errors(records, status, preconditions, oracle, steps)
    if authority_errors:
        for message in authority_errors:
            print(message)
        return 1

    payload = build_flow_payload(
        record_id=next_record_id(records, "FLOW-"),
        timestamp=now_timestamp(),
        knowledge_class=knowledge_class,
        domain=domain,
        scope=scope,
        status=status,
        is_primary=is_primary,
        summary=summary,
        model_refs=model_refs,
        open_question_refs=open_question_refs,
        preconditions=preconditions,
        oracle=oracle,
        steps=steps,
        supersedes_refs=supersedes_refs,
        promoted_from_refs=promoted_from_refs,
        project_refs=project_refs_for_write(root, project_refs),
        task_refs=task_refs,
        note=note,
    )
    return persist_candidate(root, records, payload, "flow")


def cmd_record_open_question(
    root: Path,
    domain: str,
    scope: str,
    aspect: str,
    status: str,
    question: str,
    related_claim_refs: list[str],
    related_model_refs: list[str],
    related_flow_refs: list[str],
    resolved_by_claim_refs: list[str],
    project_refs: list[str],
    task_refs: list[str],
    note: str,
) -> int:
    records, exit_code = load_clean_context(root)
    if exit_code:
        return 1

    payload = build_open_question_payload(
        record_id=next_record_id(records, "OPEN-"),
        timestamp=now_timestamp(),
        domain=domain,
        scope=scope,
        aspect=aspect,
        status=status,
        question=question,
        related_claim_refs=related_claim_refs,
        related_model_refs=related_model_refs,
        related_flow_refs=related_flow_refs,
        resolved_by_claim_refs=resolved_by_claim_refs,
        project_refs=project_refs_for_write(root, project_refs),
        task_refs=task_refs,
        note=note,
    )
    return persist_candidate(root, records, payload, "open_question")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Explicit TEP context commands.")
    parser.add_argument(
        "--context",
        default=None,
        help="Path to TEP context root. Defaults to TEP_CONTEXT_ROOT, ~/.tep_context, or legacy ./.codex_context.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    tep_help = subparsers.add_parser(
        "help",
        aliases=["tep-help"],
        help="Show compact human-facing TEP Runtime modes, commands, records, and workflows.",
    )
    tep_help.set_defaults(command="help")
    tep_help.add_argument("topic", nargs="?", default="modes", choices=["all", "modes", "commands", "records", "workflows"])

    subparsers.add_parser("review-context", help="Check structural and epistemic correctness.")
    subparsers.add_parser("reindex-context", help="Regenerate index and review artifacts.")
    type_graph = subparsers.add_parser(
        "type-graph",
        help="Show allowed TEP record chains and optional typing/scope pressure diagnostics.",
    )
    type_graph.add_argument("--check", action="store_true")
    type_graph.add_argument("--format", dest="output_format", choices=("text", "json"), default="text")
    brief_context = subparsers.add_parser(
        "brief-context",
        help="Print a task-oriented context brief for agent reasoning.",
    )
    brief_context.add_argument("--task", required=True)
    brief_context.add_argument("--limit", type=int, default=8)
    brief_context.add_argument("--detail", choices=("compact", "full"), default="compact")
    next_step = subparsers.add_parser(
        "next-step",
        help="Print the compact TEP action route for the agent's current intent.",
    )
    next_step.add_argument("--intent", choices=sorted(NEXT_STEP_INTENTS), default="auto")
    next_step.add_argument("--task", default="")
    next_step.add_argument("--detail", choices=("compact", "full"), default="compact")
    next_step.add_argument("--format", dest="output_format", choices=("text", "json"), default="text")
    lookup = subparsers.add_parser(
        "lookup",
        help="One front door for choosing fact, code, theory, research, or policy lookup routes.",
    )
    lookup.add_argument("--query", required=True)
    lookup.add_argument("--kind", choices=sorted(LOOKUP_KINDS), default="auto")
    lookup.add_argument("--reason", choices=sorted(LOOKUP_REASONS), required=True)
    lookup.add_argument("--root", type=Path, help="Repository root for code lookup routes. Defaults to cwd.")
    lookup.add_argument("--scope", choices=sorted(ATTENTION_SCOPES), default="current")
    lookup.add_argument("--mode", choices=sorted(ATTENTION_MODES), default="general")
    lookup.add_argument("--format", dest="output_format", choices=("text", "json"), default="text")
    search_records = subparsers.add_parser(
        "search-records",
        help="Search canonical records by keyword before expanding links.",
    )
    search_records.add_argument("--query", required=True)
    search_records.add_argument("--limit", type=int, default=12)
    search_records.add_argument("--type", dest="record_types", action="append", default=[])
    search_records.add_argument("--all-projects", action="store_true")
    search_records.add_argument("--include-task-local", action="store_true")
    search_records.add_argument("--include-fallback", action="store_true")
    search_records.add_argument("--include-archived", action="store_true")
    search_records.add_argument("--format", dest="output_format", choices=("text", "json"), default="text")
    claim_graph = subparsers.add_parser(
        "claim-graph",
        help="Search CLM-* records by keyword and return a compact linked graph.",
    )
    claim_graph.add_argument("--query", required=True)
    claim_graph.add_argument("--limit", type=int, default=8)
    claim_graph.add_argument("--depth", type=int, default=1)
    claim_graph.add_argument("--all-projects", action="store_true")
    claim_graph.add_argument("--include-task-local", action="store_true")
    claim_graph.add_argument("--include-fallback", action="store_true")
    claim_graph.add_argument("--include-archived", action="store_true")
    claim_graph.add_argument("--format", dest="output_format", choices=("text", "json"), default="text")
    record_detail = subparsers.add_parser(
        "record-detail",
        help="Show one canonical record with direct sources and links.",
    )
    record_detail.add_argument("--record", dest="record_ref", required=True)
    record_detail.add_argument("--format", dest="output_format", choices=("text", "json"), default="text")
    record_neighborhood = subparsers.add_parser(
        "record-neighborhood",
        help="Show one canonical record plus linked records by distance.",
    )
    record_neighborhood.add_argument("--record", dest="record_ref", required=True)
    record_neighborhood.add_argument("--depth", type=int, default=2)
    record_neighborhood.add_argument("--format", dest="output_format", choices=("text", "json"), default="text")
    guidelines_for = subparsers.add_parser(
        "guidelines-for",
        help="Select applicable active guidelines for a concrete task.",
    )
    guidelines_for.add_argument("--task", required=True)
    guidelines_for.add_argument("--domain", choices=sorted(GUIDELINE_DOMAINS))
    guidelines_for.add_argument("--limit", type=int, default=8)
    guidelines_for.add_argument("--all-projects", action="store_true")
    guidelines_for.add_argument("--include-task-local", action="store_true")
    guidelines_for.add_argument("--format", dest="output_format", choices=("text", "json"), default="text")
    cleanup_candidates = subparsers.add_parser(
        "cleanup-candidates",
        help="Report stale/noisy records that may be safe to resolve or archive later.",
    )
    cleanup_candidates.add_argument("--limit", type=int, default=20)
    cleanup_candidates.add_argument("--format", dest="output_format", choices=("text", "json"), default="text")
    cleanup_archives = subparsers.add_parser(
        "cleanup-archives",
        help="List cleanup archives or inspect one ARC-* archive manifest.",
    )
    cleanup_archives.add_argument("--archive", dest="archive_ref")
    cleanup_archives.add_argument("--limit", type=int, default=50)
    cleanup_archives.add_argument("--format", dest="output_format", choices=("text", "json"), default="text")
    cleanup_archive = subparsers.add_parser(
        "cleanup-archive",
        help="Plan or write cleanup archive contents without deleting records.",
    )
    cleanup_archive.add_argument("--dry-run", action="store_true")
    cleanup_archive.add_argument("--apply", action="store_true")
    cleanup_archive.add_argument("--limit", type=int, default=20)
    cleanup_archive.add_argument("--format", dest="output_format", choices=("text", "json"), default="text")
    cleanup_restore = subparsers.add_parser(
        "cleanup-restore",
        help="Plan or restore files from a cleanup archive without overwriting existing files.",
    )
    cleanup_restore.add_argument("--archive", dest="archive_ref", required=True)
    cleanup_restore.add_argument("--dry-run", action="store_true")
    cleanup_restore.add_argument("--apply", action="store_true")
    cleanup_restore.add_argument("--format", dest="output_format", choices=("text", "json"), default="text")
    topic_index = subparsers.add_parser(
        "topic-index",
        help="Build generated lexical topic navigation indexes over canonical records.",
    )
    topic_index_subparsers = topic_index.add_subparsers(dest="topic_index_command", required=True)
    topic_index_build = topic_index_subparsers.add_parser("build", help="Rebuild generated topic_index/*.json and reports.")
    topic_index_build.add_argument("--method", choices=("lexical",), default="lexical")
    topic_index_build.add_argument("--terms-per-record", type=int, default=8)
    topic_index_build.add_argument("--topic-limit", type=int, default=80)
    topic_index_build.add_argument("--candidate-limit", type=int, default=50)
    topic_search = subparsers.add_parser(
        "topic-search",
        help="Search generated topic index as a navigation prefilter. Not proof.",
    )
    topic_search.add_argument("--query", required=True)
    topic_search.add_argument("--limit", type=int, default=12)
    topic_search.add_argument("--type", dest="record_types", action="append", default=[])
    topic_search.add_argument("--format", dest="output_format", choices=("text", "json"), default="text")
    topic_info = subparsers.add_parser(
        "topic-info",
        help="Show generated topic terms and similar records for one record id.",
    )
    topic_info.add_argument("--record", dest="record_ref", required=True)
    topic_info.add_argument("--limit", type=int, default=8)
    topic_info.add_argument("--format", dest="output_format", choices=("text", "json"), default="text")
    topic_conflicts = subparsers.add_parser(
        "topic-conflict-candidates",
        help="Show lexical overlap candidates for contradiction review. Not proof.",
    )
    topic_conflicts.add_argument("--limit", type=int, default=20)
    topic_conflicts.add_argument("--format", dest="output_format", choices=("text", "json"), default="text")
    tap_record = subparsers.add_parser(
        "tap-record",
        help="Record a non-proof activity tap for attention-map scoring.",
    )
    tap_record.add_argument("--record", dest="record_ref", required=True)
    tap_record.add_argument("--kind", choices=sorted(TAP_KINDS), required=True)
    tap_record.add_argument("--intent", required=True)
    tap_record.add_argument("--note", default="")
    telemetry_report = subparsers.add_parser(
        "telemetry-report",
        help="Show read/navigation telemetry over MCP/CLI/hook lookup activity.",
    )
    telemetry_report.add_argument("--limit", type=int, default=10)
    telemetry_report.add_argument("--format", dest="output_format", choices=("text", "json"), default="text")
    attention_index = subparsers.add_parser(
        "attention-index",
        help="Build generated attention/curiosity indexes from topics, links, and taps.",
    )
    attention_index_subparsers = attention_index.add_subparsers(dest="attention_index_command", required=True)
    attention_index_build = attention_index_subparsers.add_parser("build", help="Rebuild generated attention_index/*.json and reports.")
    attention_index_build.add_argument("--probe-limit", type=int, default=20)
    attention_map = subparsers.add_parser(
        "attention-map",
        help="Show generated attention-map clusters and cold zones. Not proof.",
    )
    attention_map.add_argument("--limit", type=int, default=12)
    attention_map.add_argument("--format", dest="output_format", choices=("text", "json"), default="text")
    attention_map.add_argument("--scope", choices=sorted(ATTENTION_SCOPES), default="current")
    attention_map.add_argument("--mode", choices=sorted(ATTENTION_MODES), default="general")
    attention_diagram = subparsers.add_parser(
        "attention-diagram",
        help="Show generated Mermaid attention graph over clusters, records, bridges, and probes. Not proof.",
    )
    attention_diagram.add_argument("--limit", type=int, default=8)
    attention_diagram.add_argument("--format", dest="output_format", choices=("text", "json"), default="text")
    attention_diagram.add_argument("--scope", choices=sorted(ATTENTION_SCOPES), default="current")
    attention_diagram.add_argument("--mode", choices=sorted(ATTENTION_MODES), default="general")
    attention_diagram.add_argument("--detail", choices=("compact", "full"), default="compact")
    attention_diagram_compare = subparsers.add_parser(
        "attention-diagram-compare",
        help="Compare compact and full attention-diagram metrics. Not proof.",
    )
    attention_diagram_compare.add_argument("--limit", type=int, default=8)
    attention_diagram_compare.add_argument("--format", dest="output_format", choices=("text", "json"), default="text")
    attention_diagram_compare.add_argument("--scope", choices=sorted(ATTENTION_SCOPES), default="current")
    attention_diagram_compare.add_argument("--mode", choices=sorted(ATTENTION_MODES), default="general")
    curiosity_map = subparsers.add_parser(
        "curiosity-map",
        help="Show a generated visual-thinking curiosity map with heat, cold zones, bridges, and probes. Not proof.",
    )
    curiosity_map.add_argument("--volume", choices=sorted(CURIOSITY_MAP_VOLUMES), default="normal")
    curiosity_map.add_argument("--format", dest="output_format", choices=("text", "json"), default="text")
    curiosity_map.add_argument("--scope", choices=sorted(ATTENTION_SCOPES), default="current")
    curiosity_map.add_argument("--mode", choices=sorted(ATTENTION_MODES), default="general")
    curiosity_map.add_argument("--html", action="store_true", help="Write a standalone HTML visual map under <context>/views/curiosity/.")
    map_brief = subparsers.add_parser(
        "map-brief",
        help="Show a compact Map Graph projection with topology islands, bridge pressure, and probes. Not proof.",
    )
    map_brief.add_argument("--volume", choices=sorted(CURIOSITY_MAP_VOLUMES), default="compact")
    map_brief.add_argument("--limit", type=int, default=6)
    map_brief.add_argument("--format", dest="output_format", choices=("text", "json"), default="text")
    map_brief.add_argument("--scope", choices=sorted(ATTENTION_SCOPES), default="current")
    map_brief.add_argument("--mode", choices=sorted(ATTENTION_MODES), default="general")
    curiosity_probes = subparsers.add_parser(
        "curiosity-probes",
        help="Show generated bounded curiosity probes. Not proof.",
    )
    curiosity_probes.add_argument("--budget", type=int, default=8)
    curiosity_probes.add_argument("--format", dest="output_format", choices=("text", "json"), default="text")
    curiosity_probes.add_argument("--scope", choices=sorted(ATTENTION_SCOPES), default="current")
    curiosity_probes.add_argument("--mode", choices=sorted(ATTENTION_MODES), default="general")
    probe_inspect = subparsers.add_parser(
        "probe-inspect",
        help="Inspect one curiosity probe with canonical record details and link status. Not proof.",
    )
    probe_inspect.add_argument("--index", dest="probe_index", type=int, default=1)
    probe_inspect.add_argument("--format", dest="output_format", choices=("text", "json"), default="text")
    probe_inspect.add_argument("--scope", choices=sorted(ATTENTION_SCOPES), default="current")
    probe_inspect.add_argument("--mode", choices=sorted(ATTENTION_MODES), default="general")
    probe_chain_draft = subparsers.add_parser(
        "probe-chain-draft",
        help="Draft an evidence-chain skeleton from one curiosity probe. Draft is not proof.",
    )
    probe_chain_draft.add_argument("--index", dest="probe_index", type=int, default=1)
    probe_chain_draft.add_argument("--format", dest="output_format", choices=("text", "json"), default="text")
    probe_chain_draft.add_argument("--scope", choices=sorted(ATTENTION_SCOPES), default="current")
    probe_chain_draft.add_argument("--mode", choices=sorted(ATTENTION_MODES), default="general")
    probe_route = subparsers.add_parser(
        "probe-route",
        help="Generate an ordered inspection route for one curiosity probe. Route is not proof.",
    )
    probe_route.add_argument("--index", dest="probe_index", type=int, default=1)
    probe_route.add_argument("--format", dest="output_format", choices=("text", "json"), default="text")
    probe_route.add_argument("--scope", choices=sorted(ATTENTION_SCOPES), default="current")
    probe_route.add_argument("--mode", choices=sorted(ATTENTION_MODES), default="general")
    probe_pack = subparsers.add_parser(
        "probe-pack",
        help="Compactly bundle top curiosity probes with inspection summaries and chain drafts. Not proof.",
    )
    probe_pack.add_argument("--budget", type=int, default=3)
    probe_pack.add_argument("--format", dest="output_format", choices=("text", "json"), default="text")
    probe_pack.add_argument("--scope", choices=sorted(ATTENTION_SCOPES), default="current")
    probe_pack.add_argument("--mode", choices=sorted(ATTENTION_MODES), default="general")
    probe_pack.add_argument("--detail", choices=("compact", "full"), default="compact")
    probe_pack_compare = subparsers.add_parser(
        "probe-pack-compare",
        help="Compare compact and full probe-pack detail metrics. Not proof.",
    )
    probe_pack_compare.add_argument("--budget", type=int, default=3)
    probe_pack_compare.add_argument("--format", dest="output_format", choices=("text", "json"), default="text")
    probe_pack_compare.add_argument("--scope", choices=sorted(ATTENTION_SCOPES), default="current")
    probe_pack_compare.add_argument("--mode", choices=sorted(ATTENTION_MODES), default="general")
    logic_index = subparsers.add_parser(
        "logic-index",
        help="Build generated predicate logic indexes over CLM.logic blocks.",
    )
    logic_index_subparsers = logic_index.add_subparsers(dest="logic_index_command", required=True)
    logic_index_build = logic_index_subparsers.add_parser("build", help="Rebuild generated logic_index/*.json and reports.")
    logic_index_build.add_argument("--candidate-limit", type=int, default=50)
    logic_search = subparsers.add_parser(
        "logic-search",
        help="Search generated predicate atoms/rules. Not proof.",
    )
    logic_search.add_argument("--predicate")
    logic_search.add_argument("--symbol")
    logic_search.add_argument("--claim", dest="claim_ref")
    logic_search.add_argument("--limit", type=int, default=20)
    logic_search.add_argument("--format", dest="output_format", choices=("text", "json"), default="text")
    logic_graph = subparsers.add_parser(
        "logic-graph",
        help="Read generated logic vocabulary graph and pressure smells. Not proof.",
    )
    logic_graph.add_argument("--symbol")
    logic_graph.add_argument("--predicate")
    logic_graph.add_argument("--smells", action="store_true", dest="smells_only")
    logic_graph.add_argument("--limit", type=int, default=20)
    logic_graph.add_argument("--format", dest="output_format", choices=("text", "json"), default="text")
    logic_check = subparsers.add_parser(
        "logic-check",
        help="Read-only predicate consistency check over CLM.logic blocks.",
    )
    logic_check.add_argument("--limit", type=int, default=20)
    logic_check.add_argument("--format", dest="output_format", choices=("text", "json"), default="text")
    logic_check.add_argument("--solver", choices=("structural", "z3", "auto"))
    logic_check.add_argument("--closure", choices=("direct", "rules", "system"), default="direct")
    logic_conflicts = subparsers.add_parser(
        "logic-conflict-candidates",
        help="Show predicate-level conflict candidates. Not proof.",
    )
    logic_conflicts.add_argument("--limit", type=int, default=20)
    logic_conflicts.add_argument("--format", dest="output_format", choices=("text", "json"), default="text")
    init_code_index = subparsers.add_parser(
        "init-code-index",
        help="Initialize generated CIX-* code index entries from git-tracked files.",
    )
    init_code_index.add_argument("--root")
    init_code_index.add_argument("--include-untracked", action="store_true")
    init_code_index.add_argument("--max-files", type=int, default=1000)
    init_code_index.add_argument("--max-bytes-per-file", type=int, default=512 * 1024)
    init_code_index.add_argument("--backend-index", choices=("auto", "none", "project", "workspace", "both"), default="auto")
    index_code = subparsers.add_parser(
        "index-code",
        help="Index code files by include/exclude globs into CIX-* entries.",
    )
    index_code.add_argument("--root")
    index_code.add_argument("--include", dest="includes", action="append", default=[])
    index_code.add_argument("--exclude", dest="excludes", action="append", default=[])
    index_code.add_argument("--max-files", type=int, default=1000)
    index_code.add_argument("--max-bytes-per-file", type=int, default=512 * 1024)
    index_code.add_argument("--backend-index", choices=("auto", "none", "project", "workspace", "both"), default="auto")
    code_refresh = subparsers.add_parser(
        "code-refresh",
        help="Refresh existing CIX-* metadata for path globs and mark missing files.",
    )
    code_refresh.add_argument("--root")
    code_refresh.add_argument("--path", dest="paths", action="append", default=[])
    code_refresh.add_argument("--max-bytes-per-file", type=int, default=512 * 1024)
    code_refresh.add_argument("--backend-index", choices=("auto", "none", "project", "workspace", "both"), default="auto")
    code_info = subparsers.add_parser(
        "code-info",
        help="Show projected metadata for one CIX-* entry or path.",
    )
    code_info.add_argument("--root")
    code_info.add_argument("--entry", dest="entry_ref")
    code_info.add_argument("--path")
    code_info.add_argument("--fields")
    code_info.add_argument("--format", dest="output_format", choices=("text", "json"), default="text")
    code_search = subparsers.add_parser(
        "code-search",
        help="Search CIX-* entries with explicit filters and projection fields.",
    )
    code_search.add_argument("--root")
    code_search.add_argument("--query", help="Optional semantic code query proxied through the configured TEP code backend.")
    code_search.add_argument("--scope", choices=sorted(COCOINDEX_SCOPES), help="Backend index scope. Defaults to CocoIndex settings.")
    code_search.add_argument("--path", dest="path_patterns", action="append", default=[])
    code_search.add_argument("--language")
    code_search.add_argument("--code-kind")
    code_search.add_argument("--import", dest="imports", action="append", default=[])
    code_search.add_argument("--symbol", dest="symbols", action="append", default=[])
    code_search.add_argument("--feature", dest="features", action="append", default=[])
    code_search.add_argument("--ref", dest="refs", action="append", default=[])
    code_search.add_argument(
        "--link-candidate",
        dest="link_candidate_refs",
        action="append",
        default=[],
        help="Canonical record ref to include in backend-hit link suggestions without mutating records.",
    )
    code_search.add_argument("--annotation-kind", choices=sorted(CODE_INDEX_ANNOTATION_KINDS))
    code_search.add_argument("--annotation-category", dest="annotation_categories", action="append", default=[])
    code_search.add_argument("--annotation-status", choices=sorted(CODE_INDEX_ANNOTATION_STATUSES))
    code_search.add_argument("--include-stale-annotations", action="store_true")
    code_search.add_argument("--stale", choices=("true", "false"))
    code_search.add_argument("--include-missing", action="store_true")
    code_search.add_argument("--include-superseded", action="store_true")
    code_search.add_argument("--include-archived", action="store_true")
    code_search.add_argument("--fields")
    code_search.add_argument("--limit", type=int, default=20)
    code_search.add_argument("--format", dest="output_format", choices=("text", "json"), default="text")
    code_feedback = subparsers.add_parser(
        "code-feedback",
        help="Review or apply backend-hit feedback links through TEP CIX records.",
    )
    code_feedback.add_argument("--root")
    code_feedback.add_argument("--query", help="Semantic code query to review through the configured TEP code backend.")
    code_feedback.add_argument("--path", dest="path_patterns", action="append", default=[])
    code_feedback.add_argument("--language")
    code_feedback.add_argument(
        "--link-candidate",
        dest="link_candidate_refs",
        action="append",
        default=[],
        help="Canonical record ref to include in review suggestions or apply as a CIX link.",
    )
    code_feedback.add_argument("--entry", dest="entry_ref")
    code_feedback.add_argument("--target-path", dest="target_path", help="CIX target path to apply feedback when --entry is not used.")
    code_feedback.add_argument("--apply", action="store_true", help="Apply reviewed CIX links. Requires --entry/--target-path, --link-candidate, and --note.")
    code_feedback.add_argument("--note")
    code_feedback.add_argument("--limit", type=int, default=20)
    code_feedback.add_argument("--format", dest="output_format", choices=("text", "json"), default="text")
    code_smell_report = subparsers.add_parser(
        "code-smell-report",
        help="Read-only report of active CIX smell annotations.",
    )
    code_smell_report.add_argument("--root")
    code_smell_report.add_argument("--category", dest="categories", action="append", default=[])
    code_smell_report.add_argument("--severity", dest="severities", action="append", default=[])
    code_smell_report.add_argument("--include-stale", action="store_true")
    code_smell_report.add_argument("--limit", type=int, default=20)
    code_smell_report.add_argument("--format", dest="output_format", choices=("text", "json"), default="text")
    code_entry = subparsers.add_parser(
        "code-entry",
        help="Create manual CIX-* entries for directories, globs, symbols, or logical areas.",
    )
    code_entry_subparsers = code_entry.add_subparsers(dest="code_entry_command", required=True)
    code_entry_create = code_entry_subparsers.add_parser("create")
    code_entry_create.add_argument("--target-kind", required=True, choices=sorted(CODE_INDEX_TARGET_KINDS))
    code_entry_create.add_argument("--path")
    code_entry_create.add_argument("--name")
    code_entry_create.add_argument("--symbol-name")
    code_entry_create.add_argument("--summary", required=True)
    code_entry_create.add_argument("--feature", dest="manual_features", action="append", default=[])
    code_entry_create.add_argument("--note", required=True)
    code_entry_archive_unscoped = code_entry_subparsers.add_parser(
        "archive-unscoped",
        help="Archive legacy CIX entries without project_ref so they cannot leak across projects.",
    )
    code_entry_archive_unscoped.add_argument("--status", dest="statuses", action="append")
    code_entry_archive_unscoped.add_argument("--apply", action="store_true")
    code_entry_archive_unscoped.add_argument("--format", dest="output_format", choices=("text", "json"), default="text")
    code_entry_attach_unscoped = code_entry_subparsers.add_parser(
        "attach-unscoped",
        help="Attach legacy unscoped CIX entries to the project/workspace matching --root.",
    )
    code_entry_attach_unscoped.add_argument("--root", required=True)
    code_entry_attach_unscoped.add_argument("--status", dest="statuses", action="append")
    code_entry_attach_unscoped.add_argument("--apply", action="store_true")
    code_entry_attach_unscoped.add_argument("--format", dest="output_format", choices=("text", "json"), default="text")
    annotate_code = subparsers.add_parser(
        "annotate-code",
        help="Add a non-proof annotation to a CIX-* entry.",
    )
    annotate_code.add_argument("--entry", dest="entry_ref")
    annotate_code.add_argument("--path")
    annotate_code.add_argument("--kind", required=True, choices=sorted(CODE_INDEX_ANNOTATION_KINDS))
    annotate_code.add_argument("--note", required=True)
    annotate_code.add_argument("--confidence", default="moderate", choices=sorted(CONFIDENCE_LEVELS))
    annotate_code.add_argument("--supersedes", dest="supersedes", action="append", default=[])
    annotate_code.add_argument("--category", dest="categories", action="append", default=[])
    annotate_code.add_argument("--severity", choices=sorted(CODE_SMELL_SEVERITIES))
    annotate_code.add_argument("--suggestion", dest="suggestions", action="append", default=[])
    annotate_code.add_argument("--source", dest="source_refs", action="append", default=[])
    annotate_code.add_argument("--claim", dest="claim_refs", action="append", default=[])
    annotate_code.add_argument("--proposal", dest="proposal_refs", action="append", default=[])
    link_code = subparsers.add_parser(
        "link-code",
        help="Link a CIX-* entry to canonical records for navigation and impact only.",
    )
    link_code.add_argument("--entry", dest="entry_ref")
    link_code.add_argument("--path")
    link_code.add_argument("--guideline", dest="guideline_refs", action="append", default=[])
    link_code.add_argument("--claim", dest="claim_refs", action="append", default=[])
    link_code.add_argument("--model", dest="model_refs", action="append", default=[])
    link_code.add_argument("--flow", dest="flow_refs", action="append", default=[])
    link_code.add_argument("--source", dest="source_refs", action="append", default=[])
    link_code.add_argument("--plan", dest="plan_refs", action="append", default=[])
    link_code.add_argument("--debt", dest="debt_refs", action="append", default=[])
    link_code.add_argument("--open-question", dest="open_question_refs", action="append", default=[])
    link_code.add_argument("--working-context", dest="working_context_refs", action="append", default=[])
    link_code.add_argument("--note", required=True)
    assign_code_index = subparsers.add_parser(
        "assign-code-index",
        help="Attach CIX-* refs to allowed canonical records as navigation scope.",
    )
    assign_code_index.add_argument("--record", dest="record_ref", required=True)
    assign_code_index.add_argument("--entry", dest="entry_refs", action="append", required=True)
    assign_code_index.add_argument("--note")
    reasoning_case = subparsers.add_parser(
        "build-reasoning-case",
        help="Expand selected models/flows/claims into an auditable fact chain.",
    )
    reasoning_case.add_argument("--task", required=True)
    reasoning_case.add_argument("--claim", dest="claim_refs", action="append", default=[])
    reasoning_case.add_argument("--model", dest="model_refs", action="append", default=[])
    reasoning_case.add_argument("--flow", dest="flow_refs", action="append", default=[])
    reasoning_case.add_argument("--limit", type=int, default=12)
    validate_planning_chain = subparsers.add_parser(
        "validate-planning-chain",
        help="Deprecated alias for validate-evidence-chain.",
    )
    validate_planning_chain.add_argument("--file", dest="chain_file", required=True)
    validate_evidence_chain = subparsers.add_parser(
        "validate-evidence-chain",
        help="Validate an agent-supplied evidence chain with role/ref/quote nodes.",
    )
    validate_evidence_chain.add_argument("--file", dest="chain_file", required=True)
    validate_decision = subparsers.add_parser(
        "validate-decision",
        help="Validate whether an evidence chain is acceptable for a planning/permission/edit/model/flow/proposal/final decision.",
    )
    validate_decision.add_argument("--mode", required=True, choices=["planning", "permission", "edit", "model", "flow", "proposal", "final", "curiosity", "debugging"])
    validate_decision.add_argument("--chain", dest="chain_file", required=True)
    validate_decision.add_argument("--format", dest="output_format", choices=("text", "json"), default="text")
    validate_decision.add_argument("--kind", dest="action_kind")
    validate_decision.add_argument("--emit-permit", action="store_true")
    validate_decision.add_argument("--ttl-seconds", type=int, default=DEFAULT_CHAIN_PERMIT_TTL_SECONDS)
    augment_chain = subparsers.add_parser(
        "augment-chain",
        help="Read-only enrichment of an evidence chain with record metadata, quotes, sources, and validation.",
    )
    augment_chain.add_argument("--file", dest="chain_file", required=True)
    augment_chain.add_argument("--format", dest="output_format", choices=("text", "json"), default="text")
    subparsers.add_parser(
        "scan-conflicts",
        help="Scan comparable supported facts for structured contradictions.",
    )

    record_workspace = subparsers.add_parser(
        "record-workspace",
        help="Create a canonical WSP-* workspace boundary record.",
    )
    record_workspace.add_argument("--workspace-key", required=True)
    record_workspace.add_argument("--title", required=True)
    record_workspace.add_argument("--context-root")
    record_workspace.add_argument("--root-ref", dest="root_refs", action="append", default=[])
    record_workspace.add_argument("--project", dest="project_refs", action="append", default=[])
    record_workspace.add_argument("--status", default="active", choices=sorted(WORKSPACE_STATUSES))
    record_workspace.add_argument("--tag", dest="tags", action="append", default=[])
    record_workspace.add_argument("--note", required=True)

    show_workspace = subparsers.add_parser(
        "show-workspace",
        help="Show the current WSP-* boundary, or all workspaces with --all.",
    )
    show_workspace.add_argument("--all", action="store_true", dest="show_all")

    set_current_workspace = subparsers.add_parser(
        "set-current-workspace",
        help="Set or clear settings.current_workspace_ref.",
    )
    set_current_workspace.add_argument("--workspace", dest="workspace_ref")
    set_current_workspace.add_argument("--clear", action="store_true")

    workspace_admission = subparsers.add_parser(
        "workspace-admission",
        help="Check whether an external repo can be associated with the current workspace.",
    )
    workspace_admission_subparsers = workspace_admission.add_subparsers(dest="workspace_admission_command", required=True)
    workspace_admission_check = workspace_admission_subparsers.add_parser("check", help="Read-only workspace admission decision aid.")
    workspace_admission_check.add_argument("--repo", required=True)
    workspace_admission_check.add_argument("--format", dest="output_format", choices=("text", "json"), default="text")

    assign_workspace = subparsers.add_parser(
        "assign-workspace",
        help="Attach existing records to a WSP-* via workspace_refs.",
    )
    assign_workspace.add_argument("--workspace", dest="workspace_ref", required=True)
    assign_workspace.add_argument("--record", dest="record_refs", action="append", default=[])
    assign_workspace.add_argument("--records-file")
    assign_workspace.add_argument("--all-unassigned", action="store_true")
    assign_workspace.add_argument("--note")

    init_anchor = subparsers.add_parser(
        "init-anchor",
        help="Write a local .tep anchor for the current workdir. The anchor is not canonical memory.",
    )
    init_anchor.add_argument("--directory", help="Directory where .tep should be written. Defaults to cwd.")
    init_anchor.add_argument("--workspace", dest="workspace_ref", required=True)
    init_anchor.add_argument("--project", dest="project_ref")
    init_anchor.add_argument("--task", dest="task_ref")
    init_anchor.add_argument("--allowed-freedom", choices=sorted(ALLOWED_FREEDOM))
    init_anchor.add_argument("--hook-verbosity", choices=("quiet", "normal", "debug"))
    init_anchor.add_argument("--force", action="store_true")
    init_anchor.add_argument("--note", default="Local TEP anchor. Not canonical memory and not proof.")

    show_anchor = subparsers.add_parser(
        "show-anchor",
        help="Show the nearest local .tep anchor.",
    )
    show_anchor.add_argument("--start")

    validate_anchor = subparsers.add_parser(
        "validate-anchor",
        help="Validate the nearest local .tep anchor against the resolved context.",
    )
    validate_anchor.add_argument("--start")

    record_project = subparsers.add_parser(
        "record-project",
        help="Create a canonical PRJ-* project boundary record.",
    )
    record_project.add_argument("--project-key", required=True)
    record_project.add_argument("--title", required=True)
    record_project.add_argument("--root-ref", dest="root_refs", action="append", required=True)
    record_project.add_argument("--workspace", dest="workspace_refs", action="append", default=[])
    record_project.add_argument("--status", default="active", choices=sorted(PROJECT_STATUSES))
    record_project.add_argument("--related-project", dest="related_project_refs", action="append", default=[])
    record_project.add_argument("--tag", dest="tags", action="append", default=[])
    record_project.add_argument("--note", required=True)

    show_project = subparsers.add_parser(
        "show-project",
        help="Show the current PRJ-* boundary, or all projects with --all.",
    )
    show_project.add_argument("--all", action="store_true", dest="show_all")

    set_current_project = subparsers.add_parser(
        "set-current-project",
        help="Set or clear settings.current_project_ref.",
    )
    set_current_project.add_argument("--project", dest="project_ref")
    set_current_project.add_argument("--clear", action="store_true")

    assign_project = subparsers.add_parser(
        "assign-project",
        help="Attach an existing record to a PRJ-* via project_refs.",
    )
    assign_project.add_argument("--project", dest="project_ref", required=True)
    assign_project.add_argument("--record", dest="record_ref", required=True)
    assign_project.add_argument("--note")

    assign_task = subparsers.add_parser(
        "assign-task",
        help="Attach an existing record to a TASK-* via task_refs.",
    )
    assign_task.add_argument("--task", dest="task_ref", required=True)
    assign_task.add_argument("--record", dest="record_ref", required=True)
    assign_task.add_argument("--note")

    record_restriction = subparsers.add_parser(
        "record-restriction",
        help="Create a canonical RST-* restriction record.",
    )
    record_restriction.add_argument("--scope", required=True)
    record_restriction.add_argument("--title", required=True)
    record_restriction.add_argument("--applies-to", required=True, choices=sorted(RESTRICTION_APPLIES_TO))
    record_restriction.add_argument("--severity", default="hard", choices=sorted(RESTRICTION_SEVERITIES))
    record_restriction.add_argument("--rule", dest="rules", action="append", required=True)
    record_restriction.add_argument("--project", dest="project_refs", action="append", default=[])
    record_restriction.add_argument("--task", dest="task_refs", action="append", default=[])
    record_restriction.add_argument("--related-claim", dest="related_claim_refs", action="append", default=[])
    record_restriction.add_argument("--supersedes", dest="supersedes_refs", action="append", default=[])
    record_restriction.add_argument("--imposed-by", default="user")
    record_restriction.add_argument("--imposed-at")
    record_restriction.add_argument("--tag", dest="tags", action="append", default=[])
    record_restriction.add_argument("--note", required=True)

    show_restrictions = subparsers.add_parser(
        "show-restrictions",
        help="Show active restrictions for current project/task, or all with --all.",
    )
    show_restrictions.add_argument("--all", action="store_true", dest="show_all")

    record_guideline = subparsers.add_parser(
        "record-guideline",
        help="Create a GLD-* operational guideline record for code, tests, review, debugging, architecture, or agent behavior.",
    )
    record_guideline.add_argument("--scope", required=True)
    record_guideline.add_argument("--domain", required=True, choices=sorted(GUIDELINE_DOMAINS))
    record_guideline.add_argument("--applies-to", required=True, choices=sorted(GUIDELINE_APPLIES_TO))
    record_guideline.add_argument("--priority", required=True, choices=sorted(GUIDELINE_PRIORITIES))
    record_guideline.add_argument("--rule", required=True)
    record_guideline.add_argument("--source", dest="source_refs", action="append", required=True)
    record_guideline.add_argument("--project", dest="project_refs", action="append", default=[])
    record_guideline.add_argument("--task", dest="task_refs", action="append", default=[])
    record_guideline.add_argument("--related-claim", dest="related_claim_refs", action="append", default=[])
    record_guideline.add_argument("--conflict", dest="conflict_refs", action="append", default=[])
    record_guideline.add_argument("--supersedes", dest="supersedes_refs", action="append", default=[])
    record_guideline.add_argument("--example", dest="examples", action="append", default=[])
    record_guideline.add_argument("--rationale")
    record_guideline.add_argument("--tag", dest="tags", action="append", default=[])
    record_guideline.add_argument("--note", required=True)

    show_guidelines = subparsers.add_parser(
        "show-guidelines",
        help="Show active guidelines for current project/task, or all with --all.",
    )
    show_guidelines.add_argument("--all", action="store_true", dest="show_all")
    show_guidelines.add_argument("--domain", choices=sorted(GUIDELINE_DOMAINS))

    record_proposal = subparsers.add_parser(
        "record-proposal",
        help="Create a PRP-* constructive agent proposal with cited support and concrete options.",
    )
    record_proposal.add_argument("--scope", required=True)
    record_proposal.add_argument("--status", default="active", choices=sorted(PROPOSAL_STATUSES))
    record_proposal.add_argument("--subject", required=True)
    record_proposal.add_argument("--position", required=True)
    record_proposal.add_argument(
        "--proposal",
        dest="proposal_options",
        action="append",
        required=True,
        help="Option shaped as title|why[|tradeoff1;tradeoff2][|recommended]",
    )
    record_proposal.add_argument("--claim", dest="claim_refs", action="append", default=[])
    record_proposal.add_argument("--guideline", dest="guideline_refs", action="append", default=[])
    record_proposal.add_argument("--model", dest="model_refs", action="append", default=[])
    record_proposal.add_argument("--flow", dest="flow_refs", action="append", default=[])
    record_proposal.add_argument("--open-question", dest="open_question_refs", action="append", default=[])
    record_proposal.add_argument("--assumption", dest="assumptions", action="append", default=[])
    record_proposal.add_argument("--concern", dest="concerns", action="append", default=[])
    record_proposal.add_argument("--risk", dest="risks", action="append", default=[])
    record_proposal.add_argument("--stop-condition", dest="stop_conditions", action="append", default=[])
    record_proposal.add_argument("--confidence", default="moderate", choices=sorted(CONFIDENCE_LEVELS))
    record_proposal.add_argument("--created-by", default="agent")
    record_proposal.add_argument("--project", dest="project_refs", action="append", default=[])
    record_proposal.add_argument("--task", dest="task_refs", action="append", default=[])
    record_proposal.add_argument("--supersedes", dest="supersedes_refs", action="append", default=[])
    record_proposal.add_argument("--tag", dest="tags", action="append", default=[])
    record_proposal.add_argument("--note", required=True)

    configure_runtime = subparsers.add_parser(
        "configure-runtime",
        help="Show or update runtime verbosity, context budget, input capture, and analysis settings.",
    )
    configure_runtime.add_argument("--hook-verbosity", choices=["quiet", "normal", "debug"])
    configure_runtime.add_argument("--hook-run-capture", choices=["off", "mutating", "all"])
    configure_runtime.add_argument(
        "--backend-preset",
        choices=["minimal", "recommended"],
        help="Apply a named backend set: minimal disables optional backends; recommended enables Serena + CocoIndex.",
    )
    configure_runtime.add_argument(
        "--context-budget",
        dest="context_budget",
        action="append",
        default=[],
        help="Set context_budget key=value.",
    )
    configure_runtime.add_argument(
        "--analysis",
        dest="analysis_items",
        action="append",
        default=[],
        help="Set analysis section.key=value, e.g. logic_solver.backend=z3 or topic_prefilter.backend=nmf.",
    )
    configure_runtime.add_argument(
        "--backend",
        dest="backend_items",
        action="append",
        default=[],
        help="Set backend section.key=value, e.g. fact_validation.backend=rdf_shacl or derivation.datalog.enabled=true.",
    )
    configure_runtime.add_argument(
        "--input-capture",
        dest="input_capture_items",
        action="append",
        default=[],
        help="Set input_capture key=value, e.g. user_prompts=metadata-only or session_linking=false.",
    )
    configure_runtime.add_argument("--show", action="store_true")

    backend_status = subparsers.add_parser(
        "backend-status",
        help="Show optional backend availability. Backend output is not proof.",
    )
    backend_status.add_argument("--root", type=Path, help="Optional repository root for backend storage diagnostics.")
    backend_status.add_argument("--scope", choices=("project", "workspace"), help="Optional backend index scope override.")
    backend_status.add_argument("--format", dest="output_format", choices=("text", "json"), default="text")

    backend_check = subparsers.add_parser(
        "backend-check",
        help="Show one optional backend or backend group. Backend output is not proof.",
    )
    backend_check.add_argument("--backend", required=True)
    backend_check.add_argument("--root", type=Path, help="Optional repository root for backend storage diagnostics.")
    backend_check.add_argument("--scope", choices=("project", "workspace"), help="Optional backend index scope override.")
    backend_check.add_argument("--format", dest="output_format", choices=("text", "json"), default="text")

    validate_facts = subparsers.add_parser(
        "validate-facts",
        help="Run backend fact-validation candidates. Backend output is not proof.",
    )
    validate_facts.add_argument("--backend", default="rdf_shacl", choices=sorted(FACT_VALIDATION_BACKENDS))
    validate_facts.add_argument("--format", dest="output_format", choices=("text", "json"), default="text")

    export_rdf = subparsers.add_parser(
        "export-rdf",
        help="Export canonical records as an RDF projection. The export is not proof.",
    )
    export_rdf.add_argument("--format", dest="output_format", choices=("turtle", "jsonld"), default="turtle")
    export_rdf.add_argument("--output", type=Path)

    start_task = subparsers.add_parser(
        "start-task",
        help="Create a TASK-* record and set it as the current hydrated task focus.",
    )
    start_task.add_argument("--scope", required=True)
    start_task.add_argument("--title", required=True)
    start_task.add_argument("--type", dest="task_type", choices=sorted(TASK_TYPES), default="general")
    start_task.add_argument("--execution-mode", choices=sorted(TASK_EXECUTION_MODES), default="manual")
    start_task.add_argument("--autonomous", action="store_true", help="Shortcut for --execution-mode autonomous.")
    start_task.add_argument("--description")
    start_task.add_argument("--related-claim", dest="related_claim_refs", action="append", default=[])
    start_task.add_argument("--related-model", dest="related_model_refs", action="append", default=[])
    start_task.add_argument("--related-flow", dest="related_flow_refs", action="append", default=[])
    start_task.add_argument("--open-question", dest="open_question_refs", action="append", default=[])
    start_task.add_argument("--plan", dest="plan_refs", action="append", default=[])
    start_task.add_argument("--debt", dest="debt_refs", action="append", default=[])
    start_task.add_argument("--action", dest="action_refs", action="append", default=[])
    start_task.add_argument("--project", dest="project_refs", action="append", default=[])
    start_task.add_argument("--tag", dest="tags", action="append", default=[])
    start_task.add_argument("--note", required=True)

    show_task = subparsers.add_parser(
        "show-task",
        help="Show the current TASK-* focus, or all task records with --all.",
    )
    show_task.add_argument("--all", action="store_true", dest="show_all")

    validate_task_decomposition = subparsers.add_parser(
        "validate-task-decomposition",
        help="Check whether a TASK-* is atomic or decomposed enough for one-pass work.",
    )
    validate_task_decomposition.add_argument("--task", dest="task_ref", required=True)
    validate_task_decomposition.add_argument("--format", dest="output_format", choices=("text", "json"), default="text")

    confirm_atomic_task = subparsers.add_parser(
        "confirm-atomic-task",
        help="Mark an existing TASK-* as an executable one-pass leaf task.",
    )
    confirm_atomic_task.add_argument("--task", dest="task_ref", required=True)
    confirm_atomic_task.add_argument("--deliverable", required=True)
    confirm_atomic_task.add_argument("--done", dest="done_criteria", action="append", required=True)
    confirm_atomic_task.add_argument("--verify", dest="verification", action="append", default=[])
    confirm_atomic_task.add_argument("--boundary", dest="scope_boundary", required=True)
    confirm_atomic_task.add_argument("--blocker-policy", required=True)
    confirm_atomic_task.add_argument("--no-verification-needed")
    confirm_atomic_task.add_argument("--note")

    decompose_task = subparsers.add_parser(
        "decompose-task",
        help="Split a parent TASK-* into one-pass atomic child tasks.",
    )
    decompose_task.add_argument("--task", dest="task_ref", required=True)
    decompose_task.add_argument("--subtask", dest="subtask_specs", action="append", required=True)
    decompose_task.add_argument("--note")

    task_outcome_check = subparsers.add_parser(
        "task-outcome-check",
        help="Mechanically check whether a TASK-* can declare done, blocked, or user-question.",
    )
    task_outcome_check.add_argument("--task", dest="task_ref")
    task_outcome_check.add_argument("--outcome", required=True, choices=sorted(TASK_TERMINAL_OUTCOMES))
    task_outcome_check.add_argument("--format", dest="output_format", choices=("text", "json"), default="text")

    working_context = subparsers.add_parser(
        "working-context",
        help="Manage WCTX-* operational working contexts. Working contexts are not proof.",
    )
    working_context_subparsers = working_context.add_subparsers(dest="working_context_command", required=True)
    working_context_create = working_context_subparsers.add_parser("create", help="Create a WCTX-* working context.")
    working_context_create.add_argument("--scope", required=True)
    working_context_create.add_argument("--title", required=True)
    working_context_create.add_argument("--kind", dest="context_kind", choices=sorted(WORKING_CONTEXT_KINDS), default="general")
    working_context_create.add_argument("--pin", dest="pinned_refs", action="append", default=[])
    working_context_create.add_argument("--focus-path", dest="focus_paths", action="append", default=[])
    working_context_create.add_argument("--topic-term", dest="topic_terms", action="append", default=[])
    working_context_create.add_argument("--topic-seed", dest="topic_seed_refs", action="append", default=[])
    working_context_create.add_argument(
        "--assumption",
        dest="assumptions",
        action="append",
        default=[],
        help="Assumption shaped as text[|exploration-only|supported|deprecated][|ref1,ref2]",
    )
    working_context_create.add_argument("--concern", dest="concerns", action="append", default=[])
    working_context_create.add_argument("--project", dest="project_refs", action="append", default=[])
    working_context_create.add_argument("--task", dest="task_refs", action="append", default=[])
    working_context_create.add_argument("--tag", dest="tags", action="append", default=[])
    working_context_create.add_argument("--note", required=True)

    working_context_show = working_context_subparsers.add_parser("show", help="Show active WCTX-* records or one selected context.")
    working_context_show.add_argument("--context", dest="context_ref")
    working_context_show.add_argument("--all", action="store_true", dest="show_all")
    working_context_show.add_argument("--format", dest="output_format", choices=("text", "json"), default="text")

    working_context_drift = working_context_subparsers.add_parser(
        "check-drift",
        help="Check whether the current task text matches the active WCTX focus.",
    )
    working_context_drift.add_argument("--task", required=True, help="Current user task or planned task summary.")
    working_context_drift.add_argument("--format", dest="output_format", choices=("text", "json"), default="text")

    working_context_fork = working_context_subparsers.add_parser("fork", help="Copy-on-write fork of a WCTX-* record.")
    working_context_fork.add_argument("--context", dest="context_ref", required=True)
    working_context_fork.add_argument("--title")
    working_context_fork.add_argument("--kind", dest="context_kind", choices=sorted(WORKING_CONTEXT_KINDS))
    working_context_fork.add_argument("--add-pin", dest="add_pinned_refs", action="append", default=[])
    working_context_fork.add_argument("--remove-pin", dest="remove_pinned_refs", action="append", default=[])
    working_context_fork.add_argument("--add-focus-path", dest="add_focus_paths", action="append", default=[])
    working_context_fork.add_argument("--remove-focus-path", dest="remove_focus_paths", action="append", default=[])
    working_context_fork.add_argument("--add-topic-term", dest="add_topic_terms", action="append", default=[])
    working_context_fork.add_argument("--remove-topic-term", dest="remove_topic_terms", action="append", default=[])
    working_context_fork.add_argument("--add-topic-seed", dest="add_topic_seed_refs", action="append", default=[])
    working_context_fork.add_argument("--remove-topic-seed", dest="remove_topic_seed_refs", action="append", default=[])
    working_context_fork.add_argument("--add-assumption", dest="add_assumptions", action="append", default=[])
    working_context_fork.add_argument("--add-concern", dest="add_concerns", action="append", default=[])
    working_context_fork.add_argument("--project", dest="project_refs", action="append", default=[])
    working_context_fork.add_argument("--task", dest="task_refs", action="append", default=[])
    working_context_fork.add_argument("--tag", dest="tags", action="append", default=[])
    working_context_fork.add_argument("--note", required=True)

    working_context_close = working_context_subparsers.add_parser("close", help="Close or archive a WCTX-* record.")
    working_context_close.add_argument("--context", dest="context_ref", required=True)
    working_context_close.add_argument("--status", choices=("closed", "archived"), default="closed")
    working_context_close.add_argument("--note")

    complete_task = subparsers.add_parser(
        "complete-task",
        help="Mark the current or selected TASK-* as completed and clear current_task_ref.",
    )
    complete_task.add_argument("--task", dest="task_ref")
    complete_task.add_argument("--note")

    pause_task = subparsers.add_parser(
        "pause-task",
        help="Mark the current or selected TASK-* as paused and clear current_task_ref.",
    )
    pause_task.add_argument("--task", dest="task_ref")
    pause_task.add_argument("--note")

    resume_task = subparsers.add_parser(
        "resume-task",
        help="Resume a paused TASK-* and set it as current_task_ref.",
    )
    resume_task.add_argument("--task", dest="task_ref", required=True)
    resume_task.add_argument("--note")

    switch_task = subparsers.add_parser(
        "switch-task",
        help="Pause the current active task if needed and switch to another active/paused TASK-*.",
    )
    switch_task.add_argument("--task", dest="task_ref", required=True)
    switch_task.add_argument("--note")

    stop_task = subparsers.add_parser(
        "stop-task",
        help="Mark the current or selected TASK-* as stopped and clear current_task_ref.",
    )
    stop_task.add_argument("--task", dest="task_ref")
    stop_task.add_argument("--note")

    task_drift_check = subparsers.add_parser(
        "task-drift-check",
        help="Mechanically check whether an intended operation still aligns with current TASK-*.",
    )
    task_drift_check.add_argument("--intent", required=True)
    task_drift_check.add_argument("--task", dest="task_ref")
    task_drift_check.add_argument("--type", dest="task_type", choices=sorted(TASK_TYPES))

    review_precedents = subparsers.add_parser(
        "review-precedents",
        help="Review previous TASK-* records with the same task_type before repeating a work mode.",
    )
    review_precedents.add_argument("--task", dest="task_ref")
    review_precedents.add_argument("--task-type", choices=sorted(TASK_TYPES))
    review_precedents.add_argument("--query")
    review_precedents.add_argument("--limit", type=int, default=5)

    impact_graph = subparsers.add_parser(
        "impact-graph",
        help="Show direct and transitive dependencies of a claim across records and hypothesis usage.",
    )
    impact_graph.add_argument("--claim", dest="claim_ref", required=True)
    linked_records = subparsers.add_parser(
        "linked-records",
        help="Show incoming/outgoing linked records for any canonical record id.",
    )
    linked_records.add_argument("--record", dest="record_ref", required=True)
    linked_records.add_argument("--direction", choices=("incoming", "outgoing", "both"), default="both")
    linked_records.add_argument("--depth", type=int, default=1)
    linked_records.add_argument("--format", dest="output_format", choices=("text", "json"), default="text")
    promote_model = subparsers.add_parser(
        "promote-model-to-domain",
        help="Clone a stable investigation model into domain knowledge and supersede the source model.",
    )
    promote_model.add_argument("--model", dest="model_ref", required=True)
    promote_model.add_argument("--note")
    promote_flow = subparsers.add_parser(
        "promote-flow-to-domain",
        help="Clone a stable investigation flow into domain knowledge and supersede the source flow.",
    )
    promote_flow.add_argument("--flow", dest="flow_ref", required=True)
    promote_flow.add_argument("--note")
    mark_stale = subparsers.add_parser(
        "mark-stale-from-claim",
        help="Mark dependent models and flows stale from a weakened claim.",
    )
    mark_stale.add_argument("--claim", dest="claim_ref", required=True)
    mark_stale.add_argument("--note")
    rollback_report = subparsers.add_parser(
        "rollback-report",
        help="Show what would need review if a claim or hypothesis-stage claim is invalidated.",
    )
    rollback_report.add_argument("--claim", dest="claim_ref", required=True)

    strictness = subparsers.add_parser(
        "change-strictness",
        help="Change allowed_freedom strictness for the context.",
    )
    strictness.add_argument("value", choices=sorted(ALLOWED_FREEDOM))
    strictness.add_argument("--permission", dest="permission_ref")
    strictness.add_argument("--request", dest="request_ref")
    strictness.add_argument("--approval-source", dest="approval_source_ref")

    request_strictness = subparsers.add_parser(
        "request-strictness-change",
        help="Create a pending user approval request for escalating allowed_freedom.",
    )
    request_strictness.add_argument("value", choices=sorted(ALLOWED_FREEDOM))
    request_strictness.add_argument("--permission", dest="permission_ref")
    request_strictness.add_argument("--scope")
    request_strictness.add_argument("--reason", required=True)

    record_permission = subparsers.add_parser(
        "record-permission",
        help="Create a canonical permission record and refresh generated views.",
    )
    record_permission.add_argument("--scope", required=True)
    record_permission.add_argument("--applies-to", choices=sorted(PERMISSION_APPLIES_TO))
    record_permission.add_argument("--granted-by", default="user")
    record_permission.add_argument("--grant", dest="grants", action="append", required=True)
    record_permission.add_argument("--project", dest="project_refs", action="append", default=[])
    record_permission.add_argument("--task", dest="task_refs", action="append", default=[])
    record_permission.add_argument("--granted-at")
    record_permission.add_argument("--tag", dest="tags", action="append", default=[])
    record_permission.add_argument("--note", required=True)

    record_action = subparsers.add_parser(
        "record-action",
        help="Create a canonical action record and refresh generated views.",
    )
    record_action.add_argument("--kind", required=True)
    record_action.add_argument("--scope", required=True)
    record_action.add_argument("--justify", dest="justified_by", action="append", required=True)
    record_action.add_argument("--safety-class", required=True, choices=sorted(ACTION_SAFETY_CLASSES))
    record_action.add_argument("--status", default="planned", choices=sorted(ACTION_STATUSES))
    record_action.add_argument("--planned-at")
    record_action.add_argument("--executed-at")
    record_action.add_argument("--evidence-chain", type=Path)
    record_action.add_argument("--project", dest="project_refs", action="append", default=[])
    record_action.add_argument("--task", dest="task_refs", action="append", default=[])
    record_action.add_argument("--tag", dest="tags", action="append", default=[])
    record_action.add_argument("--note", required=True)

    record_input = subparsers.add_parser(
        "record-input",
        help="Create a canonical INP-* provenance record and refresh generated views.",
    )
    record_input.add_argument("--scope", required=True)
    record_input.add_argument("--input-kind", required=True, choices=sorted(INPUT_KINDS))
    record_input.add_argument("--origin-kind", required=True)
    record_input.add_argument("--origin-ref", required=True)
    record_input.add_argument("--text", default="")
    record_input.add_argument("--text-stdin", action="store_true")
    record_input.add_argument("--artifact-ref", dest="artifact_refs", action="append", default=[])
    record_input.add_argument("--session-ref")
    record_input.add_argument("--derived-record", dest="derived_record_refs", action="append", default=[])
    record_input.add_argument("--captured-at")
    record_input.add_argument("--project", dest="project_refs", action="append", default=[])
    record_input.add_argument("--task", dest="task_refs", action="append", default=[])
    record_input.add_argument("--tag", dest="tags", action="append", default=[])
    record_input.add_argument("--note", required=True)

    record_run = subparsers.add_parser(
        "record-run",
        help="Create a RUN-* record for a Bash/tool execution.",
    )
    record_run.add_argument("--scope", default="runtime.bash")
    record_run.add_argument("--command", dest="shell_command", required=True)
    record_run.add_argument("--cwd")
    record_run.add_argument("--exit-code", type=int)
    record_run.add_argument("--stdout-quote")
    record_run.add_argument("--stderr-quote")
    record_run.add_argument("--action-kind")
    record_run.add_argument("--artifact-ref", dest="artifact_refs", action="append", default=[])
    record_run.add_argument("--project", dest="project_refs", action="append", default=[])
    record_run.add_argument("--task", dest="task_refs", action="append", default=[])
    record_run.add_argument("--tag", dest="tags", action="append", default=[])
    record_run.add_argument("--note", default="")

    classify_input = subparsers.add_parser(
        "classify-input",
        help="Attach derived canonical records to an existing INP-* provenance record.",
    )
    classify_input.add_argument("--input", dest="input_ref", required=True)
    classify_input.add_argument("--derived-record", dest="derived_record_refs", action="append", default=[])
    classify_input.add_argument("--note")

    input_triage = subparsers.add_parser(
        "input-triage",
        help="Report or structurally link unclassified INP-* provenance records.",
    )
    input_triage_subparsers = input_triage.add_subparsers(dest="input_triage_command", required=True)
    input_triage_report = input_triage_subparsers.add_parser("report", help="Show unclassified INP-* records.")
    input_triage_report.add_argument("--task", dest="task_ref")
    input_triage_report.add_argument("--limit", type=int, default=50)
    input_triage_report.add_argument("--format", dest="output_format", choices=("text", "json"), default="text")
    input_triage_link = input_triage_subparsers.add_parser(
        "link-operational",
        help="Link operational INP-* prompts to a WCTX-* instead of promoting them to facts.",
    )
    input_triage_link.add_argument("--task", dest="task_ref", required=True)
    input_triage_link.add_argument("--input", dest="input_refs", action="append", default=[])
    input_triage_link.add_argument("--note")

    record_evidence = subparsers.add_parser(
        "record-evidence",
        help="Create a SRC-* and optional CLM-* from compact evidence inputs.",
    )
    record_evidence.add_argument("--scope", required=True)
    record_evidence.add_argument("--kind", required=True, choices=sorted(EVIDENCE_KIND_DEFAULTS))
    record_evidence.add_argument("--quote", default="")
    record_evidence.add_argument("--path", dest="path_value")
    record_evidence.add_argument("--line", type=int)
    record_evidence.add_argument("--end-line", type=int)
    record_evidence.add_argument("--command", dest="shell_command")
    record_evidence.add_argument("--cwd")
    record_evidence.add_argument("--exit-code", type=int)
    record_evidence.add_argument("--stdout-quote")
    record_evidence.add_argument("--stderr-quote")
    record_evidence.add_argument("--action-kind")
    record_evidence.add_argument("--input", dest="input_refs", action="append", default=[])
    record_evidence.add_argument("--artifact-ref", dest="artifact_refs", action="append", default=[])
    record_evidence.add_argument("--origin-ref")
    record_evidence.add_argument("--critique-status", choices=sorted(CRITIQUE_STATUSES), default="accepted")
    record_evidence.add_argument("--confidence", choices=sorted(CONFIDENCE_LEVELS))
    record_evidence.add_argument("--project", dest="project_refs", action="append", default=[])
    record_evidence.add_argument("--task", dest="task_refs", action="append", default=[])
    record_evidence.add_argument("--tag", dest="tags", action="append", default=[])
    record_evidence.add_argument("--red-flag", dest="red_flags", action="append", default=[])
    record_evidence.add_argument("--note", default="")
    record_evidence.add_argument("--claim", "--claim-statement", dest="claim_statement")
    record_evidence.add_argument("--claim-plane", choices=sorted(CLAIM_PLANES))
    record_evidence.add_argument("--claim-status", choices=sorted(CLAIM_STATUSES), default="supported")
    record_evidence.add_argument("--claim-kind", choices=sorted(CLAIM_KINDS))
    record_evidence.add_argument("--support", dest="support_refs", action="append", default=[])
    record_evidence.add_argument("--contradiction", dest="contradiction_refs", action="append", default=[])
    record_evidence.add_argument("--derived-from", dest="derived_from", action="append", default=[])
    record_evidence.add_argument("--recorded-at")

    record_support = subparsers.add_parser(
        "record-support",
        help="Graph-v2 front door: agent gives a thought plus support; API creates FILE/RUN/SRC/CLM links.",
    )
    record_support.add_argument("--scope", required=True)
    record_support.add_argument("--kind", required=True, choices=sorted(EVIDENCE_KIND_DEFAULTS))
    record_support.add_argument("--thought", required=True)
    record_support.add_argument("--quote", default="")
    record_support.add_argument("--path", dest="path_value")
    record_support.add_argument("--line", type=int)
    record_support.add_argument("--end-line", type=int)
    record_support.add_argument("--command", dest="shell_command")
    record_support.add_argument("--cwd")
    record_support.add_argument("--exit-code", type=int)
    record_support.add_argument("--stdout-quote")
    record_support.add_argument("--stderr-quote")
    record_support.add_argument("--action-kind")
    record_support.add_argument("--input", dest="input_refs", action="append", default=[])
    record_support.add_argument("--artifact-ref", dest="artifact_refs", action="append", default=[])
    record_support.add_argument("--project", dest="project_refs", action="append", default=[])
    record_support.add_argument("--task", dest="task_refs", action="append", default=[])
    record_support.add_argument("--tag", dest="tags", action="append", default=[])
    record_support.add_argument("--note", default="")
    record_support.add_argument("--claim-plane", choices=sorted(CLAIM_PLANES))
    record_support.add_argument("--claim-status", choices=sorted(CLAIM_STATUSES), default="supported")
    record_support.add_argument("--claim-kind", choices=sorted(CLAIM_KINDS), default="factual")

    record_source = subparsers.add_parser(
        "record-source",
        help="Create a canonical source record and refresh generated views.",
    )
    record_source.add_argument("--scope", required=True)
    record_source.add_argument("--source-kind", required=True, choices=sorted(SOURCE_KINDS))
    record_source.add_argument("--critique-status", required=True, choices=sorted(CRITIQUE_STATUSES))
    record_source.add_argument("--origin-kind", required=True)
    record_source.add_argument("--origin-ref", required=True)
    record_source.add_argument("--quote", default="")
    record_source.add_argument("--artifact-ref", dest="artifact_refs", action="append", default=[])
    record_source.add_argument("--confidence", choices=sorted(CONFIDENCE_LEVELS))
    record_source.add_argument("--independence-group")
    record_source.add_argument("--captured-at")
    record_source.add_argument("--project", dest="project_refs", action="append", default=[])
    record_source.add_argument("--task", dest="task_refs", action="append", default=[])
    record_source.add_argument("--tag", dest="tags", action="append", default=[])
    record_source.add_argument("--red-flag", dest="red_flags", action="append", default=[])
    record_source.add_argument("--note", required=True)

    record_claim = subparsers.add_parser(
        "record-claim",
        help="Create a canonical claim record and refresh generated views.",
    )
    record_claim.add_argument("--scope", required=True)
    record_claim.add_argument("--plane", required=True, choices=sorted(CLAIM_PLANES))
    record_claim.add_argument("--status", default="tentative", choices=sorted(CLAIM_STATUSES))
    record_claim.add_argument("--statement", required=True)
    record_claim.add_argument("--source", dest="source_refs", action="append", required=True)
    record_claim.add_argument("--support", dest="support_refs", action="append", default=[])
    record_claim.add_argument("--contradiction", dest="contradiction_refs", action="append", default=[])
    record_claim.add_argument("--derived-from", dest="derived_from", action="append", default=[])
    record_claim.add_argument("--claim-kind", choices=sorted(CLAIM_KINDS))
    record_claim.add_argument("--confidence", choices=sorted(CONFIDENCE_LEVELS))
    record_claim.add_argument("--comparison-key")
    record_claim.add_argument("--comparison-subject")
    record_claim.add_argument("--comparison-aspect")
    record_claim.add_argument("--comparison-comparator", choices=sorted(CLAIM_COMPARATORS))
    record_claim.add_argument("--comparison-value")
    record_claim.add_argument("--comparison-polarity", choices=sorted(CLAIM_POLARITIES))
    record_claim.add_argument("--comparison-context-scope")
    record_claim.add_argument(
        "--logic-json",
        help="Inline JSON object or @path with logic.symbols/atoms/rules to attach to this CLM-*.",
    )
    record_claim.add_argument(
        "--logic-symbol",
        dest="logic_symbols",
        action="append",
        default=[],
        help="Typed symbol shaped as symbol|kind[|note], e.g. person:alice|entity.",
    )
    record_claim.add_argument(
        "--logic-atom",
        dest="logic_atoms",
        action="append",
        default=[],
        help="Atom shaped as Predicate|arg1,arg2[|polarity][|value=...][|context=k=v;...][|functional].",
    )
    record_claim.add_argument(
        "--logic-rule",
        dest="logic_rules",
        action="append",
        default=[],
        help="Horn-style rule shaped as name|Body(?x)&Other(?x,?y)->Head(?x,?y).",
    )
    record_claim.add_argument("--recorded-at")
    record_claim.add_argument("--project", dest="project_refs", action="append", default=[])
    record_claim.add_argument("--task", dest="task_refs", action="append", default=[])
    record_claim.add_argument("--tag", dest="tags", action="append", default=[])
    record_claim.add_argument("--red-flag", dest="red_flags", action="append", default=[])
    record_claim.add_argument("--note", required=True)

    record_link = subparsers.add_parser(
        "record-link",
        help="Create an append-only source-backed claim linking two claim records or one curiosity probe pair.",
    )
    record_link.add_argument("--scope", required=True)
    record_link.add_argument("--left", dest="left_ref")
    record_link.add_argument("--right", dest="right_ref")
    record_link.add_argument("--probe-index", type=int)
    record_link.add_argument("--probe-scope", choices=sorted(ATTENTION_SCOPES), default="current")
    record_link.add_argument("--mode", choices=sorted(ATTENTION_MODES), default="general")
    record_link.add_argument("--relation", choices=sorted(RECORD_LINK_RELATIONS), default="related")
    record_link.add_argument("--quote", required=True, help="Short quote or observation that supports recording this reviewed link.")
    record_link.add_argument("--confidence", choices=sorted(CONFIDENCE_LEVELS))
    record_link.add_argument("--project", dest="project_refs", action="append", default=[])
    record_link.add_argument("--task", dest="task_refs", action="append", default=[])
    record_link.add_argument("--tag", dest="tags", action="append", default=[])
    record_link.add_argument("--note", required=True)

    show_claim_lifecycle = subparsers.add_parser(
        "show-claim-lifecycle",
        help="Show retrieval lifecycle metadata for a CLM-* record.",
    )
    show_claim_lifecycle.add_argument("--claim", dest="claim_ref", required=True)

    resolve_claim = subparsers.add_parser(
        "resolve-claim",
        help="Mark a true-but-no-longer-current CLM-* as fallback-only historical context.",
    )
    resolve_claim.add_argument("--claim", dest="claim_ref", required=True)
    resolve_claim.add_argument("--resolved-by-claim", dest="resolved_by_claim_refs", action="append", default=[])
    resolve_claim.add_argument("--resolved-by-action", dest="resolved_by_action_refs", action="append", default=[])
    resolve_claim.add_argument("--reactivate-when", dest="reactivation_conditions", action="append", default=[])
    resolve_claim.add_argument("--note", required=True)

    archive_claim = subparsers.add_parser(
        "archive-claim",
        help="Move a CLM-* out of default retrieval; it remains available by explicit ref/audit.",
    )
    archive_claim.add_argument("--claim", dest="claim_ref", required=True)
    archive_claim.add_argument("--note", required=True)

    restore_claim = subparsers.add_parser(
        "restore-claim",
        help="Return a fallback/archived CLM-* to normal active retrieval.",
    )
    restore_claim.add_argument("--claim", dest="claim_ref", required=True)
    restore_claim.add_argument("--note", required=True)

    record_plan = subparsers.add_parser(
        "record-plan",
        help="Create a canonical plan record and refresh generated views.",
    )
    record_plan.add_argument("--scope", required=True)
    record_plan.add_argument("--title", required=True)
    record_plan.add_argument("--priority", required=True, choices=sorted(PRIORITY_LEVELS))
    record_plan.add_argument("--status", default="proposed", choices=sorted(PLAN_STATUSES))
    record_plan.add_argument("--justify", dest="justified_by", action="append", required=True)
    record_plan.add_argument("--step", dest="steps", action="append", required=True)
    record_plan.add_argument("--success", dest="success_criteria", action="append", required=True)
    record_plan.add_argument("--blocked-by", dest="blocked_by", action="append", default=[])
    record_plan.add_argument("--project", dest="project_refs", action="append", default=[])
    record_plan.add_argument("--task", dest="task_refs", action="append", default=[])
    record_plan.add_argument("--tag", dest="tags", action="append", default=[])
    record_plan.add_argument("--note", required=True)

    validate_plan_decomposition = subparsers.add_parser(
        "validate-plan-decomposition",
        help="Check whether a PLN-* is atomic or decomposed enough to execute.",
    )
    validate_plan_decomposition.add_argument("--plan", dest="plan_ref", required=True)
    validate_plan_decomposition.add_argument("--format", dest="output_format", choices=("text", "json"), default="text")

    confirm_atomic_plan = subparsers.add_parser(
        "confirm-atomic-plan",
        help="Mark an existing PLN-* as an executable one-pass plan.",
    )
    confirm_atomic_plan.add_argument("--plan", dest="plan_ref", required=True)
    confirm_atomic_plan.add_argument("--task", dest="task_ref")
    confirm_atomic_plan.add_argument("--note")

    decompose_plan = subparsers.add_parser(
        "decompose-plan",
        help="Split a parent PLN-* into one-pass atomic child plans.",
    )
    decompose_plan.add_argument("--plan", dest="plan_ref", required=True)
    decompose_plan.add_argument("--subplan", dest="subplan_specs", action="append", required=True)
    decompose_plan.add_argument("--note")

    record_debt = subparsers.add_parser(
        "record-debt",
        help="Create a canonical debt record and refresh generated views.",
    )
    record_debt.add_argument("--scope", required=True)
    record_debt.add_argument("--title", required=True)
    record_debt.add_argument("--priority", required=True, choices=sorted(PRIORITY_LEVELS))
    record_debt.add_argument("--status", default="open", choices=sorted(DEBT_STATUSES))
    record_debt.add_argument("--evidence", dest="evidence_refs", action="append", required=True)
    record_debt.add_argument("--plan-ref", dest="plan_refs", action="append", default=[])
    record_debt.add_argument("--project", dest="project_refs", action="append", default=[])
    record_debt.add_argument("--task", dest="task_refs", action="append", default=[])
    record_debt.add_argument("--tag", dest="tags", action="append", default=[])
    record_debt.add_argument("--note", required=True)

    record_feedback = subparsers.add_parser(
        "record-feedback",
        help="Create an agent feedback source plus an open DEBT-* item for TEP/plugin problems.",
    )
    record_feedback.add_argument("--scope", required=True)
    record_feedback.add_argument("--kind", required=True, choices=sorted(FEEDBACK_KINDS))
    record_feedback.add_argument("--severity", default="medium", choices=sorted(FEEDBACK_SEVERITY_TO_PRIORITY))
    record_feedback.add_argument("--surface", required=True, choices=sorted(FEEDBACK_SURFACES))
    record_feedback.add_argument("--title", required=True)
    record_feedback.add_argument("--actual", required=True)
    record_feedback.add_argument("--expected")
    record_feedback.add_argument("--repro", dest="repro_steps", action="append", default=[])
    record_feedback.add_argument("--suggestion", dest="suggestions", action="append", default=[])
    record_feedback.add_argument("--evidence", dest="evidence_refs", action="append", default=[])
    record_feedback.add_argument("--project", dest="project_refs", action="append", default=[])
    record_feedback.add_argument("--task", dest="task_refs", action="append", default=[])
    record_feedback.add_argument("--tag", dest="tags", action="append", default=[])
    record_feedback.add_argument("--note", default="")
    record_feedback.add_argument("--origin-ref", default="agent feedback")
    record_feedback.add_argument("--created-by", default="agent")

    record_model = subparsers.add_parser(
        "record-model",
        help="Create a canonical model record and refresh generated views.",
    )
    record_model.add_argument("--knowledge-class", required=True, choices=sorted(MODEL_KNOWLEDGE_CLASSES))
    record_model.add_argument("--domain", required=True)
    record_model.add_argument("--scope", required=True)
    record_model.add_argument("--aspect", required=True)
    record_model.add_argument("--status", default="draft", choices=sorted(MODEL_STATUSES))
    record_model.add_argument("--primary", action="store_true")
    record_model.add_argument("--summary", required=True)
    record_model.add_argument("--claim", dest="claim_refs", action="append", required=True)
    record_model.add_argument("--open-question", dest="open_question_refs", action="append", default=[])
    record_model.add_argument("--hypothesis", dest="hypothesis_refs", action="append", default=[])
    record_model.add_argument("--related-model", dest="related_model_refs", action="append", default=[])
    record_model.add_argument("--supersedes", dest="supersedes_refs", action="append", default=[])
    record_model.add_argument("--promoted-from", dest="promoted_from_refs", action="append", default=[])
    record_model.add_argument("--project", dest="project_refs", action="append", default=[])
    record_model.add_argument("--task", dest="task_refs", action="append", default=[])
    record_model.add_argument("--note", required=True)

    record_flow = subparsers.add_parser(
        "record-flow",
        help="Create a canonical flow record and refresh generated views.",
    )
    record_flow.add_argument("--knowledge-class", required=True, choices=sorted(MODEL_KNOWLEDGE_CLASSES))
    record_flow.add_argument("--domain", required=True)
    record_flow.add_argument("--scope", required=True)
    record_flow.add_argument("--status", default="draft", choices=sorted(MODEL_STATUSES))
    record_flow.add_argument("--primary", action="store_true")
    record_flow.add_argument("--summary", required=True)
    record_flow.add_argument("--model", dest="model_refs", action="append", required=True)
    record_flow.add_argument("--open-question", dest="open_question_refs", action="append", default=[])
    record_flow.add_argument("--precondition-claim", dest="precondition_claim_refs", action="append", default=[])
    record_flow.add_argument("--precondition-hypothesis", dest="precondition_hypothesis_refs", action="append", default=[])
    record_flow.add_argument("--precondition-note")
    record_flow.add_argument("--oracle-success", dest="oracle_success_claim_refs", action="append", default=[])
    record_flow.add_argument("--oracle-failure", dest="oracle_failure_claim_refs", action="append", default=[])
    record_flow.add_argument("--oracle-hypothesis", dest="oracle_hypothesis_refs", action="append", default=[])
    record_flow.add_argument("--oracle-note")
    record_flow.add_argument("--step-id", dest="step_ids", action="append", default=[])
    record_flow.add_argument("--step-label", dest="step_labels", action="append", default=[])
    record_flow.add_argument("--step-status", dest="step_statuses", action="append", default=[])
    record_flow.add_argument("--step-claims", dest="step_claim_refs", action="append", default=[])
    record_flow.add_argument("--step-next", dest="step_next_steps", action="append", default=[])
    record_flow.add_argument("--step-open-questions", dest="step_open_question_refs", action="append", default=[])
    record_flow.add_argument("--step-accepted-deviation-refs", dest="step_accepted_deviation_refs", action="append", default=[])
    record_flow.add_argument("--supersedes", dest="supersedes_refs", action="append", default=[])
    record_flow.add_argument("--promoted-from", dest="promoted_from_refs", action="append", default=[])
    record_flow.add_argument("--project", dest="project_refs", action="append", default=[])
    record_flow.add_argument("--task", dest="task_refs", action="append", default=[])
    record_flow.add_argument("--note", required=True)

    record_open_question = subparsers.add_parser(
        "record-open-question",
        help="Create a canonical open-question record and refresh generated views.",
    )
    record_open_question.add_argument("--domain", required=True)
    record_open_question.add_argument("--scope", required=True)
    record_open_question.add_argument("--aspect", required=True)
    record_open_question.add_argument("--status", default="open", choices=sorted(OPEN_QUESTION_STATUSES))
    record_open_question.add_argument("--question", required=True)
    record_open_question.add_argument("--related-claim", dest="related_claim_refs", action="append", default=[])
    record_open_question.add_argument("--related-model", dest="related_model_refs", action="append", default=[])
    record_open_question.add_argument("--related-flow", dest="related_flow_refs", action="append", default=[])
    record_open_question.add_argument("--resolved-by-claim", dest="resolved_by_claim_refs", action="append", default=[])
    record_open_question.add_argument("--project", dest="project_refs", action="append", default=[])
    record_open_question.add_argument("--task", dest="task_refs", action="append", default=[])
    record_open_question.add_argument("--note", required=True)

    record_artifact = subparsers.add_parser(
        "record-artifact",
        help="Copy a payload file into the canonical artifacts store.",
    )
    record_artifact.add_argument("--path", required=True)

    hypothesis = subparsers.add_parser(
        "hypothesis",
        help="Manage the active hypothesis index built over tentative claims.",
    )
    hypothesis_subparsers = hypothesis.add_subparsers(dest="hypothesis_command", required=True)

    hypothesis_add = hypothesis_subparsers.add_parser("add", help="Add an active hypothesis index entry.")
    hypothesis_add.add_argument("--claim", dest="claim_ref", required=True)
    hypothesis_add.add_argument("--domain")
    hypothesis_add.add_argument("--scope")
    hypothesis_add.add_argument("--model", dest="model_refs", action="append", default=[])
    hypothesis_add.add_argument("--flow", dest="flow_refs", action="append", default=[])
    hypothesis_add.add_argument("--action", dest="action_refs", action="append", default=[])
    hypothesis_add.add_argument("--plan", dest="plan_refs", action="append", default=[])
    hypothesis_add.add_argument("--rollback-ref", dest="rollback_refs", action="append", default=[])
    hypothesis_add.add_argument("--mode", choices=["durable", "exploration"], default="durable")
    hypothesis_add.add_argument("--based-on-hypothesis", dest="based_on_hypotheses", action="append", default=[])
    hypothesis_add.add_argument("--note", required=True)

    hypothesis_list = hypothesis_subparsers.add_parser("list", help="List hypothesis index entries.")
    hypothesis_list.add_argument("--status", choices=["active", "confirmed", "falsified", "abandoned"])

    hypothesis_close = hypothesis_subparsers.add_parser("close", help="Close an active hypothesis entry.")
    hypothesis_close.add_argument("--claim", dest="claim_ref", required=True)
    hypothesis_close.add_argument("--status", required=True, choices=["confirmed", "falsified", "abandoned"])
    hypothesis_close.add_argument("--note")

    hypothesis_reopen = hypothesis_subparsers.add_parser("reopen", help="Reopen a closed hypothesis entry.")
    hypothesis_reopen.add_argument("--claim", dest="claim_ref", required=True)
    hypothesis_reopen.add_argument("--note")

    hypothesis_remove = hypothesis_subparsers.add_parser("remove", help="Remove a hypothesis index entry entirely.")
    hypothesis_remove.add_argument("--claim", dest="claim_ref", required=True)

    hypothesis_sync = hypothesis_subparsers.add_parser(
        "sync",
        help="Remove index entries that no longer match tentative claims.",
    )
    hypothesis_sync.add_argument(
        "--drop-closed",
        action="store_true",
        help="Also drop confirmed/falsified/abandoned entries instead of only stale mismatches.",
    )

    return parser.parse_args()


def dispatch(args: argparse.Namespace, root: Path) -> None:
    if args.command == "help":
        raise SystemExit(cmd_help(args.topic))
    if args.command == "review-context":
        raise SystemExit(cmd_review_context(root))
    if args.command == "reindex-context":
        raise SystemExit(cmd_reindex_context(root))
    if args.command == "type-graph":
        raise SystemExit(cmd_type_graph(root, check=args.check, output_format=args.output_format))
    if args.command == "brief-context":
        raise SystemExit(cmd_brief_context(root, task=args.task, limit=args.limit, detail=args.detail))
    if args.command == "next-step":
        raise SystemExit(
            cmd_next_step(root, intent=args.intent, task=args.task, detail=args.detail, output_format=args.output_format)
        )
    if args.command == "lookup":
        raise SystemExit(
            cmd_lookup(
                root,
                query=args.query,
                kind=args.kind,
                root_path=args.root,
                scope=args.scope,
                mode=args.mode,
                reason=args.reason,
                output_format=args.output_format,
            )
        )
    if args.command == "search-records":
        raise SystemExit(
            cmd_search_records(
                root,
                query=args.query,
                limit=args.limit,
                record_types=args.record_types,
                all_projects=args.all_projects,
                include_task_local=args.include_task_local,
                include_fallback=args.include_fallback,
                include_archived=args.include_archived,
                output_format=args.output_format,
            )
        )
    if args.command == "claim-graph":
        raise SystemExit(
            cmd_claim_graph(
                root,
                query=args.query,
                limit=args.limit,
                depth=args.depth,
                all_projects=args.all_projects,
                include_task_local=args.include_task_local,
                include_fallback=args.include_fallback,
                include_archived=args.include_archived,
                output_format=args.output_format,
            )
        )
    if args.command == "record-detail":
        raise SystemExit(cmd_record_detail(root, record_ref=args.record_ref, output_format=args.output_format))
    if args.command == "record-neighborhood":
        raise SystemExit(
            cmd_record_neighborhood(
                root,
                record_ref=args.record_ref,
                depth=args.depth,
                output_format=args.output_format,
            )
        )
    if args.command == "guidelines-for":
        raise SystemExit(
            cmd_guidelines_for(
                root,
                task=args.task,
                domain=args.domain,
                limit=args.limit,
                all_projects=args.all_projects,
                include_task_local=args.include_task_local,
                output_format=args.output_format,
            )
        )
    if args.command == "cleanup-candidates":
        raise SystemExit(cmd_cleanup_candidates(root, limit=args.limit, output_format=args.output_format))
    if args.command == "cleanup-archives":
        raise SystemExit(
            cmd_cleanup_archives(
                root,
                archive_ref=args.archive_ref,
                limit=args.limit,
                output_format=args.output_format,
            )
        )
    if args.command == "cleanup-archive":
        raise SystemExit(
            cmd_cleanup_archive(
                root,
                dry_run=args.dry_run,
                apply=args.apply,
                limit=args.limit,
                output_format=args.output_format,
            )
        )
    if args.command == "cleanup-restore":
        raise SystemExit(
            cmd_cleanup_restore(
                root,
                archive_ref=args.archive_ref,
                dry_run=args.dry_run,
                apply=args.apply,
                output_format=args.output_format,
            )
        )
    if args.command == "topic-index":
        if args.topic_index_command == "build":
            raise SystemExit(
                cmd_topic_index_build(
                    root,
                    method=args.method,
                    terms_per_record=args.terms_per_record,
                    topic_limit=args.topic_limit,
                    candidate_limit=args.candidate_limit,
                )
            )
    if args.command == "topic-search":
        raise SystemExit(
            cmd_topic_search(
                root,
                query=args.query,
                limit=args.limit,
                record_types=args.record_types,
                output_format=args.output_format,
            )
        )
    if args.command == "topic-info":
        raise SystemExit(cmd_topic_info(root, record_ref=args.record_ref, limit=args.limit, output_format=args.output_format))
    if args.command == "topic-conflict-candidates":
        raise SystemExit(cmd_topic_conflict_candidates(root, limit=args.limit, output_format=args.output_format))
    if args.command == "tap-record":
        raise SystemExit(
            cmd_tap_record(
                root,
                record_ref=args.record_ref,
                kind=args.kind,
                intent=args.intent,
                note=args.note,
            )
        )
    if args.command == "telemetry-report":
        raise SystemExit(cmd_telemetry_report(root, limit=args.limit, output_format=args.output_format))
    if args.command == "attention-index":
        if args.attention_index_command == "build":
            raise SystemExit(cmd_attention_index_build(root, probe_limit=args.probe_limit))
    if args.command == "attention-map":
        raise SystemExit(cmd_attention_map(root, limit=args.limit, output_format=args.output_format, scope=args.scope, mode=args.mode))
    if args.command == "attention-diagram":
        raise SystemExit(
            cmd_attention_diagram(
                root,
                limit=args.limit,
                output_format=args.output_format,
                scope=args.scope,
                detail=args.detail,
                mode=args.mode,
            )
        )
    if args.command == "attention-diagram-compare":
        raise SystemExit(
            cmd_attention_diagram_compare(
                root,
                limit=args.limit,
                output_format=args.output_format,
                scope=args.scope,
                mode=args.mode,
            )
        )
    if args.command == "curiosity-map":
        raise SystemExit(
            cmd_curiosity_map(
                root,
                volume=args.volume,
                output_format=args.output_format,
                scope=args.scope,
                mode=args.mode,
                html=args.html,
            )
        )
    if args.command == "map-brief":
        raise SystemExit(
            cmd_map_brief(
                root,
                volume=args.volume,
                output_format=args.output_format,
                scope=args.scope,
                mode=args.mode,
                limit=args.limit,
            )
        )
    if args.command == "curiosity-probes":
        raise SystemExit(cmd_curiosity_probes(root, budget=args.budget, output_format=args.output_format, scope=args.scope, mode=args.mode))
    if args.command == "probe-inspect":
        raise SystemExit(cmd_probe_inspect(root, probe_index=args.probe_index, output_format=args.output_format, scope=args.scope, mode=args.mode))
    if args.command == "probe-chain-draft":
        raise SystemExit(cmd_probe_chain_draft(root, probe_index=args.probe_index, output_format=args.output_format, scope=args.scope, mode=args.mode))
    if args.command == "probe-route":
        raise SystemExit(cmd_probe_route(root, probe_index=args.probe_index, output_format=args.output_format, scope=args.scope, mode=args.mode))
    if args.command == "probe-pack":
        raise SystemExit(cmd_probe_pack(root, budget=args.budget, output_format=args.output_format, scope=args.scope, detail=args.detail, mode=args.mode))
    if args.command == "probe-pack-compare":
        raise SystemExit(cmd_probe_pack_compare(root, budget=args.budget, output_format=args.output_format, scope=args.scope, mode=args.mode))
    if args.command == "logic-index":
        if args.logic_index_command == "build":
            raise SystemExit(cmd_logic_index_build(root, candidate_limit=args.candidate_limit))
    if args.command == "logic-search":
        raise SystemExit(
            cmd_logic_search(
                root,
                predicate=args.predicate,
                symbol=args.symbol,
                claim_ref=args.claim_ref,
                limit=args.limit,
                output_format=args.output_format,
            )
        )
    if args.command == "logic-graph":
        raise SystemExit(
            cmd_logic_graph(
                root,
                symbol=args.symbol,
                predicate=args.predicate,
                smells_only=args.smells_only,
                limit=args.limit,
                output_format=args.output_format,
            )
        )
    if args.command == "logic-check":
        raise SystemExit(
            cmd_logic_check(
                root,
                limit=args.limit,
                output_format=args.output_format,
                solver=args.solver,
                closure=args.closure,
            )
        )
    if args.command == "logic-conflict-candidates":
        raise SystemExit(cmd_logic_conflict_candidates(root, limit=args.limit, output_format=args.output_format))
    if args.command == "init-code-index":
        repo_root, repo_root_source = resolve_code_repo_root_or_exit(root, args.root)
        raise SystemExit(
            cmd_init_code_index(
                root,
                repo_root=repo_root,
                max_files=args.max_files,
                max_bytes=args.max_bytes_per_file,
                include_untracked=args.include_untracked,
                backend_index=args.backend_index,
            )
        )
    if args.command == "index-code":
        repo_root, repo_root_source = resolve_code_repo_root_or_exit(root, args.root)
        raise SystemExit(
            cmd_index_code(
                root,
                repo_root=repo_root,
                includes=args.includes,
                excludes=args.excludes,
                max_files=args.max_files,
                max_bytes=args.max_bytes_per_file,
                backend_index=args.backend_index,
            )
        )
    if args.command == "code-refresh":
        repo_root, repo_root_source = resolve_code_repo_root_or_exit(root, args.root)
        raise SystemExit(
            cmd_code_refresh(
                root,
                repo_root=repo_root,
                paths=args.paths,
                max_bytes=args.max_bytes_per_file,
                backend_index=args.backend_index,
            )
        )
    if args.command == "code-info":
        repo_root, repo_root_source = resolve_code_repo_root_or_exit(root, args.root)
        raise SystemExit(
            cmd_code_info(
                root,
                repo_root=repo_root,
                entry_ref=args.entry_ref,
                path=args.path,
                fields_value=args.fields,
                output_format=args.output_format,
            )
        )
    if args.command == "code-search":
        repo_root, repo_root_source = resolve_code_repo_root_or_exit(root, args.root)
        raise SystemExit(
            cmd_code_search(
                root,
                repo_root=repo_root,
                repo_root_source=repo_root_source,
                query=args.query,
                path_patterns=args.path_patterns,
                language=args.language,
                code_kind=args.code_kind,
                imports=args.imports,
                symbols=args.symbols,
                features=args.features,
                refs=args.refs,
                link_candidate_refs=args.link_candidate_refs,
                annotation_kind=args.annotation_kind,
                annotation_categories=args.annotation_categories,
                annotation_status=args.annotation_status,
                include_stale_annotations=args.include_stale_annotations,
                stale=args.stale,
                include_missing=args.include_missing,
                include_superseded=args.include_superseded,
                include_archived=args.include_archived,
                fields_value=args.fields,
                limit=args.limit,
                scope=args.scope,
                output_format=args.output_format,
            )
        )
    if args.command == "code-feedback":
        repo_root, repo_root_source = resolve_code_repo_root_or_exit(root, args.root)
        raise SystemExit(
            cmd_code_feedback(
                root,
                repo_root=repo_root,
                query=args.query,
                path_patterns=args.path_patterns,
                language=args.language,
                link_candidate_refs=args.link_candidate_refs,
                entry_ref=args.entry_ref,
                path=args.target_path,
                apply=args.apply,
                note=args.note,
                limit=args.limit,
                output_format=args.output_format,
            )
        )
    if args.command == "code-smell-report":
        repo_root, repo_root_source = resolve_code_repo_root_or_exit(root, args.root)
        raise SystemExit(
            cmd_code_smell_report(
                root,
                repo_root=repo_root,
                categories=args.categories,
                severities=args.severities,
                include_stale=args.include_stale,
                limit=args.limit,
                output_format=args.output_format,
            )
        )
    if args.command == "code-entry":
        if args.code_entry_command == "create":
            raise SystemExit(
                cmd_code_entry_create(
                    root,
                    target_kind=args.target_kind,
                    path=args.path,
                    name=args.name,
                    symbol_name=args.symbol_name,
                    summary=args.summary,
                    manual_features=args.manual_features,
                    note=args.note,
                )
            )
        if args.code_entry_command == "archive-unscoped":
            raise SystemExit(
                cmd_code_entry_archive_unscoped(
                    root,
                    statuses=args.statuses,
                    apply=args.apply,
                    output_format=args.output_format,
                )
            )
        if args.code_entry_command == "attach-unscoped":
            raise SystemExit(
                cmd_code_entry_attach_unscoped(
                    root,
                    repo_root=args.root,
                    statuses=args.statuses,
                    apply=args.apply,
                    output_format=args.output_format,
                )
            )
    if args.command == "annotate-code":
        raise SystemExit(
            cmd_annotate_code(
                root,
                entry_ref=args.entry_ref,
                path=args.path,
                kind=args.kind,
                text=args.note,
                confidence=args.confidence,
                supersedes=args.supersedes,
                categories=args.categories,
                severity=args.severity,
                suggestions=args.suggestions,
                source_refs=args.source_refs,
                claim_refs=args.claim_refs,
                proposal_refs=args.proposal_refs,
            )
        )
    if args.command == "link-code":
        raise SystemExit(
            cmd_link_code(
                root,
                entry_ref=args.entry_ref,
                path=args.path,
                link_refs={
                    "guideline_refs": args.guideline_refs,
                    "claim_refs": args.claim_refs,
                    "model_refs": args.model_refs,
                    "flow_refs": args.flow_refs,
                    "source_refs": args.source_refs,
                    "plan_refs": args.plan_refs,
                    "debt_refs": args.debt_refs,
                    "open_question_refs": args.open_question_refs,
                    "working_context_refs": args.working_context_refs,
                },
                note=args.note,
            )
        )
    if args.command == "assign-code-index":
        raise SystemExit(cmd_assign_code_index(root, record_ref=args.record_ref, entry_refs=args.entry_refs, note=args.note))
    if args.command == "build-reasoning-case":
        raise SystemExit(
            cmd_build_reasoning_case(
                root,
                task=args.task,
                claim_refs=args.claim_refs,
                model_refs=args.model_refs,
                flow_refs=args.flow_refs,
                limit=args.limit,
            )
        )
    if args.command in {"validate-planning-chain", "validate-evidence-chain"}:
        raise SystemExit(cmd_validate_evidence_chain(root, Path(args.chain_file).expanduser().resolve()))
    if args.command == "validate-decision":
        raise SystemExit(
            cmd_validate_decision(
                root,
                mode=args.mode,
                chain_file=Path(args.chain_file).expanduser().resolve(),
                output_format=args.output_format,
                emit_permit=args.emit_permit,
                action_kind=args.action_kind,
                ttl_seconds=args.ttl_seconds,
            )
        )
    if args.command == "augment-chain":
        raise SystemExit(
            cmd_augment_chain(
                root,
                Path(args.chain_file).expanduser().resolve(),
                output_format=args.output_format,
            )
        )
    if args.command == "change-strictness":
        raise SystemExit(
            cmd_change_strictness(
                root,
                args.value,
                permission_ref=args.permission_ref,
                request_ref=args.request_ref,
                approval_source_ref=args.approval_source_ref,
            )
        )
    if args.command == "request-strictness-change":
        raise SystemExit(
            cmd_request_strictness_change(
                root,
                args.value,
                permission_ref=args.permission_ref,
                reason=args.reason,
                scope=args.scope,
            )
        )
    if args.command == "scan-conflicts":
        raise SystemExit(cmd_scan_conflicts(root))
    if args.command == "record-workspace":
        raise SystemExit(
            cmd_record_workspace(
                root,
                workspace_key=args.workspace_key,
                title=args.title,
                context_root=args.context_root,
                root_refs=args.root_refs,
                project_refs=args.project_refs,
                status=args.status,
                tags=args.tags,
                note=args.note,
            )
        )
    if args.command == "show-workspace":
        raise SystemExit(cmd_show_workspace(root, show_all=args.show_all))
    if args.command == "set-current-workspace":
        raise SystemExit(cmd_set_current_workspace(root, workspace_ref=args.workspace_ref, clear=args.clear))
    if args.command == "workspace-admission":
        if args.workspace_admission_command == "check":
            raise SystemExit(
                cmd_workspace_admission_check(
                    root,
                    repo=Path(args.repo).expanduser(),
                    output_format=args.output_format,
                )
            )
    if args.command == "assign-workspace":
        raise SystemExit(
            cmd_assign_workspace(
                root,
                workspace_ref=args.workspace_ref,
                record_refs=args.record_refs,
                records_file=args.records_file,
                all_unassigned=args.all_unassigned,
                note=args.note,
            )
        )
    if args.command == "init-anchor":
        raise SystemExit(
            cmd_init_anchor(
                root,
                directory=args.directory,
                workspace_ref=args.workspace_ref,
                project_ref=args.project_ref,
                task_ref=args.task_ref,
                allowed_freedom=args.allowed_freedom,
                hook_verbosity=args.hook_verbosity,
                force=args.force,
                note=args.note,
            )
        )
    if args.command == "show-anchor":
        raise SystemExit(cmd_show_anchor(args.start))
    if args.command == "validate-anchor":
        raise SystemExit(cmd_validate_anchor(root, args.start))
    if args.command == "record-project":
        raise SystemExit(
            cmd_record_project(
                root,
                project_key=args.project_key,
                title=args.title,
                root_refs=args.root_refs,
                workspace_refs=args.workspace_refs,
                status=args.status,
                related_project_refs=args.related_project_refs,
                tags=args.tags,
                note=args.note,
            )
        )
    if args.command == "show-project":
        raise SystemExit(cmd_show_project(root, show_all=args.show_all))
    if args.command == "set-current-project":
        raise SystemExit(cmd_set_current_project(root, project_ref=args.project_ref, clear=args.clear))
    if args.command == "assign-project":
        raise SystemExit(cmd_assign_project(root, project_ref=args.project_ref, record_ref=args.record_ref, note=args.note))
    if args.command == "assign-task":
        raise SystemExit(cmd_assign_task(root, task_ref=args.task_ref, record_ref=args.record_ref, note=args.note))
    if args.command == "record-restriction":
        raise SystemExit(
            cmd_record_restriction(
                root,
                scope=args.scope,
                title=args.title,
                applies_to=args.applies_to,
                severity=args.severity,
                rules=args.rules,
                project_refs=args.project_refs,
                task_refs=args.task_refs,
                related_claim_refs=args.related_claim_refs,
                supersedes_refs=args.supersedes_refs,
                imposed_by=args.imposed_by,
                imposed_at=args.imposed_at,
                tags=args.tags,
                note=args.note,
            )
        )
    if args.command == "show-restrictions":
        raise SystemExit(cmd_show_restrictions(root, show_all=args.show_all))
    if args.command == "record-guideline":
        raise SystemExit(
            cmd_record_guideline(
                root,
                scope=args.scope,
                domain=args.domain,
                applies_to=args.applies_to,
                priority=args.priority,
                rule=args.rule,
                source_refs=args.source_refs,
                project_refs=args.project_refs,
                task_refs=args.task_refs,
                related_claim_refs=args.related_claim_refs,
                conflict_refs=args.conflict_refs,
                supersedes_refs=args.supersedes_refs,
                examples=args.examples,
                rationale=args.rationale,
                tags=args.tags,
                note=args.note,
            )
        )
    if args.command == "show-guidelines":
        raise SystemExit(cmd_show_guidelines(root, show_all=args.show_all, domain=args.domain))
    if args.command == "record-proposal":
        raise SystemExit(
            cmd_record_proposal(
                root,
                scope=args.scope,
                status=args.status,
                subject=args.subject,
                position=args.position,
                proposal_options=args.proposal_options,
                claim_refs=args.claim_refs,
                guideline_refs=args.guideline_refs,
                model_refs=args.model_refs,
                flow_refs=args.flow_refs,
                open_question_refs=args.open_question_refs,
                assumptions=args.assumptions,
                concerns=args.concerns,
                risks=args.risks,
                stop_conditions=args.stop_conditions,
                confidence=args.confidence,
                created_by=args.created_by,
                project_refs=args.project_refs,
                task_refs=args.task_refs,
                supersedes_refs=args.supersedes_refs,
                tags=args.tags,
                note=args.note,
            )
        )
    if args.command == "configure-runtime":
        raise SystemExit(
                cmd_configure_runtime(
                    root,
                    hook_verbosity=args.hook_verbosity,
                    hook_run_capture=args.hook_run_capture,
                    backend_preset=args.backend_preset,
                budget_items=args.context_budget,
                input_capture_items=args.input_capture_items,
                analysis_items=args.analysis_items,
                backend_items=args.backend_items,
                show=args.show,
            )
        )
    if args.command == "backend-status":
        repo_root, repo_root_source = resolve_code_repo_root(root, args.root, fallback_to_cwd=False)
        raise SystemExit(cmd_backend_status(root, output_format=args.output_format, repo_root=repo_root, scope=args.scope))
    if args.command == "backend-check":
        repo_root, repo_root_source = resolve_code_repo_root(root, args.root, fallback_to_cwd=False)
        raise SystemExit(
            cmd_backend_check(root, backend=args.backend, output_format=args.output_format, repo_root=repo_root, scope=args.scope)
        )
    if args.command == "validate-facts":
        raise SystemExit(cmd_validate_facts(root, backend=args.backend, output_format=args.output_format))
    if args.command == "export-rdf":
        output_path = args.output.expanduser().resolve() if args.output else None
        raise SystemExit(cmd_export_rdf(root, output_format=args.output_format, output=output_path))
    if args.command == "start-task":
        raise SystemExit(
            cmd_start_task(
                root,
                scope=args.scope,
                title=args.title,
                task_type=args.task_type,
                execution_mode="autonomous" if args.autonomous else args.execution_mode,
                description=args.description,
                related_claim_refs=args.related_claim_refs,
                related_model_refs=args.related_model_refs,
                related_flow_refs=args.related_flow_refs,
                open_question_refs=args.open_question_refs,
                plan_refs=args.plan_refs,
                debt_refs=args.debt_refs,
                action_refs=args.action_refs,
                project_refs=args.project_refs,
                tags=args.tags,
                note=args.note,
            )
        )
    if args.command == "show-task":
        raise SystemExit(cmd_show_task(root, show_all=args.show_all))
    if args.command == "validate-task-decomposition":
        raise SystemExit(
            cmd_validate_task_decomposition(
                root,
                task_ref=args.task_ref,
                output_format=args.output_format,
            )
        )
    if args.command == "confirm-atomic-task":
        raise SystemExit(
            cmd_confirm_atomic_task(
                root,
                task_ref=args.task_ref,
                deliverable=args.deliverable,
                done_criteria=args.done_criteria,
                verification=args.verification,
                scope_boundary=args.scope_boundary,
                blocker_policy=args.blocker_policy,
                no_verification_needed=args.no_verification_needed,
                note=args.note,
            )
        )
    if args.command == "decompose-task":
        raise SystemExit(
            cmd_decompose_task(
                root,
                task_ref=args.task_ref,
                subtask_specs=args.subtask_specs,
                note=args.note,
            )
        )
    if args.command == "task-outcome-check":
        raise SystemExit(
            cmd_task_outcome_check(
                root,
                task_ref=args.task_ref,
                outcome=args.outcome,
                output_format=args.output_format,
            )
        )
    if args.command == "working-context":
        if args.working_context_command == "create":
            raise SystemExit(
                cmd_working_context_create(
                    root,
                    scope=args.scope,
                    title=args.title,
                    context_kind=args.context_kind,
                    pinned_refs=args.pinned_refs,
                    focus_paths=args.focus_paths,
                    topic_terms=args.topic_terms,
                    topic_seed_refs=args.topic_seed_refs,
                    assumption_values=args.assumptions,
                    concerns=args.concerns,
                    project_refs=args.project_refs,
                    task_refs=args.task_refs,
                    tags=args.tags,
                    note=args.note,
                )
            )
        if args.working_context_command == "show":
            raise SystemExit(
                cmd_working_context_show(
                    root,
                    context_ref=args.context_ref,
                    show_all=args.show_all,
                    output_format=args.output_format,
                )
            )
        if args.working_context_command == "check-drift":
            raise SystemExit(cmd_working_context_check_drift(root, task_text=args.task, output_format=args.output_format))
        if args.working_context_command == "fork":
            raise SystemExit(
                cmd_working_context_fork(
                    root,
                    context_ref=args.context_ref,
                    title=args.title,
                    context_kind=args.context_kind,
                    add_pinned_refs=args.add_pinned_refs,
                    remove_pinned_refs=args.remove_pinned_refs,
                    add_focus_paths=args.add_focus_paths,
                    remove_focus_paths=args.remove_focus_paths,
                    add_topic_terms=args.add_topic_terms,
                    remove_topic_terms=args.remove_topic_terms,
                    add_topic_seed_refs=args.add_topic_seed_refs,
                    remove_topic_seed_refs=args.remove_topic_seed_refs,
                    add_assumption_values=args.add_assumptions,
                    add_concerns=args.add_concerns,
                    project_refs=args.project_refs,
                    task_refs=args.task_refs,
                    tags=args.tags,
                    note=args.note,
                )
            )
        if args.working_context_command == "close":
            raise SystemExit(
                cmd_working_context_close(
                    root,
                    context_ref=args.context_ref,
                    status=args.status,
                    note=args.note,
                )
            )
    if args.command == "complete-task":
        raise SystemExit(cmd_finish_task(root, task_ref=args.task_ref, final_status="completed", note=args.note))
    if args.command == "pause-task":
        raise SystemExit(cmd_finish_task(root, task_ref=args.task_ref, final_status="paused", note=args.note))
    if args.command == "resume-task":
        raise SystemExit(cmd_resume_task(root, task_ref=args.task_ref, note=args.note))
    if args.command == "switch-task":
        raise SystemExit(cmd_switch_task(root, task_ref=args.task_ref, note=args.note))
    if args.command == "stop-task":
        raise SystemExit(cmd_finish_task(root, task_ref=args.task_ref, final_status="stopped", note=args.note))
    if args.command == "task-drift-check":
        raise SystemExit(cmd_task_drift_check(root, intent=args.intent, task_ref=args.task_ref, task_type=args.task_type))
    if args.command == "review-precedents":
        raise SystemExit(
            cmd_review_precedents(
                root,
                task_ref=args.task_ref,
                task_type=args.task_type,
                query=args.query,
                limit=args.limit,
            )
        )
    if args.command == "impact-graph":
        raise SystemExit(cmd_impact_graph(root, claim_ref=args.claim_ref))
    if args.command == "linked-records":
        raise SystemExit(
            cmd_linked_records(
                root,
                record_ref=args.record_ref,
                direction=args.direction,
                depth=args.depth,
                output_format=args.output_format,
            )
        )
    if args.command == "promote-model-to-domain":
        raise SystemExit(cmd_promote_model_to_domain(root, model_ref=args.model_ref, note=args.note))
    if args.command == "promote-flow-to-domain":
        raise SystemExit(cmd_promote_flow_to_domain(root, flow_ref=args.flow_ref, note=args.note))
    if args.command == "mark-stale-from-claim":
        raise SystemExit(cmd_mark_stale_from_claim(root, claim_ref=args.claim_ref, note=args.note))
    if args.command == "rollback-report":
        raise SystemExit(cmd_rollback_report(root, claim_ref=args.claim_ref))
    if args.command == "record-permission":
        raise SystemExit(
            cmd_record_permission(
                root,
                scope=args.scope,
                applies_to=args.applies_to,
                granted_by=args.granted_by,
                grants=args.grants,
                project_refs=args.project_refs,
                task_refs=args.task_refs,
                granted_at=args.granted_at,
                tags=args.tags,
                note=args.note,
            )
        )
    if args.command == "record-action":
        raise SystemExit(
            cmd_record_action(
                root,
                kind=args.kind,
                scope=args.scope,
                justified_by=args.justified_by,
                safety_class=args.safety_class,
                status=args.status,
                planned_at=args.planned_at,
                executed_at=args.executed_at,
                project_refs=args.project_refs,
                task_refs=args.task_refs,
                evidence_chain=args.evidence_chain.expanduser().resolve() if args.evidence_chain else None,
                tags=args.tags,
                note=args.note,
            )
        )
    if args.command == "record-input":
        text = sys.stdin.read() if args.text_stdin else args.text
        raise SystemExit(
            cmd_record_input(
                root,
                scope=args.scope,
                input_kind=args.input_kind,
                origin_kind=args.origin_kind,
                origin_ref=args.origin_ref,
                text=text,
                artifact_refs=args.artifact_refs,
                session_ref=args.session_ref,
                derived_record_refs=args.derived_record_refs,
                captured_at=args.captured_at,
                project_refs=args.project_refs,
                task_refs=args.task_refs,
                tags=args.tags,
                note=args.note,
            )
        )
    if args.command == "record-run":
        raise SystemExit(
            cmd_record_run(
                root,
                scope=args.scope,
                command=args.shell_command,
                cwd=args.cwd,
                exit_code=args.exit_code,
                stdout_quote=args.stdout_quote,
                stderr_quote=args.stderr_quote,
                action_kind=args.action_kind,
                artifact_refs=args.artifact_refs,
                project_refs=args.project_refs,
                task_refs=args.task_refs,
                tags=args.tags,
                note=args.note,
            )
        )
    if args.command == "classify-input":
        raise SystemExit(
            cmd_classify_input(
                root,
                input_ref=args.input_ref,
                derived_record_refs=args.derived_record_refs,
                note=args.note,
            )
        )
    if args.command == "input-triage":
        if args.input_triage_command == "report":
            raise SystemExit(
                cmd_input_triage_report(
                    root,
                    task_ref=args.task_ref,
                    limit=args.limit,
                    output_format=args.output_format,
                )
            )
        if args.input_triage_command == "link-operational":
            raise SystemExit(
                cmd_input_triage_link_operational(
                    root,
                    task_ref=args.task_ref,
                    input_refs=args.input_refs,
                    note=args.note,
                )
            )
        raise SystemExit(2)
    if args.command == "record-evidence":
        raise SystemExit(
            cmd_record_evidence(
                root,
                scope=args.scope,
                kind=args.kind,
                quote=args.quote,
                path_value=args.path_value,
                line=args.line,
                end_line=args.end_line,
                command=args.shell_command,
                cwd=args.cwd,
                exit_code=args.exit_code,
                stdout_quote=args.stdout_quote,
                stderr_quote=args.stderr_quote,
                action_kind=args.action_kind,
                input_refs=args.input_refs,
                artifact_refs=args.artifact_refs,
                origin_ref=args.origin_ref,
                critique_status=args.critique_status,
                confidence=args.confidence,
                project_refs=args.project_refs,
                task_refs=args.task_refs,
                tags=args.tags,
                red_flags=args.red_flags,
                note=args.note,
                claim_statement=args.claim_statement,
                claim_plane=args.claim_plane,
                claim_status=args.claim_status,
                claim_kind=args.claim_kind,
                support_refs=args.support_refs,
                contradiction_refs=args.contradiction_refs,
                derived_from=args.derived_from,
                recorded_at=args.recorded_at,
            )
        )
    if args.command == "record-support":
        raise SystemExit(
            cmd_record_evidence(
                root,
                scope=args.scope,
                kind=args.kind,
                quote=args.quote,
                path_value=args.path_value,
                line=args.line,
                end_line=args.end_line,
                command=args.shell_command,
                cwd=args.cwd,
                exit_code=args.exit_code,
                stdout_quote=args.stdout_quote,
                stderr_quote=args.stderr_quote,
                action_kind=args.action_kind,
                input_refs=args.input_refs,
                artifact_refs=args.artifact_refs,
                origin_ref=None,
                critique_status="accepted",
                confidence=None,
                project_refs=args.project_refs,
                task_refs=args.task_refs,
                tags=args.tags,
                red_flags=[],
                note=args.note,
                claim_statement=args.thought,
                claim_plane=args.claim_plane,
                claim_status=args.claim_status,
                claim_kind=args.claim_kind,
                support_refs=[],
                contradiction_refs=[],
                derived_from=[],
                recorded_at=None,
            )
        )
    if args.command == "record-source":
        raise SystemExit(
            cmd_record_source(
                root,
                scope=args.scope,
                source_kind=args.source_kind,
                critique_status=args.critique_status,
                origin_kind=args.origin_kind,
                origin_ref=args.origin_ref,
                quote=args.quote,
                artifact_refs=args.artifact_refs,
                confidence=args.confidence,
                independence_group=args.independence_group,
                captured_at=args.captured_at,
                project_refs=args.project_refs,
                task_refs=args.task_refs,
                tags=args.tags,
                red_flags=args.red_flags,
                note=args.note,
            )
        )
    if args.command == "record-claim":
        try:
            comparison = build_comparison_payload(args)
            logic = build_logic_payload(args)
        except ValueError as exc:
            print(exc)
            raise SystemExit(1)
        except json.JSONDecodeError as exc:
            print(f"invalid --logic-json: {exc}")
            raise SystemExit(1)
        raise SystemExit(
            cmd_record_claim(
                root,
                scope=args.scope,
                plane=args.plane,
                status=args.status,
                statement=args.statement,
                source_refs=args.source_refs,
                support_refs=args.support_refs,
                contradiction_refs=args.contradiction_refs,
                derived_from=args.derived_from,
                claim_kind=args.claim_kind,
                confidence=args.confidence,
                comparison=comparison,
                logic=logic,
                recorded_at=args.recorded_at,
                project_refs=args.project_refs,
                task_refs=args.task_refs,
                tags=args.tags,
                red_flags=args.red_flags,
                note=args.note,
            )
        )
    if args.command == "record-link":
        raise SystemExit(
            cmd_record_link(
                root,
                scope=args.scope,
                left_ref=args.left_ref,
                right_ref=args.right_ref,
                probe_index=args.probe_index,
                probe_scope=args.probe_scope,
                mode=args.mode,
                relation=args.relation,
                quote=args.quote,
                confidence=args.confidence,
                project_refs=args.project_refs,
                task_refs=args.task_refs,
                tags=args.tags,
                note=args.note,
            )
        )
    if args.command == "show-claim-lifecycle":
        raise SystemExit(cmd_show_claim_lifecycle(root, claim_ref=args.claim_ref))
    if args.command == "resolve-claim":
        raise SystemExit(
            cmd_resolve_claim(
                root,
                claim_ref=args.claim_ref,
                note=args.note,
                resolved_by_claim_refs=args.resolved_by_claim_refs,
                resolved_by_action_refs=args.resolved_by_action_refs,
                reactivation_conditions=args.reactivation_conditions,
            )
        )
    if args.command == "archive-claim":
        raise SystemExit(cmd_archive_claim(root, claim_ref=args.claim_ref, note=args.note))
    if args.command == "restore-claim":
        raise SystemExit(cmd_restore_claim(root, claim_ref=args.claim_ref, note=args.note))
    if args.command == "record-plan":
        raise SystemExit(
            cmd_record_plan(
                root,
                scope=args.scope,
                title=args.title,
                priority=args.priority,
                status=args.status,
                justified_by=args.justified_by,
                steps=args.steps,
                success_criteria=args.success_criteria,
                blocked_by=args.blocked_by,
                project_refs=args.project_refs,
                task_refs=args.task_refs,
                tags=args.tags,
                note=args.note,
            )
        )
    if args.command == "validate-plan-decomposition":
        raise SystemExit(
            cmd_validate_plan_decomposition(
                root,
                plan_ref=args.plan_ref,
                output_format=args.output_format,
            )
        )
    if args.command == "confirm-atomic-plan":
        raise SystemExit(
            cmd_confirm_atomic_plan(
                root,
                plan_ref=args.plan_ref,
                task_ref=args.task_ref,
                note=args.note,
            )
        )
    if args.command == "decompose-plan":
        raise SystemExit(
            cmd_decompose_plan(
                root,
                plan_ref=args.plan_ref,
                subplan_specs=args.subplan_specs,
                note=args.note,
            )
        )
    if args.command == "record-debt":
        raise SystemExit(
            cmd_record_debt(
                root,
                scope=args.scope,
                title=args.title,
                priority=args.priority,
                status=args.status,
                evidence_refs=args.evidence_refs,
                plan_refs=args.plan_refs,
                project_refs=args.project_refs,
                task_refs=args.task_refs,
                tags=args.tags,
                note=args.note,
            )
        )
    if args.command == "record-feedback":
        raise SystemExit(
            cmd_record_feedback(
                root,
                scope=args.scope,
                kind=args.kind,
                severity=args.severity,
                surface=args.surface,
                title=args.title,
                actual=args.actual,
                expected=args.expected,
                repro_steps=args.repro_steps,
                suggestions=args.suggestions,
                evidence_refs=args.evidence_refs,
                project_refs=args.project_refs,
                task_refs=args.task_refs,
                tags=args.tags,
                note=args.note,
                origin_ref=args.origin_ref,
                created_by=args.created_by,
            )
        )
    if args.command == "record-model":
        raise SystemExit(
            cmd_record_model(
                root,
                knowledge_class=args.knowledge_class,
                domain=args.domain,
                scope=args.scope,
                aspect=args.aspect,
                status=args.status,
                is_primary=args.primary,
                summary=args.summary,
                claim_refs=args.claim_refs,
                open_question_refs=args.open_question_refs,
                hypothesis_refs=args.hypothesis_refs,
                related_model_refs=args.related_model_refs,
                supersedes_refs=args.supersedes_refs,
                promoted_from_refs=args.promoted_from_refs,
                project_refs=args.project_refs,
                task_refs=args.task_refs,
                note=args.note,
            )
        )
    if args.command == "record-flow":
        step_fields = [
            args.step_ids,
            args.step_labels,
            args.step_statuses,
            args.step_claim_refs,
            args.step_next_steps,
            args.step_open_question_refs,
            args.step_accepted_deviation_refs,
        ]
        lengths = {len(field) for field in step_fields}
        if len(lengths) != 1:
            print("flow step arguments must be supplied with the same number of entries")
            raise SystemExit(1)
        steps: list[dict] = []
        for step_id, label, status, claim_refs_raw, next_steps_raw, open_refs_raw, deviation_refs_raw in zip(
            args.step_ids,
            args.step_labels,
            args.step_statuses,
            args.step_claim_refs,
            args.step_next_steps,
            args.step_open_question_refs,
            args.step_accepted_deviation_refs,
            strict=True,
        ):
            steps.append(
                build_flow_step(
                    step_id=step_id,
                    label=label,
                    status=status,
                    claim_refs=[item for item in claim_refs_raw.split(",") if item],
                    next_steps=[item for item in next_steps_raw.split(",") if item],
                    open_question_refs=[item for item in open_refs_raw.split(",") if item],
                    accepted_deviation_refs=[item for item in deviation_refs_raw.split(",") if item],
                )
            )
        raise SystemExit(
            cmd_record_flow(
                root,
                knowledge_class=args.knowledge_class,
                domain=args.domain,
                scope=args.scope,
                status=args.status,
                is_primary=args.primary,
                summary=args.summary,
                model_refs=args.model_refs,
                open_question_refs=args.open_question_refs,
                precondition_claim_refs=args.precondition_claim_refs,
                precondition_hypothesis_refs=args.precondition_hypothesis_refs,
                precondition_note=args.precondition_note,
                oracle_success_claim_refs=args.oracle_success_claim_refs,
                oracle_failure_claim_refs=args.oracle_failure_claim_refs,
                oracle_hypothesis_refs=args.oracle_hypothesis_refs,
                oracle_note=args.oracle_note,
                steps=steps,
                supersedes_refs=args.supersedes_refs,
                promoted_from_refs=args.promoted_from_refs,
                project_refs=args.project_refs,
                task_refs=args.task_refs,
                note=args.note,
            )
        )
    if args.command == "record-open-question":
        raise SystemExit(
            cmd_record_open_question(
                root,
                domain=args.domain,
                scope=args.scope,
                aspect=args.aspect,
                status=args.status,
                question=args.question,
                related_claim_refs=args.related_claim_refs,
                related_model_refs=args.related_model_refs,
                related_flow_refs=args.related_flow_refs,
                resolved_by_claim_refs=args.resolved_by_claim_refs,
                project_refs=args.project_refs,
                task_refs=args.task_refs,
                note=args.note,
            )
        )
    if args.command == "record-artifact":
        raise SystemExit(cmd_record_artifact(root, Path(args.path).expanduser().resolve()))
    if args.command == "hypothesis":
        if args.hypothesis_command == "add":
            raise SystemExit(
                cmd_hypothesis_add(
                    root,
                    claim_ref=args.claim_ref,
                    domain=args.domain,
                    scope=args.scope,
                    model_refs=args.model_refs,
                    flow_refs=args.flow_refs,
                    action_refs=args.action_refs,
                    plan_refs=args.plan_refs,
                    rollback_refs=args.rollback_refs,
                    mode=args.mode,
                    based_on_hypotheses=args.based_on_hypotheses,
                    note=args.note,
                )
            )
        if args.hypothesis_command == "list":
            raise SystemExit(cmd_hypothesis_list(root, status=args.status))
        if args.hypothesis_command == "close":
            raise SystemExit(cmd_hypothesis_close(root, claim_ref=args.claim_ref, status=args.status, note=args.note))
        if args.hypothesis_command == "reopen":
            raise SystemExit(cmd_hypothesis_reopen(root, claim_ref=args.claim_ref, note=args.note))
        if args.hypothesis_command == "remove":
            raise SystemExit(cmd_hypothesis_remove(root, claim_ref=args.claim_ref))
        if args.hypothesis_command == "sync":
            raise SystemExit(cmd_hypothesis_sync(root, drop_closed=args.drop_closed))
    raise SystemExit(2)


def main() -> None:
    args = parse_args()
    root = resolve_context_root(args.context, start=Path.cwd())
    if root is None:
        print("Could not resolve TEP context root")
        raise SystemExit(1)
    if command_requires_write_lock(args):
        try:
            with context_write_lock(root):
                dispatch(args, root)
        except TimeoutError as exc:
            print(exc)
            raise SystemExit(1)
        return
    dispatch(args, root)


if __name__ == "__main__":
    main()
