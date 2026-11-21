<!-- Reference for the release-standards skill. Ported from setting-up-claude/branch-flow (v0.1.0); read only when the digest is not enough. -->

# Branch flow

## Branches and environments

| Branch | Environment | the AWS emulator port | Purpose |
|---|---|---|---|
| `develop` | develop | 4566 | Daily development. Default branch. |
| `qa` | qa | 4567 | Quality testing. |
| `release` | release | 4568 | UAT and release candidate. |
| `master` | production | 4569 | Production. AWS-emulator-backed until real AWS is set up. |
| `feature/<name>` | none | none | One feature, cut from `develop`. |

## Promotion
- Order: `feature/*` → `develop` → `qa` → `release` → `master`.
- Every step is a pull request. No direct pushes to `qa`, `release`, or `master`.
- Merge with merge commits, not squash, so promotion history stays visible.
- Each step reruns the checks on the source branch's commit.
- `master` needs a manual approval, enforced by the GitHub environment rule.
- Keep `develop` ahead of the others. If a fix lands on `qa` only, merge it back to `develop` straight away.

## Agent rules
- Read the current branch with `git branch --show-current` before any work.
- Allowed to edit: `develop` and `feature/*`.
- Stop and report on `qa`, `release`, `master`, or a detached HEAD.
- A feature branch changes only its own feature's files. Changes to `config/application-qa.properties`, `config/application-release.properties`, or `config/application-master.properties` need a design approval that names them.
- Name the branch in every design doc and every commit message scope.

## Not yet in scope
- Hotfix branches. Add when the main flow works end to end.
