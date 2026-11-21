---
name: ci-pipeline
description: GitHub Actions rules for the develop, qa, release and master flow and the reusable env-test workflow. Use when creating or changing CI or when a pipeline step fails.
pack: core
---

# CI pipeline

Templates `templates/ci/ci.yml` and `templates/ci/env-tests.yml` are copied unchanged to `.github/workflows/`. Edit the templates, not the copies.

## Rules
- Every push and PR runs `verify`: ruff, mypy, `unit or config or security` tests with the 80% floor, bandit, pip-audit, gitleaks. A failure blocks the merge.
- The `frontend` job runs only if `frontend/package.json` exists.
- An environment job runs only for its branch, after `verify`, using the GitHub environment of that name and secret `CP_SECRETS`.
- Write the secrets file from `CP_SECRETS` through an `env:` variable, never `${{ secrets.* }}` inside `run:`. Delete it in an `always()` step.
- Each job builds its own image and stack. Test runs use `--profile test`.
- `master` needs a reviewer on its environment.
- Setting `CP_SECRETS` uploads secrets: only after the user confirms the repository and environment, in a separate step from creating environments and protection. Never on a public repo without that confirmation.
- `permissions: contents: read` by default. Third-party actions pinned to a major version.

Later: a real deploy step after smoke on `master`; CodeQL.

Full text: `references/full-rules.md`.
