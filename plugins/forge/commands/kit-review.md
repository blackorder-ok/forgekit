---
description: Review the lesson inbox, group repeats, and propose global lessons as a branch in the kit repo for your approval. Project lessons stay in the project.
argument-hint: (none)
---

1. Run `python "${CLAUDE_PLUGIN_ROOT}/scripts/kit_mem.py" inbox`. It prints the grouped lesson lines from `~/.kit/inbox` (source, count, projects, sample).
2. For each group with 3 or more occurrences across at least 2 projects, classify it: **global** (belongs to a kit skill, agent, command or hook) or **project** (specific to one project).
3. For a **project** lesson: offer to add it with `/forge:mem add` in that project. Do nothing else.
4. For a **global** lesson: draft the smallest edit to one kit file (name it) and show the diff. Only after a yes, create the branch `learn/<date>` in the kit repo, apply the edit there, run `python tools/check_kit.py --tokens`, and stop. Never edit the plugin cache or `~/.claude`.
5. After approval, mark the group handled: `python "${CLAUDE_PLUGIN_ROOT}/scripts/kit_mem.py" inbox --clear <group>`.

Only units registered in `kit.json` are reviewed. Never merge, tag or push; the user does.
Keep the report under 30 lines.
