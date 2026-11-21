---
description: Open a promotion pull request between environment branches, after the source checks pass.
argument-hint: <from> <to>  (develop qa, qa release, or release master)
---

Promotion: $ARGUMENTS

Allowed pairs only: `develop qa`, `qa release`, `release master`. Anything else: stop and report.

1. Run `git status`. The working tree must be clean and the local branch must match the remote. Otherwise stop.
2. Run `/forge:check <from>`. Require `GREEN`. Stop on `RED`.
3. Open a pull request with `gh pr create --base <to> --head <from>`. Title: `promote: <from> → <to>`. The body lists the commits being promoted and the `/forge:check` result.
4. Report the pull request link.

Rules:
- Never push directly to `qa`, `release`, or `master`.
- Never merge. The user merges after approval. `master` also needs the environment reviewer.
- Do not promote if `<to>` has commits that are not on `<from>`. Report them and stop.

## On failure
- `gh` not installed or not logged in: print the exact commands to run by hand, then stop. Do not guess credentials.
- `/forge:check <from>` `RED`: stop and report it.
- Remote does not match local: stop. Ask the user to push or pull. Never force.
- Pull request creation fails: retry once, then print the compare URL and stop.
