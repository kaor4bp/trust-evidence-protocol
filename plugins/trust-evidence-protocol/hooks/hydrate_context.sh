#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PLUGIN_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

if [[ $# -gt 0 && "$1" != --* ]]; then
  context_path="$1"
  shift
  exec python3 "$PLUGIN_ROOT/scripts/runtime_gate.py" --context "$context_path" hydrate-context "$@"
fi

exec python3 "$PLUGIN_ROOT/scripts/runtime_gate.py" hydrate-context "$@"
