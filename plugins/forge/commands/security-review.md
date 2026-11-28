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

**Missing verdict.** If the agent's reply has no `VERDICT:` line (cut off or at its turn limit), send it once with `SendMessage`: summarise what is done and what is left, finish the task, and end with the verdict line. If there is still no verdict, or the agent does not reply, stop and report `INCOMPLETE` with its partial output. Never make a third attempt.
