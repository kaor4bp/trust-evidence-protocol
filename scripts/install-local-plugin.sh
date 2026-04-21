#!/usr/bin/env bash
set -euo pipefail
export PYTHONDONTWRITEBYTECODE=1

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
plugin_root="$repo_root/plugins/trust-evidence-protocol"

local_source="${TEP_LOCAL_PLUGIN_SOURCE:-$HOME/plugins/trust-evidence-protocol}"
cache_base="${TEP_CODEX_PLUGIN_CACHE:-$HOME/.codex/plugins/cache/home-local-plugins/trust-evidence-protocol}"
claude_cache_base="${TEP_CLAUDE_PLUGIN_CACHE:-$HOME/.claude/plugins/cache/home-local-plugins/trust-evidence-protocol}"
archive_name="${TEP_CACHE_ARCHIVE_NAME:-_archived-pre-active}"

version="$(
  python3 - "$plugin_root/.codex-plugin/plugin.json" <<'PY'
import json
import sys
from pathlib import Path

print(json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))["version"])
PY
)"

cache_target="$cache_base/$version"
archive_dir="$cache_base/$archive_name"
claude_cache_target="$claude_cache_base/$version"
claude_archive_dir="$claude_cache_base/$archive_name"

echo "Installing trust-evidence-protocol $version"
echo "repo=$repo_root"
echo "local_source=$local_source"
echo "cache_target=$cache_target"
echo "claude_cache_target=$claude_cache_target"

mkdir -p "$local_source" "$cache_target" "$archive_dir" "$claude_cache_target" "$claude_archive_dir"
rsync_args=(
  -a
  --delete
  --delete-excluded
  --exclude '__pycache__/'
  --exclude '*.pyc'
  --exclude '.pytest_cache/'
  --exclude '.mypy_cache/'
  --exclude '.ruff_cache/'
)
rsync "${rsync_args[@]}" "$plugin_root/" "$local_source/"
rsync "${rsync_args[@]}" "$plugin_root/" "$cache_target/"
rsync "${rsync_args[@]}" "$plugin_root/" "$claude_cache_target/"

_archive_old_versions() {
  local base="$1" version="$2" archive="$3"
  find "$base" -mindepth 1 -maxdepth 1 -type d | while IFS= read -r dir; do
    name="$(basename "$dir")"
    case "$name" in
      "$version"|"$(basename "$archive")")
        ;;
      *)
        target="$archive/$name"
        if [[ -e "$target" ]]; then
          rm -rf "$target"
        fi
        mv "$dir" "$target"
        ;;
    esac
  done
}
_archive_old_versions "$cache_base" "$version" "$archive_dir"
_archive_old_versions "$claude_cache_base" "$version" "$claude_archive_dir"

python3 - "$local_source" "$cache_target" "$claude_cache_target" "$version" <<'PY'
import json
import sys
from pathlib import Path

local_source = Path(sys.argv[1])
cache_target = Path(sys.argv[2])
claude_cache_target = Path(sys.argv[3])
expected = sys.argv[4]
for root in (local_source, cache_target, claude_cache_target):
    codex_manifest = root / ".codex-plugin" / "plugin.json"
    actual = json.loads(codex_manifest.read_text(encoding="utf-8"))["version"]
    if actual != expected:
        raise SystemExit(f"{codex_manifest}: expected {expected}, got {actual}")
    claude_manifest = root / ".claude-plugin" / "plugin.json"
    if not claude_manifest.exists():
        raise SystemExit(f"{claude_manifest}: missing Claude plugin manifest")
    claude_payload = json.loads(claude_manifest.read_text(encoding="utf-8"))
    if claude_payload.get("version") != expected:
        raise SystemExit(f"{claude_manifest}: expected {expected}, got {claude_payload.get('version')}")
    if claude_payload.get("hooks") != "./hooks/claude/hooks.json":
        raise SystemExit(f"{claude_manifest}: hooks must point to ./hooks/claude/hooks.json")
    codex_hook = root / "hooks" / "codex" / "hook_common.py"
    if "should_defer_unanchored_hydration" not in codex_hook.read_text(encoding="utf-8"):
        raise SystemExit(f"{codex_hook}: missing unanchored hydration guard")
    claude_hook = root / "hooks" / "claude" / "hook_common.py"
    if "should_defer_unanchored_hydration" not in claude_hook.read_text(encoding="utf-8"):
        raise SystemExit(f"{claude_hook}: missing unanchored hydration guard")
    claude_hooks_json = root / "hooks" / "claude" / "hooks.json"
    if not claude_hooks_json.exists():
        raise SystemExit(f"{claude_hooks_json}: missing Claude hooks registration")
    bytecode = [
        path
        for path in root.rglob("*")
        if path.name == "__pycache__" or path.suffix == ".pyc"
    ]
    if bytecode:
        sample = "\n".join(str(path) for path in bytecode[:10])
        raise SystemExit(f"{root}: bytecode/cache artifacts must not be installed:\n{sample}")
print(f"verified version={expected} (codex + claude)")
PY

if [[ -d "$HOME/.tep_context" ]]; then
  "$cache_target/hooks/hydrate_context.sh" --allow-unanchored >/dev/null || true
fi

python3 - "$local_source" "$cache_target" "$claude_cache_target" <<'PY'
import sys
from pathlib import Path

for root_arg in sys.argv[1:]:
    root = Path(root_arg)
    bytecode = [
        path
        for path in root.rglob("*")
        if path.name == "__pycache__" or path.suffix == ".pyc"
    ]
    if bytecode:
        sample = "\n".join(str(path) for path in bytecode[:10])
        raise SystemExit(f"{root}: post-hydration bytecode/cache artifacts must not remain:\n{sample}")
print("verified bytecode-free install")
PY

codex_config="${TEP_CODEX_CONFIG:-$HOME/.codex/config.toml}"
python3 - "$codex_config" "$cache_target" <<'PY'
import re
import sys
from pathlib import Path

config_path = Path(sys.argv[1])
cache_target = Path(sys.argv[2])
if not config_path.exists():
    raise SystemExit(0)

text = config_path.read_text(encoding="utf-8")
section_header = "[mcp_servers.trust_evidence_protocol]"
section_body = "\n".join(
    [
        section_header,
        f'args = ["{cache_target / "mcp" / "tep_server.py"}"]',
        'command = "python3"',
        f'cwd = "{cache_target}"',
        "enabled = true",
        "",
        "",
    ]
)
pattern = re.compile(
    r"(?ms)^\[mcp_servers\.trust_evidence_protocol\]\n.*?(?=^\[|\Z)"
)
if pattern.search(text):
    updated = pattern.sub(section_body, text)
else:
    separator = "" if text.endswith("\n") else "\n"
    updated = f"{text}{separator}\n{section_body}"
if updated != text:
    config_path.write_text(updated, encoding="utf-8")
    print(f"updated Codex TEP MCP server: {cache_target}")
else:
    print(f"verified Codex TEP MCP server: {cache_target}")
PY

echo "active_cache_dirs (codex):"
find "$cache_base" -mindepth 1 -maxdepth 1 -type d -print | sort
echo "active_cache_dirs (claude):"
find "$claude_cache_base" -mindepth 1 -maxdepth 1 -type d -print | sort
