---
name: config-db
description: Rules for config files, secrets, database and vector-store settings per environment. Use when code reads settings, keys, endpoints or stored records.
pack: stack
---

# Config, secrets, database

## Files (the only settings files)
- `config/application.properties` shared · `config/application-<env>.properties` per env · `secrets/application-<env>-secrets.properties` git-ignored; only `.example` (key names, no values) is committed.
- Load order shared → env → secrets; later wins. CI writes the secrets file from `CP_SECRETS`, then deletes it.

## Rules
- `APP_ENV` is the only env var. Unknown or missing: refuse to start.
- One loader, `backend/app/config/loader.py`, reads all settings. No `os.getenv` or file reads elsewhere. Load once, cache in a singleton.
- Missing key: raise an error naming the key. Never default a secret or an endpoint.
- Log which file supplied a key, never the value.
- Each env names its own resources. A `qa` config pointing at `develop` resources fails to start.
- The image copies only the shared file and `application-<APP_ENV>.properties`. Secrets are mounted at run time.

## Database
MySQL inside the env's app container, data on the `app-data` volume. Alembic migrations run on start. Seed data is idempotent, `develop` and `qa` only. Runtime data only in the DB: flags, prompt versions, model profiles, never secrets.

## Vector store
Pinecone behind a `VectorStore` interface (`PineconeVectorStore`, `FakeVectorStore`). One index per env, `<project>-<env>`. Validate vector length against the task type's dimension before every write.

## Reviewer checks
No `os.getenv` outside the loader. Every new key is in the right file with a `config` test for its missing-key error. No real secret in a committed file.

Key lists and generated file content: `references/keys-and-rules.md`.
