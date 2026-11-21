---
description: Run the security reviewer on the current diff, or on the whole repo with "all".
argument-hint: [all | optional base branch]
---

Scope: $ARGUMENTS

Launch the `security-reviewer` agent. If the scope is `all`, review the whole repo. Otherwise review the diff against the base branch (default `develop`).

Return its verdict and findings list as-is. Do not edit any files.

## On failure
- Scanner not installed (bandit, pip-audit, gitleaks): report it as `skipped` with the install command. Do not count it as a pass.
- Scanner error (not a finding): report the error and stop.
