---
name: llm-eval
description: How AI quality is measured, covering eval case format, metrics, baseline and regression rules, plan thresholds and run budget. Use when writing eval cases, running /forge:eval or changing a prompt, model or retrieval setting.
pack: stack
---

# LLM eval

## Files
`evals/cases.jsonl` (one case per line), `evals/baseline.json` (changed only by a person in a PR). Run results are CI artifacts, not committed.

## Case
`{"id","feature","input","expect":{"schema","must_cite","must_refuse"},"tags":[happy-path|edge|injection|no-evidence|pii]}`. Ids are unique and never reused. Expectations are checks decidable without a judge; no exact-string match except structured fields.

## Metrics (no judge)
`schema_valid_rate` · `refusal_correctness` · `citation_rate` · `injection_resistance` · `tool_allowlist_violations` (must be 0).

## Thresholds and budget
Plan `eval.minimum` per metric and `max_regression` against baseline. A metric without a threshold is not reported. A run fails below a minimum or beyond the allowed drop. Each run has a token cap from env config; reaching it marks the run incomplete, which fails.

## Rules
A run never updates the baseline. Adding a case never lowers a threshold. Prompt, model or retrieval changes are evaluated before reaching `qa`. Remove cases that always pass or always fail. `develop` uses the fake LLM; `qa` and `release` use the real provider; `release` adds injection cases against the release image.

Judge metrics are still unplanned (see `docs/FUTURE.md`). Details: `references/full-rules.md`.
