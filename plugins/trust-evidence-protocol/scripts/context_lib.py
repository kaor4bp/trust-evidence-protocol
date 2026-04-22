#!/usr/bin/env python3
"""Shared .codex_context helpers for the trust-evidence-protocol plugin."""

from __future__ import annotations

import re
from pathlib import Path
import sys


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
if str(PLUGIN_ROOT) not in sys.path:
    sys.path.insert(0, str(PLUGIN_ROOT))

from tep_runtime.errors import ValidationError
from tep_runtime.code_index import (
    CODE_INDEX_ALLOWED_RECORD_TYPES,
    CODE_INDEX_ANNOTATION_KINDS,
    CODE_INDEX_ANNOTATION_STATUSES,
    CODE_INDEX_LANGUAGES,
    CODE_INDEX_LINK_KEYS,
    CODE_SEARCH_FIELD_ORDER,
    CODE_INDEX_STATUSES,
    CODE_INDEX_TARGET_KINDS,
    CODE_INDEX_TARGET_STATES,
    CODE_SMELL_CATEGORIES,
    CODE_SMELL_SEVERITIES,
    DEFAULT_CODE_INDEX_EXCLUDES,
    DEFAULT_CODE_INDEX_PATTERNS,
    analyze_code_file,
    analyze_js_like,
    analyze_markdown,
    analyze_python,
    annotation_snapshot,
    build_manual_code_index_entry,
    code_annotation_is_stale,
    code_annotation_matches,
    code_entry_current_target_sha,
    code_entry_freshness,
    code_entry_matching_annotations,
    code_entries_text_lines,
    code_index_entry_for_file,
    code_index_excluded,
    code_index_kind,
    code_index_language,
    code_index_path_matches,
    code_index_rel_path,
    code_smell_report_payload,
    code_smell_report_text_lines,
    code_smell_rows,
    code_target_rank,
    detect_code_features,
    discover_files,
    next_code_index_id,
    normalize_smell_categories,
    parse_code_fields,
    persist_code_index_entries,
    project_code_entry,
    public_code_index_entry,
    read_text_sample,
    resolve_code_entry,
    sha256_file,
    validate_code_index_entry,
    validate_code_index_state,
    write_code_index_views,
)
from tep_runtime.chain_permits import (
    DEFAULT_CHAIN_PERMIT_TTL_SECONDS,
    chain_hash,
    chain_permit_text_lines,
    create_chain_permit,
    validate_chain_permit,
)
from tep_runtime.code_backends import (
    cocoindex_index_payload,
    cocoindex_index_text_lines,
    cocoindex_search_payload,
    cocoindex_search_text_lines,
    enrich_backend_results_with_cix,
    parse_cocoindex_search_output,
)
from tep_runtime.actions import build_action_payload
from tep_runtime.attention import (
    ATTENTION_MODES,
    ATTENTION_SCOPES,
    CURIOSITY_MAP_VOLUMES,
    TAP_KINDS,
    append_tap_event,
    attention_diagram_mermaid_lines,
    attention_diagram_metrics,
    attention_diagram_payload,
    attention_diagram_text_lines,
    attention_map_text_lines,
    build_attention_index,
    curiosity_map_html,
    curiosity_map_payload,
    curiosity_map_text_lines,
    map_brief_payload,
    map_brief_text_lines,
    curiosity_probe_text_lines,
    filter_attention_payload,
    load_attention_payload,
    load_tap_events,
    write_attention_index_reports,
)
from tep_runtime.backends import backend_status_payload, backend_status_text_lines, select_backend_status
from tep_runtime.fact_validation import export_rdf_text, rdf_jsonld_payload, validate_facts_payload, validate_facts_text_lines
from tep_runtime.conflicts import (
    CLAIM_COMPARATORS,
    CLAIM_POLARITIES,
    build_comparison_payload,
    collect_conflict_lines,
    comparison_signature,
    validate_claim_comparison,
    write_conflicts_report,
)
from tep_runtime.context_root import (
    GLOBAL_CONTEXT_DIR,
    LEGACY_CONTEXT_DIR,
    TEP_CONTEXT_ENV,
    env_context_root,
    find_legacy_context_root,
    global_context_root,
    normalize_context_root,
    resolve_context_root,
)
from tep_runtime.context_brief import (
    build_context_brief_payload,
    context_brief_text_lines,
    guideline_detail_lines,
    project_detail_lines,
    restriction_detail_lines,
    task_detail_lines,
)
from tep_runtime.curator import (
    CURATOR_POOL_KINDS,
    build_curator_pool_payload,
    curator_pool_text_lines,
)
from tep_runtime.display import (
    claim_line,
    guideline_summary_line,
    project_summary_line,
    restriction_summary_line,
    source_line,
)
from tep_runtime.evidence import join_quote_items, normalize_quote, quote_matches_record
from tep_runtime.flows import (
    build_flow_oracle,
    build_flow_payload,
    build_flow_preconditions,
    build_flow_step,
    promote_flow_to_domain_payloads,
)
from tep_runtime.claims import (
    action_reference_timestamp,
    build_claim_lifecycle_history_entry,
    build_claim_payload,
    claim_attention,
    claim_blocks_current_action,
    claim_is_archived,
    claim_is_fallback,
    claim_lifecycle,
    claim_lifecycle_state,
    claim_lifecycle_transition_timestamp,
    claim_retrieval_tier,
    mutate_claim_lifecycle_payload,
    parse_timestamp,
)
from tep_runtime.cleanup import (
    cleanup_archive_apply_payload,
    cleanup_archive_plan_payload,
    cleanup_archive_plan_text_lines,
    cleanup_archives_payload,
    cleanup_archives_text_lines,
    cleanup_restore_apply_payload,
    cleanup_restore_plan_payload,
    cleanup_restore_plan_text_lines,
    cleanup_candidate_items,
    next_cleanup_archive_id,
)
from tep_runtime.action_graph import NEXT_STEP_INTENTS, build_next_step_payload, next_step_inline, next_step_text_lines
from tep_runtime.ids import (
    ARTIFACT_ID_PATTERN,
    CODE_INDEX_ID_PATTERN,
    ID_PATTERN,
    ID_SUFFIX_PATTERN,
    LEGACY_ID_SUFFIX_PATTERN,
    PROJECT_ID_PATTERN,
    RANDOM_ID_SUFFIX_PATTERN,
    TASK_ID_PATTERN,
    WORKING_CONTEXT_ID_PATTERN,
    WORKSPACE_ID_PATTERN,
    next_artifact_id,
    next_record_id,
    now_timestamp,
)
from tep_runtime.hydration import (
    compute_context_fingerprint,
    invalidate_hydration_state,
    load_hydration_state,
    write_hydration_state,
)
from tep_runtime.generated_views import (
    ACTIVE_DEBT_STATUSES,
    ACTIVE_PLAN_STATUSES,
    PRIORITY_ORDER,
    TERMINAL_DEBT_STATUSES,
    TERMINAL_PLAN_STATUSES,
    attention_line,
    backlog_sort_key,
    build_index,
    collect_dependency_impact,
    fallback_claims,
    recent_records,
    record_attention_label,
    record_updated_at,
    write_attention_report,
    write_backlog,
    write_flows_report,
    write_hypotheses_report,
    write_models_report,
    write_resolved_report,
    write_stale_report,
)
from tep_runtime.guidelines import build_guideline_payload, resolve_guideline_scope
from tep_runtime.hypotheses import (
    active_hypotheses_for,
    active_hypothesis_entry_by_claim,
    build_hypothesis_entry,
    close_hypothesis_entries,
    collect_claim_refs_from_models_flows,
    hypothesis_active_entry_exists,
    load_hypotheses_index,
    remove_hypothesis_entries,
    reopen_hypothesis_entry,
    sync_hypothesis_entries,
    validate_hypothesis_claim,
    validate_hypotheses_index,
    write_hypotheses_index,
)
from tep_runtime.inputs import build_input_payload, input_items_for_task, unclassified_input_items
from tep_runtime.files import FILE_KINDS, build_file_payload, file_metadata, infer_file_kind
from tep_runtime.knowledge import mark_knowledge_records_stale_payloads, stale_knowledge_target_ids
from tep_runtime.io import context_write_lock, parse_json_file, write_json_file, write_text_file
from tep_runtime.local_anchor import ANCHOR_FILENAME, anchor_context_root, anchor_task_ref, find_anchor, find_anchor_path, load_anchor
from tep_runtime.links import (
    collect_link_edges,
    dependency_refs_for_record,
    linked_records_payload,
    record_detail_payload,
    record_detail_text_lines,
    ref_paths,
)
from tep_runtime.logic import (
    LOGIC_POLARITIES,
    LOGIC_PREDICATE_PATTERN,
    LOGIC_SYMBOL_KINDS,
    LOGIC_SYMBOL_PATTERN,
    LOGIC_VARIABLE_PATTERN,
    build_logic_payload,
    collect_logic_symbol_definitions,
    is_scalar_logic_value,
    logic_atom_symbols,
    logic_atom_variables,
    logic_from_claim,
    load_logic_json_payload,
    parse_bool_token,
    parse_logic_atom_expression,
    parse_logic_atom_spec,
    parse_logic_context,
    parse_logic_rule_spec,
    parse_logic_symbol_spec,
    parse_scalar_token,
    validate_claim_logic,
    validate_logic_atom,
    validate_logic_context,
    validate_logic_rule,
    validate_logic_state,
)
from tep_runtime.logic_index import (
    build_logic_index_payload,
    build_logic_vocabulary_graph,
    graph_components,
    load_logic_index_payload,
    load_logic_vocabulary_graph,
    logic_claim_is_current_fact,
    logic_conflict_candidates_from_payload,
    logic_context_key,
    logic_from_record,
    logic_index_paths,
    logic_index_root,
    logic_rule_variables,
    logic_symbol_local,
    logic_symbol_namespace,
    logic_value_key,
    normalized_symbol_local,
    write_logic_index_reports,
)
from tep_runtime.logic_check import (
    effective_logic_solver,
    logic_solver_settings,
    structural_logic_check_payload,
    structural_logic_check_text_lines,
    z3_logic_check_text_lines,
)
from tep_runtime.models import build_model_payload, promote_model_to_domain_payloads
from tep_runtime.open_questions import build_open_question_payload
from tep_runtime.tasks import (
    TASK_OUTCOME_MARKER,
    TASK_TERMINAL_OUTCOMES,
    apply_atomic_task_decomposition,
    apply_decomposed_task_decomposition,
    assign_task_payload,
    build_atomic_task_decomposition,
    build_decomposed_task_decomposition,
    build_precedent_review_payload,
    build_task_drift_payload,
    build_task_payload,
    finish_task_payload,
    pause_task_for_switch_payload,
    precedent_review_text_lines,
    resume_task_payload,
    select_precedent_tasks,
    task_drift_text_lines,
    task_identity_text,
    task_outcome_check_payload,
    task_outcome_check_text_lines,
    task_outcome_from_message,
    task_related_counts,
    task_summary_line,
    task_decomposition_text_lines,
    validate_task_decomposition_payload,
)
from tep_runtime.paths import (
    code_index_entries_root,
    code_index_entry_path,
    hydration_state_path,
    hypotheses_index_path,
    record_path,
    runtime_dir,
    settings_path,
)
from tep_runtime.policy import ACTION_MUTATION_MARKERS, is_mutating_action_kind, validate_runtime_policy
from tep_runtime.planning import (
    apply_atomic_plan_decomposition,
    apply_decomposed_plan_decomposition,
    build_atomic_plan_decomposition,
    build_debt_payload,
    build_plan_payload,
    plan_decomposition_text_lines,
    validate_plan_decomposition_payload,
)
from tep_runtime.permissions import build_permission_payload, resolve_permission_scope
from tep_runtime.projects import assign_project_payload, build_project_payload
from tep_runtime.proposals import build_proposal_payload, parse_proposal_option, proposal_summary_line
from tep_runtime.records import (
    RECORD_DIRS,
    RECORD_TYPE_TO_PREFIX,
    load_code_index_entries,
    load_records,
)
from tep_runtime.runs import RUN_STATUSES, build_run_payload
from tep_runtime.reports import rel_display, write_report, write_validation_report
from tep_runtime.reasoning import (
    EvidenceChainValidation,
    augment_evidence_chain_payload,
    augmented_evidence_chain_text_lines,
    decision_validation_payload,
    decision_validation_text_lines,
    evidence_chain_report_lines,
    validate_chain_node,
    validate_evidence_chain_payload,
)
from tep_runtime.reasoning_case import build_reasoning_case_payload, reasoning_case_text_lines
from tep_runtime.retrieval import (
    active_guidelines_for,
    active_permissions_for,
    select_fallback_claims,
    select_records,
)
from tep_runtime.restrictions import build_restriction_payload, resolve_restriction_scope
from tep_runtime.rollback import (
    build_impact_graph_payload,
    build_rollback_report_payload,
    impact_graph_text_lines,
    rollback_report_text_lines,
)
from tep_runtime.scopes import (
    active_restrictions_for,
    current_project_ref,
    current_task_ref,
    current_workspace_ref,
    guideline_applies,
    permission_applies,
    project_refs_for_write,
    record_belongs_to_project,
    record_belongs_to_task,
    task_refs_for_write,
    workspace_refs_for_write,
)
from tep_runtime.schemas import (
    ACTION_SAFETY_CLASSES,
    ACTION_STATUSES,
    CLAIM_ATTENTION_LEVELS,
    CLAIM_KINDS,
    CLAIM_LIFECYCLE_STATES,
    CLAIM_PLANES,
    CLAIM_STATUSES,
    CRITIQUE_STATUSES,
    DEBT_STATUSES,
    FLOW_STEP_STATUSES,
    GUIDELINE_APPLIES_TO,
    GUIDELINE_DOMAINS,
    GUIDELINE_PRIORITIES,
    GUIDELINE_STATUSES,
    INPUT_KINDS,
    MODEL_FLOW_AUTHORITY_STATUSES,
    MODEL_KNOWLEDGE_CLASSES,
    MODEL_STATUSES,
    OPEN_QUESTION_STATUSES,
    PERMISSION_APPLIES_TO,
    PLAN_STATUSES,
    PRIORITY_LEVELS,
    PROJECT_STATUSES,
    PROPOSAL_STATUSES,
    REF_KEYS,
    RESTRICTION_APPLIES_TO,
    RESTRICTION_SEVERITIES,
    RESTRICTION_STATUSES,
    SOURCE_KINDS,
    TASK_EXECUTION_MODES,
    TASK_STATUSES,
    TASK_TYPES,
    WORKING_CONTEXT_KINDS,
    WORKING_CONTEXT_STATUSES,
    WORKSPACE_STATUSES,
    artifact_ref_exists,
    claim_is_user_confirmed_theory,
    validate_record,
    validate_refs,
)
from tep_runtime.workspaces import assign_workspace_payload, build_workspace_payload
from tep_runtime.search import (
    concise,
    public_record_summary,
    ranked_record_search,
    record_search_text,
    record_search_timestamp,
    record_summary,
    search_record_matches,
    score_record,
)
from tep_runtime.topic_index import (
    TOPIC_STOP_WORDS,
    build_lexical_topic_index,
    claim_topic_terms,
    infer_topic_terms_from_refs,
    load_topic_records,
    record_topic_status,
    task_terms,
    topic_conflict_candidates,
    topic_document_weights,
    topic_index_paths,
    topic_index_root,
    topic_record_text,
    topic_search_matches,
    topic_tokenize,
    write_topic_index_reports,
)
from tep_runtime.telemetry import (
    access_report_payload,
    access_report_text_lines,
    append_access_event,
    claim_refs_from_text,
    command_reads_raw_claims,
    load_access_events,
)
from tep_runtime.sources import build_source_payload, default_independence_group
from tep_runtime.settings import (
    ALLOWED_FREEDOM,
    ANALYSIS_INSTALL_POLICIES,
    ANALYSIS_MISSING_DEPENDENCY_POLICIES,
    BACKEND_MODES,
    COCOINDEX_SCOPES,
    CODE_INTELLIGENCE_BACKENDS,
    CONTEXT_BUDGET_KEYS,
    CONTEXT_BUDGET_VALUES,
    DEFAULT_ANALYSIS_SETTINGS,
    DEFAULT_BACKEND_SETTINGS,
    DEFAULT_CONTEXT_BUDGET,
    DEFAULT_HOOK_SETTINGS,
    DEFAULT_SETTINGS,
    DERIVATION_BACKENDS,
    FACT_VALIDATION_BACKENDS,
    HOOK_MODE_VALUES,
    INPUT_CAPTURE_MODES,
    INPUT_FILE_MENTION_MODES,
    LOGIC_SOLVER_BACKENDS,
    LOGIC_SOLVER_MODES,
    LOGIC_SOLVER_OPTIONAL_BACKENDS,
    PERMISSION_REQUIRED_FREEDOMS,
    STRICTNESS_ORDER,
    TOPIC_PREFILTER_BACKENDS,
    TOPIC_PREFILTER_OPTIONAL_BACKENDS,
    TOPIC_PREFILTER_REBUILD_MODES,
    is_strictness_escalation,
    load_effective_settings,
    load_settings,
    load_strictness_requests,
    next_strictness_request_id,
    normalize_analysis_settings,
    normalize_backend_settings,
    normalize_context_budget,
    normalize_hook_settings,
    normalize_settings_payload,
    permission_allows_strictness,
    strictness_request_allows_change,
    strictness_requests_path,
    validate_settings_state,
    write_strictness_requests,
    write_settings,
)
from tep_runtime.state_validation import (
    collect_validation_errors,
    validate_candidate_record,
    validate_records_state,
)
from tep_runtime.validation import (
    CONFIDENCE_LEVELS,
    ensure_dict,
    ensure_list,
    ensure_string_list,
    safe_list,
    validate_optional_confidence,
    validate_optional_red_flags,
)
from tep_runtime.working_contexts import (
    add_remove_values,
    build_working_context_payload,
    close_working_context_payload,
    fork_working_context_payload,
    parse_working_context_assumption,
    parse_working_context_assumptions,
    working_context_detail_lines,
    working_context_show_payload,
    working_context_summary_line,
)
