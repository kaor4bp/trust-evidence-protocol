"""Lookup route service shared by CLI and MCP adapters."""

from __future__ import annotations

import os
import shlex
from pathlib import Path
from typing import Any

from .attention import ATTENTION_MODES
from .claims import claim_is_fallback
from .cli_common import public_record_payload, refresh_generated_outputs, validate_mutated_records
from .hydration import invalidate_hydration_state
from .hypotheses import active_hypothesis_entry_by_claim
from .ids import next_record_id, now_timestamp
from .io import write_json_file
from .notes import append_note
from .paths import record_path
from .reason_ledger import latest_reason_step, validate_reason_ledger
from .reasoning import decision_validation_payload
from .reports import write_validation_report
from .scopes import (
    current_project_ref,
    current_task_ref,
    current_workspace_ref,
    project_refs_for_write,
    record_belongs_to_project,
    record_belongs_to_task,
    workspace_refs_for_write,
)
from .search import concise, ranked_record_search, record_summary
from .telemetry import append_access_event
from .topic_index import task_terms
from .working_contexts import build_working_context_payload


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
LOOKUP_CHAIN_RECORD_TYPES_BY_KIND = {
    "facts": ["claim", "model", "flow", "open_question", "proposal"],
    "code": ["claim", "model", "flow", "guideline", "proposal", "open_question"],
    "theory": ["model", "flow", "claim", "open_question", "proposal"],
    "research": ["model", "flow", "claim", "open_question", "proposal"],
    "policy": ["guideline", "permission", "restriction", "proposal", "claim"],
}
LOOKUP_CHAIN_DECISION_MODE_BY_REASON = {
    "answering": "final",
    "curiosity": "curiosity",
    "debugging": "debugging",
    "editing": "edit",
    "permission": "permission",
    "planning": "planning",
    "retrospective": "planning",
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


def task_is_active(records: dict[str, dict], task_ref: str | None) -> bool:
    task = records.get(str(task_ref or "").strip())
    return bool(task and task.get("record_type") == "task" and str(task.get("status", "")).strip() == "active")


def current_active_task_ref(root: Path, records: dict[str, dict]) -> str:
    task_ref = current_task_ref(root)
    return task_ref if task_is_active(records, task_ref) else ""


def working_context_task_scope_is_usable(records: dict[str, dict], context: dict, task_ref: str | None) -> bool:
    task_refs = [str(ref).strip() for ref in context.get("task_refs", []) if str(ref).strip()]
    if not task_refs:
        return True
    return bool(task_ref and task_ref in task_refs and task_is_active(records, task_ref))


def working_context_is_usable_for_focus(
    records: dict[str, dict],
    context: dict,
    project_ref: str | None,
    task_ref: str | None,
) -> bool:
    return (
        context.get("record_type") == "working_context"
        and str(context.get("status", "")).strip() == "active"
        and record_belongs_to_project(context, project_ref)
        and record_belongs_to_task(context, task_ref)
        and working_context_task_scope_is_usable(records, context, task_ref)
    )


def active_working_context_for_lookup(records: dict[str, dict], project_ref: str, task_ref: str) -> dict | None:
    task = records.get(task_ref) if task_ref else None
    if task and task.get("record_type") == "task" and task_is_active(records, task_ref):
        for ref in task.get("working_context_refs", []):
            context = records.get(str(ref))
            if context and working_context_is_usable_for_focus(records, context, project_ref or None, task_ref):
                return context
    candidates = [
        data
        for data in records.values()
        if working_context_is_usable_for_focus(records, data, project_ref or None, task_ref or None)
    ]
    return sorted(candidates, key=lambda item: str(item.get("updated_at", "")), reverse=True)[0] if candidates else None


def persist_working_context_with_task_links(root: Path, records: dict[str, dict], payload: dict) -> str | None:
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
        return "; ".join(f"{error.path}: {error.message}" for error in errors)

    write_json_file(record_path(root, "working_context", payload["id"]), payload)
    for task_ref, task_payload in mutations.items():
        if task_ref == payload["id"]:
            continue
        write_json_file(record_path(root, "task", task_ref), task_payload)
    write_validation_report(root, [])
    refresh_generated_outputs(root, merged)
    invalidate_hydration_state(root, f"recorded working_context {payload['id']}")
    return None


def ensure_lookup_working_context(root: Path, records: dict[str, dict], query: str, reason: str) -> tuple[str, dict | None, str | None]:
    workspace_ref = current_workspace_ref(root)
    project_ref = current_project_ref(root)
    task_ref = current_active_task_ref(root, records)
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
        task_refs=[task_ref] if task_ref else [],
        tags=["auto-wctx", f"lookup-reason:{reason}"],
        note="Auto-created by lookup to keep agent operational context explicit. Not proof and not authorization.",
    )
    error = persist_working_context_with_task_links(root, records, payload)
    if error:
        return "", None, f"failed to auto-create WCTX for lookup: {error}"
    return str(payload["id"]), payload, None


def lookup_chain_record_role(record: dict) -> str:
    record_type = str(record.get("record_type", "")).strip()
    if record_type == "claim":
        status = str(record.get("status", "")).strip()
        if status in {"supported", "corroborated"} and not claim_is_fallback(record):
            return "fact"
        if status == "tentative" and not claim_is_fallback(record):
            return "exploration_context"
        return ""
    return {
        "flow": "flow",
        "guideline": "guideline",
        "model": "model",
        "open_question": "open_question",
        "permission": "permission",
        "project": "project",
        "proposal": "proposal",
        "restriction": "restriction",
        "task": "task",
        "working_context": "working_context",
    }.get(record_type, "")


def lookup_chain_record_quote(record: dict) -> str:
    for key in ("statement", "summary", "question", "position", "title", "subject", "rule", "note"):
        value = str(record.get(key, "")).strip()
        if value:
            return value
    return record_summary(record)


def append_lookup_chain_node(nodes: list[dict], records: dict[str, dict], record_ref: str) -> None:
    if record_ref not in records or any(node.get("ref") == record_ref for node in nodes):
        return
    record = records[record_ref]
    role = lookup_chain_record_role(record)
    if not role:
        return
    quote = lookup_chain_record_quote(record)
    if not quote:
        return
    nodes.append({"role": role, "ref": record_ref, "quote": quote})


def append_lookup_chain_support_nodes(nodes: list[dict], records: dict[str, dict], record: dict, limit: int) -> None:
    support_refs = [str(ref) for ref in record.get("claim_refs", []) if str(ref)]
    for model_ref in record.get("model_refs", []):
        model = records.get(str(model_ref), {})
        support_refs.extend(str(ref) for ref in model.get("claim_refs", []) if str(ref))
    for support_ref in support_refs:
        if len(nodes) >= limit:
            return
        support = records.get(support_ref)
        if not support or lookup_chain_record_role(support) != "fact":
            continue
        append_lookup_chain_node(nodes, records, support_ref)


def current_lookup_reason_context(root: Path) -> dict:
    validation = validate_reason_ledger(root)
    if not validation.get("ok"):
        return {"ok": False, "reason_ref": "", "used_refs": set(), "message": "; ".join(validation.get("errors", []))}
    task_ref = current_task_ref(root)
    reason = latest_reason_step(validation.get("entries", []), task_ref)
    if not reason:
        return {"ok": True, "reason_ref": "", "used_refs": set(), "message": "no current REASON-*"}
    chain_payload = reason.get("chain_payload") if isinstance(reason.get("chain_payload"), dict) else {}
    nodes = chain_payload.get("nodes", []) if isinstance(chain_payload.get("nodes"), list) else []
    used_refs = {
        str(node.get("ref", "")).strip()
        for node in nodes
        if isinstance(node, dict) and str(node.get("ref", "")).strip()
    }
    return {
        "ok": True,
        "reason_ref": str(reason.get("id", "")).strip(),
        "reason_mode": str(reason.get("mode", "")).strip(),
        "used_refs": used_refs,
        "message": "",
    }


def build_lookup_chain_starter(
    root: Path,
    records: dict[str, dict],
    query: str,
    selected_kind: str,
    reason: str,
    selected_mode: str,
    scope: str,
    wctx_ref: str,
) -> dict:
    terms = task_terms(query)
    decision_mode = LOOKUP_CHAIN_DECISION_MODE_BY_REASON.get(reason, "planning")
    if not terms:
        return {
            "chain_starter_is_proof": False,
            "task": query,
            "reason": reason,
            "scope": scope,
            "mode": selected_mode,
            "decision_mode": decision_mode,
            "working_context_ref": wctx_ref,
            "nodes": [],
            "edges": [],
            "validation_preview": {"ok": False, "blockers": ["lookup query has no searchable terms"], "warnings": []},
            "next_commands": [],
            "notes": [
                "Lookup chain starters are mechanical drafts, not proof.",
                "Provide a more specific query before validating a decision chain.",
            ],
        }

    record_types = LOOKUP_CHAIN_RECORD_TYPES_BY_KIND.get(selected_kind, LOOKUP_CHAIN_RECORD_TYPES_BY_KIND["facts"])
    reason_context = current_lookup_reason_context(root)
    used_refs = reason_context.get("used_refs", set()) if reason_context.get("ok") else set()
    ranked = ranked_record_search(
        records,
        terms,
        16,
        record_types,
        current_project_ref(root) or None,
        current_task_ref(root) or None,
        include_fallback=False,
        include_archived=False,
    )
    if used_refs:
        ranked = [item for item in ranked if str(item["record"].get("id") or "") not in used_refs]
    nodes: list[dict] = []
    for item in ranked:
        if len(nodes) >= 5:
            break
        record = item["record"]
        append_lookup_chain_node(nodes, records, str(record.get("id") or ""))
        append_lookup_chain_support_nodes(nodes, records, record, limit=6)
    task_ref = current_task_ref(root)
    if task_ref:
        append_lookup_chain_node(nodes, records, task_ref)

    fact_refs = [str(node["ref"]) for node in nodes if node.get("role") == "fact"]
    edges: list[dict] = []
    if fact_refs and nodes:
        anchor = fact_refs[0]
        for node in nodes:
            target = str(node.get("ref") or "")
            if target == anchor:
                continue
            edges.append({"from": anchor, "to": target, "relation": "lookup_candidate_support"})
        if not edges:
            edges.append({"from": anchor, "to": anchor, "relation": "single_fact_anchor"})

    chain: dict[str, Any] = {
        "chain_starter_is_proof": False,
        "task": query,
        "reason": reason,
        "scope": scope,
        "mode": selected_mode,
        "decision_mode": decision_mode,
        "working_context_ref": wctx_ref,
        "chain_extension": {
            "default": bool(reason_context.get("reason_ref")),
            "current_reason_ref": reason_context.get("reason_ref", ""),
            "current_reason_mode": reason_context.get("reason_mode", ""),
            "excluded_existing_ref_count": len(used_refs),
            "new_candidate_count": len([node for node in nodes if str(node.get("ref", "")).strip() not in used_refs]),
            "fallback_when_empty": (
                "If no new proof-capable nodes are returned, review existing chain nodes and record a fact-compatible hypothesis or open question."
            ),
        },
        "nodes": nodes,
        "edges": edges,
    }
    validation = decision_validation_payload(records, active_hypothesis_entry_by_claim(root, records), chain, decision_mode)
    validation_details = validation.get("validation", {}) if isinstance(validation.get("validation"), dict) else {}
    chain["validation_preview"] = {
        "ok": bool(validation.get("decision_valid")),
        "chain_ok": bool(validation_details.get("ok")),
        "blockers": validation.get("blockers", []),
        "errors": validation_details.get("errors", []),
        "warnings": validation.get("warnings", []),
    }
    chain["write_hint"] = "write the chain_starter object to evidence-chain.json"
    chain["next_commands"] = [
        "augment-chain --file evidence-chain.json --format json",
        f"validate-decision --mode {decision_mode} --chain evidence-chain.json --format json",
    ]
    chain["notes"] = [
        "Lookup chain starters are mechanical drafts, not proof.",
        "CIX/backend/map candidates are intentionally omitted because they are navigation, not proof.",
        "Use augment-chain before presenting the chain to the user or requesting permission.",
    ]
    if not fact_refs:
        chain["notes"].append("No supported/corroborated CLM fact matched; open record-detail/claim-graph before relying on this draft.")
    if reason_context.get("reason_ref") and not any(str(node.get("ref", "")).strip() not in used_refs and node.get("role") == "fact" for node in nodes):
        chain["notes"].append(
            "No new fact node was found for the current REASON-*; fallback is to review existing nodes and create a supported hypothesis/open question."
        )
    return chain


def lookup_payload(
    root: Path,
    records: dict[str, dict],
    query: str,
    kind: str,
    root_path: str,
    scope: str,
    mode: str,
    reason: str,
    wctx_ref: str,
    auto_wctx: dict | None,
) -> dict:
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
    chain_starter = build_lookup_chain_starter(
        root=root,
        records=records,
        query=query,
        selected_kind=selected_kind,
        reason=reason,
        selected_mode=selected_mode,
        scope=scope,
        wctx_ref=wctx_ref,
    )
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
        "if_continuing_reason": "prefer new chain nodes not already present in current REASON-*; only fall back to revisiting old nodes when lookup finds no new candidates",
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
            "workspace_ref": current_workspace_ref(root),
            "project_ref": current_project_ref(root),
            "task_ref": current_task_ref(root),
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
        "chain_starter": chain_starter,
        "rules": [
            "Use lookup first when unsure where to search.",
            "Treat lookup and generated maps as navigation only, not proof.",
            "Open record-detail or linked-records before citing a canonical record.",
            "When new support is found, prefer record-support or record-evidence over separate manual record-source/record-claim calls.",
            "When a current REASON-* exists, lookup defaults to proposing new chain nodes before revisiting old chain nodes.",
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
    chain_starter = payload.get("chain_starter") or {}
    if chain_starter:
        validation = chain_starter.get("validation_preview") or {}
        lines.extend(["", "## Chain Starter"])
        lines.append(
            f"- nodes: `{len(chain_starter.get('nodes', []))}` edges: `{len(chain_starter.get('edges', []))}` "
            f"decision_mode: `{chain_starter.get('decision_mode')}` validation_ok: `{validation.get('ok')}`"
        )
        extension = chain_starter.get("chain_extension") or {}
        if extension.get("current_reason_ref"):
            lines.append(
                f"- extends: `{extension.get('current_reason_ref')}` new_candidates=`{extension.get('new_candidate_count', 0)}` "
                f"excluded_existing_refs=`{extension.get('excluded_existing_ref_count', 0)}`"
            )
        if chain_starter.get("write_hint"):
            lines.append(f"- write: {chain_starter.get('write_hint')}")
        for node in chain_starter.get("nodes", [])[:4]:
            lines.append(
                f"- `{node.get('ref')}` role=`{node.get('role')}` quote=\"{concise(str(node.get('quote', '')), 140)}\""
            )
        for command in chain_starter.get("next_commands", [])[:3]:
            lines.append(f"- next: `{command}`")
    lines.extend(["", "## Rules"])
    for rule in payload.get("rules", []):
        lines.append(f"- {rule}")
    contract = payload.get("output_contract") or {}
    if contract:
        lines.extend(["", "## Output Contract"])
        lines.append(f"- agent_role: {contract.get('agent_role')}")
        lines.append(f"- if_chain_needed: {contract.get('if_chain_needed')}")
    return lines


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


def build_lookup_service_payload(
    root: Path,
    records: dict[str, dict],
    *,
    query: str,
    kind: str,
    root_path: str | None,
    scope: str,
    mode: str,
    reason: str,
    channel: str,
) -> tuple[dict | None, str | None]:
    if not query.strip():
        return None, "lookup query must not be empty"
    if reason not in LOOKUP_REASONS:
        return None, f"lookup reason is required and must be one of: {', '.join(sorted(LOOKUP_REASONS))}"
    wctx_ref, auto_wctx, error = ensure_lookup_working_context(root, records, query, reason)
    if error:
        return None, error
    payload = lookup_payload(
        root=root,
        records=records,
        query=query,
        kind=kind,
        root_path=str(root_path or Path.cwd()),
        scope=scope,
        mode=mode,
        reason=reason,
        wctx_ref=wctx_ref,
        auto_wctx=auto_wctx,
    )
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
        channel=channel,
        tool="lookup",
        access_kind="record_search",
        record_refs=[],
        query=query,
        reason=reason,
        working_context_ref=wctx_ref,
        note=f"lookup route kind={payload['kind']} primary_tool={payload['primary_tool']} reason={reason} wctx={wctx_ref}",
    )
    return payload, None
