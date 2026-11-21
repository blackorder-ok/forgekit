---
description: Bring an existing repository under the kit without rewriting it. Survey it read-only, write docs/plan.md from what it really uses, report the gaps against kit standards, then add missing pieces one small pull request each.
argument-hint: <path to the existing repository>
---

Project: $ARGUMENTS

## Preconditions
- The path is a git repository with a clean working tree. If not, stop and report it.
- Run `git branch --show-current`. Work on a new branch `kit/adopt` cut from the current branch. Never edit the current branch directly.
- Check only the tools: `git --version`, `python --version` (3.11.x). Do not run `/forge:doctor`: its environment checks assume a kit-scaffolded stack and would start containers in a repo that has none. Missing tool stops the run.

## Steps

1. **Survey, read-only.** Read at most 25 files. Cover languages, frameworks, entry points, test setup, CI, Docker, database, branches, and existing docs. List the files you did not read.

2. **Plan from reality.** Write `docs/plan.md` with `mode: existing` and a `stack:` block (language, framework, database, test runner, CI). Every field the kit would default is filled with what the project actually uses. Validate it with `project-plan`, skipping only the "folder must not exist" check.

3. **Gap report.** For each area, mark it present, partial, or missing, and name the smallest change that closes it:
   - branch flow (`release-standards`)
   - tests and test levels (`test-levels`)
   - CI and security scans (`ci-pipeline`)
   - waivers (`security-waivers`)
   - release flow (`release-standards`)
   - enforcement files (`templates/project/`)
   Write this list to the reply and to `docs/adoption-gaps.md`.

4. **Close gaps, one pull request each.** Order: `.claude/settings.json` and hooks first, then CI checks, then baseline tests. Each change is its own commit on its own branch `kit/<gap>`. Never rewrite working code or working config. If a gap needs a rewrite, list it as a gap and do not do it.

5. **Stop for review.** Tell the user the branches and what each one changes. Do not merge.

6. **After adoption.** `/forge:design`, `/forge:feature`, and `/forge:fix` work as usual on the adopted project.

## Done when
`docs/plan.md` and `docs/adoption-gaps.md` exist on `kit/adopt`. Each gap is closed by its own branch or listed as open with the reason. Nothing else changed.

## On failure
- Dirty working tree or not a git repository: stop. Nothing is changed.
- A survey file cannot be read: list it and continue.
- A gap fix breaks an existing check: drop that branch, keep the gap listed, and report the output.
