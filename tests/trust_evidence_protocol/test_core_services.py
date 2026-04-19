from __future__ import annotations

import json
import re
import sys
import zipfile
from pathlib import Path
from types import SimpleNamespace


REPO_ROOT = Path(__file__).resolve().parents[2]
PLUGIN_ROOT = REPO_ROOT / "plugins" / "trust-evidence-protocol"
SCRIPTS_ROOT = PLUGIN_ROOT / "scripts"

for path in (PLUGIN_ROOT, SCRIPTS_ROOT):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from context_lib import record_path as compat_record_path  # noqa: E402
from context_lib import write_json_file as compat_write_json_file  # noqa: E402
from context_lib import compute_context_fingerprint as compat_compute_context_fingerprint  # noqa: E402
from context_lib import resolve_context_root as compat_resolve_context_root  # noqa: E402
from context_lib import build_context_brief_payload as compat_build_context_brief_payload  # noqa: E402
from context_lib import context_brief_text_lines as compat_context_brief_text_lines  # noqa: E402
from context_lib import guideline_detail_lines as compat_guideline_detail_lines  # noqa: E402
from context_lib import project_detail_lines as compat_project_detail_lines  # noqa: E402
from context_lib import restriction_detail_lines as compat_restriction_detail_lines  # noqa: E402
from context_lib import task_detail_lines as compat_task_detail_lines  # noqa: E402
from context_lib import hydration_state_path as compat_hydration_state_path  # noqa: E402
from context_lib import invalidate_hydration_state as compat_invalidate_hydration_state  # noqa: E402
from context_lib import augment_evidence_chain_payload as compat_augment_evidence_chain_payload  # noqa: E402
from context_lib import augmented_evidence_chain_text_lines as compat_augmented_evidence_chain_text_lines  # noqa: E402
from context_lib import build_claim_lifecycle_history_entry as compat_build_claim_lifecycle_history_entry  # noqa: E402
from context_lib import build_claim_payload as compat_build_claim_payload  # noqa: E402
from context_lib import claim_line as compat_claim_line  # noqa: E402
from context_lib import build_permission_payload as compat_build_permission_payload  # noqa: E402
from context_lib import guideline_summary_line as compat_guideline_summary_line  # noqa: E402
from context_lib import join_quote_items as compat_join_quote_items  # noqa: E402
from context_lib import load_hydration_state as compat_load_hydration_state  # noqa: E402
from context_lib import normalize_quote as compat_normalize_quote  # noqa: E402
from context_lib import write_hydration_state as compat_write_hydration_state  # noqa: E402
from context_lib import is_strictness_escalation as compat_is_strictness_escalation  # noqa: E402
from context_lib import load_strictness_requests as compat_load_strictness_requests  # noqa: E402
from context_lib import next_strictness_request_id as compat_next_strictness_request_id  # noqa: E402
from context_lib import permission_allows_strictness as compat_permission_allows_strictness  # noqa: E402
from context_lib import strictness_request_allows_change as compat_strictness_request_allows_change  # noqa: E402
from context_lib import strictness_requests_path as compat_strictness_requests_path  # noqa: E402
from context_lib import validate_settings_state as compat_validate_settings_state  # noqa: E402
from context_lib import write_strictness_requests as compat_write_strictness_requests  # noqa: E402
from context_lib import claim_attention as compat_claim_attention  # noqa: E402
from context_lib import claim_blocks_current_action as compat_claim_blocks_current_action  # noqa: E402
from context_lib import claim_retrieval_tier as compat_claim_retrieval_tier  # noqa: E402
from context_lib import mutate_claim_lifecycle_payload as compat_mutate_claim_lifecycle_payload  # noqa: E402
from context_lib import cleanup_candidate_items as compat_cleanup_candidate_items  # noqa: E402
from context_lib import cleanup_archive_apply_payload as compat_cleanup_archive_apply_payload  # noqa: E402
from context_lib import cleanup_archive_plan_payload as compat_cleanup_archive_plan_payload  # noqa: E402
from context_lib import cleanup_archive_plan_text_lines as compat_cleanup_archive_plan_text_lines  # noqa: E402
from context_lib import cleanup_archives_payload as compat_cleanup_archives_payload  # noqa: E402
from context_lib import cleanup_archives_text_lines as compat_cleanup_archives_text_lines  # noqa: E402
from context_lib import cleanup_restore_apply_payload as compat_cleanup_restore_apply_payload  # noqa: E402
from context_lib import cleanup_restore_plan_payload as compat_cleanup_restore_plan_payload  # noqa: E402
from context_lib import cleanup_restore_plan_text_lines as compat_cleanup_restore_plan_text_lines  # noqa: E402
from context_lib import active_restrictions_for as compat_active_restrictions_for  # noqa: E402
from context_lib import collect_link_edges as compat_collect_link_edges  # noqa: E402
from context_lib import current_project_ref as compat_current_project_ref  # noqa: E402
from context_lib import current_task_ref as compat_current_task_ref  # noqa: E402
from context_lib import current_workspace_ref as compat_current_workspace_ref  # noqa: E402
from context_lib import dependency_refs_for_record as compat_dependency_refs_for_record  # noqa: E402
from context_lib import linked_records_payload as compat_linked_records_payload  # noqa: E402
from context_lib import guideline_applies as compat_guideline_applies  # noqa: E402
from context_lib import permission_applies as compat_permission_applies  # noqa: E402
from context_lib import parse_timestamp as compat_parse_timestamp  # noqa: E402
from context_lib import project_refs_for_write as compat_project_refs_for_write  # noqa: E402
from context_lib import workspace_refs_for_write as compat_workspace_refs_for_write  # noqa: E402
from context_lib import public_record_summary as compat_public_record_summary  # noqa: E402
from context_lib import quote_matches_record as compat_quote_matches_record  # noqa: E402
from context_lib import record_belongs_to_project as compat_record_belongs_to_project  # noqa: E402
from context_lib import record_belongs_to_task as compat_record_belongs_to_task  # noqa: E402
from context_lib import record_detail_payload as compat_record_detail_payload  # noqa: E402
from context_lib import record_detail_text_lines as compat_record_detail_text_lines  # noqa: E402
from context_lib import record_search_text as compat_record_search_text  # noqa: E402
from context_lib import record_search_timestamp as compat_record_search_timestamp  # noqa: E402
from context_lib import record_summary as compat_record_summary  # noqa: E402
from context_lib import ref_paths as compat_ref_paths  # noqa: E402
from context_lib import ranked_record_search as compat_ranked_record_search  # noqa: E402
from context_lib import resolve_permission_scope as compat_resolve_permission_scope  # noqa: E402
from context_lib import search_record_matches as compat_search_record_matches  # noqa: E402
from context_lib import score_record as compat_score_record  # noqa: E402
from context_lib import active_guidelines_for as compat_active_guidelines_for  # noqa: E402
from context_lib import active_hypotheses_for as compat_active_hypotheses_for  # noqa: E402
from context_lib import active_hypothesis_entry_by_claim as compat_active_hypothesis_entry_by_claim  # noqa: E402
from context_lib import active_permissions_for as compat_active_permissions_for  # noqa: E402
from context_lib import build_hypothesis_entry as compat_build_hypothesis_entry  # noqa: E402
from context_lib import close_hypothesis_entries as compat_close_hypothesis_entries  # noqa: E402
from context_lib import collect_claim_refs_from_models_flows as compat_collect_claim_refs_from_models_flows  # noqa: E402
from context_lib import hypothesis_active_entry_exists as compat_hypothesis_active_entry_exists  # noqa: E402
from context_lib import load_hypotheses_index as compat_load_hypotheses_index  # noqa: E402
from context_lib import is_mutating_action_kind as compat_is_mutating_action_kind  # noqa: E402
from context_lib import mark_knowledge_records_stale_payloads as compat_mark_knowledge_records_stale_payloads  # noqa: E402
from context_lib import parse_proposal_option as compat_parse_proposal_option  # noqa: E402
from context_lib import proposal_summary_line as compat_proposal_summary_line  # noqa: E402
from context_lib import select_fallback_claims as compat_select_fallback_claims  # noqa: E402
from context_lib import select_records as compat_select_records  # noqa: E402
from context_lib import stale_knowledge_target_ids as compat_stale_knowledge_target_ids  # noqa: E402
from context_lib import remove_hypothesis_entries as compat_remove_hypothesis_entries  # noqa: E402
from context_lib import reopen_hypothesis_entry as compat_reopen_hypothesis_entry  # noqa: E402
from context_lib import sync_hypothesis_entries as compat_sync_hypothesis_entries  # noqa: E402
from context_lib import validate_hypothesis_claim as compat_validate_hypothesis_claim  # noqa: E402
from context_lib import validate_hypotheses_index as compat_validate_hypotheses_index  # noqa: E402
from context_lib import validate_runtime_policy as compat_validate_runtime_policy  # noqa: E402
from context_lib import write_hypotheses_index as compat_write_hypotheses_index  # noqa: E402
from context_lib import rel_display as compat_rel_display  # noqa: E402
from context_lib import task_refs_for_write as compat_task_refs_for_write  # noqa: E402
from context_lib import validate_chain_node as compat_validate_chain_node  # noqa: E402
from context_lib import build_reasoning_case_payload as compat_build_reasoning_case_payload  # noqa: E402
from context_lib import evidence_chain_report_lines as compat_evidence_chain_report_lines  # noqa: E402
from context_lib import reasoning_case_text_lines as compat_reasoning_case_text_lines  # noqa: E402
from context_lib import validate_evidence_chain_payload as compat_validate_evidence_chain_payload  # noqa: E402
from context_lib import write_report as compat_write_report  # noqa: E402
from context_lib import write_validation_report as compat_write_validation_report  # noqa: E402
from context_lib import concise as compat_concise  # noqa: E402
from context_lib import CODE_INDEX_TARGET_KINDS as compat_CODE_INDEX_TARGET_KINDS  # noqa: E402
from context_lib import CODE_SMELL_CATEGORIES as compat_CODE_SMELL_CATEGORIES  # noqa: E402
from context_lib import ensure_dict as compat_ensure_dict  # noqa: E402
from context_lib import ensure_list as compat_ensure_list  # noqa: E402
from context_lib import ensure_string_list as compat_ensure_string_list  # noqa: E402
from context_lib import safe_list as compat_safe_list  # noqa: E402
from context_lib import validate_optional_confidence as compat_validate_optional_confidence  # noqa: E402
from context_lib import validate_optional_red_flags as compat_validate_optional_red_flags  # noqa: E402
from context_lib import analyze_code_file as compat_analyze_code_file  # noqa: E402
from context_lib import analyze_markdown as compat_analyze_markdown  # noqa: E402
from context_lib import annotation_snapshot as compat_annotation_snapshot  # noqa: E402
from context_lib import build_manual_code_index_entry as compat_build_manual_code_index_entry  # noqa: E402
from context_lib import code_entries_text_lines as compat_code_entries_text_lines  # noqa: E402
from context_lib import code_index_entry_for_file as compat_code_index_entry_for_file  # noqa: E402
from context_lib import code_smell_report_payload as compat_code_smell_report_payload  # noqa: E402
from context_lib import code_smell_report_text_lines as compat_code_smell_report_text_lines  # noqa: E402
from context_lib import code_smell_rows as compat_code_smell_rows  # noqa: E402
from context_lib import normalize_smell_categories as compat_normalize_smell_categories  # noqa: E402
from context_lib import parse_code_fields as compat_parse_code_fields  # noqa: E402
from context_lib import project_code_entry as compat_project_code_entry  # noqa: E402
from context_lib import public_code_index_entry as compat_public_code_index_entry  # noqa: E402
from context_lib import resolve_code_entry as compat_resolve_code_entry  # noqa: E402
from context_lib import write_code_index_views as compat_write_code_index_views  # noqa: E402
from context_lib import validate_code_index_entry as compat_validate_code_index_entry  # noqa: E402
from context_lib import validate_code_index_state as compat_validate_code_index_state  # noqa: E402
from context_lib import CLAIM_COMPARATORS as compat_CLAIM_COMPARATORS  # noqa: E402
from context_lib import CLAIM_POLARITIES as compat_CLAIM_POLARITIES  # noqa: E402
from context_lib import build_comparison_payload as compat_build_comparison_payload  # noqa: E402
from context_lib import collect_conflict_lines as compat_collect_conflict_lines  # noqa: E402
from context_lib import comparison_signature as compat_comparison_signature  # noqa: E402
from context_lib import validate_claim_comparison as compat_validate_claim_comparison  # noqa: E402
from context_lib import write_conflicts_report as compat_write_conflicts_report  # noqa: E402
from context_lib import SOURCE_KINDS as compat_SOURCE_KINDS  # noqa: E402
from context_lib import collect_validation_errors as compat_collect_validation_errors  # noqa: E402
from context_lib import validate_candidate_record as compat_validate_candidate_record  # noqa: E402
from context_lib import validate_record as compat_validate_record  # noqa: E402
from context_lib import validate_records_state as compat_validate_records_state  # noqa: E402
from context_lib import validate_refs as compat_validate_refs  # noqa: E402
from context_lib import build_action_payload as compat_build_action_payload  # noqa: E402
from context_lib import build_source_payload as compat_build_source_payload  # noqa: E402
from context_lib import build_input_payload as compat_build_input_payload  # noqa: E402
from context_lib import source_line as compat_source_line  # noqa: E402
from context_lib import default_independence_group as compat_default_independence_group  # noqa: E402
from context_lib import build_index as compat_build_index  # noqa: E402
from context_lib import collect_dependency_impact as compat_collect_dependency_impact  # noqa: E402
from context_lib import fallback_claims as compat_fallback_claims  # noqa: E402
from context_lib import record_attention_label as compat_record_attention_label  # noqa: E402
from context_lib import write_attention_report as compat_write_attention_report  # noqa: E402
from context_lib import write_backlog as compat_write_backlog  # noqa: E402
from context_lib import build_flow_oracle as compat_build_flow_oracle  # noqa: E402
from context_lib import build_flow_payload as compat_build_flow_payload  # noqa: E402
from context_lib import build_flow_preconditions as compat_build_flow_preconditions  # noqa: E402
from context_lib import build_flow_step as compat_build_flow_step  # noqa: E402
from context_lib import promote_flow_to_domain_payloads as compat_promote_flow_to_domain_payloads  # noqa: E402
from context_lib import build_guideline_payload as compat_build_guideline_payload  # noqa: E402
from context_lib import resolve_guideline_scope as compat_resolve_guideline_scope  # noqa: E402
from context_lib import build_debt_payload as compat_build_debt_payload  # noqa: E402
from context_lib import build_plan_payload as compat_build_plan_payload  # noqa: E402
from context_lib import build_model_payload as compat_build_model_payload  # noqa: E402
from context_lib import promote_model_to_domain_payloads as compat_promote_model_to_domain_payloads  # noqa: E402
from context_lib import build_open_question_payload as compat_build_open_question_payload  # noqa: E402
from context_lib import assign_project_payload as compat_assign_project_payload  # noqa: E402
from context_lib import build_project_payload as compat_build_project_payload  # noqa: E402
from context_lib import project_summary_line as compat_project_summary_line  # noqa: E402
from context_lib import build_proposal_payload as compat_build_proposal_payload  # noqa: E402
from context_lib import assign_task_payload as compat_assign_task_payload  # noqa: E402
from context_lib import build_precedent_review_payload as compat_build_precedent_review_payload  # noqa: E402
from context_lib import build_task_drift_payload as compat_build_task_drift_payload  # noqa: E402
from context_lib import build_task_payload as compat_build_task_payload  # noqa: E402
from context_lib import finish_task_payload as compat_finish_task_payload  # noqa: E402
from context_lib import pause_task_for_switch_payload as compat_pause_task_for_switch_payload  # noqa: E402
from context_lib import precedent_review_text_lines as compat_precedent_review_text_lines  # noqa: E402
from context_lib import resume_task_payload as compat_resume_task_payload  # noqa: E402
from context_lib import select_precedent_tasks as compat_select_precedent_tasks  # noqa: E402
from context_lib import task_drift_text_lines as compat_task_drift_text_lines  # noqa: E402
from context_lib import task_identity_text as compat_task_identity_text  # noqa: E402
from context_lib import task_related_counts as compat_task_related_counts  # noqa: E402
from context_lib import task_summary_line as compat_task_summary_line  # noqa: E402
from context_lib import write_models_report as compat_write_models_report  # noqa: E402
from context_lib import write_resolved_report as compat_write_resolved_report  # noqa: E402
from context_lib import add_remove_values as compat_add_remove_values  # noqa: E402
from context_lib import build_working_context_payload as compat_build_working_context_payload  # noqa: E402
from context_lib import close_working_context_payload as compat_close_working_context_payload  # noqa: E402
from context_lib import fork_working_context_payload as compat_fork_working_context_payload  # noqa: E402
from context_lib import parse_working_context_assumption as compat_parse_working_context_assumption  # noqa: E402
from context_lib import parse_working_context_assumptions as compat_parse_working_context_assumptions  # noqa: E402
from context_lib import working_context_detail_lines as compat_working_context_detail_lines  # noqa: E402
from context_lib import working_context_show_payload as compat_working_context_show_payload  # noqa: E402
from context_lib import working_context_summary_line as compat_working_context_summary_line  # noqa: E402
from context_lib import build_restriction_payload as compat_build_restriction_payload  # noqa: E402
from context_lib import restriction_summary_line as compat_restriction_summary_line  # noqa: E402
from context_lib import resolve_restriction_scope as compat_resolve_restriction_scope  # noqa: E402
from context_lib import build_impact_graph_payload as compat_build_impact_graph_payload  # noqa: E402
from context_lib import build_rollback_report_payload as compat_build_rollback_report_payload  # noqa: E402
from context_lib import impact_graph_text_lines as compat_impact_graph_text_lines  # noqa: E402
from context_lib import rollback_report_text_lines as compat_rollback_report_text_lines  # noqa: E402
from context_lib import LOGIC_SYMBOL_PATTERN as compat_LOGIC_SYMBOL_PATTERN  # noqa: E402
from context_lib import build_logic_payload as compat_build_logic_payload  # noqa: E402
from context_lib import load_logic_json_payload as compat_load_logic_json_payload  # noqa: E402
from context_lib import logic_atom_symbols as compat_logic_atom_symbols  # noqa: E402
from context_lib import logic_atom_variables as compat_logic_atom_variables  # noqa: E402
from context_lib import parse_bool_token as compat_parse_bool_token  # noqa: E402
from context_lib import parse_logic_atom_expression as compat_parse_logic_atom_expression  # noqa: E402
from context_lib import parse_logic_atom_spec as compat_parse_logic_atom_spec  # noqa: E402
from context_lib import parse_logic_context as compat_parse_logic_context  # noqa: E402
from context_lib import parse_logic_rule_spec as compat_parse_logic_rule_spec  # noqa: E402
from context_lib import parse_logic_symbol_spec as compat_parse_logic_symbol_spec  # noqa: E402
from context_lib import parse_scalar_token as compat_parse_scalar_token  # noqa: E402
from context_lib import validate_claim_logic as compat_validate_claim_logic  # noqa: E402
from context_lib import validate_logic_state as compat_validate_logic_state  # noqa: E402
from context_lib import build_logic_index_payload as compat_build_logic_index_payload  # noqa: E402
from context_lib import build_logic_vocabulary_graph as compat_build_logic_vocabulary_graph  # noqa: E402
from context_lib import load_logic_index_payload as compat_load_logic_index_payload  # noqa: E402
from context_lib import load_logic_vocabulary_graph as compat_load_logic_vocabulary_graph  # noqa: E402
from context_lib import logic_conflict_candidates_from_payload as compat_logic_conflict_candidates_from_payload  # noqa: E402
from context_lib import logic_rule_variables as compat_logic_rule_variables  # noqa: E402
from context_lib import effective_logic_solver as compat_effective_logic_solver  # noqa: E402
from context_lib import logic_solver_settings as compat_logic_solver_settings  # noqa: E402
from context_lib import structural_logic_check_payload as compat_structural_logic_check_payload  # noqa: E402
from context_lib import structural_logic_check_text_lines as compat_structural_logic_check_text_lines  # noqa: E402
from context_lib import write_logic_index_reports as compat_write_logic_index_reports  # noqa: E402
from context_lib import z3_logic_check_text_lines as compat_z3_logic_check_text_lines  # noqa: E402
from context_lib import build_lexical_topic_index as compat_build_lexical_topic_index  # noqa: E402
from context_lib import infer_topic_terms_from_refs as compat_infer_topic_terms_from_refs  # noqa: E402
from context_lib import load_topic_records as compat_load_topic_records  # noqa: E402
from context_lib import task_terms as compat_task_terms  # noqa: E402
from context_lib import topic_conflict_candidates as compat_topic_conflict_candidates  # noqa: E402
from context_lib import topic_search_matches as compat_topic_search_matches  # noqa: E402
from context_lib import topic_tokenize as compat_topic_tokenize  # noqa: E402
from context_lib import write_topic_index_reports as compat_write_topic_index_reports  # noqa: E402
from tep_runtime.generated_views import (  # noqa: E402
    build_index,
    collect_dependency_impact,
    fallback_claims,
    record_attention_label,
    write_attention_report,
    write_backlog,
    write_models_report,
    write_resolved_report,
)
from tep_runtime.actions import build_action_payload  # noqa: E402
from tep_runtime.schemas import SOURCE_KINDS, validate_record, validate_refs  # noqa: E402
from tep_runtime.state_validation import (  # noqa: E402
    collect_validation_errors,
    validate_candidate_record,
    validate_records_state,
)
from tep_runtime.code_index import (  # noqa: E402
    CODE_INDEX_TARGET_KINDS,
    CODE_SMELL_CATEGORIES,
    analyze_code_file,
    analyze_js_like,
    analyze_markdown,
    analyze_python,
    annotation_snapshot,
    build_manual_code_index_entry,
    code_entries_text_lines,
    code_index_entry_for_file,
    code_smell_report_payload,
    code_smell_report_text_lines,
    code_smell_rows,
    normalize_smell_categories,
    parse_code_fields,
    project_code_entry,
    public_code_index_entry,
    resolve_code_entry,
    validate_code_index_entry,
    validate_code_index_state,
    write_code_index_views,
)
from tep_runtime.code_ast import (  # noqa: E402
    analyze_js_like as language_analyze_js_like,
    analyze_markdown as language_analyze_markdown,
    analyze_python as language_analyze_python,
    empty_analysis,
)
from tep_runtime.cli_common import (  # noqa: E402
    append_note,
    command_requires_write_lock,
    parse_csv_refs,
    public_record_payload,
    sanitize_artifact_name,
)
from tep_runtime.conflicts import (  # noqa: E402
    CLAIM_COMPARATORS,
    CLAIM_POLARITIES,
    build_comparison_payload,
    collect_conflict_lines,
    comparison_signature,
    validate_claim_comparison,
    write_conflicts_report,
)
from tep_runtime.claims import (  # noqa: E402
    build_claim_lifecycle_history_entry,
    claim_attention,
    build_claim_payload,
    claim_blocks_current_action,
    claim_is_archived,
    claim_is_fallback,
    claim_lifecycle_state,
    claim_retrieval_tier,
    mutate_claim_lifecycle_payload,
    parse_timestamp,
)
from tep_runtime.cleanup import cleanup_candidate_items  # noqa: E402
from tep_runtime.cleanup import (  # noqa: E402
    cleanup_archive_apply_payload,
    cleanup_archive_plan_payload,
    cleanup_archive_plan_text_lines,
    cleanup_archives_payload,
    cleanup_archives_text_lines,
    cleanup_restore_apply_payload,
    cleanup_restore_plan_payload,
    cleanup_restore_plan_text_lines,
)
from tep_runtime.errors import ValidationError  # noqa: E402
from tep_runtime.evidence import join_quote_items, normalize_quote, quote_matches_record  # noqa: E402
from tep_runtime.flows import (  # noqa: E402
    build_flow_oracle,
    build_flow_payload,
    build_flow_preconditions,
    build_flow_step,
    promote_flow_to_domain_payloads,
)
from tep_runtime.guidelines import build_guideline_payload, resolve_guideline_scope  # noqa: E402
from tep_runtime.links import (  # noqa: E402
    collect_link_edges,
    dependency_refs_for_record,
    linked_records_payload,
    record_detail_payload,
    record_detail_text_lines,
    ref_paths,
)
from tep_runtime.planning import build_debt_payload, build_plan_payload  # noqa: E402
from tep_runtime.permissions import build_permission_payload, resolve_permission_scope  # noqa: E402
from tep_runtime.restrictions import build_restriction_payload, resolve_restriction_scope  # noqa: E402
from tep_runtime.sources import build_source_payload, default_independence_group  # noqa: E402
from tep_runtime.inputs import build_input_payload  # noqa: E402
from tep_runtime.display import (  # noqa: E402
    claim_line,
    guideline_summary_line,
    project_summary_line,
    restriction_summary_line,
    source_line,
)
from tep_runtime.action_graph import build_next_step_payload, next_step_inline, next_step_text_lines  # noqa: E402
from tep_runtime.scopes import (  # noqa: E402
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
from tep_runtime.search import (  # noqa: E402
    concise,
    public_record_summary,
    ranked_record_search,
    record_search_text,
    record_search_timestamp,
    record_summary,
    search_record_matches,
    score_record,
)
from tep_runtime.hydration import (  # noqa: E402
    compute_context_fingerprint,
    invalidate_hydration_state,
    load_hydration_state,
    write_hydration_state,
)
from tep_runtime.hypotheses import (  # noqa: E402
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
from tep_runtime.knowledge import mark_knowledge_records_stale_payloads, stale_knowledge_target_ids  # noqa: E402
from tep_runtime.rollback import (  # noqa: E402
    build_impact_graph_payload,
    build_rollback_report_payload,
    impact_graph_text_lines,
    rollback_report_text_lines,
)
from tep_runtime.context_root import (  # noqa: E402
    TEP_CONTEXT_ENV,
    find_legacy_context_root,
    global_context_root,
    resolve_context_root,
)
from tep_runtime.context_brief import (  # noqa: E402
    build_context_brief_payload,
    context_brief_text_lines,
    guideline_detail_lines,
    project_detail_lines,
    restriction_detail_lines,
    task_detail_lines,
    workspace_detail_lines,
)
from tep_runtime.ids import next_artifact_id, next_record_id, now_timestamp  # noqa: E402
from tep_runtime.io import context_write_lock, parse_json_file, write_json_file  # noqa: E402
from tep_runtime.logic import (  # noqa: E402
    LOGIC_SYMBOL_PATTERN,
    build_logic_payload,
    load_logic_json_payload,
    logic_atom_symbols,
    logic_atom_variables,
    parse_bool_token,
    parse_logic_atom_expression,
    parse_logic_atom_spec,
    parse_logic_context,
    parse_logic_rule_spec,
    parse_logic_symbol_spec,
    parse_scalar_token,
    validate_claim_logic,
    validate_logic_state,
)
from tep_runtime.logic_index import (  # noqa: E402
    build_logic_index_payload,
    build_logic_vocabulary_graph,
    load_logic_index_payload,
    load_logic_vocabulary_graph,
    logic_conflict_candidates_from_payload,
    logic_rule_variables,
    write_logic_index_reports,
)
from tep_runtime.logic_check import (  # noqa: E402
    effective_logic_solver,
    logic_solver_settings,
    structural_logic_check_payload,
    structural_logic_check_text_lines,
    z3_logic_check_text_lines,
)
from tep_runtime.topic_index import (  # noqa: E402
    build_lexical_topic_index,
    infer_topic_terms_from_refs,
    load_topic_records,
    task_terms,
    topic_conflict_candidates,
    topic_search_matches,
    topic_tokenize,
    write_topic_index_reports,
)
from tep_runtime.models import build_model_payload, promote_model_to_domain_payloads  # noqa: E402
from tep_runtime.open_questions import build_open_question_payload  # noqa: E402
from tep_runtime.projects import assign_project_payload, build_project_payload  # noqa: E402
from tep_runtime.workspaces import assign_workspace_payload, build_workspace_payload  # noqa: E402
from tep_runtime.tasks import (  # noqa: E402
    assign_task_payload,
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
    task_related_counts,
    task_summary_line,
)
from tep_runtime.working_contexts import (  # noqa: E402
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
from tep_runtime.paths import (  # noqa: E402
    code_index_entry_path,
    code_index_entries_root,
    hydration_state_path,
    hypotheses_index_path,
    record_path,
    runtime_dir,
    settings_path,
)
from tep_runtime.policy import is_mutating_action_kind, validate_runtime_policy  # noqa: E402
from tep_runtime.proposals import build_proposal_payload, parse_proposal_option, proposal_summary_line  # noqa: E402
from tep_runtime.records import RECORD_DIRS, load_code_index_entries, load_records  # noqa: E402
from tep_runtime.reports import rel_display, write_report, write_validation_report  # noqa: E402
from tep_runtime.reasoning import (  # noqa: E402
    augment_evidence_chain_payload,
    augmented_evidence_chain_text_lines,
    evidence_chain_report_lines,
    validate_chain_node,
    validate_evidence_chain_payload,
)
from tep_runtime.reasoning_case import build_reasoning_case_payload, reasoning_case_text_lines  # noqa: E402
from tep_runtime.backends import backend_status_payload, backend_status_text_lines, select_backend_status  # noqa: E402
from tep_runtime.retrieval import (  # noqa: E402
    active_guidelines_for,
    active_permissions_for,
    select_fallback_claims,
    select_records,
)
from tep_runtime.settings import (  # noqa: E402
    is_strictness_escalation,
    load_effective_settings,
    load_settings,
    load_strictness_requests,
    next_strictness_request_id,
    normalize_backend_settings,
    normalize_settings_payload,
    permission_allows_strictness,
    strictness_request_allows_change,
    strictness_requests_path,
    validate_settings_state,
    write_settings,
    write_strictness_requests,
)
from tep_runtime.validation import (  # noqa: E402
    ensure_dict,
    ensure_list,
    ensure_string_list,
    safe_list,
    validate_optional_confidence,
    validate_optional_red_flags,
)


def test_paths_are_importable_core_services_and_context_lib_facade_reuses_them(tmp_path: Path) -> None:
    root = tmp_path / ".codex_context"

    assert settings_path(root) == root / "settings.json"
    assert runtime_dir(root) == root / "runtime"
    assert hydration_state_path(root) == root / "runtime" / "hydration.json"
    assert hypotheses_index_path(root) == root / "hypotheses.jsonl"
    assert record_path(root, "claim", "CLM-20260418-abcdef12") == (
        root / "records" / "claim" / "CLM-20260418-abcdef12.json"
    )
    assert code_index_entries_root(root) == root / "code_index" / "entries"
    assert code_index_entry_path(root, "CIX-20260418-abcdef12") == (
        root / "code_index" / "entries" / "CIX-20260418-abcdef12.json"
    )
    assert compat_record_path is record_path
    assert compat_hydration_state_path is hydration_state_path
    assert compat_write_json_file is write_json_file
    assert compat_compute_context_fingerprint is compute_context_fingerprint
    assert compat_resolve_context_root is resolve_context_root
    assert compat_build_context_brief_payload is build_context_brief_payload
    assert compat_context_brief_text_lines is context_brief_text_lines
    assert compat_guideline_detail_lines is guideline_detail_lines
    assert compat_project_detail_lines is project_detail_lines
    assert compat_restriction_detail_lines is restriction_detail_lines
    assert compat_task_detail_lines is task_detail_lines
    assert compat_load_hydration_state is load_hydration_state
    assert compat_write_hydration_state is write_hydration_state
    assert compat_invalidate_hydration_state is invalidate_hydration_state
    assert compat_strictness_requests_path is strictness_requests_path
    assert compat_load_strictness_requests is load_strictness_requests
    assert compat_write_strictness_requests is write_strictness_requests
    assert compat_next_strictness_request_id is next_strictness_request_id
    assert compat_is_strictness_escalation is is_strictness_escalation
    assert compat_permission_allows_strictness is permission_allows_strictness
    assert compat_strictness_request_allows_change is strictness_request_allows_change
    assert compat_validate_settings_state is validate_settings_state
    assert compat_build_claim_lifecycle_history_entry is build_claim_lifecycle_history_entry
    assert compat_build_claim_payload is build_claim_payload
    assert compat_claim_line is claim_line
    assert compat_build_permission_payload is build_permission_payload
    assert compat_guideline_summary_line is guideline_summary_line
    assert compat_resolve_permission_scope is resolve_permission_scope
    assert compat_normalize_quote is normalize_quote
    assert compat_join_quote_items is join_quote_items
    assert compat_quote_matches_record is quote_matches_record
    assert compat_claim_attention is claim_attention
    assert compat_claim_blocks_current_action is claim_blocks_current_action
    assert compat_claim_retrieval_tier is claim_retrieval_tier
    assert compat_mutate_claim_lifecycle_payload is mutate_claim_lifecycle_payload
    assert compat_cleanup_candidate_items is cleanup_candidate_items
    assert compat_cleanup_archive_apply_payload is cleanup_archive_apply_payload
    assert compat_cleanup_archive_plan_payload is cleanup_archive_plan_payload
    assert compat_cleanup_archive_plan_text_lines is cleanup_archive_plan_text_lines
    assert compat_cleanup_archives_payload is cleanup_archives_payload
    assert compat_cleanup_archives_text_lines is cleanup_archives_text_lines
    assert compat_cleanup_restore_apply_payload is cleanup_restore_apply_payload
    assert compat_cleanup_restore_plan_payload is cleanup_restore_plan_payload
    assert compat_cleanup_restore_plan_text_lines is cleanup_restore_plan_text_lines
    assert compat_parse_timestamp is parse_timestamp
    assert compat_dependency_refs_for_record is dependency_refs_for_record
    assert compat_collect_link_edges is collect_link_edges
    assert compat_linked_records_payload is linked_records_payload
    assert compat_ref_paths is ref_paths
    assert compat_current_project_ref is current_project_ref
    assert compat_current_task_ref is current_task_ref
    assert compat_current_workspace_ref is current_workspace_ref
    assert compat_active_restrictions_for is active_restrictions_for
    assert compat_project_refs_for_write is project_refs_for_write
    assert compat_workspace_refs_for_write is workspace_refs_for_write
    assert compat_task_refs_for_write is task_refs_for_write
    assert compat_record_belongs_to_project is record_belongs_to_project
    assert compat_record_belongs_to_task is record_belongs_to_task
    assert compat_permission_applies is permission_applies
    assert compat_guideline_applies is guideline_applies
    assert compat_concise is concise
    assert compat_record_search_text is record_search_text
    assert compat_record_search_timestamp is record_search_timestamp
    assert compat_search_record_matches is search_record_matches
    assert compat_ranked_record_search is ranked_record_search
    assert compat_score_record is score_record
    assert compat_record_summary is record_summary
    assert compat_public_record_summary is public_record_summary
    assert compat_record_detail_payload is record_detail_payload
    assert compat_record_detail_text_lines is record_detail_text_lines
    assert compat_validate_chain_node is validate_chain_node
    assert compat_build_reasoning_case_payload is build_reasoning_case_payload
    assert compat_augment_evidence_chain_payload is augment_evidence_chain_payload
    assert compat_augmented_evidence_chain_text_lines is augmented_evidence_chain_text_lines
    assert compat_evidence_chain_report_lines is evidence_chain_report_lines
    assert compat_reasoning_case_text_lines is reasoning_case_text_lines
    assert compat_validate_evidence_chain_payload is validate_evidence_chain_payload
    assert compat_select_records is select_records
    assert compat_select_fallback_claims is select_fallback_claims
    assert compat_stale_knowledge_target_ids is stale_knowledge_target_ids
    assert compat_active_permissions_for is active_permissions_for
    assert compat_active_guidelines_for is active_guidelines_for
    assert compat_build_hypothesis_entry is build_hypothesis_entry
    assert compat_close_hypothesis_entries is close_hypothesis_entries
    assert compat_load_hypotheses_index is load_hypotheses_index
    assert compat_hypothesis_active_entry_exists is hypothesis_active_entry_exists
    assert compat_write_hypotheses_index is write_hypotheses_index
    assert compat_remove_hypothesis_entries is remove_hypothesis_entries
    assert compat_reopen_hypothesis_entry is reopen_hypothesis_entry
    assert compat_sync_hypothesis_entries is sync_hypothesis_entries
    assert compat_validate_hypothesis_claim is validate_hypothesis_claim
    assert compat_validate_hypotheses_index is validate_hypotheses_index
    assert compat_collect_claim_refs_from_models_flows is collect_claim_refs_from_models_flows
    assert compat_active_hypotheses_for is active_hypotheses_for
    assert compat_active_hypothesis_entry_by_claim is active_hypothesis_entry_by_claim
    assert compat_is_mutating_action_kind is is_mutating_action_kind
    assert compat_mark_knowledge_records_stale_payloads is mark_knowledge_records_stale_payloads
    assert compat_validate_runtime_policy is validate_runtime_policy
    assert compat_parse_proposal_option is parse_proposal_option
    assert compat_proposal_summary_line is proposal_summary_line
    assert compat_rel_display is rel_display
    assert compat_write_report is write_report
    assert compat_write_validation_report is write_validation_report
    assert compat_ensure_list is ensure_list
    assert compat_ensure_dict is ensure_dict
    assert compat_ensure_string_list is ensure_string_list
    assert compat_safe_list is safe_list
    assert compat_validate_optional_confidence is validate_optional_confidence
    assert compat_validate_optional_red_flags is validate_optional_red_flags
    assert compat_CODE_INDEX_TARGET_KINDS is CODE_INDEX_TARGET_KINDS
    assert compat_CODE_SMELL_CATEGORIES is CODE_SMELL_CATEGORIES
    assert compat_analyze_code_file is analyze_code_file
    assert compat_analyze_markdown is analyze_markdown
    assert compat_annotation_snapshot is annotation_snapshot
    assert compat_build_manual_code_index_entry is build_manual_code_index_entry
    assert compat_code_entries_text_lines is code_entries_text_lines
    assert compat_code_index_entry_for_file is code_index_entry_for_file
    assert compat_code_smell_report_payload is code_smell_report_payload
    assert compat_code_smell_report_text_lines is code_smell_report_text_lines
    assert compat_code_smell_rows is code_smell_rows
    assert compat_normalize_smell_categories is normalize_smell_categories
    assert compat_parse_code_fields is parse_code_fields
    assert compat_project_code_entry is project_code_entry
    assert compat_public_code_index_entry is public_code_index_entry
    assert compat_resolve_code_entry is resolve_code_entry
    assert compat_write_code_index_views is write_code_index_views
    assert compat_validate_code_index_entry is validate_code_index_entry
    assert compat_validate_code_index_state is validate_code_index_state
    assert compat_CLAIM_COMPARATORS is CLAIM_COMPARATORS
    assert compat_CLAIM_POLARITIES is CLAIM_POLARITIES
    assert compat_build_comparison_payload is build_comparison_payload
    assert compat_collect_conflict_lines is collect_conflict_lines
    assert compat_comparison_signature is comparison_signature
    assert compat_validate_claim_comparison is validate_claim_comparison
    assert compat_write_conflicts_report is write_conflicts_report
    assert compat_SOURCE_KINDS is SOURCE_KINDS
    assert compat_collect_validation_errors is collect_validation_errors
    assert compat_validate_candidate_record is validate_candidate_record
    assert compat_validate_record is validate_record
    assert compat_validate_records_state is validate_records_state
    assert compat_validate_refs is validate_refs
    assert compat_build_action_payload is build_action_payload
    assert compat_build_source_payload is build_source_payload
    assert compat_source_line is source_line
    assert compat_default_independence_group is default_independence_group
    assert compat_build_index is build_index
    assert compat_collect_dependency_impact is collect_dependency_impact
    assert compat_fallback_claims is fallback_claims
    assert compat_record_attention_label is record_attention_label
    assert compat_write_attention_report is write_attention_report
    assert compat_write_backlog is write_backlog
    assert compat_build_flow_oracle is build_flow_oracle
    assert compat_build_flow_payload is build_flow_payload
    assert compat_build_flow_preconditions is build_flow_preconditions
    assert compat_build_flow_step is build_flow_step
    assert compat_promote_flow_to_domain_payloads is promote_flow_to_domain_payloads
    assert compat_build_guideline_payload is build_guideline_payload
    assert compat_resolve_guideline_scope is resolve_guideline_scope
    assert compat_build_debt_payload is build_debt_payload
    assert compat_build_plan_payload is build_plan_payload
    assert compat_build_model_payload is build_model_payload
    assert compat_promote_model_to_domain_payloads is promote_model_to_domain_payloads
    assert compat_build_open_question_payload is build_open_question_payload
    assert compat_assign_project_payload is assign_project_payload
    assert compat_build_project_payload is build_project_payload
    assert compat_project_summary_line is project_summary_line
    assert compat_build_proposal_payload is build_proposal_payload
    assert compat_assign_task_payload is assign_task_payload
    assert compat_build_precedent_review_payload is build_precedent_review_payload
    assert compat_build_task_drift_payload is build_task_drift_payload
    assert compat_build_task_payload is build_task_payload
    assert compat_finish_task_payload is finish_task_payload
    assert compat_pause_task_for_switch_payload is pause_task_for_switch_payload
    assert compat_precedent_review_text_lines is precedent_review_text_lines
    assert compat_resume_task_payload is resume_task_payload
    assert compat_select_precedent_tasks is select_precedent_tasks
    assert compat_task_drift_text_lines is task_drift_text_lines
    assert compat_task_identity_text is task_identity_text
    assert compat_task_related_counts is task_related_counts
    assert compat_task_summary_line is task_summary_line
    assert compat_add_remove_values is add_remove_values
    assert compat_build_working_context_payload is build_working_context_payload
    assert compat_close_working_context_payload is close_working_context_payload
    assert compat_fork_working_context_payload is fork_working_context_payload
    assert compat_parse_working_context_assumption is parse_working_context_assumption
    assert compat_parse_working_context_assumptions is parse_working_context_assumptions
    assert compat_working_context_detail_lines is working_context_detail_lines
    assert compat_working_context_show_payload is working_context_show_payload
    assert compat_working_context_summary_line is working_context_summary_line
    assert compat_build_restriction_payload is build_restriction_payload
    assert compat_restriction_summary_line is restriction_summary_line
    assert compat_resolve_restriction_scope is resolve_restriction_scope
    assert compat_build_impact_graph_payload is build_impact_graph_payload
    assert compat_build_rollback_report_payload is build_rollback_report_payload
    assert compat_impact_graph_text_lines is impact_graph_text_lines
    assert compat_rollback_report_text_lines is rollback_report_text_lines
    assert compat_write_models_report is write_models_report
    assert compat_write_resolved_report is write_resolved_report
    assert compat_LOGIC_SYMBOL_PATTERN is LOGIC_SYMBOL_PATTERN
    assert compat_parse_bool_token is parse_bool_token
    assert compat_parse_scalar_token is parse_scalar_token
    assert compat_parse_logic_context is parse_logic_context
    assert compat_parse_logic_atom_spec is parse_logic_atom_spec
    assert compat_parse_logic_symbol_spec is parse_logic_symbol_spec
    assert compat_parse_logic_atom_expression is parse_logic_atom_expression
    assert compat_parse_logic_rule_spec is parse_logic_rule_spec
    assert compat_load_logic_json_payload is load_logic_json_payload
    assert compat_build_logic_payload is build_logic_payload
    assert compat_logic_atom_symbols is logic_atom_symbols
    assert compat_logic_atom_variables is logic_atom_variables
    assert compat_validate_claim_logic is validate_claim_logic
    assert compat_validate_logic_state is validate_logic_state
    assert compat_build_logic_index_payload is build_logic_index_payload
    assert compat_build_logic_vocabulary_graph is build_logic_vocabulary_graph
    assert compat_load_logic_index_payload is load_logic_index_payload
    assert compat_load_logic_vocabulary_graph is load_logic_vocabulary_graph
    assert compat_logic_conflict_candidates_from_payload is logic_conflict_candidates_from_payload
    assert compat_logic_rule_variables is logic_rule_variables
    assert compat_effective_logic_solver is effective_logic_solver
    assert compat_logic_solver_settings is logic_solver_settings
    assert compat_structural_logic_check_payload is structural_logic_check_payload
    assert compat_structural_logic_check_text_lines is structural_logic_check_text_lines
    assert compat_write_logic_index_reports is write_logic_index_reports
    assert compat_z3_logic_check_text_lines is z3_logic_check_text_lines
    assert compat_build_lexical_topic_index is build_lexical_topic_index
    assert compat_infer_topic_terms_from_refs is infer_topic_terms_from_refs
    assert compat_load_topic_records is load_topic_records
    assert compat_task_terms is task_terms
    assert compat_topic_conflict_candidates is topic_conflict_candidates
    assert compat_topic_search_matches is topic_search_matches
    assert compat_topic_tokenize is topic_tokenize
    assert compat_write_topic_index_reports is write_topic_index_reports


def test_display_core_renders_public_record_lines() -> None:
    project = {
        "id": "PRJ-20260418-aaaa1111",
        "status": "active",
        "project_key": "tep",
        "title": "Trust Evidence Protocol",
    }
    assert project_summary_line(project) == (
        '`PRJ-20260418-aaaa1111` status=`active` key=`tep` title="Trust Evidence Protocol"'
    )
    assert project_detail_lines({**project, "root_refs": ["plugins/trust-evidence-protocol"]}) == [
        '- `PRJ-20260418-aaaa1111` status=`active` key=`tep` title="Trust Evidence Protocol"',
        "  root_refs: ['plugins/trust-evidence-protocol']",
    ]

    guideline = {
        "id": "GLD-20260418-bbbb2222",
        "status": "active",
        "domain": "code",
        "applies_to": "project",
        "priority": "high",
        "rule": "Keep runtime helpers deterministic and covered by direct tests.",
    }
    assert guideline_summary_line(guideline) == (
        '`GLD-20260418-bbbb2222` status=`active` domain=`code` applies_to=`project` '
        'priority=`high` rule="Keep runtime helpers deterministic and covered by direct tests."'
    )
    assert guideline_detail_lines(
        {
            **guideline,
            "rationale": "Avoid hidden behavior drift.",
            "examples": ["Use pure render helpers."],
            "project_refs": ["PRJ-20260418-aaaa1111"],
            "task_refs": ["TASK-20260418-dddd4444"],
            "source_refs": ["SRC-20260418-eeee5555"],
            "related_claim_refs": ["CLM-20260418-ffff6666"],
        }
    ) == [
        '- `GLD-20260418-bbbb2222` status=`active` domain=`code` applies_to=`project` priority=`high` rule="Keep runtime helpers deterministic and covered by direct tests."',
        "  rationale: Avoid hidden behavior drift.",
        "  examples: ['Use pure render helpers.']",
        "  project_refs: ['PRJ-20260418-aaaa1111']",
        "  task_refs: ['TASK-20260418-dddd4444']",
        "  source_refs: ['SRC-20260418-eeee5555']",
        "  related_claim_refs: ['CLM-20260418-ffff6666']",
    ]

    restriction = {
        "id": "RST-20260418-cccc3333",
        "status": "active",
        "applies_to": "task",
        "severity": "high",
        "title": "No hidden behavior changes",
    }
    assert restriction_summary_line(restriction) == (
        '`RST-20260418-cccc3333` status=`active` applies_to=`task` severity=`high` '
        'title="No hidden behavior changes"'
    )
    assert restriction_detail_lines(
        {
            **restriction,
            "rules": ["Keep CLI output stable."],
            "project_refs": ["PRJ-20260418-aaaa1111"],
            "task_refs": ["TASK-20260418-dddd4444"],
            "related_claim_refs": ["CLM-20260418-ffff6666"],
        }
    ) == [
        '- `RST-20260418-cccc3333` status=`active` applies_to=`task` severity=`high` title="No hidden behavior changes"',
        "  rules: ['Keep CLI output stable.']",
        "  project_refs: ['PRJ-20260418-aaaa1111']",
        "  task_refs: ['TASK-20260418-dddd4444']",
        "  related_claim_refs: ['CLM-20260418-ffff6666']",
    ]

    claim = {
        "id": "CLM-20260418-dddd4444",
        "record_type": "claim",
        "status": "supported",
        "plane": "code",
        "confidence": "high",
        "statement": "Display helpers are pure text renderers.",
    }
    assert claim_line(claim) == (
        "- `CLM-20260418-dddd4444` status=`supported` plane=`code` confidence=high: "
        "Display helpers are pure text renderers."
    )
    fallback_claim = {
        **claim,
        "lifecycle": {"state": "resolved", "attention": "fallback-only"},
    }
    assert "lifecycle=`resolved` attention=`fallback-only`" in claim_line(fallback_claim)

    source = {
        "id": "SRC-20260418-eeee5555",
        "source_kind": "runtime",
        "critique_status": "accepted",
        "quote": "89 passed",
    }
    assert source_line(source) == (
        "  - `SRC-20260418-eeee5555` kind=`runtime` critique=`accepted` quote=`89 passed`"
    )
    artifact_source = {
        "id": "SRC-20260418-ffff6666",
        "source_kind": "runtime",
        "critique_status": "accepted",
        "artifact_refs": ["ART-20260418-aaaa1111"],
    }
    assert source_line(artifact_source).endswith("quote=`ART-20260418-aaaa1111`")


def test_context_brief_core_builds_payload_and_text(tmp_path: Path) -> None:
    root = tmp_path / ".codex_context"
    workspace_id = "WSP-20260418-work1111"
    project_id = "PRJ-20260418-project1"
    task_id = "TASK-20260418-task111"
    source_id = "SRC-20260418-source11"
    claim_id = "CLM-20260418-claim111"
    fallback_id = "CLM-20260418-claim222"
    fallback_search_id = "CLM-20260418-claim223"
    hypothesis_id = "CLM-20260418-claim333"
    archived_id = "CLM-20260418-claim444"
    model_id = "MODEL-20260418-model111"
    flow_id = "FLOW-20260418-flow111"
    open_id = "OPEN-20260418-open111"
    permission_id = "PRM-20260418-perm111"
    guideline_id = "GLD-20260418-guide111"
    restriction_id = "RST-20260418-rest111"
    proposal_id = "PRP-20260418-prop111"
    plan_id = "PLN-20260418-plan111"
    debt_id = "DEBT-20260418-debt111"
    records = {
        workspace_id: {
            "id": workspace_id,
            "record_type": "workspace",
            "scope": "qa-tim",
            "status": "active",
            "workspace_key": "qa-tim",
            "title": "QA TIM Workspace",
            "context_root": str(root),
            "root_refs": ["ROOT-1", "ROOT-2"],
            "project_refs": [project_id],
        },
        project_id: {
            "id": project_id,
            "record_type": "project",
            "status": "active",
            "project_key": "tep",
            "title": "TEP Project",
            "root_refs": ["ROOT-1"],
        },
        task_id: {
            "id": task_id,
            "record_type": "task",
            "status": "active",
            "scope": "tep-runtime",
            "title": "Extract context brief",
            "description": "Move brief-context logic.",
            "task_type": "coding",
            "related_claim_refs": [claim_id],
            "project_refs": [project_id],
        },
        source_id: {
            "id": source_id,
            "record_type": "source",
            "source_kind": "runtime",
            "critique_status": "accepted",
            "quote": "context brief tests pass",
            "project_refs": [project_id],
        },
        claim_id: {
            "id": claim_id,
            "record_type": "claim",
            "status": "supported",
            "plane": "code",
            "statement": "Context brief selection can be deterministic.",
            "source_refs": [source_id],
            "project_refs": [project_id],
        },
        fallback_id: {
            "id": fallback_id,
            "record_type": "claim",
            "status": "supported",
            "plane": "code",
            "statement": "Old context brief behavior is fallback history.",
            "source_refs": [source_id],
            "lifecycle": {"state": "resolved", "attention": "fallback-only"},
            "project_refs": [project_id],
        },
        fallback_search_id: {
            "id": fallback_search_id,
            "record_type": "claim",
            "status": "supported",
            "plane": "code",
            "statement": "Context brief search can append fallback history.",
            "source_refs": [source_id],
            "lifecycle": {"state": "resolved", "attention": "fallback-only"},
            "project_refs": [project_id],
        },
        hypothesis_id: {
            "id": hypothesis_id,
            "record_type": "claim",
            "status": "tentative",
            "plane": "theory",
            "statement": "Context brief can surface active hypotheses.",
            "source_refs": [source_id],
            "project_refs": [project_id],
        },
        archived_id: {
            "id": archived_id,
            "record_type": "claim",
            "status": "supported",
            "plane": "code",
            "statement": "Archived claims should not dominate fallback facts.",
            "source_refs": [source_id],
            "lifecycle": {"state": "archived", "attention": "explicit-only"},
            "project_refs": [project_id],
        },
        model_id: {
            "id": model_id,
            "record_type": "model",
            "status": "working",
            "domain": "tep",
            "scope": "tep-runtime",
            "aspect": "brief",
            "is_primary": True,
            "summary": "Context brief extraction model.",
            "claim_refs": [claim_id, hypothesis_id, fallback_id, archived_id],
            "project_refs": [project_id],
        },
        flow_id: {
            "id": flow_id,
            "record_type": "flow",
            "status": "working",
            "domain": "tep",
            "scope": "tep-runtime",
            "is_primary": True,
            "summary": "Context brief extraction flow.",
            "steps": [{"claim_refs": [claim_id]}],
            "project_refs": [project_id],
        },
        open_id: {
            "id": open_id,
            "record_type": "open_question",
            "status": "open",
            "question": "Should brief rendering stay stable?",
            "project_refs": [project_id],
        },
        permission_id: {
            "id": permission_id,
            "record_type": "permission",
            "status": "active",
            "applies_to": "project",
            "scope": "tep-runtime",
            "granted_by": "user",
            "grants": ["refactor"],
            "project_refs": [project_id],
        },
        guideline_id: {
            "id": guideline_id,
            "record_type": "guideline",
            "status": "active",
            "domain": "code",
            "applies_to": "project",
            "priority": "required",
            "rule": "Keep context brief output stable.",
            "rationale": "MCP delegates to the CLI command.",
            "examples": ["brief-context"],
            "project_refs": [project_id],
            "source_refs": [source_id],
            "related_claim_refs": [claim_id],
        },
        restriction_id: {
            "id": restriction_id,
            "record_type": "restriction",
            "status": "active",
            "applies_to": "project",
            "severity": "high",
            "title": "No context brief drift",
            "rules": ["preserve section names"],
            "project_refs": [project_id],
            "related_claim_refs": [claim_id],
        },
        proposal_id: {
            "id": proposal_id,
            "record_type": "proposal",
            "status": "active",
            "subject": "Context brief extraction",
            "position": "Move selection and rendering into runtime.",
            "confidence": "high",
            "project_refs": [project_id],
            "assumptions": ["CLI keeps output shape"],
        },
        plan_id: {
            "id": plan_id,
            "record_type": "plan",
            "status": "active",
            "priority": "high",
            "title": "Extract context brief helper",
            "project_refs": [project_id],
        },
        debt_id: {
            "id": debt_id,
            "record_type": "debt",
            "status": "open",
            "priority": "medium",
            "title": "Context CLI still has other handlers",
            "project_refs": [project_id],
        },
    }
    write_hypotheses_index(
        root,
        [
            {
                "claim_ref": hypothesis_id,
                "status": "active",
                "scope": "tep-runtime",
                "mode": "bounded",
                "note": "active context brief hypothesis",
            }
        ],
    )
    payload = build_context_brief_payload(
        records,
        root,
        "context brief extraction flow",
        task_id,
        workspace_id,
        project_id,
        8,
    )
    assert payload["current_workspace"]["id"] == workspace_id
    assert payload["current_project"]["id"] == project_id
    assert payload["current_task"]["id"] == task_id
    assert [item["id"] for item in payload["models"]] == [model_id]
    assert [item["id"] for item in payload["flows"]] == [flow_id]
    assert [item["id"] for item in payload["active_facts"]] == [claim_id, hypothesis_id]
    assert [item["id"] for item in payload["fallback_facts"]] == [fallback_id, fallback_search_id]
    assert [item["claim_ref"] for item in payload["hypotheses"]] == [hypothesis_id]
    assert [item["id"] for item in payload["permissions"]] == [permission_id]
    assert [item["id"] for item in payload["guidelines"]] == [guideline_id]
    assert [item["id"] for item in payload["restrictions"]] == [restriction_id]
    assert [item["id"] for item in payload["proposals"]] == [proposal_id]
    assert [item["id"] for item in payload["plans"]] == [plan_id]
    assert [item["id"] for item in payload["debts"]] == [debt_id]

    compact_lines = context_brief_text_lines(payload, "TEP")
    compact_text = "\n".join(compact_lines)
    assert compact_lines[0] == "# TEP Context Brief (compact)"
    assert f"- workspace: `{workspace_id}` key=`qa-tim` status=`active`" in compact_lines
    assert f"- project: `{project_id}` key=`tep` status=`active`" in compact_lines
    assert f"- task: `{task_id}` type=`coding` scope=`tep-runtime` status=`active`" in compact_lines
    assert claim_id in compact_text
    assert guideline_id in compact_text
    assert "Use `record_detail`, `linked_records`, or `brief-context --detail full`" in compact_text
    assert len(compact_text) < 2200

    lines = context_brief_text_lines(payload, "TEP", detail="full")
    assert lines[:6] == [
        "# TEP Context Brief",
        "",
        "## Current Workspace",
        '- `WSP-20260418-work1111` status=`active` key=`qa-tim` title="QA TIM Workspace"',
        f"  context_root: {root}",
        "  root_refs: ['ROOT-1', 'ROOT-2']",
    ]
    assert lines[6:10] == [
        "  project_refs: ['PRJ-20260418-project1']",
        "",
        "## Current Project",
        '- `PRJ-20260418-project1` status=`active` key=`tep` title="TEP Project"',
    ]
    assert "Project filter: `PRJ-20260418-project1`. Unassigned records are excluded from relevance sections." in lines
    assert any(line.startswith("- `MODEL-20260418-model111` status=`working` domain=`tep`") for line in lines)
    assert any(line.startswith("- `FLOW-20260418-flow111` status=`working` domain=`tep`") for line in lines)
    assert any(line.startswith("- `CLM-20260418-claim111` status=`supported` plane=`code`") for line in lines)
    assert any("lifecycle=`resolved` attention=`fallback-only`" in line for line in lines)
    assert f"- `{hypothesis_id}` scope=`tep-runtime`: Context brief can surface active hypotheses." in lines
    assert f"- `{open_id}` status=`open`: Should brief rendering stay stable?" in lines
    assert any(line.startswith(f"- `{permission_id}` applies_to=`project`") for line in lines)
    assert any(line.startswith(f"- `{guideline_id}` status=`active`") for line in lines)
    assert "  rationale: MCP delegates to the CLI command." in lines
    assert "  examples: ['brief-context']" in lines
    assert any(line.startswith(f"- `{restriction_id}` status=`active`") for line in lines)
    assert "  rules: ['preserve section names']" in lines
    assert any(line.startswith(f"- `{proposal_id}` status=`active`") for line in lines)
    assert f"- `{plan_id}` status=`active` priority=`high`: Extract context brief helper" in lines
    assert f"- `{debt_id}` status=`open` priority=`medium`: Context CLI still has other handlers" in lines
    assert lines[-1] == "- If the brief has facts but no model/flow for the scope, update the context after the next supported observation."

    empty_payload = build_context_brief_payload({}, root, "unknown brief", "", "", "", 3)
    empty_lines = context_brief_text_lines(empty_payload, "TEP", detail="full")
    assert "- none found; gather sources before making decisive claims" in empty_lines
    assert "- none; create `PRP-*` when the agent has a constructive alternative or critique" in empty_lines


def test_next_step_core_exposes_compact_action_graph(tmp_path: Path) -> None:
    root = tmp_path / ".tep_context"
    workspace_id = "WSP-20260418-11111111"
    project_id = "PRJ-20260418-22222222"
    task_id = "TASK-20260418-33333333"
    write_json_file(
        root / "records" / "workspace" / f"{workspace_id}.json",
        {
            "id": workspace_id,
            "record_type": "workspace",
            "status": "active",
            "workspace_key": "tep-workspace",
            "title": "TEP Workspace",
        },
    )
    write_json_file(
        root / "records" / "project" / f"{project_id}.json",
        {
            "id": project_id,
            "record_type": "project",
            "status": "active",
            "project_key": "tep",
            "title": "TEP Project",
            "workspace_refs": [workspace_id],
        },
    )
    write_json_file(
        root / "records" / "task" / f"{task_id}.json",
        {
            "id": task_id,
            "record_type": "task",
            "status": "active",
            "scope": "tep-core",
            "title": "Improve action graph",
            "project_refs": [project_id],
        },
    )
    write_settings(
        root,
        allowed_freedom="proof-only",
        current_workspace_ref=workspace_id,
        current_project_ref=project_id,
        current_task_ref=task_id,
    )
    write_hydration_state(root, {"status": "hydrated", "fingerprint": compute_context_fingerprint(root)})
    records, _ = load_records(root)

    payload = build_next_step_payload(records, root, intent="edit", task="change action graph")

    assert payload["hydration_fresh"] is True
    assert payload["route_graph"]["graph_version"] == 1
    assert {"if": "proof gap", "then": "build/validate evidence chain"} in payload["route_graph"]["branches"]
    assert "missing source-backed proof for truth claim" in payload["route_graph"]["stop_conditions"]
    compact_lines = next_step_text_lines(payload, "TEP", detail="compact")
    assert any(line.startswith("- graph: ") for line in compact_lines)
    assert any("proof gap=>build/validate evidence chain" in line for line in compact_lines)
    assert "missing source-backed proof for truth claim" not in "\n".join(compact_lines)
    full_lines = next_step_text_lines(payload, "TEP", detail="full")
    assert any(line.startswith("- stop: ") for line in full_lines)
    inline = next_step_inline(payload)
    assert "next=guidelines-for" in inline
    assert "graph=guidelines missing=>guidelines-for" in inline


def test_reasoning_case_core_builds_payload_and_text() -> None:
    project_id = "PRJ-20260418-project1"
    task_id = "TASK-20260418-task111"
    source_id = "SRC-20260418-source11"
    claim_id = "CLM-20260418-claim111"
    tentative_id = "CLM-20260418-claim222"
    fallback_id = "CLM-20260418-claim333"
    model_id = "MODEL-20260418-model111"
    flow_id = "FLOW-20260418-flow111"
    open_id = "OPEN-20260418-open111"
    permission_id = "PRM-20260418-perm111"
    guideline_id = "GLD-20260418-guide111"
    restriction_id = "RST-20260418-rest111"
    records = {
        project_id: {
            "id": project_id,
            "record_type": "project",
            "status": "active",
            "project_key": "tep",
            "title": "TEP Project",
        },
        task_id: {
            "id": task_id,
            "record_type": "task",
            "status": "active",
            "scope": "tep-runtime",
            "title": "Extract reasoning case",
            "task_type": "coding",
            "project_refs": [project_id],
        },
        source_id: {
            "id": source_id,
            "record_type": "source",
            "source_kind": "runtime",
            "critique_status": "accepted",
            "quote": "reasoning case command still passes",
            "project_refs": [project_id],
        },
        claim_id: {
            "id": claim_id,
            "record_type": "claim",
            "status": "supported",
            "plane": "runtime",
            "statement": "Reasoning case output includes supported runtime facts.",
            "source_refs": [source_id],
            "project_refs": [project_id],
        },
        tentative_id: {
            "id": tentative_id,
            "record_type": "claim",
            "status": "tentative",
            "plane": "code",
            "statement": "Reasoning case extraction may still need one missing source.",
            "source_refs": [],
            "project_refs": [project_id],
        },
        fallback_id: {
            "id": fallback_id,
            "record_type": "claim",
            "status": "supported",
            "plane": "code",
            "statement": "Old reasoning case helper was true historically.",
            "source_refs": [source_id],
            "lifecycle": {"state": "resolved", "attention": "fallback-only"},
            "project_refs": [project_id],
        },
        model_id: {
            "id": model_id,
            "record_type": "model",
            "status": "working",
            "scope": "tep-runtime",
            "summary": "Reasoning case model.",
            "claim_refs": [claim_id, tentative_id],
            "open_question_refs": [open_id],
            "project_refs": [project_id],
        },
        flow_id: {
            "id": flow_id,
            "record_type": "flow",
            "status": "contested",
            "scope": "tep-runtime",
            "summary": "Reasoning case flow.",
            "steps": [{"claim_refs": [fallback_id], "open_question_refs": [open_id]}],
            "project_refs": [project_id],
        },
        open_id: {
            "id": open_id,
            "record_type": "open_question",
            "status": "open",
            "question": "Should reasoning case rendering move out of CLI?",
            "project_refs": [project_id],
        },
        permission_id: {
            "id": permission_id,
            "record_type": "permission",
            "status": "active",
            "applies_to": "project",
            "scope": "tep-runtime",
            "grants": ["refactor"],
            "project_refs": [project_id],
        },
        guideline_id: {
            "id": guideline_id,
            "record_type": "guideline",
            "status": "active",
            "domain": "code",
            "applies_to": "project",
            "priority": "required",
            "rule": "Keep reasoning case behavior deterministic.",
            "project_refs": [project_id],
        },
        restriction_id: {
            "id": restriction_id,
            "record_type": "restriction",
            "status": "active",
            "applies_to": "project",
            "severity": "high",
            "title": "No behavior drift",
            "rules": ["preserve CLI text shape"],
            "project_refs": [project_id],
        },
    }
    payload = build_reasoning_case_payload(
        records,
        "extract reasoning case flow",
        [],
        [model_id],
        [flow_id],
        task_id,
        project_id,
        10,
    )
    assert payload["current_project"]["id"] == project_id
    assert payload["current_task"]["id"] == task_id
    assert [model["id"] for model in payload["models"]] == [model_id]
    assert [flow["id"] for flow in payload["flows"]] == [flow_id]
    assert [item["claim"]["id"] for item in payload["claim_items"]] == [claim_id, tentative_id, fallback_id]
    assert payload["unsupported"] == [tentative_id]
    assert payload["tentative"] == [tentative_id]
    assert payload["lifecycle_fallback"] == [fallback_id]
    assert payload["inactive_context"] == [flow_id]
    assert [item["ref"] for item in payload["open_questions"]] == [open_id]
    assert [item["id"] for item in payload["permissions"]] == [permission_id]
    assert [item["id"] for item in payload["guidelines"]] == [guideline_id]
    assert [item["id"] for item in payload["restrictions"]] == [restriction_id]

    lines = reasoning_case_text_lines(payload)
    assert lines[:6] == [
        "# Reasoning Case",
        "",
        'Current Project: `PRJ-20260418-project1` status=`active` key=`tep` title="TEP Project"',
        'Current Task: `TASK-20260418-task111` status=`active` type=`coding` scope=`tep-runtime` '
        'title="Extract reasoning case"',
        "Requested Task: extract reasoning case flow",
        "",
    ]
    assert any(line.startswith("- `MODEL-20260418-model111` status=`working`") for line in lines)
    assert any(line.startswith("- `FLOW-20260418-flow111` status=`contested`") for line in lines)
    assert any(line.startswith("- `CLM-20260418-claim111` status=`supported`") for line in lines)
    assert any(line.startswith("  - `SRC-20260418-source11` kind=`runtime`") for line in lines)
    assert f"- `{open_id}` status=`open`: Should reasoning case rendering move out of CLI?" in lines
    assert any(line.startswith(f"- `{permission_id}` applies_to=`project`") for line in lines)
    assert any(line.startswith(f"- `{guideline_id}` status=`active`") for line in lines)
    assert any(line.startswith(f"- `{restriction_id}` status=`active`") for line in lines)
    assert f"- WARNING: selected inactive model/flow records: {flow_id}" in lines
    assert f"- BLOCKER: unsupported or missing source refs in claims: {tentative_id}" in lines
    assert f"- WARNING: tentative claims used as hypotheses: {tentative_id}" in lines
    assert (
        "- WARNING: lifecycle fallback/archived claims are background or audit context only; "
        f"restore or re-support before decisive use: {fallback_id}"
    ) in lines
    assert lines[-1] == "- gather/record sources before acting"

    empty_payload = build_reasoning_case_payload({}, "debug setup pipeline", [], [], [], "", "", 5)
    empty_lines = reasoning_case_text_lines(empty_payload)
    assert "- WARNING: no model selected; if this reasoning spans multiple facts, create/update `MODEL-*`" in empty_lines
    assert "- WARNING: task looks flow-shaped but no `FLOW-*` was selected" in empty_lines
    assert empty_lines[-1] == "- action may proceed if strictness and permissions allow it; record `ACT-*` for durable changes"

    missing_source_id = "CLM-20260418-missing1"
    missing_source_payload = build_reasoning_case_payload(
        {
            missing_source_id: {
                "id": missing_source_id,
                "record_type": "claim",
                "status": "supported",
                "plane": "code",
                "statement": "Missing source refs are blockers.",
                "source_refs": ["SRC-20260418-missing1"],
            }
        },
        "missing source",
        [missing_source_id],
        [],
        [],
        "",
        "",
        5,
    )
    assert missing_source_payload["unsupported"] == [missing_source_id]

    tentative_only = reasoning_case_text_lines(
        {
            "task": "tentative only",
            "terms": set(),
            "models": [{"id": "MODEL-1"}],
            "flows": [{"id": "FLOW-1"}],
            "claim_items": [],
            "open_questions": [],
            "permissions": [],
            "guidelines": [],
            "restrictions": [],
            "unsupported": [],
            "tentative": ["CLM-1"],
            "lifecycle_fallback": [],
            "inactive_context": [],
        }
    )
    assert tentative_only[-1] == "- only safe/guarded exploratory action; do not promote conclusions without more support"

    fallback_only = reasoning_case_text_lines(
        {
            "task": "fallback only",
            "terms": set(),
            "models": [{"id": "MODEL-1"}],
            "flows": [{"id": "FLOW-1"}],
            "claim_items": [],
            "open_questions": [],
            "permissions": [],
            "guidelines": [],
            "restrictions": [],
            "unsupported": [],
            "tentative": [],
            "lifecycle_fallback": ["CLM-1"],
            "inactive_context": [],
        }
    )
    assert fallback_only[-1] == "- proceed only from active claims; restore or re-support fallback claims before using them as proof"


def test_policy_core_classifies_mutating_action_kinds() -> None:
    mutating = ["edit", "write-file", "create_task", "delete", "remove", "rename", "move", "refactor", "patch", "update", "modify"]
    for kind in mutating:
        assert is_mutating_action_kind(kind)

    assert not is_mutating_action_kind("read")
    assert not is_mutating_action_kind("inspect")
    assert not is_mutating_action_kind("record-source")
    assert validate_runtime_policy(Path("/tmp/context"), {}, allowed_freedom="proof-only") == []


def test_cli_common_core_handles_small_payload_and_mutation_helpers() -> None:
    assert parse_csv_refs(" CLM-1, ,SRC-2 ") == ["CLM-1", "SRC-2"]
    assert sanitize_artifact_name(" ../bad name?.png ") == "bad_name_.png"
    assert public_record_payload({"id": "CLM-1", "_path": "/tmp/x", "statement": "ok"}) == {
        "id": "CLM-1",
        "statement": "ok",
    }
    assert append_note("base", "extra") == "base\n\nextra"
    assert append_note("base\n\nextra", "extra") == "base\n\nextra"

    assert command_requires_write_lock(SimpleNamespace(command="record-claim"))
    assert command_requires_write_lock(SimpleNamespace(command="hypothesis", hypothesis_command="add"))
    assert command_requires_write_lock(SimpleNamespace(command="topic-index", topic_index_command="build"))
    assert command_requires_write_lock(SimpleNamespace(command="logic-index", logic_index_command="build"))
    assert command_requires_write_lock(SimpleNamespace(command="working-context", working_context_command="close"))
    assert command_requires_write_lock(SimpleNamespace(command="cleanup-archive", apply=True))
    assert not command_requires_write_lock(SimpleNamespace(command="cleanup-archive", apply=False))
    assert command_requires_write_lock(SimpleNamespace(command="cleanup-restore", apply=True))
    assert not command_requires_write_lock(SimpleNamespace(command="cleanup-restore", apply=False))
    assert not command_requires_write_lock(SimpleNamespace(command="search-records"))


def test_proposal_core_parses_options_and_summarizes_recommended_choice() -> None:
    option = parse_proposal_option("Extract seam|reduces CLI risk|less churn;direct tests|recommended")
    assert option == {
        "title": "Extract seam",
        "why": "reduces CLI risk",
        "tradeoffs": ["less churn", "direct tests"],
        "recommended": True,
    }
    assert parse_proposal_option("Keep adapter|preserves command surface") == {
        "title": "Keep adapter",
        "why": "preserves command surface",
        "tradeoffs": [],
        "recommended": False,
    }
    for raw, expected in (
        ("bad", "--proposal must be shaped"),
        ("Title|Why|tradeoff|maybe", "--proposal recommended flag must be"),
    ):
        try:
            parse_proposal_option(raw)
        except ValueError as exc:
            assert expected in str(exc)
        else:
            raise AssertionError(f"parse_proposal_option accepted invalid input: {raw}")

    summary = proposal_summary_line(
        {
            "id": "PRP-20260418-abcdef12",
            "status": "active",
            "confidence": "high",
            "subject": "TEP refactor",
            "proposals": [option],
        }
    )
    assert "`PRP-20260418-abcdef12` status=`active` confidence=`high`" in summary
    assert 'recommended="Extract seam"' in summary


def test_project_and_proposal_core_build_payloads() -> None:
    workspace = build_workspace_payload(
        record_id="WSP-20260418-work1111",
        timestamp="2026-04-18T08:00:00+03:00",
        workspace_key=" qa_tim_workspace ",
        title=" QA TIM Workspace ",
        status="active",
        context_root=" /Users/example/.tep_context ",
        root_refs=["/repo", "/bridge"],
        project_refs=["PRJ-20260418-abcdef12"],
        tags=["tep-core-rewrite"],
        note=" workspace note ",
    )
    assert workspace == {
        "id": "WSP-20260418-work1111",
        "record_type": "workspace",
        "scope": "qa_tim_workspace",
        "workspace_key": "qa_tim_workspace",
        "title": "QA TIM Workspace",
        "status": "active",
        "context_root": "/Users/example/.tep_context",
        "root_refs": ["/repo", "/bridge"],
        "project_refs": ["PRJ-20260418-abcdef12"],
        "created_at": "2026-04-18T08:00:00+03:00",
        "updated_at": "2026-04-18T08:00:00+03:00",
        "tags": ["tep-core-rewrite"],
        "note": "workspace note",
    }

    project = build_project_payload(
        record_id="PRJ-20260418-abcdef12",
        timestamp="2026-04-18T08:00:00+03:00",
        project_key=" qa_tim ",
        title=" TEP Plugin ",
        status="active",
        root_refs=["/repo"],
        related_project_refs=["PRJ-20260418-bbbb2222"],
        workspace_refs=["WSP-20260418-work1111"],
        tags=["tep-core-rewrite"],
        note=" project note ",
    )
    assert project == {
        "id": "PRJ-20260418-abcdef12",
        "record_type": "project",
        "scope": "qa_tim",
        "project_key": "qa_tim",
        "title": "TEP Plugin",
        "status": "active",
        "root_refs": ["/repo"],
        "related_project_refs": ["PRJ-20260418-bbbb2222"],
        "workspace_refs": ["WSP-20260418-work1111"],
        "created_at": "2026-04-18T08:00:00+03:00",
        "updated_at": "2026-04-18T08:00:00+03:00",
        "tags": ["tep-core-rewrite"],
        "note": "project note",
    }

    assigned = assign_project_payload(
        {
            "id": "CLM-20260418-aaaa1111",
            "project_refs": ["PRJ-20260418-bbbb2222"],
            "note": "base",
            "updated_at": "old",
        },
        "2026-04-18T08:05:00+03:00",
        "PRJ-20260418-aaaa1111",
        None,
    )
    assert assigned["project_refs"] == ["PRJ-20260418-aaaa1111", "PRJ-20260418-bbbb2222"]
    assert assigned["updated_at"] == "2026-04-18T08:05:00+03:00"
    assert assigned["note"] == (
        "base\n\n[2026-04-18T08:05:00+03:00] assigned to project PRJ-20260418-aaaa1111"
    )
    duplicate_assignment = assign_project_payload(
        assigned,
        "2026-04-18T08:05:00+03:00",
        "PRJ-20260418-aaaa1111",
        None,
    )
    assert duplicate_assignment["note"] == assigned["note"]

    manual_assignment = assign_project_payload(
        {"note": ""},
        "2026-04-18T08:05:00+03:00",
        "PRJ-20260418-aaaa1111",
        "manual",
    )
    assert manual_assignment["note"] == "manual"

    proposal_option = {
        "title": "Extract builders",
        "why": "smaller CLI",
        "tradeoffs": ["more modules"],
        "recommended": True,
    }
    proposal = build_proposal_payload(
        record_id="PRP-20260418-abcdef12",
        timestamp="2026-04-18T08:10:00+03:00",
        scope=" tep-plugin-development ",
        status="active",
        subject=" Builder extraction ",
        position=" Keep command semantics. ",
        claim_refs=["CLM-20260418-aaaa1111"],
        guideline_refs=["GLD-20260418-bbbb2222"],
        model_refs=["MODEL-20260418-cccc3333"],
        flow_refs=["FLOW-20260418-dddd4444"],
        open_question_refs=["OPEN-20260418-eeee5555"],
        assumptions=["commands remain stable"],
        concerns=["module sprawl"],
        proposals=[proposal_option],
        risks=["missed import"],
        stop_conditions=["tests fail"],
        confidence="high",
        created_by=" agent ",
        project_refs=["PRJ-20260418-ffff6666"],
        task_refs=["TASK-20260418-11112222"],
        supersedes_refs=["PRP-20260418-33334444"],
        tags=["tep-core-rewrite"],
        note=" proposal note ",
    )
    assert proposal == {
        "id": "PRP-20260418-abcdef12",
        "record_type": "proposal",
        "scope": "tep-plugin-development",
        "status": "active",
        "subject": "Builder extraction",
        "position": "Keep command semantics.",
        "claim_refs": ["CLM-20260418-aaaa1111"],
        "guideline_refs": ["GLD-20260418-bbbb2222"],
        "model_refs": ["MODEL-20260418-cccc3333"],
        "flow_refs": ["FLOW-20260418-dddd4444"],
        "open_question_refs": ["OPEN-20260418-eeee5555"],
        "assumptions": ["commands remain stable"],
        "concerns": ["module sprawl"],
        "proposals": [proposal_option],
        "risks": ["missed import"],
        "stop_conditions": ["tests fail"],
        "confidence": "high",
        "created_by": "agent",
        "project_refs": ["PRJ-20260418-ffff6666"],
        "task_refs": ["TASK-20260418-11112222"],
        "supersedes_refs": ["PRP-20260418-33334444"],
        "created_at": "2026-04-18T08:10:00+03:00",
        "updated_at": "2026-04-18T08:10:00+03:00",
        "tags": ["tep-core-rewrite"],
        "note": "proposal note",
    }


def test_task_core_builds_payload_and_lifecycle_mutations() -> None:
    timestamp = "2026-04-18T08:00:00+03:00"
    task = build_task_payload(
        record_id="TASK-20260418-abcdef12",
        timestamp=timestamp,
        scope=" tep-plugin-development ",
        title=" Extract TASK helpers ",
        task_type=" coding ",
        description=" Move pure task logic. ",
        related_claim_refs=["CLM-20260418-aaaa1111"],
        related_model_refs=["MODEL-20260418-bbbb2222"],
        related_flow_refs=["FLOW-20260418-cccc3333"],
        open_question_refs=["OPEN-20260418-dddd4444"],
        plan_refs=["PLN-20260418-eeee5555"],
        debt_refs=["DEBT-20260418-ffff6666"],
        action_refs=["ACT-20260418-11112222"],
        project_refs=["PRJ-20260418-33334444"],
        tags=["tep-core-rewrite"],
        note=" task note ",
    )
    assert task == {
        "id": "TASK-20260418-abcdef12",
        "record_type": "task",
        "scope": "tep-plugin-development",
        "title": "Extract TASK helpers",
        "description": "Move pure task logic.",
        "status": "active",
        "task_type": "coding",
        "related_claim_refs": ["CLM-20260418-aaaa1111"],
        "related_model_refs": ["MODEL-20260418-bbbb2222"],
        "related_flow_refs": ["FLOW-20260418-cccc3333"],
        "open_question_refs": ["OPEN-20260418-dddd4444"],
        "plan_refs": ["PLN-20260418-eeee5555"],
        "debt_refs": ["DEBT-20260418-ffff6666"],
        "action_refs": ["ACT-20260418-11112222"],
        "project_refs": ["PRJ-20260418-33334444"],
        "restriction_refs": [],
        "created_at": timestamp,
        "updated_at": timestamp,
        "tags": ["tep-core-rewrite"],
        "note": "task note",
    }
    assert task_summary_line(task) == (
        '`TASK-20260418-abcdef12` status=`active` type=`coding` scope=`tep-plugin-development` '
        'title="Extract TASK helpers"'
    )
    assert task_detail_lines(task) == [
        '- `TASK-20260418-abcdef12` status=`active` type=`coding` scope=`tep-plugin-development` title="Extract TASK helpers"',
        "  description: Move pure task logic.",
        "  related_claim_refs: ['CLM-20260418-aaaa1111']",
        "  related_model_refs: ['MODEL-20260418-bbbb2222']",
        "  related_flow_refs: ['FLOW-20260418-cccc3333']",
        "  open_question_refs: ['OPEN-20260418-dddd4444']",
        "  plan_refs: ['PLN-20260418-eeee5555']",
        "  debt_refs: ['DEBT-20260418-ffff6666']",
        "  action_refs: ['ACT-20260418-11112222']",
        "  project_refs: ['PRJ-20260418-33334444']",
    ]
    assert task_identity_text(task) == (
        "tep-plugin-development Extract TASK helpers Move pure task logic. coding tep-core-rewrite"
    )
    assert task_identity_text(None) == ""
    assert task_related_counts(task) == (
        "plan_refs=1, debt_refs=1, action_refs=1, open_question_refs=1, related_claim_refs=1"
    )

    no_task = build_task_drift_payload("", None, "extract task helpers", None)
    assert no_task["alignment"] == "unknown"
    assert no_task["exit_code"] == 0
    assert task_drift_text_lines(no_task) == [
        "alignment=unknown",
        "recommendation=start-task or ask the user before substantial work",
    ]

    missing_task = build_task_drift_payload("TASK-20260418-missing1", None, "extract task helpers", None)
    assert missing_task["exit_code"] == 1
    assert task_drift_text_lines(missing_task) == [
        "alignment=unknown",
        "reason=missing task record TASK-20260418-missing1",
    ]

    paused_task = dict(task, status="paused")
    paused_drift = build_task_drift_payload(paused_task["id"], paused_task, "extract task helpers", None)
    assert task_drift_text_lines(paused_drift) == [
        "alignment=unknown",
        "current_task=TASK-20260418-abcdef12 status=paused",
        "recommendation=resume-task or start a new task before substantial work",
    ]

    aligned = build_task_drift_payload(task["id"], task, "extract task helper lifecycle", "coding")
    assert aligned["alignment"] == "aligned"
    assert aligned["overlap"] == ["extract", "task"]
    assert task_drift_text_lines(aligned) == [
        "alignment=aligned",
        "current_task=TASK-20260418-abcdef12 type=coding title=Extract TASK helpers",
        "intent_type=coding",
        "overlap_terms=extract,task",
        "recommendation=continue",
    ]

    adjacent = build_task_drift_payload(task["id"], task, "coding", None)
    assert adjacent["alignment"] == "adjacent"
    assert adjacent["recommendation"] == "continue only if this is supporting work; otherwise pause/switch task"

    drifted = build_task_drift_payload(task["id"], task, "unrelated screenshots", None)
    assert drifted["alignment"] == "drifted"
    assert drifted["overlap"] == []

    type_drifted = build_task_drift_payload(task["id"], task, "extract task helper lifecycle", "investigation")
    assert type_drifted["alignment"] == "drifted"
    assert type_drifted["recommendation"] == "pause/switch current task before continuing"

    previous = dict(
        task,
        id="TASK-20260418-prev1111",
        title="Investigate prompt retry path",
        task_type="investigation",
        note="Prompt retry path already failed on stale selectors.",
        plan_refs=["PLN-20260418-prev1111"],
        debt_refs=["DEBT-20260418-prev1111"],
        action_refs=["ACT-20260418-prev1111"],
        open_question_refs=["OPEN-20260418-prev1111"],
        related_claim_refs=["CLM-20260418-prev1111"],
        updated_at="2026-04-18T09:00:00+03:00",
    )
    older = dict(
        previous,
        id="TASK-20260418-old11111",
        title="Investigate retry fallback",
        note="Fallback retry was checked earlier.",
        updated_at="2026-04-18T08:30:00+03:00",
    )
    other_project = dict(
        previous,
        id="TASK-20260418-other111",
        project_refs=["PRJ-20260418-other111"],
        updated_at="2026-04-18T10:00:00+03:00",
    )
    other_type = dict(
        previous,
        id="TASK-20260418-type1111",
        task_type="coding",
    )
    no_match = dict(
        previous,
        id="TASK-20260418-nomatch1",
        title="Investigate unrelated cache",
        note="Cache warmup does not mention the query terms.",
        updated_at="2026-04-18T10:30:00+03:00",
    )
    current = dict(task, task_type="investigation")
    records = {
        current["id"]: current,
        previous["id"]: previous,
        older["id"]: older,
        other_project["id"]: other_project,
        other_type["id"]: other_type,
        no_match["id"]: no_match,
        "CLM-20260418-notatask1": {
            "id": "CLM-20260418-notatask1",
            "record_type": "claim",
            "statement": "Prompt retry should not be selected as a task precedent.",
        },
    }
    selected = select_precedent_tasks(
        records,
        current["id"],
        "investigation",
        "prompt retry",
        "PRJ-20260418-33334444",
        "prompt retry",
        5,
    )
    assert [item["id"] for item in selected] == ["TASK-20260418-prev1111", "TASK-20260418-old11111"]
    review_payload = build_precedent_review_payload(current, "investigation", "prompt retry", selected)
    review_lines = precedent_review_text_lines(review_payload)
    assert review_lines[:6] == [
        "# Precedent Review",
        'Current task: `TASK-20260418-abcdef12` status=`active` type=`investigation` '
        'scope=`tep-plugin-development` title="Extract TASK helpers"',
        "task_type=`investigation`",
        'query="prompt retry"',
        "",
        "## Similar Tasks",
    ]
    assert "- `TASK-20260418-prev1111` status=`active` type=`investigation`" in review_lines[6]
    assert any(
        line == "  linked: plan_refs=1, debt_refs=1, action_refs=1, open_question_refs=1, related_claim_refs=1"
        for line in review_lines
    )
    assert "## Recommended Move" in review_lines
    empty_review = precedent_review_text_lines(build_precedent_review_payload(None, "general", None, []))
    assert empty_review == ["# Precedent Review", "task_type=`general`", "", "## Similar Tasks", "- none found"]

    assigned = assign_task_payload(
        {
            "id": "CLM-20260418-aaaa1111",
            "task_refs": ["TASK-20260418-bbbb2222"],
            "note": "base",
            "updated_at": "old",
        },
        timestamp,
        "TASK-20260418-aaaa1111",
        None,
    )
    assert assigned["task_refs"] == ["TASK-20260418-aaaa1111", "TASK-20260418-bbbb2222"]
    assert assigned["updated_at"] == timestamp
    assert assigned["note"] == f"base\n\n[{timestamp}] assigned to task TASK-20260418-aaaa1111"

    duplicate_assignment = assign_task_payload(assigned, timestamp, "TASK-20260418-aaaa1111", None)
    assert duplicate_assignment["note"] == assigned["note"]

    manual_assignment = assign_task_payload({"note": ""}, timestamp, "TASK-20260418-aaaa1111", "manual")
    assert manual_assignment["note"] == "manual"

    finished = finish_task_payload({"note": "base"}, timestamp, "completed", "done")
    assert finished["status"] == "completed"
    assert finished["updated_at"] == timestamp
    assert finished["completed_at"] == timestamp
    assert finished["note"] == f"base\n\n[{timestamp}] done"

    paused_without_note = finish_task_payload({"note": "base"}, timestamp, "paused", None)
    assert paused_without_note["status"] == "paused"
    assert paused_without_note["paused_at"] == timestamp
    assert paused_without_note["note"] == "base"

    resumed = resume_task_payload({"note": "base"}, timestamp, "resume")
    assert resumed["status"] == "active"
    assert resumed["resumed_at"] == timestamp
    assert resumed["note"] == f"base\n\n[{timestamp}] resume"

    switch_pause = pause_task_for_switch_payload(
        {"note": "base"},
        timestamp,
        "TASK-20260418-cccc3333",
        "context shift",
    )
    assert switch_pause["status"] == "paused"
    assert switch_pause["paused_at"] == timestamp
    assert switch_pause["note"] == f"base\n\n[{timestamp}] paused by switch-task to TASK-20260418-cccc3333: context shift"


def test_working_context_core_builds_payloads_and_mutations() -> None:
    timestamp = "2026-04-18T08:00:00+03:00"
    assumption = parse_working_context_assumption(
        " topic inference is useful | supported | CLM-20260418-aaaa1111, CLM-20260418-bbbb2222 "
    )
    assert assumption == {
        "text": "topic inference is useful",
        "mode": "supported",
        "support_refs": ["CLM-20260418-aaaa1111", "CLM-20260418-bbbb2222"],
    }
    assert parse_working_context_assumptions(["needs exploration"]) == [
        {"text": "needs exploration", "mode": "exploration-only", "support_refs": []}
    ]
    for raw, expected in (("", "--assumption must start"), ("x|bad", "--assumption mode must be")):
        try:
            parse_working_context_assumption(raw)
        except ValueError as exc:
            assert expected in str(exc)
        else:
            raise AssertionError(f"parse_working_context_assumption accepted invalid input: {raw}")

    context = build_working_context_payload(
        record_id="WCTX-20260418-abcdef12",
        timestamp=timestamp,
        scope=" tep-plugin-development ",
        title=" WCTX extraction ",
        context_kind="investigation",
        pinned_refs=["CLM-20260418-aaaa1111"],
        focus_paths=["plugins/trust-evidence-protocol/scripts/context_cli.py"],
        topic_terms=["working", "context"],
        topic_seed_refs=["MODEL-20260418-bbbb2222"],
        assumptions=[assumption],
        concerns=["avoid proof misuse"],
        project_refs=["PRJ-20260418-cccc3333"],
        task_refs=["TASK-20260418-dddd4444"],
        tags=["tep-core-rewrite"],
        note=" context note ",
    )
    assert context == {
        "id": "WCTX-20260418-abcdef12",
        "record_type": "working_context",
        "scope": "tep-plugin-development",
        "title": "WCTX extraction",
        "status": "active",
        "context_kind": "investigation",
        "pinned_refs": ["CLM-20260418-aaaa1111"],
        "focus_paths": ["plugins/trust-evidence-protocol/scripts/context_cli.py"],
        "topic_terms": ["working", "context"],
        "topic_seed_refs": ["MODEL-20260418-bbbb2222"],
        "assumptions": [assumption],
        "concerns": ["avoid proof misuse"],
        "parent_context_ref": "",
        "supersedes_refs": [],
        "project_refs": ["PRJ-20260418-cccc3333"],
        "task_refs": ["TASK-20260418-dddd4444"],
        "created_at": timestamp,
        "updated_at": timestamp,
        "tags": ["tep-core-rewrite"],
        "note": "context note",
    }
    assert working_context_summary_line(context) == (
        '`WCTX-20260418-abcdef12` status=`active` kind=`investigation` title="WCTX extraction"'
    )
    assert working_context_detail_lines(context) == [
        '- `WCTX-20260418-abcdef12` status=`active` kind=`investigation` title="WCTX extraction"',
        "  pinned_refs: ['CLM-20260418-aaaa1111']",
        "  focus_paths: ['plugins/trust-evidence-protocol/scripts/context_cli.py']",
        "  topic_terms: ['working', 'context']",
        "  topic_seed_refs: ['MODEL-20260418-bbbb2222']",
        "  project_refs: ['PRJ-20260418-cccc3333']",
        "  task_refs: ['TASK-20260418-dddd4444']",
        "  assumptions:",
        "    - mode=supported: topic inference is useful support_refs=['CLM-20260418-aaaa1111', 'CLM-20260418-bbbb2222']",
        "  concerns: ['avoid proof misuse']",
        "  note: context note",
    ]
    assert working_context_show_payload([context]) == {
        "working_context_is_proof": False,
        "contexts": [context],
    }
    assert "  parent_context_ref: WCTX-20260418-parent1" in working_context_detail_lines(
        {**context, "parent_context_ref": "WCTX-20260418-parent1"}
    )

    assert add_remove_values([" a ", "b"], ["b", " c "], [" a "]) == ["b", "c"]

    forked = fork_working_context_payload(
        source_payload={
            "id": "WCTX-20260418-source111",
            "record_type": "working_context",
            "title": "Old title",
            "status": "closed",
            "context_kind": "",
            "pinned_refs": ["CLM-20260418-old11111"],
            "focus_paths": ["old.py"],
            "topic_terms": ["old"],
            "topic_seed_refs": ["CLM-20260418-seed1111"],
            "assumptions": [{"text": "old", "mode": "supported", "support_refs": []}],
            "concerns": ["old concern"],
            "supersedes_refs": ["WCTX-20260418-prev1111"],
            "project_refs": ["PRJ-20260418-old1111"],
            "task_refs": ["TASK-20260418-old1111"],
            "tags": ["old"],
            "note": "base",
        },
        record_id="WCTX-20260418-new11111",
        timestamp="2026-04-18T08:10:00+03:00",
        context_ref="WCTX-20260418-source111",
        title=None,
        context_kind=None,
        add_pinned_refs=["CLM-20260418-new22222"],
        remove_pinned_refs=["CLM-20260418-old11111"],
        add_focus_paths=["new.py"],
        remove_focus_paths=[],
        add_topic_terms=[],
        remove_topic_terms=["old"],
        add_topic_seed_refs=["MODEL-20260418-new33333"],
        remove_topic_seed_refs=[],
        added_assumptions=[{"text": "new", "mode": "exploration-only", "support_refs": []}],
        add_concerns=["new concern"],
        inferred_topic_terms=["inferred"],
        project_refs=["PRJ-20260418-new44444"],
        task_refs=[],
        tags=["new"],
        note="fork note",
    )
    assert forked["id"] == "WCTX-20260418-new11111"
    assert forked["status"] == "active"
    assert forked["title"] == "Old title"
    assert forked["context_kind"] == "general"
    assert forked["pinned_refs"] == ["CLM-20260418-new22222"]
    assert forked["focus_paths"] == ["old.py", "new.py"]
    assert forked["topic_terms"] == ["inferred"]
    assert forked["topic_seed_refs"] == ["CLM-20260418-seed1111", "MODEL-20260418-new33333"]
    assert forked["parent_context_ref"] == "WCTX-20260418-source111"
    assert forked["supersedes_refs"] == ["WCTX-20260418-prev1111", "WCTX-20260418-source111"]
    assert forked["project_refs"] == ["PRJ-20260418-new44444"]
    assert forked["task_refs"] == ["TASK-20260418-old1111"]
    assert forked["tags"] == ["new", "old"]
    assert forked["note"] == "base\n\nfork note"

    forked_with_task_override = fork_working_context_payload(
        source_payload={"id": "WCTX-20260418-source111", "note": ""},
        record_id="WCTX-20260418-task1111",
        timestamp="2026-04-18T08:15:00+03:00",
        context_ref="WCTX-20260418-source111",
        title="Task override",
        context_kind="general",
        add_pinned_refs=[],
        remove_pinned_refs=[],
        add_focus_paths=[],
        remove_focus_paths=[],
        add_topic_terms=["topic"],
        remove_topic_terms=[],
        add_topic_seed_refs=[],
        remove_topic_seed_refs=[],
        added_assumptions=[],
        add_concerns=[],
        inferred_topic_terms=[],
        project_refs=[],
        task_refs=["TASK-20260418-new55555"],
        tags=[],
        note="task override",
    )
    assert forked_with_task_override["task_refs"] == ["TASK-20260418-new55555"]

    closed = close_working_context_payload({"note": "base"}, "2026-04-18T08:20:00+03:00", "closed", "done")
    assert closed == {
        "note": "base\n\n[2026-04-18T08:20:00+03:00] done",
        "status": "closed",
        "updated_at": "2026-04-18T08:20:00+03:00",
        "closed_at": "2026-04-18T08:20:00+03:00",
    }


def test_topic_index_core_builds_navigation_prefilter_and_reports(tmp_path: Path) -> None:
    root = tmp_path / ".codex_context"
    claim_a = "CLM-20260418-aaaa1111"
    claim_b = "CLM-20260418-bbbb2222"
    source_id = "SRC-20260418-cccc3333"
    context_id = "WCTX-20260418-dddd4444"
    records = {
        claim_a: {
            "id": claim_a,
            "record_type": "claim",
            "status": "supported",
            "scope": "gateway",
            "statement": "Gateway timeout retry policy writes an artifact screenshot after a UI timeout.",
            "recorded_at": "2026-04-18T10:00:00+03:00",
            "comparison": {"key": "gateway.timeout.policy"},
        },
        claim_b: {
            "id": claim_b,
            "record_type": "claim",
            "status": "tentative",
            "scope": "gateway",
            "statement": "Gateway retry timeout policy differs in the prompt action flow.",
            "recorded_at": "2026-04-18T10:01:00+03:00",
            "comparison": {"key": "gateway.timeout.policy"},
        },
        source_id: {
            "id": source_id,
            "record_type": "source",
            "critique_status": "accepted",
            "source_kind": "runtime",
            "quote": "gateway timeout retry artifact screenshot",
            "captured_at": "2026-04-18T10:02:00+03:00",
        },
        context_id: {
            "id": context_id,
            "record_type": "working_context",
            "status": "active",
            "context_kind": "implementation",
            "title": "Gateway topic investigation",
            "pinned_refs": [claim_a],
            "assumptions": [{"text": "Gateway retry topic needs inspection", "support_refs": [claim_a]}],
        },
    }

    assert "the" not in task_terms("the gateway lexical topic")
    assert topic_tokenize("Gateway and the 123 retry retry") == ["gateway", "retry", "retry"]

    payload = build_lexical_topic_index(records, terms_per_record=12, topic_limit=12)
    assert payload["method"] == "lexical"
    assert payload["record_count"] == 4
    assert all(topic["note"] == "Generated lexical navigation topic. Not proof." for topic in payload["topics"].values())

    topic_records = payload["records"]
    score, matched = topic_search_matches(topic_records[claim_a], {"gateway", "timeout"})
    assert score > 0
    assert matched == ["gateway", "timeout"]

    candidates = topic_conflict_candidates(records, topic_records, limit=5)
    assert candidates
    assert candidates[0]["signals"]["candidate_only"] is True
    assert "does not prove contradiction" in candidates[0]["note"]

    write_topic_index_reports(root, payload, candidates)
    assert load_topic_records(root) == topic_records
    assert "Generated Topic Index" in (root / "topic_index" / "summary.md").read_text(encoding="utf-8")
    assert "Generated lexical prefilter" in (root / "topic_index" / "conflict_candidates.md").read_text(encoding="utf-8")

    inferred_terms = infer_topic_terms_from_refs(root, records, [claim_a], limit=3)
    assert inferred_terms


def test_report_core_renders_reports_and_relative_paths(tmp_path: Path) -> None:
    root = tmp_path / ".codex_context"
    nested = root / "records" / "claim" / "CLM-20260418-abcdef12.json"
    external = tmp_path / "external.txt"

    assert rel_display(root, nested) == "records/claim/CLM-20260418-abcdef12.json"
    assert rel_display(root, external) == str(external)

    empty_report = root / "review" / "empty.md"
    write_report(empty_report, "Empty", "Generated.", [])
    assert "No issues found." in empty_report.read_text(encoding="utf-8")

    write_validation_report(root, [ValidationError(nested, "missing ref")])
    validation_report = root / "review" / "broken.md"
    assert "- `records/claim/CLM-20260418-abcdef12.json`: missing ref" in validation_report.read_text(encoding="utf-8")


def test_generated_views_core_writes_backlog_index_and_dependency_impact(tmp_path: Path) -> None:
    root = tmp_path / ".codex_context"
    claim_id = "CLM-20260418-aaaa1111"
    plan_id = "PLN-20260418-bbbb2222"
    debt_id = "DEBT-20260418-cccc3333"
    model_id = "MODEL-20260418-dddd4444"

    records = {
        claim_id: {
            "_path": root / "records" / "claim" / f"{claim_id}.json",
            "id": claim_id,
            "record_type": "claim",
            "status": "supported",
            "statement": "The generated views render active work.",
            "lifecycle": {"state": "historical", "attention": "fallback-only"},
            "updated_at": "2026-04-18T10:00:00+03:00",
        },
        plan_id: {
            "_path": root / "records" / "plan" / f"{plan_id}.json",
            "id": plan_id,
            "record_type": "plan",
            "status": "active",
            "priority": "high",
            "title": "Move generated views",
            "blocked_by": [claim_id],
            "updated_at": "2026-04-18T11:00:00+03:00",
        },
        debt_id: {
            "_path": root / "records" / "debt" / f"{debt_id}.json",
            "id": debt_id,
            "record_type": "debt",
            "status": "open",
            "priority": "medium",
            "title": "Add more view assertions",
            "plan_refs": [plan_id],
        },
        model_id: {
            "_path": root / "records" / "model" / f"{model_id}.json",
            "id": model_id,
            "record_type": "model",
            "status": "working",
            "scope": "tep-plugin-development",
            "aspect": "views",
            "claim_refs": [claim_id],
            "summary": "Generated views summarize records.",
        },
    }

    assert record_attention_label(records[claim_id]) == "The generated views render active work."
    assert [item["id"] for item in fallback_claims(records, 10)] == [claim_id]
    impact = collect_dependency_impact(root, records, claim_id)
    assert impact["direct_by_type"] == {"model": [model_id], "plan": [plan_id]}

    write_backlog(root, records)
    backlog = (root / "backlog.md").read_text(encoding="utf-8")
    assert f"`{plan_id}` priority=`high` status=`active`" in backlog
    assert f"`{debt_id}` priority=`medium` status=`open`" in backlog

    write_models_report(root, records)
    assert "Generated Model Review" in (root / "review" / "models.md").read_text(encoding="utf-8")

    write_resolved_report(root, records)
    resolved = (root / "review" / "resolved.md").read_text(encoding="utf-8")
    assert f"`{claim_id}`" in resolved
    assert "fallback-only" in resolved

    write_attention_report(root, records)
    attention = (root / "review" / "attention.md").read_text(encoding="utf-8")
    assert "Fallback Historical Claims" in attention

    build_index(root, records)
    index = (root / "index.md").read_text(encoding="utf-8")
    assert "- `claim`: 1" in index
    assert f"`{model_id}`" in index


def test_rollback_core_builds_report_payload_and_text() -> None:
    claim_id = "CLM-20260418-aaaa1111"
    model_id = "MODEL-20260418-bbbb2222"
    flow_id = "FLOW-20260418-cccc3333"
    plan_id = "PLN-20260418-dddd4444"
    action_id = "ACT-20260418-eeee5555"
    records = {
        model_id: {"id": model_id, "record_type": "model"},
        flow_id: {"id": flow_id, "record_type": "flow"},
        plan_id: {"id": plan_id, "record_type": "plan"},
    }
    impact = {
        "direct": [model_id],
        "direct_by_type": {"model": [model_id]},
        "transitive_only_by_type": {"flow": [flow_id], "plan": [plan_id]},
        "transitive": [model_id, flow_id, plan_id, action_id],
    }
    hypothesis_entries = [
        {
            "claim_ref": claim_id,
            "status": "active",
            "scope": "gateway.retry",
            "used_by": {"actions": [action_id], "models": [model_id]},
            "rollback_refs": [action_id],
        },
        {"claim_ref": "CLM-20260418-other111", "status": "active"},
    ]

    impact_payload = build_impact_graph_payload(claim_id, impact)
    assert impact_payload == {
        "claim_ref": claim_id,
        "direct": [model_id],
        "direct_by_type": {"model": [model_id]},
        "transitive_only_by_type": {"flow": [flow_id], "plan": [plan_id]},
    }
    assert impact_graph_text_lines(impact_payload) == [
        f"Anchor claim: {claim_id}",
        "",
        "Directly affected:",
        f"- model: {model_id}",
        "",
        "Transitively affected:",
        f"- flow: {flow_id}",
        f"- plan: {plan_id}",
    ]
    assert impact_graph_text_lines(build_impact_graph_payload(claim_id, {})) == [
        f"Anchor claim: {claim_id}",
        "",
        "Directly affected:",
        "- none",
        "",
        "Transitively affected:",
        "- none",
    ]

    payload = build_rollback_report_payload(records, claim_id, impact, hypothesis_entries)
    assert payload == {
        "claim_ref": claim_id,
        "direct_by_type": {"model": [model_id]},
        "transitive_only_by_type": {"flow": [flow_id], "plan": [plan_id]},
        "stale_candidates": [model_id, flow_id],
        "hypothesis_entries": [hypothesis_entries[0]],
    }
    assert rollback_report_text_lines(payload) == [
        f"Rollback report for {claim_id}",
        "",
        "Directly affected:",
        f"- model: {model_id}",
        "",
        "Transitively affected:",
        f"- flow: {flow_id}",
        f"- plan: {plan_id}",
        "",
        "Stale candidates:",
        f"- {model_id}, {flow_id}",
        "",
        "Hypothesis index entries:",
        (
            f"- status=active scope=gateway.retry used_by={{'actions': ['{action_id}'], "
            f"'models': ['{model_id}']}} rollback_refs=['{action_id}']"
        ),
    ]

    empty_payload = build_rollback_report_payload({}, claim_id, {}, [])
    assert rollback_report_text_lines(empty_payload) == [
        f"Rollback report for {claim_id}",
        "",
        "Directly affected:",
        "- none",
        "",
        "Transitively affected:",
        "- none",
        "",
        "Stale candidates:",
        "- none",
        "",
        "Hypothesis index entries:",
        "- none",
    ]


def test_schema_core_validates_record_shapes_and_typed_refs(tmp_path: Path) -> None:
    root = tmp_path / ".codex_context"
    input_id = "INP-20260418-aaaa1111"
    source_id = "SRC-20260418-aaaa1111"
    claim_id = "CLM-20260418-bbbb2222"
    model_id = "MODEL-20260418-cccc3333"

    input_record = {
        "_path": root / "records" / "input" / f"{input_id}.json",
        "_folder": "input",
        "id": input_id,
        "record_type": "input",
        "scope": "tep-plugin-development",
        "note": "Test input.",
        "input_kind": "user_prompt",
        "captured_at": "2026-04-18T09:59:00+03:00",
        "origin": {"kind": "user_prompt", "ref": "chat:1"},
        "text": "Please preserve input provenance.",
        "derived_record_refs": [claim_id],
    }
    source = {
        "_path": root / "records" / "source" / f"{source_id}.json",
        "_folder": "source",
        "id": source_id,
        "record_type": "source",
        "scope": "tep-plugin-development",
        "note": "Test source.",
        "source_kind": "code",
        "critique_status": "accepted",
        "captured_at": "2026-04-18T10:00:00+03:00",
        "independence_group": "test",
        "origin": {"kind": "file", "ref": "plugins/example.py"},
        "quote": "def example(): pass",
    }
    claim = {
        "_path": root / "records" / "claim" / f"{claim_id}.json",
        "_folder": "claim",
        "id": claim_id,
        "record_type": "claim",
        "scope": "tep-plugin-development",
        "note": "Test claim.",
        "plane": "code",
        "status": "supported",
        "statement": "Example exists.",
        "recorded_at": "2026-04-18T10:01:00+03:00",
        "source_refs": [source_id],
        "input_refs": [input_id],
    }
    bad_model = {
        "_path": root / "records" / "model" / f"{model_id}.json",
        "_folder": "model",
        "id": model_id,
        "record_type": "model",
        "scope": "tep-plugin-development",
        "note": "Bad model.",
        "knowledge_class": "domain",
        "status": "working",
        "domain": "tep",
        "aspect": "schemas",
        "summary": "Bad claim ref type.",
        "updated_at": "2026-04-18T10:02:00+03:00",
        "is_primary": False,
        "claim_refs": [source_id],
    }

    assert validate_record(input_id, input_record) == []
    assert validate_record(source_id, source) == []
    assert validate_record(claim_id, claim) == []
    errors = validate_refs({input_id: input_record, source_id: source, claim_id: claim, model_id: bad_model})
    assert any(error.message == f"model claim ref {source_id} must reference a claim record" for error in errors)

    wrong_input_ref = {**claim, "input_refs": [source_id]}
    wrong_input_errors = validate_refs({input_id: input_record, source_id: source, claim_id: wrong_input_ref})
    assert any(error.message == f"input ref {source_id} must reference an input record" for error in wrong_input_errors)

    _, candidate_errors = validate_candidate_record(root, {source_id: source}, source)
    assert any(error.message == f"duplicate id: {source_id}" for error in candidate_errors)


def test_validation_core_normalizes_optional_lists_and_confidence() -> None:
    payload = {
        "items": [1, " two ", ""],
        "mapping": {"ok": True},
        "confidence": "high",
        "red_flags": [" risk ", ""],
    }

    assert ensure_list(payload, "items") == ["1", " two ", ""]
    assert ensure_string_list(payload, "items") == ["1", "two"]
    assert ensure_dict(payload, "mapping") == {"ok": True}
    assert safe_list({"items": "bad"}, "items") == []
    assert validate_optional_confidence(payload) == []
    assert validate_optional_confidence({"confidence": "certain"}) == ["confidence must be high, moderate, or low"]
    assert validate_optional_red_flags(payload) == []
    assert validate_optional_red_flags({"red_flags": ""}) == []
    assert validate_optional_red_flags({"red_flags": [""]}) == ["red_flags must contain non-empty strings when provided"]
    assert validate_optional_red_flags({"red_flags": "bad"}) == ["red_flags must be a list"]

    try:
        ensure_list({"items": "bad"}, "items")
    except ValueError as exc:
        assert str(exc) == "items must be a list"
    else:
        raise AssertionError("ensure_list accepted a non-list value")

    try:
        ensure_dict({"mapping": []}, "mapping")
    except ValueError as exc:
        assert str(exc) == "mapping must be an object"
    else:
        raise AssertionError("ensure_dict accepted a non-object value")


def test_flow_core_builds_cli_payload_helpers() -> None:
    step = build_flow_step(
        " setup ",
        " Setup environment ",
        "aligned",
        ["CLM-20260418-aaaa1111"],
        ["execute"],
        ["OPEN-20260418-bbbb2222"],
        ["CLM-20260418-cccc3333"],
    )
    assert step == {
        "id": "setup",
        "label": "Setup environment",
        "status": "aligned",
        "claim_refs": ["CLM-20260418-aaaa1111"],
        "next_steps": ["execute"],
        "open_question_refs": ["OPEN-20260418-bbbb2222"],
        "accepted_deviation_refs": ["CLM-20260418-cccc3333"],
    }

    minimal_step = build_flow_step("done", "Done", "unresolved", [], [], [], [])
    assert minimal_step == {
        "id": "done",
        "label": "Done",
        "status": "unresolved",
        "claim_refs": [],
        "next_steps": [],
    }

    assert build_flow_preconditions(["CLM-1"], ["CLM-2"], " needs setup ") == {
        "claim_refs": ["CLM-1"],
        "hypothesis_refs": ["CLM-2"],
        "note": "needs setup",
    }
    assert build_flow_oracle(["CLM-3"], ["CLM-4"], ["CLM-5"], " verify both ") == {
        "success_claim_refs": ["CLM-3"],
        "failure_claim_refs": ["CLM-4"],
        "hypothesis_refs": ["CLM-5"],
        "note": "verify both",
    }

    flow = build_flow_payload(
        record_id="FLOW-20260418-abcdef12",
        timestamp="2026-04-18T08:00:00+03:00",
        knowledge_class="domain",
        domain=" tep-runtime ",
        scope=" plugin-rewrite ",
        status="working",
        is_primary=True,
        summary=" Extract pure builders. ",
        model_refs=["MODEL-20260418-aaaa1111"],
        open_question_refs=["OPEN-20260418-bbbb2222"],
        preconditions={"claim_refs": ["CLM-1"], "hypothesis_refs": []},
        oracle={"success_claim_refs": ["CLM-2"], "failure_claim_refs": [], "hypothesis_refs": []},
        steps=[step],
        supersedes_refs=["FLOW-20260418-cccc3333"],
        promoted_from_refs=[],
        project_refs=["PROJ-20260418-dddd4444"],
        task_refs=["TASK-20260418-eeee5555"],
        note=" flow note ",
    )
    assert flow == {
        "id": "FLOW-20260418-abcdef12",
        "record_type": "flow",
        "knowledge_class": "domain",
        "domain": "tep-runtime",
        "scope": "plugin-rewrite",
        "status": "working",
        "is_primary": True,
        "summary": "Extract pure builders.",
        "model_refs": ["MODEL-20260418-aaaa1111"],
        "open_question_refs": ["OPEN-20260418-bbbb2222"],
        "preconditions": {"claim_refs": ["CLM-1"], "hypothesis_refs": []},
        "oracle": {"success_claim_refs": ["CLM-2"], "failure_claim_refs": [], "hypothesis_refs": []},
        "steps": [step],
        "supersedes_refs": ["FLOW-20260418-cccc3333"],
        "promoted_from_refs": [],
        "project_refs": ["PROJ-20260418-dddd4444"],
        "task_refs": ["TASK-20260418-eeee5555"],
        "updated_at": "2026-04-18T08:00:00+03:00",
        "note": "flow note",
    }


def test_knowledge_core_builds_model_and_open_question_payloads() -> None:
    model = build_model_payload(
        record_id="MODEL-20260418-abcdef12",
        timestamp="2026-04-18T08:00:00+03:00",
        knowledge_class="domain",
        domain=" tep-runtime ",
        scope=" plugin-rewrite ",
        aspect=" architecture ",
        status="working",
        is_primary=True,
        summary=" Stable core owns deterministic records. ",
        claim_refs=["CLM-20260418-aaaa1111"],
        open_question_refs=["OPEN-20260418-bbbb2222"],
        hypothesis_refs=["CLM-20260418-cccc3333"],
        related_model_refs=["MODEL-20260418-dddd4444"],
        supersedes_refs=[],
        promoted_from_refs=["PRP-20260418-eeee5555"],
        project_refs=["PROJ-20260418-ffff6666"],
        task_refs=["TASK-20260418-11112222"],
        note=" model note ",
    )
    assert model == {
        "id": "MODEL-20260418-abcdef12",
        "record_type": "model",
        "knowledge_class": "domain",
        "domain": "tep-runtime",
        "scope": "plugin-rewrite",
        "aspect": "architecture",
        "status": "working",
        "is_primary": True,
        "summary": "Stable core owns deterministic records.",
        "claim_refs": ["CLM-20260418-aaaa1111"],
        "open_question_refs": ["OPEN-20260418-bbbb2222"],
        "hypothesis_refs": ["CLM-20260418-cccc3333"],
        "related_model_refs": ["MODEL-20260418-dddd4444"],
        "supersedes_refs": [],
        "promoted_from_refs": ["PRP-20260418-eeee5555"],
        "project_refs": ["PROJ-20260418-ffff6666"],
        "task_refs": ["TASK-20260418-11112222"],
        "updated_at": "2026-04-18T08:00:00+03:00",
        "note": "model note",
    }

    question = build_open_question_payload(
        record_id="OPEN-20260418-abcdef12",
        timestamp="2026-04-18T08:10:00+03:00",
        domain=" tep-runtime ",
        scope=" plugin-rewrite ",
        aspect=" flow ",
        status="open",
        question=" Should task mutation move next? ",
        related_claim_refs=["CLM-20260418-aaaa1111"],
        related_model_refs=["MODEL-20260418-bbbb2222"],
        related_flow_refs=["FLOW-20260418-cccc3333"],
        resolved_by_claim_refs=[],
        project_refs=["PROJ-20260418-dddd4444"],
        task_refs=["TASK-20260418-eeee5555"],
        note=" question note ",
    )
    assert question == {
        "id": "OPEN-20260418-abcdef12",
        "record_type": "open_question",
        "domain": "tep-runtime",
        "scope": "plugin-rewrite",
        "aspect": "flow",
        "status": "open",
        "question": "Should task mutation move next?",
        "related_claim_refs": ["CLM-20260418-aaaa1111"],
        "related_model_refs": ["MODEL-20260418-bbbb2222"],
        "related_flow_refs": ["FLOW-20260418-cccc3333"],
        "resolved_by_claim_refs": [],
        "project_refs": ["PROJ-20260418-dddd4444"],
        "task_refs": ["TASK-20260418-eeee5555"],
        "created_at": "2026-04-18T08:10:00+03:00",
        "note": "question note",
    }


def test_knowledge_core_promotes_model_and_flow_to_domain_payloads() -> None:
    timestamp = "2026-04-18T08:20:00+03:00"
    source_model_ref = "MODEL-20260418-source11"
    promoted_model_id = "MODEL-20260418-domain22"
    model_source = {
        "id": source_model_ref,
        "record_type": "model",
        "knowledge_class": "investigation",
        "status": "stable",
        "is_primary": True,
        "promoted_from_refs": ["MODEL-20260418-old3333"],
        "note": "model base",
    }

    model_update, promoted_model = promote_model_to_domain_payloads(
        source_payload=model_source,
        timestamp=timestamp,
        source_model_ref=source_model_ref,
        promoted_model_id=promoted_model_id,
        note=None,
    )

    assert model_update["id"] == source_model_ref
    assert model_update["status"] == "superseded"
    assert model_update["is_primary"] is False
    assert model_update["updated_at"] == timestamp
    assert model_update["note"] == (
        f"model base\n\n[{timestamp}] superseded by domain promotion from {source_model_ref}"
    )
    assert promoted_model["id"] == promoted_model_id
    assert promoted_model["knowledge_class"] == "domain"
    assert promoted_model["status"] == "stable"
    assert promoted_model["is_primary"] is True
    assert promoted_model["promoted_from_refs"] == ["MODEL-20260418-old3333", source_model_ref]
    assert promoted_model["note"] == (
        f"model base\n\n[{timestamp}] promoted to domain knowledge from {source_model_ref}"
    )
    assert model_source["status"] == "stable"

    source_flow_ref = "FLOW-20260418-source11"
    promoted_flow_id = "FLOW-20260418-domain22"
    flow_source = {
        "id": source_flow_ref,
        "record_type": "flow",
        "knowledge_class": "investigation",
        "status": "stable",
        "is_primary": True,
        "promoted_from_refs": [],
        "note": "flow base",
    }

    flow_update, promoted_flow = promote_flow_to_domain_payloads(
        source_payload=flow_source,
        timestamp=timestamp,
        source_flow_ref=source_flow_ref,
        promoted_flow_id=promoted_flow_id,
        note="approved domain flow",
    )

    assert flow_update["id"] == source_flow_ref
    assert flow_update["status"] == "superseded"
    assert flow_update["is_primary"] is False
    assert flow_update["updated_at"] == timestamp
    assert flow_update["note"] == (
        f"flow base\n\n[{timestamp}] superseded by domain promotion from {source_flow_ref}"
    )
    assert promoted_flow["id"] == promoted_flow_id
    assert promoted_flow["knowledge_class"] == "domain"
    assert promoted_flow["status"] == "stable"
    assert promoted_flow["promoted_from_refs"] == [source_flow_ref]
    assert promoted_flow["note"] == "flow base\n\napproved domain flow"
    assert flow_source["status"] == "stable"


def test_knowledge_core_marks_model_and_flow_stale_from_claim() -> None:
    claim_ref = "CLM-20260418-aaaa1111"
    model_ref = "MODEL-20260418-bbbb2222"
    flow_ref = "FLOW-20260418-cccc3333"
    stale_model_ref = "MODEL-20260418-dddd4444"
    superseded_flow_ref = "FLOW-20260418-eeee5555"
    plan_ref = "PLN-20260418-ffff6666"
    records = {
        model_ref: {
            "_path": "/tmp/private",
            "id": model_ref,
            "record_type": "model",
            "status": "stable",
            "note": "model base",
        },
        flow_ref: {
            "id": flow_ref,
            "record_type": "flow",
            "status": "working",
            "note": "",
        },
        stale_model_ref: {"id": stale_model_ref, "record_type": "model", "status": "stale"},
        superseded_flow_ref: {"id": superseded_flow_ref, "record_type": "flow", "status": "superseded"},
        plan_ref: {"id": plan_ref, "record_type": "plan", "status": "active"},
    }
    candidates = [plan_ref, model_ref, flow_ref, "MISSING-20260418-00000000", stale_model_ref, superseded_flow_ref]

    target_ids = stale_knowledge_target_ids(records, candidates)
    assert target_ids == [model_ref, flow_ref]

    timestamp = "2026-04-18T10:30:00+03:00"
    updates = mark_knowledge_records_stale_payloads(records, target_ids, timestamp, claim_ref, None)
    assert sorted(updates) == [flow_ref, model_ref]
    assert updates[model_ref]["status"] == "stale"
    assert updates[model_ref]["updated_at"] == timestamp
    assert updates[model_ref]["note"] == f"model base\n\n[{timestamp}] marked stale from weakened claim {claim_ref}"
    assert "_path" not in updates[model_ref]
    assert updates[flow_ref]["note"] == f"[{timestamp}] marked stale from weakened claim {claim_ref}"
    assert records[model_ref]["status"] == "stable"

    custom_updates = mark_knowledge_records_stale_payloads(records, [flow_ref], timestamp, claim_ref, "manual stale note")
    assert custom_updates[flow_ref]["note"] == "manual stale note"


def test_planning_core_builds_plan_and_debt_payloads() -> None:
    plan = build_plan_payload(
        record_id="PLN-20260418-abcdef12",
        timestamp="2026-04-18T08:00:00+03:00",
        scope=" tep-plugin-development ",
        title=" Split CLI ",
        priority="high",
        status="active",
        justified_by=["CLM-20260418-aaaa1111"],
        steps=["extract pure helpers"],
        success_criteria=["deterministic tests pass"],
        blocked_by=["DEBT-20260418-bbbb2222"],
        project_refs=["PROJ-20260418-cccc3333"],
        task_refs=["TASK-20260418-dddd4444"],
        tags=["tep-core-rewrite"],
        note=" keep CLI behavior ",
    )
    assert plan == {
        "id": "PLN-20260418-abcdef12",
        "record_type": "plan",
        "scope": "tep-plugin-development",
        "title": "Split CLI",
        "status": "active",
        "priority": "high",
        "justified_by": ["CLM-20260418-aaaa1111"],
        "steps": ["extract pure helpers"],
        "success_criteria": ["deterministic tests pass"],
        "blocked_by": ["DEBT-20260418-bbbb2222"],
        "project_refs": ["PROJ-20260418-cccc3333"],
        "task_refs": ["TASK-20260418-dddd4444"],
        "created_at": "2026-04-18T08:00:00+03:00",
        "updated_at": "2026-04-18T08:00:00+03:00",
        "tags": ["tep-core-rewrite"],
        "note": "keep CLI behavior",
    }

    debt = build_debt_payload(
        record_id="DEBT-20260418-abcdef12",
        timestamp="2026-04-18T08:10:00+03:00",
        scope=" tep-plugin-development ",
        title=" Move command handlers ",
        priority="medium",
        status="open",
        evidence_refs=["CLM-20260418-aaaa1111"],
        plan_refs=["PLN-20260418-abcdef12"],
        project_refs=["PROJ-20260418-cccc3333"],
        task_refs=[],
        tags=["tep-core-rewrite"],
        note=" finish later ",
    )
    assert debt == {
        "id": "DEBT-20260418-abcdef12",
        "record_type": "debt",
        "scope": "tep-plugin-development",
        "title": "Move command handlers",
        "status": "open",
        "priority": "medium",
        "evidence_refs": ["CLM-20260418-aaaa1111"],
        "plan_refs": ["PLN-20260418-abcdef12"],
        "project_refs": ["PROJ-20260418-cccc3333"],
        "task_refs": [],
        "created_at": "2026-04-18T08:10:00+03:00",
        "updated_at": "2026-04-18T08:10:00+03:00",
        "tags": ["tep-core-rewrite"],
        "note": "finish later",
    }


def test_action_core_builds_payload_timestamps() -> None:
    planned = build_action_payload(
        record_id="ACT-20260418-abcdef12",
        timestamp="2026-04-18T08:00:00+03:00",
        kind=" core-extraction ",
        scope=" tep-plugin-development ",
        justified_by=["CLM-20260418-aaaa1111"],
        safety_class="safe",
        status="planned",
        planned_at=None,
        executed_at=None,
        project_refs=["PROJ-20260418-bbbb2222"],
        task_refs=[],
        tags=["tep-core-rewrite"],
        note=" extract helper ",
    )
    assert planned == {
        "id": "ACT-20260418-abcdef12",
        "record_type": "action",
        "kind": "core-extraction",
        "scope": "tep-plugin-development",
        "justified_by": ["CLM-20260418-aaaa1111"],
        "safety_class": "safe",
        "status": "planned",
        "project_refs": ["PROJ-20260418-bbbb2222"],
        "task_refs": [],
        "tags": ["tep-core-rewrite"],
        "note": "extract helper",
        "planned_at": "2026-04-18T08:00:00+03:00",
    }

    executed = build_action_payload(
        record_id="ACT-20260418-bcdef123",
        timestamp="2026-04-18T08:10:00+03:00",
        kind="core-extraction",
        scope="tep-plugin-development",
        justified_by=["CLM-20260418-aaaa1111"],
        safety_class="safe",
        status="executed",
        planned_at=" 2026-04-18T08:05:00+03:00 ",
        executed_at=None,
        project_refs=[],
        task_refs=[],
        tags=[],
        note=" done ",
    )
    assert executed["planned_at"] == "2026-04-18T08:05:00+03:00"
    assert executed["executed_at"] == "2026-04-18T08:10:00+03:00"
    assert executed["note"] == "done"

    explicit_execution = build_action_payload(
        record_id="ACT-20260418-cdef1234",
        timestamp="2026-04-18T08:20:00+03:00",
        kind="review",
        scope="tep-plugin-development",
        justified_by=["CLM-20260418-aaaa1111"],
        safety_class="safe",
        status="executed",
        planned_at=None,
        executed_at=" 2026-04-18T08:15:00+03:00 ",
        project_refs=[],
        task_refs=[],
        tags=[],
        note="explicit timestamp",
    )
    assert "planned_at" not in explicit_execution
    assert explicit_execution["executed_at"] == "2026-04-18T08:15:00+03:00"


def test_input_core_builds_prompt_provenance_payload() -> None:
    prompt = "Please remember this testing guideline."
    payload = build_input_payload(
        record_id="INP-20260418-abcdef12",
        scope=" tep-plugin-development ",
        input_kind="user_prompt",
        origin_kind=" codex-hook ",
        origin_ref=" UserPromptSubmit:session-1 ",
        text=prompt,
        artifact_refs=[],
        session_ref=" session-1 ",
        derived_record_refs=["GLD-20260418-aaaa1111"],
        captured_at=None,
        captured_timestamp="2026-04-18T08:00:00+03:00",
        project_refs=["PRJ-20260418-bbbb2222"],
        task_refs=["TASK-20260418-cccc3333"],
        tags=["hook", "user-prompt"],
        note=" captured prompt ",
    )

    assert payload == {
        "id": "INP-20260418-abcdef12",
        "record_type": "input",
        "input_kind": "user_prompt",
        "scope": "tep-plugin-development",
        "captured_at": "2026-04-18T08:00:00+03:00",
        "origin": {"kind": "codex-hook", "ref": "UserPromptSubmit:session-1"},
        "project_refs": ["PRJ-20260418-bbbb2222"],
        "task_refs": ["TASK-20260418-cccc3333"],
        "artifact_refs": [],
        "text": prompt,
        "derived_record_refs": ["GLD-20260418-aaaa1111"],
        "tags": ["hook", "user-prompt"],
        "note": "captured prompt",
        "session_ref": "session-1",
    }
    assert compat_build_input_payload(
        record_id="INP-20260418-bcdef123",
        scope="demo",
        input_kind="tool_payload",
        origin_kind="hook",
        origin_ref="event",
        text="payload",
        artifact_refs=[],
        session_ref=None,
        derived_record_refs=[],
        captured_at="2026-04-18T08:10:00+03:00",
        captured_timestamp="unused",
        project_refs=[],
        task_refs=[],
        tags=[],
        note="compat",
    )["captured_at"] == "2026-04-18T08:10:00+03:00"


def test_source_core_builds_payload_and_default_independence_group() -> None:
    assert (
        default_independence_group("runtime", "2026-04-18T08:00:00+03:00")
        == "runtime-ingest-2026-04-18T080000_0300"
    )

    source = build_source_payload(
        record_id="SRC-20260418-abcdef12",
        source_kind="runtime",
        scope=" tep-plugin-development ",
        critique_status="accepted",
        origin_kind=" command ",
        origin_ref=" pytest ",
        quote=" 77 passed ",
        artifact_refs=["artifact://coverage.txt"],
        confidence="high",
        independence_group=None,
        captured_at=None,
        captured_timestamp="2026-04-18T08:00:00+03:00",
        independence_timestamp="2026-04-18T08:01:00+03:00",
        project_refs=["PROJ-20260418-aaaa1111"],
        task_refs=["TASK-20260418-bbbb2222"],
        tags=["tep-core-rewrite"],
        red_flags=[],
        note=" deterministic run ",
    )
    assert source == {
        "id": "SRC-20260418-abcdef12",
        "record_type": "source",
        "source_kind": "runtime",
        "scope": "tep-plugin-development",
        "captured_at": "2026-04-18T08:00:00+03:00",
        "critique_status": "accepted",
        "independence_group": "runtime-ingest-2026-04-18T080100_0300",
        "origin": {"kind": "command", "ref": "pytest"},
        "project_refs": ["PROJ-20260418-aaaa1111"],
        "task_refs": ["TASK-20260418-bbbb2222"],
        "artifact_refs": ["artifact://coverage.txt"],
        "quote": "77 passed",
        "tags": ["tep-core-rewrite"],
        "red_flags": [],
        "note": "deterministic run",
        "confidence": "high",
    }

    explicit_source = build_source_payload(
        record_id="SRC-20260418-bcdef123",
        source_kind="code",
        scope="tep-plugin-development",
        critique_status="audited",
        origin_kind="file",
        origin_ref="plugin.py",
        quote="",
        artifact_refs=[],
        confidence=None,
        independence_group=" explicit-group ",
        captured_at=" 2026-04-18T09:00:00+03:00 ",
        captured_timestamp="unused",
        independence_timestamp="unused",
        project_refs=[],
        task_refs=[],
        tags=[],
        red_flags=["needs review"],
        note=" explicit fields ",
    )
    assert explicit_source["captured_at"] == "2026-04-18T09:00:00+03:00"
    assert explicit_source["independence_group"] == "explicit-group"
    assert "confidence" not in explicit_source


def test_claim_core_builds_payload_with_optional_blocks() -> None:
    comparison = {"key": "runtime.status", "comparator": "exact", "polarity": "affirmed", "value": "ready"}
    logic = {"atoms": [{"predicate": "Ready", "args": ["runtime:gateway"], "polarity": "affirmed"}]}
    claim = build_claim_payload(
        record_id="CLM-20260418-abcdef12",
        timestamp="2026-04-18T08:00:00+03:00",
        scope=" tep-plugin-development ",
        plane="runtime",
        status="supported",
        statement=" Runtime is ready. ",
        source_refs=["SRC-20260418-aaaa1111"],
        support_refs=["CLM-20260418-bbbb2222"],
        contradiction_refs=[],
        derived_from=[],
        claim_kind="factual",
        confidence="high",
        comparison=comparison,
        logic=logic,
        recorded_at=None,
        project_refs=["PROJ-20260418-cccc3333"],
        task_refs=["TASK-20260418-dddd4444"],
        tags=["tep-core-rewrite"],
        red_flags=[],
        note=" supported by runtime ",
    )
    assert claim == {
        "id": "CLM-20260418-abcdef12",
        "record_type": "claim",
        "plane": "runtime",
        "status": "supported",
        "scope": "tep-plugin-development",
        "statement": "Runtime is ready.",
        "source_refs": ["SRC-20260418-aaaa1111"],
        "support_refs": ["CLM-20260418-bbbb2222"],
        "contradiction_refs": [],
        "derived_from": [],
        "project_refs": ["PROJ-20260418-cccc3333"],
        "task_refs": ["TASK-20260418-dddd4444"],
        "recorded_at": "2026-04-18T08:00:00+03:00",
        "tags": ["tep-core-rewrite"],
        "red_flags": [],
        "note": "supported by runtime",
        "claim_kind": "factual",
        "confidence": "high",
        "comparison": comparison,
        "logic": logic,
    }

    minimal_claim = build_claim_payload(
        record_id="CLM-20260418-bcdef123",
        timestamp="2026-04-18T08:00:00+03:00",
        scope="scope",
        plane="code",
        status="tentative",
        statement="statement",
        source_refs=["SRC-1"],
        support_refs=[],
        contradiction_refs=[],
        derived_from=[],
        claim_kind=None,
        confidence=None,
        comparison=None,
        logic=None,
        recorded_at=" 2026-04-18T09:00:00+03:00 ",
        project_refs=[],
        task_refs=[],
        tags=[],
        red_flags=["needs corroboration"],
        note=" note ",
    )
    assert minimal_claim["recorded_at"] == "2026-04-18T09:00:00+03:00"
    assert minimal_claim["red_flags"] == ["needs corroboration"]
    assert "claim_kind" not in minimal_claim
    assert "confidence" not in minimal_claim
    assert "comparison" not in minimal_claim
    assert "logic" not in minimal_claim


def test_permission_core_resolves_scope_and_builds_payload() -> None:
    assert resolve_permission_scope(None, [], [], None, None) == ("global", [], [])
    assert resolve_permission_scope(None, ["PROJ-20260418-aaaa1111"], [], None, None) == (
        "project",
        ["PROJ-20260418-aaaa1111"],
        [],
    )
    assert resolve_permission_scope("project", [], [], "PROJ-20260418-bbbb2222", None) == (
        "project",
        ["PROJ-20260418-bbbb2222"],
        [],
    )
    assert resolve_permission_scope("task", [], [], "PROJ-20260418-bbbb2222", "TASK-20260418-cccc3333") == (
        "task",
        [],
        ["TASK-20260418-cccc3333"],
    )

    permission = build_permission_payload(
        record_id="PRM-20260418-abcdef12",
        timestamp="2026-04-18T08:00:00+03:00",
        scope=" tep-plugin-development ",
        applies_to="project",
        granted_by=" user ",
        grants=["allowed_freedom:implementation-choice"],
        project_refs=["PROJ-20260418-aaaa1111"],
        task_refs=[],
        granted_at=None,
        tags=["tep-core-rewrite"],
        note=" bounded permission ",
    )
    assert permission == {
        "id": "PRM-20260418-abcdef12",
        "record_type": "permission",
        "scope": "tep-plugin-development",
        "applies_to": "project",
        "granted_by": "user",
        "granted_at": "2026-04-18T08:00:00+03:00",
        "grants": ["allowed_freedom:implementation-choice"],
        "project_refs": ["PROJ-20260418-aaaa1111"],
        "task_refs": [],
        "tags": ["tep-core-rewrite"],
        "note": "bounded permission",
    }

    explicit_grant_time = build_permission_payload(
        record_id="PRM-20260418-bcdef123",
        timestamp="unused",
        scope="scope",
        applies_to="global",
        granted_by="agent",
        grants=["records:write"],
        project_refs=[],
        task_refs=[],
        granted_at=" 2026-04-18T09:00:00+03:00 ",
        tags=[],
        note="note",
    )
    assert explicit_grant_time["granted_at"] == "2026-04-18T09:00:00+03:00"


def test_restriction_core_resolves_scope_and_builds_payload() -> None:
    assert resolve_restriction_scope("global", [], [], None, None) == ([], [])
    assert resolve_restriction_scope("project", [], [], "PROJ-20260418-aaaa1111", None) == (
        ["PROJ-20260418-aaaa1111"],
        [],
    )
    assert resolve_restriction_scope("task", [], [], "PROJ-20260418-aaaa1111", "TASK-20260418-bbbb2222") == (
        [],
        ["TASK-20260418-bbbb2222"],
    )

    restriction = build_restriction_payload(
        record_id="RST-20260418-abcdef12",
        timestamp="2026-04-18T08:00:00+03:00",
        scope=" tep-plugin-development ",
        title=" No unsafe edits ",
        applies_to="task",
        severity="hard",
        rules=["ask before destructive commands"],
        project_refs=[],
        task_refs=["TASK-20260418-bbbb2222"],
        related_claim_refs=["CLM-20260418-aaaa1111"],
        supersedes_refs=["RST-20260418-cccc3333"],
        imposed_by=" user ",
        imposed_at=None,
        tags=["tep-core-rewrite"],
        note=" bounded restriction ",
    )
    assert restriction == {
        "id": "RST-20260418-abcdef12",
        "record_type": "restriction",
        "scope": "tep-plugin-development",
        "title": "No unsafe edits",
        "status": "active",
        "applies_to": "task",
        "severity": "hard",
        "rules": ["ask before destructive commands"],
        "project_refs": [],
        "task_refs": ["TASK-20260418-bbbb2222"],
        "related_claim_refs": ["CLM-20260418-aaaa1111"],
        "supersedes_refs": ["RST-20260418-cccc3333"],
        "imposed_by": "user",
        "imposed_at": "2026-04-18T08:00:00+03:00",
        "created_at": "2026-04-18T08:00:00+03:00",
        "updated_at": "2026-04-18T08:00:00+03:00",
        "tags": ["tep-core-rewrite"],
        "note": "bounded restriction",
    }

    explicit_imposed_time = build_restriction_payload(
        record_id="RST-20260418-bcdef123",
        timestamp="2026-04-18T08:00:00+03:00",
        scope="scope",
        title="title",
        applies_to="global",
        severity="warning",
        rules=["rule"],
        project_refs=[],
        task_refs=[],
        related_claim_refs=[],
        supersedes_refs=[],
        imposed_by="agent",
        imposed_at=" 2026-04-18T09:00:00+03:00 ",
        tags=[],
        note="note",
    )
    assert explicit_imposed_time["imposed_at"] == "2026-04-18T09:00:00+03:00"
    assert explicit_imposed_time["created_at"] == "2026-04-18T08:00:00+03:00"


def test_guideline_core_resolves_scope_and_builds_payload() -> None:
    assert resolve_guideline_scope("global", [], [], None, None) == ([], [])
    assert resolve_guideline_scope("project", [], [], "PROJ-20260418-aaaa1111", None) == (
        ["PROJ-20260418-aaaa1111"],
        [],
    )
    assert resolve_guideline_scope("task", [], [], "PROJ-20260418-aaaa1111", "TASK-20260418-bbbb2222") == (
        [],
        ["TASK-20260418-bbbb2222"],
    )

    guideline = build_guideline_payload(
        record_id="GLD-20260418-abcdef12",
        timestamp="2026-04-18T08:00:00+03:00",
        scope=" tep-plugin-development ",
        domain="code",
        applies_to="task",
        priority="high",
        rule=" Cite guideline before large edits. ",
        source_refs=["SRC-20260418-aaaa1111"],
        project_refs=[],
        task_refs=["TASK-20260418-bbbb2222"],
        related_claim_refs=["CLM-20260418-cccc3333"],
        conflict_refs=[],
        supersedes_refs=["GLD-20260418-dddd4444"],
        examples=["show id + quote"],
        rationale=" Keep edits auditable. ",
        tags=["tep-core-rewrite"],
        note=" guideline builder ",
    )
    assert guideline == {
        "id": "GLD-20260418-abcdef12",
        "record_type": "guideline",
        "scope": "tep-plugin-development",
        "domain": "code",
        "status": "active",
        "applies_to": "task",
        "priority": "high",
        "rule": "Cite guideline before large edits.",
        "rationale": "Keep edits auditable.",
        "source_refs": ["SRC-20260418-aaaa1111"],
        "project_refs": [],
        "task_refs": ["TASK-20260418-bbbb2222"],
        "related_claim_refs": ["CLM-20260418-cccc3333"],
        "conflict_refs": [],
        "supersedes_refs": ["GLD-20260418-dddd4444"],
        "examples": ["show id + quote"],
        "created_at": "2026-04-18T08:00:00+03:00",
        "updated_at": "2026-04-18T08:00:00+03:00",
        "tags": ["tep-core-rewrite"],
        "note": "guideline builder",
    }

    empty_rationale = build_guideline_payload(
        record_id="GLD-20260418-bcdef123",
        timestamp="2026-04-18T08:00:00+03:00",
        scope="scope",
        domain="tests",
        applies_to="global",
        priority="medium",
        rule="rule",
        source_refs=["SRC-1"],
        project_refs=[],
        task_refs=[],
        related_claim_refs=[],
        conflict_refs=[],
        supersedes_refs=[],
        examples=[],
        rationale=None,
        tags=[],
        note="note",
    )
    assert empty_rationale["rationale"] == ""


def test_conflict_core_validates_comparisons_and_reports_disagreements(tmp_path: Path) -> None:
    assert build_comparison_payload(
        SimpleNamespace(
            comparison_key=None,
            comparison_subject=None,
            comparison_aspect=None,
            comparison_comparator=None,
            comparison_value=None,
            comparison_polarity=None,
            comparison_context_scope=None,
        )
    ) is None

    boolean_payload = build_comparison_payload(
        SimpleNamespace(
            comparison_key=" runtime.gateway.ready ",
            comparison_subject=" gateway ",
            comparison_aspect=" ready ",
            comparison_comparator="boolean",
            comparison_value="true",
            comparison_polarity="affirmed",
            comparison_context_scope=" pytest ",
        )
    )
    assert boolean_payload == {
        "key": "runtime.gateway.ready",
        "subject": "gateway",
        "aspect": "ready",
        "comparator": "boolean",
        "value": True,
        "polarity": "affirmed",
        "context_scope": "pytest",
    }

    try:
        build_comparison_payload(
            SimpleNamespace(
                comparison_key="runtime.gateway.ready",
                comparison_subject=None,
                comparison_aspect="ready",
                comparison_comparator="boolean",
                comparison_value="maybe",
                comparison_polarity="affirmed",
                comparison_context_scope=None,
            )
        )
    except ValueError as exc:
        assert "incomplete comparison payload; missing comparison.subject" in str(exc)
    else:
        raise AssertionError("build_comparison_payload accepted an incomplete comparison")

    comparison = {
        "key": "runtime.gateway.status",
        "subject": "gateway",
        "aspect": "status",
        "comparator": "exact",
        "polarity": "affirmed",
        "value": "ready",
        "context_scope": "pytest",
    }
    assert validate_claim_comparison(comparison) == []
    assert comparison_signature(comparison) == 'affirmed:"ready"'
    assert comparison_signature({"comparator": "boolean", "polarity": "denied", "value": False}) == "denied:false"

    invalid_messages = validate_claim_comparison(
        {"key": "", "subject": "", "aspect": "", "comparator": "boolean", "polarity": "maybe", "value": "yes"}
    )
    assert "comparison.key is required" in invalid_messages
    assert "comparison.subject is required" in invalid_messages
    assert "comparison.aspect is required" in invalid_messages
    assert "comparison.polarity must be affirmed or denied" in invalid_messages
    assert "comparison.value must be boolean when comparator=boolean" in invalid_messages

    root = tmp_path / ".codex_context"
    records = {
        "CLM-20260418-aaaa1111": {
            "_path": root / "records" / "claim" / "CLM-20260418-aaaa1111.json",
            "id": "CLM-20260418-aaaa1111",
            "record_type": "claim",
            "status": "supported",
            "comparison": comparison,
        },
        "CLM-20260418-bbbb2222": {
            "_path": root / "records" / "claim" / "CLM-20260418-bbbb2222.json",
            "id": "CLM-20260418-bbbb2222",
            "record_type": "claim",
            "status": "supported",
            "comparison": {**comparison, "value": "down"},
        },
        "CLM-20260418-cccc3333": {
            "_path": root / "records" / "claim" / "CLM-20260418-cccc3333.json",
            "id": "CLM-20260418-cccc3333",
            "record_type": "claim",
            "status": "contested",
        },
        "CLM-20260418-dddd4444": {
            "_path": root / "records" / "claim" / "CLM-20260418-dddd4444.json",
            "id": "CLM-20260418-dddd4444",
            "record_type": "claim",
            "status": "supported",
            "contradiction_refs": ["CLM-20260418-cccc3333"],
        },
    }
    lines = collect_conflict_lines(root, records)
    rendered = "".join(lines)
    assert "comparable claims disagree for key `runtime.gateway.status`, context `pytest`, comparator `exact`" in rendered
    assert "contested claim missing contradiction_refs" in rendered
    assert "contradiction_refs present but status is supported" in rendered

    report_lines = write_conflicts_report(root, records)
    assert report_lines == lines
    assert "Generated Conflict Review" in (root / "review" / "conflicts.md").read_text(encoding="utf-8")


def test_code_ast_language_analyzers_are_split_and_reexported() -> None:
    python_analysis = language_analyze_python(
        "import pytest\n"
        "from pathlib import Path\n"
        "\n"
        "class Page:\n"
        "    pass\n"
        "\n"
        "@pytest.fixture\n"
        "async def test_page():\n"
        "    return Path('.')\n"
    )
    assert python_analysis["imports"] == ["pathlib", "pytest"]
    assert python_analysis["classes"] == ["Page"]
    assert python_analysis["tests"] == ["test_page"]
    assert "pytest.fixture" in python_analysis["decorators"]

    js_analysis = language_analyze_js_like(
        "import { test } from '@playwright/test';\n"
        "class CheckoutPage {}\n"
        "const chooseProduct = async () => true;\n"
        "test('chooses product', async () => {});\n"
    )
    assert js_analysis["imports"] == ["@playwright/test"]
    assert js_analysis["classes"] == ["CheckoutPage"]
    assert js_analysis["functions"] == ["chooseProduct"]
    assert js_analysis["tests"] == ["chooses product"]
    markdown_analysis = language_analyze_markdown(
        "# TEP Runtime\n"
        "\n"
        "See [commands](workflows/plugin-commands.md).\n"
        "\n"
        "## Install\n"
        "\n"
        "```bash\n"
        "uv run pytest -q\n"
        "```\n"
    )
    assert markdown_analysis["headings"] == [
        {"level": 1, "title": "TEP Runtime", "anchor": "tep-runtime", "line": 1},
        {"level": 2, "title": "Install", "anchor": "install", "line": 5},
    ]
    assert markdown_analysis["links"] == [
        {"text": "commands", "target": "workflows/plugin-commands.md", "line": 3}
    ]
    assert markdown_analysis["code_blocks"] == [{"language": "bash", "line_start": 7, "line_end": 9}]
    assert empty_analysis()["parse_error"] == ""
    assert analyze_python is language_analyze_python
    assert analyze_js_like is language_analyze_js_like
    assert analyze_markdown is language_analyze_markdown


def test_code_index_core_analyzes_projects_and_projects_entries(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    source_path = repo_root / "src" / "app.py"
    source_path.parent.mkdir(parents=True)
    source_path.write_text(
        "import pytest\n"
        "import requests\n"
        "\n"
        "class AppPage:\n"
        "    pass\n"
        "\n"
        "@pytest.fixture\n"
        "def fixture_value():\n"
        "    return 1\n"
        "\n"
        "def test_app():\n"
        "    assert fixture_value() == 1\n",
        encoding="utf-8",
    )

    analyzed = analyze_code_file(repo_root, source_path, max_bytes=4096)
    assert analyzed["target"] == {"kind": "file", "path": "src/app.py"}
    assert analyzed["language"] == "python"
    assert analyzed["metadata"]["imports"] == ["pytest", "requests"]
    assert "AppPage" in analyzed["metadata"]["classes"]
    assert {"assertions", "fixtures", "network", "pytest"} <= set(analyzed["detected_features"])

    docs_path = repo_root / "docs" / "guide.md"
    docs_path.parent.mkdir()
    docs_path.write_text(
        "# Guide\n"
        "\n"
        "Read [README](../README.md).\n"
        "\n"
        "```python\n"
        "print('example')\n"
        "```\n",
        encoding="utf-8",
    )
    docs_analysis = analyze_code_file(repo_root, docs_path, max_bytes=4096)
    assert docs_analysis["language"] == "markdown"
    assert docs_analysis["code_kind"] == "docs"
    assert docs_analysis["metadata"]["headings"] == [
        {"level": 1, "title": "Guide", "anchor": "guide", "line": 1}
    ]
    assert docs_analysis["metadata"]["links"] == [
        {"text": "README", "target": "../README.md", "line": 3}
    ]
    assert docs_analysis["metadata"]["code_blocks"] == [
        {"language": "python", "line_start": 5, "line_end": 7}
    ]
    assert {"code-blocks", "links", "markdown", "outline"} <= set(docs_analysis["detected_features"])

    entry, created = code_index_entry_for_file(tmp_path / ".codex_context", {}, repo_root, source_path, max_bytes=4096)
    assert created is True
    assert entry["record_type"] == "code_index_entry"
    assert entry["summary"] == "source src/app.py"
    manual_entry = build_manual_code_index_entry(
        entry_id="CIX-20260418-abcdef12",
        timestamp="2026-04-18T08:00:00+03:00",
        target_kind="symbol",
        path=" src/app.py ",
        name=" App area ",
        symbol_name=" AppPage ",
        summary=" Manual symbol entry. ",
        manual_features=["pytest"],
        note=" manual note ",
    )
    assert manual_entry == {
        "id": "CIX-20260418-abcdef12",
        "record_type": "code_index_entry",
        "status": "active",
        "target": {"kind": "symbol", "path": "src/app.py", "name": "App area", "symbol_name": "AppPage"},
        "target_state": "unknown",
        "language": "",
        "code_kind": "symbol",
        "summary": "Manual symbol entry.",
        "metadata": {},
        "detected_features": [],
        "manual_features": ["pytest"],
        "manual_links": {},
        "annotations": [],
        "links": [],
        "child_entry_refs": [],
        "related_entry_refs": [],
        "supersedes_refs": [],
        "created_at": "2026-04-18T08:00:00+03:00",
        "updated_at": "2026-04-18T08:00:00+03:00",
        "note": "manual note",
    }
    assert build_manual_code_index_entry(
        "CIX-20260418-bcdef123",
        "2026-04-18T08:00:00+03:00",
        "file",
        None,
        None,
        None,
        "File entry",
        [],
        "",
    )["target_state"] == "present"
    assert "_path" not in public_code_index_entry({"id": "CIX-1", "_path": "/tmp/x"})
    assert resolve_code_entry({entry["id"]: entry}, None, "src/app.py")["id"] == entry["id"]

    assert parse_code_fields(None) == ["target", "summary", "features", "freshness"]
    projected = project_code_entry(entry, ["target", "imports", "symbols", "features", "hash"], repo_root)
    assert projected["imports"] == ["pytest", "requests"]
    assert projected["symbols"]["classes"] == ["AppPage"]
    assert projected["hash"]["sha256"] == entry["metadata"]["sha256"]
    code_lines = code_entries_text_lines([entry], ["target", "imports", "symbols", "features", "hash"], repo_root)
    assert code_lines[0:3] == [
        "# Code Index Results",
        "",
        f"- `{entry['id']}` status=`active` target=`src/app.py`",
    ]
    assert '  imports: ["pytest", "requests"]' in code_lines

    annotation = {
        "id": "ANN-1",
        "kind": "smell",
        "status": "active",
        "categories": ["mixed-responsibility"],
        "severity": "high",
        "text": "Helper mixes multiple responsibilities.",
        "suggestions": ["Split rendering from filtering."],
        **annotation_snapshot(entry),
    }
    stale_rows = code_smell_rows(repo_root, {entry["id"]: {**entry, "annotations": [annotation]}}, ["mixed-responsibility"], ["high"], include_stale=False)
    assert len(stale_rows) == 1
    smell_payload = code_smell_report_payload(stale_rows, ["mixed-responsibility"], ["high"], include_stale=False)
    assert smell_payload["results"][0]["entry"]["target"] == {"kind": "file", "path": "src/app.py"}
    assert smell_payload["results"][0]["freshness"]["stale"] is False
    smell_lines = code_smell_report_text_lines(stale_rows)
    assert smell_lines == [
        "# Code Smell Report",
        "",
        "Mode: read-only. CIX smell annotations are navigation/critique, not proof or hard rules.",
        "",
        f"- `{entry['id']}` target=`src/app.py` severity=`high` categories=['mixed-responsibility']: Helper mixes multiple responsibilities.",
        '  suggestions: ["Split rendering from filtering."]',
    ]
    source_path.write_text("def changed():\n    return 2\n", encoding="utf-8")
    assert code_smell_rows(repo_root, {entry["id"]: {**entry, "annotations": [annotation]}}, ["mixed-responsibility"], ["high"], include_stale=False) == []
    assert normalize_smell_categories(["mixed-responsibility", "custom:local-pattern"])[0] == [
        "custom:local-pattern",
        "mixed-responsibility",
    ]

    context_root = tmp_path / ".codex_context"
    write_code_index_views(context_root, {entry["id"]: {**entry, "manual_links": {"claim_refs": ["CLM-1"]}}})
    assert json.loads((context_root / "code_index" / "by_path.json").read_text(encoding="utf-8")) == {
        "src/app.py": [entry["id"]]
    }
    assert json.loads((context_root / "code_index" / "by_ref.json").read_text(encoding="utf-8")) == {"CLM-1": [entry["id"]]}


def test_code_index_core_validates_entries_and_state(tmp_path: Path) -> None:
    entry_id = "CIX-20260418-abcdef12"
    claim_id = "CLM-20260418-abcdef12"
    source_id = "SRC-20260418-abcdef12"
    path = tmp_path / ".codex_context" / "code_index" / "entries" / f"{entry_id}.json"
    records = {
        claim_id: {"id": claim_id, "record_type": "claim"},
        source_id: {"id": source_id, "record_type": "source"},
    }
    entry = {
        "_path": path,
        "id": entry_id,
        "record_type": "code_index_entry",
        "status": "active",
        "target_state": "present",
        "target": {"kind": "file", "path": "src/app.py"},
        "manual_links": {"claim_refs": [claim_id]},
        "annotations": [
            {
                "id": "ann-1",
                "kind": "smell",
                "status": "active",
                "text": "Mixed responsibility.",
                "confidence": "high",
                "categories": ["mixed-responsibility"],
                "severity": "low",
                "source_refs": [source_id],
                "suggestions": ["Split responsibilities."],
            }
        ],
        "links": [{"id": "link-1", "status": "active", "ref_key": "claim_refs", "ref": claim_id}],
    }

    assert validate_code_index_entry(entry_id, entry, records, {entry_id: entry}) == []

    invalid = dict(entry)
    invalid.update(
        {
            "status": "unknown",
            "target": {"kind": "symbol", "path": "src/app.py"},
            "manual_links": {"claim_refs": [source_id]},
            "annotations": [{"id": "ann-1", "kind": "smell", "text": "", "categories": [], "severity": "critical"}],
            "links": [{"id": "link-1", "ref_key": "claim_refs", "ref": source_id}],
        }
    )
    messages = [error.message for error in validate_code_index_entry(entry_id, invalid, records, {entry_id: invalid})]
    assert "status must be active, missing, superseded, or archived" in messages
    assert "target.kind=symbol requires target.path and target.symbol_name" in messages
    assert f"manual_links.claim_refs ref {source_id} must reference claim" in messages
    assert "smell annotation.categories must be a non-empty list" in messages
    assert "critical smell annotation requires at least one claim_ref" in messages
    assert f"link ref {source_id} must reference claim" in messages

    root = tmp_path / ".codex_context"
    write_json_file(code_index_entry_path(root, entry_id), {key: value for key, value in entry.items() if key != "_path"})
    working_context_id = "WCTX-20260418-abcdef12"
    state_records = {
        working_context_id: {
            "_path": root / "records" / "working_context" / f"{working_context_id}.json",
            "id": working_context_id,
            "record_type": "working_context",
            "pinned_refs": ["CIX-20260418-deadbeef"],
            "code_index_refs": [entry_id],
        },
        "CLM-20260418-badbad00": {
            "_path": root / "records" / "claim" / "CLM-20260418-badbad00.json",
            "id": "CLM-20260418-badbad00",
            "record_type": "claim",
            "code_index_refs": [entry_id],
        },
    }
    state_messages = [error.message for error in validate_code_index_state(root, state_records)]
    assert "missing pinned code index ref: CIX-20260418-deadbeef" in state_messages
    assert "code_index_refs are not allowed for this record_type" in state_messages


def test_logic_core_parses_cli_specs_and_json_payload(tmp_path: Path) -> None:
    symbol = parse_logic_symbol_spec("person:alice|entity|Alice test person|seeded by unit test")
    assert symbol == {
        "symbol": "person:alice",
        "kind": "entity",
        "meaning": "Alice test person",
        "note": "seeded by unit test",
    }

    atom = parse_logic_atom_spec("Status|person:alice|affirmed|value=student|context=scope=unit;fresh=true|functional")
    assert atom == {
        "predicate": "Status",
        "args": ["person:alice"],
        "polarity": "affirmed",
        "value": "student",
        "context": {"scope": "unit", "fresh": True},
        "functional": True,
    }
    assert parse_logic_atom_spec("Visible|system:ui|affirmed|functional=false")["functional"] is False
    assert parse_logic_atom_expression("Studies(?x, course:math)") == {
        "predicate": "Studies",
        "args": ["?x", "course:math"],
        "polarity": "affirmed",
    }
    assert parse_logic_rule_spec("pass-rule|Student(?x)&Studies(?x,course:math)->PassesExam(?x)") == {
        "name": "pass-rule",
        "body": [
            {"predicate": "Student", "args": ["?x"], "polarity": "affirmed"},
            {"predicate": "Studies", "args": ["?x", "course:math"], "polarity": "affirmed"},
        ],
        "head": {"predicate": "PassesExam", "args": ["?x"], "polarity": "affirmed"},
    }

    logic_file = tmp_path / "logic.json"
    logic_file.write_text(
        json.dumps({"atoms": [{"predicate": "Seed", "args": ["person:alice"], "polarity": "affirmed"}]}),
        encoding="utf-8",
    )
    payload = load_logic_json_payload(f"@{logic_file}")
    assert payload["atoms"][0]["predicate"] == "Seed"

    merged = build_logic_payload(
        SimpleNamespace(
            logic_json=f"@{logic_file}",
            logic_atoms=["Status|person:alice|affirmed|value=student"],
            logic_symbols=["person:alice|entity|Alice"],
            logic_rules=["pass-rule|Student(?x)->PassesExam(?x)"],
        )
    )
    assert [item["predicate"] for item in merged["atoms"]] == ["Seed", "Status"]
    assert merged["symbols"] == [{"symbol": "person:alice", "kind": "entity", "meaning": "Alice"}]
    assert merged["rules"][0]["name"] == "pass-rule"
    assert build_logic_payload(SimpleNamespace(logic_json=None, logic_atoms=[], logic_symbols=[], logic_rules=[])) is None

    assert parse_bool_token("true") is True
    assert parse_scalar_token("null") is None
    assert parse_logic_context("attempt=3;enabled=false") == {"attempt": 3, "enabled": False}
    for parser, raw, message in (
        (parse_logic_symbol_spec, "bad|entity|Bad", "invalid logic symbol"),
        (parse_logic_atom_spec, "1Bad|person:alice", "invalid logic predicate"),
        (parse_logic_rule_spec, "bad-rule|Student(?x)", "--logic-rule must be"),
    ):
        try:
            parser(raw)
        except ValueError as exc:
            assert message in str(exc)
        else:
            raise AssertionError(f"{parser.__name__} accepted invalid input")


def test_logic_core_validates_claim_logic_and_state(tmp_path: Path) -> None:
    valid_logic = {
        "symbols": [{"symbol": "person:alice", "kind": "entity", "meaning": "Alice"}],
        "atoms": [{"predicate": "Student", "args": ["person:alice"], "polarity": "affirmed"}],
    }
    assert validate_claim_logic(valid_logic) == []
    assert logic_atom_symbols(valid_logic["atoms"][0]) == {"person:alice"}
    assert logic_atom_variables({"predicate": "Student", "args": ["?x"]}) == {"?x"}

    invalid_logic = {
        "symbols": [
            {"symbol": "person:alice", "kind": "entity"},
            {"symbol": "person:alice", "kind": "entity"},
        ],
        "atoms": [{"predicate": "Student", "args": ["?x"], "polarity": "unknown", "value": []}],
        "rules": [
            {
                "name": "bad-rule",
                "body": [{"predicate": "Student", "args": ["?x"]}],
                "head": {"predicate": "Passes", "args": ["?y"]},
            }
        ],
    }
    claim_logic_messages = validate_claim_logic(invalid_logic)
    assert "logic.symbols[2].symbol duplicates person:alice" in claim_logic_messages
    assert "logic.atoms[1].args[1] cannot be a variable outside logic.rules" in claim_logic_messages
    assert "logic.atoms[1].polarity must be affirmed or denied" in claim_logic_messages
    assert "logic.atoms[1].value must be scalar when provided" in claim_logic_messages
    assert "logic.rules[1].head has unbound variables: ?y" in claim_logic_messages

    root = tmp_path / ".codex_context"
    records = {
        "CLM-20260418-intro111": {
            "_path": root / "records" / "claim" / "CLM-20260418-intro111.json",
            "id": "CLM-20260418-intro111",
            "record_type": "claim",
            "status": "supported",
            "logic": {"symbols": [{"symbol": "person:alice", "kind": "entity"}]},
        },
        "CLM-20260418-okatom11": {
            "_path": root / "records" / "claim" / "CLM-20260418-okatom11.json",
            "id": "CLM-20260418-okatom11",
            "record_type": "claim",
            "status": "supported",
            "logic": {"atoms": [{"predicate": "Student", "args": ["person:alice"]}]},
        },
        "CLM-20260418-tent111": {
            "_path": root / "records" / "claim" / "CLM-20260418-tent111.json",
            "id": "CLM-20260418-tent111",
            "record_type": "claim",
            "status": "tentative",
            "logic": {"symbols": [{"symbol": "person:bob", "kind": "entity"}]},
        },
        "CLM-20260418-badatom1": {
            "_path": root / "records" / "claim" / "CLM-20260418-badatom1.json",
            "id": "CLM-20260418-badatom1",
            "record_type": "claim",
            "status": "supported",
            "logic": {
                "atoms": [
                    {"predicate": "Student", "args": ["person:bob"]},
                    {"predicate": "Student", "args": ["person:carol"]},
                ]
            },
        },
    }
    state_messages = [error.message for error in validate_logic_state(root, records)]
    assert "logic.atoms[1] symbol lacks supported/corroborated introduction: person:bob" in state_messages
    assert "logic.atoms[2] references unknown symbol: person:carol" in state_messages


def test_logic_index_core_builds_generated_payload_candidates_and_reports(tmp_path: Path) -> None:
    root = tmp_path / ".codex_context"
    claim_a = "CLM-20260418-logic111"
    claim_b = "CLM-20260418-logic222"
    claim_rule = "CLM-20260418-logic333"
    records = {
        claim_a: {
            "id": claim_a,
            "record_type": "claim",
            "status": "supported",
            "statement": "Alice status is student.",
            "source_refs": ["SRC-1"],
            "logic": {
                "symbols": [
                    {"symbol": "person:alice", "kind": "entity", "meaning": "Alice"},
                    {"symbol": "person:Alice", "kind": "entity", "meaning": "Alias Alice"},
                    {"symbol": "person:unused", "kind": "entity", "meaning": "Unused person"},
                ],
                "atoms": [
                    {
                        "predicate": "Status",
                        "args": ["person:alice"],
                        "polarity": "affirmed",
                        "value": "student",
                        "functional": True,
                        "context": {"scope": "unit"},
                    }
                ],
            },
        },
        claim_b: {
            "id": claim_b,
            "record_type": "claim",
            "status": "supported",
            "statement": "Alice status is graduate.",
            "source_refs": ["SRC-2"],
            "logic": {
                "atoms": [
                    {
                        "predicate": "Status",
                        "args": ["person:alice"],
                        "polarity": "affirmed",
                        "value": "graduate",
                        "functional": True,
                        "context": {"scope": "unit"},
                    }
                ],
            },
        },
        claim_rule: {
            "id": claim_rule,
            "record_type": "claim",
            "status": "supported",
            "statement": "Students pass exams.",
            "source_refs": ["SRC-3"],
            "logic": {
                "rules": [
                    {
                        "name": "student-pass",
                        "body": [{"predicate": "Student", "args": ["?x"]}],
                        "head": {"predicate": "PassesExam", "args": ["?x"]},
                    }
                ],
            },
        },
    }

    payload = build_logic_index_payload(records)
    assert len(payload["atoms"]) == 2
    assert payload["by_predicate"]["Status"] == [f"{claim_a}#atom-1", f"{claim_b}#atom-1"]
    assert payload["by_symbol"]["person:alice"] == [f"{claim_a}#atom-1", f"{claim_b}#atom-1"]

    variables = logic_rule_variables(payload["rules"][0])
    assert variables["?x"]["sections"] == ["body", "head"]

    candidates = logic_conflict_candidates_from_payload(payload, limit=5)
    assert candidates[0]["reason"] == "different affirmed values for functional predicate/args/context"
    assert candidates[0]["logic_index_is_proof"] is False
    structural_payload = structural_logic_check_payload(payload, candidates, "auto")
    assert structural_payload["solver"] == "structural"
    assert structural_payload["candidate_count"] == 1
    assert structural_payload["solver_warning"] == "z3-solver is not installed; auto fell back to structural"
    assert effective_logic_solver(root, "z3") == "z3"
    assert effective_logic_solver(root, None) == "structural"
    assert logic_solver_settings(root)["backend"] == "structural"
    structural_lines = structural_logic_check_text_lines(payload, candidates, "structural", "TEP")
    assert structural_lines[0:5] == [
        "# TEP Logic Check",
        "",
        "Mode: read-only predicate consistency check. Not proof.",
        "",
        "- atoms: 2",
    ]
    assert "`CLM-20260418-logic111` <-> `CLM-20260418-logic222`" in structural_lines[-1]
    assert "- solver warning: z3-solver is not installed; auto fell back to structural" in structural_logic_check_text_lines(
        payload,
        candidates,
        "auto",
        "TEP",
    )
    assert z3_logic_check_text_lines(
        {"available": False, "error": "z3-solver is not installed"},
        candidates,
        "TEP",
    ) == [
        "# TEP Logic Check",
        "",
        "Mode: Z3-backed system consistency candidate check. Not proof.",
        "",
        "- solver: z3 unavailable (z3-solver is not installed)",
        "- structural fallback candidates: 1",
    ]
    z3_lines = z3_logic_check_text_lines(
        {
            "available": True,
            "result": "unsat",
            "closure": "rules",
            "atom_count": 2,
            "derived_atom_count": 1,
            "rule_count": 1,
            "candidate_count": 1,
            "candidates": [
                {
                    "kind": "opposite-polarity",
                    "reason": "demo conflict",
                    "claims": [{"claim_ref": claim_a, "roles": ["asserting_claim"], "logic_refs": [f"{claim_a}#atom-1"]}],
                    "derived_atoms": [{"id": "derived-1", "predicate": "PassesExam", "args": ["person:alice"]}],
                }
            ],
        },
        [],
        "TEP",
    )
    assert "- solver: z3" in z3_lines
    assert f"  - `{claim_a}` roles=`asserting_claim` logic_refs=`{claim_a}#atom-1`" in z3_lines
    assert "  - `derived-1` PassesExam(person:alice)" in z3_lines
    assert z3_lines[-1] == "These claims participate in an inconsistent formal snapshot; inspect underlying SRC-* before changing claim status."

    graph = build_logic_vocabulary_graph(payload)
    smell_kinds = {smell["kind"] for smell in graph["smells"]}
    assert {"duplicate-like-symbol", "generic-rule-variable", "orphan-symbol"} <= smell_kinds
    assert graph["logic_graph_is_proof"] is False

    write_logic_index_reports(root, payload, candidates)
    assert load_logic_index_payload(root)["atoms"] == payload["atoms"]
    assert load_logic_vocabulary_graph(root)["logic_graph_is_proof"] is False
    assert "Logic Index Summary" in (root / "logic_index" / "summary.md").read_text(encoding="utf-8")
    assert "Candidates are not proof" in (root / "logic_index" / "conflict_candidates.md").read_text(encoding="utf-8")
    assert "Generated pressure report" in (root / "logic_index" / "vocabulary_smells.md").read_text(encoding="utf-8")


def test_atomic_json_io_and_write_lock(tmp_path: Path) -> None:
    path = tmp_path / "nested" / "payload.json"
    payload = {"kind": "demo", "value": 1}

    write_json_file(path, payload)
    assert parse_json_file(path) == payload
    assert path.read_text(encoding="utf-8").endswith("\n")

    bad = tmp_path / "array.json"
    bad.write_text("[1, 2, 3]", encoding="utf-8")
    try:
        parse_json_file(bad)
    except ValueError as exc:
        assert str(exc) == "record must be a JSON object"
    else:
        raise AssertionError("parse_json_file accepted a non-object payload")

    with context_write_lock(tmp_path / ".codex_context"):
        assert (tmp_path / ".codex_context" / "runtime" / "write.lock").exists()


def test_context_root_resolver_prefers_explicit_env_global_then_legacy(tmp_path: Path, monkeypatch) -> None:
    explicit = tmp_path / "explicit-context"
    assert resolve_context_root(str(explicit), start=tmp_path) == explicit.resolve()

    env_root = tmp_path / "env-context"
    monkeypatch.setenv(TEP_CONTEXT_ENV, str(env_root))
    assert resolve_context_root(start=tmp_path) == env_root.resolve()
    monkeypatch.delenv(TEP_CONTEXT_ENV)

    home = tmp_path / "home"
    monkeypatch.setattr(Path, "home", lambda: home)
    global_root = home / ".tep_context"
    assert global_context_root() == global_root.resolve()
    global_root.mkdir(parents=True)
    legacy = tmp_path / "repo" / ".codex_context"
    legacy.mkdir(parents=True)
    assert resolve_context_root(start=legacy.parent) == global_root.resolve()

    global_root.rmdir()
    assert find_legacy_context_root(legacy.parent) == legacy.resolve()
    assert resolve_context_root(start=legacy.parent) == legacy.resolve()

    legacy.rmdir()
    assert resolve_context_root(start=tmp_path) == global_root.resolve()
    assert resolve_context_root(start=tmp_path, require_exists=True) is None


def test_context_root_resolver_uses_local_tep_anchor_before_global(tmp_path: Path, monkeypatch) -> None:
    home = tmp_path / "home"
    monkeypatch.setattr(Path, "home", lambda: home)
    global_root = home / ".tep_context"
    global_root.mkdir(parents=True)
    anchored_root = tmp_path / "anchored-context"
    anchored_root.mkdir()
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    write_json_file(
        workspace / ".tep",
        {
            "schema_version": 1,
            "context_root": str(anchored_root),
            "workspace_ref": "WSP-20260418-abcdef12",
            "project_ref": "PRJ-20260418-abcdef12",
            "settings": {"allowed_freedom": "proof-only"},
        },
    )

    assert resolve_context_root(start=workspace) == anchored_root.resolve()
    assert resolve_context_root(start=workspace, require_exists=True) == anchored_root.resolve()


def test_claim_core_classifies_lifecycle_retrieval_and_action_blocks() -> None:
    active = {"id": "CLM-20260418-abcdef12", "record_type": "claim"}
    assert claim_lifecycle_state(active) == "active"
    assert claim_attention(active) == "normal"
    assert not claim_is_fallback(active)
    assert not claim_is_archived(active)
    assert claim_retrieval_tier(active) == 3
    assert claim_blocks_current_action(active, {"executed_at": "2026-04-18T10:00:00"}) is False

    source = {"id": "SRC-20260418-abcdef12", "record_type": "source"}
    assert claim_retrieval_tier(source) == 2

    low_attention = {
        "id": "CLM-20260418-bcdef123",
        "record_type": "claim",
        "lifecycle": {"state": "active", "attention": "low"},
    }
    assert claim_attention(low_attention) == "low"
    assert claim_retrieval_tier(low_attention) == 2

    resolved = {
        "id": "CLM-20260418-cdef1234",
        "record_type": "claim",
        "lifecycle": {"state": "resolved", "resolved_at": "2026-04-18T10:00:00"},
    }
    assert claim_attention(resolved) == "fallback-only"
    assert claim_is_fallback(resolved)
    assert not claim_is_archived(resolved)
    assert claim_retrieval_tier(resolved) == 1
    assert claim_blocks_current_action(resolved, {"executed_at": "2026-04-18T09:59:59"}) is False
    assert claim_blocks_current_action(resolved, {"executed_at": "2026-04-18T10:00:00"}) is True
    assert claim_blocks_current_action(resolved, {}) is True

    archived = {
        "id": "CLM-20260418-def12345",
        "record_type": "claim",
        "lifecycle": {"state": "archived"},
    }
    assert claim_attention(archived) == "explicit-only"
    assert claim_is_archived(archived)
    assert claim_retrieval_tier(archived) == 0
    assert claim_retrieval_tier(archived, explicit_refs={"CLM-20260418-def12345"}) == 4

    timestamp = "2026-04-18T10:05:00+03:00"
    history_entry = build_claim_lifecycle_history_entry(
        "resolved",
        "fallback-only",
        timestamp,
        " resolved by newer claim ",
        {"resolved_by_claim_refs": ["CLM-20260418-eeee1111"], "empty": []},
    )
    assert history_entry == {
        "state": "resolved",
        "attention": "fallback-only",
        "at": timestamp,
        "note": "resolved by newer claim",
        "resolved_by_claim_refs": ["CLM-20260418-eeee1111"],
    }

    source_claim = {
        "id": "CLM-20260418-ffff2222",
        "record_type": "claim",
        "project_refs": [],
        "note": "base",
        "lifecycle": {"history": "bad history"},
    }
    resolved_payload = mutate_claim_lifecycle_payload(
        claim_payload=source_claim,
        timestamp=timestamp,
        state="resolved",
        attention="fallback-only",
        note="resolved by newer claim",
        current_project_ref="PRJ-20260418-aaaa1111",
        resolved_by_claim_refs=["CLM-20260418-eeee1111"],
        resolved_by_action_refs=["ACT-20260418-bbbb2222"],
        reactivation_conditions=["new runtime contradiction"],
    )
    assert source_claim["note"] == "base"
    assert resolved_payload["project_refs"] == ["PRJ-20260418-aaaa1111"]
    assert resolved_payload["updated_at"] == timestamp
    assert resolved_payload["note"] == f"base\n\n[{timestamp}] lifecycle=resolved/fallback-only: resolved by newer claim"
    assert resolved_payload["lifecycle"]["resolved_at"] == timestamp
    assert resolved_payload["lifecycle"]["resolved_by_claim_refs"] == ["CLM-20260418-eeee1111"]
    assert resolved_payload["lifecycle"]["resolved_by_action_refs"] == ["ACT-20260418-bbbb2222"]
    assert resolved_payload["lifecycle"]["reactivation_conditions"] == ["new runtime contradiction"]
    expected_resolved_history = {
        **history_entry,
        "resolved_by_action_refs": ["ACT-20260418-bbbb2222"],
        "reactivation_conditions": ["new runtime contradiction"],
    }
    assert resolved_payload["lifecycle"]["history"] == [expected_resolved_history]

    restored_payload = mutate_claim_lifecycle_payload(
        claim_payload=resolved_payload,
        timestamp="2026-04-18T10:06:00+03:00",
        state="active",
        attention="normal",
        note="restored after recheck",
    )
    assert restored_payload["lifecycle"]["state"] == "active"
    assert restored_payload["lifecycle"]["attention"] == "normal"
    assert "resolved_at" not in restored_payload["lifecycle"]
    assert "resolved_by_claim_refs" not in restored_payload["lifecycle"]
    assert len(restored_payload["lifecycle"]["history"]) == 2

    assert parse_timestamp("not a timestamp") is None
    assert parse_timestamp("2026-04-18T10:00:00") is not None


def test_link_core_collects_dependency_refs_paths_and_edges() -> None:
    source_id = "SRC-20260418-abcdef12"
    claim_id = "CLM-20260418-abcdef12"
    support_id = "CLM-20260418-bcdef123"
    action_id = "ACT-20260418-abcdef12"
    guideline_id = "GLD-20260418-abcdef12"

    claim = {
        "id": claim_id,
        "record_type": "claim",
        "source_refs": [source_id],
        "support_refs": [support_id],
        "derived_from": "not-a-list",
        "lifecycle": {"state": "resolved", "resolved_by_action_refs": [action_id]},
    }
    assert dependency_refs_for_record(claim) == {source_id, support_id, action_id}

    working_context = {
        "id": "WCTX-20260418-abcdef12",
        "record_type": "working_context",
        "pinned_refs": ["CIX-20260418-abcdef12", claim_id],
        "assumptions": [{"support_refs": [support_id]}],
        "parent_context_ref": "WCTX-20260418-bcdef123",
    }
    assert "CIX-20260418-abcdef12" not in dependency_refs_for_record(working_context)
    assert {claim_id, support_id, "WCTX-20260418-bcdef123"}.issubset(
        dependency_refs_for_record(working_context)
    )

    flow = {
        "id": "FLOW-20260418-abcdef12",
        "record_type": "flow",
        "model_refs": ["MODEL-20260418-abcdef12"],
        "preconditions": {"claim_refs": [claim_id], "hypothesis_refs": [""]},
        "steps": [{"claim_refs": [support_id], "open_question_refs": ["OPEN-20260418-abcdef12"]}],
    }
    assert {claim_id, support_id, "MODEL-20260418-abcdef12", "OPEN-20260418-abcdef12"}.issubset(
        dependency_refs_for_record(flow)
    )

    nested = {"source_refs": [source_id], "_path": source_id, "nested": [{"claim": claim_id}]}
    assert ref_paths(nested, source_id) == ["source_refs"]
    assert ref_paths(nested, claim_id) == ["nested[0].claim"]

    records = {
        source_id: {"id": source_id, "record_type": "source"},
        claim_id: claim,
        guideline_id: {
            "id": guideline_id,
            "record_type": "guideline",
            "source_refs": [source_id],
            "related_claim_refs": [claim_id],
        },
    }
    edges = collect_link_edges(records)
    assert {"from": claim_id, "to": source_id, "fields": ["source_refs"]} in edges
    assert {"from": guideline_id, "to": claim_id, "fields": ["related_claim_refs"]} in edges
    assert {"from": guideline_id, "to": source_id, "fields": ["source_refs"]} in edges

    graph = linked_records_payload(records, claim_id, "both", depth=2)
    assert graph["anchor"]["id"] == claim_id
    assert graph["direction"] == "both"
    assert graph["records_by_distance"] == {"1": [guideline_id, source_id]}
    assert {record["id"] for record in graph["records"]} == {guideline_id, source_id}
    graph_edges = {(edge["from"], edge["to"]) for edge in graph["edges"]}
    assert (claim_id, source_id) in graph_edges
    assert (guideline_id, claim_id) in graph_edges
    assert graph["_outgoing_by_ref"][claim_id][0]["to"] == source_id
    assert graph["_incoming_by_ref"][claim_id][0]["from"] == guideline_id

    detail = record_detail_payload(records, claim_id, depth=2)
    assert detail["record"]["id"] == claim_id
    assert "_path" not in detail["record"]
    assert detail["summary"]["id"] == claim_id
    assert detail["source_quotes"] == [{"id": source_id, "source_kind": "", "critique_status": "", "quote": "", "artifact_refs": []}]
    assert {record["id"] for record in detail["links"]["records"]} == {guideline_id, source_id}
    detail_lines = record_detail_text_lines(detail)
    assert detail_lines[:5] == [
        "# Record Detail",
        "",
        f"ID: `{claim_id}`",
        "Type: `claim`",
        "Scope: ``",
    ]
    assert "Lifecycle: `resolved` attention=`fallback-only`" in detail_lines
    assert "## Direct Links" in detail_lines
    assert f"- out: `{source_id}` via `source_refs`" in detail_lines
    assert f"- in: `{guideline_id}` via `related_claim_refs`" in detail_lines


def test_cleanup_core_reports_lifecycle_and_dependency_candidates(tmp_path: Path) -> None:
    root = tmp_path / ".codex_context"
    for directory in RECORD_DIRS.values():
        (root / "records" / directory).mkdir(parents=True, exist_ok=True)
    write_settings(root, cleanup={"orphan_input_stale_after_days": 30})

    fresh_input_id = "INP-20260418-f1111111"
    stale_input_id = "INP-20260418-51111111"
    linked_input_id = "INP-20260418-11111111"
    fallback_claim_id = "CLM-20260418-fallback1"
    archived_claim_id = "CLM-20260418-archived1"
    model_id = "MODEL-20260418-abcdef12"
    flow_id = "FLOW-20260418-abcdef12"
    records = {
        fresh_input_id: {
            "id": fresh_input_id,
            "record_type": "input",
            "input_kind": "user_prompt",
            "scope": "cleanup.demo",
            "captured_at": now_timestamp(),
            "origin": {"kind": "user_prompt", "ref": "chat:fresh"},
            "text": "Fresh unlinked input should stay hot enough for later classification.",
            "note": "Fresh input.",
        },
        stale_input_id: {
            "id": stale_input_id,
            "record_type": "input",
            "input_kind": "user_prompt",
            "scope": "cleanup.demo",
            "captured_at": "2026-01-01T00:00:00+03:00",
            "origin": {"kind": "user_prompt", "ref": "chat:stale"},
            "text": "Old unlinked input can be archived after retention expires.",
            "note": "Stale input.",
        },
        linked_input_id: {
            "id": linked_input_id,
            "record_type": "input",
            "input_kind": "user_prompt",
            "scope": "cleanup.demo",
            "captured_at": "2026-01-01T00:00:00+03:00",
            "origin": {"kind": "user_prompt", "ref": "chat:linked"},
            "text": "Old linked input should not be an orphan cleanup candidate.",
            "derived_record_refs": [fallback_claim_id],
            "note": "Linked input.",
        },
        fallback_claim_id: {
            "id": fallback_claim_id,
            "record_type": "claim",
            "status": "supported",
            "statement": "Old claim still appears too prominently.",
            "lifecycle": {"state": "resolved", "attention": "normal"},
            "input_refs": [linked_input_id],
        },
        archived_claim_id: {
            "id": archived_claim_id,
            "record_type": "claim",
            "status": "supported",
            "statement": "Archived claim should be explicit only.",
            "lifecycle": {"state": "archived", "attention": "fallback-only"},
        },
        model_id: {
            "id": model_id,
            "record_type": "model",
            "status": "working",
            "claim_refs": [fallback_claim_id],
            "summary": "Model still depends on fallback claim.",
        },
        flow_id: {
            "id": flow_id,
            "record_type": "flow",
            "status": "stable",
            "preconditions": {"claim_refs": [fallback_claim_id]},
            "summary": "Flow still depends on fallback claim.",
        },
    }
    write_hypotheses_index(
        root,
        [{"claim_ref": fallback_claim_id, "status": "active", "mode": "durable", "used_by": {}}],
    )

    items, validation_errors = cleanup_candidate_items(root, records)
    kinds = {item["kind"] for item in items}
    assert {
        "claim_lifecycle_attention_mismatch",
        "archived_claim_visible_in_retrieval",
        "model_depends_on_fallback_claim",
        "flow_depends_on_fallback_claim",
        "active_hypothesis_points_to_fallback_claim",
        "orphan_input_stale",
    } <= kinds
    assert any(error.message.startswith("line 1: missing claim_ref") for error in validation_errors)
    model_item = next(item for item in items if item["kind"] == "model_depends_on_fallback_claim")
    assert model_item["refs"] == [fallback_claim_id]
    input_item = next(item for item in items if item["kind"] == "orphan_input_stale")
    assert input_item["record"]["id"] == stale_input_id
    assert input_item["threshold_days"] == 30
    assert fresh_input_id not in json.dumps(items)
    assert linked_input_id not in json.dumps([item for item in items if item["kind"] == "orphan_input_stale"])

    plan, plan_errors = cleanup_archive_plan_payload(root, records, limit=10)
    assert [error.message for error in plan_errors] == [error.message for error in validation_errors]
    assert plan["cleanup_is_read_only"] is True
    assert plan["archive_plan_is_dry_run"] is True
    assert plan["archive_format"] == "zip"
    assert plan["archivable_candidate_count"] == 1
    assert plan["items"] == [
        {
            "record_id": stale_input_id,
            "record_type": "input",
            "path": f"records/input/{stale_input_id}.json",
            "reason": "orphan_input_stale",
            "summary": "Old unlinked input can be archived after retention expires.",
            "age_days": input_item["age_days"],
            "threshold_days": 30,
        }
    ]
    plan_lines = cleanup_archive_plan_text_lines(plan)
    assert "Mode: dry-run. No archive was written and no records were changed." in plan_lines
    assert any(stale_input_id in line and "orphan_input_stale" in line for line in plan_lines)

    stale_input_path = root / "records" / "input" / f"{stale_input_id}.json"
    write_json_file(stale_input_path, records[stale_input_id])
    archive_payload, archive_errors = cleanup_archive_apply_payload(root, records, limit=10)
    assert [error.message for error in archive_errors] == [error.message for error in validation_errors]
    assert archive_payload["archive_written"] is True
    assert archive_payload["records_mutated"] is False
    assert archive_payload["records_deleted"] is False
    assert archive_payload["items"][0]["sha256"]
    assert archive_payload["items"][0]["bytes"] > 0
    assert stale_input_path.exists()
    archive_path = root / archive_payload["archive_path"]
    manifest_path = root / archive_payload["manifest_path"]
    assert archive_path.exists()
    assert manifest_path.exists()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["archive_id"] == archive_payload["archive_id"]
    assert manifest["records_deleted"] is False
    assert manifest["items"][0]["record_id"] == stale_input_id
    with zipfile.ZipFile(archive_path) as archive:
        assert "manifest.json" in archive.namelist()
        assert f"records/input/{stale_input_id}.json" in archive.namelist()
        zipped_manifest = json.loads(archive.read("manifest.json").decode("utf-8"))
    assert zipped_manifest["archive_id"] == archive_payload["archive_id"]
    apply_lines = cleanup_archive_plan_text_lines(archive_payload)
    assert "Mode: apply. Archive was written; records were not changed or deleted." in apply_lines

    archive_catalog = cleanup_archives_payload(root)
    assert archive_catalog["cleanup_archives_is_read_only"] is True
    assert archive_catalog["archive_count"] == 1
    assert archive_catalog["archives"][0]["archive_id"] == archive_payload["archive_id"]
    assert archive_catalog["archives"][0]["item_count"] == 1
    archive_catalog_lines = cleanup_archives_text_lines(archive_catalog)
    assert any(archive_payload["archive_id"] in line for line in archive_catalog_lines)

    archive_detail = cleanup_archives_payload(root, archive_ref=archive_payload["archive_id"])
    assert archive_detail["archive_id"] == archive_payload["archive_id"]
    assert archive_detail["items"][0]["record_id"] == stale_input_id
    archive_detail_lines = cleanup_archives_text_lines(archive_detail)
    assert any(stale_input_id in line for line in archive_detail_lines)

    restore_plan_existing = cleanup_restore_plan_payload(root, archive_payload["archive_id"])
    assert restore_plan_existing["restore_plan_is_dry_run"] is True
    assert restore_plan_existing["already_present_count"] == 1
    assert restore_plan_existing["items"][0]["status"] == "already-present"

    archived_record_payload = json.loads(stale_input_path.read_text(encoding="utf-8"))
    stale_input_path.unlink()
    restore_plan = cleanup_restore_plan_payload(root, archive_payload["archive_id"])
    assert restore_plan["restorable_count"] == 1
    assert restore_plan["blocking_count"] == 0
    assert restore_plan["items"][0]["status"] == "restore-ready"
    restore_lines = cleanup_restore_plan_text_lines(restore_plan)
    assert "Mode: dry-run. No files were restored." in restore_lines
    assert any(stale_input_id in line and "restore-ready" in line for line in restore_lines)

    restore_payload = cleanup_restore_apply_payload(root, archive_payload["archive_id"])
    assert restore_payload["restore_applied"] is True
    assert restore_payload["restore_blocked"] is False
    assert restore_payload["restored_count"] == 1
    assert stale_input_path.exists()
    assert json.loads(stale_input_path.read_text(encoding="utf-8")) == archived_record_payload
    restore_apply_lines = cleanup_restore_plan_text_lines(restore_payload)
    assert "Mode: apply. Missing archive files were restored without overwriting existing files." in restore_apply_lines

    stale_input_path.write_text(json.dumps({"different": True}, indent=2), encoding="utf-8")
    conflict_plan = cleanup_restore_plan_payload(root, archive_payload["archive_id"])
    assert conflict_plan["blocking_count"] == 1
    assert conflict_plan["items"][0]["status"] == "target-conflict"
    conflict_payload = cleanup_restore_apply_payload(root, archive_payload["archive_id"])
    assert conflict_payload["restore_applied"] is False
    assert conflict_payload["restore_blocked"] is True
    assert json.loads(stale_input_path.read_text(encoding="utf-8")) == {"different": True}


def test_scope_core_resolves_current_refs_and_applicability(tmp_path: Path) -> None:
    root = tmp_path / ".codex_context"
    project_id = "PRJ-20260418-abcdef12"
    task_id = "TASK-20260418-abcdef12"
    other_project_id = "PRJ-20260418-bcdef123"
    other_task_id = "TASK-20260418-bcdef123"

    write_settings(root, current_project_ref=project_id, current_task_ref=task_id)
    assert current_project_ref(root) == project_id
    assert current_task_ref(root) == task_id
    assert project_refs_for_write(root, []) == [project_id]
    assert task_refs_for_write(root, []) == [task_id]
    assert project_refs_for_write(root, [other_project_id, " "]) == [other_project_id]
    assert task_refs_for_write(root, [other_task_id, " "]) == [other_task_id]

    assert record_belongs_to_project({"id": project_id}, project_id)
    assert record_belongs_to_project({"project_refs": [project_id]}, project_id)
    assert record_belongs_to_project({}, None)
    assert not record_belongs_to_project({"project_refs": [other_project_id]}, project_id)

    assert record_belongs_to_task({}, task_id)
    assert record_belongs_to_task({"id": task_id, "task_refs": [other_task_id]}, task_id)
    assert record_belongs_to_task({"task_refs": [task_id]}, task_id)
    assert not record_belongs_to_task({"task_refs": [other_task_id]}, task_id)

    assert permission_applies({"applies_to": "global"}, project_id, task_id)
    assert permission_applies({"project_refs": [project_id]}, project_id, task_id)
    assert permission_applies({"task_refs": [task_id]}, project_id, task_id)
    assert not permission_applies({"applies_to": "project", "project_refs": [other_project_id]}, project_id, task_id)
    assert not permission_applies({"applies_to": "task", "task_refs": [other_task_id]}, project_id, task_id)

    assert guideline_applies({"status": "active", "applies_to": "global"}, project_id, task_id)
    assert guideline_applies(
        {"status": "active", "applies_to": "project", "project_refs": [project_id]}, project_id, task_id
    )
    assert guideline_applies({"status": "active", "applies_to": "task", "task_refs": [task_id]}, project_id, task_id)
    assert not guideline_applies({"status": "inactive", "applies_to": "global"}, project_id, task_id)
    assert not guideline_applies(
        {"status": "active", "applies_to": "project", "project_refs": [other_project_id]}, project_id, task_id
    )

    restrictions = {
        "RST-20260418-00000001": {
            "id": "RST-20260418-00000001",
            "record_type": "restriction",
            "status": "active",
            "applies_to": "global",
            "severity": "warning",
        },
        "RST-20260418-00000002": {
            "id": "RST-20260418-00000002",
            "record_type": "restriction",
            "status": "active",
            "applies_to": "task",
            "task_refs": [task_id],
            "severity": "hard",
        },
        "RST-20260418-00000003": {
            "id": "RST-20260418-00000003",
            "record_type": "restriction",
            "status": "inactive",
            "applies_to": "global",
            "severity": "hard",
        },
        "RST-20260418-00000004": {
            "id": "RST-20260418-00000004",
            "record_type": "restriction",
            "status": "active",
            "applies_to": "project",
            "project_refs": [other_project_id],
            "severity": "hard",
        },
    }
    assert [item["id"] for item in active_restrictions_for(restrictions, project_id, task_id)] == [
        "RST-20260418-00000002",
        "RST-20260418-00000001",
    ]


def test_search_core_scores_and_summarizes_records() -> None:
    record = {
        "id": "CLM-20260418-abcdef12",
        "record_type": "claim",
        "scope": "Search.Demo",
        "status": "supported",
        "statement": "Search helpers extract deterministic text.",
        "tags": ["Lookup"],
        "comparison": {"key": "search.demo", "value": "enabled"},
        "logic": {"atoms": [{"predicate": "Uses", "args": ["search:demo"]}]},
        "assumptions": [{"text": "Assumption text", "support_refs": ["SRC-20260418-abcdef12"]}],
        "proposals": [{"title": "Proposal title", "why": "Because lookup matters", "tradeoffs": ["small API"]}],
        "is_primary": True,
    }

    haystack = record_search_text(record)
    assert "search helpers extract deterministic text" in haystack
    assert "lookup" in haystack
    assert "src-20260418-abcdef12" in haystack
    assert "search:demo" in haystack
    assert score_record(record, {"search", "lookup", "missing"}) == 5
    assert score_record(record, {"anything"}, explicit_refs={"CLM-20260418-abcdef12"}) == 100
    assert score_record({"status": "rejected"}, {"absent"}) == -3
    assert search_record_matches(record, {"search", "lookup", "missing"}) == (8, ["lookup", "search"])
    assert record_search_timestamp({"updated_at": "2026-04-18T10:00:00+03:00"}) == "2026-04-18T10:00:00+03:00"

    fallback = {
        "id": "CLM-20260418-fallback1",
        "record_type": "claim",
        "status": "supported",
        "statement": "Search helpers historical fallback.",
        "lifecycle": {"state": "resolved", "attention": "fallback-only"},
        "updated_at": "2026-04-18T09:00:00+03:00",
    }
    archived = {
        "id": "CLM-20260418-archived1",
        "record_type": "claim",
        "status": "supported",
        "statement": "Search helpers archived explicit.",
        "lifecycle": {"state": "archived", "attention": "explicit-only"},
        "updated_at": "2026-04-18T11:00:00+03:00",
    }
    scoped = {
        "id": "GLD-20260418-abcdef12",
        "record_type": "guideline",
        "status": "active",
        "rule": "Search helpers should respect project scope.",
        "project_refs": ["PRJ-20260418-abcdef12"],
        "updated_at": "2026-04-18T12:00:00+03:00",
    }
    ranked = ranked_record_search(
        {
            record["id"]: record,
            fallback["id"]: fallback,
            archived["id"]: archived,
            scoped["id"]: scoped,
        },
        {"search", "helpers"},
        limit=10,
        record_types=[],
        project_ref=None,
        task_ref=None,
        include_fallback=False,
        include_archived=False,
    )
    assert [item["id"] for item in ranked] == [record["id"], scoped["id"]]
    with_fallback = ranked_record_search(
        {fallback["id"]: fallback, archived["id"]: archived},
        {"archived", "explicit", "helpers", "search"},
        limit=10,
        record_types=["claim"],
        project_ref=None,
        task_ref=None,
        include_fallback=True,
        include_archived=True,
    )
    assert [item["id"] for item in with_fallback] == [fallback["id"], archived["id"]]

    assert concise("  one \n two  ", 20) == "one two"
    assert concise("abcdef", 4) == "abc..."
    assert record_summary(record) == "Search helpers extract deterministic text."
    assert record_summary({"record_type": "source", "artifact_refs": ["ART-20260418-abcdef12"]}) == "ART-20260418-abcdef12"
    assert record_summary({"record_type": "proposal", "position": "Prefer smaller seams"}) == "Prefer smaller seams"
    assert public_record_summary({"id": "SRC-20260418-abcdef12", "record_type": "source", "critique_status": "accepted"}) == {
        "id": "SRC-20260418-abcdef12",
        "record_type": "source",
        "scope": "",
        "status": "accepted",
        "summary": "",
    }


def test_retrieval_core_selects_active_explicit_and_fallback_records() -> None:
    project_id = "PRJ-20260418-abcdef12"
    task_id = "TASK-20260418-abcdef12"
    active_id = "CLM-20260418-abcdef12"
    fallback_id = "CLM-20260418-bcdef123"
    archived_id = "CLM-20260418-cdef1234"
    rejected_id = "CLM-20260418-def12345"
    other_project_id = "CLM-20260418-ef123456"
    no_score_id = "CLM-20260418-f1234567"
    no_score_fallback_id = "CLM-20260418-12345678"
    records = {
        active_id: {
            "id": active_id,
            "record_type": "claim",
            "status": "supported",
            "statement": "Retry selection should prefer active facts.",
            "updated_at": "2026-04-18T12:00:00",
            "project_refs": [project_id],
            "task_refs": [task_id],
        },
        fallback_id: {
            "id": fallback_id,
            "record_type": "claim",
            "status": "supported",
            "statement": "Retry selection historical fact.",
            "updated_at": "2026-04-18T11:00:00",
            "lifecycle": {"state": "resolved"},
            "project_refs": [project_id],
        },
        archived_id: {
            "id": archived_id,
            "record_type": "claim",
            "status": "supported",
            "statement": "Retry selection archived fact.",
            "lifecycle": {"state": "archived"},
            "project_refs": [project_id],
        },
        rejected_id: {
            "id": rejected_id,
            "record_type": "claim",
            "status": "rejected",
            "statement": "Retry selection rejected fact.",
            "lifecycle": {"state": "resolved"},
            "project_refs": [project_id],
        },
        other_project_id: {
            "id": other_project_id,
            "record_type": "claim",
            "status": "supported",
            "statement": "Retry selection other project fact.",
            "lifecycle": {"state": "resolved"},
            "project_refs": ["PRJ-20260418-other"],
        },
        no_score_id: {
            "id": no_score_id,
            "record_type": "claim",
            "status": "tentative",
            "statement": "Unrelated current fact.",
            "project_refs": [project_id],
        },
        no_score_fallback_id: {
            "id": no_score_fallback_id,
            "record_type": "claim",
            "status": "tentative",
            "statement": "Unrelated historical fact.",
            "lifecycle": {"state": "resolved"},
            "project_refs": [project_id],
        },
        "MODEL-20260418-abcdef12": {
            "id": "MODEL-20260418-abcdef12",
            "record_type": "model",
            "status": "working",
            "summary": "Retry selection model.",
            "is_primary": True,
            "updated_at": "2026-04-18T10:00:00",
            "project_refs": [project_id],
        },
    }

    active = select_records(records, "claim", {"retry", "selection"}, 10, project_ref=project_id, task_ref=task_id)
    assert [record["id"] for record in active] == [active_id]

    explicit = select_records(
        records,
        "claim",
        {"retry", "selection"},
        10,
        explicit_refs={fallback_id},
        project_ref="PRJ-20260418-mismatch",
        task_ref="TASK-20260418-mismatch",
    )
    assert [record["id"] for record in explicit] == [fallback_id]

    fallback = select_fallback_claims(records, {"retry", "selection"}, 10, project_ref=project_id)
    assert [record["id"] for record in fallback] == [fallback_id]

    models = select_records(records, "model", {"retry", "selection"}, 10, project_ref=project_id)
    assert [record["id"] for record in models] == ["MODEL-20260418-abcdef12"]


def test_retrieval_core_selects_active_permissions_and_guidelines() -> None:
    project_id = "PRJ-20260418-abcdef12"
    task_id = "TASK-20260418-abcdef12"
    other_project_id = "PRJ-20260418-bcdef123"
    records = {
        "PERM-20260418-00000001": {
            "id": "PERM-20260418-00000001",
            "record_type": "permission",
            "task_refs": [task_id],
            "grants": ["edit"],
            "granted_at": "2026-04-18T09:00:00",
        },
        "PERM-20260418-00000002": {
            "id": "PERM-20260418-00000002",
            "record_type": "permission",
            "applies_to": "global",
            "grants": ["read"],
            "granted_at": "2026-04-18T10:00:00",
        },
        "PERM-20260418-00000003": {
            "id": "PERM-20260418-00000003",
            "record_type": "permission",
            "project_refs": [project_id],
            "grants": ["inspect"],
            "granted_at": "2026-04-18T08:00:00",
        },
        "PERM-20260418-00000004": {
            "id": "PERM-20260418-00000004",
            "record_type": "permission",
            "project_refs": [other_project_id],
            "grants": ["wrong project"],
        },
        "GLD-20260418-00000001": {
            "id": "GLD-20260418-00000001",
            "record_type": "guideline",
            "status": "active",
            "applies_to": "global",
            "priority": "required",
            "rule": "Keep changes small.",
            "updated_at": "2026-04-18T08:00:00",
        },
        "GLD-20260418-00000002": {
            "id": "GLD-20260418-00000002",
            "record_type": "guideline",
            "status": "active",
            "applies_to": "project",
            "project_refs": [project_id],
            "priority": "preferred",
            "rule": "Use pytest for runtime checks.",
            "updated_at": "2026-04-18T09:00:00",
        },
        "GLD-20260418-00000003": {
            "id": "GLD-20260418-00000003",
            "record_type": "guideline",
            "status": "active",
            "applies_to": "task",
            "task_refs": [task_id],
            "priority": "optional",
            "rule": "Task-local check.",
            "updated_at": "2026-04-18T07:00:00",
        },
        "GLD-20260418-00000004": {
            "id": "GLD-20260418-00000004",
            "record_type": "guideline",
            "status": "inactive",
            "applies_to": "global",
            "priority": "required",
            "rule": "Inactive rule.",
        },
        "GLD-20260418-00000005": {
            "id": "GLD-20260418-00000005",
            "record_type": "guideline",
            "status": "active",
            "applies_to": "project",
            "project_refs": [other_project_id],
            "priority": "required",
            "rule": "Wrong project rule.",
        },
    }

    permissions = active_permissions_for(records, {"pytest"}, project_id, task_id, 10)
    assert [permission["id"] for permission in permissions] == [
        "PERM-20260418-00000001",
        "PERM-20260418-00000002",
        "PERM-20260418-00000003",
    ]

    guidelines = active_guidelines_for(records, {"pytest"}, project_id, task_id, 10)
    assert [guideline["id"] for guideline in guidelines] == [
        "GLD-20260418-00000003",
        "GLD-20260418-00000002",
        "GLD-20260418-00000001",
    ]


def test_hypothesis_core_loads_writes_and_selects_active_entries(tmp_path: Path) -> None:
    root = tmp_path / ".codex_context"
    assert load_hypotheses_index(root) == ([], [])

    project_id = "PRJ-20260418-abcdef12"
    task_id = "TASK-20260418-abcdef12"
    active_claim_id = "CLM-20260418-abcdef12"
    model_claim_id = "CLM-20260418-bcdef123"
    fallback_claim_id = "CLM-20260418-cdef1234"
    other_project_claim_id = "CLM-20260418-def12345"
    inactive_claim_id = "CLM-20260418-ef123456"
    missing_claim_id = "CLM-20260418-f1234567"
    other_task_claim_id = "CLM-20260418-12345678"

    entries = [
        {
            "claim_ref": active_claim_id,
            "status": "active",
            "mode": "durable",
            "summary": "Retry hypothesis should be visible by search terms.",
        },
        {
            "claim_ref": model_claim_id,
            "status": "active",
            "mode": "durable",
            "summary": "Referenced by a model even without matching text.",
        },
        {"claim_ref": fallback_claim_id, "status": "active", "mode": "durable"},
        {"claim_ref": other_project_claim_id, "status": "active", "mode": "durable"},
        {"claim_ref": inactive_claim_id, "status": "confirmed", "mode": "durable"},
        {"claim_ref": missing_claim_id, "status": "active", "mode": "durable"},
        {"claim_ref": other_task_claim_id, "status": "active", "mode": "durable"},
    ]
    write_hypotheses_index(root, entries)
    loaded_entries, errors = load_hypotheses_index(root)
    assert errors == []
    assert [entry["claim_ref"] for entry in loaded_entries] == [entry["claim_ref"] for entry in entries]
    assert all("_line" in entry for entry in loaded_entries)
    assert "_line" not in (root / "hypotheses.jsonl").read_text(encoding="utf-8")

    records = {
        active_claim_id: {
            "id": active_claim_id,
            "record_type": "claim",
            "status": "tentative",
            "statement": "Retry selection hypothesis.",
            "project_refs": [project_id],
            "task_refs": [task_id],
        },
        model_claim_id: {
            "id": model_claim_id,
            "record_type": "claim",
            "status": "tentative",
            "statement": "Model-linked hypothesis.",
            "project_refs": [project_id],
            "task_refs": [task_id],
        },
        fallback_claim_id: {
            "id": fallback_claim_id,
            "record_type": "claim",
            "status": "tentative",
            "statement": "Resolved hypothesis.",
            "lifecycle": {"state": "resolved"},
            "project_refs": [project_id],
            "task_refs": [task_id],
        },
        other_project_claim_id: {
            "id": other_project_claim_id,
            "record_type": "claim",
            "status": "tentative",
            "statement": "Other project hypothesis.",
            "project_refs": ["PRJ-20260418-other"],
            "task_refs": [task_id],
        },
        inactive_claim_id: {
            "id": inactive_claim_id,
            "record_type": "claim",
            "status": "tentative",
            "statement": "Confirmed hypothesis.",
            "project_refs": [project_id],
            "task_refs": [task_id],
        },
        other_task_claim_id: {
            "id": other_task_claim_id,
            "record_type": "claim",
            "status": "tentative",
            "statement": "Other task retry hypothesis.",
            "project_refs": [project_id],
            "task_refs": ["TASK-20260418-other"],
        },
    }
    models = [{"claim_refs": [model_claim_id], "hypothesis_refs": ["not-a-claim-ref"]}]
    flows = [
        {
            "preconditions": {"claim_refs": [active_claim_id]},
            "oracle": {"success_claim_refs": [model_claim_id], "failure_claim_refs": [fallback_claim_id]},
            "steps": [{"claim_refs": [other_project_claim_id]}],
        }
    ]
    claim_refs = collect_claim_refs_from_models_flows(models, flows)
    assert claim_refs == {active_claim_id, model_claim_id, fallback_claim_id, other_project_claim_id}

    active_entries = active_hypotheses_for(
        records,
        root,
        {"retry", "selection"},
        {model_claim_id},
        project_ref=project_id,
        task_ref=task_id,
    )
    assert [entry["claim_ref"] for entry in active_entries] == [active_claim_id, model_claim_id]
    assert active_entries[0]["_claim"]["id"] == active_claim_id

    by_claim = active_hypothesis_entry_by_claim(root, records)
    assert set(by_claim) == {
        active_claim_id,
        model_claim_id,
        other_project_claim_id,
        missing_claim_id,
        other_task_claim_id,
    }
    assert fallback_claim_id not in by_claim

    timestamp = "2026-04-18T10:40:00+03:00"
    built_entry = build_hypothesis_entry(
        claim={"domain": "runtime", "scope": "retry"},
        claim_ref=active_claim_id,
        timestamp=timestamp,
        domain=None,
        scope=None,
        model_refs=["MODEL-20260418-aaaa1111"],
        flow_refs=["FLOW-20260418-bbbb2222"],
        action_refs=["ACT-20260418-cccc3333"],
        plan_refs=["PLN-20260418-dddd4444"],
        rollback_refs=["ACT-20260418-eeee5555"],
        mode="exploration",
        based_on_hypotheses=[model_claim_id],
        note=" explore retry ",
    )
    assert built_entry == {
        "claim_ref": active_claim_id,
        "domain": "runtime",
        "scope": "retry",
        "status": "active",
        "mode": "exploration",
        "based_on_hypotheses": [model_claim_id],
        "used_by": {
            "models": ["MODEL-20260418-aaaa1111"],
            "flows": ["FLOW-20260418-bbbb2222"],
            "actions": ["ACT-20260418-cccc3333"],
            "plans": ["PLN-20260418-dddd4444"],
        },
        "rollback_refs": ["ACT-20260418-eeee5555"],
        "created_at": timestamp,
        "updated_at": timestamp,
        "note": "explore retry",
    }
    assert hypothesis_active_entry_exists([built_entry], active_claim_id)
    assert validate_hypothesis_claim(records, active_claim_id) is None
    assert validate_hypothesis_claim(records, fallback_claim_id) == (
        f"{fallback_claim_id} must reference an active lifecycle claim"
    )

    closed_entries, closed = close_hypothesis_entries([built_entry], active_claim_id, "abandoned", timestamp, "closed")
    assert closed
    assert closed_entries[0]["status"] == "abandoned"
    assert closed_entries[0]["note"] == "closed"
    assert built_entry["status"] == "active"

    reopened_entries, reopen_status = reopen_hypothesis_entry(closed_entries, active_claim_id, timestamp, "reopened")
    assert reopen_status == "reopened"
    assert reopened_entries[0]["status"] == "active"
    assert reopened_entries[0]["note"] == "reopened"
    _, active_reopen_status = reopen_hypothesis_entry(reopened_entries, active_claim_id, timestamp, None)
    assert active_reopen_status == "active-exists"
    _, missing_reopen_status = reopen_hypothesis_entry([], active_claim_id, timestamp, None)
    assert missing_reopen_status == "missing"

    remaining_entries, removed = remove_hypothesis_entries(reopened_entries, active_claim_id)
    assert removed
    assert remaining_entries == []

    supported_claim_id = "CLM-20260418-supported"
    kept_entries, removed_reasons = sync_hypothesis_entries(
        [
            {"claim_ref": active_claim_id, "status": "active"},
            {"claim_ref": inactive_claim_id, "status": "confirmed"},
            {"claim_ref": supported_claim_id, "status": "active"},
            {"claim_ref": "CLM-20260418-missing", "status": "active"},
        ],
        {
            **records,
            supported_claim_id: {"id": supported_claim_id, "record_type": "claim", "status": "supported"},
        },
        drop_closed=True,
    )
    assert kept_entries == [{"claim_ref": active_claim_id, "status": "active"}]
    assert removed_reasons == [
        f"{inactive_claim_id}: dropped-closed-status=confirmed",
        f"{supported_claim_id}: claim-no-longer-tentative",
        "CLM-20260418-missing: missing-claim",
    ]


def test_hypothesis_core_reports_malformed_index_lines(tmp_path: Path) -> None:
    root = tmp_path / ".codex_context"
    path = root / "hypotheses.jsonl"
    path.parent.mkdir(parents=True)
    path.write_text("\n{bad json}\n[]\n{\"claim_ref\":\"CLM-20260418-abcdef12\"}\n", encoding="utf-8")

    entries, errors = load_hypotheses_index(root)
    assert [entry["claim_ref"] for entry in entries] == ["CLM-20260418-abcdef12"]
    assert [error.message for error in errors] == [
        "line 2: invalid JSON (Expecting property name enclosed in double quotes)",
        "line 3: hypothesis entry must be a JSON object",
    ]


def test_hypothesis_core_validates_index_semantics(tmp_path: Path) -> None:
    root = tmp_path / ".codex_context"
    supported_claim_id = "CLM-20260418-00000001"
    source_id = "SRC-20260418-00000001"
    fallback_claim_id = "CLM-20260418-00000002"
    base_claim_id = "CLM-20260418-00000003"
    supported_base_id = "CLM-20260418-00000004"
    fallback_base_id = "CLM-20260418-00000005"
    crowded_claim_ids = [f"CLM-20260418-0000001{index}" for index in range(6)]
    missing_claim_id = "CLM-20260418-missing"

    records = {
        supported_claim_id: {"id": supported_claim_id, "record_type": "claim", "status": "supported"},
        source_id: {"id": source_id, "record_type": "source"},
        fallback_claim_id: {
            "id": fallback_claim_id,
            "record_type": "claim",
            "status": "tentative",
            "lifecycle": {"state": "resolved"},
            "scope": "fallback",
        },
        base_claim_id: {"id": base_claim_id, "record_type": "claim", "status": "tentative", "scope": "base"},
        supported_base_id: {"id": supported_base_id, "record_type": "claim", "status": "supported"},
        fallback_base_id: {
            "id": fallback_base_id,
            "record_type": "claim",
            "status": "tentative",
            "lifecycle": {"state": "resolved"},
        },
    }
    for claim_id in crowded_claim_ids:
        records[claim_id] = {"id": claim_id, "record_type": "claim", "status": "tentative", "scope": "crowded"}

    write_hypotheses_index(
        root,
        [
            {},
            {"claim_ref": missing_claim_id, "status": "active"},
            {"claim_ref": source_id, "status": "active"},
            {
                "claim_ref": supported_claim_id,
                "status": "active",
                "mode": "invalid",
                "based_on_hypotheses": "not-a-list",
                "used_by": [],
            },
            {"claim_ref": fallback_claim_id, "status": "active"},
            {
                "claim_ref": base_claim_id,
                "status": "active",
                "based_on_hypotheses": [missing_claim_id, supported_base_id, fallback_base_id],
            },
            {"claim_ref": base_claim_id, "status": "invalid"},
            *({"claim_ref": claim_id, "status": "active"} for claim_id in crowded_claim_ids),
        ],
    )

    messages = [error.message for error in validate_hypotheses_index(root, records)]
    expected_fragments = [
        "line 1: claim_ref is required",
        f"line 2: missing claim_ref {missing_claim_id}",
        f"line 3: claim_ref {source_id} must reference a claim",
        "line 4: hypothesis index may reference only tentative claims",
        "line 4: invalid hypothesis mode",
        "line 4: based_on_hypotheses must be a list",
        "line 4: used_by must be an object",
        "line 5: active hypothesis index may reference only active lifecycle claims",
        f"line 6: missing based_on_hypothesis {missing_claim_id}",
        f"line 6: based_on_hypothesis {supported_base_id} must reference tentative claim",
        f"line 6: based_on_hypothesis {fallback_base_id} must reference active lifecycle claim",
        "line 6: based_on_hypotheses requires mode=exploration",
        "line 7: invalid hypothesis status",
        "scope 'crowded' has too many active hypotheses (6)",
    ]
    for fragment in expected_fragments:
        assert any(fragment in message for message in messages)


def test_evidence_core_matches_quotes_against_records_and_sources() -> None:
    source_id = "SRC-20260418-abcdef12"
    source = {
        "id": source_id,
        "record_type": "source",
        "quote": "Runtime output says PASS",
        "artifact_refs": ["ART-20260418-abcdef12"],
    }
    claim = {
        "id": "CLM-20260418-abcdef12",
        "record_type": "claim",
        "statement": "Feature is supported",
        "source_refs": [source_id],
        "assumptions": [{"text": "Assumption detail", "support_refs": [source_id]}],
        "proposals": [{"title": "Use smaller seam", "why": "reduces risk", "tradeoffs": ["less churn"]}],
    }

    assert normalize_quote("  Runtime \n OUTPUT  ") == "runtime output"
    assert join_quote_items(["plain", {"text": "structured", "support_refs": [source_id]}, ""]) == (
        f"plain structured {source_id}"
    )
    assert quote_matches_record({source_id: source}, claim, "feature is supported")
    assert quote_matches_record({source_id: source}, claim, "runtime output says pass")
    assert quote_matches_record({source_id: source}, claim, "use smaller seam")
    assert quote_matches_record({source_id: source}, claim, source_id)
    assert not quote_matches_record({source_id: source}, claim, "")
    assert not quote_matches_record({source_id: source}, claim, "unrelated text")


def test_reasoning_core_validates_evidence_chain_payloads() -> None:
    source_id = "SRC-20260418-abcdef12"
    fact_id = "CLM-20260418-abcdef12"
    hypothesis_id = "CLM-20260418-bcdef123"
    permission_id = "PERM-20260418-abcdef12"
    records = {
        source_id: {
            "id": source_id,
            "record_type": "source",
            "quote": "runtime retry passed",
        },
        fact_id: {
            "id": fact_id,
            "record_type": "claim",
            "plane": "runtime",
            "status": "supported",
            "statement": "Runtime retry passed.",
            "source_refs": [source_id],
        },
        hypothesis_id: {
            "id": hypothesis_id,
            "record_type": "claim",
            "plane": "runtime",
            "status": "tentative",
            "statement": "Stale state may cause the first failure.",
            "source_refs": [source_id],
        },
        permission_id: {
            "id": permission_id,
            "record_type": "permission",
            "status": "active",
            "subject": "mutating edits allowed",
        },
    }

    valid_payload = {
        "task": "request safe probe",
        "nodes": [
            {"role": "fact", "ref": fact_id, "quote": "Runtime retry passed."},
            {"role": "exploration_context", "ref": hypothesis_id, "quote": "Stale state may cause"},
            {
                "role": "requested_permission",
                "ref": "REQ-safe-probe",
                "quote": "Run a safe probe to test stale state.",
            },
        ],
        "edges": [
            {"from": fact_id, "to": "REQ-safe-probe", "relation": "justifies-request"},
            {"from": hypothesis_id, "to": "REQ-safe-probe", "relation": "motivates-probe"},
        ],
    }
    valid = validate_evidence_chain_payload(records, {}, valid_payload)
    assert valid.ok
    assert valid.roles_by_ref[fact_id] == "fact"
    assert len(valid.display_nodes) == 3
    assert evidence_chain_report_lines(valid, valid_payload, "TEP") == [
        "# TEP Evidence Chain Check",
        "",
        "Task: request safe probe",
        "Chain: 3 node(s), 2 edge(s)",
        "",
        "## User-Facing Chain",
        f'- fact `{fact_id}`: "Runtime retry passed." ->',
        f'- exploration_context `{hypothesis_id}`: "Stale state may cause" ->',
        '- requested_permission `REQ-safe-probe`: "Run a safe probe to test stale state."',
        "",
        "## Result",
        "- OK: evidence chain is mechanically valid",
        "- OK: quotes match referenced records or their sources",
        "- OK: role/status constraints passed",
    ]

    compact_payload = {
        "task": "request safe probe",
        "nodes": [
            {"role": "fact", "ref": fact_id},
            {"role": "exploration_context", "ref": hypothesis_id},
            {
                "role": "requested_permission",
                "ref": "REQ-safe-probe",
                "quote": "Run a safe probe to test stale state.",
            },
        ],
        "edges": [
            {"from": fact_id, "to": "REQ-safe-probe", "relation": "justifies-request"},
            {"from": hypothesis_id, "to": "REQ-safe-probe", "relation": "motivates-probe"},
        ],
    }
    augmented = augment_evidence_chain_payload(records, {}, compact_payload)
    assert augmented["augment_is_read_only"] is True
    assert augmented["validation"]["ok"] is True
    assert augmented["chain"]["nodes"][0]["quote"] == "Runtime retry passed."
    assert augmented["chain"]["nodes"][0]["quote_source"] == "record"
    assert augmented["chain"]["nodes"][0]["record"]["status"] == "supported"
    assert augmented["chain"]["nodes"][0]["source_quotes"] == [
        {"ref": source_id, "quote": "runtime retry passed"}
    ]
    assert augmented["user_facing_chain"][0] == {
        "role": "fact",
        "ref": fact_id,
        "quote": "Runtime retry passed.",
    }
    augmented_lines = augmented_evidence_chain_text_lines(augmented, "TEP")
    assert "# TEP Augmented Evidence Chain" in augmented_lines
    assert "Mode: read-only augmentation. No records were changed." in augmented_lines
    assert "- OK: evidence chain is mechanically valid" in augmented_lines

    blocked_hypothesis = validate_evidence_chain_payload(
        records,
        {hypothesis_id: {"mode": "exploration"}},
        {
            "nodes": [
                {"role": "fact", "ref": fact_id, "quote": "runtime retry passed"},
                {"role": "hypothesis", "ref": hypothesis_id, "quote": "Stale state may cause"},
            ],
            "edges": [{"from": fact_id, "to": hypothesis_id, "relation": "supports"}],
        },
    )
    assert not blocked_hypothesis.ok
    assert any("cannot use unconfirmed exploration hypotheses as proof" in error for error in blocked_hypothesis.errors)
    blocked_report = evidence_chain_report_lines(blocked_hypothesis, {"task": "bad proof"}, "TEP")
    assert "## Blockers" in blocked_report
    assert blocked_report[-1].startswith("- node[1]")

    blocked_control_edge = validate_evidence_chain_payload(
        records,
        {},
        {
            "nodes": [
                {"role": "permission", "ref": permission_id, "quote": "mutating edits allowed"},
                {"role": "fact", "ref": fact_id, "quote": "runtime retry passed"},
            ],
            "edges": [{"from": permission_id, "to": fact_id, "relation": "supports"}],
        },
    )
    assert not blocked_control_edge.ok
    assert any("uses authorization/control" in error for error in blocked_control_edge.errors)

    _, quote_errors, _ = validate_chain_node(
        records,
        {},
        {"role": "fact", "ref": fact_id, "quote": "unrelated text"},
        0,
    )
    assert any("quote does not match" in error for error in quote_errors)


def test_reasoning_core_reports_invalid_chain_roles_edges_and_lifecycle() -> None:
    source_id = "SRC-20260418-abcdef12"
    fact_id = "CLM-20260418-abcdef12"
    theory_id = "CLM-20260418-bcdef123"
    tentative_id = "CLM-20260418-cdef1234"
    fallback_fact_id = "CLM-20260418-def12345"
    fallback_hypothesis_id = "CLM-20260418-ef123456"
    contested_id = "CLM-20260418-f1234567"
    permission_id = "PERM-20260418-abcdef12"
    task_id = "TASK-20260418-abcdef12"
    context_id = "WCTX-20260418-abcdef12"
    records = {
        source_id: {"id": source_id, "record_type": "source", "quote": "runtime retry passed"},
        fact_id: {
            "id": fact_id,
            "record_type": "claim",
            "plane": "runtime",
            "status": "supported",
            "statement": "Runtime retry passed.",
            "source_refs": [source_id],
        },
        theory_id: {
            "id": theory_id,
            "record_type": "claim",
            "plane": "theory",
            "status": "supported",
            "statement": "Retry should pass.",
        },
        tentative_id: {
            "id": tentative_id,
            "record_type": "claim",
            "plane": "runtime",
            "status": "tentative",
            "statement": "Retry may be flaky.",
        },
        fallback_fact_id: {
            "id": fallback_fact_id,
            "record_type": "claim",
            "plane": "runtime",
            "status": "supported",
            "statement": "Old retry fact.",
            "lifecycle": {"state": "resolved"},
        },
        fallback_hypothesis_id: {
            "id": fallback_hypothesis_id,
            "record_type": "claim",
            "plane": "runtime",
            "status": "tentative",
            "statement": "Old retry hypothesis.",
            "lifecycle": {"state": "resolved"},
        },
        contested_id: {
            "id": contested_id,
            "record_type": "claim",
            "plane": "runtime",
            "status": "contested",
            "statement": "Retry status is contested.",
        },
        permission_id: {
            "id": permission_id,
            "record_type": "permission",
            "status": "active",
            "subject": "mutating edits allowed",
        },
        task_id: {
            "id": task_id,
            "record_type": "task",
            "status": "active",
            "summary": "debug retry",
        },
        context_id: {
            "id": context_id,
            "record_type": "working_context",
            "status": "active",
            "summary": "retry investigation context",
        },
    }

    ref, errors, _ = validate_chain_node(records, {}, {"role": "invalid", "ref": ""}, 0)
    assert ref is None
    assert "node[0] has invalid role `invalid`" in errors
    assert "node[0] missing ref" in errors

    requested_ref, requested_errors, _ = validate_chain_node(
        records,
        {},
        {"role": "requested_permission", "ref": "REQ-missing-quote"},
        1,
    )
    assert requested_ref == "REQ-missing-quote"
    assert any("missing requested grant quote" in error for error in requested_errors)

    missing_ref, missing_errors, _ = validate_chain_node(
        records,
        {},
        {"role": "fact", "ref": "CLM-20260418-missing", "quote": "missing"},
        2,
    )
    assert missing_ref == "CLM-20260418-missing"
    assert any("missing record" in error for error in missing_errors)

    role_cases = [
        ("fact", permission_id, "mutating edits allowed", "must reference claim"),
        ("fact", tentative_id, "Retry may be flaky.", "must be supported/corroborated"),
        ("fact", fallback_fact_id, "Old retry fact.", "lifecycle fallback/archived"),
        ("observation", permission_id, "mutating edits allowed", "must reference claim"),
        ("observation", theory_id, "Retry should pass.", "must be runtime-plane claim"),
        ("observation", fallback_fact_id, "Old retry fact.", "lifecycle fallback/archived"),
        ("hypothesis", permission_id, "mutating edits allowed", "must reference claim"),
        ("hypothesis", fact_id, "Runtime retry passed.", "must be tentative"),
        ("hypothesis", fallback_hypothesis_id, "Old retry hypothesis.", "lifecycle fallback/archived"),
        ("exploration_context", permission_id, "mutating edits allowed", "must reference claim"),
        ("exploration_context", fact_id, "Runtime retry passed.", "must be tentative"),
        ("guideline", permission_id, "mutating edits allowed", "must reference guideline record"),
    ]
    for index, (role, ref_id, quote, expected) in enumerate(role_cases, start=3):
        _, case_errors, _ = validate_chain_node(records, {}, {"role": role, "ref": ref_id, "quote": quote}, index)
        assert any(expected in error for error in case_errors)

    _, missing_quote_errors, _ = validate_chain_node(records, {}, {"role": "fact", "ref": fact_id}, 20)
    assert any("missing quote" in error for error in missing_quote_errors)

    _, contested_errors, contested_warnings = validate_chain_node(
        records,
        {},
        {"role": "fact", "ref": contested_id, "quote": "Retry status is contested."},
        21,
    )
    assert any("must be supported/corroborated" in error for error in contested_errors)
    assert any("has status `contested`" in warning for warning in contested_warnings)

    contested_payload = {
        "task": "contested warning report",
        "nodes": [{"role": "fact", "ref": contested_id, "quote": "Retry status is contested."}],
        "edges": [{"from": contested_id, "to": contested_id}],
    }
    contested_validation = validate_evidence_chain_payload(records, {}, contested_payload)
    contested_report = evidence_chain_report_lines(contested_validation, contested_payload, "TEP")
    assert "## Warnings" in contested_report
    assert any("has status `contested`" in line for line in contested_report)
    assert "## Blockers" in contested_report

    malformed = validate_evidence_chain_payload(records, {}, {"nodes": [], "edges": []})
    assert not malformed.ok
    assert "evidence chain must define non-empty nodes" in malformed.errors
    assert "evidence chain must define non-empty edges" in malformed.errors
    assert "evidence chain must include at least one fact node" in malformed.errors

    edge_errors = validate_evidence_chain_payload(
        records,
        {},
        {
            "nodes": [
                "not a node",
                {"role": "fact", "ref": fact_id, "quote": "Runtime retry passed."},
                {"role": "task", "ref": task_id, "quote": "debug retry"},
                {"role": "working_context", "ref": context_id, "quote": "retry investigation context"},
            ],
            "edges": [
                "not an edge",
                {"from": "missing-from", "to": "missing-to"},
                {"from": task_id, "to": fact_id},
                {"from": context_id, "to": fact_id},
            ],
        },
    )
    assert any("node[0] must be an object" in error for error in edge_errors.errors)
    assert any("edge[0] must be an object" in error for error in edge_errors.errors)
    assert any("references unknown from" in error for error in edge_errors.errors)
    assert any("references unknown to" in error for error in edge_errors.errors)
    assert any("uses task" in error for error in edge_errors.errors)
    assert any("uses context" in error for error in edge_errors.errors)


def test_hydration_core_tracks_state_and_context_fingerprint(tmp_path: Path) -> None:
    root = tmp_path / ".codex_context"

    assert load_hydration_state(root) == {"status": "unhydrated"}
    write_hydration_state(
        root,
        {
            "status": "hydrated",
            "fingerprint": "previous-fingerprint",
            "hydrated_at": "2026-04-18T00:00:00+00:00",
        },
    )
    assert load_hydration_state(root)["status"] == "hydrated"

    initial_fingerprint = compute_context_fingerprint(root)
    write_settings(root, allowed_freedom="proof-only")
    settings_fingerprint = compute_context_fingerprint(root)
    assert settings_fingerprint != initial_fingerprint

    record_dir = root / "records" / "source"
    write_json_file(
        record_dir / "SRC-20260418-abcdef12.json",
        {
            "id": "SRC-20260418-abcdef12",
            "record_type": "source",
            "scope": "unit",
            "note": "unit",
        },
    )
    record_fingerprint = compute_context_fingerprint(root)
    assert record_fingerprint != settings_fingerprint

    artifacts = root / "artifacts"
    artifacts.mkdir(parents=True)
    (artifacts / "artifact.txt.tmp").write_text("ignored temp payload", encoding="utf-8")
    assert compute_context_fingerprint(root) == record_fingerprint
    (artifacts / "artifact.txt").write_text("tracked payload", encoding="utf-8")
    artifact_fingerprint = compute_context_fingerprint(root)
    assert artifact_fingerprint != record_fingerprint

    invalidate_hydration_state(root, "unit mutation")
    state = load_hydration_state(root)
    assert state["status"] == "stale"
    assert state["reason"] == "unit mutation"
    assert state["hydrated_at"] == "2026-04-18T00:00:00+00:00"
    assert state["last_hydrated_fingerprint"] == "previous-fingerprint"
    assert state["current_fingerprint"] == artifact_fingerprint


def test_id_allocation_keeps_legacy_ids_valid_and_allocates_random_suffixes(tmp_path: Path) -> None:
    records = {"SRC-20260418-0001": {"id": "SRC-20260418-0001"}}

    record_id = next_record_id(records, "SRC-")
    assert re.match(r"^SRC-\d{8}-[0-9a-f]{8}$", record_id)
    assert record_id not in records

    artifact_id = next_artifact_id(tmp_path / ".codex_context")
    assert re.match(r"^ART-\d{8}-[0-9a-f]{8}$", artifact_id)

    timestamp = now_timestamp()
    assert re.match(r"^\d{4}-\d{2}-\d{2}T", timestamp)


def test_settings_core_normalizes_and_persists_policy(tmp_path: Path) -> None:
    root = tmp_path / ".codex_context"

    normalized = normalize_settings_payload(
        {
            "allowed_freedom": "implementation-choice",
            "hooks": {"enabled": False, "pre_tool_use_guard": "warn", "unknown": "ignored"},
            "context_budget": {"brief": "compact", "quotes": "invalid"},
            "input_capture": {"user_prompts": "metadata-only", "file_mentions": "copy-allowed", "session_linking": False},
            "artifact_policy": {
                "copy_mode": "copy-small",
                "max_copy_bytes": 2048,
                "copy_allow_extensions": [".md", ".log"],
                "copy_deny_globs": ["*.secret"],
            },
            "cleanup": {
                "mode": "archive",
                "archive_format": "zip",
                "orphan_input_stale_after_days": 14,
                "orphan_record_stale_after_days": 120,
                "orphan_artifact_stale_after_days": 21,
                "delete_after_archive_days": 365,
            },
            "analysis": {
                "logic_solver": {"backend": "z3", "timeout_ms": 50, "max_symbols": 12},
                "topic_prefilter": {"backend": "nmf", "max_records": 10},
            },
            "backends": {
                "fact_validation": {
                    "backend": "rdf_shacl",
                    "rdf_shacl": {"enabled": True, "mode": "fake", "strict": True},
                },
                "code_intelligence": {
                    "backend": "serena",
                    "serena": {"enabled": True, "mode": "mcp", "max_results": 5},
                    "cocoindex": {
                        "enabled": True,
                        "mode": "cli",
                        "max_results": 6,
                        "import_into_cix": True,
                    },
                },
                "derivation": {"backend": "datalog", "datalog": {"enabled": True, "mode": "fake"}},
            },
            "current_task_ref": "TASK-20260418-abcdef12",
            "current_project_ref": "PRJ-20260418-abcdef12",
        }
    )

    assert normalized["allowed_freedom"] == "implementation-choice"
    assert normalized["hooks"]["enabled"] is False
    assert normalized["hooks"]["pre_tool_use_guard"] == "warn"
    assert normalized["context_budget"]["brief"] == "compact"
    assert normalized["context_budget"]["quotes"] == "normal"
    assert normalized["input_capture"]["user_prompts"] == "metadata-only"
    assert normalized["input_capture"]["file_mentions"] == "copy-allowed"
    assert normalized["input_capture"]["session_linking"] is False
    assert normalized["artifact_policy"]["copy_mode"] == "copy-small"
    assert normalized["artifact_policy"]["max_copy_bytes"] == 2048
    assert normalized["artifact_policy"]["copy_allow_extensions"] == [".md", ".log"]
    assert normalized["artifact_policy"]["copy_deny_globs"] == ["*.secret"]
    assert normalized["cleanup"]["mode"] == "archive"
    assert normalized["cleanup"]["archive_format"] == "zip"
    assert normalized["cleanup"]["orphan_input_stale_after_days"] == 14
    assert normalized["cleanup"]["orphan_record_stale_after_days"] == 120
    assert normalized["cleanup"]["orphan_artifact_stale_after_days"] == 21
    assert normalized["cleanup"]["delete_after_archive_days"] == 365
    assert normalized["analysis"]["logic_solver"]["backend"] == "z3"
    assert normalized["analysis"]["logic_solver"]["timeout_ms"] == 2000
    assert normalized["analysis"]["logic_solver"]["max_symbols"] == 12
    assert normalized["analysis"]["topic_prefilter"]["backend"] == "nmf"
    assert normalized["backends"]["fact_validation"]["backend"] == "rdf_shacl"
    assert normalized["backends"]["fact_validation"]["rdf_shacl"]["enabled"] is True
    assert normalized["backends"]["fact_validation"]["rdf_shacl"]["mode"] == "fake"
    assert normalized["backends"]["fact_validation"]["rdf_shacl"]["strict"] is True
    assert normalized["backends"]["code_intelligence"]["backend"] == "serena"
    assert normalized["backends"]["code_intelligence"]["serena"]["max_results"] == 5
    assert normalized["backends"]["code_intelligence"]["cocoindex"]["import_into_cix"] is True
    assert normalized["backends"]["derivation"]["backend"] == "datalog"
    assert normalized["backends"]["derivation"]["datalog"]["mode"] == "fake"
    assert normalized["current_task_ref"] == "TASK-20260418-abcdef12"

    write_settings(root, allowed_freedom="evidence-authorized", current_task_ref=None)
    stored = load_settings(root)
    assert stored["allowed_freedom"] == "evidence-authorized"
    assert stored["current_task_ref"] is None
    assert "updated_at" in json.loads(settings_path(root).read_text(encoding="utf-8"))

    backend_status = backend_status_payload(root)
    assert backend_status["backend_status_is_proof"] is False
    assert select_backend_status(backend_status, "fact_validation")[0]["id"] == "builtin"
    assert "Backend status is diagnostic/navigation data only" in "\n".join(
        backend_status_text_lines(backend_status)
    )

    fake_settings = normalize_backend_settings(
        {"derivation": {"backend": "datalog", "datalog": {"enabled": True, "mode": "fake"}}}
    )
    write_settings(root, backends=fake_settings)
    fake_status = backend_status_payload(root)
    datalog = select_backend_status(fake_status, "derivation.datalog")[0]
    assert datalog["available"] is True
    assert datalog["backend_output_is_proof"] is False


def test_local_anchor_overrides_focus_and_can_only_lower_allowed_freedom(tmp_path: Path, monkeypatch) -> None:
    root = tmp_path / ".tep_context"
    root.mkdir()
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    write_settings(root, allowed_freedom="proof-only", current_workspace_ref=None, current_project_ref=None)
    write_json_file(
        workspace / ".tep",
        {
            "schema_version": 1,
            "context_root": str(root),
            "workspace_ref": "WSP-20260418-abcdef12",
            "project_ref": "PRJ-20260418-abcdef12",
            "settings": {"allowed_freedom": "implementation-choice", "hooks": {"verbosity": "debug"}},
        },
    )

    monkeypatch.chdir(workspace)
    effective = load_effective_settings(root)
    assert effective["current_workspace_ref"] == "WSP-20260418-abcdef12"
    assert effective["current_project_ref"] == "PRJ-20260418-abcdef12"
    assert effective["allowed_freedom"] == "proof-only"
    assert effective["hooks"]["verbosity"] == "debug"

    write_settings(root, allowed_freedom="implementation-choice")
    write_json_file(
        workspace / ".tep",
        {
            "schema_version": 1,
            "context_root": str(root),
            "workspace_ref": "WSP-20260418-abcdef12",
            "settings": {"allowed_freedom": "proof-only"},
        },
    )
    assert load_effective_settings(root)["allowed_freedom"] == "proof-only"


def test_settings_core_handles_strictness_approval_requests(tmp_path: Path) -> None:
    root = tmp_path / ".codex_context"
    request_id = "REQ-20260418-abcdef12"
    permission_id = "PRM-20260418-abcdef12"
    source_id = "SRC-20260418-abcdef12"
    entries = [
        {
            "id": request_id,
            "status": "pending",
            "from": "proof-only",
            "to": "implementation-choice",
            "permission_ref": permission_id,
        }
    ]

    assert strictness_requests_path(root) == root / "strictness_requests.jsonl"
    assert load_strictness_requests(root) == ([], [])
    write_strictness_requests(root, entries)
    assert load_strictness_requests(root) == (entries, [])
    assert re.match(r"^REQ-\d{8}-[0-9a-f]{8}$", next_strictness_request_id())
    assert is_strictness_escalation("proof-only", "evidence-authorized")
    assert not is_strictness_escalation("implementation-choice", "proof-only")

    malformed_path = strictness_requests_path(root)
    malformed_path.write_text('{"ok": true}\n[]\n{bad json}\n', encoding="utf-8")
    loaded, errors = load_strictness_requests(root)
    assert loaded == [{"ok": True}]
    assert "entry must be an object" in errors[0]
    assert "invalid JSON" in errors[1]

    records = {
        permission_id: {
            "id": permission_id,
            "record_type": "permission",
            "grants": ["allowed_freedom:implementation-choice"],
        },
        source_id: {
            "id": source_id,
            "record_type": "source",
            "critique_status": "accepted",
            "origin": {"kind": "user", "ref": "prompt"},
            "quote": f"TEP-APPROVE {request_id}",
        },
    }
    assert permission_allows_strictness(records, permission_id, "implementation-choice")
    request, error = strictness_request_allows_change(
        records,
        entries,
        request_ref=request_id,
        approval_source_ref=source_id,
        current_value="proof-only",
        value="implementation-choice",
        permission_ref=permission_id,
    )
    assert request is entries[0]
    assert error is None

    _, missing_error = strictness_request_allows_change(
        records,
        entries,
        request_ref=request_id,
        approval_source_ref=source_id,
        current_value="proof-only",
        value="evidence-authorized",
        permission_ref=permission_id,
    )
    assert missing_error == f"strictness request {request_id} does not target evidence-authorized"


def test_settings_core_validates_raw_policy_shapes_and_refs(tmp_path: Path) -> None:
    root = tmp_path / ".codex_context"
    path = settings_path(root)
    path.parent.mkdir(parents=True)
    assert validate_settings_state(root, {}) == []

    path.write_text("{bad json}", encoding="utf-8")
    assert validate_settings_state(root, {})[0].message.startswith("invalid settings.json:")

    raw_error_cases = [
        ([], "settings.json must be an object"),
        ({"current_task_ref": "bad"}, "current_task_ref must be empty or TASK-YYYYMMDD-xxxxxxxx"),
        ({"current_project_ref": "bad"}, "current_project_ref must be empty or PRJ-YYYYMMDD-xxxxxxxx"),
        ({"hooks": []}, "hooks must be an object"),
        ({"hooks": {"pre_tool_use_guard": "block-everything"}}, "hooks.pre_tool_use_guard has invalid value"),
        ({"context_budget": []}, "context_budget must be an object"),
        ({"context_budget": {"brief": "oversized"}}, "context_budget.brief has invalid value"),
        ({"input_capture": []}, "input_capture must be an object"),
        ({"input_capture": {"user_prompts": "always-full"}}, "input_capture.user_prompts has invalid value"),
        ({"input_capture": {"file_mentions": "inline"}}, "input_capture.file_mentions has invalid value"),
        ({"input_capture": {"session_linking": "yes"}}, "input_capture.session_linking must be boolean"),
        ({"artifact_policy": []}, "artifact_policy must be an object"),
        ({"artifact_policy": {"copy_mode": "always"}}, "artifact_policy.copy_mode has invalid value"),
        ({"artifact_policy": {"max_copy_bytes": True}}, "artifact_policy.max_copy_bytes has invalid value"),
        ({"artifact_policy": {"copy_allow_extensions": [""]}}, "artifact_policy.copy_allow_extensions has invalid value"),
        ({"artifact_policy": {"copy_deny_globs": [""]}}, "artifact_policy.copy_deny_globs has invalid value"),
        ({"cleanup": []}, "cleanup must be an object"),
        ({"cleanup": {"mode": "auto-delete"}}, "cleanup.mode has invalid value"),
        ({"cleanup": {"archive_format": "tar"}}, "cleanup.archive_format has invalid value"),
        ({"cleanup": {"orphan_input_stale_after_days": True}}, "cleanup.orphan_input_stale_after_days has invalid value"),
        ({"cleanup": {"orphan_record_stale_after_days": -1}}, "cleanup.orphan_record_stale_after_days has invalid value"),
        ({"cleanup": {"orphan_artifact_stale_after_days": 4000}}, "cleanup.orphan_artifact_stale_after_days has invalid value"),
        ({"cleanup": {"delete_after_archive_days": "soon"}}, "cleanup.delete_after_archive_days has invalid value"),
        ({"analysis": []}, "analysis must be an object"),
        ({"analysis": {"logic_solver": []}}, "analysis.logic_solver must be an object"),
        ({"analysis": {"logic_solver": {"enabled": "yes"}}}, "analysis.logic_solver.enabled must be boolean"),
        ({"analysis": {"logic_solver": {"backend": "sat4j"}}}, "analysis.logic_solver.backend has invalid value"),
        ({"analysis": {"logic_solver": {"mode": "proof"}}}, "analysis.logic_solver.mode has invalid value"),
        (
            {"analysis": {"logic_solver": {"missing_dependency": "install"}}},
            "analysis.logic_solver.missing_dependency has invalid value",
        ),
        (
            {"analysis": {"logic_solver": {"install_policy": "always"}}},
            "analysis.logic_solver.install_policy has invalid value",
        ),
        (
            {"analysis": {"logic_solver": {"optional_backends": ["z3", "prolog"]}}},
            "analysis.logic_solver.optional_backends has invalid value",
        ),
        ({"analysis": {"logic_solver": {"timeout_ms": True}}}, "analysis.logic_solver.timeout_ms has invalid value"),
        ({"analysis": {"topic_prefilter": []}}, "analysis.topic_prefilter must be an object"),
        (
            {"analysis": {"topic_prefilter": {"enabled": "yes"}}},
            "analysis.topic_prefilter.enabled must be boolean",
        ),
        (
            {"analysis": {"topic_prefilter": {"backend": "lda"}}},
            "analysis.topic_prefilter.backend has invalid value",
        ),
        (
            {"analysis": {"topic_prefilter": {"missing_dependency": "install"}}},
            "analysis.topic_prefilter.missing_dependency has invalid value",
        ),
        (
            {"analysis": {"topic_prefilter": {"install_policy": "always"}}},
            "analysis.topic_prefilter.install_policy has invalid value",
        ),
        (
            {"analysis": {"topic_prefilter": {"rebuild": "always"}}},
            "analysis.topic_prefilter.rebuild has invalid value",
        ),
        (
            {"analysis": {"topic_prefilter": {"optional_backends": ["nmf", "lda"]}}},
            "analysis.topic_prefilter.optional_backends has invalid value",
        ),
        (
            {"analysis": {"topic_prefilter": {"max_records": True}}},
            "analysis.topic_prefilter.max_records has invalid value",
        ),
        ({"backends": []}, "backends must be an object"),
        ({"backends": {"fact_validation": []}}, "backends.fact_validation must be an object"),
        (
            {"backends": {"fact_validation": {"backend": "custom"}}},
            "backends.fact_validation.backend has invalid value",
        ),
        (
            {"backends": {"fact_validation": {"rdf_shacl": []}}},
            "backends.fact_validation.rdf_shacl must be an object",
        ),
        (
            {"backends": {"fact_validation": {"rdf_shacl": {"enabled": "yes"}}}},
            "backends.fact_validation.rdf_shacl.enabled must be boolean",
        ),
        (
            {"backends": {"code_intelligence": {"backend": "ctags"}}},
            "backends.code_intelligence.backend has invalid value",
        ),
        (
            {"backends": {"code_intelligence": {"serena": {"max_results": 0}}}},
            "backends.code_intelligence.serena.max_results has invalid value",
        ),
        (
            {"backends": {"code_intelligence": {"cocoindex": {"import_into_cix": "yes"}}}},
            "backends.code_intelligence.cocoindex.import_into_cix must be boolean",
        ),
        (
            {"backends": {"derivation": {"backend": "prolog"}}},
            "backends.derivation.backend has invalid value",
        ),
        (
            {"backends": {"derivation": {"datalog": {"mode": "prod"}}}},
            "backends.derivation.datalog.mode has invalid value",
        ),
    ]
    for raw, expected in raw_error_cases:
        write_json_file(path, raw)
        assert validate_settings_state(root, {})[0].message == expected

    task_id = "TASK-20260418-abcdef12"
    project_id = "PRJ-20260418-abcdef12"
    write_json_file(path, {"current_task_ref": task_id, "current_project_ref": project_id})
    assert [error.message for error in validate_settings_state(root, {})] == [
        f"current_task_ref missing task record: {task_id}",
        f"current_project_ref missing project record: {project_id}",
    ]
    wrong_records = {
        task_id: {"id": task_id, "record_type": "claim"},
        project_id: {"id": project_id, "record_type": "claim"},
    }
    assert [error.message for error in validate_settings_state(root, wrong_records)] == [
        f"current_task_ref must reference a task record: {task_id}",
        f"current_project_ref must reference a project record: {project_id}",
    ]
    valid_records = {
        task_id: {"id": task_id, "record_type": "task"},
        project_id: {"id": project_id, "record_type": "project"},
    }
    assert validate_settings_state(root, valid_records) == []


def test_record_loaders_return_records_with_paths_and_validation_errors(tmp_path: Path) -> None:
    root = tmp_path / ".codex_context"
    claim_dir = root / "records" / "claim"
    source_dir = root / "records" / "source"
    claim_dir.mkdir(parents=True)
    source_dir.mkdir(parents=True)

    write_json_file(
        claim_dir / "CLM-20260418-abcdef12.json",
        {
            "id": "CLM-20260418-abcdef12",
            "record_type": "claim",
            "scope": "unit",
            "note": "unit",
        },
    )
    write_json_file(source_dir / "broken.json", {"record_type": "source"})

    records, errors = load_records(root)
    assert "CLM-20260418-abcdef12" in records
    assert records["CLM-20260418-abcdef12"]["_folder"] == "claim"
    assert records["CLM-20260418-abcdef12"]["_path"] == claim_dir / "CLM-20260418-abcdef12.json"
    assert any("missing record directory" in error.message for error in errors)
    assert any("missing id" in error.message for error in errors)

    cix_dir = root / "code_index" / "entries"
    cix_dir.mkdir(parents=True)
    write_json_file(cix_dir / "CIX-20260418-abcdef12.json", {"id": "CIX-20260418-abcdef12"})
    write_json_file(cix_dir / "missing.json", {"target": {}})

    entries, cix_errors = load_code_index_entries(root)
    assert "CIX-20260418-abcdef12" in entries
    assert entries["CIX-20260418-abcdef12"]["_path"] == cix_dir / "CIX-20260418-abcdef12.json"
    assert any("missing id" in error.message for error in cix_errors)
