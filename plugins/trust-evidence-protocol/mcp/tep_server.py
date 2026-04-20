#!/usr/bin/env python3
"""Minimal read-only MCP stdio server for Trust Evidence Protocol.

The server intentionally delegates all policy and context logic to context_cli.py.
It only exposes bounded read-only tools so MCP does not become a second mutation
surface for the TEP context root.
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
SERVER_VERSION = "0.1.73"
DEFAULT_PROTOCOL_VERSION = "2025-06-18"


JsonObject = dict[str, Any]


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
                "context": {"type": "string", "description": "Path to TEP context root. Defaults to TEP_CONTEXT_ROOT, nearest .tep context_root, ~/.tep_context, or legacy ./.codex_context."},
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
                "context": {"type": "string", "description": "Path to TEP context root. Defaults to TEP_CONTEXT_ROOT, nearest .tep context_root, ~/.tep_context, or legacy ./.codex_context."},
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
        "name": "search_records",
        "description": (
            "Search canonical records by keyword. Defaults keep current project/task scope and rank current "
            "claims before fallback or archived claims."
        ),
        "inputSchema": schema(
            {
                "context": {"type": "string", "description": "Path to TEP context root. Defaults to TEP_CONTEXT_ROOT, nearest .tep context_root, ~/.tep_context, or legacy ./.codex_context."},
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
                "context": {"type": "string", "description": "Path to TEP context root. Defaults to TEP_CONTEXT_ROOT, nearest .tep context_root, ~/.tep_context, or legacy ./.codex_context."},
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
                "context": {"type": "string", "description": "Path to TEP context root. Defaults to TEP_CONTEXT_ROOT, nearest .tep context_root, ~/.tep_context, or legacy ./.codex_context."},
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
                "context": {"type": "string", "description": "Path to TEP context root. Defaults to TEP_CONTEXT_ROOT, nearest .tep context_root, ~/.tep_context, or legacy ./.codex_context."},
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
                "context": {"type": "string", "description": "Path to TEP context root. Defaults to TEP_CONTEXT_ROOT, nearest .tep context_root, ~/.tep_context, or legacy ./.codex_context."},
                "limit": {"type": "integer", "minimum": 1, "maximum": 50, "default": 10},
                "format": {"type": "string", "enum": ["text", "json"], "default": "text"},
            },
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
                "context": {"type": "string", "description": "Path to TEP context root. Defaults to TEP_CONTEXT_ROOT, nearest .tep context_root, ~/.tep_context, or legacy ./.codex_context."},
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
                "context": {"type": "string", "description": "Path to TEP context root. Defaults to TEP_CONTEXT_ROOT, nearest .tep context_root, ~/.tep_context, or legacy ./.codex_context."},
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
                "context": {"type": "string", "description": "Path to TEP context root. Defaults to TEP_CONTEXT_ROOT, nearest .tep context_root, ~/.tep_context, or legacy ./.codex_context."},
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
                "context": {"type": "string", "description": "Path to TEP context root. Defaults to TEP_CONTEXT_ROOT, nearest .tep context_root, ~/.tep_context, or legacy ./.codex_context."},
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
                "context": {"type": "string", "description": "Path to TEP context root. Defaults to TEP_CONTEXT_ROOT, nearest .tep context_root, ~/.tep_context, or legacy ./.codex_context."},
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
                "context": {"type": "string", "description": "Path to TEP context root. Defaults to TEP_CONTEXT_ROOT, nearest .tep context_root, ~/.tep_context, or legacy ./.codex_context."},
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
                "context": {"type": "string", "description": "Path to TEP context root. Defaults to TEP_CONTEXT_ROOT, nearest .tep context_root, ~/.tep_context, or legacy ./.codex_context."},
                "archive": {"type": "string", "description": "Optional ARC-* id or archive zip path under the context root."},
                "limit": {"type": "integer", "minimum": 1, "maximum": 100, "default": 50},
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
                "context": {"type": "string", "description": "Path to TEP context root. Defaults to TEP_CONTEXT_ROOT, nearest .tep context_root, ~/.tep_context, or legacy ./.codex_context."},
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
                "context": {"type": "string", "description": "Path to TEP context root. Defaults to TEP_CONTEXT_ROOT, nearest .tep context_root, ~/.tep_context, or legacy ./.codex_context."},
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
                "context": {"type": "string", "description": "Path to TEP context root. Defaults to TEP_CONTEXT_ROOT, nearest .tep context_root, ~/.tep_context, or legacy ./.codex_context."},
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
                "context": {"type": "string", "description": "Path to TEP context root. Defaults to TEP_CONTEXT_ROOT, nearest .tep context_root, ~/.tep_context, or legacy ./.codex_context."},
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
                "context": {"type": "string", "description": "Path to TEP context root. Defaults to TEP_CONTEXT_ROOT, nearest .tep context_root, ~/.tep_context, or legacy ./.codex_context."},
                "limit": {"type": "integer", "minimum": 1, "maximum": 100, "default": 12},
                "scope": {"type": "string", "enum": ["current", "all"], "default": "current"},
                "format": {"type": "string", "enum": ["text", "json"], "default": "text"},
            },
        ),
    },
    {
        "name": "attention_diagram",
        "description": "Read a generated Mermaid attention graph over clusters, top records, established bridges, and curiosity probes. Diagram data is navigation only, not proof.",
        "inputSchema": schema(
            {
                "context": {"type": "string", "description": "Path to TEP context root. Defaults to TEP_CONTEXT_ROOT, nearest .tep context_root, ~/.tep_context, or legacy ./.codex_context."},
                "limit": {"type": "integer", "minimum": 1, "maximum": 100, "default": 8},
                "scope": {"type": "string", "enum": ["current", "all"], "default": "current"},
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
                "context": {"type": "string", "description": "Path to TEP context root. Defaults to TEP_CONTEXT_ROOT, nearest .tep context_root, ~/.tep_context, or legacy ./.codex_context."},
                "limit": {"type": "integer", "minimum": 1, "maximum": 100, "default": 8},
                "scope": {"type": "string", "enum": ["current", "all"], "default": "current"},
                "format": {"type": "string", "enum": ["text", "json"], "default": "text"},
            },
        ),
    },
    {
        "name": "curiosity_probes",
        "description": "Read generated bounded curiosity probes over attention clusters. Probes are questions, not proof.",
        "inputSchema": schema(
            {
                "context": {"type": "string", "description": "Path to TEP context root. Defaults to TEP_CONTEXT_ROOT, nearest .tep context_root, ~/.tep_context, or legacy ./.codex_context."},
                "budget": {"type": "integer", "minimum": 1, "maximum": 100, "default": 8},
                "scope": {"type": "string", "enum": ["current", "all"], "default": "current"},
                "format": {"type": "string", "enum": ["text", "json"], "default": "text"},
            },
        ),
    },
    {
        "name": "probe_inspect",
        "description": "Inspect one generated curiosity probe with canonical record details and direct link status. Inspection is navigation only, not proof.",
        "inputSchema": schema(
            {
                "context": {"type": "string", "description": "Path to TEP context root. Defaults to TEP_CONTEXT_ROOT, nearest .tep context_root, ~/.tep_context, or legacy ./.codex_context."},
                "index": {"type": "integer", "minimum": 1, "maximum": 100, "default": 1},
                "scope": {"type": "string", "enum": ["current", "all"], "default": "current"},
                "format": {"type": "string", "enum": ["text", "json"], "default": "text"},
            },
        ),
    },
    {
        "name": "probe_chain_draft",
        "description": "Draft a mechanical evidence-chain skeleton from one curiosity probe. Draft is not proof.",
        "inputSchema": schema(
            {
                "context": {"type": "string", "description": "Path to TEP context root. Defaults to TEP_CONTEXT_ROOT, nearest .tep context_root, ~/.tep_context, or legacy ./.codex_context."},
                "index": {"type": "integer", "minimum": 1, "maximum": 100, "default": 1},
                "scope": {"type": "string", "enum": ["current", "all"], "default": "current"},
                "format": {"type": "string", "enum": ["text", "json"], "default": "text"},
            },
        ),
    },
    {
        "name": "probe_route",
        "description": "Generate an ordered mechanical inspection route for one curiosity probe. Route is navigation only, not proof.",
        "inputSchema": schema(
            {
                "context": {"type": "string", "description": "Path to TEP context root. Defaults to TEP_CONTEXT_ROOT, nearest .tep context_root, ~/.tep_context, or legacy ./.codex_context."},
                "index": {"type": "integer", "minimum": 1, "maximum": 100, "default": 1},
                "scope": {"type": "string", "enum": ["current", "all"], "default": "current"},
                "format": {"type": "string", "enum": ["text", "json"], "default": "text"},
            },
        ),
    },
    {
        "name": "probe_pack",
        "description": "Read a compact mechanical bundle of top curiosity probes, inspection summaries, and chain-draft validation. Pack is not proof.",
        "inputSchema": schema(
            {
                "context": {"type": "string", "description": "Path to TEP context root. Defaults to TEP_CONTEXT_ROOT, nearest .tep context_root, ~/.tep_context, or legacy ./.codex_context."},
                "budget": {"type": "integer", "minimum": 1, "maximum": 20, "default": 3},
                "scope": {"type": "string", "enum": ["current", "all"], "default": "current"},
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
                "context": {"type": "string", "description": "Path to TEP context root. Defaults to TEP_CONTEXT_ROOT, nearest .tep context_root, ~/.tep_context, or legacy ./.codex_context."},
                "budget": {"type": "integer", "minimum": 1, "maximum": 20, "default": 3},
                "scope": {"type": "string", "enum": ["current", "all"], "default": "current"},
                "format": {"type": "string", "enum": ["text", "json"], "default": "text"},
            },
        ),
    },
    {
        "name": "working_contexts",
        "description": "Read WCTX-* operational working contexts. WCTX is handoff/focus context, not proof.",
        "inputSchema": schema(
            {
                "context": {"type": "string", "description": "Path to TEP context root. Defaults to TEP_CONTEXT_ROOT, nearest .tep context_root, ~/.tep_context, or legacy ./.codex_context."},
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
                "context": {"type": "string", "description": "Path to TEP context root. Defaults to TEP_CONTEXT_ROOT, nearest .tep context_root, ~/.tep_context, or legacy ./.codex_context."},
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
                "context": {"type": "string", "description": "Path to TEP context root. Defaults to TEP_CONTEXT_ROOT, nearest .tep context_root, ~/.tep_context, or legacy ./.codex_context."},
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
                "context": {"type": "string", "description": "Path to TEP context root. Defaults to TEP_CONTEXT_ROOT, nearest .tep context_root, ~/.tep_context, or legacy ./.codex_context."},
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
                "context": {"type": "string", "description": "Path to TEP context root. Defaults to TEP_CONTEXT_ROOT, nearest .tep context_root, ~/.tep_context, or legacy ./.codex_context."},
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
                "context": {"type": "string", "description": "Path to TEP context root. Defaults to TEP_CONTEXT_ROOT, nearest .tep context_root, ~/.tep_context, or legacy ./.codex_context."},
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
                "context": {"type": "string", "description": "Path to TEP context root. Defaults to TEP_CONTEXT_ROOT, nearest .tep context_root, ~/.tep_context, or legacy ./.codex_context."},
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
    if not context:
        return None
    return Path(context).expanduser().resolve()


def unsafe_unanchored_fallback(args: JsonObject, cwd: Path) -> str | None:
    if args.get("cwd") or has_nearest_anchor(cwd):
        return None
    context_root = mcp_context_root(args)
    if context_root is None or active_workspace_count(context_root) <= 1:
        return None
    return (
        "MCP cwd is required: refusing to use the MCP server cwd as TEP focus in a multi-workspace context. "
        "Pass the active agent workdir via the tool `cwd` argument so `.tep` can select workspace/project/task."
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
    return run_cli(
        args,
        [
            "next-step",
            "--intent",
            str(args.get("intent") or "auto"),
            "--task",
            str(args.get("task") or ""),
            "--detail",
            str(args.get("detail") or "compact"),
            "--format",
            as_format(args.get("format")),
        ],
    )


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
        "--root",
        str(args.get("root") or "."),
        "--limit",
        str(as_int(args.get("limit"), 20, 1, 100)),
        "--format",
        as_format(args.get("format")),
    ]
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
        "--root",
        str(args.get("root") or "."),
        "--limit",
        str(as_int(args.get("limit"), 20, 1, 100)),
        "--format",
        as_format(args.get("format")),
    ]
    add_repeated(cli_args, "--category", as_list(args.get("categories")))
    add_repeated(cli_args, "--severity", as_list(args.get("severities")))
    add_flag(cli_args, as_bool(args.get("include_stale")), "--include-stale")
    return run_cli(args, cli_args)


def tool_code_feedback(args: JsonObject) -> tuple[bool, str]:
    cli_args = [
        "code-feedback",
        "--root",
        str(args.get("root") or "."),
        "--query",
        str(args.get("query") or ""),
        "--limit",
        str(as_int(args.get("limit"), 20, 1, 100)),
        "--format",
        as_format(args.get("format")),
    ]
    add_repeated(cli_args, "--path", as_list(args.get("paths")))
    add_repeated(cli_args, "--link-candidate", as_list(args.get("link_candidate_refs")))
    if args.get("language"):
        cli_args.extend(["--language", str(args["language"])])
    return run_cli(args, cli_args)


def tool_code_info(args: JsonObject) -> tuple[bool, str]:
    cli_args = [
        "code-info",
        "--root",
        str(args.get("root") or "."),
        "--format",
        as_format(args.get("format")),
    ]
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


def tool_augment_chain(args: JsonObject) -> tuple[bool, str]:
    return run_cli(
        args,
        [
            "augment-chain",
            "--file",
            str(args.get("file", "")),
            "--format",
            as_format(args.get("format")),
        ],
    )


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
    "search_records": tool_search_records,
    "record_detail": tool_record_detail,
    "claim_graph": tool_claim_graph,
    "linked_records": tool_linked_records,
    "telemetry_report": tool_telemetry_report,
    "guidelines_for": tool_guidelines_for,
    "code_search": tool_code_search,
    "code_feedback": tool_code_feedback,
    "code_smell_report": tool_code_smell_report,
    "code_info": tool_code_info,
    "cleanup_candidates": tool_cleanup_candidates,
    "cleanup_archives": tool_cleanup_archives,
    "augment_chain": tool_augment_chain,
    "topic_search": tool_topic_search,
    "topic_info": tool_topic_info,
    "topic_conflict_candidates": tool_topic_conflict_candidates,
    "attention_map": tool_attention_map,
    "attention_diagram": tool_attention_diagram,
    "attention_diagram_compare": tool_attention_diagram_compare,
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
