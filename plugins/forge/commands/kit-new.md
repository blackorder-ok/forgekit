---
description: Create a new kit unit (skill, agent or command) from a template directly inside the kit repo, register it in kit.json and run the budget check.
argument-hint: <skill|agent|command> <name>
---

Request: $ARGUMENTS

1. Run `python "${CLAUDE_PLUGIN_ROOT}/scripts/kit_new.py" $ARGUMENTS`. It resolves the kit repo from `~/.kit/repo`, creates the file from a template in `plugins/forge/`, adds the entry to `kit.json`, and prints the path.
2. Open the new file and fill it in with the user. Keep to the budgets: a skill digest 2.5k bytes or less, an agent 3.5k bytes or less, a command 3k bytes or less. Put detail in `references/`.
3. Run `python tools/check_kit.py --tokens` in the kit repo. Fix failures.
4. Do not commit or tag. Tell the user the file and that a commit and a new tag publish it.

A unit made here is born in the repo, so there is nothing to claim later. Never create the unit under `~/.claude/` for a kit unit.

## On failure
- `~/.kit/repo` missing: tell the user to create it with the path of their kit clone, then stop.
- Name taken or invalid (lowercase letters, digits, hyphens): stop and say so.
