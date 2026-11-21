---
description: Scaffold a new project skeleton from a validated plan. Copies the kept Docker, CI and root templates, generates config, pytest, lint and dependency files from the skills, and makes the first commit. Application code (F01) is built afterwards with /feature.
argument-hint: <path to <project>.plan.md, or the project name>
---

Plan: $ARGUMENTS

## Preconditions
- Resolve the plan. If the argument ends in `.plan.md`, use that path. Otherwise use `./<name>.plan.md`. If it doesn't exist, stop and say to run `/forge:plan-project` first.
- The plan must have `mode: new`. For `mode: existing`, stop and say to use `/forge:adopt-project`.
- Validate the plan with the checklist in the `project-plan` skill. Any failure: stop and list the failures.
- No open decision may be unresolved. A `deferred` decision is allowed.
- The folder named by the plan's `project` field must not exist in the parent folder.
- `git`, Python 3.11, and `docker` must be installed. If one is missing, stop and name it.

Read the plan once and use its values everywhere below. Never guess a value the plan does not give.

## Templates and placeholders
Copy from the plugin's `templates/` folder (`${CLAUDE_PLUGIN_ROOT}/templates/`) and replace only these placeholders, which are the complete list: `{{PROJECT}}`, `{{ENV}}`, `{{AWS_EMULATOR_IMAGE}}`, `{{AWS_EMULATOR_PORT}}`, `{{APP_PORT}}`. Do not rewrite a template's content.

Kept templates: `docker/app.Dockerfile`, `backend.Dockerfile`, `frontend.Dockerfile`, `compose.stack.yml`, `entrypoint.sh`, `nginx.conf`, `supervisord.conf`, `ci/ci.yml`, `ci/env-tests.yml`, `root/.gitignore`, `root/.dockerignore`.

## Steps

1. **Repo.** Create the project folder, `cd` into it, run `git init -b develop`, and move the plan to `docs/plan.md`. Do not commit yet.

2. **Root and generated files.**
   - Copy `root/.gitignore` and `root/.dockerignore`.
   - Write `pytest.ini`, `ruff.toml`, `mypy.ini` from `test-levels` and `python-style`.
   - Write `.gitattributes` and `.github/dependabot.yml` from `dependency-policy`. Drop the `frontend` entry if the plan has no page.
   - Copy `templates/project/settings.json` to `.claude/settings.json` and `templates/project/hooks/*` to `scripts/hooks/`. Copy `templates/project/CLAUDE.md` (replace `{{PROJECT}}`) to `CLAUDE.md` and `templates/project/constitution.md` to `.claude/constitution.md`. Create `.claude/memory/` with a `.gitkeep`.

3. **Config and secrets.** Write `config/application.properties`, `config/application-<env>.properties` for each environment, and `secrets/application-<env>-secrets.properties.example`, all from the key list in `config-db`. Fill values from the plan. Add `llm.baseUrl` from the plan.

4. **Docker.**
   - Copy `docker/app.Dockerfile`, `backend.Dockerfile`, `entrypoint.sh`, `nginx.conf`, `supervisord.conf` to `docker/`.
   - Render `compose.stack.yml` to `docker/compose.<env>.yml` for each environment. Fill `{{AWS_EMULATOR_IMAGE}}` from `aws_emulator.image` and `{{AWS_EMULATOR_PORT}}` from `aws_emulator.ports.<env>`, and `{{APP_PORT}}` from `app_ports.<env>`. Stop if `aws_emulator.image` is missing or uses `latest`.
   - If the plan has a page: copy `docker/frontend.Dockerfile` and keep the `frontend` service. Otherwise delete the `frontend` service from each compose file, and remove the `FRONTEND_IMAGE` build arg and the frontend stage from `app.Dockerfile`.

5. **CI.** Copy `ci/ci.yml` and `ci/env-tests.yml` to `.github/workflows/`. Do not edit them.

6. **Frontend.** Only if the plan has a page: apply the `frontend` skill to create `frontend/` with its scripts (`typecheck`, `test`, `build`, `gen:api`) that `ci.yml` calls. Nothing else is created here.

7. **Docs.**
   - `docs/branching.md` from `release-standards`. `docs/testing.md` from `test-levels`.
   - `docs/design/.gitkeep`. `docs/security-waivers.md` with `waivers: []`.
   - `docs/runbook.md`: deploy, rollback (see `release-standards`), secret rotation, resetting the MySQL volume and the AWS emulator state, the data-persistence check from `docker-prod`, and a scheduled `mysqldump` for `master` with a restore test at `release`.
   - `CHANGELOG.md` with the Keep a Changelog header and an empty `## [Unreleased]`.
   - `evals/cases.jsonl` (empty) and `evals/baseline.json` (`{}`). `release-notes/.gitkeep`.
   - `README.md`: summary from the plan, the four branches, the run command per environment, the app at `http://localhost:<app_ports.develop>` and its API docs at `/api/docs`.

8. **Commit on develop.** Stage all files and commit `chore: scaffold project skeleton`, with the attribution lines from the system instructions. Create `qa`, `release`, and `master` from `develop` at this commit.

9. **Hand off to F01.** The backend is not part of the skeleton. The first feature, F01 (`project-plan`), is built with `/forge:design F01` and then `/forge:feature F01`. Its final gate runs `/forge:check develop`, which replaces a scaffold-time stack check. Do not run `/forge:check` before F01 exists.

10. **GitHub setup (each sub-step needs its own yes from the user).**
    - **a. Repository and remote:** ask where the project goes: a new private repository under the user's account, or an existing URL. Never make a repository public without an explicit request. Before any public repo, check `git ls-files` and `git grep` for real keys or filled secret values.
    - **b. Protection and environments:** create the four GitHub environments, apply branch protection to `qa`, `release`, and `master`, and add the user as reviewer on `master`. These hold no secret values.
    - **c. Secrets:** set `CP_SECRETS` per environment from the local secrets files. Only after the user confirms it for that repository, naming the repository and each environment. Never in the same step as (a) or (b).
    - Push all four branches only after (a) is done and the user says so.

11. **Print the manual steps.** Tell the user to:
    - Create the Pinecone account and one index per environment, named as in `config/application-<env>.properties`.
    - Create `secrets/application-<env>-secrets.properties` locally from its `.example` file.
    - Set the GitHub items from step 10 when ready.

## Done when
The folder has four branches, the plan is at `docs/plan.md`, the skeleton is committed on `develop`, and the manual steps are printed. Compose files pass `docker compose -f docker/compose.develop.yml config`.

## On failure
- Plan not found or not validated: stop. Run `/forge:plan-project` first.
- The project folder already exists: stop and report it. Never overwrite a project folder.
- A placeholder has no value in the plan: stop and name it.
