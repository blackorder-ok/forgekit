---
description: Check that an approved design, its tests and the code still agree, and fix the smallest mismatch. At most two rounds. Use after a feature build or when drift is suspected.
argument-hint: <feature name matching docs/design/<feature>.md>
---

Feature: $ARGUMENTS

Preconditions: branch is `develop` or `feature/*`; `docs/design/$ARGUMENTS.md` has `status: approved`; working tree clean.

Round (max 2):
1. Read the design's contracts and test plan. Read the tests and the code named in `touches`. Read nothing else.
2. Build a table: contract → test that covers it → code that implements it. Mark each row `ok`, `no test`, `no code`, or `mismatch`.
3. If all rows are `ok`: report `CONVERGED` and stop.
4. Otherwise route the smallest fix: `no test`/`mismatch` in tests → `tester`; `no code`/code mismatch → `developer` in fix mode; design wrong or incomplete → stop and tell the user to amend the design (never edit an approved design yourself).
5. Run `pytest -q -m unit` and repeat.

After round 2 with open rows: report `NOT CONVERGED` with the rows. Do not run a third round.

Report (under 25 lines): rows, verdict, files changed. Do not commit.

## On failure
- Design not approved or missing: stop.
- Tests fail for a reason outside the table: report it, do not widen scope.
