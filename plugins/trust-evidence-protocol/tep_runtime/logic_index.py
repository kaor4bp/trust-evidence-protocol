"""Generated CLM.logic index and vocabulary-pressure helpers."""

from __future__ import annotations

import json
import re
from pathlib import Path

from .claims import claim_is_archived, claim_is_fallback, claim_lifecycle_state
from .ids import now_timestamp
from .io import write_json_file, write_text_file
from .logic import LOGIC_SYMBOL_PATTERN, logic_atom_symbols
from .search import public_record_summary


GENERIC_RULE_VARIABLES = {"?x", "?y", "?z", "?a", "?b"}


def logic_index_root(root: Path) -> Path:
    return root / "logic_index"


def logic_index_paths(root: Path) -> dict[str, Path]:
    base = logic_index_root(root)
    return {
        "atoms": base / "atoms.json",
        "symbols": base / "symbols.json",
        "rules": base / "rules.json",
        "by_predicate": base / "by_predicate.json",
        "by_symbol": base / "by_symbol.json",
        "variable_graph": base / "variable_graph.json",
        "summary": base / "summary.md",
        "conflict_candidates": base / "conflict_candidates.md",
        "vocabulary_smells": base / "vocabulary_smells.md",
    }


def logic_from_record(data: dict) -> dict:
    logic = data.get("logic", {})
    return logic if isinstance(logic, dict) else {}


def logic_context_key(context) -> str:
    if not isinstance(context, dict):
        return "{}"
    return json.dumps(context, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def logic_value_key(atom: dict) -> str:
    if "value" not in atom:
        return "<no-value>"
    return json.dumps(atom.get("value"), ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def logic_claim_is_current_fact(data: dict) -> bool:
    return (
        data.get("record_type") == "claim"
        and str(data.get("status", "")).strip() in {"supported", "corroborated"}
        and not claim_is_fallback(data)
        and not claim_is_archived(data)
    )


def build_logic_index_payload(records: dict[str, dict]) -> dict:
    atoms: list[dict] = []
    rules: list[dict] = []
    symbols: dict[str, dict] = {}
    by_predicate: dict[str, list[str]] = {}
    by_symbol: dict[str, list[str]] = {}

    for claim_ref, data in sorted(records.items()):
        if data.get("record_type") != "claim":
            continue
        logic = logic_from_record(data)
        if not logic:
            continue
        claim_summary = public_record_summary(data)
        for symbol in logic.get("symbols", []) if isinstance(logic.get("symbols", []), list) else []:
            if not isinstance(symbol, dict):
                continue
            name = str(symbol.get("symbol", "")).strip()
            if not name:
                continue
            bucket = symbols.setdefault(
                name,
                {
                    "symbol": name,
                    "kind": str(symbol.get("kind", "")).strip(),
                    "definitions": [],
                    "uses": [],
                },
            )
            bucket["definitions"].append(
                {
                    "claim_ref": claim_ref,
                    "status": data.get("status", ""),
                    "lifecycle": claim_lifecycle_state(data),
                    "meaning": str(symbol.get("meaning", "")).strip(),
                    "note": str(symbol.get("note", "")).strip(),
                }
            )
        for index, atom in enumerate(logic.get("atoms", []) if isinstance(logic.get("atoms", []), list) else [], start=1):
            if not isinstance(atom, dict):
                continue
            predicate = str(atom.get("predicate", "")).strip()
            if not predicate:
                continue
            atom_id = f"{claim_ref}#atom-{index}"
            entry = {
                "id": atom_id,
                "claim_ref": claim_ref,
                "claim_status": data.get("status", ""),
                "claim_lifecycle": claim_lifecycle_state(data),
                "claim_summary": claim_summary,
                "predicate": predicate,
                "args": [str(arg).strip() for arg in atom.get("args", [])],
                "polarity": str(atom.get("polarity", "affirmed")).strip() or "affirmed",
                "context": atom.get("context", {}) if isinstance(atom.get("context", {}), dict) else {},
                "functional": bool(atom.get("functional", "value" in atom)),
                "source_refs": data.get("source_refs", []),
            }
            if "value" in atom:
                entry["value"] = atom.get("value")
            atoms.append(entry)
            by_predicate.setdefault(predicate, []).append(atom_id)
            for symbol in logic_atom_symbols(entry):
                by_symbol.setdefault(symbol, []).append(atom_id)
                symbols.setdefault(
                    symbol,
                    {"symbol": symbol, "kind": "", "definitions": [], "uses": []},
                )["uses"].append({"atom_ref": atom_id, "claim_ref": claim_ref, "predicate": predicate})
        for index, rule in enumerate(logic.get("rules", []) if isinstance(logic.get("rules", []), list) else [], start=1):
            if not isinstance(rule, dict):
                continue
            rule_id = f"{claim_ref}#rule-{index}"
            entry = {
                "id": rule_id,
                "claim_ref": claim_ref,
                "claim_status": data.get("status", ""),
                "claim_lifecycle": claim_lifecycle_state(data),
                "claim_summary": claim_summary,
                "name": str(rule.get("name", "")).strip() or rule_id,
                "body": rule.get("body", []),
                "head": rule.get("head", {}),
                "source_refs": data.get("source_refs", []),
            }
            rules.append(entry)
            head = entry["head"] if isinstance(entry["head"], dict) else {}
            predicate = str(head.get("predicate", "")).strip()
            if predicate:
                by_predicate.setdefault(predicate, []).append(rule_id)

    return {
        "generated_at": now_timestamp(),
        "atoms": atoms,
        "symbols": symbols,
        "rules": rules,
        "by_predicate": {key: sorted(value) for key, value in sorted(by_predicate.items())},
        "by_symbol": {key: sorted(value) for key, value in sorted(by_symbol.items())},
    }


def logic_symbol_namespace(symbol: str) -> str:
    return symbol.split(":", 1)[0] if ":" in symbol else ""


def logic_symbol_local(symbol: str) -> str:
    return symbol.split(":", 1)[1] if ":" in symbol else symbol


def normalized_symbol_local(symbol: str) -> str:
    return re.sub(r"[^a-z0-9]", "", logic_symbol_local(symbol).lower())


def graph_add_edge(graph: dict[str, set[str]], left: str, right: str) -> None:
    graph.setdefault(left, set()).add(right)
    graph.setdefault(right, set()).add(left)


def graph_components(graph: dict[str, set[str]]) -> list[list[str]]:
    visited: set[str] = set()
    components: list[list[str]] = []
    for node in sorted(graph):
        if node in visited:
            continue
        stack = [node]
        component: list[str] = []
        visited.add(node)
        while stack:
            current = stack.pop()
            component.append(current)
            for neighbor in sorted(graph.get(current, set())):
                if neighbor not in visited:
                    visited.add(neighbor)
                    stack.append(neighbor)
        components.append(sorted(component))
    return sorted(components, key=lambda item: (-len(item), item[0] if item else ""))


def logic_rule_variables(rule: dict) -> dict[str, dict]:
    variables: dict[str, dict] = {}
    body = rule.get("body", []) if isinstance(rule.get("body", []), list) else []
    head = rule.get("head", {}) if isinstance(rule.get("head", {}), dict) else {}
    for section, atoms in (("body", body), ("head", [head] if head else [])):
        for atom in atoms:
            if not isinstance(atom, dict):
                continue
            predicate = str(atom.get("predicate", "")).strip()
            for position, arg in enumerate(atom.get("args", []), start=1):
                rendered = str(arg).strip()
                if not rendered.startswith("?"):
                    continue
                bucket = variables.setdefault(
                    rendered,
                    {
                        "variable": rendered,
                        "sections": [],
                        "predicates": [],
                        "positions": [],
                    },
                )
                if section not in bucket["sections"]:
                    bucket["sections"].append(section)
                if predicate and predicate not in bucket["predicates"]:
                    bucket["predicates"].append(predicate)
                bucket["positions"].append({"section": section, "predicate": predicate, "position": position})
    return variables


def build_logic_vocabulary_graph(payload: dict) -> dict:
    atoms = payload.get("atoms", []) if isinstance(payload.get("atoms", []), list) else []
    rules = payload.get("rules", []) if isinstance(payload.get("rules", []), list) else []
    symbols_payload = payload.get("symbols", {}) if isinstance(payload.get("symbols", {}), dict) else {}

    symbols: dict[str, dict] = {}
    predicates: dict[str, dict] = {}
    rule_variables: dict[str, dict] = {}
    graph: dict[str, set[str]] = {}

    for symbol, data in sorted(symbols_payload.items()):
        uses = data.get("uses", []) if isinstance(data.get("uses", []), list) else []
        definitions = data.get("definitions", []) if isinstance(data.get("definitions", []), list) else []
        symbols[symbol] = {
            "symbol": symbol,
            "namespace": logic_symbol_namespace(symbol),
            "local": logic_symbol_local(symbol),
            "kind": str(data.get("kind", "")).strip(),
            "meanings": sorted(
                {
                    str(item.get("meaning", "")).strip()
                    for item in definitions
                    if isinstance(item, dict) and str(item.get("meaning", "")).strip()
                }
            ),
            "definition_count": len(definitions),
            "use_count": len(uses),
            "claim_refs": sorted(
                {
                    str(item.get("claim_ref"))
                    for item in definitions + uses
                    if isinstance(item, dict) and item.get("claim_ref")
                }
            ),
        }
        graph.setdefault(f"symbol:{symbol}", set())

    for atom in atoms:
        if not isinstance(atom, dict):
            continue
        predicate = str(atom.get("predicate", "")).strip()
        if not predicate:
            continue
        atom_ref = str(atom.get("id", "")).strip()
        predicate_bucket = predicates.setdefault(
            predicate,
            {
                "predicate": predicate,
                "atom_refs": [],
                "rule_refs": [],
                "claim_refs": [],
                "arg_positions": {},
            },
        )
        if atom_ref:
            predicate_bucket["atom_refs"].append(atom_ref)
        claim_ref = str(atom.get("claim_ref", "")).strip()
        if claim_ref and claim_ref not in predicate_bucket["claim_refs"]:
            predicate_bucket["claim_refs"].append(claim_ref)
        predicate_node = f"predicate:{predicate}"
        graph.setdefault(predicate_node, set())
        for position, arg in enumerate(atom.get("args", []), start=1):
            symbol = str(arg).strip()
            if not LOGIC_SYMBOL_PATTERN.match(symbol):
                continue
            position_key = str(position)
            position_bucket = predicate_bucket["arg_positions"].setdefault(
                position_key,
                {"symbols": [], "namespaces": [], "kinds": []},
            )
            if symbol not in position_bucket["symbols"]:
                position_bucket["symbols"].append(symbol)
            namespace = logic_symbol_namespace(symbol)
            if namespace and namespace not in position_bucket["namespaces"]:
                position_bucket["namespaces"].append(namespace)
            kind = symbols.get(symbol, {}).get("kind", "")
            if kind and kind not in position_bucket["kinds"]:
                position_bucket["kinds"].append(kind)
            graph_add_edge(graph, predicate_node, f"symbol:{symbol}")

    for rule in rules:
        if not isinstance(rule, dict):
            continue
        rule_ref = str(rule.get("id", "")).strip()
        rule_node = f"rule:{rule_ref}"
        graph.setdefault(rule_node, set())
        variables = logic_rule_variables(rule)
        rule_variables[rule_ref] = {
            "rule_ref": rule_ref,
            "claim_ref": rule.get("claim_ref"),
            "name": rule.get("name"),
            "variables": variables,
        }
        for atom in [*(rule.get("body", []) if isinstance(rule.get("body", []), list) else []), rule.get("head", {})]:
            if not isinstance(atom, dict):
                continue
            predicate = str(atom.get("predicate", "")).strip()
            if not predicate:
                continue
            predicate_bucket = predicates.setdefault(
                predicate,
                {"predicate": predicate, "atom_refs": [], "rule_refs": [], "claim_refs": [], "arg_positions": {}},
            )
            if rule_ref and rule_ref not in predicate_bucket["rule_refs"]:
                predicate_bucket["rule_refs"].append(rule_ref)
            claim_ref = str(rule.get("claim_ref", "")).strip()
            if claim_ref and claim_ref not in predicate_bucket["claim_refs"]:
                predicate_bucket["claim_refs"].append(claim_ref)
            graph_add_edge(graph, rule_node, f"predicate:{predicate}")
        for variable, detail in variables.items():
            variable_node = f"variable:{rule_ref}:{variable}"
            graph_add_edge(graph, rule_node, variable_node)
            for predicate in detail.get("predicates", []):
                graph_add_edge(graph, variable_node, f"predicate:{predicate}")

    smells: list[dict] = []
    for symbol, detail in sorted(symbols.items()):
        if detail["definition_count"] > 0 and detail["use_count"] == 0:
            smells.append(
                {
                    "kind": "orphan-symbol",
                    "severity": "warning",
                    "symbol": symbol,
                    "claim_refs": detail["claim_refs"],
                    "message": "Symbol is introduced but not used by any logic atom.",
                }
            )
        if detail["definition_count"] > 0 and not detail.get("meanings"):
            smells.append(
                {
                    "kind": "missing-symbol-meaning",
                    "severity": "warning",
                    "symbol": symbol,
                    "claim_refs": detail["claim_refs"],
                    "message": "Symbol lacks an explicit meaning; explain what semantic object it represents.",
                }
            )

    by_namespace_local: dict[tuple[str, str], list[str]] = {}
    for symbol in symbols:
        key = (logic_symbol_namespace(symbol), normalized_symbol_local(symbol))
        by_namespace_local.setdefault(key, []).append(symbol)
    for (_, normalized), bucket in sorted(by_namespace_local.items()):
        if normalized and len(bucket) > 1:
            smells.append(
                {
                    "kind": "duplicate-like-symbol",
                    "severity": "warning",
                    "symbols": sorted(bucket),
                    "message": "Symbols normalize to the same local name; reuse or link them explicitly.",
                }
            )

    for predicate, detail in sorted(predicates.items()):
        total_refs = len(detail.get("atom_refs", [])) + len(detail.get("rule_refs", []))
        if total_refs == 1:
            smells.append(
                {
                    "kind": "single-use-predicate",
                    "severity": "info",
                    "predicate": predicate,
                    "claim_refs": detail.get("claim_refs", []),
                    "message": "Predicate appears only once; check whether an existing predicate should be reused.",
                }
            )

    for rule_ref, detail in sorted(rule_variables.items()):
        variables = detail.get("variables", {})
        for variable, variable_detail in sorted(variables.items()):
            if variable in GENERIC_RULE_VARIABLES:
                smells.append(
                    {
                        "kind": "generic-rule-variable",
                        "severity": "info",
                        "rule_ref": rule_ref,
                        "claim_ref": detail.get("claim_ref"),
                        "variable": variable,
                        "message": "Generic variable name reduces readability; prefer role-shaped names such as ?service.",
                    }
                )
            if "head" not in variable_detail.get("sections", []) and len(variable_detail.get("predicates", [])) == 1:
                smells.append(
                    {
                        "kind": "weakly-connected-variable",
                        "severity": "warning",
                        "rule_ref": rule_ref,
                        "claim_ref": detail.get("claim_ref"),
                        "variable": variable,
                        "message": "Variable is local to one body predicate and does not connect rule predicates or head.",
                    }
                )

    components = [
        {"id": f"LGC-{index:04d}", "nodes": component, "size": len(component)}
        for index, component in enumerate(graph_components(graph), start=1)
    ]

    return {
        "generated_at": payload.get("generated_at") or now_timestamp(),
        "logic_graph_is_proof": False,
        "symbols": symbols,
        "predicates": predicates,
        "rules": rule_variables,
        "components": components,
        "smells": smells,
    }


def logic_conflict_candidates_from_payload(payload: dict, limit: int) -> list[dict]:
    atoms = payload.get("atoms", [])
    if not isinstance(atoms, list):
        return []
    by_bucket: dict[tuple[str, tuple[str, ...], str], list[dict]] = {}
    for atom in atoms:
        if not isinstance(atom, dict):
            continue
        if str(atom.get("claim_status", "")).strip() not in {"supported", "corroborated"}:
            continue
        if str(atom.get("claim_lifecycle", "active")).strip() != "active":
            continue
        bucket = (
            str(atom.get("predicate", "")).strip(),
            tuple(str(arg).strip() for arg in atom.get("args", [])),
            logic_context_key(atom.get("context", {})),
        )
        by_bucket.setdefault(bucket, []).append(atom)

    candidates: list[dict] = []
    for (predicate, args, context_key), bucket_atoms in by_bucket.items():
        for left_index, left in enumerate(bucket_atoms):
            for right in bucket_atoms[left_index + 1 :]:
                if left.get("claim_ref") == right.get("claim_ref"):
                    continue
                left_value = logic_value_key(left)
                right_value = logic_value_key(right)
                left_polarity = str(left.get("polarity", "affirmed")).strip()
                right_polarity = str(right.get("polarity", "affirmed")).strip()
                reason = ""
                if left_value == right_value and left_polarity != right_polarity:
                    reason = "opposite polarity for same predicate/args/value/context"
                elif left_polarity == right_polarity == "affirmed" and left_value != right_value and (
                    left.get("functional") or right.get("functional")
                ):
                    reason = "different affirmed values for functional predicate/args/context"
                if not reason:
                    continue
                candidates.append(
                    {
                        "predicate": predicate,
                        "args": list(args),
                        "context": json.loads(context_key),
                        "reason": reason,
                        "left": left,
                        "right": right,
                        "logic_index_is_proof": False,
                    }
                )
    return sorted(
        candidates,
        key=lambda item: (
            item["predicate"],
            ",".join(item["args"]),
            item["left"]["claim_ref"],
            item["right"]["claim_ref"],
        ),
    )[: max(1, limit)]


def write_logic_index_reports(root: Path, payload: dict, candidates: list[dict]) -> None:
    paths = logic_index_paths(root)
    vocabulary_graph = build_logic_vocabulary_graph(payload)
    write_json_file(paths["atoms"], payload["atoms"])
    write_json_file(paths["symbols"], payload["symbols"])
    write_json_file(paths["rules"], payload["rules"])
    write_json_file(paths["by_predicate"], payload["by_predicate"])
    write_json_file(paths["by_symbol"], payload["by_symbol"])
    write_json_file(paths["variable_graph"], vocabulary_graph)

    summary_lines = [
        "# Logic Index Summary",
        "",
        "Generated predicate index. This is checking/navigation data, not proof.",
        "",
        f"- generated_at: `{payload['generated_at']}`",
        f"- atoms: `{len(payload['atoms'])}`",
        f"- symbols: `{len(payload['symbols'])}`",
        f"- rules: `{len(payload['rules'])}`",
        f"- conflict_candidates: `{len(candidates)}`",
        f"- vocabulary_smells: `{len(vocabulary_graph['smells'])}`",
        "",
        "## Predicates",
    ]
    for predicate, refs in sorted(payload["by_predicate"].items()):
        summary_lines.append(f"- `{predicate}` refs={len(refs)}")
    write_text_file(paths["summary"], "\n".join(summary_lines).rstrip() + "\n")

    lines = [
        "# Logic Conflict Candidates",
        "",
        "Generated predicate-level candidate report. Candidates are not proof and do not change claim status.",
        "",
    ]
    if not candidates:
        lines.append("- no candidates")
    for item in candidates:
        lines.append(
            f"- `{item['predicate']}`({', '.join(item['args'])}) "
            f"`{item['left']['claim_ref']}` <-> `{item['right']['claim_ref']}`: {item['reason']}"
        )
    write_text_file(paths["conflict_candidates"], "\n".join(lines).rstrip() + "\n")

    smell_lines = [
        "# Logic Vocabulary Smells",
        "",
        "Generated pressure report for CLM.logic vocabulary. This is navigation data, not proof.",
        "",
    ]
    if not vocabulary_graph["smells"]:
        smell_lines.append("- no smells")
    for smell in vocabulary_graph["smells"]:
        target = smell.get("symbol") or smell.get("predicate") or smell.get("rule_ref") or ",".join(smell.get("symbols", []))
        smell_lines.append(f"- `{smell['kind']}` severity=`{smell['severity']}` target=`{target}`: {smell['message']}")
    write_text_file(paths["vocabulary_smells"], "\n".join(smell_lines).rstrip() + "\n")


def load_logic_index_payload(root: Path) -> dict:
    paths = logic_index_paths(root)
    payload: dict = {}
    for key in ("atoms", "symbols", "rules", "by_predicate", "by_symbol"):
        path = paths[key]
        try:
            payload[key] = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            payload[key] = [] if key in {"atoms", "rules"} else {}
    return payload


def load_logic_vocabulary_graph(root: Path) -> dict:
    path = logic_index_paths(root)["variable_graph"]
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}
