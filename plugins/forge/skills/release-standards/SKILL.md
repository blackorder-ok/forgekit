---
name: release-standards
description: Branch flow, versioning, commit and changelog rules, tags, rollback and back-merge. Use when promoting, committing, cutting a release or rolling back.
pack: core
---

# Release standards and branch flow

## Branches
`feature/*` → `develop` → `qa` → `release` → `master` (production). `hotfix/*` is cut from `master` and merged to `master` and `develop`. Every step is a PR with merge commits, no squash. `master` needs a reviewer on its GitHub environment. Keep `develop` ahead: merge a fix landed on `qa` back at once.

## Who may edit
Only `develop`, `feature/*`, `hotfix/*`. Stop on `qa`, `release`, `master` or a detached HEAD. Read `git branch --show-current` before any work.

## Versioning and commits
- SemVer. PATCH fixes, MINOR features, MAJOR breaking. Before 1.0 a breaking change bumps MINOR with a `BREAKING` label.
- Conventional commits `type(scope): subject`, imperative, at most 72 chars. Types: feat, fix, perf, security, refactor, test, docs, build, ci, chore. `!` marks a breaking change.

## Changelog
Keep a Changelog. Entries under `## [Unreleased]` in Added, Changed, Fixed, Security, Removed, each naming the feature id. A release moves it to a dated version section.

## Release
`/forge:promote release master`, reviewer approves, merge, then `/forge:release tag X.Y.Z` tags the merge commit. Tags are annotated, on `master` only, never moved or deleted. A bad release gets a new patch. No release without a changelog section or a `GREEN` `/forge:check master`.

## Rollback
Deploy the previous tag's image; never rewrite history. A migration that cannot be reversed must be stated in the release notes with a plan.

References: `references/full-rules.md`, `references/branch-flow.md` (branch and port table).
