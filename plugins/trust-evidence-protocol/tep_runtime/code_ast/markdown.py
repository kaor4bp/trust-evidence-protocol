"""Markdown outline metadata extraction for CIX entries."""

from __future__ import annotations

import re

HEADING_PATTERN = re.compile(r"^(?P<marks>#{1,6})\s+(?P<title>.+?)\s*#*\s*$")
LINK_PATTERN = re.compile(r"(?<!!)\[(?P<text>[^\]]+)\]\((?P<target>[^)\s]+)(?:\s+\"[^\"]*\")?\)")
FENCE_PATTERN = re.compile(r"^\s*(```|~~~)\s*(?P<language>[A-Za-z0-9_+.#-]*)")


def heading_anchor(title: str) -> str:
    normalized = re.sub(r"<[^>]+>", "", title).strip().lower()
    normalized = re.sub(r"[^\w\s-]", "", normalized, flags=re.UNICODE)
    normalized = re.sub(r"\s+", "-", normalized)
    normalized = re.sub(r"-+", "-", normalized).strip("-")
    return normalized


def analyze_markdown(text: str) -> dict:
    headings: list[dict] = []
    links: list[dict] = []
    code_blocks: list[dict] = []
    active_fence: dict | None = None

    for line_no, line in enumerate(text.splitlines(), start=1):
        fence_match = FENCE_PATTERN.match(line)
        if fence_match:
            marker = fence_match.group(1)
            language = fence_match.group("language").strip()
            if active_fence is None:
                active_fence = {
                    "language": language,
                    "line_start": line_no,
                    "marker": marker,
                }
            elif line.lstrip().startswith(active_fence["marker"]):
                code_blocks.append(
                    {
                        "language": active_fence["language"],
                        "line_start": active_fence["line_start"],
                        "line_end": line_no,
                    }
                )
                active_fence = None
            continue

        if active_fence is not None:
            continue

        heading_match = HEADING_PATTERN.match(line)
        if heading_match:
            title = heading_match.group("title").strip()
            headings.append(
                {
                    "level": len(heading_match.group("marks")),
                    "title": title,
                    "anchor": heading_anchor(title),
                    "line": line_no,
                }
            )

        for link_match in LINK_PATTERN.finditer(line):
            links.append(
                {
                    "text": link_match.group("text").strip(),
                    "target": link_match.group("target").strip(),
                    "line": line_no,
                }
            )

    if active_fence is not None:
        code_blocks.append(
            {
                "language": active_fence["language"],
                "line_start": active_fence["line_start"],
                "line_end": None,
            }
        )

    return {
        "imports": [],
        "classes": [],
        "functions": [],
        "tests": [],
        "decorators": [],
        "headings": headings,
        "links": links,
        "code_blocks": code_blocks,
        "parse_error": "",
    }
