"""Language-specific code metadata analyzers for CIX generation."""

from __future__ import annotations

from .js_like import analyze_js_like
from .python import analyze_python


def empty_analysis() -> dict:
    return {"imports": [], "classes": [], "functions": [], "tests": [], "decorators": [], "parse_error": ""}


__all__ = ["analyze_js_like", "analyze_python", "empty_analysis"]
