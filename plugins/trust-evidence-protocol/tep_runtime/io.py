from __future__ import annotations

import json
import os
import tempfile
import time
from contextlib import contextmanager
from pathlib import Path

from .paths import runtime_dir


def parse_json_file(path: Path) -> dict:
    with path.open(encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError("record must be a JSON object")
    return data


def write_json_file(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
        delete=False,
    ) as handle:
        tmp_path = Path(handle.name)
        json.dump(payload, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
    os.replace(tmp_path, path)


def write_text_file(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
        delete=False,
    ) as handle:
        tmp_path = Path(handle.name)
        handle.write(content)
    os.replace(tmp_path, path)


@contextmanager
def context_write_lock(root: Path, timeout_seconds: float = 30.0):
    lock_dir = runtime_dir(root)
    lock_dir.mkdir(parents=True, exist_ok=True)
    lock_path = lock_dir / "write.lock"
    deadline = time.monotonic() + timeout_seconds
    with lock_path.open("a+", encoding="utf-8") as handle:
        while True:
            try:
                import fcntl

                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if time.monotonic() >= deadline:
                    raise TimeoutError(f"timed out waiting for context write lock: {lock_path}")
                time.sleep(0.05)
        try:
            yield
        finally:
            import fcntl

            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)

