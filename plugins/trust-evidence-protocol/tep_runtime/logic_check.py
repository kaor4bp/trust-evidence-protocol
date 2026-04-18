"""Logic-check solver settings and report rendering helpers."""

from __future__ import annotations

from pathlib import Path

from .settings import load_settings


def effective_logic_solver(root: Path, requested_solver: str | None) -> str:
    if requested_solver:
        return requested_solver
    settings = load_settings(root)
    analysis = settings.get("analysis", {}) if isinstance(settings.get("analysis", {}), dict) else {}
    logic_solver = analysis.get("logic_solver", {}) if isinstance(analysis.get("logic_solver", {}), dict) else {}
    backend = str(logic_solver.get("backend", "structural")).strip()
    return backend if backend in {"structural", "z3", "auto"} else "structural"


def logic_solver_settings(root: Path) -> dict:
    settings = load_settings(root)
    analysis = settings.get("analysis", {}) if isinstance(settings.get("analysis", {}), dict) else {}
    logic_solver = analysis.get("logic_solver", {}) if isinstance(analysis.get("logic_solver", {}), dict) else {}
    return logic_solver


def structural_logic_check_payload(payload: dict, candidates: list[dict], selected_solver: str) -> dict:
    return {
        "solver": "structural",
        "logic_index_is_proof": False,
        "atom_count": len(payload["atoms"]),
        "symbol_count": len(payload["symbols"]),
        "rule_count": len(payload["rules"]),
        "candidate_count": len(candidates),
        "candidates": candidates,
        **(
            {"solver_warning": "z3-solver is not installed; auto fell back to structural"}
            if selected_solver == "auto"
            else {}
        ),
    }


def structural_logic_check_text_lines(payload: dict, candidates: list[dict], selected_solver: str, icon: str) -> list[str]:
    lines = [
        f"# {icon} Logic Check",
        "",
        "Mode: read-only predicate consistency check. Not proof.",
        "",
        f"- atoms: {len(payload['atoms'])}",
        f"- symbols: {len(payload['symbols'])}",
        f"- rules: {len(payload['rules'])}",
        f"- conflict candidates: {len(candidates)}",
    ]
    if selected_solver == "auto":
        lines.append("- solver warning: z3-solver is not installed; auto fell back to structural")
    if candidates:
        lines.extend(["", "## Candidates"])
        for item in candidates:
            lines.append(
                f"- `{item['predicate']}`({', '.join(item['args'])}) "
                f"`{item['left']['claim_ref']}` <-> `{item['right']['claim_ref']}`: {item['reason']}"
            )
    return lines


def z3_logic_check_text_lines(result: dict, structural_candidates: list[dict], icon: str) -> list[str]:
    lines = [
        f"# {icon} Logic Check",
        "",
        "Mode: Z3-backed system consistency candidate check. Not proof.",
        "",
    ]
    if not result.get("available"):
        lines.append(f"- solver: z3 unavailable ({result.get('error', 'unknown error')})")
        if structural_candidates:
            lines.append(f"- structural fallback candidates: {len(structural_candidates)}")
        return lines

    lines.extend(
        [
            "- solver: z3",
            f"- result: {result.get('result')}",
            f"- closure: {result.get('closure')}",
            f"- atoms: {result.get('atom_count')}",
            f"- derived atoms: {result.get('derived_atom_count')}",
            f"- rules: {result.get('rule_count')}",
            f"- conflict candidates: {result.get('candidate_count')}",
        ]
    )
    candidates = result.get("candidates", [])
    if candidates:
        lines.extend(["", "## Candidates"])
        for candidate in candidates:
            lines.append(f"- {candidate.get('kind')}: {candidate.get('reason')}")
            claims = candidate.get("claims", [])
            if claims:
                lines.append("  claims:")
                for claim in claims:
                    roles = ",".join(claim.get("roles", []))
                    logic_refs = ",".join(claim.get("logic_refs", []))
                    lines.append(f"  - `{claim.get('claim_ref')}` roles=`{roles}` logic_refs=`{logic_refs}`")
            derived_atoms = candidate.get("derived_atoms", [])
            if derived_atoms:
                lines.append("  derived:")
                for atom in derived_atoms:
                    lines.append(f"  - `{atom.get('id')}` {atom.get('predicate')}({', '.join(atom.get('args', []))})")
    lines.extend(["", "These claims participate in an inconsistent formal snapshot; inspect underlying SRC-* before changing claim status."])
    return lines
