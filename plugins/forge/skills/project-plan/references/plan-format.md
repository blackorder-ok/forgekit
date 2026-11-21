<!-- Reference for the project-plan skill. Ported from setting-up-claude/project-plan (v0.1.0); read only when the digest is not enough. -->

# Project plan

The plan is the only input to `/scaffold-project`. It is written once, validated, and then read as data. It contains no code and creates no folder, repo, or branch.

## File
- Location: `./<project>.plan.md`, in the parent folder where the project will be created.
- Structure: a YAML front matter block, then the prose sections below.

## Front matter (required)

```yaml
project: <kebab-case or snake_case name, unique, not an existing folder>
mode: new | existing      # existing: written by /adopt-project from a repository that already exists
summary: <one sentence>
owner: <name>
python: "3.11"
stack:                    # required when mode is existing; the values the project really uses
  language: <e.g. python 3.11>
  framework: <e.g. fastapi>
  database: <e.g. mysql 8.0>
  test_runner: <e.g. pytest>
  ci: <e.g. github actions, or none>

environments: [develop, qa, release, master]
branches: {develop: develop, qa: qa, release: release, master: master}
aws_emulator:
  image: "<image:tag@sha256:digest>"   # pinned, never latest; default today: the Floci image
  ports: {develop: 4566, qa: 4567, release: 4568, master: 4569}

app_ports: {develop: 8080, qa: 8081, release: 8082, master: 8083}   # host ports, one per environment

database:
  engine: mysql
  version: "8.0"
  host: 127.0.0.1          # MySQL runs inside the app container
  migrations: alembic
  contains_personal_data: true | false

vector_store:
  provider: pinecone
  index_per_env: "<project>-<env>"
  dimension: <int, 256 to 1536, chosen per task type: each task type in the plan (for example retrieval, classification, similarity) names its own embedding model and dimension>
  metric: cosine

llm:
  local_dev: ollama | none
  cloud_provider: <name>
  monthly_token_budget: {develop: <int>, qa: <int>, release: <int>, master: <int>}

eval:                      # required if any feature uses the llm test level
  metrics: [schema_valid_rate, refusal_correctness, citation_rate, injection_resistance, tool_allowlist_violations]
  minimum: {schema_valid_rate: <0-1>, refusal_correctness: <0-1>, citation_rate: <0-1>, injection_resistance: <0-1>, tool_allowlist_violations: 0}
  max_regression: <0-1>    # how far a metric may drop below baseline

aws_services: [<services the app calls, emulated by the AWS emulator>]

features:
  - id: F01
    name: <short name>
    goal: <one sentence>
    depends_on: []
    environments: [develop, qa, release, master]
    touches: [db, vector, llm, aws, api]
    tests: [unit, config, integration, contract, security, e2e, llm, load, uat]   # subset from test-levels
```

## Body sections (required, in order)
1. **Goal:** what the product does, in plain words.
2. **Users:** who uses it, and what they do.
3. **Scope:** what is in version one.
4. **Non-goals:** what is explicitly out.
5. **Data model:** each entity with its key fields, and whether it holds personal data.
6. **Features in build order:** generated from the `features` list. Each feature gets a short paragraph of acceptance criteria.
7. **Security and data:** who can see what, retention per entity, deletion requests.
8. **Open decisions:** each one marked `deferred` with a reason, or resolved. None may be left unmarked.

## Team defaults (use unless the user overrides)
- Branches: `develop`, `qa`, `release`, `master` (production). Feature branches from `develop`.
- Database: MySQL 8.0 inside the environment's app container, data on a persistent volume. Migrations with Alembic.
- Vector store: Pinecone, one index per environment, named `<project>-<env>`. No local emulator exists, so tests use a fake.
- AWS: emulated by the AWS emulator in every environment until real AWS is set up.
- Local LLM: Ollama in `develop` only. Cloud provider in `qa`, `release`, and `master`.
- Foundation feature F01 comes first. It is built by `/design F01` and `/feature F01`, not by the scaffold. F01 contains:
  - config loader and logging (`config-db`)
  - database connection and Alembic migrations, with one empty initial migration
  - `VectorStore` interface, `FakeVectorStore`, and `PineconeVectorStore`
  - health and docs endpoints (`/health`, `/api/docs`)
  - one test per test level the plan enables, including a `smoke` test on `/health`

## Feature ordering rules
- Each feature lists only earlier features in `depends_on`. No cycles.
- The foundation features come first, in the order above.
- A feature that touches `vector` or `llm` must come after the interface it uses.
- A feature with `contains_personal_data` entities includes the `security` test level.
- Keep features small enough for one `/design` and one `/feature` run each.

## Validation checklist
A plan passes only if every item holds:
- All required front matter keys are present, and their types match.
- `mode` is `new` or `existing`. A `new` plan needs no `stack` block; an `existing` plan needs all five `stack` keys.
- `project` is kebab-case (Pinecone index names allow only lowercase letters, digits, and hyphens). For `mode: new`, no folder with that name exists in the parent folder. For `mode: existing`, the folder is the repository being adopted.
- `environments` is exactly `[develop, qa, release, master]`.
- AWS emulator ports are unique and are one per environment.
- `app_ports` values are unique and one per environment.
- `aws_emulator.image` is pinned by tag and digest, not `latest`.
- `database.engine` is `mysql` unless the user explicitly changed it.
- `vector_store.index_per_env` contains the literal `<env>` placeholder, so one index name is produced for each of the four environments.
- Every entry in `monthly_token_budget` is a positive number.
- If any feature lists the `llm` test level, `eval` is present, and each metric it lists has a `minimum`. `tool_allowlist_violations` has a minimum of 0.
- Every feature `id` is unique, and every `depends_on` refers to an earlier feature.
- Each body section is present. Open decisions are all `deferred` or resolved.
- Each entity in the data model states whether it holds personal data.

Any failure is reported as a list. The plan is not written as valid until the list is empty.

## Planning rules
- Ask only for facts the idea does not answer: users, main features, cloud LLM provider, token budgets, and whether personal data is stored.
- Prefer the team defaults above. Record each override in the open-decisions section with the reason.
- Do not design modules, classes, or endpoints here. That belongs to `/design` for each feature.

## Frontend default
- A project with a page uses the `frontend` skill: React with TypeScript, built with Vite, served by nginx in its own container. Name a different stack in the plan only with a reason.
