---
description: Learn your personal Python style from your own repos and save it to ~/.kit/style.md. Samples files read-only, asks before saving.
argument-hint: <path to a folder with your own code> [more paths]
---

Folders: $ARGUMENTS

1. Run `python "${CLAUDE_PLUGIN_ROOT}/scripts/style_sample.py" $ARGUMENTS`. It prints counts only (naming styles, logging idioms, type-hint and docstring rates, line lengths, import habits, top-level patterns). It reads at most 40 files and prints no code.
2. Compare with the kit defaults in the `python-style` skill. List the differences in at most 12 bullets.
3. Show the proposed `~/.kit/style.md` (under 40 lines) and ask the user to approve it. Write it only after a yes. The file lives outside the kit repo and is never committed to it.
4. Tell the user a project can override it in `.claude/style.local.md`.

Never copy code or business names from the sampled files into the style file.
