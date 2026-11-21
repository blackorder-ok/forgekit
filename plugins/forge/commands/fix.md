---
description: Fix one bug with the smallest change. Reproduce it with a failing regression test first, make one root-cause change, and keep the diff inside the budget. Runs on develop or a feature branch.
argument-hint: <bug description>
---

Bug: $ARGUMENTS

## Preconditions
- Run `git branch --show-current`. It must be `develop` or `feature/<name>`. For a production bug use `/forge:hotfix`. Otherwise stop and report the branch.
- Run `git status`. The working tree must be clean. If not, stop and ask the user to commit or stash.
- Run `/forge:doctor stack`. `NOT READY` stops the run.

## Steps
1. **Mark the run.** Create the empty file `.claude/fix-active`. The diff_budget hook (`templates/project/hooks/diff_budget.sh`) reads it, and the file is removed at the end.
2. **Reproduce.** Launch `tester` to write one regression test that fails for the bug, marked with its level from `test-levels`. Run it and confirm it fails for the reported reason. No test, no fix: if it cannot be reproduced, stop and report what was tried.
3. **Root cause.** State the cause in one sentence, with `file:line`.
4. **Fix.** Launch `developer` with the bug, the root cause, and the failing test. Require the regression test to pass.
5. **Budget.** The diff_budget hook blocks the stop if the change is over 3 files or 20 changed lines. If it blocks, do not widen the budget. Report and recommend `/forge:design`.
6. **Review.** Launch `reviewer` with one question: does every changed line trace to this bug? Any no is a blocker, and `developer` reverts that line.
7. **Gates.** Run the affected tests and the `unit` level. Then launch `ops` with `/forge:check <branch's environment>`. Require `GREEN`.
8. **Clean up.** Delete `.claude/fix-active`. Docs need no change unless behaviour changed. If it did, launch `doc-updater`.
9. **Report.** Root cause, files changed, tests run with results, reviewer verdict, devops verdict, and the "Other findings" list from `developer`.

Do not commit. Commit and push are the user's call.

## On failure
- Cannot reproduce: stop. Report what was tried.
- Regression test fails for a reason other than the bug (import, syntax): fix the test file once. If it still fails, stop.
- Over budget: stop, delete `.claude/fix-active`, and recommend `/forge:design`.
- Reviewer blocker that `developer` cannot clear in one round: stop and report it.
- Gate `RED`: stop and report the output. Delete `.claude/fix-active` first.
