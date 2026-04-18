"""Shared note formatting helpers."""

from __future__ import annotations


def append_note(existing_note: str, addition: str) -> str:
    base = existing_note.strip()
    suffix = addition.strip()
    if not base:
        return suffix
    if suffix in base:
        return base
    return f"{base}\n\n{suffix}"
