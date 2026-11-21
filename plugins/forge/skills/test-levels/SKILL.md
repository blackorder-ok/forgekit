---
name: test-levels
description: Test levels, their pytest markers, where each runs, pass rules and folder layout. Use when writing tests, planning a test run or deciding if a promotion can proceed.
pack: core
---

# Test levels

One marker per test, registered in `pytest.ini`.

| Marker | Runs on | Covers |
|---|---|---|
| `unit` | every branch | pure logic, fakes for DB, AWS, LLM; no network; under 1 s |
| `config` | every branch | each env file loads; missing keys fail; env isolation |
| `integration` | develop, qa | MySQL, AWS emulator, env Pinecone index (own namespace, deleted after) |
| `contract` | develop, qa | OpenAPI matches snapshot; model output matches schemas |
| `security` | PR, qa | 401/403, malicious input, prompt-injection (fake LLM) |
| `migration` | qa | apply, roll back, reapply on a throwaway DB |
| `e2e` | qa, release | critical flows via the API, seed data |
| `llm` | qa, release | golden set with thresholds and token budget |
| `backup` | release | restore then smoke |
| `uat` | release | written scenarios signed off by a person |
| `smoke` | master | health plus one read-only check |
`load` is deferred.

## Pass rules
- A level passes only if every test passes. Skips count as failures unless the design lists them out of scope.
- Promotion needs the target level green on the source commit.
- Coverage floor 80% on `backend/app` for `unit`, `config`, `security`.
- Real-provider tests never run on a PR.
- pytest exit code 5 (nothing selected) is a warning in CI, any other non-zero fails.

## Tester's job
Every feature: a `unit` test, plus `config` if it adds a setting, `integration` for AWS or DB, `security` for auth, input or model output.

## Layout
Top-level `tests/<level>/` mirroring the package path (`app/services/chat.py` → `tests/unit/services/test_chat.py`). Fixtures in `conftest.py`, fakes in `tests/fakes/`. Names `test_<unit>_<behaviour>`.

`config` tests use only the committed `config/*.properties` plus secrets built inside the test: the tests container has no `secrets/` (it is in `.dockerignore`), so never read `secrets/*` or `.example` files from a test. The image carries only its own env's config file: build the env list from the files that exist, and run `smoke` and `e2e` against a deployed env, not in the tests container.

Full table, `pytest.ini` block and layout: `references/levels-and-layout.md`.
