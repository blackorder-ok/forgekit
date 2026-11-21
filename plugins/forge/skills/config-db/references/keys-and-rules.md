<!-- Reference for the config-db skill. Ported from setting-up-claude/config-db (v0.1.0); read only when the digest is not enough. -->

# Config, secrets, and database

## Files and naming (Spring Boot convention)
- `config/application.properties`: shared settings for every environment. Committed.
- `config/application-<env>.properties`: settings for one environment. Committed. `<env>` is `develop`, `qa`, `release`, or `master`.
- `secrets/application-<env>-secrets.properties`: secrets for one environment. Git-ignored. Only `secrets/application-<env>-secrets.properties.example` is committed, with key names and no values.
- Those three kinds of file are the only settings files. Do not add other `*.properties` files for settings.
- Load order: shared, then environment, then secrets. A later file overrides an earlier key.
- In CI, the job writes `secrets/application-<env>-secrets.properties` from the GitHub environment secret `CP_SECRETS`, then deletes it.

## Precedence per setting
1. The secrets file wins for every key it defines.
2. Otherwise the environment file, then the shared file.
3. Missing key: raise an error that names the key. Never guess a default for a secret or an endpoint.
4. The database holds runtime data only: feature flags, prompt versions, model profiles. Never secrets, and never anything that must differ from the committed config without a migration.

## Environment switch
- `APP_ENV` selects the environment. It is the only environment variable the app needs.
- Unknown or missing `APP_ENV`: refuse to start.
- The image build copies only `config/application-<APP_ENV>.properties` and the shared file.

## Startup guard
- Each environment's config must name its own resources. A `qa` config that points at `develop` resources fails to start.
- `master` may point at its own AWS emulator until real AWS is set up. When real AWS is set up, `master` must not point at any local address. Remove the AWS emulator exception at that point.

## Rules
- One loader module reads all settings: `backend/app/config/loader.py`. No other module reads env vars or files directly.
- Load once at startup. Cache in a singleton.
- Log which file supplied each key, never the value.
- Each database schema change is a migration. No hand edits.
- Downloaded files go to a configured directory, are checked for size and type, and are never executed.

## Database
- Engine: MySQL 8.0, running inside the environment's `app` container (see `docker-prod`). Data lives on the `app-data` volume and survives restarts.
- Host and port: `database.host` and `database.port` in the shared file. Name: `database.name` in the environment file. Password: `database.password` in the secrets file.
- Migrations: Alembic. The backend process applies them on start, before it serves requests.
- Seed data is an idempotent script in the repo, loaded only in `develop` and `qa`.
- No production data outside `master`. `develop` and `qa` use seed data.

## Vector store
- Provider: Pinecone. No local emulator exists, so there is nothing to run in compose.
- One index per environment, named `<project>-<env>`. The index name lives in `config/application-<env>.properties`. The API key lives in the secrets file.
- Code talks to the `VectorStore` interface only. `PineconeVectorStore` is the real implementation and `FakeVectorStore` is used by `unit` and `config` tests.
- Index dimension is set per task type in the plan, between 256 and 1536. Features that share a task type share its index and dimension. The vector length is validated against the task type's dimension before every write. Changing it requires a new index and a re-embedding plan for the stored vectors.

## Checks for the reviewer
- No `os.getenv`, and no direct file reads, outside `loader.py`.
- Every new key is in the right file, and has a `config` test for its missing-key error.
- No real secret in any committed file.

## Generated config and secrets files
Scaffold writes these from the key list below. Keys are the same in every environment; only the values change.

Shared, `config/application.properties` (values as the plan gives them; `{{PROJECT}}` is the project name):
```
app.name={{PROJECT}}
database.host=127.0.0.1
database.port=3306
database.user=app
vector.provider=pinecone
vector.metric=cosine
vector.dimension=<from the plan's vector_store.dimension for the first task type>
llm.apiKeyRequired=true
aws.region=us-east-1
aws.endpointUrl=http://aws-emulator:4566
```

Per environment, `config/application-<env>.properties`:
```
app.env=<env>
database.name={{PROJECT}}_<env>
vector.indexName={{PROJECT}}-<env>
llm.provider=<plan llm.cloud_provider, or ollama in develop>
llm.model=<from the plan>
llm.embeddingModel=<from the plan, per task type>
llm.baseUrl=<from the plan; empty for ollama is not allowed, use http://127.0.0.1:11434 in develop>
llm.tokenBudget=<plan llm.monthly_token_budget.<env>>
aws.hostEndpointUrl=http://localhost:<aws_emulator.ports.<env>>
```

Per environment, `secrets/application-<env>-secrets.properties.example` (key names only, no values):
```
database.password=
vector.apiKey=
llm.apiKey=
aws.accessKeyId=test
aws.secretAccessKey=test
```
