#!/usr/bin/env bash
set -euo pipefail
export PYTHONDONTWRITEBYTECODE=1

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
plugin_root="$repo_root/plugins/trust-evidence-protocol"

local_source="${TEP_LOCAL_PLUGIN_SOURCE:-$HOME/plugins/trust-evidence-protocol}"
cache_base="${TEP_CODEX_PLUGIN_CACHE:-$HOME/.codex/plugins/cache/home-local-plugins/trust-evidence-protocol}"
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

echo "Installing trust-evidence-protocol $version"
echo "repo=$repo_root"
echo "local_source=$local_source"
echo "cache_target=$cache_target"

mkdir -p "$local_source" "$cache_target" "$archive_dir"
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

find "$cache_base" -mindepth 1 -maxdepth 1 -type d | while IFS= read -r dir; do
  name="$(basename "$dir")"
  case "$name" in
    "$version"|"$archive_name")
      ;;
    *)
      target="$archive_dir/$name"
      if [[ -e "$target" ]]; then
        rm -rf "$target"
      fi
      mv "$dir" "$target"
      ;;
  esac
done

python3 - "$local_source" "$cache_target" "$version" <<'PY'
import json
import sys
from pathlib import Path

local_source = Path(sys.argv[1])
cache_target = Path(sys.argv[2])
expected = sys.argv[3]
for root in (local_source, cache_target):
    manifest = root / ".codex-plugin" / "plugin.json"
    actual = json.loads(manifest.read_text(encoding="utf-8"))["version"]
    if actual != expected:
        raise SystemExit(f"{manifest}: expected {expected}, got {actual}")
    hook = root / "hooks" / "codex" / "hook_common.py"
    if "should_defer_unanchored_hydration" not in hook.read_text(encoding="utf-8"):
        raise SystemExit(f"{hook}: missing unanchored hydration guard")
    bytecode = [
        path
        for path in root.rglob("*")
        if path.name == "__pycache__" or path.suffix == ".pyc"
    ]
    if bytecode:
        sample = "\n".join(str(path) for path in bytecode[:10])
        raise SystemExit(f"{root}: bytecode/cache artifacts must not be installed:\n{sample}")
print(f"verified version={expected}")
PY

if [[ -d "$HOME/.tep_context" ]]; then
  "$cache_target/hooks/hydrate_context.sh" --allow-unanchored >/dev/null || true
fi

python3 - "$local_source" "$cache_target" <<'PY'
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

echo "active_cache_dirs:"
find "$cache_base" -mindepth 1 -maxdepth 1 -type d -print | sort
