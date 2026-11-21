<!-- Reference for the ci-pipeline skill. Ported from setting-up-claude/ci-pipeline (v0.1.0); read only when the digest is not enough. -->

# CI pipeline

Templates: `templates/ci/ci.yml` and `templates/ci/env-tests.yml`. `/scaffold-project` copies them to `.github/workflows/` unchanged. Edit the templates, not the copies in a project.

## Rules
- Every push and every PR runs `verify`. A failing `verify` blocks the merge.
- `verify` runs `ruff`, `mypy`, the `unit or config or security` tests with an 80% coverage floor on `backend/app`, `bandit`, `pip-audit`, and `gitleaks`.
- The `frontend` job runs only when `frontend/package.json` exists. It runs typecheck, tests, build, and the `innerHTML` check.
- Each branch's environment job runs only for that branch, after `verify` passes.
- Each job uses a GitHub environment named after the branch. The secret is `CP_SECRETS` per environment, holding the full contents of that environment's `secrets/application-<env>-secrets.properties`.
- The job writes `secrets/application-<env>-secrets.properties` from `CP_SECRETS` through an `env:` variable, never by putting `${{ secrets.* }}` inside a `run:` script. It deletes the file in an `always()` step.
- Each job builds its own image and starts its own stack. Nothing persists between runs.
- The test run uses `--profile test` so the `tests` service starts.
- `master` requires a reviewer on its GitHub environment.
- Setting `CP_SECRETS` uploads secret values to GitHub. Do it only after the user confirms it for that repository and environment. Keep it in a separate step from creating environments and protection rules. Do not combine them in one command.
- Never set secrets on a public repository without that confirmation.
- `permissions: contents: read` at workflow level. Grant more only to a job that needs it.
- Third-party actions are pinned to a major version. Pinning to commit SHAs is a later hardening step.

## Later
- The `master` job stops at smoke tests. Add a real deploy step when a deploy target exists.
- Add CodeQL when the code base grows.
