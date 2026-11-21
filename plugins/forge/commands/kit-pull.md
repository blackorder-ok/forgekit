---
description: Check the kit repo for new tags, show what would change and update the plugin only after you approve. Never automatic.
argument-hint: (none)
---

1. Run `python "${CLAUDE_PLUGIN_ROOT}/scripts/kit_pull.py"`. It runs `git fetch --tags` in the kit repo, lists tags newer than the installed version, and prints the changelog lines and the diff stat between them. It changes nothing.
2. Show that to the user. If there is no newer tag, say so and stop.
3. Only after a yes, tell the user to run: `/plugin marketplace update forgekit` then `/plugin update forge@forgekit` (or restart the session). Run the update yourself only if the user asks.
4. Mention that auto-update stays off for this marketplace; this command is the only update path.

Never check out, merge or pull on the user's kit clone. Never touch files in `~/.claude`.
