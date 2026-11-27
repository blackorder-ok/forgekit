#!/usr/bin/env bash
# Git for Windows keeps date/basename/mkdir in /usr/bin; a non-login shell may not have it on PATH.
[ -d /usr/bin ] && PATH="/usr/bin:/bin:$PATH" && export PATH
# PreToolUse hook. Exit 2 blocks the edit and shows the message to Claude.
# Also logs the gate decision via kit_log.py (event store) so /forge:kit-review can count recurrences.
# note <detail> <reason_code> <branch>; logging never fails the hook.
note() {
  local s="${CLAUDE_PLUGIN_ROOT:-}/scripts/kit_log.py" py
  [ -f "$s" ] || s="${HOME}/.kit/repo/plugins/forge/scripts/kit_log.py"
  [ -f "$s" ] || return 0
  py=$(command -v python 2>/dev/null || command -v python3 2>/dev/null) || return 0
  "$py" "$s" event --type gate --agent branch_guard --reason-code "$2" --severity block --branch "$3" --detail "$1" >/dev/null 2>&1
  return 0
}
branch=$(git branch --show-current 2>/dev/null)
case "$branch" in
  qa|release|master)
    note "edit blocked on $branch" protected_branch "$branch"
    echo "branch_guard: edits are blocked on '$branch'. Work on develop or feature/*." >&2
    exit 2 ;;
  "")
    note "edit blocked on detached HEAD" detached_head ""
    echo "branch_guard: detached HEAD or no git repo. Check out develop or feature/* first." >&2
    exit 2 ;;
esac
exit 0
