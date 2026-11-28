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

**Missing verdict.** If the agent's reply has no `VERDICT:` line (cut off or at its turn limit), send it once with `SendMessage`: summarise what is done and what is left, finish the task, and end with the verdict line. If there is still no verdict, or the agent does not reply, stop and report `INCOMPLETE` with its partial output. Never make a third attempt.
