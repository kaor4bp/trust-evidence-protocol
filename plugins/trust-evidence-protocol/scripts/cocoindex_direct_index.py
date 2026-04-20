#!/usr/bin/env python3
"""Run CocoIndex indexing without the daemon or repo-local DB storage.

Input is a JSON payload on stdin:
{
  "project_root": "/tmp/shadow-project",
  "storage_dir": "/path/to/scoped/.cocoindex_code"
}

This helper intentionally runs inside the CocoIndex Python environment selected
from the `ccc` entrypoint. It keeps CocoIndex a TEP implementation detail while
allowing TEP to own scoped storage outside the repository checkout.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path


async def _run(project_root: Path) -> None:
    from cocoindex_code.project import Project
    from cocoindex_code.settings import load_user_settings
    from cocoindex_code.shared import create_embedder

    user_settings = load_user_settings()
    for key, value in user_settings.envs.items():
        os.environ.setdefault(str(key), str(value))
    embedder = create_embedder(user_settings.embedding)
    project = await Project.create(project_root, embedder)
    try:
        await project.run_index()
    finally:
        project.close()


def main() -> int:
    payload = json.loads(sys.stdin.read() or "{}")
    project_root = Path(str(payload.get("project_root") or "")).expanduser()
    storage_dir = Path(str(payload.get("storage_dir") or "")).expanduser()
    if not project_root.is_dir():
        print(f"missing CocoIndex shadow project root: {project_root}", file=sys.stderr)
        return 2
    if not (project_root / ".cocoindex_code" / "settings.yml").is_file():
        print(f"missing CocoIndex shadow project settings: {project_root}", file=sys.stderr)
        return 2
    storage_dir.mkdir(parents=True, exist_ok=True)
    asyncio.run(_run(project_root))
    print(json.dumps({"success": True, "storage_dir": str(storage_dir)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
