---
description: Preflight check before any feature, release, or stack run. Confirms the tools and services the other commands need.
argument-hint: (none)
---

Run every check in order. Do not change any file. Use only commands that work on Windows, macOS, and Linux.

1. `docker info` succeeds (Docker daemon running). FAIL: start Docker, then rerun once.
2. `docker compose version` prints a version.
3. the AWS emulator answers for this branch's environment. Read the port from `aws_emulator.ports` for the environment in `docs/plan.md`. Run `curl -s -o /dev/null -w "%{http_code}" http://localhost:<port>/` and expect 200 or 204. FAIL: run `docker compose -f docker/compose.<env>.yml up -d aws-emulator`, wait 15 s, rerun once.
4. Ollama inside the app container (develop only). Run `docker compose -f docker/compose.develop.yml exec app curl -fsS http://127.0.0.1:11434/api/tags`. Expect a JSON reply. FAIL: run `docker compose -f docker/compose.develop.yml logs app`, check the ollama program, then rerun once.
5. `git --version` prints a version, and `git branch --show-current` prints the branch.
6. `gh --version` and `gh auth status` succeed. Required for `/forge:promote` and `/forge:release` only.
7. Credentials present for the branch's environment: `secrets/application-<env>-secrets.properties` exists. Report the path only, never its contents.
8. Python: `python --version` is 3.11.x.

Report a table: check, PASS or FAIL, the output or the fix. Overall `READY` if every check needed by the next command passes, otherwise `NOT READY` with the first blocking check.

## On failure
- Transient failure (Docker or the AWS emulator still starting): retry that one check once after 15 seconds.
- Any other failure: report `NOT READY` and stop. Do not start the next command.
