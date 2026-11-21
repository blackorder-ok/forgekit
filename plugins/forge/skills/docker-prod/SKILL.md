---
name: docker-prod
description: Production-like Docker rules, one app container per environment with nginx, backend, MySQL and Ollama, plus the AWS emulator. Use when writing or reviewing Dockerfiles, compose files or runtime setup.
pack: stack
---

# Docker, one stack per environment

Templates (`templates/docker/`) are rendered by `/forge:scaffold-project`; do not rewrite them by hand.

## Layout
- **app** (one per env): nginx (frontend and `/api` proxy), FastAPI, MySQL, Ollama (develop only), under supervisord, each as its own non-root user.
- **aws-emulator**: internal network only, no Docker access.
- **tests**: pytest behind the `test` profile, `network_mode: service:app`.

## Image
Build order frontend → backend → app. Config files for one env only; secrets mounted at run time. Tag `app-api:<env>-<sha>`, never `latest`. Pinned MySQL and Ollama, checksum-verified, no pipe-to-shell.

## Security layers
Read-only root with named volumes and tmpfs; `cap_drop: ALL` then only what mysqld and nginx need (list marked `TODO-VERIFY`); `no-new-privileges`; `init: true`; app port bound to `127.0.0.1` at `app_ports.<env>`; networks `edge` (outbound) and `internal` (emulator); no Docker socket; nginx security headers; secrets mounted read-only, entrypoint prints key names only; image scanned in CI before a release tag.

## Compose
`docker/compose.<env>.yml`, project `app-<env>`; no shared networks or volumes between envs; services wait on `service_healthy`; no source bind mounts.

## Verify
`config` valid · `up -d --wait` healthy · `/api/health` ok · `--profile test run --rm tests pytest -q -m unit` passes · data survives `down` then `up` · logs show no tracebacks.

Full rules: `references/full-rules.md`.
