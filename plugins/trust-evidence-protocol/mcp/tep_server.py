#!/usr/bin/env python3
"""Minimal MCP stdio server for Trust Evidence Protocol lookup.

The server exposes bounded lookup tools. Front-door tools call core services
directly; legacy drill-down wrappers still delegate to the development CLI until
their service adapters are split out.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
CLI = PLUGIN_ROOT / "scripts" / "context_cli.py"
SERVER_VERSION = "0.4.9"
DEFAULT_PROTOCOL_VERSION = "2025-06-18"

plugin_root = str(PLUGIN_ROOT)
if plugin_root not in sys.path:
    sys.path.insert(0, plugin_root)

from tep_runtime.action_graph import build_next_step_payload, next_step_text_lines  # noqa: E402
from tep_runtime.agent_identity import agent_identity_scope, require_agent_private_key  # noqa: E402
from tep_runtime.chain_service import (  # noqa: E402
    augment_chain_service,
    augment_chain_text,
    read_chain_payload_file,
    validate_chain_service,
    validate_chain_text,
)
from tep_runtime.cli_common import TEP_ICON  # noqa: E402
from tep_runtime.context_root import resolve_context_root  # noqa: E402
from tep_runtime.evidence_service import record_evidence_service, record_evidence_text  # noqa: E402
from tep_runtime.io import context_write_lock  # noqa: E402
from tep_runtime.lookup_service import build_lookup_service_payload, lookup_text_lines  # noqa: E402
from tep_runtime.map_refresh import map_refresh_service, map_refresh_text_lines  # noqa: E402
from tep_runtime.map_session import (  # noqa: E402
    map_checkpoint_service,
    map_drilldown_service,
    map_drilldown_text_lines,
    map_move_service,
    map_open_service,
    map_view_service,
    map_view_text_lines,
)
from tep_runtime.migrations import (  # noqa: E402
    build_migration_dry_run_report,
    build_schema_migration_report,
    migration_report_text_lines,
)
from tep_runtime.reason_service import (  # noqa: E402
    reason_review_service,
    reason_review_text,
    reason_step_service,
    reason_step_text,
)
from tep_runtime.state_validation import collect_validation_errors  # noqa: E402
from tep_runtime.task_outcome_service import (  # noqa: E402
    task_outcome_check_service,
    task_outcome_check_text,
)


JsonObject = dict[str, Any]

CONTEXT_ROOT_DESCRIPTION = (
    "Path to TEP context root. Defaults to TEP_CONTEXT_ROOT, nearest .tep context_root, "
    "or ~/.tep_context. Legacy .codex_context requires explicit migration/debug tooling."
)


def context_property() -> JsonObject:
    return {"type": "string", "description": CONTEXT_ROOT_DESCRIPTION}


def agent_private_key_property() -> JsonObject:
    return {
        "type": "string",
        "description": (
            "Per-agent private key for owner-bound mutations. The agent invents and keeps this secret; "
            "the runtime stores only its fingerprint and thread-scoped bindings."
        ),
    }


def schema(
    properties: JsonObject,
    required: list[str] | None = None,
) -> JsonObject:
    properties = dict(properties)
    properties.setdefault(
        "cwd",
        {
            "type": "string",
            "description": (
                "Working directory used for .tep anchor resolution and relative paths. "
                "Pass the active agent workdir in multi-workspace contexts; otherwise MCP refuses unsafe global focus fallback."
            ),
        },
    )
    return {
        "type": "object",
        "properties": properties,
        "required": required or [],
        "additionalProperties": False,
    }


TOOLS: list[JsonObject] = [
    {
        "name": "brief_context",
        "description": (
            "Read a task-oriented TEP context brief: current workspace/project/task, relevant models, flows, "
            "claims, permissions, restrictions, guidelines, proposals, plans, debt, and questions. "
            "Use before answering, planning, or editing."
        ),
        "inputSchema": schema(
            {
                "context": context_property(),
                "task": {"type": "string", "description": "Concrete task or question to brief."},
                "limit": {"type": "integer", "minimum": 1, "maximum": 50, "default": 8},
                "detail": {
                    "type": "string",
                    "enum": ["compact", "full"],
                    "default": "compact",
                    "description": "Output detail. Compact is token-light; full preserves the expanded sectioned brief.",
                },
            },
            ["task"],
        ),
    },
    {
        "name": "next_step",
        "description": (
            "Read the compact TEP action route for the current agent intent. "
            "Use this before choosing between answering, planning, editing, testing, persisting, permission, or debugging."
        ),
        "inputSchema": schema(
            {
                "context": context_property(),
                "intent": {
                    "type": "string",
                    "enum": ["auto", "answer", "plan", "edit", "test", "persist", "permission", "debug", "after-mutation"],
                    "default": "auto",
                },
                "task": {"type": "string", "description": "Optional concrete task or prompt summary."},
                "detail": {"type": "string", "enum": ["compact", "full"], "default": "compact"},
                "format": {"type": "string", "enum": ["text", "json"], "default": "text"},
            },
        ),
    },
    {
        "name": "lookup",
        "description": (
            "One front door for deciding whether to search facts, code, theory/model context, broad research context, "
            "or policy/guideline context. Returns route data plus a compact chain_starter draft. "
            "Navigation only; run augment-chain/validate-decision before citing or authorizing from the draft."
        ),
        "inputSchema": schema(
            {
                "context": context_property(),
                "query": {"type": "string", "description": "Lookup query or task summary."},
                "reason": {
                    "type": "string",
                    "enum": [
                        "orientation",
                        "planning",
                        "answering",
                        "permission",
                        "editing",
                        "debugging",
                        "retrospective",
                        "curiosity",
                        "migration",
                    ],
                    "description": "Mandatory reason for telemetry, WCTX selection, and route shaping.",
                },
                "kind": {
                    "type": "string",
                    "enum": ["auto", "facts", "code", "theory", "research", "policy"],
                    "default": "auto",
                    "description": "Lookup route to choose. Auto uses lightweight lexical routing.",
                },
                "root": {"type": "string", "description": "Repository root for code lookup routes. Defaults to cwd."},
                "scope": {"type": "string", "enum": ["current", "all"], "default": "current"},
                "mode": {"type": "string", "enum": ["general", "research", "theory", "code"], "default": "general"},
                "agent_private_key": agent_private_key_property(),
                "format": {"type": "string", "enum": ["text", "json"], "default": "text"},
            },
            ["query", "reason"],
        ),
    },
    {
        "name": "reason_step",
        "description": (
            "Append a validated STEP-* claim-step from CLM transitions. Use claim_ref plus relation_claim_ref "
            "when continuing so the ledger follows the CLM graph."
        ),
        "inputSchema": schema(
            {
                "context": context_property(),
                "claim_ref": {"type": "string", "description": "CLM-* to append as the next semantic step."},
                "prev_claim_ref": {"type": "string", "description": "Previous CLM-* in the semantic chain."},
                "relation_claim_ref": {"type": "string", "description": "Relation CLM-* connecting prev_claim_ref -> claim_ref."},
                "prev_step_ref": {"type": "string", "description": "Previous STEP-* ledger entry for linear continuation."},
                "wctx_ref": {"type": "string", "description": "Owner-bound WCTX-* focus for this claim step."},
                "intent": {"type": "string", "default": "planning"},
                "mode": {
                    "type": "string",
                    "enum": ["answering", "curiosity", "debugging", "edit", "final", "permission", "planning", "test"],
                    "default": "planning",
                },
                "action_kind": {"type": "string", "description": "Optional protected action kind such as write, bash, git, or final."},
                "why": {"type": "string", "description": "Short public justification for appending this reasoning step."},
                "branch": {"type": "string", "default": "main"},
                "agent_private_key": agent_private_key_property(),
                "format": {"type": "string", "enum": ["text", "json"], "default": "text"},
            },
            ["claim_ref", "why"],
        ),
    },
    {
        "name": "record_evidence",
        "description": (
            "Mutating front door for capturing agent-supplied support. "
            "Creates or links provenance records such as FILE/RUN/SRC and optional CLM records mechanically."
        ),
        "inputSchema": schema(
            {
                "context": context_property(),
                "scope": {"type": "string", "description": "Evidence scope. Defaults to mcp.record_evidence."},
                "kind": {
                    "type": "string",
                    "enum": ["file-line", "url", "command-output", "user-input", "artifact"],
                },
                "quote": {"type": "string", "description": "Verbatim support quote or output excerpt."},
                "claim_text": {"type": "string", "description": "Optional claim statement to create as CLM-*."},
                "path": {"type": "string", "description": "File path for file-line evidence."},
                "line_start": {"type": "integer", "minimum": 1},
                "line_end": {"type": "integer", "minimum": 1},
                "url": {"type": "string", "description": "URL for url evidence."},
                "command": {"type": "string", "description": "Command for command-output evidence."},
                "command_cwd": {"type": "string", "description": "Working directory captured for command-output evidence."},
                "exit_code": {"type": "integer"},
                "stdout_quote": {"type": "string"},
                "stderr_quote": {"type": "string"},
                "action_kind": {"type": "string"},
                "input_ref": {"type": "string", "description": "INP-* provenance ref for user-input evidence."},
                "artifact_ref": {"type": "string", "description": "ART-* artifact ref for artifact evidence."},
                "claim_plane": {"type": "string", "enum": ["theory", "code", "runtime"]},
                "claim_status": {"type": "string", "enum": ["supported", "corroborated", "tentative"], "default": "supported"},
                "note": {"type": "string"},
                "tags": {"type": "array", "items": {"type": "string"}},
                "agent_private_key": agent_private_key_property(),
                "format": {"type": "string", "enum": ["text", "json"], "default": "text"},
            },
            ["kind", "quote"],
        ),
    },
    {
        "name": "reason_review",
        "description": (
            "Review a STEP-* ledger step and optionally create a one-shot GRANT-* for the current task/action."
        ),
        "inputSchema": schema(
            {
                "context": context_property(),
                "reason_ref": {"type": "string", "description": "STEP-* step to review."},
                "mode": {
                    "type": "string",
                    "enum": ["answering", "curiosity", "debugging", "edit", "final", "permission", "planning", "test"],
                    "default": "planning",
                },
                "action_kind": {"type": "string", "description": "Optional protected action kind such as write, bash, git, or final."},
                "grant": {"type": "boolean", "default": False},
                "ttl_seconds": {"type": "integer", "minimum": 1, "description": "Optional grant TTL; runtime settings still clamp the final value."},
                "command": {"type": "string", "description": "Optional exact command binding for shell grants."},
                "command_cwd": {"type": "string", "description": "Optional cwd binding for exact command grants."},
                "tool": {"type": "string", "default": "bash"},
                "agent_private_key": agent_private_key_property(),
                "format": {"type": "string", "enum": ["text", "json"], "default": "text"},
            },
            ["reason_ref"],
        ),
    },
    {
        "name": "task_outcome_check",
        "description": (
            "Read-only mechanical gate for autonomous task finalization. "
            "Checks whether done, blocked, or user-question is currently allowed; this is navigation/control, not proof."
        ),
        "inputSchema": schema(
            {
                "context": context_property(),
                "task_ref": {"type": "string", "description": "Optional TASK-*; defaults to current task focus."},
                "outcome": {
                    "type": "string",
                    "enum": ["done", "blocked", "user-question"],
                    "description": "Terminal outcome marker from the agent final message.",
                },
                "format": {"type": "string", "enum": ["text", "json"], "default": "text"},
            },
            ["outcome"],
        ),
    },
    {
        "name": "search_records",
        "description": (
            "Search canonical records by keyword. Defaults keep current project/task scope and rank current "
            "claims before fallback or archived claims."
        ),
        "inputSchema": schema(
            {
                "context": context_property(),
                "query": {"type": "string", "description": "Search query with meaningful 3+ char tokens."},
                "limit": {"type": "integer", "minimum": 1, "maximum": 100, "default": 12},
                "record_types": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional record type filters such as claim, guideline, model, flow, plan.",
                },
                "all_projects": {"type": "boolean", "default": False},
                "include_task_local": {"type": "boolean", "default": False},
                "include_fallback": {"type": "boolean", "default": False},
                "include_archived": {"type": "boolean", "default": False},
                "format": {"type": "string", "enum": ["text", "json"], "default": "text"},
            },
            ["query"],
        ),
    },
    {
        "name": "record_detail",
        "description": "Read one canonical record with its source quotes and direct incoming/outgoing links.",
        "inputSchema": schema(
            {
                "context": context_property(),
                "record": {"type": "string", "description": "Record id such as CLM-*, SRC-*, GLD-*, MODEL-*."},
                "format": {"type": "string", "enum": ["text", "json"], "default": "text"},
            },
            ["record"],
        ),
    },
    {
        "name": "claim_graph",
        "description": (
            "Search source-backed CLM-* claims by keyword and return a compact linked graph. "
            "Navigation only, not proof; use record_detail for proof-critical records."
        ),
        "inputSchema": schema(
            {
                "context": context_property(),
                "query": {"type": "string", "description": "Claim search query with meaningful 3+ char tokens."},
                "limit": {"type": "integer", "minimum": 1, "maximum": 50, "default": 8},
                "depth": {"type": "integer", "minimum": 1, "maximum": 4, "default": 1},
                "all_projects": {"type": "boolean", "default": False},
                "include_task_local": {"type": "boolean", "default": False},
                "include_fallback": {"type": "boolean", "default": False},
                "include_archived": {"type": "boolean", "default": False},
                "format": {"type": "string", "enum": ["text", "json"], "default": "text"},
            },
            ["query"],
        ),
    },
    {
        "name": "linked_records",
        "description": "Expand canonical record graph links around an anchor record.",
        "inputSchema": schema(
            {
                "context": context_property(),
                "record": {"type": "string", "description": "Anchor record id."},
                "direction": {"type": "string", "enum": ["incoming", "outgoing", "both"], "default": "both"},
                "depth": {"type": "integer", "minimum": 1, "maximum": 4, "default": 1},
                "format": {"type": "string", "enum": ["text", "json"], "default": "text"},
            },
            ["record"],
        ),
    },
    {
        "name": "telemetry_report",
        "description": "Read non-proof lookup telemetry for MCP/CLI/hook access, including raw claim read counts.",
        "inputSchema": schema(
            {
                "context": context_property(),
                "limit": {"type": "integer", "minimum": 1, "maximum": 50, "default": 10},
                "format": {"type": "string", "enum": ["text", "json"], "default": "text"},
            },
        ),
    },
    {
        "name": "backend_status",
        "description": (
            "Read optional backend availability, selected backend, current WSP/PRJ/TASK focus, and scoped storage diagnostics. "
            "Backend status is navigation/diagnostic data only, not proof."
        ),
        "inputSchema": schema(
            {
                "context": context_property(),
                "root": {"type": "string", "description": "Optional repository root for backend storage diagnostics."},
                "scope": {"type": "string", "enum": ["project", "workspace"], "description": "Optional backend index scope override."},
                "format": {"type": "string", "enum": ["text", "json"], "default": "text"},
            },
        ),
    },
    {
        "name": "backend_check",
        "description": (
            "Read one optional backend group or concrete backend id with selected/available/default-use and scoped storage diagnostics. "
            "Use before relying on an optional backend such as code_intelligence.cocoindex."
        ),
        "inputSchema": schema(
            {
                "context": context_property(),
                "backend": {"type": "string", "description": "Backend group or id such as code_intelligence, cocoindex, or code_intelligence.cocoindex."},
                "root": {"type": "string", "description": "Optional repository root for backend storage diagnostics."},
                "scope": {"type": "string", "enum": ["project", "workspace"], "description": "Optional backend index scope override."},
                "format": {"type": "string", "enum": ["text", "json"], "default": "text"},
            },
            ["backend"],
        ),
    },
    {
        "name": "guidelines_for",
        "description": (
            "Select active scoped GLD-* guidelines applicable to a concrete task. Use before sizeable "
            "code/test edits and cite returned ids plus short rule quotes."
        ),
        "inputSchema": schema(
            {
                "context": context_property(),
                "task": {"type": "string", "description": "Concrete task the guidelines should apply to."},
                "domain": {
                    "type": "string",
                    "enum": ["code", "tests", "review", "debugging", "architecture", "agent-behavior"],
                },
                "limit": {"type": "integer", "minimum": 1, "maximum": 50, "default": 8},
                "all_projects": {"type": "boolean", "default": False},
                "include_task_local": {"type": "boolean", "default": False},
                "format": {"type": "string", "enum": ["text", "json"], "default": "text"},
            },
            ["task"],
        ),
    },
    {
        "name": "code_search",
        "description": (
            "Search CIX-* code-index entries by explicit filters and projected fields. Optional semantic query "
            "is proxied through TEP-managed code backends such as CocoIndex. Output is navigation only, not proof."
        ),
        "inputSchema": schema(
            {
                "context": context_property(),
                "root": {"type": "string", "description": "Repository root for freshness checks. Defaults to current directory."},
                "query": {
                    "type": "string",
                    "description": "Optional semantic code query proxied through the configured TEP code backend.",
                },
                "scope": {
                    "type": "string",
                    "enum": ["project", "workspace"],
                    "description": "Optional backend index scope. Defaults to TEP CocoIndex settings.",
                },
                "paths": {"type": "array", "items": {"type": "string"}},
                "language": {"type": "string"},
                "code_kind": {"type": "string"},
                "imports": {"type": "array", "items": {"type": "string"}},
                "symbols": {"type": "array", "items": {"type": "string"}},
                "features": {"type": "array", "items": {"type": "string"}},
                "refs": {"type": "array", "items": {"type": "string"}},
                "link_candidate_refs": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Canonical refs to turn backend hits into CIX link suggestions without mutating records.",
                },
                "annotation_kind": {
                    "type": "string",
                    "enum": ["agent-note", "review-note", "TODO", "rationale", "risk", "smell"],
                },
                "annotation_categories": {"type": "array", "items": {"type": "string"}},
                "annotation_status": {
                    "type": "string",
                    "enum": ["active", "stale", "superseded", "invalid", "rejected"],
                },
                "include_stale_annotations": {"type": "boolean", "default": False},
                "stale": {"type": "string", "enum": ["true", "false"]},
                "include_missing": {"type": "boolean", "default": False},
                "include_superseded": {"type": "boolean", "default": False},
                "include_archived": {"type": "boolean", "default": False},
                "fields": {
                    "type": "string",
                    "description": "Comma-separated projection fields, e.g. target,imports,symbols,features,freshness.",
                },
                "limit": {"type": "integer", "minimum": 1, "maximum": 100, "default": 20},
                "format": {"type": "string", "enum": ["text", "json"], "default": "text"},
            },
        ),
    },
    {
        "name": "code_smell_report",
        "description": (
            "Read-only report of active CIX smell annotations. Smells are local navigation/critique, not proof "
            "or hard guidelines unless promoted to canonical records."
        ),
        "inputSchema": schema(
            {
                "context": context_property(),
                "root": {"type": "string", "description": "Repository root for stale annotation checks. Defaults to current directory."},
                "categories": {"type": "array", "items": {"type": "string"}},
                "severities": {"type": "array", "items": {"type": "string", "enum": ["low", "medium", "high", "critical"]}},
                "include_stale": {"type": "boolean", "default": False},
                "limit": {"type": "integer", "minimum": 1, "maximum": 100, "default": 20},
                "format": {"type": "string", "enum": ["text", "json"], "default": "text"},
            },
        ),
    },
    {
        "name": "code_feedback",
        "description": (
            "Review backend code-search hits as TEP feedback: CIX candidates, index suggestions, and link "
            "suggestions. Read-only; apply reviewed links with CLI code-feedback --apply or link-code."
        ),
        "inputSchema": schema(
            {
                "context": context_property(),
                "root": {"type": "string", "description": "Repository root for backend search. Defaults to current directory."},
                "query": {"type": "string", "description": "Semantic code query to review through the configured TEP code backend."},
                "paths": {"type": "array", "items": {"type": "string"}},
                "language": {"type": "string"},
                "link_candidate_refs": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Canonical refs to turn backend hits into CIX link suggestions without mutating records.",
                },
                "limit": {"type": "integer", "minimum": 1, "maximum": 100, "default": 20},
                "format": {"type": "string", "enum": ["text", "json"], "default": "text"},
            },
            ["query"],
        ),
    },
    {
        "name": "code_info",
        "description": "Read projected metadata for one CIX-* entry or path. CIX is navigation only, not proof.",
        "inputSchema": schema(
            {
                "context": context_property(),
                "root": {"type": "string", "description": "Repository root for freshness checks. Defaults to current directory."},
                "entry": {"type": "string", "description": "CIX-* id."},
                "path": {"type": "string", "description": "Indexed target path."},
                "fields": {"type": "string", "description": "Comma-separated projection fields."},
                "format": {"type": "string", "enum": ["text", "json"], "default": "text"},
            },
        ),
    },
    {
        "name": "cleanup_candidates",
        "description": (
            "Read-only triage report for stale or noisy records. Does not resolve, archive, delete, or mutate records."
        ),
        "inputSchema": schema(
            {
                "context": context_property(),
                "limit": {"type": "integer", "minimum": 1, "maximum": 100, "default": 20},
                "format": {"type": "string", "enum": ["text", "json"], "default": "text"},
            },
        ),
    },
    {
        "name": "cleanup_archives",
        "description": "Read-only cleanup archive catalog. Lists ARC-* archives or inspects one archive manifest.",
        "inputSchema": schema(
            {
                "context": context_property(),
                "archive": {"type": "string", "description": "Optional ARC-* id or archive zip path under the context root."},
                "limit": {"type": "integer", "minimum": 1, "maximum": 100, "default": 50},
                "format": {"type": "string", "enum": ["text", "json"], "default": "text"},
            },
        ),
    },
    {
        "name": "migration_dry_run",
        "description": (
            "Inspect an explicit legacy context input and return a TEP 0.4 migration report. "
            "Read-only: does not create backups, records, or target files."
        ),
        "inputSchema": schema(
            {
                "context": context_property(),
                "source": {
                    "type": "string",
                    "description": "Explicit legacy context root to inspect, such as an old .codex_context path.",
                },
                "target": {
                    "type": "string",
                    "description": "Target ~/.tep_context root for report planning. Defaults to context, TEP_CONTEXT_ROOT, or ~/.tep_context.",
                },
                "format": {"type": "string", "enum": ["text", "json"], "default": "text"},
            },
            ["source"],
        ),
    },
    {
        "name": "schema_migration_plan",
        "description": (
            "Read-only record schema migration plan for a .tep_context root. "
            "Does not write records."
        ),
        "inputSchema": schema(
            {
                "context": context_property(),
                "migrations": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional migration ids to run. Defaults to the full registered schema migration chain.",
                },
                "format": {"type": "string", "enum": ["text", "json"], "default": "text"},
            },
        ),
    },
    {
        "name": "schema_migration_apply",
        "description": (
            "Mutating record schema migration apply for a .tep_context root. "
            "Runs post-migration validation and writes only if the whole plan is clean."
        ),
        "inputSchema": schema(
            {
                "context": context_property(),
                "migrations": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional migration ids to run. Defaults to the full registered schema migration chain.",
                },
                "agent_private_key": agent_private_key_property(),
                "format": {"type": "string", "enum": ["text", "json"], "default": "text"},
            },
        ),
    },
    {
        "name": "augment_chain",
        "description": (
            "Read-only enrichment of an evidence-chain JSON file with canonical quotes, public record metadata, "
            "source quotes, and mechanical validation output. This does not create proof beyond records."
        ),
        "inputSchema": schema(
            {
                "context": context_property(),
                "file": {"type": "string", "description": "Path to an evidence-chain JSON file."},
                "format": {"type": "string", "enum": ["text", "json"], "default": "text"},
            },
            ["file"],
        ),
    },
    {
        "name": "validate_chain",
        "description": (
            "Read-only mechanical validation of an evidence-chain JSON file. "
            "Validity is not proof of reasoning quality; use the returned gaps and repair routes before decisive use."
        ),
        "inputSchema": schema(
            {
                "context": context_property(),
                "file": {"type": "string", "description": "Path to an evidence-chain JSON file."},
                "format": {"type": "string", "enum": ["text", "json"], "default": "text"},
            },
            ["file"],
        ),
    },
    {
        "name": "topic_search",
        "description": (
            "Search the generated lexical topic_index as a navigation prefilter. Topic matches are not proof."
        ),
        "inputSchema": schema(
            {
                "context": context_property(),
                "query": {"type": "string", "description": "Search query with meaningful 3+ char tokens."},
                "limit": {"type": "integer", "minimum": 1, "maximum": 100, "default": 12},
                "record_types": {"type": "array", "items": {"type": "string"}},
                "format": {"type": "string", "enum": ["text", "json"], "default": "text"},
            },
            ["query"],
        ),
    },
    {
        "name": "topic_info",
        "description": "Read generated topic terms and similar records for one record id. Navigation only, not proof.",
        "inputSchema": schema(
            {
                "context": context_property(),
                "record": {"type": "string", "description": "Canonical record id to inspect in topic_index."},
                "limit": {"type": "integer", "minimum": 1, "maximum": 50, "default": 8},
                "format": {"type": "string", "enum": ["text", "json"], "default": "text"},
            },
            ["record"],
        ),
    },
    {
        "name": "topic_conflict_candidates",
        "description": (
            "Read lexical overlap candidates for contradiction review. Candidates are not contradictions or proof."
        ),
        "inputSchema": schema(
            {
                "context": context_property(),
                "limit": {"type": "integer", "minimum": 1, "maximum": 100, "default": 20},
                "format": {"type": "string", "enum": ["text", "json"], "default": "text"},
            },
        ),
    },
    {
        "name": "attention_map",
        "description": "Read generated attention-map clusters and cold zones. Attention data is navigation only, not proof.",
        "inputSchema": schema(
            {
                "context": context_property(),
                "limit": {"type": "integer", "minimum": 1, "maximum": 100, "default": 12},
                "scope": {"type": "string", "enum": ["current", "all"], "default": "current"},
                "mode": {"type": "string", "enum": ["general", "research", "theory", "code"], "default": "general"},
                "format": {"type": "string", "enum": ["text", "json"], "default": "text"},
            },
        ),
    },
    {
        "name": "attention_diagram",
        "description": "Read a generated Mermaid attention graph over clusters, top records, established bridges, and curiosity probes. Diagram data is navigation only, not proof.",
        "inputSchema": schema(
            {
                "context": context_property(),
                "limit": {"type": "integer", "minimum": 1, "maximum": 100, "default": 8},
                "scope": {"type": "string", "enum": ["current", "all"], "default": "current"},
                "mode": {"type": "string", "enum": ["general", "research", "theory", "code"], "default": "general"},
                "detail": {"type": "string", "enum": ["compact", "full"], "default": "compact"},
                "format": {"type": "string", "enum": ["text", "json"], "default": "text"},
            },
        ),
    },
    {
        "name": "attention_diagram_compare",
        "description": "Compare compact and full attention-diagram metrics so agents can decide whether summary labels are worth requesting. Comparison is not proof.",
        "inputSchema": schema(
            {
                "context": context_property(),
                "limit": {"type": "integer", "minimum": 1, "maximum": 100, "default": 8},
                "scope": {"type": "string", "enum": ["current", "all"], "default": "current"},
                "mode": {"type": "string", "enum": ["general", "research", "theory", "code"], "default": "general"},
                "format": {"type": "string", "enum": ["text", "json"], "default": "text"},
            },
        ),
    },
    {
        "name": "curiosity_map",
        "description": (
            "Read a generated visual-thinking curiosity map with heat, cold zones, established bridges, "
            "candidate probes, and next inspection commands. Map data is navigation only, not proof."
        ),
        "inputSchema": schema(
            {
                "context": context_property(),
                "volume": {"type": "string", "enum": ["compact", "normal", "wide"], "default": "normal"},
                "scope": {"type": "string", "enum": ["current", "all"], "default": "current"},
                "mode": {"type": "string", "enum": ["general", "research", "theory", "code"], "default": "general"},
                "html": {
                    "type": "boolean",
                    "default": False,
                    "description": "When true, write a standalone HTML map under <context>/views/curiosity/ and return html_path.",
                },
                "format": {"type": "string", "enum": ["text", "json"], "default": "text"},
            },
        ),
    },
    {
        "name": "map_refresh",
        "description": (
            "Create or update durable MAP-* navigation cells from current attention/curiosity data. "
            "This is a mutating navigation operation; MAP-* records are not proof."
        ),
        "inputSchema": schema(
            {
                "context": context_property(),
                "volume": {"type": "string", "enum": ["compact", "normal", "wide"], "default": "compact"},
                "limit": {"type": "integer", "minimum": 1, "maximum": 50, "default": 5},
                "scope": {"type": "string", "enum": ["current", "all"], "default": "current"},
                "mode": {"type": "string", "enum": ["general", "research", "theory", "code"], "default": "general"},
                "dry_run": {"type": "boolean", "default": False},
                "agent_private_key": agent_private_key_property(),
                "format": {"type": "string", "enum": ["text", "json"], "default": "text"},
            },
        ),
    },
    {
        "name": "map_open",
        "description": "Open or replace the owner-bound WCTX map session and return a bounded map view. Navigation only, not proof.",
        "inputSchema": schema(
            {
                "context": context_property(),
                "query": {"type": "string", "description": "Task, topic, or map question to orient the session."},
                "scope": {"type": "string", "enum": ["current", "all"], "default": "current"},
                "mode": {"type": "string", "enum": ["general", "research", "theory", "code"], "default": "general"},
                "agent_private_key": agent_private_key_property(),
                "format": {"type": "string", "enum": ["text", "json"], "default": "text"},
            },
        ),
    },
    {
        "name": "map_view",
        "description": "Read the current owner-bound WCTX map session. Navigation only, not proof.",
        "inputSchema": schema(
            {
                "context": context_property(),
                "map_session_ref": {"type": "string", "description": "WCTX-*#map-session. Defaults to current owned WCTX session."},
                "agent_private_key": agent_private_key_property(),
                "format": {"type": "string", "enum": ["text", "json"], "default": "text"},
            },
        ),
    },
    {
        "name": "map_move",
        "description": "Move the owner-bound WCTX map session to another MAP-* zone. Navigation only, not proof.",
        "inputSchema": schema(
            {
                "context": context_property(),
                "map_session_ref": {"type": "string", "description": "WCTX-*#map-session.", "minLength": 1},
                "target": {"type": "string", "description": "MAP-* ref or MZONE-MAP-* zone id.", "minLength": 1},
                "agent_private_key": agent_private_key_property(),
                "format": {"type": "string", "enum": ["text", "json"], "default": "text"},
            },
            ["map_session_ref", "target"],
        ),
    },
    {
        "name": "map_drilldown",
        "description": "Return navigation drilldown hints for a map or record ref. Routes are not proof.",
        "inputSchema": schema(
            {
                "context": context_property(),
                "map_session_ref": {"type": "string", "description": "WCTX-*#map-session.", "minLength": 1},
                "record": {"type": "string", "description": "MAP-*/CLM-*/SRC-* or other canonical ref to inspect.", "minLength": 1},
                "agent_private_key": agent_private_key_property(),
                "format": {"type": "string", "enum": ["text", "json"], "default": "text"},
            },
            ["map_session_ref", "record"],
        ),
    },
    {
        "name": "map_checkpoint",
        "description": "Persist a checkpoint in the owner-bound WCTX map session. Navigation state only, not proof.",
        "inputSchema": schema(
            {
                "context": context_property(),
                "map_session_ref": {"type": "string", "description": "WCTX-*#map-session.", "minLength": 1},
                "note": {"type": "string", "description": "Short checkpoint note."},
                "agent_private_key": agent_private_key_property(),
                "format": {"type": "string", "enum": ["text", "json"], "default": "text"},
            },
            ["map_session_ref"],
        ),
    },
    {
        "name": "curiosity_probes",
        "description": "Read generated bounded curiosity probes over attention clusters. Probes are questions, not proof.",
        "inputSchema": schema(
            {
                "context": context_property(),
                "budget": {"type": "integer", "minimum": 1, "maximum": 100, "default": 8},
                "scope": {"type": "string", "enum": ["current", "all"], "default": "current"},
                "mode": {"type": "string", "enum": ["general", "research", "theory", "code"], "default": "general"},
                "format": {"type": "string", "enum": ["text", "json"], "default": "text"},
            },
        ),
    },
    {
        "name": "map_brief",
        "description": "Read a compact Map Graph projection with topology islands, bridge pressure, candidate probes, and next inspection commands. Navigation only, not proof.",
        "inputSchema": schema(
            {
                "context": context_property(),
                "volume": {"type": "string", "enum": ["compact", "normal", "wide"], "default": "compact"},
                "limit": {"type": "integer", "minimum": 1, "maximum": 50, "default": 6},
                "scope": {"type": "string", "enum": ["current", "all"], "default": "current"},
                "mode": {"type": "string", "enum": ["general", "research", "theory", "code"], "default": "general"},
                "format": {"type": "string", "enum": ["text", "json"], "default": "text"},
            },
        ),
    },
    {
        "name": "probe_inspect",
        "description": "Inspect one generated curiosity probe with canonical record details and direct link status. Inspection is navigation only, not proof.",
        "inputSchema": schema(
            {
                "context": context_property(),
                "index": {"type": "integer", "minimum": 1, "maximum": 100, "default": 1},
                "scope": {"type": "string", "enum": ["current", "all"], "default": "current"},
                "mode": {"type": "string", "enum": ["general", "research", "theory", "code"], "default": "general"},
                "format": {"type": "string", "enum": ["text", "json"], "default": "text"},
            },
        ),
    },
    {
        "name": "probe_chain_draft",
        "description": "Draft a mechanical evidence-chain skeleton from one curiosity probe. Draft is not proof.",
        "inputSchema": schema(
            {
                "context": context_property(),
                "index": {"type": "integer", "minimum": 1, "maximum": 100, "default": 1},
                "scope": {"type": "string", "enum": ["current", "all"], "default": "current"},
                "mode": {"type": "string", "enum": ["general", "research", "theory", "code"], "default": "general"},
                "format": {"type": "string", "enum": ["text", "json"], "default": "text"},
            },
        ),
    },
    {
        "name": "probe_route",
        "description": "Generate an ordered mechanical inspection route for one curiosity probe. Route is navigation only, not proof.",
        "inputSchema": schema(
            {
                "context": context_property(),
                "index": {"type": "integer", "minimum": 1, "maximum": 100, "default": 1},
                "scope": {"type": "string", "enum": ["current", "all"], "default": "current"},
                "mode": {"type": "string", "enum": ["general", "research", "theory", "code"], "default": "general"},
                "format": {"type": "string", "enum": ["text", "json"], "default": "text"},
            },
        ),
    },
    {
        "name": "probe_pack",
        "description": "Read a compact mechanical bundle of top curiosity probes, inspection summaries, and chain-draft validation. Pack is not proof.",
        "inputSchema": schema(
            {
                "context": context_property(),
                "budget": {"type": "integer", "minimum": 1, "maximum": 20, "default": 3},
                "scope": {"type": "string", "enum": ["current", "all"], "default": "current"},
                "mode": {"type": "string", "enum": ["general", "research", "theory", "code"], "default": "general"},
                "detail": {"type": "string", "enum": ["compact", "full"], "default": "compact"},
                "format": {"type": "string", "enum": ["text", "json"], "default": "text"},
            },
        ),
    },
    {
        "name": "probe_pack_compare",
        "description": "Compare compact and full probe-pack metrics so agents can decide whether expanded context is worth requesting. Comparison is not proof.",
        "inputSchema": schema(
            {
                "context": context_property(),
                "budget": {"type": "integer", "minimum": 1, "maximum": 20, "default": 3},
                "scope": {"type": "string", "enum": ["current", "all"], "default": "current"},
                "mode": {"type": "string", "enum": ["general", "research", "theory", "code"], "default": "general"},
                "format": {"type": "string", "enum": ["text", "json"], "default": "text"},
            },
        ),
    },
    {
        "name": "working_contexts",
        "description": "Read WCTX-* operational working contexts. WCTX is handoff/focus context, not proof.",
        "inputSchema": schema(
            {
                "context": context_property(),
                "record": {"type": "string", "description": "Optional WCTX-* id."},
                "all": {"type": "boolean", "default": False},
                "format": {"type": "string", "enum": ["text", "json"], "default": "text"},
            },
        ),
    },
    {
        "name": "working_context_drift",
        "description": (
            "Read-only check that compares a task summary against active WCTX-* focus. "
            "Use before persisting task-local conclusions after topic/repo/task-type drift."
        ),
        "inputSchema": schema(
            {
                "context": context_property(),
                "task": {"type": "string", "description": "Current user task or planned task summary."},
                "format": {"type": "string", "enum": ["text", "json"], "default": "text"},
            },
            ["task"],
        ),
    },
    {
        "name": "workspace_admission",
        "description": (
            "Read-only guard before analyzing or persisting facts for an external repo. "
            "If it requires a decision, ask whether to create a new workspace, add a project to the current workspace, or inspect read-only."
        ),
        "inputSchema": schema(
            {
                "context": context_property(),
                "repo": {"type": "string", "description": "Repository/workdir path to classify against current WSP/PRJ focus."},
                "format": {"type": "string", "enum": ["text", "json"], "default": "text"},
            },
            ["repo"],
        ),
    },
    {
        "name": "logic_search",
        "description": "Search generated CLM.logic predicate atoms and rules. Logic index is checking/navigation only, not proof.",
        "inputSchema": schema(
            {
                "context": context_property(),
                "predicate": {"type": "string"},
                "symbol": {"type": "string"},
                "claim": {"type": "string", "description": "Optional CLM-* filter."},
                "limit": {"type": "integer", "minimum": 1, "maximum": 100, "default": 20},
                "format": {"type": "string", "enum": ["text", "json"], "default": "text"},
            },
        ),
    },
    {
        "name": "logic_check",
        "description": "Read-only predicate consistency check over CLM.logic blocks. Does not mutate records.",
        "inputSchema": schema(
            {
                "context": context_property(),
                "limit": {"type": "integer", "minimum": 1, "maximum": 100, "default": 20},
                "format": {"type": "string", "enum": ["text", "json"], "default": "text"},
            },
        ),
    },
    {
        "name": "logic_graph",
        "description": (
            "Read generated CLM.logic vocabulary graph for symbols, predicates, rule variables, and pressure smells. "
            "Logic graph is navigation only, not proof."
        ),
        "inputSchema": schema(
            {
                "context": context_property(),
                "symbol": {"type": "string", "description": "Optional typed symbol filter such as service:api."},
                "predicate": {"type": "string", "description": "Optional predicate filter."},
                "smells": {"type": "boolean", "default": False},
                "limit": {"type": "integer", "minimum": 1, "maximum": 100, "default": 20},
                "format": {"type": "string", "enum": ["text", "json"], "default": "text"},
            },
        ),
    },
    {
        "name": "logic_conflict_candidates",
        "description": "Read predicate-level conflict candidates. Candidates are not proof and do not change claim status.",
        "inputSchema": schema(
            {
                "context": context_property(),
                "limit": {"type": "integer", "minimum": 1, "maximum": 100, "default": 20},
                "format": {"type": "string", "enum": ["text", "json"], "default": "text"},
            },
        ),
    },
]


def as_bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    return bool(value)


def as_int(value: Any, default: int, minimum: int, maximum: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = default
    return max(minimum, min(maximum, parsed))


def as_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    return [str(value)] if str(value).strip() else []


def as_format(value: Any) -> str:
    return "json" if value == "json" else "text"


def agent_private_key_arg(args: JsonObject) -> str:
    return str(args.get("agent_private_key") or "").strip()


def require_agent_private_key_arg(args: JsonObject) -> str | None:
    try:
        require_agent_private_key(agent_private_key_arg(args) or None)
    except RuntimeError as exc:
        return str(exc)
    return None


def context_path(args: JsonObject) -> str | None:
    value = args.get("context")
    return str(value) if value else None


def call_cwd(args: JsonObject) -> Path:
    value = args.get("cwd")
    return Path(str(value)).expanduser().resolve() if value else Path.cwd()


def has_nearest_anchor(cwd: Path) -> bool:
    current = cwd.resolve()
    for candidate in (current, *current.parents):
        if (candidate / ".tep").is_file():
            return True
    return False


def nearest_anchor_has_workspace(cwd: Path) -> bool:
    current = cwd.resolve()
    for candidate in (current, *current.parents):
        anchor = candidate / ".tep"
        if anchor.is_file():
            try:
                data = json.loads(anchor.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                return False
            return bool(str(data.get("workspace_ref") or "").strip().startswith("WSP-"))
    return False


def active_workspace_count(context_root: Path) -> int:
    workspace_root = context_root / "records" / "workspace"
    if not workspace_root.is_dir():
        return 0
    count = 0
    for path in workspace_root.glob("WSP-*.json"):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if data.get("record_type") == "workspace" and data.get("status") == "active":
            count += 1
    return count


def mcp_context_root(args: JsonObject) -> Path | None:
    context = context_path(args) or os.environ.get("TEP_CONTEXT_ROOT")
    root = resolve_context_root(context, start=call_cwd(args))
    return root.resolve() if root else None


def load_mcp_records(root: Path) -> tuple[dict[str, dict] | None, str | None]:
    records, errors = collect_validation_errors(root)
    if errors:
        return records, "\n".join(f"{error.path}: {error.message}" for error in errors)
    return records, None


def unsafe_unanchored_fallback(args: JsonObject, cwd: Path) -> str | None:
    context_root = mcp_context_root(args)
    if context_root is None or active_workspace_count(context_root) == 0:
        return None
    if nearest_anchor_has_workspace(cwd):
        return None
    return (
        "MCP workspace anchor is required: refusing to use global TEP focus while active workspaces exist. "
        "Pass `cwd` pointing to a workdir with a `.tep` file that declares `workspace_ref`, or create/validate the local anchor first."
    )


def run_cli(args: JsonObject, cli_args: list[str]) -> tuple[bool, str]:
    command = [sys.executable, str(CLI)]
    context = context_path(args)
    if context:
        command.extend(["--context", context])
    command.extend(cli_args)
    cwd = call_cwd(args)
    if not cwd.is_dir():
        return False, f"cwd is not a directory: {cwd}"
    unsafe_fallback = unsafe_unanchored_fallback(args, cwd)
    if unsafe_fallback:
        return False, unsafe_fallback
    result = subprocess.run(
        command,
        cwd=cwd,
        env={**os.environ, "TEP_ACCESS_CHANNEL": "mcp"},
        capture_output=True,
        text=True,
        check=False,
    )
    output = result.stdout.strip()
    if result.stderr.strip():
        output = f"{output}\n\nstderr:\n{result.stderr.strip()}" if output else f"stderr:\n{result.stderr.strip()}"
    if not output:
        output = f"command exited with status {result.returncode}"
    return result.returncode == 0, output


def add_flag(cli_args: list[str], condition: bool, flag: str) -> None:
    if condition:
        cli_args.append(flag)


def add_repeated(cli_args: list[str], flag: str, values: list[str]) -> None:
    for value in values:
        cli_args.extend([flag, value])


def tool_brief_context(args: JsonObject) -> tuple[bool, str]:
    return run_cli(
        args,
        [
            "brief-context",
            "--task",
            str(args.get("task", "")),
            "--limit",
            str(as_int(args.get("limit"), 8, 1, 50)),
            "--detail",
            str(args.get("detail") or "compact"),
        ],
    )


def tool_next_step(args: JsonObject) -> tuple[bool, str]:
    cwd = call_cwd(args)
    if not cwd.is_dir():
        return False, f"cwd is not a directory: {cwd}"
    root = mcp_context_root(args)
    if root is None:
        return False, "Could not resolve TEP context root"
    unsafe_fallback = unsafe_unanchored_fallback(args, cwd)
    if unsafe_fallback:
        return False, unsafe_fallback
    records, error = load_mcp_records(root)
    if error:
        return False, error
    assert records is not None
    payload = build_next_step_payload(
        records,
        root,
        intent=str(args.get("intent") or "auto"),
        task=str(args.get("task") or ""),
    )
    if as_format(args.get("format")) == "json":
        return True, json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)
    return True, "\n".join(next_step_text_lines(payload, TEP_ICON, detail=str(args.get("detail") or "compact")))


def tool_lookup(args: JsonObject) -> tuple[bool, str]:
    cwd = call_cwd(args)
    if not cwd.is_dir():
        return False, f"cwd is not a directory: {cwd}"
    root = mcp_context_root(args)
    if root is None:
        return False, "Could not resolve TEP context root"
    unsafe_fallback = unsafe_unanchored_fallback(args, cwd)
    if unsafe_fallback:
        return False, unsafe_fallback
    records, load_error = load_mcp_records(root)
    if load_error:
        return False, load_error
    assert records is not None
    with agent_identity_scope(agent_private_key_arg(args)):
        payload, error = build_lookup_service_payload(
            root,
            records,
            query=str(args.get("query", "")),
            kind=str(args.get("kind") or "auto"),
            root_path=str(args.get("root") or cwd),
            scope=str(args.get("scope") or "current"),
            mode=str(args.get("mode") or "general"),
            reason=str(args.get("reason") or ""),
            channel="mcp",
        )
    if error:
        return False, error
    assert payload is not None
    if as_format(args.get("format")) == "json":
        return True, json.dumps(payload, ensure_ascii=False, indent=2)
    return True, "\n".join(lookup_text_lines(payload))


def tool_record_evidence(args: JsonObject) -> tuple[bool, str]:
    cwd = call_cwd(args)
    if not cwd.is_dir():
        return False, f"cwd is not a directory: {cwd}"
    root = mcp_context_root(args)
    if root is None:
        return False, "Could not resolve TEP context root"
    unsafe_fallback = unsafe_unanchored_fallback(args, cwd)
    if unsafe_fallback:
        return False, unsafe_fallback
    token_error = require_agent_private_key_arg(args)
    if token_error:
        return False, token_error
    try:
        with agent_identity_scope(agent_private_key_arg(args)), context_write_lock(root):
            records, load_error = load_mcp_records(root)
            if load_error:
                return False, load_error
            assert records is not None
            payload, error = record_evidence_service(
                root,
                records,
                scope=str(args.get("scope") or "mcp.record_evidence"),
                kind=str(args.get("kind") or ""),
                quote=str(args.get("quote") or ""),
                path_value=str(args.get("path") or "").strip() or None,
                line=as_int(args.get("line_start"), 0, 1, 1_000_000) if args.get("line_start") is not None else None,
                end_line=as_int(args.get("line_end"), 0, 1, 1_000_000) if args.get("line_end") is not None else None,
                url=str(args.get("url") or "").strip() or None,
                command=str(args.get("command") or "").strip() or None,
                cwd=str(args.get("command_cwd") or "").strip() or str(cwd),
                exit_code=int(args["exit_code"]) if args.get("exit_code") is not None else None,
                stdout_quote=str(args.get("stdout_quote") or "") or None,
                stderr_quote=str(args.get("stderr_quote") or "") or None,
                action_kind=str(args.get("action_kind") or "").strip() or None,
                input_refs=[str(args.get("input_ref") or "").strip()] if args.get("input_ref") else [],
                artifact_refs=[str(args.get("artifact_ref") or "").strip()] if args.get("artifact_ref") else [],
                claim_statement=str(args.get("claim_text") or "").strip() or None,
                claim_plane=str(args.get("claim_plane") or "").strip() or None,
                claim_status=str(args.get("claim_status") or "supported"),
                tags=as_list(args.get("tags")),
                note=str(args.get("note") or ""),
                base_cwd=cwd,
            )
    except TimeoutError as exc:
        return False, str(exc)
    if error:
        return False, error
    assert payload is not None
    if as_format(args.get("format")) == "json":
        return True, json.dumps(payload, ensure_ascii=False, indent=2)
    return True, record_evidence_text(payload, root)


def tool_reason_step(args: JsonObject) -> tuple[bool, str]:
    cwd = call_cwd(args)
    if not cwd.is_dir():
        return False, f"cwd is not a directory: {cwd}"
    root = mcp_context_root(args)
    if root is None:
        return False, "Could not resolve TEP context root"
    unsafe_fallback = unsafe_unanchored_fallback(args, cwd)
    if unsafe_fallback:
        return False, unsafe_fallback
    records, load_error = load_mcp_records(root)
    if load_error:
        return False, load_error
    assert records is not None
    token_error = require_agent_private_key_arg(args)
    if token_error:
        return False, token_error
    claim_ref = str(args.get("claim_ref") or "").strip()
    if not claim_ref:
        return False, "reason_step requires claim_ref for STEP-*"
    with agent_identity_scope(agent_private_key_arg(args)):
        reason, error = reason_step_service(
            root,
            records,
            claim_ref=claim_ref or None,
            prev_claim_ref=str(args.get("prev_claim_ref") or "").strip() or None,
            relation_claim_ref=str(args.get("relation_claim_ref") or "").strip() or None,
            prev_step_ref=str(args.get("prev_step_ref") or "").strip() or None,
            wctx_ref=str(args.get("wctx_ref") or "").strip() or None,
            intent=str(args.get("intent") or "planning"),
            mode=str(args.get("mode") or "planning"),
            action_kind=str(args.get("action_kind") or "").strip() or None,
            why=str(args.get("why") or ""),
            branch=str(args.get("branch") or "main"),
        )
    if error:
        if as_format(args.get("format")) == "json" and isinstance(reason, dict):
            return False, json.dumps(reason, ensure_ascii=False, indent=2)
        return False, error
    assert reason is not None
    if as_format(args.get("format")) == "json":
        return True, json.dumps(reason, ensure_ascii=False, indent=2)
    return True, reason_step_text(
        reason,
        str(args.get("mode") or "planning"),
        str(args.get("action_kind") or "").strip() or None,
    )


def tool_reason_review(args: JsonObject) -> tuple[bool, str]:
    cwd = call_cwd(args)
    if not cwd.is_dir():
        return False, f"cwd is not a directory: {cwd}"
    root = mcp_context_root(args)
    if root is None:
        return False, "Could not resolve TEP context root"
    unsafe_fallback = unsafe_unanchored_fallback(args, cwd)
    if unsafe_fallback:
        return False, unsafe_fallback
    _, load_error = load_mcp_records(root)
    if load_error:
        return False, load_error
    token_error = require_agent_private_key_arg(args)
    if token_error:
        return False, token_error
    ttl_seconds = None
    if args.get("ttl_seconds") is not None:
        ttl_seconds = as_int(args.get("ttl_seconds"), 0, 1, 604800)
    with agent_identity_scope(agent_private_key_arg(args)):
        payload, error = reason_review_service(
            root,
            reason_ref=str(args.get("reason_ref") or ""),
            mode=str(args.get("mode") or "planning"),
            action_kind=str(args.get("action_kind") or "").strip() or None,
            grant=as_bool(args.get("grant")),
            ttl_seconds=ttl_seconds,
            command=str(args.get("command") or "").strip() or None,
            cwd=str(args.get("command_cwd") or "").strip() or None,
            tool=str(args.get("tool") or "bash"),
        )
    if error:
        return False, error
    assert payload is not None
    if as_format(args.get("format")) == "json":
        return True, json.dumps(payload, ensure_ascii=False, indent=2)
    return True, reason_review_text(
        payload,
        str(args.get("reason_ref") or ""),
        as_bool(args.get("grant")),
    )


def tool_task_outcome_check(args: JsonObject) -> tuple[bool, str]:
    cwd = call_cwd(args)
    if not cwd.is_dir():
        return False, f"cwd is not a directory: {cwd}"
    root = mcp_context_root(args)
    if root is None:
        return False, "Could not resolve TEP context root"
    unsafe_fallback = unsafe_unanchored_fallback(args, cwd)
    if unsafe_fallback:
        return False, unsafe_fallback
    records, load_error = load_mcp_records(root)
    if load_error:
        return False, load_error
    assert records is not None
    payload, error = task_outcome_check_service(
        root,
        records,
        task_ref=str(args.get("task_ref") or "").strip() or None,
        outcome=str(args.get("outcome") or ""),
    )
    if error:
        return False, error
    assert payload is not None
    if as_format(args.get("format")) == "json":
        return True, json.dumps(payload, ensure_ascii=False, indent=2)
    return True, task_outcome_check_text(payload)


def tool_search_records(args: JsonObject) -> tuple[bool, str]:
    cli_args = [
        "search-records",
        "--query",
        str(args.get("query", "")),
        "--limit",
        str(as_int(args.get("limit"), 12, 1, 100)),
        "--format",
        as_format(args.get("format")),
    ]
    add_repeated(cli_args, "--type", as_list(args.get("record_types")))
    add_flag(cli_args, as_bool(args.get("all_projects")), "--all-projects")
    add_flag(cli_args, as_bool(args.get("include_task_local")), "--include-task-local")
    add_flag(cli_args, as_bool(args.get("include_fallback")), "--include-fallback")
    add_flag(cli_args, as_bool(args.get("include_archived")), "--include-archived")
    return run_cli(args, cli_args)


def tool_record_detail(args: JsonObject) -> tuple[bool, str]:
    return run_cli(
        args,
        [
            "record-detail",
            "--record",
            str(args.get("record", "")),
            "--format",
            as_format(args.get("format")),
        ],
    )


def tool_claim_graph(args: JsonObject) -> tuple[bool, str]:
    cli_args = [
        "claim-graph",
        "--query",
        str(args.get("query", "")),
        "--limit",
        str(as_int(args.get("limit"), 8, 1, 50)),
        "--depth",
        str(as_int(args.get("depth"), 1, 1, 4)),
        "--format",
        as_format(args.get("format")),
    ]
    add_flag(cli_args, as_bool(args.get("all_projects")), "--all-projects")
    add_flag(cli_args, as_bool(args.get("include_task_local")), "--include-task-local")
    add_flag(cli_args, as_bool(args.get("include_fallback")), "--include-fallback")
    add_flag(cli_args, as_bool(args.get("include_archived")), "--include-archived")
    return run_cli(args, cli_args)


def tool_linked_records(args: JsonObject) -> tuple[bool, str]:
    direction = str(args.get("direction") or "both")
    if direction not in {"incoming", "outgoing", "both"}:
        direction = "both"
    return run_cli(
        args,
        [
            "linked-records",
            "--record",
            str(args.get("record", "")),
            "--direction",
            direction,
            "--depth",
            str(as_int(args.get("depth"), 1, 1, 4)),
            "--format",
            as_format(args.get("format")),
        ],
    )


def tool_telemetry_report(args: JsonObject) -> tuple[bool, str]:
    return run_cli(
        args,
        [
            "telemetry-report",
            "--limit",
            str(as_int(args.get("limit"), 10, 1, 50)),
            "--format",
            as_format(args.get("format")),
        ],
    )


def tool_backend_status(args: JsonObject) -> tuple[bool, str]:
    cli_args = ["backend-status", "--format", as_format(args.get("format"))]
    if args.get("root"):
        cli_args.extend(["--root", str(args["root"])])
    if args.get("scope"):
        cli_args.extend(["--scope", str(args["scope"])])
    return run_cli(args, cli_args)


def tool_backend_check(args: JsonObject) -> tuple[bool, str]:
    cli_args = [
        "backend-check",
        "--backend",
        str(args.get("backend", "")),
        "--format",
        as_format(args.get("format")),
    ]
    if args.get("root"):
        cli_args.extend(["--root", str(args["root"])])
    if args.get("scope"):
        cli_args.extend(["--scope", str(args["scope"])])
    return run_cli(args, cli_args)


def tool_guidelines_for(args: JsonObject) -> tuple[bool, str]:
    cli_args = [
        "guidelines-for",
        "--task",
        str(args.get("task", "")),
        "--limit",
        str(as_int(args.get("limit"), 8, 1, 50)),
        "--format",
        as_format(args.get("format")),
    ]
    if args.get("domain"):
        cli_args.extend(["--domain", str(args["domain"])])
    add_flag(cli_args, as_bool(args.get("all_projects")), "--all-projects")
    add_flag(cli_args, as_bool(args.get("include_task_local")), "--include-task-local")
    return run_cli(args, cli_args)


def tool_code_search(args: JsonObject) -> tuple[bool, str]:
    cli_args = [
        "code-search",
        "--limit",
        str(as_int(args.get("limit"), 20, 1, 100)),
        "--format",
        as_format(args.get("format")),
    ]
    if args.get("root"):
        cli_args.extend(["--root", str(args["root"])])
    if args.get("query"):
        cli_args.extend(["--query", str(args["query"])])
    if args.get("scope"):
        cli_args.extend(["--scope", str(args["scope"])])
    add_repeated(cli_args, "--path", as_list(args.get("paths")))
    for key, flag in (
        ("imports", "--import"),
        ("symbols", "--symbol"),
        ("features", "--feature"),
        ("refs", "--ref"),
        ("link_candidate_refs", "--link-candidate"),
    ):
        add_repeated(cli_args, flag, as_list(args.get(key)))
    for key, flag in (("language", "--language"), ("code_kind", "--code-kind"), ("fields", "--fields")):
        if args.get(key):
            cli_args.extend([flag, str(args[key])])
    if args.get("stale") in {"true", "false"}:
        cli_args.extend(["--stale", str(args["stale"])])
    for key, flag in (
        ("annotation_kind", "--annotation-kind"),
        ("annotation_status", "--annotation-status"),
    ):
        if args.get(key):
            cli_args.extend([flag, str(args[key])])
    add_repeated(cli_args, "--annotation-category", as_list(args.get("annotation_categories")))
    add_flag(cli_args, as_bool(args.get("include_stale_annotations")), "--include-stale-annotations")
    add_flag(cli_args, as_bool(args.get("include_missing")), "--include-missing")
    add_flag(cli_args, as_bool(args.get("include_superseded")), "--include-superseded")
    add_flag(cli_args, as_bool(args.get("include_archived")), "--include-archived")
    return run_cli(args, cli_args)


def tool_code_smell_report(args: JsonObject) -> tuple[bool, str]:
    cli_args = [
        "code-smell-report",
        "--limit",
        str(as_int(args.get("limit"), 20, 1, 100)),
        "--format",
        as_format(args.get("format")),
    ]
    if args.get("root"):
        cli_args.extend(["--root", str(args["root"])])
    add_repeated(cli_args, "--category", as_list(args.get("categories")))
    add_repeated(cli_args, "--severity", as_list(args.get("severities")))
    add_flag(cli_args, as_bool(args.get("include_stale")), "--include-stale")
    return run_cli(args, cli_args)


def tool_code_feedback(args: JsonObject) -> tuple[bool, str]:
    cli_args = [
        "code-feedback",
        "--query",
        str(args.get("query") or ""),
        "--limit",
        str(as_int(args.get("limit"), 20, 1, 100)),
        "--format",
        as_format(args.get("format")),
    ]
    if args.get("root"):
        cli_args.extend(["--root", str(args["root"])])
    add_repeated(cli_args, "--path", as_list(args.get("paths")))
    add_repeated(cli_args, "--link-candidate", as_list(args.get("link_candidate_refs")))
    if args.get("language"):
        cli_args.extend(["--language", str(args["language"])])
    return run_cli(args, cli_args)


def tool_code_info(args: JsonObject) -> tuple[bool, str]:
    cli_args = [
        "code-info",
        "--format",
        as_format(args.get("format")),
    ]
    if args.get("root"):
        cli_args.extend(["--root", str(args["root"])])
    if args.get("entry"):
        cli_args.extend(["--entry", str(args["entry"])])
    if args.get("path"):
        cli_args.extend(["--path", str(args["path"])])
    if args.get("fields"):
        cli_args.extend(["--fields", str(args["fields"])])
    return run_cli(args, cli_args)


def tool_cleanup_candidates(args: JsonObject) -> tuple[bool, str]:
    return run_cli(
        args,
        [
            "cleanup-candidates",
            "--limit",
            str(as_int(args.get("limit"), 20, 1, 100)),
            "--format",
            as_format(args.get("format")),
        ],
    )


def tool_cleanup_archives(args: JsonObject) -> tuple[bool, str]:
    cli_args = [
        "cleanup-archives",
        "--limit",
        str(as_int(args.get("limit"), 50, 1, 100)),
        "--format",
        as_format(args.get("format")),
    ]
    if args.get("archive"):
        cli_args.extend(["--archive", str(args["archive"])])
    return run_cli(args, cli_args)


def migration_report_text(report: JsonObject) -> str:
    return "\n".join(migration_report_text_lines(report))


def schema_migration_ids(args: JsonObject) -> list[str] | None:
    raw = args.get("migrations")
    if raw is None:
        return None
    if isinstance(raw, list):
        return [str(item).strip() for item in raw if str(item).strip()]
    return [str(raw).strip()] if str(raw).strip() else None


def tool_migration_dry_run(args: JsonObject) -> tuple[bool, str]:
    source = str(args.get("source") or "").strip()
    if not source:
        return False, "source is required"
    target = (
        str(args.get("target") or "").strip()
        or context_path(args)
        or os.environ.get("TEP_CONTEXT_ROOT")
        or str(Path.home() / ".tep_context")
    )
    report = build_migration_dry_run_report(source, target).to_payload()
    if as_format(args.get("format")) == "json":
        return True, json.dumps(report, ensure_ascii=False, indent=2)
    return True, migration_report_text(report)


def tool_schema_migration_plan(args: JsonObject) -> tuple[bool, str]:
    root = mcp_context_root(args)
    if root is None:
        return False, "Could not resolve TEP context root"
    report = build_schema_migration_report(root, migration_ids=schema_migration_ids(args)).to_payload()
    if as_format(args.get("format")) == "json":
        return True, json.dumps(report, ensure_ascii=False, indent=2)
    return True, migration_report_text(report)


def tool_schema_migration_apply(args: JsonObject) -> tuple[bool, str]:
    root = mcp_context_root(args)
    if root is None:
        return False, "Could not resolve TEP context root"
    token_error = require_agent_private_key_arg(args)
    if token_error:
        return False, token_error
    report = build_schema_migration_report(root, apply=True, migration_ids=schema_migration_ids(args)).to_payload()
    if as_format(args.get("format")) == "json":
        return True, json.dumps(report, ensure_ascii=False, indent=2)
    return True, migration_report_text(report)


def tool_augment_chain(args: JsonObject) -> tuple[bool, str]:
    cwd = call_cwd(args)
    if not cwd.is_dir():
        return False, f"cwd is not a directory: {cwd}"
    root = mcp_context_root(args)
    if root is None:
        return False, "Could not resolve TEP context root"
    unsafe_fallback = unsafe_unanchored_fallback(args, cwd)
    if unsafe_fallback:
        return False, unsafe_fallback
    records, load_error = load_mcp_records(root)
    if load_error:
        return False, load_error
    assert records is not None
    chain_payload, error = read_chain_payload_file(Path(str(args.get("file", ""))).expanduser().resolve())
    if error:
        return False, error
    assert chain_payload is not None
    payload = augment_chain_service(root, records, chain_payload=chain_payload)
    if as_format(args.get("format")) == "json":
        return True, json.dumps(payload, ensure_ascii=False, indent=2)
    return True, augment_chain_text(payload, TEP_ICON)


def tool_validate_chain(args: JsonObject) -> tuple[bool, str]:
    cwd = call_cwd(args)
    if not cwd.is_dir():
        return False, f"cwd is not a directory: {cwd}"
    root = mcp_context_root(args)
    if root is None:
        return False, "Could not resolve TEP context root"
    unsafe_fallback = unsafe_unanchored_fallback(args, cwd)
    if unsafe_fallback:
        return False, unsafe_fallback
    records, load_error = load_mcp_records(root)
    if load_error:
        return False, load_error
    assert records is not None
    chain_payload, error = read_chain_payload_file(Path(str(args.get("file", ""))).expanduser().resolve())
    if error:
        return False, error
    assert chain_payload is not None
    payload = validate_chain_service(root, records, chain_payload=chain_payload)
    if as_format(args.get("format")) == "json":
        return True, json.dumps(payload, ensure_ascii=False, indent=2)
    return True, validate_chain_text(payload, chain_payload, TEP_ICON)


def tool_topic_search(args: JsonObject) -> tuple[bool, str]:
    cli_args = [
        "topic-search",
        "--query",
        str(args.get("query", "")),
        "--limit",
        str(as_int(args.get("limit"), 12, 1, 100)),
        "--format",
        as_format(args.get("format")),
    ]
    add_repeated(cli_args, "--type", as_list(args.get("record_types")))
    return run_cli(args, cli_args)


def tool_topic_info(args: JsonObject) -> tuple[bool, str]:
    return run_cli(
        args,
        [
            "topic-info",
            "--record",
            str(args.get("record", "")),
            "--limit",
            str(as_int(args.get("limit"), 8, 1, 50)),
            "--format",
            as_format(args.get("format")),
        ],
    )


def tool_topic_conflict_candidates(args: JsonObject) -> tuple[bool, str]:
    return run_cli(
        args,
        [
            "topic-conflict-candidates",
            "--limit",
            str(as_int(args.get("limit"), 20, 1, 100)),
            "--format",
            as_format(args.get("format")),
        ],
    )


def tool_attention_map(args: JsonObject) -> tuple[bool, str]:
    return run_cli(
        args,
        [
            "attention-map",
            "--limit",
            str(as_int(args.get("limit"), 12, 1, 100)),
            "--scope",
            str(args.get("scope") or "current"),
            "--mode",
            str(args.get("mode") or "general"),
            "--format",
            as_format(args.get("format")),
        ],
    )


def tool_attention_diagram(args: JsonObject) -> tuple[bool, str]:
    return run_cli(
        args,
        [
            "attention-diagram",
            "--limit",
            str(as_int(args.get("limit"), 8, 1, 100)),
            "--scope",
            str(args.get("scope") or "current"),
            "--mode",
            str(args.get("mode") or "general"),
            "--detail",
            str(args.get("detail") or "compact"),
            "--format",
            as_format(args.get("format")),
        ],
    )


def tool_attention_diagram_compare(args: JsonObject) -> tuple[bool, str]:
    return run_cli(
        args,
        [
            "attention-diagram-compare",
            "--limit",
            str(as_int(args.get("limit"), 8, 1, 100)),
            "--scope",
            str(args.get("scope") or "current"),
            "--mode",
            str(args.get("mode") or "general"),
            "--format",
            as_format(args.get("format")),
        ],
    )


def tool_curiosity_map(args: JsonObject) -> tuple[bool, str]:
    cli_args = [
        "curiosity-map",
        "--volume",
        str(args.get("volume") or "normal"),
        "--scope",
        str(args.get("scope") or "current"),
        "--mode",
        str(args.get("mode") or "general"),
        "--format",
        as_format(args.get("format")),
    ]
    if as_bool(args.get("html")):
        cli_args.append("--html")
    return run_cli(args, cli_args)


def tool_map_refresh(args: JsonObject) -> tuple[bool, str]:
    cwd = call_cwd(args)
    if not cwd.is_dir():
        return False, f"cwd is not a directory: {cwd}"
    root = mcp_context_root(args)
    if root is None:
        return False, "Could not resolve TEP context root"
    unsafe_fallback = unsafe_unanchored_fallback(args, cwd)
    if unsafe_fallback:
        return False, unsafe_fallback
    if not as_bool(args.get("dry_run")):
        token_error = require_agent_private_key_arg(args)
        if token_error:
            return False, token_error
    records, load_error = load_mcp_records(root)
    if load_error:
        return False, load_error
    assert records is not None
    with agent_identity_scope(agent_private_key_arg(args)):
        payload, error = map_refresh_service(
            root,
            records,
            scope=str(args.get("scope") or "current"),
            mode=str(args.get("mode") or "general"),
            volume=str(args.get("volume") or "compact"),
            limit=as_int(args.get("limit"), 5, 1, 50),
            apply=not as_bool(args.get("dry_run")),
        )
    if error:
        return False, error
    assert payload is not None
    if as_format(args.get("format")) == "json":
        return True, json.dumps(payload, ensure_ascii=False, indent=2)
    return True, "\n".join(map_refresh_text_lines(payload))


def _load_map_tool_context(args: JsonObject) -> tuple[Path | None, dict[str, dict] | None, str | None]:
    cwd = call_cwd(args)
    if not cwd.is_dir():
        return None, None, f"cwd is not a directory: {cwd}"
    root = mcp_context_root(args)
    if root is None:
        return None, None, "Could not resolve TEP context root"
    unsafe_fallback = unsafe_unanchored_fallback(args, cwd)
    if unsafe_fallback:
        return None, None, unsafe_fallback
    records, load_error = load_mcp_records(root)
    if load_error:
        return None, None, load_error
    assert records is not None
    return root, records, None


def tool_map_open(args: JsonObject) -> tuple[bool, str]:
    root, records, error = _load_map_tool_context(args)
    if error:
        return False, error
    assert root is not None and records is not None
    token_error = require_agent_private_key_arg(args)
    if token_error:
        return False, token_error
    with agent_identity_scope(agent_private_key_arg(args)):
        payload, service_error = map_open_service(
            root,
            records,
            query=str(args.get("query") or ""),
            mode=str(args.get("mode") or "general"),
            scope=str(args.get("scope") or "current"),
        )
    if service_error:
        return False, service_error
    assert payload is not None
    if as_format(args.get("format")) == "json":
        return True, json.dumps(payload, ensure_ascii=False, indent=2)
    return True, "\n".join(map_view_text_lines(payload))


def tool_map_view(args: JsonObject) -> tuple[bool, str]:
    root, records, error = _load_map_tool_context(args)
    if error:
        return False, error
    assert root is not None and records is not None
    with agent_identity_scope(agent_private_key_arg(args)):
        payload, service_error = map_view_service(root, records, session_ref=str(args.get("map_session_ref") or ""))
    if service_error:
        return False, service_error
    assert payload is not None
    if as_format(args.get("format")) == "json":
        return True, json.dumps(payload, ensure_ascii=False, indent=2)
    return True, "\n".join(map_view_text_lines(payload))


def tool_map_move(args: JsonObject) -> tuple[bool, str]:
    root, records, error = _load_map_tool_context(args)
    if error:
        return False, error
    assert root is not None and records is not None
    token_error = require_agent_private_key_arg(args)
    if token_error:
        return False, token_error
    with agent_identity_scope(agent_private_key_arg(args)):
        payload, service_error = map_move_service(
            root,
            records,
            session_ref=str(args.get("map_session_ref") or ""),
            target=str(args.get("target") or ""),
        )
    if service_error:
        return False, service_error
    assert payload is not None
    if as_format(args.get("format")) == "json":
        return True, json.dumps(payload, ensure_ascii=False, indent=2)
    return True, "\n".join(map_view_text_lines(payload))


def tool_map_drilldown(args: JsonObject) -> tuple[bool, str]:
    root, records, error = _load_map_tool_context(args)
    if error:
        return False, error
    assert root is not None and records is not None
    with agent_identity_scope(agent_private_key_arg(args)):
        payload, service_error = map_drilldown_service(
            root,
            records,
            session_ref=str(args.get("map_session_ref") or ""),
            record_ref=str(args.get("record") or ""),
        )
    if service_error:
        return False, service_error
    assert payload is not None
    if as_format(args.get("format")) == "json":
        return True, json.dumps(payload, ensure_ascii=False, indent=2)
    return True, "\n".join(map_drilldown_text_lines(payload))


def tool_map_checkpoint(args: JsonObject) -> tuple[bool, str]:
    root, records, error = _load_map_tool_context(args)
    if error:
        return False, error
    assert root is not None and records is not None
    token_error = require_agent_private_key_arg(args)
    if token_error:
        return False, token_error
    with agent_identity_scope(agent_private_key_arg(args)):
        payload, service_error = map_checkpoint_service(
            root,
            records,
            session_ref=str(args.get("map_session_ref") or ""),
            note=str(args.get("note") or ""),
        )
    if service_error:
        return False, service_error
    assert payload is not None
    if as_format(args.get("format")) == "json":
        return True, json.dumps(payload, ensure_ascii=False, indent=2)
    return True, "\n".join(map_view_text_lines(payload))


def tool_map_brief(args: JsonObject) -> tuple[bool, str]:
    return run_cli(
        args,
        [
            "map-brief",
            "--volume",
            str(args.get("volume") or "compact"),
            "--limit",
            str(as_int(args.get("limit"), 6, 1, 50)),
            "--scope",
            str(args.get("scope") or "current"),
            "--mode",
            str(args.get("mode") or "general"),
            "--format",
            as_format(args.get("format")),
        ],
    )


def tool_curiosity_probes(args: JsonObject) -> tuple[bool, str]:
    return run_cli(
        args,
        [
            "curiosity-probes",
            "--budget",
            str(as_int(args.get("budget"), 8, 1, 100)),
            "--scope",
            str(args.get("scope") or "current"),
            "--mode",
            str(args.get("mode") or "general"),
            "--format",
            as_format(args.get("format")),
        ],
    )


def tool_probe_inspect(args: JsonObject) -> tuple[bool, str]:
    return run_cli(
        args,
        [
            "probe-inspect",
            "--index",
            str(as_int(args.get("index"), 1, 1, 100)),
            "--scope",
            str(args.get("scope") or "current"),
            "--mode",
            str(args.get("mode") or "general"),
            "--format",
            as_format(args.get("format")),
        ],
    )


def tool_probe_chain_draft(args: JsonObject) -> tuple[bool, str]:
    return run_cli(
        args,
        [
            "probe-chain-draft",
            "--index",
            str(as_int(args.get("index"), 1, 1, 100)),
            "--scope",
            str(args.get("scope") or "current"),
            "--mode",
            str(args.get("mode") or "general"),
            "--format",
            as_format(args.get("format")),
        ],
    )


def tool_probe_route(args: JsonObject) -> tuple[bool, str]:
    return run_cli(
        args,
        [
            "probe-route",
            "--index",
            str(as_int(args.get("index"), 1, 1, 100)),
            "--scope",
            str(args.get("scope") or "current"),
            "--mode",
            str(args.get("mode") or "general"),
            "--format",
            as_format(args.get("format")),
        ],
    )


def tool_probe_pack(args: JsonObject) -> tuple[bool, str]:
    return run_cli(
        args,
        [
            "probe-pack",
            "--budget",
            str(as_int(args.get("budget"), 3, 1, 20)),
            "--scope",
            str(args.get("scope") or "current"),
            "--mode",
            str(args.get("mode") or "general"),
            "--detail",
            str(args.get("detail") or "compact"),
            "--format",
            as_format(args.get("format")),
        ],
    )


def tool_probe_pack_compare(args: JsonObject) -> tuple[bool, str]:
    return run_cli(
        args,
        [
            "probe-pack-compare",
            "--budget",
            str(as_int(args.get("budget"), 3, 1, 20)),
            "--scope",
            str(args.get("scope") or "current"),
            "--mode",
            str(args.get("mode") or "general"),
            "--format",
            as_format(args.get("format")),
        ],
    )


def tool_working_contexts(args: JsonObject) -> tuple[bool, str]:
    cli_args = ["working-context", "show", "--format", as_format(args.get("format"))]
    if args.get("record"):
        cli_args.extend(["--context", str(args["record"])])
    if as_bool(args.get("all")):
        cli_args.append("--all")
    return run_cli(args, cli_args)


def tool_working_context_drift(args: JsonObject) -> tuple[bool, str]:
    return run_cli(
        args,
        [
            "working-context",
            "check-drift",
            "--task",
            str(args.get("task", "")),
            "--format",
            as_format(args.get("format")),
        ],
    )


def tool_workspace_admission(args: JsonObject) -> tuple[bool, str]:
    return run_cli(
        args,
        [
            "workspace-admission",
            "check",
            "--repo",
            str(args.get("repo", "")),
            "--format",
            as_format(args.get("format")),
        ],
    )


def tool_logic_search(args: JsonObject) -> tuple[bool, str]:
    cli_args = [
        "logic-search",
        "--limit",
        str(as_int(args.get("limit"), 20, 1, 100)),
        "--format",
        as_format(args.get("format")),
    ]
    for key, flag in (("predicate", "--predicate"), ("symbol", "--symbol"), ("claim", "--claim")):
        if args.get(key):
            cli_args.extend([flag, str(args[key])])
    return run_cli(args, cli_args)


def tool_logic_check(args: JsonObject) -> tuple[bool, str]:
    return run_cli(
        args,
        [
            "logic-check",
            "--limit",
            str(as_int(args.get("limit"), 20, 1, 100)),
            "--format",
            as_format(args.get("format")),
        ],
    )


def tool_logic_graph(args: JsonObject) -> tuple[bool, str]:
    cli_args = [
        "logic-graph",
        "--limit",
        str(as_int(args.get("limit"), 20, 1, 100)),
        "--format",
        as_format(args.get("format")),
    ]
    for key, flag in (("symbol", "--symbol"), ("predicate", "--predicate")):
        if args.get(key):
            cli_args.extend([flag, str(args[key])])
    if as_bool(args.get("smells")):
        cli_args.append("--smells")
    return run_cli(args, cli_args)


def tool_logic_conflict_candidates(args: JsonObject) -> tuple[bool, str]:
    return run_cli(
        args,
        [
            "logic-conflict-candidates",
            "--limit",
            str(as_int(args.get("limit"), 20, 1, 100)),
            "--format",
            as_format(args.get("format")),
        ],
    )


TOOL_HANDLERS: dict[str, Callable[[JsonObject], tuple[bool, str]]] = {
    "brief_context": tool_brief_context,
    "next_step": tool_next_step,
    "lookup": tool_lookup,
    "record_evidence": tool_record_evidence,
    "reason_step": tool_reason_step,
    "reason_review": tool_reason_review,
    "task_outcome_check": tool_task_outcome_check,
    "search_records": tool_search_records,
    "record_detail": tool_record_detail,
    "claim_graph": tool_claim_graph,
    "linked_records": tool_linked_records,
    "telemetry_report": tool_telemetry_report,
    "backend_status": tool_backend_status,
    "backend_check": tool_backend_check,
    "guidelines_for": tool_guidelines_for,
    "code_search": tool_code_search,
    "code_feedback": tool_code_feedback,
    "code_smell_report": tool_code_smell_report,
    "code_info": tool_code_info,
    "cleanup_candidates": tool_cleanup_candidates,
    "cleanup_archives": tool_cleanup_archives,
    "migration_dry_run": tool_migration_dry_run,
    "schema_migration_plan": tool_schema_migration_plan,
    "schema_migration_apply": tool_schema_migration_apply,
    "augment_chain": tool_augment_chain,
    "validate_chain": tool_validate_chain,
    "topic_search": tool_topic_search,
    "topic_info": tool_topic_info,
    "topic_conflict_candidates": tool_topic_conflict_candidates,
    "attention_map": tool_attention_map,
    "attention_diagram": tool_attention_diagram,
    "attention_diagram_compare": tool_attention_diagram_compare,
    "curiosity_map": tool_curiosity_map,
    "map_refresh": tool_map_refresh,
    "map_open": tool_map_open,
    "map_view": tool_map_view,
    "map_move": tool_map_move,
    "map_drilldown": tool_map_drilldown,
    "map_checkpoint": tool_map_checkpoint,
    "map_brief": tool_map_brief,
    "curiosity_probes": tool_curiosity_probes,
    "probe_inspect": tool_probe_inspect,
    "probe_chain_draft": tool_probe_chain_draft,
    "probe_route": tool_probe_route,
    "probe_pack": tool_probe_pack,
    "probe_pack_compare": tool_probe_pack_compare,
    "working_contexts": tool_working_contexts,
    "working_context_drift": tool_working_context_drift,
    "workspace_admission": tool_workspace_admission,
    "logic_search": tool_logic_search,
    "logic_check": tool_logic_check,
    "logic_graph": tool_logic_graph,
    "logic_conflict_candidates": tool_logic_conflict_candidates,
}


def response(message_id: Any, result: JsonObject | None = None, error: JsonObject | None = None) -> JsonObject:
    payload: JsonObject = {"jsonrpc": "2.0", "id": message_id}
    if error is not None:
        payload["error"] = error
    else:
        payload["result"] = result or {}
    return payload


def method_not_found(message_id: Any, method: str) -> JsonObject:
    return response(message_id, error={"code": -32601, "message": f"Method not found: {method}"})


def invalid_request(message_id: Any, message: str) -> JsonObject:
    return response(message_id, error={"code": -32600, "message": message})


def handle_request(message: JsonObject) -> JsonObject | None:
    message_id = message.get("id")
    method = str(message.get("method", ""))
    params = message.get("params") or {}
    if not isinstance(params, dict):
        return invalid_request(message_id, "params must be an object")

    if method == "initialize":
        protocol_version = str(params.get("protocolVersion") or DEFAULT_PROTOCOL_VERSION)
        return response(
            message_id,
            {
                "protocolVersion": protocol_version,
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {
                    "name": "trust-evidence-protocol",
                    "version": SERVER_VERSION,
                },
            },
        )

    if method == "notifications/initialized":
        return None

    if method == "tools/list":
        return response(message_id, {"tools": TOOLS})

    if method == "tools/call":
        name = str(params.get("name", ""))
        arguments = params.get("arguments") or {}
        if not isinstance(arguments, dict):
            return invalid_request(message_id, "tools/call arguments must be an object")
        handler = TOOL_HANDLERS.get(name)
        if not handler:
            return response(
                message_id,
                {
                    "content": [{"type": "text", "text": f"Unknown tool: {name}"}],
                    "isError": True,
                },
            )
        ok, output = handler(arguments)
        return response(
            message_id,
            {
                "content": [{"type": "text", "text": output}],
                "isError": not ok,
            },
        )

    return method_not_found(message_id, method)


def emit(message: JsonObject) -> None:
    sys.stdout.write(json.dumps(message, ensure_ascii=False, separators=(",", ":")) + "\n")
    sys.stdout.flush()


def main() -> None:
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            message = json.loads(line)
        except json.JSONDecodeError as exc:
            emit(response(None, error={"code": -32700, "message": f"Parse error: {exc}"}))
            continue

        messages = message if isinstance(message, list) else [message]
        batch_responses = []
        for item in messages:
            if not isinstance(item, dict):
                batch_responses.append(invalid_request(None, "message must be an object"))
                continue
            result = handle_request(item)
            if result is not None:
                batch_responses.append(result)
        if isinstance(message, list):
            if batch_responses:
                emit(batch_responses)
        elif batch_responses:
            emit(batch_responses[0])


if __name__ == "__main__":
    main()
