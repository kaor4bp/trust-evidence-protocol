"""Canonical record schema constants and validators."""

from __future__ import annotations

from pathlib import Path

from .claims import claim_blocks_current_action, claim_is_fallback, claim_lifecycle
from .conflicts import validate_claim_comparison
from .errors import ValidationError
from .ids import WORKING_CONTEXT_ID_PATTERN
from .logic import validate_claim_logic
from .records import RECORD_TYPE_TO_PREFIX
from .repo_scope import root_refs_are_absolute
from .validation import (
    ensure_dict,
    ensure_list,
    ensure_string_list,
    safe_list,
    validate_optional_confidence,
    validate_optional_red_flags,
)

SOURCE_KINDS = {"theory", "code", "runtime", "memory"}
INPUT_KINDS = {"user_prompt", "file_reference", "attachment", "tool_payload"}
CRITIQUE_STATUSES = {"accepted", "audited", "unresolved"}
CLAIM_PLANES = {"theory", "code", "runtime"}
CLAIM_STATUSES = {"tentative", "supported", "corroborated", "contested", "rejected"}
CLAIM_KINDS = {"factual", "implied", "statistical", "opinion", "prediction", "unfalsifiable"}
CLAIM_LIFECYCLE_STATES = {"active", "resolved", "historical", "archived"}
CLAIM_ATTENTION_LEVELS = {"normal", "low", "fallback-only", "explicit-only"}
ACTION_STATUSES = {"planned", "executed", "abandoned"}
ACTION_SAFETY_CLASSES = {"safe", "guarded", "unsafe"}
WORKSPACE_STATUSES = {"active", "archived"}
PROJECT_STATUSES = {"active", "archived"}
PERMISSION_APPLIES_TO = {"global", "project", "task"}
RESTRICTION_STATUSES = {"active", "inactive", "superseded"}
RESTRICTION_APPLIES_TO = {"global", "project", "task"}
RESTRICTION_SEVERITIES = {"hard", "warning"}
GUIDELINE_STATUSES = {"active", "inactive", "superseded"}
GUIDELINE_DOMAINS = {"code", "tests", "review", "debugging", "architecture", "agent-behavior"}
GUIDELINE_APPLIES_TO = {"global", "project", "task"}
GUIDELINE_PRIORITIES = {"required", "preferred", "optional"}
PROPOSAL_STATUSES = {"active", "accepted", "rejected", "superseded", "abandoned"}
TASK_STATUSES = {"active", "completed", "paused", "stopped"}
TASK_TYPES = {
    "general",
    "investigation",
    "implementation",
    "review",
    "debugging",
    "refactor",
    "migration",
    "test-writing",
    "release",
}
WORKING_CONTEXT_STATUSES = {"active", "closed", "superseded", "archived"}
WORKING_CONTEXT_KINDS = {"general", "investigation", "planning", "edit", "review", "permission", "handoff"}
PLAN_STATUSES = {"proposed", "active", "blocked", "completed", "abandoned"}
DEBT_STATUSES = {"open", "accepted", "scheduled", "resolved", "invalid", "wont-fix"}
MODEL_KNOWLEDGE_CLASSES = {"domain", "investigation"}
MODEL_STATUSES = {"draft", "working", "stable", "contested", "stale", "superseded"}
FLOW_STEP_STATUSES = {"aligned", "contradicted", "unresolved", "accepted-deviation"}
OPEN_QUESTION_STATUSES = {"open", "resolved", "deferred", "invalid"}
PRIORITY_LEVELS = {"critical", "high", "medium", "low"}
REF_KEYS = {
    "source_refs",
    "support_refs",
    "contradiction_refs",
    "derived_from",
    "input_refs",
    "derived_record_refs",
    "workspace_refs",
    "project_refs",
    "task_refs",
    "working_context_refs",
    "restriction_refs",
    "guideline_refs",
    "claim_refs",
    "flow_refs",
    "proposal_refs",
    "related_project_refs",
    "justified_by",
    "blocked_by",
    "evidence_refs",
    "plan_refs",
    "open_question_refs",
    "related_model_refs",
    "related_claim_refs",
    "related_flow_refs",
    "related_open_question_refs",
    "model_refs",
    "action_refs",
    "topic_seed_refs",
    "debt_refs",
    "supersedes_refs",
    "conflict_refs",
    "hypothesis_refs",
    "promoted_from_refs",
    "accepted_deviation_refs",
    "resolved_by_claim_refs",
}


def artifact_ref_exists(record_path: Path, artifact_ref: str) -> bool:
    if not artifact_ref.strip():
        return False

    candidates = []
    try:
        root = record_path.parents[2]
    except IndexError:
        root = None
    candidates.append((record_path.parent / artifact_ref).resolve())
    if root is not None:
        candidates.append((root / artifact_ref).resolve())

    for candidate in candidates:
        if candidate.exists() and root is not None and candidate.is_relative_to(root.resolve()):
            return True
    return False


def validate_record(record_id: str, data: dict) -> list[str]:
    errors: list[str] = []
    path = Path(data["_path"])
    folder = str(data["_folder"])
    record_type = str(data.get("record_type", "")).strip()
    scope = str(data.get("scope", "")).strip()

    if path.stem != record_id:
        errors.append("filename must match id")
    if record_type != folder:
        errors.append("record_type must match enclosing record folder")
    prefix = RECORD_TYPE_TO_PREFIX.get(record_type)
    if not prefix or not record_id.startswith(prefix):
        errors.append("id prefix does not match record_type")
    if not scope:
        errors.append("scope is required")
    if not str(data.get("note", "")).strip():
        errors.append("note is required")

    if record_type == "workspace":
        if not str(data.get("workspace_key", "")).strip():
            errors.append("workspace_key is required")
        if not str(data.get("title", "")).strip():
            errors.append("title is required")
        if str(data.get("status", "")).strip() not in WORKSPACE_STATUSES:
            errors.append("invalid workspace status")
        if not str(data.get("context_root", "")).strip():
            errors.append("context_root is required")
        if not str(data.get("created_at", "")).strip():
            errors.append("created_at is required")
        if not str(data.get("updated_at", "")).strip():
            errors.append("updated_at is required")
        try:
            root_refs = ensure_string_list(data, "root_refs")
        except ValueError as exc:
            errors.append(str(exc))
            root_refs = []
        if not root_refs_are_absolute(root_refs):
            errors.append("workspace root_refs must be absolute paths")
        for key in ("project_refs", "tags"):
            if key in data:
                try:
                    ensure_list(data, key)
                except ValueError as exc:
                    errors.append(str(exc))

    elif record_type == "project":
        if not str(data.get("project_key", "")).strip():
            errors.append("project_key is required")
        if not str(data.get("title", "")).strip():
            errors.append("title is required")
        if str(data.get("status", "")).strip() not in PROJECT_STATUSES:
            errors.append("invalid project status")
        if not str(data.get("created_at", "")).strip():
            errors.append("created_at is required")
        if not str(data.get("updated_at", "")).strip():
            errors.append("updated_at is required")
        try:
            root_refs = ensure_string_list(data, "root_refs")
            if not root_refs:
                errors.append("project must define root_refs")
        except ValueError as exc:
            errors.append(str(exc))
            root_refs = []
        if not root_refs_are_absolute(root_refs):
            errors.append("project root_refs must be absolute paths")
        for key in ("related_project_refs", "workspace_refs"):
            if key in data:
                try:
                    ensure_list(data, key)
                except ValueError as exc:
                    errors.append(str(exc))

    elif record_type == "input":
        if str(data.get("input_kind", "")).strip() not in INPUT_KINDS:
            errors.append("invalid input_kind")
        if not str(data.get("captured_at", "")).strip():
            errors.append("captured_at is required")
        try:
            origin = ensure_dict(data, "origin")
        except ValueError as exc:
            errors.append(str(exc))
            origin = {}
        if not origin.get("kind") or not origin.get("ref"):
            errors.append("origin.kind and origin.ref are required")
        artifact_refs = ensure_list(data, "artifact_refs")
        text = str(data.get("text", "")).strip()
        if not text and not artifact_refs:
            errors.append("input must define text or artifact_refs")
        for artifact_ref in artifact_refs:
            if not artifact_ref_exists(path, artifact_ref):
                errors.append(f"missing artifact ref: {artifact_ref}")
        if "session_ref" in data and not str(data.get("session_ref", "")).strip():
            errors.append("session_ref must be non-empty when provided")
        for key in ("derived_record_refs",):
            if key in data:
                try:
                    ensure_list(data, key)
                except ValueError as exc:
                    errors.append(str(exc))

    elif record_type == "source":
        if str(data.get("source_kind", "")).strip() not in SOURCE_KINDS:
            errors.append("invalid source_kind")
        if str(data.get("critique_status", "")).strip() not in CRITIQUE_STATUSES:
            errors.append("invalid critique_status")
        if not str(data.get("captured_at", "")).strip():
            errors.append("captured_at is required")
        if not str(data.get("independence_group", "")).strip():
            errors.append("independence_group is required")
        try:
            origin = ensure_dict(data, "origin")
        except ValueError as exc:
            errors.append(str(exc))
            origin = {}
        if not origin.get("kind") or not origin.get("ref"):
            errors.append("origin.kind and origin.ref are required")
        artifact_refs = ensure_list(data, "artifact_refs")
        quote = str(data.get("quote", "")).strip()
        if not quote and not artifact_refs:
            errors.append("source must define quote or artifact_refs")
        for artifact_ref in artifact_refs:
            if not artifact_ref_exists(path, artifact_ref):
                errors.append(f"missing artifact ref: {artifact_ref}")
        errors.extend(validate_optional_confidence(data))
        errors.extend(validate_optional_red_flags(data))

    elif record_type == "claim":
        if str(data.get("plane", "")).strip() not in CLAIM_PLANES:
            errors.append("invalid plane")
        status = str(data.get("status", "")).strip()
        if status not in CLAIM_STATUSES:
            errors.append("invalid status")
        if not str(data.get("statement", "")).strip():
            errors.append("statement is required")
        if not str(data.get("recorded_at", "")).strip():
            errors.append("recorded_at is required")
        try:
            if not ensure_list(data, "source_refs"):
                errors.append("claim must define source_refs")
        except ValueError as exc:
            errors.append(str(exc))
        if "comparison" in data:
            comparison = data.get("comparison")
            if not isinstance(comparison, dict):
                errors.append("comparison must be an object when provided")
            elif not comparison:
                errors.append("comparison must not be empty when provided")
            else:
                errors.extend(validate_claim_comparison(comparison))
        if "logic" in data:
            logic = data.get("logic")
            if not isinstance(logic, dict):
                errors.append("logic must be an object when provided")
            elif not logic:
                errors.append("logic must not be empty when provided")
            else:
                errors.extend(validate_claim_logic(logic))
        claim_kind = str(data.get("claim_kind", "")).strip()
        if claim_kind and claim_kind not in CLAIM_KINDS:
            errors.append("claim_kind must be factual, implied, statistical, opinion, prediction, or unfalsifiable")
        if claim_kind in {"opinion", "prediction", "unfalsifiable"} and status in {
            "supported",
            "corroborated",
            "contested",
            "rejected",
        }:
            errors.append(
                "opinion, prediction, and unfalsifiable claims must stay tentative until re-expressed as checkable factual claims"
            )
        if "lifecycle" in data:
            lifecycle = data.get("lifecycle")
            if not isinstance(lifecycle, dict):
                errors.append("claim.lifecycle must be an object when provided")
            else:
                state = str(lifecycle.get("state", "")).strip() or "active"
                attention = str(lifecycle.get("attention", "")).strip()
                if state not in CLAIM_LIFECYCLE_STATES:
                    errors.append("claim.lifecycle.state must be active, resolved, historical, or archived")
                if attention and attention not in CLAIM_ATTENTION_LEVELS:
                    errors.append("claim.lifecycle.attention must be normal, low, fallback-only, or explicit-only")
                for key in (
                    "resolved_by_claim_refs",
                    "resolved_by_action_refs",
                    "reactivation_conditions",
                ):
                    if key in lifecycle:
                        try:
                            ensure_string_list(lifecycle, key)
                        except ValueError as exc:
                            errors.append(str(exc))
                if "history" in lifecycle:
                    history = lifecycle.get("history")
                    if not isinstance(history, list):
                        errors.append("claim.lifecycle.history must be a list when provided")
                    elif any(not isinstance(item, dict) for item in history):
                        errors.append("claim.lifecycle.history entries must be objects")
                if state == "resolved" and not str(lifecycle.get("resolved_at", "")).strip():
                    errors.append("resolved claim lifecycle requires resolved_at")
                if state == "archived" and not str(lifecycle.get("archived_at", "")).strip():
                    errors.append("archived claim lifecycle requires archived_at")
        errors.extend(validate_optional_confidence(data))
        errors.extend(validate_optional_red_flags(data))

    elif record_type == "permission":
        if not str(data.get("granted_by", "")).strip():
            errors.append("granted_by is required")
        if not str(data.get("granted_at", "")).strip():
            errors.append("granted_at is required")
        try:
            if not ensure_list(data, "grants"):
                errors.append("permission must define grants")
        except ValueError as exc:
            errors.append(str(exc))
        applies_to = str(data.get("applies_to", "")).strip()
        if applies_to and applies_to not in PERMISSION_APPLIES_TO:
            errors.append("permission.applies_to must be global, project, or task")
        for key in ("project_refs", "task_refs"):
            if key in data:
                try:
                    ensure_list(data, key)
                except ValueError as exc:
                    errors.append(str(exc))
        if applies_to == "project" and not safe_list(data, "project_refs"):
            errors.append("project permission requires project_refs")
        if applies_to == "task" and not safe_list(data, "task_refs"):
            errors.append("task permission requires task_refs")

    elif record_type == "restriction":
        if not str(data.get("title", "")).strip():
            errors.append("title is required")
        if str(data.get("status", "")).strip() not in RESTRICTION_STATUSES:
            errors.append("invalid restriction status")
        if str(data.get("applies_to", "")).strip() not in RESTRICTION_APPLIES_TO:
            errors.append("restriction.applies_to must be global, project, or task")
        if str(data.get("severity", "")).strip() not in RESTRICTION_SEVERITIES:
            errors.append("restriction.severity must be hard or warning")
        if not str(data.get("imposed_by", "")).strip():
            errors.append("imposed_by is required")
        if not str(data.get("imposed_at", "")).strip():
            errors.append("imposed_at is required")
        try:
            if not ensure_string_list(data, "rules"):
                errors.append("restriction must define rules")
        except ValueError as exc:
            errors.append(str(exc))
        for key in ("project_refs", "task_refs", "related_claim_refs", "supersedes_refs"):
            if key in data:
                try:
                    ensure_list(data, key)
                except ValueError as exc:
                    errors.append(str(exc))
        if str(data.get("applies_to", "")).strip() == "project" and not safe_list(data, "project_refs"):
            errors.append("project restriction requires project_refs")
        if str(data.get("applies_to", "")).strip() == "task" and not safe_list(data, "task_refs"):
            errors.append("task restriction requires task_refs")
        if not str(data.get("created_at", "")).strip():
            errors.append("created_at is required")
        if not str(data.get("updated_at", "")).strip():
            errors.append("updated_at is required")

    elif record_type == "guideline":
        if str(data.get("domain", "")).strip() not in GUIDELINE_DOMAINS:
            errors.append("guideline.domain must be code, tests, review, debugging, architecture, or agent-behavior")
        if str(data.get("status", "")).strip() not in GUIDELINE_STATUSES:
            errors.append("invalid guideline status")
        if str(data.get("applies_to", "")).strip() not in GUIDELINE_APPLIES_TO:
            errors.append("guideline.applies_to must be global, project, or task")
        if str(data.get("priority", "")).strip() not in GUIDELINE_PRIORITIES:
            errors.append("guideline.priority must be required, preferred, or optional")
        if not str(data.get("rule", "")).strip():
            errors.append("guideline rule is required")
        if not str(data.get("created_at", "")).strip():
            errors.append("created_at is required")
        if not str(data.get("updated_at", "")).strip():
            errors.append("updated_at is required")
        try:
            if not ensure_list(data, "source_refs"):
                errors.append("guideline must define source_refs")
        except ValueError as exc:
            errors.append(str(exc))
        for key in ("project_refs", "task_refs", "related_claim_refs", "conflict_refs", "supersedes_refs", "examples"):
            if key in data:
                try:
                    ensure_list(data, key)
                except ValueError as exc:
                    errors.append(str(exc))
        if str(data.get("applies_to", "")).strip() == "project" and not safe_list(data, "project_refs"):
            errors.append("project guideline requires project_refs")
        if str(data.get("applies_to", "")).strip() == "task" and not safe_list(data, "task_refs"):
            errors.append("task guideline requires task_refs")

    elif record_type == "proposal":
        if str(data.get("status", "")).strip() not in PROPOSAL_STATUSES:
            errors.append("invalid proposal status")
        if not str(data.get("subject", "")).strip():
            errors.append("subject is required")
        if not str(data.get("position", "")).strip():
            errors.append("position is required")
        if not str(data.get("created_by", "")).strip():
            errors.append("created_by is required")
        if not str(data.get("created_at", "")).strip():
            errors.append("created_at is required")
        if not str(data.get("updated_at", "")).strip():
            errors.append("updated_at is required")
        proposals = data.get("proposals", [])
        if not isinstance(proposals, list) or not proposals:
            errors.append("proposal must define non-empty proposals")
        else:
            has_recommended = False
            for index, option in enumerate(proposals, start=1):
                if not isinstance(option, dict):
                    errors.append(f"proposal option {index} must be an object")
                    continue
                if not str(option.get("title", "")).strip():
                    errors.append(f"proposal option {index} title is required")
                if not str(option.get("why", "")).strip():
                    errors.append(f"proposal option {index} why is required")
                if not isinstance(option.get("recommended", False), bool):
                    errors.append(f"proposal option {index} recommended must be boolean")
                elif option.get("recommended") is True:
                    has_recommended = True
                if "tradeoffs" in option and not isinstance(option.get("tradeoffs"), list):
                    errors.append(f"proposal option {index} tradeoffs must be a list")
            if not has_recommended:
                errors.append("proposal must mark one option as recommended")
        for key in ("assumptions", "concerns", "risks", "stop_conditions"):
            if key in data:
                try:
                    ensure_string_list(data, key)
                except ValueError as exc:
                    errors.append(str(exc))
        for key in (
            "claim_refs",
            "guideline_refs",
            "model_refs",
            "flow_refs",
            "open_question_refs",
            "project_refs",
            "task_refs",
            "supersedes_refs",
        ):
            if key in data:
                try:
                    ensure_list(data, key)
                except ValueError as exc:
                    errors.append(str(exc))
        support_ref_count = sum(
            len(safe_list(data, key))
            for key in ("claim_refs", "guideline_refs", "model_refs", "flow_refs", "open_question_refs")
        )
        if support_ref_count == 0:
            errors.append("proposal must cite at least one claim, guideline, model, flow, or open question")
        errors.extend(validate_optional_confidence(data))

    elif record_type == "action":
        if not str(data.get("kind", "")).strip():
            errors.append("kind is required")
        if str(data.get("safety_class", "")).strip() not in ACTION_SAFETY_CLASSES:
            errors.append("action.safety_class must be safe, guarded, or unsafe")
        try:
            if not ensure_list(data, "justified_by"):
                errors.append("action must define justified_by")
        except ValueError as exc:
            errors.append(str(exc))
        action_status = str(data.get("status", "")).strip()
        if action_status not in ACTION_STATUSES:
            errors.append("invalid action status")
        if not str(data.get("planned_at", "")).strip() and not str(data.get("executed_at", "")).strip():
            errors.append("action must define planned_at or executed_at")
        if "hypothesis_refs" in data:
            try:
                ensure_list(data, "hypothesis_refs")
            except ValueError as exc:
                errors.append(str(exc))

    elif record_type == "task":
        if not str(data.get("title", "")).strip():
            errors.append("title is required")
        if str(data.get("status", "")).strip() not in TASK_STATUSES:
            errors.append("invalid task status")
        task_type = str(data.get("task_type", "general")).strip() or "general"
        if task_type not in TASK_TYPES:
            errors.append("invalid task_type")
        if not str(data.get("created_at", "")).strip():
            errors.append("created_at is required")
        if not str(data.get("updated_at", "")).strip():
            errors.append("updated_at is required")
        for key in (
            "related_claim_refs",
            "related_model_refs",
            "related_flow_refs",
            "open_question_refs",
            "plan_refs",
            "debt_refs",
            "action_refs",
            "project_refs",
            "restriction_refs",
        ):
            if key in data:
                try:
                    ensure_list(data, key)
                except ValueError as exc:
                    errors.append(str(exc))

    elif record_type == "working_context":
        if not str(data.get("title", "")).strip():
            errors.append("title is required")
        if str(data.get("status", "")).strip() not in WORKING_CONTEXT_STATUSES:
            errors.append("invalid working_context status")
        context_kind = str(data.get("context_kind", "general")).strip() or "general"
        if context_kind not in WORKING_CONTEXT_KINDS:
            errors.append("invalid working_context context_kind")
        if not str(data.get("created_at", "")).strip():
            errors.append("created_at is required")
        if not str(data.get("updated_at", "")).strip():
            errors.append("updated_at is required")
        for key in (
            "pinned_refs",
            "focus_paths",
            "topic_terms",
            "topic_seed_refs",
            "concerns",
            "project_refs",
            "task_refs",
            "supersedes_refs",
            "tags",
        ):
            if key in data:
                try:
                    ensure_list(data, key)
                except ValueError as exc:
                    errors.append(str(exc))
        parent_ref = str(data.get("parent_context_ref", "")).strip()
        if parent_ref and not WORKING_CONTEXT_ID_PATTERN.match(parent_ref):
            errors.append("parent_context_ref must be empty or WCTX-YYYYMMDD-xxxxxxxx")
        assumptions = data.get("assumptions", [])
        if assumptions in ("", None):
            assumptions = []
        if not isinstance(assumptions, list):
            errors.append("assumptions must be a list")
        else:
            for index, assumption in enumerate(assumptions, start=1):
                if not isinstance(assumption, dict):
                    errors.append(f"assumption {index} must be an object")
                    continue
                if not str(assumption.get("text", "")).strip():
                    errors.append(f"assumption {index} text is required")
                mode = str(assumption.get("mode", "exploration-only")).strip() or "exploration-only"
                if mode not in {"exploration-only", "supported", "deprecated"}:
                    errors.append(f"assumption {index} mode is invalid")
                if "support_refs" in assumption and not isinstance(assumption.get("support_refs"), list):
                    errors.append(f"assumption {index} support_refs must be a list")

    elif record_type == "plan":
        if not str(data.get("title", "")).strip():
            errors.append("title is required")
        if str(data.get("status", "")).strip() not in PLAN_STATUSES:
            errors.append("invalid plan status")
        if str(data.get("priority", "")).strip() not in PRIORITY_LEVELS:
            errors.append("invalid priority")
        try:
            if not ensure_list(data, "justified_by"):
                errors.append("plan must define justified_by")
        except ValueError as exc:
            errors.append(str(exc))
        try:
            if not ensure_string_list(data, "steps"):
                errors.append("plan must define steps")
        except ValueError as exc:
            errors.append(str(exc))
        try:
            if not ensure_string_list(data, "success_criteria"):
                errors.append("plan must define success_criteria")
        except ValueError as exc:
            errors.append(str(exc))
        if not str(data.get("created_at", "")).strip():
            errors.append("created_at is required")
        if not str(data.get("updated_at", "")).strip():
            errors.append("updated_at is required")
        if str(data.get("status", "")).strip() == "blocked":
            try:
                if not ensure_list(data, "blocked_by"):
                    errors.append("blocked plan must define blocked_by")
            except ValueError as exc:
                errors.append(str(exc))

    elif record_type == "debt":
        if not str(data.get("title", "")).strip():
            errors.append("title is required")
        if str(data.get("status", "")).strip() not in DEBT_STATUSES:
            errors.append("invalid debt status")
        if str(data.get("priority", "")).strip() not in PRIORITY_LEVELS:
            errors.append("invalid priority")
        try:
            if not ensure_list(data, "evidence_refs"):
                errors.append("debt must define evidence_refs")
        except ValueError as exc:
            errors.append(str(exc))
        if not str(data.get("created_at", "")).strip():
            errors.append("created_at is required")
        if not str(data.get("updated_at", "")).strip():
            errors.append("updated_at is required")
        if str(data.get("status", "")).strip() == "scheduled":
            try:
                if not ensure_list(data, "plan_refs"):
                    errors.append("scheduled debt must define plan_refs")
            except ValueError as exc:
                errors.append(str(exc))

    elif record_type == "model":
        if str(data.get("knowledge_class", "")).strip() not in MODEL_KNOWLEDGE_CLASSES:
            errors.append("model.knowledge_class must be domain or investigation")
        if str(data.get("status", "")).strip() not in MODEL_STATUSES:
            errors.append("invalid model status")
        if not str(data.get("domain", "")).strip():
            errors.append("domain is required")
        if not str(data.get("aspect", "")).strip():
            errors.append("aspect is required")
        if not str(data.get("summary", "")).strip():
            errors.append("summary is required")
        if not str(data.get("updated_at", "")).strip():
            errors.append("updated_at is required")
        if not isinstance(data.get("is_primary"), bool):
            errors.append("model.is_primary must be boolean")
        try:
            if not ensure_list(data, "claim_refs"):
                errors.append("model must define claim_refs")
        except ValueError as exc:
            errors.append(str(exc))
        for key in ("open_question_refs", "hypothesis_refs", "related_model_refs", "supersedes_refs", "promoted_from_refs"):
            if key in data:
                try:
                    ensure_list(data, key)
                except ValueError as exc:
                    errors.append(str(exc))
        if str(data.get("status", "")).strip() == "stable" and ensure_list(data, "hypothesis_refs"):
            errors.append("stable model cannot rely on hypothesis_refs")

    elif record_type == "flow":
        if str(data.get("knowledge_class", "")).strip() not in MODEL_KNOWLEDGE_CLASSES:
            errors.append("flow.knowledge_class must be domain or investigation")
        if str(data.get("status", "")).strip() not in MODEL_STATUSES:
            errors.append("invalid flow status")
        if not str(data.get("domain", "")).strip():
            errors.append("domain is required")
        if not str(data.get("summary", "")).strip():
            errors.append("summary is required")
        if not str(data.get("updated_at", "")).strip():
            errors.append("updated_at is required")
        if not isinstance(data.get("is_primary"), bool):
            errors.append("flow.is_primary must be boolean")
        try:
            if not ensure_list(data, "model_refs"):
                errors.append("flow must define model_refs")
        except ValueError as exc:
            errors.append(str(exc))
        try:
            steps = ensure_list(data, "steps")
            if not steps:
                errors.append("flow must define steps")
        except ValueError:
            steps = []
            errors.append("steps must be a list")
        if not isinstance(data.get("steps"), list):
            errors.append("steps must be a list of objects")
        else:
            for index, step in enumerate(data.get("steps", []), start=1):
                if not isinstance(step, dict):
                    errors.append(f"flow step {index} must be an object")
                    continue
                if not str(step.get("id", "")).strip():
                    errors.append(f"flow step {index} id is required")
                if not str(step.get("label", "")).strip():
                    errors.append(f"flow step {index} label is required")
                if str(step.get("status", "")).strip() not in FLOW_STEP_STATUSES:
                    errors.append(f"flow step {index} status is invalid")
                claim_refs = step.get("claim_refs", [])
                if not isinstance(claim_refs, list) or not [str(item).strip() for item in claim_refs if str(item).strip()]:
                    errors.append(f"flow step {index} must define claim_refs")
                for key in ("open_question_refs", "accepted_deviation_refs", "next_steps"):
                    if key in step and not isinstance(step.get(key), list):
                        errors.append(f"flow step {index} {key} must be a list")
                if str(step.get("status", "")).strip() == "accepted-deviation":
                    refs = step.get("accepted_deviation_refs", [])
                    if not isinstance(refs, list) or not [str(item).strip() for item in refs if str(item).strip()]:
                        errors.append(f"flow step {index} accepted-deviation requires accepted_deviation_refs")
        for field_name in ("preconditions", "oracle"):
            block = data.get(field_name)
            if block is not None and not isinstance(block, dict):
                errors.append(f"{field_name} must be an object when provided")
            elif isinstance(block, dict):
                for key in ("claim_refs", "hypothesis_refs"):
                    if key in block and not isinstance(block.get(key), list):
                        errors.append(f"{field_name}.{key} must be a list")
        oracle = data.get("oracle")
        if str(data.get("status", "")).strip() == "stable":
            if not isinstance(oracle, dict):
                errors.append("stable flow requires oracle")
            else:
                success = oracle.get("success_claim_refs", [])
                failure = oracle.get("failure_claim_refs", [])
                if not isinstance(success, list) or not [str(item).strip() for item in success if str(item).strip()]:
                    errors.append("stable flow requires oracle.success_claim_refs")
                if not isinstance(failure, list) or not [str(item).strip() for item in failure if str(item).strip()]:
                    errors.append("stable flow requires oracle.failure_claim_refs")
        for key in ("open_question_refs", "supersedes_refs", "promoted_from_refs"):
            if key in data:
                try:
                    ensure_list(data, key)
                except ValueError as exc:
                    errors.append(str(exc))

    elif record_type == "open_question":
        if str(data.get("status", "")).strip() not in OPEN_QUESTION_STATUSES:
            errors.append("invalid open_question status")
        if not str(data.get("domain", "")).strip():
            errors.append("domain is required")
        if not str(data.get("question", "")).strip():
            errors.append("question is required")
        if not str(data.get("created_at", "")).strip():
            errors.append("created_at is required")
        for key in ("related_claim_refs", "related_model_refs", "related_flow_refs", "resolved_by_claim_refs"):
            if key in data:
                try:
                    ensure_list(data, key)
                except ValueError as exc:
                    errors.append(str(exc))

    return errors


def validate_refs(records: dict[str, dict]) -> list[ValidationError]:
    errors: list[ValidationError] = []
    for _, data in records.items():
        path = Path(data["_path"])
        for key in REF_KEYS:
            try:
                refs = ensure_list(data, key)
            except ValueError as exc:
                errors.append(ValidationError(path, str(exc)))
                continue
            for ref in refs:
                if ref and ref not in records:
                    errors.append(ValidationError(path, f"missing ref in {key}: {ref}"))

        for ref in safe_list(data, "project_refs") + safe_list(data, "related_project_refs"):
            if ref in records and records[ref].get("record_type") != "project":
                errors.append(ValidationError(path, f"project ref {ref} must reference a project record"))
        for ref in safe_list(data, "workspace_refs"):
            if ref in records and records[ref].get("record_type") != "workspace":
                errors.append(ValidationError(path, f"workspace ref {ref} must reference a workspace record"))
        for ref in safe_list(data, "task_refs"):
            if ref in records and records[ref].get("record_type") != "task":
                errors.append(ValidationError(path, f"task ref {ref} must reference a task record"))
        for ref in safe_list(data, "restriction_refs"):
            if ref in records and records[ref].get("record_type") != "restriction":
                errors.append(ValidationError(path, f"restriction ref {ref} must reference a restriction record"))
        for ref in safe_list(data, "guideline_refs"):
            if ref in records and records[ref].get("record_type") != "guideline":
                errors.append(ValidationError(path, f"guideline ref {ref} must reference a guideline record"))
        for ref in safe_list(data, "claim_refs"):
            if ref in records and records[ref].get("record_type") != "claim":
                errors.append(ValidationError(path, f"claim ref {ref} must reference a claim record"))
        for ref in safe_list(data, "model_refs"):
            if ref in records and records[ref].get("record_type") != "model":
                errors.append(ValidationError(path, f"model ref {ref} must reference a model record"))
        for ref in safe_list(data, "flow_refs"):
            if ref in records and records[ref].get("record_type") != "flow":
                errors.append(ValidationError(path, f"flow ref {ref} must reference a flow record"))
        for ref in safe_list(data, "open_question_refs"):
            if ref in records and records[ref].get("record_type") != "open_question":
                errors.append(ValidationError(path, f"open question ref {ref} must reference an open_question record"))
        for ref in safe_list(data, "proposal_refs"):
            if ref in records and records[ref].get("record_type") != "proposal":
                errors.append(ValidationError(path, f"proposal ref {ref} must reference a proposal record"))
        for ref in safe_list(data, "working_context_refs"):
            if ref in records and records[ref].get("record_type") != "working_context":
                errors.append(ValidationError(path, f"working context ref {ref} must reference a working_context record"))
        for ref in safe_list(data, "input_refs"):
            if ref in records and records[ref].get("record_type") != "input":
                errors.append(ValidationError(path, f"input ref {ref} must reference an input record"))

        if data.get("record_type") == "workspace":
            for ref in safe_list(data, "project_refs"):
                if ref in records and records[ref].get("record_type") != "project":
                    errors.append(ValidationError(path, f"workspace project ref {ref} must reference a project record"))

        if data.get("record_type") == "project":
            for ref in safe_list(data, "related_project_refs"):
                if ref in records and records[ref].get("record_type") != "project":
                    errors.append(ValidationError(path, f"related project ref {ref} must reference a project record"))

        if data.get("record_type") == "claim":
            source_refs = ensure_list(data, "source_refs")
            support_refs = ensure_list(data, "support_refs")
            contradiction_refs = ensure_list(data, "contradiction_refs")
            derived_from = ensure_list(data, "derived_from")
            lifecycle = claim_lifecycle(data)

            for ref in support_refs + contradiction_refs + derived_from:
                if ref in records and records[ref].get("record_type") != "claim":
                    errors.append(ValidationError(path, f"{ref} must reference a claim record"))
            for ref in safe_list(lifecycle, "resolved_by_claim_refs"):
                if ref and ref not in records:
                    errors.append(ValidationError(path, f"missing ref in lifecycle.resolved_by_claim_refs: {ref}"))
                elif ref in records and records[ref].get("record_type") != "claim":
                    errors.append(ValidationError(path, f"lifecycle resolved_by_claim ref {ref} must reference a claim record"))
            for ref in safe_list(lifecycle, "resolved_by_action_refs"):
                if ref and ref not in records:
                    errors.append(ValidationError(path, f"missing ref in lifecycle.resolved_by_action_refs: {ref}"))
                elif ref in records and records[ref].get("record_type") != "action":
                    errors.append(ValidationError(path, f"lifecycle resolved_by_action ref {ref} must reference an action record"))

            if str(data.get("status", "")).strip() in {"supported", "corroborated"}:
                resolved_sources = [records[ref] for ref in source_refs if ref in records]
                if not resolved_sources:
                    errors.append(ValidationError(path, "supported/corroborated claim has no resolvable sources"))
                else:
                    if all(src.get("source_kind") == "memory" for src in resolved_sources):
                        errors.append(
                            ValidationError(path, "supported/corroborated claim cannot rely only on memory sources")
                        )
                    if any(src.get("critique_status") != "accepted" for src in resolved_sources):
                        errors.append(
                            ValidationError(path, "supported/corroborated claim requires accepted sources")
                        )

        if data.get("record_type") == "action":
            justified_by = ensure_list(data, "justified_by")
            resolved_claims = [records[ref] for ref in justified_by if ref in records]
            if any(ref in records and records[ref].get("record_type") != "claim" for ref in justified_by):
                errors.append(ValidationError(path, "action.justified_by must reference claim records"))
            if not resolved_claims:
                errors.append(ValidationError(path, "action requires resolvable claim justification"))
            else:
                for claim in resolved_claims:
                    status = str(claim.get("status", "")).strip()
                    if status not in {"supported", "corroborated"}:
                        errors.append(
                            ValidationError(
                                path,
                                f"action justification claim {claim.get('id', '<unknown>')} must be supported or corroborated",
                            )
                        )
                    if not ensure_list(claim, "source_refs"):
                        errors.append(
                            ValidationError(
                                path,
                                f"action justification claim {claim.get('id', '<unknown>')} must preserve source_refs",
                            )
                        )
                    if claim_blocks_current_action(claim, data):
                        errors.append(
                            ValidationError(
                                path,
                                f"action justification claim {claim.get('id', '<unknown>')} is lifecycle fallback/archived for this action timestamp",
                            )
                        )
            for ref in safe_list(data, "hypothesis_refs"):
                if ref in records and records[ref].get("record_type") != "claim":
                    errors.append(ValidationError(path, f"action hypothesis ref {ref} must reference a claim record"))
                elif ref in records and records[ref].get("status") != "tentative":
                    errors.append(ValidationError(path, f"action hypothesis ref {ref} must point to a tentative claim"))
                elif ref in records and claim_is_fallback(records[ref]):
                    errors.append(ValidationError(path, f"action hypothesis ref {ref} must point to an active tentative claim"))

        if data.get("record_type") == "restriction":
            for ref in safe_list(data, "related_claim_refs"):
                if ref in records and records[ref].get("record_type") != "claim":
                    errors.append(ValidationError(path, f"restriction related claim ref {ref} must reference a claim record"))
            for ref in safe_list(data, "supersedes_refs"):
                if ref in records and records[ref].get("record_type") != "restriction":
                    errors.append(ValidationError(path, f"restriction supersedes ref {ref} must reference a restriction record"))

        if data.get("record_type") == "guideline":
            for ref in safe_list(data, "source_refs"):
                if ref in records and records[ref].get("record_type") != "source":
                    errors.append(ValidationError(path, f"guideline source ref {ref} must reference a source record"))
            for ref in safe_list(data, "related_claim_refs"):
                if ref in records and records[ref].get("record_type") != "claim":
                    errors.append(ValidationError(path, f"guideline related claim ref {ref} must reference a claim record"))
            for ref in safe_list(data, "conflict_refs") + safe_list(data, "supersedes_refs"):
                if ref in records and records[ref].get("record_type") != "guideline":
                    errors.append(ValidationError(path, f"guideline relation ref {ref} must reference a guideline record"))

        if data.get("record_type") == "proposal":
            for ref in safe_list(data, "supersedes_refs"):
                if ref in records and records[ref].get("record_type") != "proposal":
                    errors.append(ValidationError(path, f"proposal supersedes ref {ref} must reference a proposal record"))

        if data.get("record_type") == "task":
            typed_ref_fields = {
                "related_claim_refs": "claim",
                "related_model_refs": "model",
                "related_flow_refs": "flow",
                "open_question_refs": "open_question",
                "plan_refs": "plan",
                "debt_refs": "debt",
                "action_refs": "action",
            }
            for key, expected_type in typed_ref_fields.items():
                for ref in safe_list(data, key):
                    if ref in records and records[ref].get("record_type") != expected_type:
                        errors.append(ValidationError(path, f"task {key} ref {ref} must reference a {expected_type} record"))

        if data.get("record_type") == "working_context":
            parent_ref = str(data.get("parent_context_ref", "")).strip()
            if parent_ref:
                if parent_ref not in records:
                    errors.append(ValidationError(path, f"missing parent_context_ref: {parent_ref}"))
                elif records[parent_ref].get("record_type") != "working_context":
                    errors.append(ValidationError(path, f"parent_context_ref {parent_ref} must reference a working_context record"))
            for ref in safe_list(data, "supersedes_refs"):
                if ref in records and records[ref].get("record_type") != "working_context":
                    errors.append(ValidationError(path, f"working_context supersedes ref {ref} must reference a working_context record"))
            for ref in safe_list(data, "topic_seed_refs"):
                if ref in records and records[ref].get("record_type") not in {"claim", "model", "flow", "task", "proposal", "open_question"}:
                    errors.append(
                        ValidationError(path, f"working_context topic_seed_ref {ref} must reference a claim/model/flow/task/proposal/open_question")
                    )
            for ref in safe_list(data, "pinned_refs"):
                if str(ref).startswith("CIX-"):
                    continue
                if ref not in records:
                    errors.append(ValidationError(path, f"missing pinned_ref: {ref}"))
            assumptions = data.get("assumptions", [])
            if isinstance(assumptions, list):
                for index, assumption in enumerate(assumptions, start=1):
                    if not isinstance(assumption, dict):
                        continue
                    for ref in safe_list(assumption, "support_refs"):
                        if ref not in records:
                            errors.append(ValidationError(path, f"missing assumption {index} support_ref: {ref}"))

        if data.get("record_type") == "plan":
            justified_by = safe_list(data, "justified_by")
            blocked_by = safe_list(data, "blocked_by")
            if any(ref in records and records[ref].get("record_type") != "claim" for ref in justified_by):
                errors.append(ValidationError(path, "plan.justified_by must reference claim records"))
            for ref in blocked_by:
                if ref in records and records[ref].get("record_type") not in {"claim", "plan", "debt"}:
                    errors.append(ValidationError(path, f"blocked_by ref {ref} must be claim, plan, or debt"))

        if data.get("record_type") == "debt":
            evidence_refs = safe_list(data, "evidence_refs")
            plan_refs = safe_list(data, "plan_refs")
            for ref in evidence_refs:
                if ref in records and records[ref].get("record_type") not in {"source", "claim", "action"}:
                    errors.append(ValidationError(path, f"evidence ref {ref} must be source, claim, or action"))
            for ref in plan_refs:
                if ref in records and records[ref].get("record_type") != "plan":
                    errors.append(ValidationError(path, f"plan ref {ref} must reference a plan record"))

        if data.get("record_type") == "model":
            for ref in safe_list(data, "claim_refs"):
                if ref in records and records[ref].get("record_type") != "claim":
                    errors.append(ValidationError(path, f"model claim ref {ref} must reference a claim record"))
            for ref in safe_list(data, "open_question_refs"):
                if ref in records and records[ref].get("record_type") != "open_question":
                    errors.append(ValidationError(path, f"model open question ref {ref} must reference an open_question record"))
            for ref in safe_list(data, "hypothesis_refs"):
                if ref in records and records[ref].get("record_type") != "claim":
                    errors.append(ValidationError(path, f"model hypothesis ref {ref} must reference a claim record"))
                elif ref in records and records[ref].get("status") != "tentative":
                    errors.append(ValidationError(path, f"model hypothesis ref {ref} must point to a tentative claim"))
                elif ref in records and claim_is_fallback(records[ref]):
                    errors.append(ValidationError(path, f"model hypothesis ref {ref} must point to an active tentative claim"))
            for ref in safe_list(data, "related_model_refs") + safe_list(data, "supersedes_refs") + safe_list(data, "promoted_from_refs"):
                if ref in records and records[ref].get("record_type") != "model":
                    errors.append(ValidationError(path, f"model relation {ref} must reference a model record"))
            if str(data.get("status", "")).strip() in {"working", "stable"}:
                weakened = [
                    ref
                    for ref in safe_list(data, "claim_refs")
                    if ref in records and str(records[ref].get("status", "")).strip() in {"contested", "rejected"}
                ]
                if weakened:
                    errors.append(
                        ValidationError(path, f"working/stable model depends on weakened claim(s): {', '.join(weakened)}")
                    )
                fallback_refs = [
                    ref
                    for ref in safe_list(data, "claim_refs")
                    if ref in records and claim_is_fallback(records[ref])
                ]
                if fallback_refs:
                    errors.append(
                        ValidationError(
                            path,
                            f"working/stable model depends on lifecycle fallback claim(s): {', '.join(fallback_refs)}",
                        )
                    )

        if data.get("record_type") == "flow":
            for ref in safe_list(data, "model_refs"):
                if ref in records and records[ref].get("record_type") != "model":
                    errors.append(ValidationError(path, f"flow model ref {ref} must reference a model record"))
            for ref in safe_list(data, "open_question_refs"):
                if ref in records and records[ref].get("record_type") != "open_question":
                    errors.append(ValidationError(path, f"flow open question ref {ref} must reference an open_question record"))
            for ref in safe_list(data, "supersedes_refs") + safe_list(data, "promoted_from_refs"):
                if ref in records and records[ref].get("record_type") != "flow":
                    errors.append(ValidationError(path, f"flow relation {ref} must reference a flow record"))
            for field_name in ("preconditions", "oracle"):
                block = data.get(field_name)
                if not isinstance(block, dict):
                    continue
                for key in ("claim_refs", "success_claim_refs", "failure_claim_refs", "hypothesis_refs"):
                    refs = block.get(key)
                    if refs is None:
                        continue
                    if not isinstance(refs, list):
                        continue
                    for ref in refs:
                        if ref in records and records[ref].get("record_type") != "claim":
                            errors.append(ValidationError(path, f"{field_name} ref {ref} must reference a claim record"))
                        elif ref in records and key == "hypothesis_refs" and records[ref].get("status") != "tentative":
                            errors.append(
                                ValidationError(path, f"{field_name}.hypothesis_refs {ref} must point to a tentative claim")
                            )
                        elif ref in records and key == "hypothesis_refs" and claim_is_fallback(records[ref]):
                            errors.append(
                                ValidationError(path, f"{field_name}.hypothesis_refs {ref} must point to an active tentative claim")
                            )
                if str(data.get("status", "")).strip() in {"working", "stable"}:
                    fallback_refs = []
                    for key in ("claim_refs", "success_claim_refs", "failure_claim_refs"):
                        refs = block.get(key)
                        if isinstance(refs, list):
                            fallback_refs.extend(ref for ref in refs if ref in records and claim_is_fallback(records[ref]))
                    if fallback_refs:
                        errors.append(
                            ValidationError(
                                path,
                                f"working/stable flow {field_name} depends on lifecycle fallback claim(s): {', '.join(sorted(set(fallback_refs)))}",
                            )
                        )
            if isinstance(data.get("steps"), list):
                for step in data.get("steps", []):
                    if not isinstance(step, dict):
                        continue
                    for ref in step.get("claim_refs", []):
                        if ref in records and records[ref].get("record_type") != "claim":
                            errors.append(ValidationError(path, f"flow step claim ref {ref} must reference a claim record"))
                    for ref in step.get("open_question_refs", []):
                        if ref in records and records[ref].get("record_type") != "open_question":
                            errors.append(
                                ValidationError(path, f"flow step open question ref {ref} must reference an open_question record")
                            )
                    if str(step.get("status", "")).strip() == "accepted-deviation":
                        for ref in step.get("accepted_deviation_refs", []):
                            if ref in records and records[ref].get("record_type") not in {"permission", "claim"}:
                                errors.append(
                                    ValidationError(path, f"accepted_deviation ref {ref} must reference permission or claim")
                                )
                    weakened = [
                        ref
                        for ref in step.get("claim_refs", [])
                        if ref in records and str(records[ref].get("status", "")).strip() in {"contested", "rejected"}
                    ]
                    if weakened and str(data.get("status", "")).strip() in {"working", "stable"}:
                        errors.append(
                            ValidationError(path, f"working/stable flow step depends on weakened claim(s): {', '.join(weakened)}")
                        )
                    fallback_refs = [
                        ref
                        for ref in step.get("claim_refs", [])
                        if ref in records and claim_is_fallback(records[ref])
                    ]
                    if fallback_refs and str(data.get("status", "")).strip() in {"working", "stable"}:
                        errors.append(
                            ValidationError(
                                path,
                                f"working/stable flow step depends on lifecycle fallback claim(s): {', '.join(fallback_refs)}",
                            )
                        )

        if data.get("record_type") == "open_question":
            for ref in safe_list(data, "related_claim_refs") + safe_list(data, "resolved_by_claim_refs"):
                if ref in records and records[ref].get("record_type") != "claim":
                    errors.append(ValidationError(path, f"open question claim ref {ref} must reference a claim record"))
            for ref in safe_list(data, "related_model_refs"):
                if ref in records and records[ref].get("record_type") != "model":
                    errors.append(ValidationError(path, f"open question model ref {ref} must reference a model record"))
            for ref in safe_list(data, "related_flow_refs"):
                if ref in records and records[ref].get("record_type") != "flow":
                    errors.append(ValidationError(path, f"open question flow ref {ref} must reference a flow record"))
    return errors
