#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "$SCRIPT_DIR/.." && pwd)"

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 /abs/path/to/workspace [prompt...]" >&2
  echo "       printf '...' | $0 /abs/path/to/workspace" >&2
  exit 1
fi

WORKSPACE_DIR="$(cd -- "$1" && pwd)"
shift

AUTH_HOME="${CODEX_TEST_HOME:-$REPO_ROOT/.codex-test-home}"
ENV_FILE="${CODEX_TEST_ENV:-$REPO_ROOT/.env}"
IMAGE_TAG="${CODEX_TEST_IMAGE:-tim-codex-skill-runner}"
PLUGIN_SKILL_DIR="$REPO_ROOT/plugins/trust-evidence-protocol/skills/trust-evidence-protocol"

if [[ -f "$ENV_FILE" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "$ENV_FILE"
  set +a
fi

if [[ -z "${OPENAI_API_KEY:-}" ]]; then
  echo "Missing OPENAI_API_KEY. Add it to $ENV_FILE." >&2
  exit 1
fi

if [[ ! -f "$PLUGIN_SKILL_DIR/SKILL.md" ]]; then
  echo "Missing plugin skill: $PLUGIN_SKILL_DIR" >&2
  exit 1
fi

if ! docker image inspect "$IMAGE_TAG" >/dev/null 2>&1; then
  docker build -t "$IMAGE_TAG" -f "$SCRIPT_DIR/Dockerfile" "$SCRIPT_DIR"
fi

mkdir -p "$AUTH_HOME/skills"
rm -rf "$AUTH_HOME/skills"
mkdir -p "$AUTH_HOME/skills"
cp -R "$PLUGIN_SKILL_DIR" "$AUTH_HOME/skills/"

printf '%s' "$OPENAI_API_KEY" \
  | docker run --rm -i \
      -e CODEX_HOME=/codex-home \
      -v "$AUTH_HOME:/codex-home" \
      "$IMAGE_TAG" \
      codex login -c 'cli_auth_credentials_store="file"' --with-api-key >/dev/null

TTY_ARGS=(-i)
if [[ -t 0 && -t 1 ]]; then
  TTY_ARGS=(-it)
fi

DOCKER_ARGS=(
  docker
  run
  --rm
  "${TTY_ARGS[@]}"
  -e CODEX_HOME=/codex-home
  -v "$AUTH_HOME:/codex-home"
  -v "$WORKSPACE_DIR:/workspace"
  "$IMAGE_TAG"
  codex
  exec
  --cd /workspace
  --sandbox workspace-write
  --skip-git-repo-check
)

if [[ $# -gt 0 ]]; then
  exec "${DOCKER_ARGS[@]}" "$*"
fi

if [[ -t 0 ]]; then
  echo "Prompt is required either as arguments or via stdin." >&2
  exit 1
fi

exec "${DOCKER_ARGS[@]}" -
