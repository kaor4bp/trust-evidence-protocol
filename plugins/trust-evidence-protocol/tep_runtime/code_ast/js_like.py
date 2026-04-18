"""Lightweight JavaScript/TypeScript metadata extraction for CIX entries."""

from __future__ import annotations

import re


def analyze_js_like(text: str) -> dict:
    imports = sorted(
        {
            match.group(1) or match.group(2)
            for match in re.finditer(r"(?:from\s+['\"]([^'\"]+)['\"]|import\s+['\"]([^'\"]+)['\"])", text)
            if match.group(1) or match.group(2)
        }
    )
    classes = re.findall(r"\bclass\s+([A-Za-z_$][\w$]*)", text)
    functions = re.findall(r"\bfunction\s+([A-Za-z_$][\w$]*)", text)
    functions.extend(re.findall(r"\b(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=\s*(?:async\s*)?\(", text))
    tests = re.findall(r"\b(?:it|test|describe)\s*\(\s*['\"]([^'\"]+)['\"]", text)
    return {
        "imports": imports,
        "classes": classes,
        "functions": functions,
        "tests": tests,
        "decorators": [],
        "parse_error": "",
    }
