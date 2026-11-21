---
name: python-style
description: Your Python conventions for all code and tests, such as naming, logging, structure, forbidden patterns and tooling. Use when writing, reviewing or refactoring Python.
pack: stack
---

# Python style (Python 3.11)

## Naming
File names `snake_case` (every file, scripts and hooks too) · functions, methods, variables `camelCase` · classes, interfaces, enums, type aliases `PascalCase` · constants and module-level (global) variables `SCREAMING_SNAKE_CASE` · tests `test_<unit>_<behaviour>`. FastAPI instance `APP`, routers `ROUTER`. Exempt: `pytestmark`, Alembic revision names.

## Logging
Top of every module `LOGGER = LoggingHandler().getLogs()`. Messages start with a tag: `[LLM] ...`, `[UTILS][CONFIG] ...`. Log lengths and ids, never prompts, bodies or secrets.

## Structure
Shared services (config, logging) are singletons via `SingletonMetaClass`. Type hints on all public functions and attributes; a one-line docstring on public functions and classes. A usecase is a class with `createPromptMessage`, `modelRequest`, `execute`.

## Forbidden
Hardcoded keys, passwords, models, endpoints or paths (use `config-db`). `@lru_cache` on instance methods. Bare `except:`. Silent defaults for secrets or endpoints (raise `ValueError` naming the key). Modules over 300 lines, functions over 40.

## Tools
`ruff` format and lint, `mypy` strict, `pytest`. Dependencies via `dependency-policy`. Settings live in `pytest.ini`, `ruff.toml`, `mypy.ini`; no `pyproject.toml` unless packaging needs it.

Layered style: this kit default < your `~/.kit/style.md` (from `/forge:learn-style`) < the project's `.claude/style.local.md`. The closer file wins.

Generated `ruff.toml` and `mypy.ini` blocks: `references/generated-configs.md`.
