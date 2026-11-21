---
description: Search project and kit memory cheaply. Subcommands are search, show, timeline and add; the session-start index shows ids.
argument-hint: search <words> | show <id> | timeline <id> | add <type> "<title>" "<body>"
---

Request: $ARGUMENTS

Run `python "${CLAUDE_PLUGIN_ROOT}/scripts/kit_mem.py" $ARGUMENTS` from the project root and show the output as is.

Subcommands: `search <words>` returns ids and titles only (cheap); `show <id>` returns one entry (at most about 150 tokens); `timeline <id>` returns the neighbours in time; `add <type> "<title>" "<body>"` writes a project memory entry, where type is `gotcha`, `fix`, `decision` or `preference`.

Use `search` first, then `show` only for the ids that matter. Never print all entries. Project memory lives in `.claude/memory/`; it never enters the kit unless the user runs `/forge:kit-review` and approves.
