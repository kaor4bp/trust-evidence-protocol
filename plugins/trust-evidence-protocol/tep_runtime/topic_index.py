"""Lexical topic-index helpers for generated navigation data."""

from __future__ import annotations

import json
import math
import re
from collections import Counter
from pathlib import Path

from .claims import claim_is_archived
from .ids import now_timestamp
from .io import write_json_file, write_text_file
from .search import public_record_summary, record_search_text, record_summary


TASK_STOP_WORDS = {
    "and",
    "the",
    "for",
    "with",
    "from",
    "that",
    "this",
    "как",
    "что",
    "для",
    "или",
    "про",
    "при",
    "это",
    "если",
}

TOPIC_STOP_WORDS = {
    "and",
    "the",
    "for",
    "with",
    "from",
    "that",
    "this",
    "into",
    "only",
    "must",
    "should",
    "when",
    "where",
    "which",
    "what",
    "как",
    "что",
    "для",
    "или",
    "при",
    "это",
    "если",
    "чтобы",
    "надо",
    "нужно",
    "можно",
    "когда",
    "где",
    "такой",
    "такая",
}


def task_terms(task: str) -> set[str]:
    return {
        item.lower()
        for item in re.findall(r"[A-Za-zА-Яа-я0-9_.:-]{3,}", task)
        if item.lower() not in TASK_STOP_WORDS
    }


def topic_tokenize(text: str) -> list[str]:
    tokens = []
    for raw in re.findall(r"[A-Za-zА-Яа-я0-9_.:-]{3,}", text.lower()):
        token = raw.strip("._:-")
        if len(token) < 3 or token in TOPIC_STOP_WORDS:
            continue
        if token.isdigit():
            continue
        tokens.append(token)
    return tokens


def topic_index_root(root: Path) -> Path:
    return root / "topic_index"


def topic_index_paths(root: Path) -> dict[str, Path]:
    base = topic_index_root(root)
    return {
        "records": base / "records.json",
        "topics": base / "topics.json",
        "by_record": base / "by_record.json",
        "by_topic": base / "by_topic.json",
        "summary": base / "summary.md",
        "conflict_candidates": base / "conflict_candidates.md",
    }


def topic_record_text(data: dict) -> str:
    parts = [record_search_text(data), record_summary(data)]
    for key in ("focus_paths", "topic_terms", "topic_seed_refs", "pinned_refs"):
        parts.extend(str(item) for item in data.get(key, []) if item)
    for assumption in data.get("assumptions", []):
        if isinstance(assumption, dict):
            parts.append(str(assumption.get("text", "")))
            parts.extend(str(ref) for ref in assumption.get("support_refs", []) if ref)
    return " ".join(parts)


def record_topic_status(data: dict) -> str:
    if data.get("record_type") == "source":
        return str(data.get("critique_status", "")).strip()
    return str(data.get("status", "")).strip()


def topic_document_weights(records: dict[str, dict], terms_per_record: int) -> tuple[dict[str, dict], Counter]:
    docs: dict[str, Counter] = {}
    document_frequency: Counter = Counter()
    for record_id, data in records.items():
        if str(data.get("record_type", "")).strip() == "":
            continue
        tokens = topic_tokenize(topic_record_text(data))
        if not tokens:
            continue
        counts = Counter(tokens)
        docs[record_id] = counts
        document_frequency.update(counts.keys())

    document_count = max(1, len(docs))
    indexed: dict[str, dict] = {}
    aggregate: Counter = Counter()
    for record_id, counts in docs.items():
        total = sum(counts.values()) or 1
        weights = {}
        for term, count in counts.items():
            idf = math.log((1 + document_count) / (1 + document_frequency[term])) + 1.0
            weights[term] = round((count / total) * idf, 6)
        top_terms = sorted(weights.items(), key=lambda item: (-item[1], item[0]))[: max(1, terms_per_record)]
        aggregate.update({term: score for term, score in top_terms})
        data = records[record_id]
        indexed[record_id] = {
            "id": record_id,
            "record_type": data.get("record_type", ""),
            "status": record_topic_status(data),
            "scope": str(data.get("scope", "")).strip(),
            "summary": record_summary(data),
            "terms": [{"term": term, "score": score} for term, score in top_terms],
            "weights": {term: score for term, score in top_terms},
            "updated_at": str(
                data.get("updated_at")
                or data.get("recorded_at")
                or data.get("captured_at")
                or data.get("created_at")
                or ""
            ),
        }
    return indexed, aggregate


def build_lexical_topic_index(records: dict[str, dict], terms_per_record: int, topic_limit: int) -> dict:
    indexed_records, aggregate = topic_document_weights(records, terms_per_record=terms_per_record)
    topic_terms = [term for term, _ in sorted(aggregate.items(), key=lambda item: (-item[1], item[0]))[: max(1, topic_limit)]]
    topic_id_by_term = {term: f"topic-{index:04d}" for index, term in enumerate(topic_terms, start=1)}

    by_record: dict[str, list[dict]] = {}
    by_topic: dict[str, list[dict]] = {topic_id_by_term[term]: [] for term in topic_terms}
    for record_id, item in indexed_records.items():
        memberships = []
        for term_info in item["terms"]:
            term = term_info["term"]
            topic_id = topic_id_by_term.get(term)
            if not topic_id:
                continue
            membership = {"topic_id": topic_id, "term": term, "score": term_info["score"]}
            memberships.append(membership)
            by_topic[topic_id].append(
                {
                    "id": record_id,
                    "record_type": item["record_type"],
                    "status": item["status"],
                    "score": term_info["score"],
                    "summary": item["summary"],
                }
            )
        by_record[record_id] = memberships
        item["topics"] = memberships

    topics = {}
    for term in topic_terms:
        topic_id = topic_id_by_term[term]
        ranked_records = sorted(by_topic[topic_id], key=lambda item: (-item["score"], item["id"]))
        by_topic[topic_id] = ranked_records
        topics[topic_id] = {
            "id": topic_id,
            "term": term,
            "record_count": len(ranked_records),
            "top_records": ranked_records[:12],
            "note": "Generated lexical navigation topic. Not proof.",
        }

    return {
        "method": "lexical",
        "generated_at": now_timestamp(),
        "record_count": len(indexed_records),
        "topic_count": len(topics),
        "records": indexed_records,
        "topics": topics,
        "by_record": by_record,
        "by_topic": by_topic,
    }


def claim_topic_terms(topic_records: dict[str, dict], claim_ref: str) -> set[str]:
    item = topic_records.get(claim_ref, {})
    return {str(term.get("term", "")).strip() for term in item.get("terms", []) if str(term.get("term", "")).strip()}


def topic_conflict_candidates(records: dict[str, dict], topic_records: dict[str, dict], limit: int) -> list[dict]:
    claims = [
        data
        for data in records.values()
        if data.get("record_type") == "claim"
        and str(data.get("status", "")).strip() in {"supported", "corroborated", "contested", "tentative"}
        and not claim_is_archived(data)
    ]
    candidates = []
    for left_index, left in enumerate(claims):
        left_terms = claim_topic_terms(topic_records, str(left.get("id", "")))
        if not left_terms:
            continue
        left_comparison = left.get("comparison", {}) if isinstance(left.get("comparison"), dict) else {}
        for right in claims[left_index + 1 :]:
            right_terms = claim_topic_terms(topic_records, str(right.get("id", "")))
            shared_terms = sorted(left_terms & right_terms)
            if len(shared_terms) < 2:
                continue
            right_comparison = right.get("comparison", {}) if isinstance(right.get("comparison"), dict) else {}
            same_comparison_key = bool(
                left_comparison.get("key")
                and right_comparison.get("key")
                and left_comparison.get("key") == right_comparison.get("key")
            )
            missing_comparison = not left_comparison.get("key") or not right_comparison.get("key")
            different_comparison_key = bool(left_comparison.get("key") and right_comparison.get("key") and not same_comparison_key)
            score = len(shared_terms)
            if missing_comparison:
                score += 1
            if same_comparison_key:
                score += 2
            candidates.append(
                {
                    "score": score,
                    "left": public_record_summary(left),
                    "right": public_record_summary(right),
                    "shared_terms": shared_terms,
                    "signals": {
                        "same_comparison_key": same_comparison_key,
                        "missing_comparison": missing_comparison,
                        "different_comparison_key": different_comparison_key,
                        "candidate_only": True,
                    },
                    "note": "Topic overlap is only a review prefilter; it does not prove contradiction.",
                }
            )
    return sorted(candidates, key=lambda item: (-item["score"], item["left"]["id"], item["right"]["id"]))[: max(1, limit)]


def write_topic_index_reports(root: Path, payload: dict, candidates: list[dict]) -> None:
    paths = topic_index_paths(root)
    write_json_file(paths["records"], payload["records"])
    write_json_file(paths["topics"], payload["topics"])
    write_json_file(paths["by_record"], payload["by_record"])
    write_json_file(paths["by_topic"], payload["by_topic"])

    summary_lines = [
        "# Generated Topic Index",
        "",
        "Generated lexical topic index. This is navigation/prefilter data, not proof.",
        "",
        f"- method: `{payload['method']}`",
        f"- generated_at: `{payload['generated_at']}`",
        f"- records: `{payload['record_count']}`",
        f"- topics: `{payload['topic_count']}`",
        "",
        "## Top Topics",
    ]
    for topic in list(payload["topics"].values())[:20]:
        summary_lines.append(f"- `{topic['id']}` term=`{topic['term']}` records={topic['record_count']}")
    write_text_file(paths["summary"], "\n".join(summary_lines).rstrip() + "\n")

    candidate_lines = [
        "# Topic Conflict Candidates",
        "",
        "Generated lexical prefilter. These are candidates for human/agent review, not contradictions.",
        "",
    ]
    if not candidates:
        candidate_lines.append("- no candidates")
    for item in candidates:
        candidate_lines.append(
            f"- score={item['score']} `{item['left']['id']}` <-> `{item['right']['id']}` "
            f"shared_terms={', '.join(item['shared_terms'])}"
        )
        candidate_lines.append(f"  - left: {item['left']['summary']}")
        candidate_lines.append(f"  - right: {item['right']['summary']}")
    write_text_file(paths["conflict_candidates"], "\n".join(candidate_lines).rstrip() + "\n")


def load_topic_records(root: Path) -> dict[str, dict]:
    path = topic_index_paths(root)["records"]
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def infer_topic_terms_from_refs(root: Path, records: dict[str, dict], refs: list[str], limit: int = 12) -> list[str]:
    if not refs:
        return []
    topic_records = load_topic_records(root)
    if not topic_records:
        topic_records, _ = topic_document_weights(records, terms_per_record=limit)
    terms: Counter = Counter()
    for ref in refs:
        item = topic_records.get(ref, {})
        for term in item.get("terms", []):
            if isinstance(term, dict) and term.get("term"):
                terms[str(term["term"])] += float(term.get("score", 1.0))
    return [term for term, _ in sorted(terms.items(), key=lambda item: (-item[1], item[0]))[:limit]]


def topic_search_matches(item: dict, query_terms: set[str]) -> tuple[float, list[str]]:
    weights = item.get("weights", {}) if isinstance(item.get("weights"), dict) else {}
    matched = sorted(term for term in query_terms if term in weights)
    score = float(sum(float(weights.get(term, 0.0)) for term in matched))
    haystack = f"{item.get('id', '')} {item.get('record_type', '')} {item.get('scope', '')} {item.get('summary', '')}".lower()
    for term in query_terms:
        if term in matched:
            continue
        if term in haystack:
            matched.append(term)
            score += 0.01
    return score, sorted(matched)
