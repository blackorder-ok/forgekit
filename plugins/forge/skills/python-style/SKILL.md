---
name: python-style
description: Your Python conventions for all code and tests, such as naming, logging, structure, forbidden patterns and tooling. Use when writing, reviewing or refactoring Python.
pack: stack
---

# Python style (Python 3.11)

## Naming
Files `snake_case.py` · functions, methods, variables `camelCase` · classes `PascalCase` · constants `UPPER_SNAKE` · tests `test_<unit>_<behaviour>`.

## Logging
Top of every module `logger = LoggingHandler().getLogs()`. Messages start with a tag: `[LLM] ...`, `[UTILS][CONFIG] ...`. Log lengths and ids, never prompts, bodies or secrets.

## Structure
Shared services (config, logging) are singletons via `SingletonMetaClass`. Type hints on all public functions and attributes; a one-line docstring on public functions and classes. A usecase is a class with `createPromptMessage`, `modelRequest`, `execute`.

## Forbidden
Hardcoded keys, passwords, models, endpoints or paths (use `config-db`). `@lru_cache` on instance methods. Bare `except:`. Silent defaults for secrets or endpoints (raise `ValueError` naming the key). Modules over 300 lines, functions over 40.

## Tools
`ruff` format and lint, `mypy` strict, `pytest`. Dependencies via `dependency-policy`. Settings live in `pytest.ini`, `ruff.toml`, `mypy.ini`; no `pyproject.toml` unless packaging needs it.

Layered style: this kit default < your `~/.kit/style.md` (from `/forge:learn-style`) < the project's `.claude/style.local.md`. The closer file wins.

Generated `ruff.toml` and `mypy.ini` blocks: `references/generated-configs.md`.
