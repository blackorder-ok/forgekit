---
name: project-plan
description: Plan file format, team defaults, validation checklist and feature order for a new or adopted project. Use when planning, or when a command must validate a plan.
pack: core
---

# Project plan

The plan is `./<project>.plan.md`: YAML front matter, then 8 body sections. It holds no code and creates no folder, repo or branch. `/forge:scaffold-project` reads it as data.

## Front matter keys (all required unless noted)
`project` (kebab-case) · `mode: new|existing` · `summary` · `owner` · `python` · `stack` (5 keys, only for `existing`) · `environments: [develop, qa, release, master]` · `branches` · `aws_emulator` (pinned image, one port per env) · `app_ports` (one per env) · `database` · `vector_store` · `llm` (token budget per env) · `eval` (if any feature uses the `llm` test level) · `aws_services` · `track: quick|standard|full` (set by `/forge:route`) · `features[]` (`id`, `name`, `goal`, `depends_on`, `environments`, `touches`, `tests`).

## Body sections, in order
Goal · Users · Scope · Non-goals · Data model (mark personal data per entity) · Features in build order · Security and data · Open decisions (each `deferred` with a reason, or resolved).

## Defaults (override only with a recorded reason)
Branches `develop → qa → release → master`. MySQL inside the app container. Pinecone, one index per env, named `<project>-<env>`. AWS emulated. Ollama in develop only. Foundation feature F01 first: config loader, DB and migrations, `VectorStore` with a fake, `/health`, one test per enabled level.

## Validation (a plan passes only if all hold)
- Required keys present, types right, `mode` valid, `stack` complete for `existing`.
- `project` is kebab-case; for `new`, no such folder exists.
- Environments are exactly the four. Ports unique. Emulator image pinned by tag and digest.
- `vector_store.index_per_env` contains `<env>`. Every token budget is positive.
- Feature ids unique; each `depends_on` points to an earlier id; no cycles.
- Open decisions are all `deferred` or resolved.
Report failures as a list. Never write a plan as valid with failures.

## Rules
Ask only for facts the idea does not give. Do not design modules here; `/forge:design` does that per feature.

Full format with every field: `references/plan-format.md`.
