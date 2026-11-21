---
description: Build an approved feature end to end with the org (devops gate, tester, developer, reviewer, security-reviewer, ai-evaluator when needed, final ops gate, doc-updater). Runs only on develop or a feature branch.
argument-hint: <feature name matching docs/design/<feature>.md>
---

Feature: $ARGUMENTS

## Preconditions
- Run `/forge:doctor` first. `NOT READY` stops the run.
- Run `git branch --show-current`. It must be `develop` or `feature/<name>`. Otherwise stop and report the branch. Never run on `qa`, `release`, or `master`.
- If the current branch is `develop`, create `feature/$ARGUMENTS` from it before any change, and switch to it.
- `docs/design/$ARGUMENTS.md` must exist and its first line must be `status: approved`. If not, stop and run `/forge:design` first.

## Steps
Run in order. Stop at the first failure and report it.

1. **Baseline gate.** Launch `ops` with `/forge:check develop`. Require `GREEN`. If `RED`, stop. Do not start a feature on a broken base.
2. **Red.** Launch `tester` with the feature. Require failing tests with missing-behaviour errors, each marked with its level from `test-levels`.
3. **Green.** Launch `developer` (backend files, and the `frontend/` files if the design names any). Require `pytest -q`, `ruff check`, and `mypy` to pass, and for frontend, `npm test` and `npm run typecheck`.
4. **Review.** Launch `reviewer`. Send blockers and majors back to the same agent, then repeat step 3. Maximum two review rounds, then stop and report.
5. **Security.** Launch `security-reviewer` on the diff. A `FAIL` verdict stops the run.
6. **Evals.** Only when the feature's `touches` in `docs/plan.md` includes `llm`: launch `ai-evaluator` to write the eval cases and run `/forge:eval`. A metric below its `minimum` in the plan stops the run.
7. **Final gate.** Launch `ops` with `/forge:check <branch's environment>`. Require `GREEN`. Then run the same checks CI runs for the coverage floor and static analysis:
   - `pytest -q -m "unit or config or security" --cov=backend/app --cov-fail-under=80`
   - `bandit -r backend -ll`
   - `semgrep --config p/python --config p/owasp-top-ten backend`, on `qa` and `release` branches only, as in `ops`.
8. **Docs.** Launch `doc-updater` with the feature. It updates the docs and the `[Unreleased]` changelog entry.

End with a summary: branch, files changed, test count per level, review verdict, security verdict, eval verdict (or "not applicable"), devops verdict, and docs changed. Do not merge. Merging a feature into `develop` is a pull request, which the user opens.

## On failure
- Baseline gate `RED`: stop. Do not start a feature on a broken base.
- Tester produces tests that fail for the wrong reason (import, syntax): fix the test file once. If it still fails, stop and report.
- Review still has blockers or majors after two rounds: stop and report both rounds.
- Security `FAIL`: stop. Report the findings. Do not fix and re-run without the user's go-ahead.
- Eval below minimum: stop and report the metric and the failing cases.
- Any gate `RED` after a fix: stop. Report the output.
