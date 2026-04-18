"""Language-specific code metadata analyzers for CIX generation."""

from __future__ import annotations

from .js_like import analyze_js_like
from .markdown import analyze_markdown
from .python import analyze_python


def empty_analysis() -> dict:
    return {
        "imports": [],
        "classes": [],
        "functions": [],
        "tests": [],
        "decorators": [],
        "headings": [],
        "links": [],
        "code_blocks": [],
        "parse_error": "",
    }


__all__ = ["analyze_js_like", "analyze_markdown", "analyze_python", "empty_analysis"]
