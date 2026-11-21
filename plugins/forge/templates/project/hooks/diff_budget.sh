#!/usr/bin/env bash
# Stop hook. Active only while /forge:fix or /forge:hotfix has created .claude/fix-active.
# KIT_HOOKS=minimal turns this hook off; standard and strict keep it on.
[ "${KIT_HOOKS:-standard}" = minimal ] && exit 0
[ -f .claude/fix-active ] || exit 0
input=$(cat)
# Do not loop: if this stop is already a retry from this hook, let it finish.
echo "$input" | grep -q '"stop_hook_active": *true' && exit 0
read -r files lines < <(git diff --numstat HEAD | awk 'NF==3 && $1 ~ /^[0-9]+$/ {f++; l+=$1+$2} END {print f+0, l+0}')
budget_files=3
budget_lines=20
if [ "$files" -gt "$budget_files" ] || [ "$lines" -gt "$budget_lines" ]; then
  mkdir -p "${HOME}/.kit" 2>/dev/null && printf '%s\tdiff_budget\t%s\tfix over budget %s files %s lines\n' "$(date +%F)" "$(basename "$PWD")" "$files" "$lines" >> "${HOME}/.kit/inbox" 2>/dev/null
  echo "diff_budget: $files files and $lines changed lines; the budget is $budget_files files and $budget_lines lines. Stop, report, and recommend /forge:design." >&2
  exit 2
fi
exit 0
