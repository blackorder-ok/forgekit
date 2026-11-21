---
description: Bring the docs and the changelog in line with the current branch's changes, without touching code.
---

Launch the `doc-updater` agent on the current branch against `develop`. It updates only documentation files and `CHANGELOG.md`.

When it finishes, report the list of files changed and any open questions it raised. Do not commit. Show the diff summary and wait for the user to commit it.

If the current branch is `qa`, `release`, or `master`, stop and report: documentation changes go through `develop` first.

## On failure
- A command in the README does not exist or a flag is wrong: fix the README line, then rerun the check.
- A link does not resolve: report it as an open question. Do not invent the target.
- On `qa`, `release`, or `master`: stop before any edit (already in the command), and say which branch to use.
