<!-- Reference for the test-levels skill. Ported from setting-up-claude/test-levels (v0.1.0); read only when the digest is not enough. -->

# Test levels

Each test carries one marker. Markers are set in `pytest.ini`.

| Marker | Runs on | Covers | Rules |
|---|---|---|---|
| `unit` | every branch and PR | Pure logic with fakes for DB, AWS, and LLM | No network, no tokens, under 1 s each |
| `config` | every branch and PR | Each `config/application-<env>.properties` loads. Missing keys fail. Each environment rejects settings from another environment | No secrets needed |
| `integration` | `develop`, `qa` | MySQL in the app container, the AWS emulator AWS, and the environment's Pinecone index. Repositories, config loader, AWS calls, vector writes and reads | Uses seed data from the repo. Each run uses its own namespace in the Pinecone index and deletes it afterwards |
| `contract` | `develop`, `qa` | OpenAPI matches the saved snapshot. Model output validates against each Pydantic schema, using recorded responses | Snapshot changes need a reviewer |
| `security` | PR, `qa` | Unauthenticated calls return 401. Cross-user access returns 403. Malicious input is rejected. Prompt-injection text does not change tool use. DAST baseline on the running API | Uses the fake LLM for injection tests |
| `migration` | `qa` | Migrations apply on an empty database, roll back the latest, and reapply | Runs against a throwaway database |
| `e2e` | `qa`, `release` | Critical user flows through the API | Seed data only, no production data |
| `llm` | `qa`, `release` | Golden set of expected outputs with pass thresholds. Token budget per run | Real provider on `qa`, recorded responses on PR. Fails the run if the budget is exceeded |
| `load` | deferred | Latency and throughput thresholds. Token cost per request | Not built yet. See `FUTURE.md` |
| `backup` | `release` | Restore a database backup, then run the smoke tests against it | Restore to a throwaway database |
| `uat` | `release` | Business scenarios from a written checklist, signed off by a person | Recorded in the pull request |
| `smoke` | `master` | Health endpoint, one read-only check, and a rollback trigger on failure | No writes in production |

## Pass rules
- A level passes only if every test in it passes. Skipped tests count as failures unless the design lists them as out of scope.
- A promotion needs the target level's tests green on the source branch's commit.
- Coverage floor: 80% on `backend/app`, enforced in `verify` for `unit`, `config`, and `security`. The `develop` run also reports `integration` coverage.
- Tests that call a real provider never run on a PR.

## Tester's job
- Write tests for the level the branch is at, using the table above.
- Every new feature needs a `unit` test and a `config` test if it adds a setting. Add `integration` if it touches AWS or the database. Add `security` if it touches auth, input, or model output.

## Layout (industry standard)
- Tests live in a top-level `tests/` folder, separate from the application package.
- Below `tests/`, one folder per level: `tests/unit/`, `tests/integration/`, `tests/e2e/`, `tests/contract/`, `tests/config/`, `tests/security/`, `tests/llm/`. The marker and the folder agree.
- Inside each level, mirror the package path. A test for `app/services/chat.py` is `tests/unit/services/test_chat.py`.
- Shared fixtures live in `tests/conftest.py`. Level-specific fixtures live in `tests/<level>/conftest.py`. No fixtures in test modules.
- Fakes live in `tests/fakes/`, not in application code. Application code must not import from `tests/`.
- `pytest.ini` at the project root: `testpaths = tests`, `pythonpath = .`, every marker registered.
- Test names: `test_<unit>_<behaviour>`. One behaviour per test.

## Generated: pytest.ini
Scaffold writes this file at the project root, unchanged except the `pythonpath` line.

```ini
[pytest]
testpaths = tests
pythonpath = backend .
markers =
    unit: pure logic with fakes for DB, AWS, and LLM
    config: each config/application-<env>.properties and secrets/application-<env>-secrets.properties loads, missing keys fail
    integration: MySQL, the AWS emulator, and the Pinecone index
    contract: OpenAPI and model output match snapshots
    security: auth, input validation, prompt injection
    migration: migrations apply, roll back, and reapply
    e2e: critical user flows through the API
    llm: golden set against the provider or recorded responses
    backup: restore a database backup and run smoke tests
    uat: business scenarios signed off by a person
    smoke: read-only checks in production
```
