#!/usr/bin/env bash
# PreToolUse hook. Exit 2 blocks the edit and shows the message to Claude.
# Also appends one line to the lesson inbox (~/.kit/inbox) so /forge:kit-review can count recurrences.
inbox="${HOME}/.kit/inbox"
note() { mkdir -p "$(dirname "$inbox")" 2>/dev/null && printf '%s\tbranch_guard\t%s\t%s\n' "$(date +%F)" "$(basename "$PWD")" "$1" >> "$inbox" 2>/dev/null; }
branch=$(git branch --show-current 2>/dev/null)
case "$branch" in
  qa|release|master)
    note "edit blocked on $branch"
    echo "branch_guard: edits are blocked on '$branch'. Work on develop or feature/*." >&2
    exit 2 ;;
  "")
    note "edit blocked on detached HEAD"
    echo "branch_guard: detached HEAD or no git repo. Check out develop or feature/* first." >&2
    exit 2 ;;
esac
exit 0
