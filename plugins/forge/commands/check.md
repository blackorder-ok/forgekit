---
description: Run the devops stack checks for one environment, with no feature work.
argument-hint: <develop | qa | release | master>
---

Environment: $ARGUMENTS

If no environment was given, use the environment of the current branch (`develop` or `feature/*` → `develop`). Stop if the environment is not one of `develop`, `qa`, `release`, `master`.

Launch the `ops` agent in the foreground (never in the background) with the check sequence for this environment only. It uses `docker/compose.<env>.yml` and `config/application-<env>.properties`. Return its per-check PASS/FAIL report and the overall `GREEN` or `RED` verdict.

If `RED`, include the failing output and the most likely cause. Do not change application code.

## On failure
- Transient failure (network, image pull, service still starting): retry the failed step once after 20 seconds.
- Any other failure: stop, return `RED` with the step name, the output, and the most likely cause. Do not continue to later steps.
- Missing `secrets/application-<env>-secrets.properties`: stop and tell the user which file to create. Never create it with values.
- Never edit application code to pass a check.

**Missing verdict.** If the agent's reply has no `VERDICT:` line (cut off or at its turn limit), send it once with `SendMessage`: summarise what is done and what is left, finish the task, and end with the verdict line. If there is still no verdict, or the agent does not reply, stop and report `INCOMPLETE` with its partial output. Never make a third attempt.
