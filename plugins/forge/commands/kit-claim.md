---
description: Move one orphan unit from ~/.claude into the kit repo after you approve it. Scans for secrets and personal paths first.
argument-hint: <skill|agent|command> <name>
---

Request: $ARGUMENTS

1. Run `python "${CLAUDE_PLUGIN_ROOT}/scripts/kit_claim.py" $ARGUMENTS --dry-run`. It shows the source, the target path in the repo, the size and any scan hits (secrets, absolute personal paths, company names from `~/.kit/local-ignore`).
2. If there are hits, stop and show them. The user fixes the file first. Never claim around a hit.
3. Show the user the file's description line and size and ask for a yes. Only after a yes, run the same command with `--apply`. It copies the file into `plugins/forge/`, adds the `kit.json` entry, and leaves the original in place.
4. Run `python tools/check_kit.py --tokens` in the kit repo. Report the result.
5. Do not commit, tag or push.

One file per run. Never claim a unit that the user did not name.

## On failure
- Name not found in `~/.claude`: stop.
- Name already in `kit.json`: stop and tell the user to use `/forge:kit-new` or edit the repo copy.
