#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "$SCRIPT_DIR/.." && pwd)"
FIXTURE_DIR="$SCRIPT_DIR/fixtures/smoke-workspace"
WORKDIR="$(mktemp -d "${TMPDIR:-/tmp}/codex-skill-smoke.XXXXXX")"
KEEP_WORKDIR="${CODEX_TEST_KEEP_WORKDIR:-0}"

cleanup() {
  if [[ "$KEEP_WORKDIR" != "1" ]]; then
    rm -rf "$WORKDIR"
  fi
}
trap cleanup EXIT

cp -R "$FIXTURE_DIR"/. "$WORKDIR"/

cat <<EOF
Smoke workspace: $WORKDIR
Fixture copied from: $FIXTURE_DIR
EOF

PROMPT=$'Use the karpathy-guidelines skill.\nMake the smallest possible change.\nAppend a new bullet `- SMOKE_TEST_OK` to README.md.\nDo not modify any other files.\nIn the final response, mention only the file you changed.'

"$SCRIPT_DIR/run_codex_exec.sh" "$WORKDIR" "$PROMPT"

if command -v rg >/dev/null 2>&1; then
  CHECK_CMD=(rg -n --fixed-strings -- "SMOKE_TEST_OK" "$WORKDIR/README.md")
else
  CHECK_CMD=(grep -n -F -- "SMOKE_TEST_OK" "$WORKDIR/README.md")
fi

if "${CHECK_CMD[@]}" >/dev/null; then
  echo
  echo "Smoke check passed."
  echo "Workspace: $WORKDIR"
  if [[ "$KEEP_WORKDIR" != "1" ]]; then
    echo "Workspace will be removed on exit. Set CODEX_TEST_KEEP_WORKDIR=1 to keep it."
  fi
else
  echo "Smoke check failed: README.md does not contain SMOKE_TEST_OK" >&2
  echo "Workspace kept at: $WORKDIR" >&2
  exit 1
fi
