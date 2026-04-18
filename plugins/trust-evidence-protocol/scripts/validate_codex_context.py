#!/usr/bin/env python3
"""Validate strict .codex_context records for the trust-evidence-protocol plugin."""

from __future__ import annotations

import argparse
from pathlib import Path

from context_lib import collect_validation_errors, write_validation_report

TEP_ICON = "🛡️"

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate a strict .codex_context layout.")
    parser.add_argument(
        "target",
        nargs="?",
        default=".codex_context",
        help="Target .codex_context directory (default: ./.codex_context)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    root = Path(args.target).expanduser().resolve()
    _, errors = collect_validation_errors(root)
    write_validation_report(root, errors)
    if errors:
        for error in errors:
            print(f"{error.path}: {error.message}")
        raise SystemExit(1)
    print(f"{TEP_ICON} Validated strict Codex context: {root}")


if __name__ == "__main__":
    main()
