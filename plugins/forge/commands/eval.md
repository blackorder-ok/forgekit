---
description: Run the AI eval set for one environment, compare against the baseline, and report.
argument-hint: <qa | release | develop>  (defaults to the current branch's environment)
---

Environment: $ARGUMENTS

If no environment was given, use the current branch's environment (`develop` or `feature/*` → `develop`). Stop if the environment is `master`, because evals never run in production.

1. Check that `evals/cases.jsonl`, `evals/baseline.json`, and the plan's `eval` block exist. If any is missing, stop and report it.
2. Run the `llm` level for this environment, using the marker and the budget from `config/application-<env>.properties`. On `develop`, use the fake LLM.
3. Compute each metric from the `llm-eval` skill.
4. Compare each metric with its `minimum` and with `evals/baseline.json`, using the plan's `max_regression`.
5. Report: each metric, its value, its threshold, its baseline, PASS or FAIL, and the token count of the run.
6. For any FAIL, launch the `ai-evaluator` agent to list the failing cases and the likely causes.
7. Do not update `evals/baseline.json`. Stop after the report.

Verdict: `PASS` only if every metric passes and the run finished within budget. Otherwise `FAIL`.

## On failure
- Missing `evals/cases.jsonl`, `evals/baseline.json`, or the plan `eval` block: stop and report which one.
- Token cap reached: mark the run incomplete, which is `FAIL`. Report the tokens used. Do not raise the cap.
- Provider error: retry once, then report `FAIL` with the error type. Never print the key.
- Never update `evals/baseline.json`.
