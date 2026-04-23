#!/usr/bin/env python3
"""Validate strict .tep_context records for the trust-evidence-protocol plugin."""

from __future__ import annotations

import argparse
from pathlib import Path

from context_lib import collect_validation_errors, write_validation_report

TEP_ICON = "🛡️"

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate a strict .tep_context layout.")
    parser.add_argument(
        "target",
        nargs="?",
        default=".tep_context",
        help="Target .tep_context directory (default: ./.tep_context)",
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
    print(f"{TEP_ICON} Validated strict TEP context: {root}")


if __name__ == "__main__":
    main()
