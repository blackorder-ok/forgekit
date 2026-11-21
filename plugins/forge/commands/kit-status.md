---
description: List the units in your global ~/.claude that the kit does not know about, and the kit units that changed locally. Read-only.
argument-hint: (none)
---

Run `python "${CLAUDE_PLUGIN_ROOT}/scripts/kit_status.py"` and show its output.

It compares `~/.claude/{agents,skills,commands}` with `kit.json` and `~/.kit/local-ignore`, and reports three lists: **orphans** (in `~/.claude`, not in the kit), **ignored** (personal, listed in `local-ignore`), and **drifted** (a kit unit whose installed copy differs from the repo). For each orphan it suggests one of: `/forge:kit-claim` to move it into the kit, or adding its name to `~/.kit/local-ignore`.

It changes nothing. Nothing in `~/.claude` ever reaches the kit repo without `/forge:kit-claim` and the user's yes.
