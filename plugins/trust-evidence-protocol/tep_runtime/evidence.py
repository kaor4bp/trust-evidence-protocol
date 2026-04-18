"""Evidence-chain quote matching helpers."""

from __future__ import annotations


def normalize_quote(value: str) -> str:
    return " ".join(str(value).lower().split())


def join_quote_items(items) -> str:
    parts = []
    for item in items or []:
        if isinstance(item, dict):
            parts.append(str(item.get("text", "")))
            parts.extend(str(ref) for ref in item.get("support_refs", []) if ref)
        elif item:
            parts.append(str(item))
    return " ".join(parts)


def quote_matches_record(records: dict[str, dict], record: dict, quote: str) -> bool:
    needle = normalize_quote(quote)
    if not needle:
        return False
    haystacks = [
        record.get("statement", ""),
        record.get("summary", ""),
        record.get("question", ""),
        record.get("rule", ""),
        record.get("rationale", ""),
        record.get("subject", ""),
        record.get("position", ""),
        record.get("title", ""),
        record.get("note", ""),
        record.get("quote", ""),
        join_quote_items(record.get("artifact_refs", [])),
        join_quote_items(record.get("examples", [])),
        join_quote_items(record.get("assumptions", [])),
        join_quote_items(record.get("concerns", [])),
        join_quote_items(record.get("risks", [])),
        join_quote_items(record.get("stop_conditions", [])),
        join_quote_items(record.get("focus_paths", [])),
        join_quote_items(record.get("topic_terms", [])),
        join_quote_items(record.get("pinned_refs", [])),
    ]
    for option in record.get("proposals", []):
        if isinstance(option, dict):
            haystacks.extend(
                [
                    option.get("title", ""),
                    option.get("why", ""),
                    " ".join(option.get("tradeoffs", [])),
                ]
            )
    for source_ref in record.get("source_refs", []):
        source = records.get(source_ref, {})
        haystacks.extend(
            [
                source.get("quote", ""),
                source.get("note", ""),
                " ".join(source.get("artifact_refs", [])),
            ]
        )
    return any(needle in normalize_quote(text) for text in haystacks if text)
