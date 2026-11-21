---
description: Run the reviewer on the current diff and report findings.
argument-hint: [optional feature name for design context]
---

Feature context: $ARGUMENTS

Launch the `reviewer` agent on the current diff. If a feature name was given, include `docs/design/<feature>.md` as its design reference.

Return its verdict and findings list as-is. Do not edit any files.

## On failure
- No diff against the base branch: report `APPROVE` with the note `no changes`. Do not review the wrong branch.
- Reviewer cannot read a file: report it as a finding of `major` severity. Continue with the rest.
