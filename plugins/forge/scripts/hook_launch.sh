#!/usr/bin/env bash
# Layer 1 of the fail-closed hook launcher. Usage: hook_launch.sh <hook path> | --selfcheck
# Finds a Python 3.9+ and hands off to hook_main.py, which maps every failure to exit 2 with a fix.
[ -d /usr/bin ] && PATH="/usr/bin:/bin:$PATH" && export PATH
ROOT="${CLAUDE_PLUGIN_ROOT:-$HOME/.kit/repo/plugins/forge}"
main="$ROOT/scripts/hook_main.py"
name=$(basename "${1:-hook}"); name=${name%.*}
[ -f "$main" ] || { echo "hook $name failed (missing script): forgekit not found at $ROOT. Set CLAUDE_PLUGIN_ROOT or clone the kit to ~/.kit/repo." >&2; exit 2; }
PY=""
for c in "${KIT_PYTHON:-}" python3 python py; do
  [ -n "$c" ] || continue
  if command -v "$c" >/dev/null 2>&1 && "$c" -c 'import sys; sys.exit(sys.version_info < (3, 9))' >/dev/null 2>&1; then PY="$c"; break; fi
done
[ -n "$PY" ] || { echo "hook $name failed (no Python): no Python 3.9+ found. Install Python 3.11 or set KIT_PYTHON." >&2; exit 2; }
if [ "${1:-}" = "--selfcheck" ]; then exec "$PY" "$main" selfcheck; fi
exec "$PY" "$main" run "$1"
