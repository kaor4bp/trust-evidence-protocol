from __future__ import annotations

import re
import secrets
from datetime import datetime
from pathlib import Path


LEGACY_ID_SUFFIX_PATTERN = r"\d{4}"
RANDOM_ID_SUFFIX_PATTERN = r"[0-9a-f]{8}"
ID_SUFFIX_PATTERN = rf"(?:{LEGACY_ID_SUFFIX_PATTERN}|{RANDOM_ID_SUFFIX_PATTERN})"

ARTIFACT_ID_PATTERN = re.compile(rf"^ART-(\d{{8}})-({ID_SUFFIX_PATTERN})(?:__|$)")
ID_PATTERN = re.compile(
    rf"\b(?:WSP|PRJ|INP|SRC|CLM|PRM|RST|GLD|PRP|ACT|TASK|WCTX|PLN|DEBT|MODEL|FLOW|OPEN)-\d{{8}}-{ID_SUFFIX_PATTERN}\b"
)
WORKSPACE_ID_PATTERN = re.compile(rf"^WSP-\d{{8}}-{ID_SUFFIX_PATTERN}$")
PROJECT_ID_PATTERN = re.compile(rf"^PRJ-\d{{8}}-{ID_SUFFIX_PATTERN}$")
TASK_ID_PATTERN = re.compile(rf"^TASK-\d{{8}}-{ID_SUFFIX_PATTERN}$")
WORKING_CONTEXT_ID_PATTERN = re.compile(rf"^WCTX-\d{{8}}-{ID_SUFFIX_PATTERN}$")
CODE_INDEX_ID_PATTERN = re.compile(rf"^CIX-\d{{8}}-{RANDOM_ID_SUFFIX_PATTERN}$")


def now_timestamp() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def next_record_id(records: dict[str, dict], prefix: str) -> str:
    today = datetime.now().astimezone().strftime("%Y%m%d")
    for _ in range(32):
        candidate = f"{prefix}{today}-{secrets.token_hex(4)}"
        if candidate not in records:
            return candidate
    raise RuntimeError(f"could not allocate collision-free id for {prefix}{today}")


def next_artifact_id(root: Path) -> str:
    today = datetime.now().astimezone().strftime("%Y%m%d")
    artifacts_root = root / "artifacts"
    for _ in range(32):
        candidate = f"ART-{today}-{secrets.token_hex(4)}"
        if not artifacts_root.exists():
            return candidate
        if not any(path.name.startswith(candidate) for path in artifacts_root.iterdir() if path.is_file()):
            return candidate
    raise RuntimeError(f"could not allocate collision-free artifact id for ART-{today}")
