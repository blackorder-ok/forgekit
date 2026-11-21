<!-- Reference for the docker-prod skill. Ported from setting-up-claude/docker-prod (v0.1.0); read only when the digest is not enough. -->

# Docker, production-like, one container per environment

Templates: `templates/docker/app.Dockerfile`, `templates/docker/compose.stack.yml`, `templates/docker/supervisord.conf`, `templates/docker/nginx.conf`, `templates/docker/entrypoint.sh`. `/scaffold-project` renders them. Do not rewrite them by hand.

## What runs where
- **`app` container (one per environment):** nginx (frontend and `/api` proxy), the FastAPI backend, MySQL 8.0, and Ollama (develop only). All run under supervisord, each as its own Linux user: `mysql`, `ollama`, `app`, and nginx's root master with `www-data` workers.
- **`aws-emulator` container:** the AWS API emulator for S3, SQS, and similar services. It runs on the internal network only and is given no Docker access. RDS and EC2 are disabled in its config.
- **`tests` container:** pytest, behind the `test` profile, sharing the app container network.

## Image
- Build order: `frontend` (`docker/frontend.Dockerfile`, target `artifact`), then `backend` (`docker/backend.Dockerfile`, target `runtime`), then `app` (`docker/app.Dockerfile`, which builds on the backend image and copies the frontend output).
- Compose: `docker compose -f docker/compose.<env>.yml --profile build build frontend backend`, then `docker compose -f docker/compose.<env>.yml build app`.
- The image contains the shared and environment config files only. Secrets are mounted at run time and never baked in.
- Tag: `app-api:<env>-<commit sha>`. Never `latest`.
- Stages in order: `frontend-build`, `builder` (hashed wheels), `runtime` (the app service targets this), `test` (the tests service targets this; last stage).
- Ollama and MySQL come from pinned versions. Ollama is downloaded with a SHA-256 check, never through a pipe-to-shell install.
- Non-root users per service. No login shells.

## Security layers (applied to every environment)
- Root filesystem is read-only. Writable paths are named volumes (`app-data`) or tmpfs (`/tmp`, `/run`).
- `cap_drop: ALL`, then only the capabilities mysqld and nginx need on start. The list is marked `TODO-VERIFY` until tested.
- `no-new-privileges:true`. `init: true` for signal handling.
- The app port (`app_ports.<env>`) is bound to `127.0.0.1` only. Nothing is published on all interfaces.
- Two networks: `edge` for outbound calls (cloud LLM, Pinecone) and `internal` for the AWS emulator (no outbound route). The `tests` service shares the app container network (`network_mode: service:app`), so it reaches MySQL on 127.0.0.1 and the AWS emulator by name.
- No Docker socket anywhere in the stack. The AWS emulator is not given Docker access.
- nginx sends `Content-Security-Policy`, `X-Frame-Options`, `X-Content-Type-Options`, and `Referrer-Policy`, and hides its version.
- Secrets file mounted read-only. The entrypoint prints key names only, never values, and removes the MySQL init file after first use.
- Image is scanned in CI before it is tagged for a release.

## Compose
- File: `docker/compose.<env>.yml`. Project name `app-<env>`. Environments do not share networks or volumes.
- the AWS emulator state and MySQL data are named volumes, kept across restarts (`FLOCI_STORAGE_MODE=persistent`, `FLOCI_STORAGE_PERSISTENT_PATH=/app/data`).
- Services wait with `depends_on: condition: service_healthy`.
- No source bind mounts in the main file.

## Verification
- `docker compose -f docker/compose.<env>.yml config` is valid.
- `up -d --wait` brings `app` and `aws-emulator` to healthy.
- `curl -fsS http://127.0.0.1:<app_ports.<env>>/api/health` returns `{"status":"ok"}`.
- `docker compose -f docker/compose.<env>.yml --profile test run --rm tests pytest -q -m unit` passes (the tests service runs in the app network; see Networks above).
- After `docker compose down` and `up` again, the data written in the previous run is still there. This check proves persistence.
- `docker compose logs` has no tracebacks or restart loops.
