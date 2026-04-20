#!/usr/bin/env python3
"""Direct CocoIndex search over a TEP-scoped database.

This intentionally bypasses the `ccc search` project-marker discovery path.
It still uses cocoindex-code's query implementation and user embedding
settings, but reads project settings and DB files from the TEP-owned scoped
storage directory instead of requiring `$REPO/.cocoindex_code/settings.yml`.
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path


async def main() -> int:
    payload = json.loads(sys.stdin.read() or "{}")
    storage_dir = Path(str(payload["storage_dir"]))
    target_db = Path(str(payload["target_db"]))

    import cocoindex as coco
    from cocoindex.connectors import sqlite as coco_sqlite
    from cocoindex_code.query import query_codebase
    from cocoindex_code.settings import load_user_settings
    from cocoindex_code.shared import EMBEDDER, SQLITE_DB, create_embedder

    user_settings = load_user_settings()
    embedder = create_embedder(user_settings.embedding)
    db = coco_sqlite.connect(str(target_db), load_vec=True)
    try:
        context = coco.ContextProvider()
        context.provide(SQLITE_DB, db)
        context.provide(EMBEDDER, embedder)
        env = coco.Environment(
            coco.Settings.from_env(str(storage_dir / "cocoindex.db")),
            context_provider=context,
        )
        results = await query_codebase(
            query=str(payload["query"]),
            target_sqlite_db_path=target_db,
            env=env,
            limit=int(payload.get("limit") or 8),
            offset=0,
            languages=payload.get("languages") or None,
            paths=payload.get("paths") or None,
        )
    finally:
        db.close()

    print(
        json.dumps(
            [
                {
                    "file_path": item.file_path,
                    "language": item.language,
                    "content": item.content,
                    "start_line": item.start_line,
                    "end_line": item.end_line,
                    "score": item.score,
                }
                for item in results
            ],
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
