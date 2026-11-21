# Future and open items

Carried over from setting-up-claude, plus new ones.

- Real AWS deployment step on `master` (today: emulator-backed).
- Load testing level (`load`) is deferred.
- LLM-judge eval metrics are undefined (`llm-eval` says so).
- CodeQL in CI.
- MySQL 8.0 vs 8.4 pin: still open.
- Docker `cap_add` list is marked `TODO-VERIFY` in `docker-prod` templates.
- Templates (Dockerfiles, compose, CI) were carried over unchanged and have not been run in this build.
- Optional: split `forge` into several plugins (core, stack, memory) if the kit grows.
- Optional: periodic "new tag available" notice (kept manual on purpose).
- Add a LICENSE before making the repo public.
