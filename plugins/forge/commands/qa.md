---
description: Run the e2e and uat levels against one deployed environment, and write the QA report. Read-only on application code.
argument-hint: <develop|qa|release|master>
---

Environment: $ARGUMENTS

## Preconditions
- The argument is one of `develop`, `qa`, `release`, `master`. Otherwise stop.
- Run `/forge:doctor`. `NOT READY` stops the run.

## Steps
1. Launch `tester` with the environment.
2. It runs the e2e level on `develop` and `qa`, the smoke level on `master`, and prepares the uat list for `release` and `master`.
3. Show the user the report path, the counts, the failures, and the uat items waiting for a person.

## On failure
- Stack not up: report `docker compose ps` output and stop.
- Any e2e failure: report it. Do not fix code. Hand the failing test names to the user.
