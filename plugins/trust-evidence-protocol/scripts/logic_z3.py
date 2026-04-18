#!/usr/bin/env python3
"""Optional Z3-backed consistency checks for TEP CLM.logic payloads.

This module is deliberately optional. Importing it must not require z3-solver;
the backend reports availability at runtime so structural checks remain the
baseline.
"""

from __future__ import annotations

import json
import re
from itertools import combinations
from typing import Any


FACT_STATUSES = {"supported", "corroborated"}


def atom_context_key(context: object) -> str:
    if not isinstance(context, dict):
        return "{}"
    return json.dumps(context, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def atom_value_key(atom: dict) -> str:
    if "value" not in atom:
        return "<no-value>"
    return json.dumps(atom.get("value"), ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def atom_key(atom: dict) -> tuple[str, tuple[str, ...], str, str]:
    return (
        str(atom.get("predicate", "")).strip(),
        tuple(str(arg).strip() for arg in atom.get("args", [])),
        atom_context_key(atom.get("context", {})),
        atom_value_key(atom),
    )


def atom_bucket_key(atom: dict) -> tuple[str, tuple[str, ...], str]:
    return (
        str(atom.get("predicate", "")).strip(),
        tuple(str(arg).strip() for arg in atom.get("args", [])),
        atom_context_key(atom.get("context", {})),
    )


def atom_label(atom: dict) -> str:
    value = f"={atom.get('value')!r}" if "value" in atom else ""
    return f"{atom.get('predicate')}({', '.join(str(arg) for arg in atom.get('args', []))}){value}"


def is_current_fact(entry: dict) -> bool:
    return (
        str(entry.get("claim_status", "")).strip() in FACT_STATUSES
        and str(entry.get("claim_lifecycle", "active")).strip() == "active"
    )


def safe_track_name(prefix: str, index: int) -> str:
    return re.sub(r"[^A-Za-z0-9_]", "_", f"{prefix}_{index}")


def direct_fact_entries(payload: dict) -> list[dict]:
    atoms = payload.get("atoms", [])
    if not isinstance(atoms, list):
        return []
    return [atom for atom in atoms if isinstance(atom, dict) and is_current_fact(atom)]


def current_rule_entries(payload: dict) -> list[dict]:
    rules = payload.get("rules", [])
    if not isinstance(rules, list):
        return []
    return [rule for rule in rules if isinstance(rule, dict) and is_current_fact(rule)]


def match_rule_atom(pattern: dict, fact: dict, bindings: dict[str, str]) -> dict[str, str] | None:
    if str(pattern.get("predicate", "")).strip() != str(fact.get("predicate", "")).strip():
        return None
    pattern_args = [str(arg).strip() for arg in pattern.get("args", [])]
    fact_args = [str(arg).strip() for arg in fact.get("args", [])]
    if len(pattern_args) != len(fact_args):
        return None
    next_bindings = dict(bindings)
    for pattern_arg, fact_arg in zip(pattern_args, fact_args):
        if pattern_arg.startswith("?"):
            existing = next_bindings.get(pattern_arg)
            if existing is not None and existing != fact_arg:
                return None
            next_bindings[pattern_arg] = fact_arg
        elif pattern_arg != fact_arg:
            return None
    return next_bindings


def rule_body_matches(body: list[dict], facts: list[dict]) -> list[tuple[dict[str, str], list[dict]]]:
    matches: list[tuple[dict[str, str], list[dict]]] = [({}, [])]
    for pattern in body:
        next_matches: list[tuple[dict[str, str], list[dict]]] = []
        for bindings, premises in matches:
            for fact in facts:
                next_bindings = match_rule_atom(pattern, fact, bindings)
                if next_bindings is not None:
                    next_matches.append((next_bindings, [*premises, fact]))
        matches = next_matches
        if not matches:
            break
    return matches


def substitute_rule_head(head: dict, bindings: dict[str, str]) -> dict | None:
    args: list[str] = []
    for arg in head.get("args", []):
        rendered = str(arg).strip()
        if rendered.startswith("?"):
            value = bindings.get(rendered)
            if value is None:
                return None
            args.append(value)
        else:
            args.append(rendered)
    return {
        "predicate": str(head.get("predicate", "")).strip(),
        "args": args,
        "polarity": "affirmed",
        "context": head.get("context", {}) if isinstance(head.get("context", {}), dict) else {},
        "functional": bool(head.get("functional", False)),
        **({"value": head.get("value")} if "value" in head else {}),
    }


def materialize_rule_closure(payload: dict, max_iterations: int, max_derived: int) -> list[dict]:
    facts = [atom for atom in direct_fact_entries(payload) if str(atom.get("polarity", "affirmed")).strip() == "affirmed"]
    rules = current_rule_entries(payload)
    known = {atom_key(atom) for atom in facts}
    derived: list[dict] = []

    for _ in range(max(1, max_iterations)):
        changed = False
        for rule in rules:
            body = rule.get("body", [])
            head = rule.get("head", {})
            if not isinstance(body, list) or not isinstance(head, dict):
                continue
            for bindings, premises in rule_body_matches([item for item in body if isinstance(item, dict)], facts + derived):
                atom = substitute_rule_head(head, bindings)
                if not atom:
                    continue
                key = atom_key(atom)
                if key in known:
                    continue
                entry = {
                    **atom,
                    "id": f"{rule.get('id')}#derived-{len(derived) + 1}",
                    "claim_ref": rule.get("claim_ref"),
                    "claim_status": rule.get("claim_status"),
                    "claim_lifecycle": rule.get("claim_lifecycle"),
                    "claim_summary": f"Derived from rule {rule.get('name')}",
                    "source_refs": rule.get("source_refs", []),
                    "derived": True,
                    "derived_from": {
                        "rule_ref": rule.get("id"),
                        "rule_claim_ref": rule.get("claim_ref"),
                        "premise_refs": [premise.get("id") for premise in premises],
                        "premise_claim_refs": sorted({str(premise.get("claim_ref")) for premise in premises if premise.get("claim_ref")}),
                    },
                }
                known.add(key)
                derived.append(entry)
                changed = True
                if len(derived) >= max_derived:
                    return derived
        if not changed:
            break
    return derived


def build_claim_summary(core_items: list[dict]) -> list[dict]:
    by_claim: dict[str, dict] = {}
    for item in core_items:
        refs = []
        claim_ref = item.get("claim_ref")
        if claim_ref:
            refs.append((str(claim_ref), item.get("role", "asserting_claim"), item.get("logic_ref"), item.get("summary", "")))
        derived = item.get("derived_from", {})
        if isinstance(derived, dict):
            rule_claim_ref = derived.get("rule_claim_ref")
            if rule_claim_ref:
                refs.append((str(rule_claim_ref), "rule_claim", derived.get("rule_ref"), item.get("summary", "")))
            for premise_claim_ref in derived.get("premise_claim_refs", []) if isinstance(derived.get("premise_claim_refs", []), list) else []:
                refs.append((str(premise_claim_ref), "premise_claim", None, item.get("summary", "")))
        for ref, role, logic_ref, summary in refs:
            bucket = by_claim.setdefault(
                ref,
                {
                    "claim_ref": ref,
                    "roles": [],
                    "logic_refs": [],
                    "summary": summary,
                },
            )
            if role not in bucket["roles"]:
                bucket["roles"].append(role)
            if logic_ref and logic_ref not in bucket["logic_refs"]:
                bucket["logic_refs"].append(logic_ref)
            if not bucket.get("summary") and summary:
                bucket["summary"] = summary
    return sorted(by_claim.values(), key=lambda item: item["claim_ref"])


def analyze_logic_payload_with_z3(
    payload: dict,
    *,
    limit: int,
    closure: str,
    timeout_ms: int,
    max_rules: int,
    max_symbols: int,
    use_unsat_core: bool,
) -> dict:
    try:
        import z3  # type: ignore
    except ModuleNotFoundError:
        return {
            "solver": "z3",
            "available": False,
            "logic_index_is_proof": False,
            "error": "z3-solver is not installed",
            "candidate_count": 0,
            "candidates": [],
        }

    direct_atoms = direct_fact_entries(payload)
    derived_atoms = materialize_rule_closure(
        payload,
        max_iterations=max(1, min(max_rules, 20)),
        max_derived=max(1, max_symbols * 4),
    ) if closure in {"rules", "system"} else []
    all_atoms = direct_atoms + derived_atoms

    solver = z3.Solver()
    solver.set(timeout=max(100, timeout_ms))
    variables: dict[tuple[str, tuple[str, ...], str, str], Any] = {}
    track_info: dict[str, dict] = {}

    def variable_for(atom: dict):
        key = atom_key(atom)
        if key not in variables:
            variables[key] = z3.Bool("atom__" + re.sub(r"[^A-Za-z0-9_]", "_", "__".join([key[0], ",".join(key[1]), key[2], key[3]])))
        return variables[key]

    assertion_index = 0
    for atom in all_atoms:
        assertion_index += 1
        track_name = safe_track_name("assert", assertion_index)
        var = variable_for(atom)
        polarity = str(atom.get("polarity", "affirmed")).strip() or "affirmed"
        expr = var if polarity == "affirmed" else z3.Not(var)
        if use_unsat_core:
            solver.assert_and_track(expr, track_name)
        else:
            solver.add(expr)
        track_info[track_name] = {
            "track_ref": track_name,
            "role": "derived_atom" if atom.get("derived") else "asserting_claim",
            "claim_ref": atom.get("claim_ref"),
            "logic_ref": atom.get("id"),
            "atom": atom_label(atom),
            "summary": atom.get("claim_summary", ""),
            "derived_from": atom.get("derived_from", {}),
        }

    functional_buckets: dict[tuple[str, tuple[str, ...], str], list[dict]] = {}
    for atom in all_atoms:
        if atom.get("functional") or "value" in atom:
            functional_buckets.setdefault(atom_bucket_key(atom), []).append(atom)
    for bucket_atoms in functional_buckets.values():
        for left, right in combinations(bucket_atoms, 2):
            if atom_value_key(left) == atom_value_key(right):
                continue
            assertion_index += 1
            track_name = safe_track_name("functional", assertion_index)
            expr = z3.Not(z3.And(variable_for(left), variable_for(right)))
            if use_unsat_core:
                solver.assert_and_track(expr, track_name)
            else:
                solver.add(expr)
            track_info[track_name] = {
                "track_ref": track_name,
                "role": "functional_constraint",
                "claim_ref": None,
                "logic_ref": None,
                "atom": f"{left.get('predicate')} functional values are mutually exclusive",
                "summary": "Generated functional predicate constraint",
                "constraint_claim_refs": sorted(
                    {
                        str(item.get("claim_ref"))
                        for item in (left, right)
                        if item.get("claim_ref")
                    }
                ),
                "constraint_logic_refs": [left.get("id"), right.get("id")],
            }

    result = solver.check()
    candidates: list[dict] = []
    if result == z3.unsat:
        core_names = [str(item) for item in solver.unsat_core()] if use_unsat_core else []
        core_items = [track_info[name] for name in core_names if name in track_info]
        for item in list(core_items):
            for claim_ref in item.get("constraint_claim_refs", []) if isinstance(item.get("constraint_claim_refs", []), list) else []:
                core_items.append(
                    {
                        "track_ref": item.get("track_ref"),
                        "role": "functional_constraint_claim",
                        "claim_ref": claim_ref,
                        "logic_ref": None,
                        "atom": item.get("atom"),
                        "summary": item.get("summary"),
                    }
                )
        candidates.append(
            {
                "kind": "system_consistency_unsat",
                "closure": closure,
                "reason": "Z3 found an inconsistent formal snapshot",
                "logic_index_is_proof": False,
                "unsat_core": core_items[: max(1, limit)],
                "claims": build_claim_summary(core_items),
                "derived_atoms": [atom for atom in derived_atoms if any(atom.get("id") == item.get("logic_ref") for item in core_items)],
                "resolution_targets": [
                    "check source quotes for the listed CLM-* records",
                    "check project/task scope and logic.context",
                    "check lifecycle state",
                    "check whether a rule claim is too broad",
                ],
            }
        )

    return {
        "solver": "z3",
        "available": True,
        "logic_index_is_proof": False,
        "closure": closure,
        "result": str(result),
        "atom_count": len(payload.get("atoms", [])) if isinstance(payload.get("atoms", []), list) else 0,
        "derived_atom_count": len(derived_atoms),
        "rule_count": len(payload.get("rules", [])) if isinstance(payload.get("rules", []), list) else 0,
        "candidate_count": len(candidates),
        "candidates": candidates,
    }
