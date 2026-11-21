# Future and open items

Work that is known and deliberately not done yet. An item leaves this file when it is built, and its result is recorded in the proof log (local only, not published).

## Product
- Real AWS deployment step on `master` (today: emulator-backed only).
- Load testing level (`load`) is deferred.
- LLM-judge eval metrics are undefined (`llm-eval` says so).
- Optional: split `forge` into several plugins (core, stack, memory) if the kit grows.

## Templates and infrastructure
- MySQL 8.0 vs 8.4 image pin: still open.
- Docker `cap_add` list is marked `TODO-VERIFY` in `templates/docker/compose.stack.yml` (two places) and in `docker-prod`.
- The release environment's AWS emulator image is pinned by a real digest on the demo's release branch, but the master branch of the demo still had a placeholder digest when last checked. Verify before the next master promotion.
- Generated templates have been run on a demonstration project only, not on a real application.

## Verification gaps
- Hotfix flow end to end: needs a real production defect to run against.
- `adopt-project` steps 4+ (one pull request per gap): the pull request step is unverified because no GitHub remote was used.
- Auto-update setting (`autoUpdate`): checked against the documentation only, not observed in a live Claude Code session.
- The demonstration project has no end-to-end test suite, so the QA gate passes with a warning.

## Security and CI
- CodeQL in CI.
- Security findings from the demonstration project (base image tag pinning, unauthenticated `/health` detail) were accepted without recording waivers. Record them or fix them.

## Done since the last update
- Update notice: implemented as a `SessionStart` notice in `scripts/kit_pull.py`. It never installs.
- LICENSE: MIT, present.
