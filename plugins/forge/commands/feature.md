---
description: Build an approved feature end to end with the org (devops gate, tester, developer, reviewer, security-reviewer, ai-evaluator when needed, final ops gate, doc-updater). Runs only on develop or a feature branch.
argument-hint: <feature name matching docs/design/<feature>.md>
---

Feature: $ARGUMENTS

## Preconditions
- Check the tools inline, in one Bash call, without invoking `/forge:doctor` (a nested command's report can end your turn): `docker info`, `docker compose version`, `git --version`, `python --version` (3.11.x). Do not touch `secrets/`: the project denies reads there, and a missing secrets file shows up in the gate. Any failure stops the run. Success is not a result to report: go on to step 1 in the same turn.
- Run `git branch --show-current`. It must be `develop` or `feature/<name>`. Otherwise stop and report the branch. Never run on `qa`, `release`, or `master`.
- If the current branch is `develop`, create `feature/$ARGUMENTS` from it before any change, and switch to it.
- `docs/design/$ARGUMENTS.md` must exist and its first line must be `status: approved`. If not, stop and run `/forge:design` first.

## Steps
Run in order without pausing. Launch every agent in the foreground, one at a time, and wait for its result (never in the background, never two copies): a headless run ends while background agents are still working. Stop only at a failure; otherwise finish all 8 steps, then summarise.

1. **Baseline gate.** Skip it when `git ls-files backend` is empty (F01 creates it; step 7 is its gate). Otherwise launch `ops` with `/forge:check develop`. Require `GREEN`; if `RED`, stop (never build on a broken base).
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
- Tester produces tests that fail for the wrong reason (import, syntax): fix the test file once. If it still fails, stop and report.
- Review still has blockers or majors after two rounds: stop and report both rounds.
- Security `FAIL`: stop. Report the findings. Do not fix and re-run without the user's go-ahead.
- Eval below minimum: stop and report the metric and the failing cases.
- Any gate `RED` after a fix: stop. Report the output.

**Missing verdict.** If the agent's reply has no `VERDICT:` line (cut off or at its turn limit), send it once with `SendMessage`: summarise what is done and what is left, finish the task, and end with the verdict line. If there is still no verdict, or the agent does not reply, stop and report `INCOMPLETE` with its partial output. Never make a third attempt.
