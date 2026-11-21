---
description: Fix a production bug. Cuts hotfix/<name> from master, runs the same reproduce-first flow as /forge:fix, then prepares a back-merge to develop. Changes nothing on master directly.
argument-hint: <bug description> (name used for the branch is derived from it)
---

Hotfix: $ARGUMENTS

## Preconditions
- Run `git status`. The working tree must be clean.
- Run `/forge:doctor`. `NOT READY` stops the run.
- The bug is in production (`master`). If it is only on `develop` or a feature branch, use `/forge:fix` instead.

## Steps
1. **Branch.** Run `git fetch` and create `hotfix/<short-name>` from `master`, then switch to it. The branch_guard hook allows edits on `hotfix/*`.
2. **Mark the run.** Create `.claude/fix-active`. Remove it at the end.
3. **Reproduce.** Same as `/forge:fix` step 2: one failing regression test, marked with its level. No test, no fix.
4. **Root cause and fix.** Same as `/forge:fix` steps 3 to 4.
5. **Budget and review.** Same as `/forge:fix` steps 5 to 6.
6. **Gates.** Run the regression test and `unit`. Then launch `ops` with `/forge:check master`. Require `GREEN`. If `master` has no stack running locally, run `/forge:check develop` on the same change as well.
7. **Back-merge.** Commit the change on `hotfix/<short-name>` only when the user says so. Then tell the user to open two pull requests: `hotfix/<short-name>` into `master`, and the same branch into `develop`. The user opens and merges them.
8. **Clean up and report.** Delete `.claude/fix-active`. Report root cause, files changed, tests, verdicts, "Other findings", and the two pull requests to open.

## On failure
- Same as `/forge:fix`. In addition: if `master` cannot be checked out cleanly, stop. Do not start from another branch.
