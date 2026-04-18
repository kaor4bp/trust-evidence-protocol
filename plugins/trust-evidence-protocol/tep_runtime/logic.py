from __future__ import annotations

import json
import re
from pathlib import Path

from tep_runtime.claims import claim_lifecycle_state
from tep_runtime.errors import ValidationError


LOGIC_POLARITIES = {"affirmed", "denied"}
LOGIC_SYMBOL_KINDS = {"entity", "action", "value", "type", "concept", "system", "code", "runtime"}
LOGIC_PREDICATE_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9_:-]*$")
LOGIC_SYMBOL_PATTERN = re.compile(r"^[a-z][a-z0-9_-]*:[A-Za-z0-9_.:-]+$")
LOGIC_VARIABLE_PATTERN = re.compile(r"^\?[A-Za-z][A-Za-z0-9_]*$")


def parse_bool_token(value: str) -> bool:
    normalized = value.strip().lower()
    if normalized == "true":
        return True
    if normalized == "false":
        return False
    raise ValueError("boolean comparison values must be true or false")


def parse_scalar_token(value: str):
    raw = value.strip()
    if raw.lower() == "true":
        return True
    if raw.lower() == "false":
        return False
    if raw.lower() == "null":
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return raw


def parse_logic_context(raw: str) -> dict:
    if not raw:
        return {}
    context: dict = {}
    for item in raw.split(";"):
        if not item.strip():
            continue
        if "=" not in item:
            raise ValueError(f"logic context item must be key=value: {item}")
        key, value = [part.strip() for part in item.split("=", 1)]
        if not key:
            raise ValueError("logic context key must be non-empty")
        context[key] = parse_scalar_token(value)
    return context


def parse_logic_atom_spec(raw: str) -> dict:
    parts = [part.strip() for part in raw.split("|")]
    if len(parts) < 2:
        raise ValueError("--logic-atom must be predicate|arg1,arg2[|polarity][|value=...][|context=k=v;...][|functional]")
    predicate = parts[0]
    if not LOGIC_PREDICATE_PATTERN.match(predicate):
        raise ValueError(f"invalid logic predicate: {predicate}")
    args = [item.strip() for item in parts[1].split(",") if item.strip()]
    if not args:
        raise ValueError("--logic-atom args must be non-empty")
    polarity = parts[2] if len(parts) >= 3 and parts[2] else "affirmed"
    atom = {
        "predicate": predicate,
        "args": args,
        "polarity": polarity,
    }
    for option in parts[3:]:
        if not option:
            continue
        if option == "functional":
            atom["functional"] = True
        elif option.startswith("functional="):
            atom["functional"] = parse_bool_token(option.split("=", 1)[1])
        elif option.startswith("value="):
            atom["value"] = parse_scalar_token(option.split("=", 1)[1])
        elif option.startswith("context="):
            atom["context"] = parse_logic_context(option.split("=", 1)[1])
        else:
            atom["value"] = parse_scalar_token(option)
    if "value" in atom and "functional" not in atom:
        atom["functional"] = True
    return atom


def parse_logic_symbol_spec(raw: str) -> dict:
    parts = [part.strip() for part in raw.split("|")]
    if len(parts) < 3:
        raise ValueError("--logic-symbol must be symbol|kind|meaning[|note]")
    symbol, kind, meaning = parts[0], parts[1], parts[2]
    if not LOGIC_SYMBOL_PATTERN.match(symbol):
        raise ValueError(f"invalid logic symbol: {symbol}")
    if kind not in LOGIC_SYMBOL_KINDS:
        raise ValueError(f"invalid logic symbol kind: {kind}")
    if not meaning:
        raise ValueError("--logic-symbol meaning must explain what the symbol represents")
    payload = {"symbol": symbol, "kind": kind, "meaning": meaning}
    if len(parts) >= 4 and parts[3]:
        payload["note"] = parts[3]
    return payload


def parse_logic_atom_expression(raw: str) -> dict:
    match = re.match(r"^\s*([A-Za-z][A-Za-z0-9_:-]*)\((.*)\)\s*$", raw)
    if not match:
        raise ValueError(f"invalid logic atom expression: {raw}")
    predicate = match.group(1)
    args = [item.strip() for item in match.group(2).split(",") if item.strip()]
    if not args:
        raise ValueError(f"logic atom expression has no args: {raw}")
    return {"predicate": predicate, "args": args, "polarity": "affirmed"}


def parse_logic_rule_spec(raw: str) -> dict:
    parts = [part.strip() for part in raw.split("|", 1)]
    if len(parts) != 2 or "->" not in parts[1]:
        raise ValueError("--logic-rule must be name|Body(?x)&Other(?x,?y)->Head(?x,?y)")
    name, expression = parts
    body_raw, head_raw = [part.strip() for part in expression.split("->", 1)]
    body = [parse_logic_atom_expression(item.strip()) for item in body_raw.split("&") if item.strip()]
    if not body:
        raise ValueError("--logic-rule body must be non-empty")
    return {"name": name, "body": body, "head": parse_logic_atom_expression(head_raw)}


def load_logic_json_payload(raw: str) -> dict:
    value = raw.strip()
    if value.startswith("@"):
        path = Path(value[1:]).expanduser().resolve()
        value = path.read_text(encoding="utf-8")
    payload = json.loads(value)
    if not isinstance(payload, dict):
        raise ValueError("--logic-json must decode to an object")
    return payload


def build_logic_payload(args) -> dict | None:
    logic: dict = {}
    if args.logic_json:
        logic.update(load_logic_json_payload(args.logic_json))
    atoms = list(logic.get("atoms", [])) if isinstance(logic.get("atoms", []), list) else []
    symbols = list(logic.get("symbols", [])) if isinstance(logic.get("symbols", []), list) else []
    rules = list(logic.get("rules", [])) if isinstance(logic.get("rules", []), list) else []
    atoms.extend(parse_logic_atom_spec(raw) for raw in args.logic_atoms)
    symbols.extend(parse_logic_symbol_spec(raw) for raw in args.logic_symbols)
    rules.extend(parse_logic_rule_spec(raw) for raw in args.logic_rules)
    if not atoms and not symbols and not rules:
        return None
    return {
        "symbols": symbols,
        "atoms": atoms,
        "rules": rules,
    }


def is_scalar_logic_value(value) -> bool:
    return value is None or isinstance(value, (str, int, float, bool))


def validate_logic_context(context, label: str) -> list[str]:
    errors: list[str] = []
    if context in (None, ""):
        return errors
    if not isinstance(context, dict):
        return [f"{label}.context must be an object when provided"]
    for key, value in context.items():
        if not str(key).strip():
            errors.append(f"{label}.context keys must be non-empty")
        if not isinstance(value, (str, int, float, bool)):
            errors.append(f"{label}.context.{key} must be a scalar")
    return errors


def validate_logic_atom(atom, label: str, allow_variables: bool) -> list[str]:
    errors: list[str] = []
    if not isinstance(atom, dict):
        return [f"{label} must be an object"]
    predicate = str(atom.get("predicate", "")).strip()
    if not predicate:
        errors.append(f"{label}.predicate is required")
    elif not LOGIC_PREDICATE_PATTERN.match(predicate):
        errors.append(f"{label}.predicate is invalid")
    args = atom.get("args", [])
    if not isinstance(args, list) or not args:
        errors.append(f"{label}.args must be a non-empty list")
        args = []
    for index, arg in enumerate(args, start=1):
        rendered = str(arg).strip()
        if not rendered:
            errors.append(f"{label}.args[{index}] must be non-empty")
        elif LOGIC_VARIABLE_PATTERN.match(rendered):
            if not allow_variables:
                errors.append(f"{label}.args[{index}] cannot be a variable outside logic.rules")
        elif not LOGIC_SYMBOL_PATTERN.match(rendered):
            errors.append(f"{label}.args[{index}] must be a typed symbol like namespace:name")
    polarity = str(atom.get("polarity", "affirmed")).strip() or "affirmed"
    if polarity not in LOGIC_POLARITIES:
        errors.append(f"{label}.polarity must be affirmed or denied")
    if "value" in atom and not is_scalar_logic_value(atom.get("value")):
        errors.append(f"{label}.value must be scalar when provided")
    if "functional" in atom and not isinstance(atom.get("functional"), bool):
        errors.append(f"{label}.functional must be boolean when provided")
    errors.extend(validate_logic_context(atom.get("context"), label))
    return errors


def logic_atom_variables(atom: dict) -> set[str]:
    variables = set()
    for arg in atom.get("args", []):
        rendered = str(arg).strip()
        if LOGIC_VARIABLE_PATTERN.match(rendered):
            variables.add(rendered)
    return variables


def logic_atom_symbols(atom: dict) -> set[str]:
    symbols = set()
    for arg in atom.get("args", []):
        rendered = str(arg).strip()
        if LOGIC_SYMBOL_PATTERN.match(rendered):
            symbols.add(rendered)
    return symbols


def validate_logic_rule(rule, label: str) -> list[str]:
    errors: list[str] = []
    if not isinstance(rule, dict):
        return [f"{label} must be an object"]
    name = str(rule.get("name", "")).strip()
    if not name:
        errors.append(f"{label}.name is required")
    body = rule.get("body", [])
    if not isinstance(body, list) or not body:
        errors.append(f"{label}.body must be a non-empty list")
        body = []
    head = rule.get("head")
    if not isinstance(head, dict):
        errors.append(f"{label}.head must be an object")
        head = {}
    bound_variables: set[str] = set()
    for index, atom in enumerate(body, start=1):
        errors.extend(validate_logic_atom(atom, f"{label}.body[{index}]", allow_variables=True))
        if isinstance(atom, dict):
            if str(atom.get("polarity", "affirmed")).strip() not in {"", "affirmed"}:
                errors.append(f"{label}.body[{index}].polarity must be affirmed in MVP logic rules")
            bound_variables.update(logic_atom_variables(atom))
    if head:
        errors.extend(validate_logic_atom(head, f"{label}.head", allow_variables=True))
        if str(head.get("polarity", "affirmed")).strip() not in {"", "affirmed"}:
            errors.append(f"{label}.head.polarity must be affirmed in MVP logic rules")
        head_variables = logic_atom_variables(head)
        unbound = sorted(head_variables - bound_variables)
        if unbound:
            errors.append(f"{label}.head has unbound variables: {', '.join(unbound)}")
    return errors


def validate_claim_logic(logic: dict) -> list[str]:
    errors: list[str] = []
    atoms = logic.get("atoms", [])
    rules = logic.get("rules", [])
    symbols = logic.get("symbols", [])
    if not atoms and not rules:
        errors.append("logic must define atoms or rules")
    if atoms in ("", None):
        atoms = []
    if rules in ("", None):
        rules = []
    if symbols in ("", None):
        symbols = []
    if not isinstance(atoms, list):
        errors.append("logic.atoms must be a list")
        atoms = []
    if not isinstance(rules, list):
        errors.append("logic.rules must be a list")
        rules = []
    if not isinstance(symbols, list):
        errors.append("logic.symbols must be a list")
        symbols = []
    for index, atom in enumerate(atoms, start=1):
        errors.extend(validate_logic_atom(atom, f"logic.atoms[{index}]", allow_variables=False))
    seen_symbols: set[str] = set()
    for index, symbol in enumerate(symbols, start=1):
        if not isinstance(symbol, dict):
            errors.append(f"logic.symbols[{index}] must be an object")
            continue
        name = str(symbol.get("symbol", "")).strip()
        kind = str(symbol.get("kind", "")).strip()
        if not name:
            errors.append(f"logic.symbols[{index}].symbol is required")
        elif not LOGIC_SYMBOL_PATTERN.match(name):
            errors.append(f"logic.symbols[{index}].symbol must be shaped like namespace:name")
        elif name in seen_symbols:
            errors.append(f"logic.symbols[{index}].symbol duplicates {name}")
        seen_symbols.add(name)
        if kind not in LOGIC_SYMBOL_KINDS:
            errors.append(f"logic.symbols[{index}].kind is invalid")
        if "introduced_by" in symbol and not isinstance(symbol.get("introduced_by"), str):
            errors.append(f"logic.symbols[{index}].introduced_by must be a string when provided")
        if "meaning" in symbol and not isinstance(symbol.get("meaning"), str):
            errors.append(f"logic.symbols[{index}].meaning must be a string when provided")
        if "note" in symbol and not isinstance(symbol.get("note"), str):
            errors.append(f"logic.symbols[{index}].note must be a string when provided")
    for index, rule in enumerate(rules, start=1):
        errors.extend(validate_logic_rule(rule, f"logic.rules[{index}]"))
    return errors


def logic_from_claim(data: dict) -> dict:
    logic = data.get("logic", {})
    return logic if isinstance(logic, dict) else {}


def collect_logic_symbol_definitions(records: dict[str, dict]) -> dict[str, list[dict]]:
    definitions: dict[str, list[dict]] = {}
    for record_id, data in records.items():
        if data.get("record_type") != "claim":
            continue
        if str(data.get("status", "")).strip() == "rejected":
            continue
        logic = logic_from_claim(data)
        symbols = logic.get("symbols", [])
        if not isinstance(symbols, list):
            continue
        for symbol in symbols:
            if not isinstance(symbol, dict):
                continue
            name = str(symbol.get("symbol", "")).strip()
            if LOGIC_SYMBOL_PATTERN.match(name):
                definitions.setdefault(name, []).append(
                    {
                        "claim_ref": record_id,
                        "kind": str(symbol.get("kind", "")).strip(),
                        "status": str(data.get("status", "")).strip(),
                        "lifecycle": claim_lifecycle_state(data),
                    }
                )
    return definitions


def validate_logic_state(root: Path, records: dict[str, dict]) -> list[ValidationError]:
    errors: list[ValidationError] = []
    definitions = collect_logic_symbol_definitions(records)

    def has_supported_introduction(symbol: str) -> bool:
        return any(
            item.get("status") in {"supported", "corroborated"} and item.get("lifecycle") == "active"
            for item in definitions.get(symbol, [])
        )

    for record_id, data in records.items():
        if data.get("record_type") != "claim":
            continue
        logic = logic_from_claim(data)
        if not logic:
            continue
        path = Path(data["_path"])
        claim_status = str(data.get("status", "")).strip()
        requires_supported_symbols = claim_status in {"supported", "corroborated"}
        atoms = logic.get("atoms", [])
        if isinstance(atoms, list):
            for atom_index, atom in enumerate(atoms, start=1):
                if not isinstance(atom, dict):
                    continue
                for symbol in sorted(logic_atom_symbols(atom)):
                    if symbol not in definitions:
                        errors.append(
                            ValidationError(path, f"logic.atoms[{atom_index}] references unknown symbol: {symbol}")
                        )
                    elif requires_supported_symbols and not has_supported_introduction(symbol):
                        errors.append(
                            ValidationError(
                                path,
                                f"logic.atoms[{atom_index}] symbol lacks supported/corroborated introduction: {symbol}",
                            )
                        )
        rules = logic.get("rules", [])
        if isinstance(rules, list):
            for rule_index, rule in enumerate(rules, start=1):
                if not isinstance(rule, dict):
                    continue
                for atom in list(rule.get("body", [])) + [rule.get("head", {})]:
                    if not isinstance(atom, dict):
                        continue
                    for symbol in sorted(logic_atom_symbols(atom)):
                        if symbol not in definitions:
                            errors.append(
                                ValidationError(path, f"logic.rules[{rule_index}] references unknown symbol: {symbol}")
                            )
                        elif requires_supported_symbols and not has_supported_introduction(symbol):
                            errors.append(
                                ValidationError(
                                    path,
                                    f"logic.rules[{rule_index}] symbol lacks supported/corroborated introduction: {symbol}",
                                )
                            )
    return errors
