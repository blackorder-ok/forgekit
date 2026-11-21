---
description: Preflight check before any feature, release, or stack run. Confirms the tools and, with `stack`, the running services the other commands need.
argument-hint: [stack]
---

Run the checks in order. Do not change any file. Use only commands that work on Windows, macOS, and Linux. Argument `$ARGUMENTS`: empty runs the tool checks (1, 2, 5, 6, 7, 8); `stack` adds the running-service checks (3, 4).

1. `docker info` succeeds (Docker daemon running). FAIL: start Docker, then rerun once.
2. `docker compose version` prints a version.
3. (stack) The AWS emulator is healthy for this branch's environment. It sits on an internal-only network, so its port is not reachable from the host: do not curl localhost. Run `docker compose -f docker/compose.<env>.yml ps aws-emulator --format "{{.Health}}"` and expect `healthy`. FAIL: run `docker compose -f docker/compose.<env>.yml up -d aws-emulator`, wait 15 s, rerun once.
4. (stack) Ollama inside the app container (develop only). Run `docker compose -f docker/compose.develop.yml exec app curl -fsS http://127.0.0.1:11434/api/tags`. Expect a JSON reply. FAIL: run `docker compose -f docker/compose.develop.yml logs app`, then rerun once. Before the first feature exists there is no `app` image: report `n/a (no app yet)` instead of FAIL.
5. `git --version` prints a version, and `git branch --show-current` prints the branch.
6. `gh --version` and `gh auth status` succeed. Required for `/forge:promote` and `/forge:release` only.
7. Credentials present for the branch's environment. The file is git-ignored, so do not use Glob or a directory listing; run `test -f secrets/application-<env>-secrets.properties && echo present`. Report the path only, never its contents.
8. Python: `python --version` is 3.11.x.

Read `<env>` from the branch (`develop`, `qa`, `release`, `master`; `feature/*` and `hotfix/*` use `develop`) and the ports and image from `docs/plan.md` only if a check needs them.

Report a table: check, PASS or FAIL, the output or the fix. Overall `READY` if every check needed by the next command passes, otherwise `NOT READY` with the first blocking check.

## On failure
- Transient failure (Docker or the AWS emulator still starting): retry that one check once after 15 seconds.
- Any other failure: report `NOT READY` and stop. Do not start the next command.
