"""Python code metadata extraction for CIX entries."""

from __future__ import annotations

import ast


def analyze_python(text: str) -> dict:
    imports: set[str] = set()
    classes: list[str] = []
    functions: list[str] = []
    decorators: set[str] = set()
    parse_error = ""
    try:
        tree = ast.parse(text)
    except SyntaxError as exc:
        return {
            "imports": [],
            "classes": [],
            "functions": [],
            "tests": [],
            "decorators": [],
            "parse_error": str(exc),
        }
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.add(alias.name.split(".", 1)[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.add(node.module.split(".", 1)[0])
        elif isinstance(node, ast.ClassDef):
            classes.append(node.name)
            for decorator in node.decorator_list:
                decorators.add(ast.unparse(decorator) if hasattr(ast, "unparse") else type(decorator).__name__)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            functions.append(node.name)
            for decorator in node.decorator_list:
                decorators.add(ast.unparse(decorator) if hasattr(ast, "unparse") else type(decorator).__name__)
    tests = [name for name in functions if name.startswith("test_")]
    return {
        "imports": sorted(imports),
        "classes": classes,
        "functions": functions,
        "tests": tests,
        "decorators": sorted(decorators),
        "parse_error": parse_error,
    }
