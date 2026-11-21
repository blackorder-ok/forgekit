# {{PROJECT}}

Production-grade app built with forgekit. Read `docs/plan.md` for scope; `.claude/constitution.md` for hard rules.

## Working rules (Karpathy's four)
1. **Think first.** State assumptions. Two readings of a request: say so and ask. Never pick silently.
2. **Simplest thing that works.** No speculative features, one-use abstractions, or handling of impossible cases.
3. **Surgical changes.** Every changed line traces to the request. Do not touch neighbouring code. Mention unrelated dead code, do not delete it.
4. **Goal-driven.** Write the check that proves success first, then loop until it passes.

## Token rules
- Read only the files you need; prefer `rg`/`grep` over opening whole files.
- Reports under 40 lines. No recap of steps, no restating the request.
- Memory: the session start shows a short index. Use `/forge:mem search <words>` then `/forge:mem show <id>` before re-deriving a known fix.

## Branches
`feature/*` → `develop` → `qa` → `release` → `master`. Edit only on `develop`, `feature/*`, `hotfix/*`. Never push to `qa`, `release`, `master`; open a PR.

## Commands
`/forge:route <task>` picks a track · `/forge:design` · `/forge:feature` · `/forge:fix` · `/forge:check <env>` · `/forge:review` · `/forge:promote`.

## Style
Python 3.11, camelCase functions, `LoggingHandler().getLogs()`, config only via the loader. Details: skill `python-style`. Personal overrides: `.claude/style.local.md`.

## Project memory
`.claude/memory/` (typed: gotcha, fix, decision, preference). Project lessons stay here and never go to the kit.
