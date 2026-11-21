<!-- Reference for the release-standards skill. Ported from setting-up-claude/release-standards (v0.1.0); read only when the digest is not enough. -->

# Release standards

## Versioning
- Semantic versioning: `MAJOR.MINOR.PATCH`.
- `PATCH`: fixes only. `MINOR`: new features, backward compatible. `MAJOR`: breaking changes to the API, config keys, or data.
- Before `1.0.0`, a breaking change bumps `MINOR` and is listed under `Changed` with a `BREAKING` label.

## Commit messages
- Conventional commits: `type(scope): subject`, subject in the imperative, at most 72 characters. A subject may start with a digit, as in the release commit `chore(release): 1.2.0`.
- Types: `feat`, `fix`, `perf`, `security`, `refactor`, `test`, `docs`, `build`, `ci`, `chore`.
- A breaking change has `!` after the type and a `BREAKING CHANGE:` line in the body.
- Commits that change behaviour use `feat`, `fix`, `perf`, or `security`. Those appear in the changelog. Others do not.

## Changelog
- `CHANGELOG.md` follows Keep a Changelog.
- Each unreleased change is added under `## [Unreleased]`, in the section that matches its type: `Added`, `Changed`, `Fixed`, `Security`, `Removed`.
- Every entry names the feature id from the plan, when there is one.
- A release moves `Unreleased` to a dated `## [X.Y.Z] - YYYY-MM-DD` section, and adds a new empty `Unreleased`.

## Release flow
1. Changes reach `release` through `/promote qa release`, and UAT signs off on `release`.
2. `/promote release master` opens the pull request. A reviewer on the `master` environment approves it.
3. After the merge, `/release <version>` runs on `master`. It tags the merge commit `vX.Y.Z` and writes the release notes from the changelog section.
4. The `master` image is tagged twice: `app-api:master-<sha>` and `app-api:vX.Y.Z`.
5. `master` merges back into `develop`, so `develop` contains the release commits.

## Rules
- Tags are annotated and point at a commit on `master`. A tag on any other branch is invalid.
- A tag is never moved or deleted. A bad release gets a new patch version.
- No release without a changelog section for that version.
- No release while `/check master` is not `GREEN`.

## Rollback
- Rollback means deploying the previous tag's image. The previous version is the one before the tag being rolled back.
- The steps are in `docs/runbook.md`. A rollback does not rewrite git history.
- Database migrations are not reversed automatically. A migration that cannot be reversed must be stated in the release notes, with the rollback plan.
