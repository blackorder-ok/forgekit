---
description: Prepare a release from master as a version branch and pull request, then tag the merged commit after the PR is merged.
argument-hint: <version, for example 1.2.0>  or  tag <version>  (after the PR is merged)
---

Request: $ARGUMENTS

## Mode 1: prepare (`/forge:release X.Y.Z`)
Stop if the version is not `X.Y.Z`.

Preconditions (all must hold, or stop before any change):
- `/forge:doctor` is `READY`.
- The working tree is clean, and `master` matches `origin/master`.
- The tag `vX.Y.Z` does not exist, locally or on the remote.
- `CHANGELOG.md` has entries under `## [Unreleased]`.
- `/forge:check master` is `GREEN`.

Steps:
1. `git switch -c version/vX.Y.Z master`. The name `version/*` is used because `release` is already a branch.
2. Move `## [Unreleased]` to `## [X.Y.Z] - <today>`, and add an empty `## [Unreleased]` above it. Commit `chore(release): X.Y.Z`.
3. Write `release-notes/vX.Y.Z.md`, copied from the new changelog section. Commit it.
4. Push the branch and open the pull request: `gh pr create --base master --head version/vX.Y.Z --title "release: vX.Y.Z"`. The body lists the changelog section and the `/forge:check master` result.
5. Report the PR link. Stop. A person merges it after the `master` reviewer approves.

## Mode 2: tag (`/forge:release tag X.Y.Z`)
Run only after the PR is merged.
1. `git switch master && git pull --ff-only`. The merge commit must include `chore(release): X.Y.Z`. Otherwise stop.
2. Create an annotated tag on that commit: `git tag -a vX.Y.Z -m "Release X.Y.Z"`.
3. Print `git push origin vX.Y.Z` and `git switch develop && git merge master`. Run neither.

## On failure
- Any precondition fails: stop before any change and say which one.
- Tag already exists: stop. Never move or delete a tag.
- Push or PR creation fails: stop, report the output, and leave the branch in place.
- Mode 2 and the merge commit is missing: stop. Do not tag an unmerged commit.
