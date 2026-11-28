#!/usr/bin/env bash
# Git for Windows keeps grep/awk/cat/date in /usr/bin; a non-login shell may not have it on PATH.
[ -d /usr/bin ] && PATH="/usr/bin:/bin:$PATH" && export PATH
# Stop hook. Active only while a /forge:fix or /forge:hotfix run has its marker (.claude/fix-active).
# The budget is measured by kit_fix.py against the base commit recorded at start.
# KIT_HOOKS=minimal turns this hook off; standard and strict keep it on.
[ "${KIT_HOOKS:-standard}" = minimal ] && exit 0
[ -f .claude/fix-active ] || exit 0
input=$(cat)
# Do not loop: if this stop is already a retry from this hook, let it finish.
echo "$input" | grep -q '"stop_hook_active": *true' && exit 0
s="${CLAUDE_PLUGIN_ROOT:-}/scripts/kit_fix.py"; [ -f "$s" ] || s="${HOME}/.kit/repo/plugins/forge/scripts/kit_fix.py"
py=$(command -v python 2>/dev/null || command -v python3 2>/dev/null)
if [ ! -f "$s" ] || [ -z "$py" ]; then
  echo "diff_budget: kit_fix.py or Python not found; the fix run cannot be measured. Stop and report." >&2
  exit 2
fi
"$py" "$s" check --project "$(pwd)"
exit $?
