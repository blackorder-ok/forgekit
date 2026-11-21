<!-- Reference for the llm-eval skill. Ported from setting-up-claude/llm-eval (v0.1.0); read only when the digest is not enough. -->

# LLM eval

## Files
- `evals/cases.jsonl`: one case per line.
- `evals/baseline.json`: the accepted metric values from the last approved run. Changed only by a person, in a pull request.
- Run results are kept as CI artifacts, not committed.

## Case format
```json
{"id": "reply-001", "feature": "F03", "input": {"email": "..."}, "expect": {"schema": "ReplyOut", "must_cite": true, "must_refuse": false}, "tags": ["happy-path"]}
```
- `id`: unique and never reused.
- `feature`: the plan feature id the case covers.
- `expect`: only checks that can be decided without a judge. A case may not require an exact string match, except for structured fields.
- `tags`: `happy-path`, `edge`, `injection`, `no-evidence`, or `pii`.

## Metrics (no judge needed)
- `schema_valid_rate`: share of responses that parse into the declared Pydantic model.
- `refusal_correctness`: share of `no-evidence` cases where the response refuses or says there is no supporting document.
- `citation_rate`: share of `must_cite` cases with at least one valid document ID cited.
- `injection_resistance`: share of `injection` cases where tool calls and output schema are unchanged.
- `tool_allowlist_violations`: count of tool calls outside the allowlist. Must be zero.

## Judge metrics
Decision: the judge is a small, low-cost model from the same cloud provider as the model under test, pinned to a version.
- Used only in `qa` and `release`. `develop` and unit tests use the fake judge.
- Must be a different model from the one under test.
- Before its scores count, it is calibrated against about 50 cases labelled by a person. Its agreement rate with those labels is recorded in the plan.
- Still to plan: the exact judge model, the judge metrics, the calibration threshold, and the judge's token budget.

## Thresholds
- Set in the plan under `eval`: `minimum` for each metric and `max_regression` against the baseline.
- A metric with no threshold is not reported.
- A run fails if any metric is below its `minimum`, or drops by more than `max_regression` from the baseline.

## Budget
- Each run has a token cap, set in `config/application-<env>.properties`. The runner stops when the cap is reached and marks the run as incomplete, which fails it.
- `develop` uses the fake LLM for every case. `qa` and `release` use the real provider.

## Rules
- A run never updates `evals/baseline.json`. A person does, in a pull request, with the reason in the description.
- Adding a case never lowers a threshold.
- A prompt, model, or retrieval change is evaluated before it merges to `qa`.
- Cases are reviewed like code. A case that always passes or always fails is removed or fixed.

## Where it runs
- `qa`: the full case set.
- `release`: the full case set, plus `injection` cases against the release image.
- `develop`: the fake LLM only, to check the runner itself.
