---
name: dependency-policy
description: Rules for adding, pinning, updating and removing dependencies, plus Dependabot setup. Use when adding a package, reviewing a dependency PR or answering a vulnerability advisory.
pack: core
---

# Dependency policy

## Pinning
Direct dependencies in `backend/requirements.in` and `requirements-dev.in`. Compiled `.txt` files pin everything with hashes (`pip-compile --generate-hashes` or `uv pip compile`). Commit both. Install only with `--require-hashes`. Python 3.11. Docker base images pinned by tag, by digest once live.

## Adding
Record in the PR: why stdlib or an existing dependency is not enough; licence (MIT, BSD, Apache-2.0, PSF, ISC allowed, others need a person); maintenance (release within 12 months, no open advisory); transitive footprint (`pipdeptree`).

## Updating
Dependabot weekly, minor and patch grouped. Patch merges when `verify` is green and the changelog was read. Minor needs a reviewer. Major needs a person and a note. A PR that changes only `.txt` is re-compiled from the `.in`; if the result differs, close it.

## Vulnerabilities
`pip-audit` blocks the merge. High within 7 days, medium within 30. No fix available: waive under `security-waivers`. A vulnerable GitHub Action is replaced, not waived.

## Reviewer checks
No dependency without justification. No `.txt` change without its `.in` or a Dependabot update. No unpinned package in a Dockerfile or workflow.

The `dependabot.yml` and `.gitattributes` blocks scaffold writes are in `references/full-rules.md`.
