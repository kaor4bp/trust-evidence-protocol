from __future__ import annotations

import json
import secrets
from datetime import datetime
from pathlib import Path

from .errors import ValidationError
from .ids import PROJECT_ID_PATTERN, TASK_ID_PATTERN, now_timestamp
from .io import write_json_file
from .paths import settings_path


ALLOWED_FREEDOM = {"proof-only", "evidence-authorized", "implementation-choice"}
PERMISSION_REQUIRED_FREEDOMS = {"implementation-choice"}
STRICTNESS_ORDER = {"proof-only": 0, "evidence-authorized": 1, "implementation-choice": 2}

HOOK_MODE_VALUES = {
    "session_start_hydrate": {"off", "on"},
    "user_prompt_notice": {"off", "on", "remind"},
    "pre_tool_use_guard": {"off", "warn", "enforce"},
    "post_tool_use_review": {"off", "notify", "invalidate"},
    "verbosity": {"quiet", "normal", "debug"},
}

DEFAULT_HOOK_SETTINGS = {
    "enabled": True,
    "session_start_hydrate": "on",
    "user_prompt_notice": "remind",
    "pre_tool_use_guard": "enforce",
    "post_tool_use_review": "invalidate",
    "verbosity": "normal",
}

CONTEXT_BUDGET_KEYS = {"hydration", "brief", "quotes", "guidelines", "record_details"}
CONTEXT_BUDGET_VALUES = {"compact", "normal", "debug", "on-demand"}

DEFAULT_CONTEXT_BUDGET = {
    "hydration": "normal",
    "brief": "normal",
    "quotes": "normal",
    "guidelines": "normal",
    "record_details": "on-demand",
}

INPUT_CAPTURE_MODES = {"off", "metadata-only", "capture"}
INPUT_FILE_MENTION_MODES = {"reference-only", "copy-allowed"}
ARTIFACT_COPY_MODES = {"reference-only", "copy-small", "copy-allowed"}

DEFAULT_INPUT_CAPTURE_SETTINGS = {
    "user_prompts": "capture",
    "file_mentions": "reference-only",
    "session_linking": True,
}

DEFAULT_ARTIFACT_POLICY = {
    "copy_mode": "reference-only",
    "max_copy_bytes": 1048576,
    "copy_allow_extensions": [],
    "copy_deny_globs": [".env", "*.pem", "*.key", "**/.git/**"],
}

CLEANUP_MODES = {"report-only", "archive", "delete"}
CLEANUP_ARCHIVE_FORMATS = {"zip"}

DEFAULT_CLEANUP_SETTINGS = {
    "mode": "report-only",
    "archive_format": "zip",
    "orphan_input_stale_after_days": 30,
    "orphan_record_stale_after_days": 90,
    "orphan_artifact_stale_after_days": 30,
    "delete_after_archive_days": 180,
}

LOGIC_SOLVER_BACKENDS = {"structural", "z3", "auto"}
LOGIC_SOLVER_OPTIONAL_BACKENDS = {"z3"}
LOGIC_SOLVER_MODES = {"candidate", "blocking"}
TOPIC_PREFILTER_BACKENDS = {"lexical", "nmf", "auto"}
TOPIC_PREFILTER_OPTIONAL_BACKENDS = {"nmf"}
TOPIC_PREFILTER_REBUILD_MODES = {"manual", "on-demand", "on-hydrate"}
ANALYSIS_MISSING_DEPENDENCY_POLICIES = {"warn", "error"}
ANALYSIS_INSTALL_POLICIES = {"never", "ask", "allow-safe"}

DEFAULT_ANALYSIS_SETTINGS = {
    "logic_solver": {
        "enabled": True,
        "backend": "structural",
        "optional_backends": ["z3"],
        "missing_dependency": "warn",
        "install_policy": "ask",
        "mode": "candidate",
        "timeout_ms": 2000,
        "max_symbols": 500,
        "max_rules": 100,
        "use_unsat_core": True,
    },
    "topic_prefilter": {
        "enabled": True,
        "backend": "lexical",
        "optional_backends": ["nmf"],
        "missing_dependency": "warn",
        "install_policy": "ask",
        "rebuild": "manual",
        "max_records": 5000,
    },
}

DEFAULT_SETTINGS = {
    "allowed_freedom": "proof-only",
    "hooks": DEFAULT_HOOK_SETTINGS,
    "context_budget": DEFAULT_CONTEXT_BUDGET,
    "input_capture": DEFAULT_INPUT_CAPTURE_SETTINGS,
    "artifact_policy": DEFAULT_ARTIFACT_POLICY,
    "cleanup": DEFAULT_CLEANUP_SETTINGS,
    "analysis": DEFAULT_ANALYSIS_SETTINGS,
    "current_task_ref": None,
    "current_project_ref": None,
}

_UNSET = object()


def strictness_requests_path(root: Path) -> Path:
    return root / "strictness_requests.jsonl"


def load_strictness_requests(root: Path) -> tuple[list[dict], list[str]]:
    path = strictness_requests_path(root)
    if not path.exists():
        return [], []
    entries: list[dict] = []
    errors: list[str] = []
    with path.open(encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                entry = json.loads(stripped)
            except json.JSONDecodeError as exc:
                errors.append(f"{path}: line {line_no}: invalid JSON: {exc}")
                continue
            if not isinstance(entry, dict):
                errors.append(f"{path}: line {line_no}: entry must be an object")
                continue
            entries.append(entry)
    return entries, errors


def write_strictness_requests(root: Path, entries: list[dict]) -> None:
    path = strictness_requests_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as handle:
        for entry in entries:
            handle.write(json.dumps(entry, ensure_ascii=False, sort_keys=True))
            handle.write("\n")
    tmp.replace(path)


def next_strictness_request_id() -> str:
    date = now_timestamp()[:10].replace("-", "")
    return f"REQ-{date}-{secrets.token_hex(4)}"


def is_strictness_escalation(current_value: str, next_value: str) -> bool:
    return STRICTNESS_ORDER.get(next_value, 0) > STRICTNESS_ORDER.get(current_value, 0)


def permission_allows_strictness(records: dict[str, dict], permission_ref: str, value: str) -> bool:
    permission = records.get(permission_ref)
    if not permission or permission.get("record_type") != "permission":
        return False
    grants = [str(grant).strip().lower() for grant in permission.get("grants", [])]
    needles = {
        f"allowed_freedom:{value}",
        f"allowed_freedom={value}",
        f"change-strictness:{value}",
        f"change-strictness={value}",
        f"strictness:{value}",
        f"strictness={value}",
        value,
    }
    return any(grant in needles or value in grant and "allowed_freedom" in grant for grant in grants)


def strictness_request_allows_change(
    records: dict[str, dict],
    entries: list[dict],
    request_ref: str | None,
    approval_source_ref: str | None,
    current_value: str,
    value: str,
    permission_ref: str | None,
) -> tuple[dict | None, str | None]:
    if not request_ref or not approval_source_ref:
        return None, (
            f"change-strictness {value} requires --request REQ-* and --approval-source SRC-* "
            "from an explicit user approval"
        )
    request = next((entry for entry in entries if str(entry.get("id", "")).strip() == request_ref), None)
    if not request:
        return None, f"missing strictness request {request_ref}"
    if str(request.get("status", "")).strip() != "pending":
        return None, f"strictness request {request_ref} is not pending"
    if str(request.get("from", "")).strip() != current_value:
        return None, f"strictness request {request_ref} was created for from={request.get('from')}, current={current_value}"
    if str(request.get("to", "")).strip() != value:
        return None, f"strictness request {request_ref} does not target {value}"
    if str(request.get("permission_ref") or "") != str(permission_ref or ""):
        return None, f"strictness request {request_ref} permission does not match --permission"

    source = records.get(approval_source_ref)
    if not source or source.get("record_type") != "source":
        return None, f"approval source {approval_source_ref} must reference a SRC-* source record"
    origin = source.get("origin", {})
    if not isinstance(origin, dict) or str(origin.get("kind", "")).strip() != "user":
        return None, f"approval source {approval_source_ref} must have origin.kind=user"
    if str(source.get("critique_status", "")).strip() != "accepted":
        return None, f"approval source {approval_source_ref} must have critique_status=accepted"
    quote = str(source.get("quote", ""))
    expected = f"TEP-APPROVE {request_ref}"
    if expected not in quote:
        return None, f"approval source {approval_source_ref} must quote {expected!r}"
    return request, None


def normalize_hook_settings(raw: object) -> dict:
    payload = dict(DEFAULT_HOOK_SETTINGS)
    if not isinstance(raw, dict):
        return payload

    enabled = raw.get("enabled", payload["enabled"])
    if isinstance(enabled, bool):
        payload["enabled"] = enabled

    for key, allowed_values in HOOK_MODE_VALUES.items():
        value = raw.get(key, payload[key])
        if isinstance(value, str) and value in allowed_values:
            payload[key] = value
    return payload


def normalize_context_budget(raw: object) -> dict:
    payload = dict(DEFAULT_CONTEXT_BUDGET)
    if not isinstance(raw, dict):
        return payload
    for key in CONTEXT_BUDGET_KEYS:
        value = raw.get(key, payload[key])
        if isinstance(value, str) and value in CONTEXT_BUDGET_VALUES:
            payload[key] = value
    return payload


def _bounded_int(raw: object, default: int, minimum: int, maximum: int) -> int:
    if isinstance(raw, bool):
        return default
    if isinstance(raw, int) and minimum <= raw <= maximum:
        return raw
    return default


def _normalize_optional_backends(raw: object, allowed: set[str], default: list[str]) -> list[str]:
    if not isinstance(raw, list):
        return list(default)
    values: list[str] = []
    for item in raw:
        if isinstance(item, str) and item in allowed and item not in values:
            values.append(item)
    return values


def _normalize_string_list(raw: object, default: list[str], max_items: int = 100) -> list[str]:
    if not isinstance(raw, list):
        return list(default)
    values: list[str] = []
    for item in raw:
        if isinstance(item, str):
            value = item.strip()
            if value and value not in values:
                values.append(value)
        if len(values) >= max_items:
            break
    return values


def normalize_input_capture_settings(raw: object) -> dict:
    payload = dict(DEFAULT_INPUT_CAPTURE_SETTINGS)
    if not isinstance(raw, dict):
        return payload
    user_prompts = raw.get("user_prompts")
    if isinstance(user_prompts, str) and user_prompts in INPUT_CAPTURE_MODES:
        payload["user_prompts"] = user_prompts
    file_mentions = raw.get("file_mentions")
    if isinstance(file_mentions, str) and file_mentions in INPUT_FILE_MENTION_MODES:
        payload["file_mentions"] = file_mentions
    session_linking = raw.get("session_linking")
    if isinstance(session_linking, bool):
        payload["session_linking"] = session_linking
    return payload


def normalize_artifact_policy(raw: object) -> dict:
    payload = {
        "copy_mode": DEFAULT_ARTIFACT_POLICY["copy_mode"],
        "max_copy_bytes": DEFAULT_ARTIFACT_POLICY["max_copy_bytes"],
        "copy_allow_extensions": list(DEFAULT_ARTIFACT_POLICY["copy_allow_extensions"]),
        "copy_deny_globs": list(DEFAULT_ARTIFACT_POLICY["copy_deny_globs"]),
    }
    if not isinstance(raw, dict):
        return payload
    copy_mode = raw.get("copy_mode")
    if isinstance(copy_mode, str) and copy_mode in ARTIFACT_COPY_MODES:
        payload["copy_mode"] = copy_mode
    payload["max_copy_bytes"] = _bounded_int(
        raw.get("max_copy_bytes"),
        payload["max_copy_bytes"],
        0,
        1073741824,
    )
    payload["copy_allow_extensions"] = _normalize_string_list(
        raw.get("copy_allow_extensions"),
        payload["copy_allow_extensions"],
    )
    payload["copy_deny_globs"] = _normalize_string_list(
        raw.get("copy_deny_globs"),
        payload["copy_deny_globs"],
    )
    return payload


def normalize_cleanup_settings(raw: object) -> dict:
    payload = dict(DEFAULT_CLEANUP_SETTINGS)
    if not isinstance(raw, dict):
        return payload
    mode = raw.get("mode")
    if isinstance(mode, str) and mode in CLEANUP_MODES:
        payload["mode"] = mode
    archive_format = raw.get("archive_format")
    if isinstance(archive_format, str) and archive_format in CLEANUP_ARCHIVE_FORMATS:
        payload["archive_format"] = archive_format
    for key in (
        "orphan_input_stale_after_days",
        "orphan_record_stale_after_days",
        "orphan_artifact_stale_after_days",
        "delete_after_archive_days",
    ):
        payload[key] = _bounded_int(raw.get(key), payload[key], 0, 3650)
    return payload


def normalize_analysis_settings(raw: object) -> dict:
    default_logic = DEFAULT_ANALYSIS_SETTINGS["logic_solver"]
    default_topic = DEFAULT_ANALYSIS_SETTINGS["topic_prefilter"]
    payload = {
        "logic_solver": {
            "enabled": default_logic["enabled"],
            "backend": default_logic["backend"],
            "optional_backends": list(default_logic["optional_backends"]),
            "missing_dependency": default_logic["missing_dependency"],
            "install_policy": default_logic["install_policy"],
            "mode": default_logic["mode"],
            "timeout_ms": default_logic["timeout_ms"],
            "max_symbols": default_logic["max_symbols"],
            "max_rules": default_logic["max_rules"],
            "use_unsat_core": default_logic["use_unsat_core"],
        },
        "topic_prefilter": {
            "enabled": default_topic["enabled"],
            "backend": default_topic["backend"],
            "optional_backends": list(default_topic["optional_backends"]),
            "missing_dependency": default_topic["missing_dependency"],
            "install_policy": default_topic["install_policy"],
            "rebuild": default_topic["rebuild"],
            "max_records": default_topic["max_records"],
        },
    }
    if not isinstance(raw, dict):
        return payload

    logic = raw.get("logic_solver")
    if isinstance(logic, dict):
        enabled = logic.get("enabled")
        if isinstance(enabled, bool):
            payload["logic_solver"]["enabled"] = enabled
        backend = logic.get("backend")
        if isinstance(backend, str) and backend in LOGIC_SOLVER_BACKENDS:
            payload["logic_solver"]["backend"] = backend
        payload["logic_solver"]["optional_backends"] = _normalize_optional_backends(
            logic.get("optional_backends"),
            LOGIC_SOLVER_OPTIONAL_BACKENDS,
            payload["logic_solver"]["optional_backends"],
        )
        missing_dependency = logic.get("missing_dependency")
        if isinstance(missing_dependency, str) and missing_dependency in ANALYSIS_MISSING_DEPENDENCY_POLICIES:
            payload["logic_solver"]["missing_dependency"] = missing_dependency
        install_policy = logic.get("install_policy")
        if isinstance(install_policy, str) and install_policy in ANALYSIS_INSTALL_POLICIES:
            payload["logic_solver"]["install_policy"] = install_policy
        mode = logic.get("mode")
        if isinstance(mode, str) and mode in LOGIC_SOLVER_MODES:
            payload["logic_solver"]["mode"] = mode
        payload["logic_solver"]["timeout_ms"] = _bounded_int(
            logic.get("timeout_ms"),
            payload["logic_solver"]["timeout_ms"],
            100,
            60000,
        )
        payload["logic_solver"]["max_symbols"] = _bounded_int(
            logic.get("max_symbols"),
            payload["logic_solver"]["max_symbols"],
            1,
            100000,
        )
        payload["logic_solver"]["max_rules"] = _bounded_int(
            logic.get("max_rules"),
            payload["logic_solver"]["max_rules"],
            0,
            100000,
        )
        use_unsat_core = logic.get("use_unsat_core")
        if isinstance(use_unsat_core, bool):
            payload["logic_solver"]["use_unsat_core"] = use_unsat_core

    topic = raw.get("topic_prefilter")
    if isinstance(topic, dict):
        enabled = topic.get("enabled")
        if isinstance(enabled, bool):
            payload["topic_prefilter"]["enabled"] = enabled
        backend = topic.get("backend")
        if isinstance(backend, str) and backend in TOPIC_PREFILTER_BACKENDS:
            payload["topic_prefilter"]["backend"] = backend
        payload["topic_prefilter"]["optional_backends"] = _normalize_optional_backends(
            topic.get("optional_backends"),
            TOPIC_PREFILTER_OPTIONAL_BACKENDS,
            payload["topic_prefilter"]["optional_backends"],
        )
        missing_dependency = topic.get("missing_dependency")
        if isinstance(missing_dependency, str) and missing_dependency in ANALYSIS_MISSING_DEPENDENCY_POLICIES:
            payload["topic_prefilter"]["missing_dependency"] = missing_dependency
        install_policy = topic.get("install_policy")
        if isinstance(install_policy, str) and install_policy in ANALYSIS_INSTALL_POLICIES:
            payload["topic_prefilter"]["install_policy"] = install_policy
        rebuild = topic.get("rebuild")
        if isinstance(rebuild, str) and rebuild in TOPIC_PREFILTER_REBUILD_MODES:
            payload["topic_prefilter"]["rebuild"] = rebuild
        payload["topic_prefilter"]["max_records"] = _bounded_int(
            topic.get("max_records"),
            payload["topic_prefilter"]["max_records"],
            1,
            1000000,
        )
    return payload


def normalize_settings_payload(raw: object) -> dict:
    payload = {
        "allowed_freedom": DEFAULT_SETTINGS["allowed_freedom"],
        "hooks": dict(DEFAULT_HOOK_SETTINGS),
        "context_budget": dict(DEFAULT_CONTEXT_BUDGET),
        "input_capture": normalize_input_capture_settings(None),
        "artifact_policy": normalize_artifact_policy(None),
        "cleanup": normalize_cleanup_settings(None),
        "analysis": normalize_analysis_settings(None),
        "current_task_ref": None,
        "current_project_ref": None,
    }
    if not isinstance(raw, dict):
        return payload

    allowed_freedom = raw.get("allowed_freedom")
    if isinstance(allowed_freedom, str) and allowed_freedom in ALLOWED_FREEDOM:
        payload["allowed_freedom"] = allowed_freedom

    payload["hooks"] = normalize_hook_settings(raw.get("hooks"))
    payload["context_budget"] = normalize_context_budget(raw.get("context_budget"))
    payload["input_capture"] = normalize_input_capture_settings(raw.get("input_capture"))
    payload["artifact_policy"] = normalize_artifact_policy(raw.get("artifact_policy"))
    payload["cleanup"] = normalize_cleanup_settings(raw.get("cleanup"))
    payload["analysis"] = normalize_analysis_settings(raw.get("analysis"))
    current_task_ref = raw.get("current_task_ref")
    if current_task_ref is None:
        payload["current_task_ref"] = None
    elif isinstance(current_task_ref, str) and TASK_ID_PATTERN.match(current_task_ref.strip()):
        payload["current_task_ref"] = current_task_ref.strip()
    current_project_ref = raw.get("current_project_ref")
    if current_project_ref is None:
        payload["current_project_ref"] = None
    elif isinstance(current_project_ref, str) and PROJECT_ID_PATTERN.match(current_project_ref.strip()):
        payload["current_project_ref"] = current_project_ref.strip()
    return payload


def load_settings(root: Path) -> dict:
    path = settings_path(root)
    if not path.exists():
        return normalize_settings_payload(None)
    try:
        with path.open(encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, json.JSONDecodeError):
        return normalize_settings_payload(None)
    return normalize_settings_payload(data)


def validate_settings_state(root: Path, records: dict[str, dict]) -> list[ValidationError]:
    path = settings_path(root)
    if path.exists():
        try:
            with path.open(encoding="utf-8") as handle:
                raw_settings = json.load(handle)
        except (OSError, json.JSONDecodeError) as exc:
            return [ValidationError(path, f"invalid settings.json: {exc}")]
        if not isinstance(raw_settings, dict):
            return [ValidationError(path, "settings.json must be an object")]
        raw_current_task_ref = raw_settings.get("current_task_ref")
        if raw_current_task_ref not in (None, ""):
            if not isinstance(raw_current_task_ref, str) or not TASK_ID_PATTERN.match(raw_current_task_ref.strip()):
                return [ValidationError(path, "current_task_ref must be empty or TASK-YYYYMMDD-xxxxxxxx")]
        raw_current_project_ref = raw_settings.get("current_project_ref")
        if raw_current_project_ref not in (None, ""):
            if not isinstance(raw_current_project_ref, str) or not PROJECT_ID_PATTERN.match(raw_current_project_ref.strip()):
                return [ValidationError(path, "current_project_ref must be empty or PRJ-YYYYMMDD-xxxxxxxx")]
        raw_hooks = raw_settings.get("hooks")
        if raw_hooks is not None and not isinstance(raw_hooks, dict):
            return [ValidationError(path, "hooks must be an object")]
        if isinstance(raw_hooks, dict):
            for key, value in raw_hooks.items():
                if key in HOOK_MODE_VALUES and value not in HOOK_MODE_VALUES[key]:
                    return [ValidationError(path, f"hooks.{key} has invalid value")]
        raw_context_budget = raw_settings.get("context_budget")
        if raw_context_budget is not None and not isinstance(raw_context_budget, dict):
            return [ValidationError(path, "context_budget must be an object")]
        if isinstance(raw_context_budget, dict):
            for key, value in raw_context_budget.items():
                if key in CONTEXT_BUDGET_KEYS and value not in CONTEXT_BUDGET_VALUES:
                    return [ValidationError(path, f"context_budget.{key} has invalid value")]
        raw_input_capture = raw_settings.get("input_capture")
        if raw_input_capture is not None and not isinstance(raw_input_capture, dict):
            return [ValidationError(path, "input_capture must be an object")]
        if isinstance(raw_input_capture, dict):
            if raw_input_capture.get("user_prompts") is not None and raw_input_capture.get("user_prompts") not in INPUT_CAPTURE_MODES:
                return [ValidationError(path, "input_capture.user_prompts has invalid value")]
            if (
                raw_input_capture.get("file_mentions") is not None
                and raw_input_capture.get("file_mentions") not in INPUT_FILE_MENTION_MODES
            ):
                return [ValidationError(path, "input_capture.file_mentions has invalid value")]
            session_linking = raw_input_capture.get("session_linking")
            if session_linking is not None and not isinstance(session_linking, bool):
                return [ValidationError(path, "input_capture.session_linking must be boolean")]
        raw_artifact_policy = raw_settings.get("artifact_policy")
        if raw_artifact_policy is not None and not isinstance(raw_artifact_policy, dict):
            return [ValidationError(path, "artifact_policy must be an object")]
        if isinstance(raw_artifact_policy, dict):
            if raw_artifact_policy.get("copy_mode") is not None and raw_artifact_policy.get("copy_mode") not in ARTIFACT_COPY_MODES:
                return [ValidationError(path, "artifact_policy.copy_mode has invalid value")]
            max_copy_bytes = raw_artifact_policy.get("max_copy_bytes")
            if max_copy_bytes is not None and (
                isinstance(max_copy_bytes, bool) or not isinstance(max_copy_bytes, int) or max_copy_bytes < 0 or max_copy_bytes > 1073741824
            ):
                return [ValidationError(path, "artifact_policy.max_copy_bytes has invalid value")]
            for key in ("copy_allow_extensions", "copy_deny_globs"):
                value = raw_artifact_policy.get(key)
                if value is not None and (not isinstance(value, list) or any(not isinstance(item, str) or not item.strip() for item in value)):
                    return [ValidationError(path, f"artifact_policy.{key} has invalid value")]
        raw_cleanup = raw_settings.get("cleanup")
        if raw_cleanup is not None and not isinstance(raw_cleanup, dict):
            return [ValidationError(path, "cleanup must be an object")]
        if isinstance(raw_cleanup, dict):
            if raw_cleanup.get("mode") is not None and raw_cleanup.get("mode") not in CLEANUP_MODES:
                return [ValidationError(path, "cleanup.mode has invalid value")]
            if raw_cleanup.get("archive_format") is not None and raw_cleanup.get("archive_format") not in CLEANUP_ARCHIVE_FORMATS:
                return [ValidationError(path, "cleanup.archive_format has invalid value")]
            for key in (
                "orphan_input_stale_after_days",
                "orphan_record_stale_after_days",
                "orphan_artifact_stale_after_days",
                "delete_after_archive_days",
            ):
                value = raw_cleanup.get(key)
                if value is not None and (isinstance(value, bool) or not isinstance(value, int) or value < 0 or value > 3650):
                    return [ValidationError(path, f"cleanup.{key} has invalid value")]
        raw_analysis = raw_settings.get("analysis")
        if raw_analysis is not None and not isinstance(raw_analysis, dict):
            return [ValidationError(path, "analysis must be an object")]
        if isinstance(raw_analysis, dict):
            raw_logic = raw_analysis.get("logic_solver")
            if raw_logic is not None and not isinstance(raw_logic, dict):
                return [ValidationError(path, "analysis.logic_solver must be an object")]
            if isinstance(raw_logic, dict):
                for key in ("enabled", "use_unsat_core"):
                    value = raw_logic.get(key)
                    if value is not None and not isinstance(value, bool):
                        return [ValidationError(path, f"analysis.logic_solver.{key} must be boolean")]
                if raw_logic.get("backend") is not None and raw_logic.get("backend") not in LOGIC_SOLVER_BACKENDS:
                    return [ValidationError(path, "analysis.logic_solver.backend has invalid value")]
                if raw_logic.get("mode") is not None and raw_logic.get("mode") not in LOGIC_SOLVER_MODES:
                    return [ValidationError(path, "analysis.logic_solver.mode has invalid value")]
                if (
                    raw_logic.get("missing_dependency") is not None
                    and raw_logic.get("missing_dependency") not in ANALYSIS_MISSING_DEPENDENCY_POLICIES
                ):
                    return [ValidationError(path, "analysis.logic_solver.missing_dependency has invalid value")]
                if raw_logic.get("install_policy") is not None and raw_logic.get("install_policy") not in ANALYSIS_INSTALL_POLICIES:
                    return [ValidationError(path, "analysis.logic_solver.install_policy has invalid value")]
                optional_backends = raw_logic.get("optional_backends")
                if optional_backends is not None:
                    if not isinstance(optional_backends, list) or any(item not in LOGIC_SOLVER_OPTIONAL_BACKENDS for item in optional_backends):
                        return [ValidationError(path, "analysis.logic_solver.optional_backends has invalid value")]
                for key, minimum, maximum in (("timeout_ms", 100, 60000), ("max_symbols", 1, 100000), ("max_rules", 0, 100000)):
                    value = raw_logic.get(key)
                    if value is not None and (isinstance(value, bool) or not isinstance(value, int) or value < minimum or value > maximum):
                        return [ValidationError(path, f"analysis.logic_solver.{key} has invalid value")]

            raw_topic = raw_analysis.get("topic_prefilter")
            if raw_topic is not None and not isinstance(raw_topic, dict):
                return [ValidationError(path, "analysis.topic_prefilter must be an object")]
            if isinstance(raw_topic, dict):
                enabled = raw_topic.get("enabled")
                if enabled is not None and not isinstance(enabled, bool):
                    return [ValidationError(path, "analysis.topic_prefilter.enabled must be boolean")]
                if raw_topic.get("backend") is not None and raw_topic.get("backend") not in TOPIC_PREFILTER_BACKENDS:
                    return [ValidationError(path, "analysis.topic_prefilter.backend has invalid value")]
                if (
                    raw_topic.get("missing_dependency") is not None
                    and raw_topic.get("missing_dependency") not in ANALYSIS_MISSING_DEPENDENCY_POLICIES
                ):
                    return [ValidationError(path, "analysis.topic_prefilter.missing_dependency has invalid value")]
                if raw_topic.get("install_policy") is not None and raw_topic.get("install_policy") not in ANALYSIS_INSTALL_POLICIES:
                    return [ValidationError(path, "analysis.topic_prefilter.install_policy has invalid value")]
                if raw_topic.get("rebuild") is not None and raw_topic.get("rebuild") not in TOPIC_PREFILTER_REBUILD_MODES:
                    return [ValidationError(path, "analysis.topic_prefilter.rebuild has invalid value")]
                optional_backends = raw_topic.get("optional_backends")
                if optional_backends is not None:
                    if not isinstance(optional_backends, list) or any(item not in TOPIC_PREFILTER_OPTIONAL_BACKENDS for item in optional_backends):
                        return [ValidationError(path, "analysis.topic_prefilter.optional_backends has invalid value")]
                max_records = raw_topic.get("max_records")
                if max_records is not None and (
                    isinstance(max_records, bool) or not isinstance(max_records, int) or max_records < 1 or max_records > 1000000
                ):
                    return [ValidationError(path, "analysis.topic_prefilter.max_records has invalid value")]

    settings = load_settings(root)
    current_task_ref = str(settings.get("current_task_ref") or "").strip()
    current_project_ref = str(settings.get("current_project_ref") or "").strip()
    errors: list[ValidationError] = []
    if current_task_ref not in records:
        if current_task_ref:
            errors.append(ValidationError(settings_path(root), f"current_task_ref missing task record: {current_task_ref}"))
    elif records[current_task_ref].get("record_type") != "task":
        errors.append(ValidationError(settings_path(root), f"current_task_ref must reference a task record: {current_task_ref}"))
    if current_project_ref not in records:
        if current_project_ref:
            errors.append(ValidationError(settings_path(root), f"current_project_ref missing project record: {current_project_ref}"))
    elif records[current_project_ref].get("record_type") != "project":
        errors.append(ValidationError(settings_path(root), f"current_project_ref must reference a project record: {current_project_ref}"))
    return errors


def write_settings(
    root: Path,
    allowed_freedom: str | None = None,
    hooks: dict | None = None,
    context_budget: dict | None = None,
    input_capture: dict | None = None,
    artifact_policy: dict | None = None,
    cleanup: dict | None = None,
    analysis: dict | None = None,
    current_task_ref: object = _UNSET,
    current_project_ref: object = _UNSET,
) -> None:
    payload = normalize_settings_payload(load_settings(root))
    if allowed_freedom in ALLOWED_FREEDOM:
        payload["allowed_freedom"] = allowed_freedom
    if hooks is not None:
        payload["hooks"] = normalize_hook_settings(hooks)
    if context_budget is not None:
        payload["context_budget"] = normalize_context_budget(context_budget)
    if input_capture is not None:
        payload["input_capture"] = normalize_input_capture_settings(input_capture)
    if artifact_policy is not None:
        payload["artifact_policy"] = normalize_artifact_policy(artifact_policy)
    if cleanup is not None:
        payload["cleanup"] = normalize_cleanup_settings(cleanup)
    if analysis is not None:
        payload["analysis"] = normalize_analysis_settings(analysis)
    if current_task_ref is not _UNSET:
        if current_task_ref is None:
            payload["current_task_ref"] = None
        elif isinstance(current_task_ref, str) and TASK_ID_PATTERN.match(current_task_ref.strip()):
            payload["current_task_ref"] = current_task_ref.strip()
        else:
            raise ValueError("current_task_ref must be empty or TASK-YYYYMMDD-xxxxxxxx")
    if current_project_ref is not _UNSET:
        if current_project_ref is None:
            payload["current_project_ref"] = None
        elif isinstance(current_project_ref, str) and PROJECT_ID_PATTERN.match(current_project_ref.strip()):
            payload["current_project_ref"] = current_project_ref.strip()
        else:
            raise ValueError("current_project_ref must be empty or PRJ-YYYYMMDD-xxxxxxxx")
    payload["updated_at"] = datetime.now().astimezone().isoformat(timespec="seconds")
    write_json_file(settings_path(root), payload)
