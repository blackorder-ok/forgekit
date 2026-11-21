# forgekit

[![kit-ci](https://github.com/blackorder-ok/forgekit/actions/workflows/kit-ci.yml/badge.svg)](https://github.com/blackorder-ok/forgekit/actions/workflows/kit-ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
![Python 3.11](https://img.shields.io/badge/python-3.11-3776AB.svg)
![Claude Code plugin](https://img.shields.io/badge/Claude%20Code-plugin-6B4FBB.svg)

**forgekit** is a Claude Code plugin that plans, scaffolds, builds, reviews and ships production-grade Python/FastAPI applications. It enforces one delivery path, from idea to tagged release, with explicit approval gates, and keeps the token cost of each step low.

The plugin is named **`forge`**. It is distributed through a marketplace named **`forgekit`**. Every command is namespaced: `/forge:<name>`.

| | |
|---|---|
| **Current version** | 0.4.0 (tag `v0.4.0`) |
| **Plugin** | `plugins/forge` |
| **Requires** | Claude Code, Git, Python 3.11, Docker (for generated projects) |
| **Licence** | MIT |
| **Proof record** | [docs/PROOF_LOG.md](docs/PROOF_LOG.md) |

---

## Contents

- [Why forgekit](#why-forgekit)
- [Features](#features)
- [Quick start](#quick-start)
- [Installation](#installation)
- [Usage](#usage)
- [Workflows](#workflows)
- [Architecture](#architecture)
- [Configuration](#configuration)
- [Guardrails](#guardrails)
- [Memory and token budget](#memory-and-token-budget)
- [Development](#development)
- [Updating and versioning](#updating-and-versioning)
- [Status and known limits](#status-and-known-limits)
- [Contributing](#contributing)
- [Licence](#licence)

---

## Why forgekit

Most AI coding setups fail in one of three ways: they skip planning, they let the model edit production branches, or they load so much context that every step is slow and expensive. forgekit addresses each one directly.

- **A defined path.** Work moves through plan → design → failing tests → implementation → review → gate → release. Each stage has a command, a stop rule and a "done when" test.
- **Guardrails that bite.** Hooks block edits on protected branches, block test edits that remove assertions, and stop oversized fixes. Production branches are changed only through pull requests.
- **Low token cost.** Agents preload short rule digests; long detail is read only when needed. A CI check fails the build if any file grows past its budget.
- **Your style, not a generic one.** A `learn-style` command samples your own code (counts only) and saves a personal style profile outside the repository.

## Features

| Area | What you get |
|---|---|
| Planning | `plan-project` turns an idea into a validated plan file with at most four open questions. |
| Scaffolding | `scaffold-project` generates a complete project: Docker, CI, four environment branches, config, docs, hooks, and Claude instructions. |
| Existing code | `adopt-project` surveys a repository read-only, writes a plan from what it really uses, and closes gaps one small branch at a time. |
| Building | `design`, `feature`, `converge`, `fix` and `hotfix` implement changes test-first, within a diff budget. |
| Quality | `review`, `security-review`, `eval` and `check` return explicit verdicts (`APPROVE`, `PASS`, `GREEN`, `RED`). |
| Release | `promote` and `release` open pull requests between environments; tags are created only after a merge. |
| Memory | Layered, searchable project memory with a session-start index. |
| Kit maintenance | `kit-new`, `kit-claim`, `kit-status`, `kit-review` and `kit-pull` manage the kit itself, with approval before any write. |

## Quick start

```text
/plugin marketplace add blackorder-ok/forgekit
/plugin install forge@forgekit

/forge:route "describe what you want to do"    # pick the smallest track
/forge:doctor                                   # check tools and services
```

For a new project, continue with [Workflows](#workflows).

## Installation

### Requirements

| Requirement | Notes |
|---|---|
| Claude Code | Current version with plugin support. |
| Git | Required for branches, the kit registry and the update check. |
| Python 3.11 | On `PATH` as `python`. The kit's own scripts use only the standard library. |
| Docker | Required for generated projects. Not needed to install or use the kit's planning commands. |
| GitHub CLI (`gh`) | Required for pull requests and the GitHub steps of scaffold, promote and release. |
| Git Bash (Windows) | Required so the project hooks can run `bash`. |

### From GitHub

```text
/plugin marketplace add blackorder-ok/forgekit
/plugin install forge@forgekit
```

### From a local clone

Clone the repository, then point Claude Code at the path:

```text
/plugin marketplace add <path-to-clone>
/plugin install forge@forgekit
```

To develop the kit itself without reinstalling after each edit:

```bash
claude --plugin-dir <path-to-clone>/plugins/forge
```

Run `/reload-plugins` inside the session to pick up changes.

### Kit location for maintenance commands

Commands that manage the kit (`kit-new`, `kit-claim`, `kit-status`, `kit-pull`) need the location of your clone. Either set the environment variable `FORGE_REPO`, or write the path into `~/.kit/repo`:

```bash
mkdir -p ~/.kit
echo "<path-to-clone>" > ~/.kit/repo
```

### Validate the installation

```bash
claude plugin validate ./plugins/forge
python tools/check_kit.py
```

## Usage

### Commands

Commands are grouped by purpose. Each one states its preconditions and stops before any change if they fail.

**Start here**

| Command | Purpose |
|---|---|
| `/forge:route <task>` | Chooses the track (quick, standard or full) and names the first command. Writes nothing. |
| `/forge:doctor [stack]` | Preflight check of tools; with `stack`, also the running services. Returns `READY` or `NOT READY`. |
| `/forge:ship <idea>` | Runs the full path for a new project, stopping at each decision. |

**Plan and scaffold**

| Command | Purpose |
|---|---|
| `/forge:plan-project <idea>` | Writes `<project>.plan.md`. Creates no folder, repository or branch. |
| `/forge:scaffold-project <plan>` | Generates the project skeleton from a validated plan. Each GitHub step needs your approval. |
| `/forge:adopt-project <path>` | Brings an existing repository under the kit without rewriting working code. |

**Build**

| Command | Purpose |
|---|---|
| `/forge:design <feature>` | Writes the feature's design document and stops until it is approved. |
| `/forge:feature <feature>` | Builds an approved feature: gate, failing tests, implementation, review, security, evals where relevant, final gate, docs. Never merges. |
| `/forge:converge <feature>` | Checks that design, tests and code agree; fixes the smallest mismatch; at most two rounds. |
| `/forge:fix <bug>` | One bug on `develop` or `feature/*`: failing regression test first, one root-cause change, diff budget of 3 files and 20 lines. |
| `/forge:hotfix <bug>` | A production bug, from `master`. Prepares pull requests into `master` and `develop`. |

**Check, review and release**

| Command | Purpose |
|---|---|
| `/forge:check <env>` | Runs the devops check sequence for one environment. Returns `GREEN` or `RED`. |
| `/forge:review [feature]` | Read-only review of the current diff. Returns `APPROVE` or `CHANGES REQUIRED`. |
| `/forge:security-review [all]` | Read-only security review. Returns `PASS`, `PASS WITH FINDINGS` or `FAIL`. |
| `/forge:eval <env>` | Runs the AI eval set against thresholds and baseline. Never updates the baseline. |
| `/forge:qa <env>` | Runs end-to-end, smoke and UAT checks and writes a QA report. |
| `/forge:docs-sync` | Aligns documentation and the changelog with the branch. |
| `/forge:promote <from> <to>` | Opens a pull request between environment branches after a green check. |
| `/forge:release X.Y.Z` | Prepares a version branch and pull request from `master`. |
| `/forge:release tag X.Y.Z` | Tags the merge commit, after the release pull request is merged. |

**Memory, style and kit maintenance**

| Command | Purpose |
|---|---|
| `/forge:mem search\|show\|timeline\|add` | Searches and records project and kit memory. |
| `/forge:learn-style <folders>` | Learns your Python style from sample files and saves it to `~/.kit/style.md` after you approve. |
| `/forge:kit-status` | Read-only report of local units the kit does not know. |
| `/forge:kit-claim <kind> <name>` | Moves a local unit into the kit after a secrets scan and your approval. |
| `/forge:kit-new <kind> <name>` | Creates a new skill, agent or command in the kit repository. |
| `/forge:kit-review` | Groups lessons from the inbox and proposes global ones on a branch for approval. |
| `/forge:kit-pull` | Shows what a newer kit tag would change. Changes nothing. |

### Agents

Nine specialised agents do the focused work. Each can also be invoked on its own.

| Agent | Model | Responsibility |
|---|---|---|
| `product-owner` | sonnet | Users, acceptance criteria, up to four open questions. |
| `architect` | opus | Project plan and feature design documents. |
| `developer` | sonnet | Implementation for the backend and frontend; one-bug fixes. |
| `tester` | sonnet | Failing tests before code; regression tests; e2e, smoke and UAT runs. |
| `ops` | sonnet | Docker, CI, environment health, rollback and backup. |
| `reviewer` | sonnet | Read-only code review. |
| `security-reviewer` | sonnet | Read-only security review; waiver handling. |
| `ai-evaluator` | sonnet | Eval cases and explanations of failing runs. |
| `doc-updater` | haiku | Documentation and changelog. Never changes code. |

## Workflows

Choose a track with `/forge:route`. The track sets how much process a task receives.

| Track | For | Path |
|---|---|---|
| quick | one bug or small change | `fix` |
| standard | one feature | `design` → `feature` |
| full | a new project or subsystem | `ship` |

**New project**

```text
/forge:plan-project "your idea"
/forge:scaffold-project ./<project>.plan.md
/forge:design F01          # approve the design
/forge:feature F01
/forge:promote develop qa
```

`/forge:ship "your idea"` runs the same path and stops at each decision.

**Existing project**

```text
/forge:adopt-project <path>
```

Review the `kit/*` branches it creates, then use `design`, `feature` or `fix` as usual.

**Production release**

```text
/forge:promote qa release        # open PR, merge after review
/forge:promote release master    # open PR, merge after review
/forge:release 1.2.0             # open version PR into master, merge after review
/forge:release tag 1.2.0         # tag the merge commit
```

Merges are always performed by a person. Commands open pull requests and report them.

## Architecture

```
forgekit/                         repository (source of truth)
├── .claude-plugin/               marketplace definition
├── plugins/forge/                the plugin
│   ├── agents/                   9 agents
│   ├── commands/                 26 commands
│   ├── skills/                   14 rule digests, each with references/
│   ├── hooks/                    SessionStart hooks (memory index, update notice)
│   ├── scripts/                  memory, kit management, style sampling
│   └── templates/                files copied into generated projects
├── tools/check_kit.py            self-check: manifests, references, budgets, secrets
├── tests/test_forge.py           kit test suite
├── docs/                         supporting documents and the proof log
└── kit.json                      registry of kit units and byte budgets
```

Key design points:

- **One source of truth.** The repository is the only place kit units are edited. The installed plugin is a pinned copy.
- **Registry.** `kit.json` lists every unit that belongs to the kit. `check_kit` fails on unregistered units and on registered units missing from disk.
- **Digests and references.** Agents preload short skill digests. Full rules live in `references/` and are read on demand.
- **Generated projects.** `scaffold-project` writes byte-exact templates and generates the rest from the plan.

## Configuration

### Environments

Every generated project has four environment branches, in promotion order:

| Branch | Purpose |
|---|---|
| `develop` | Integration of feature branches. |
| `qa` | Quality assurance; end-to-end checks run here. |
| `release` | Release candidate. |
| `master` | Production. Requires an environment reviewer. |

Each environment has its own compose file, configuration, secrets file and vector-store index.

### Settings

| Setting | Where | Effect |
|---|---|---|
| `KIT_HOOKS=minimal` | environment variable | Turns off the `test_guard` and `diff_budget` hooks. `branch_guard` always stays on. |
| `FORGE_HOME` | environment variable | Location of the kit's personal data (default `~/.kit`). |
| `FORGE_REPO` | environment variable | Location of the kit repository for maintenance commands. |
| `~/.kit/style.md` | file, outside any repo | Your personal Python style profile. |
| `.claude/style.local.md` | file, in a project | Project-specific style overrides. |
| `~/.kit/local-ignore` | file, outside any repo | Local units the kit should ignore. |

### Secrets

Real secrets files (`secrets/application-<env>-secrets.properties`) are git-ignored and never committed. Only the `.example` templates, which contain key names and no values, are committed. The project's `settings.json` denies reads of the real files.

## Guardrails

Generated projects receive three hooks, wired through `.claude/settings.json`:

| Hook | When it runs | What it blocks |
|---|---|---|
| `branch_guard.sh` | Before each edit | Edits on `qa`, `release`, `master` or a detached HEAD. |
| `test_guard.py` | Before each edit to `tests/` | Edits that remove assertions or add skip markers. |
| `diff_budget.sh` | When a fix finishes | Fixes that change more than 3 files or 20 lines. |

Each block adds one line to the lesson inbox (`~/.kit/inbox`), which `/forge:kit-review` reads later.

The plugin itself adds two `SessionStart` hooks: one prints the memory index, the other checks for a newer kit tag and prints one line if there is one. Neither installs anything.

## Memory and token budget

Memory is layered so that only the cheapest layer loads by default:

| Layer | Content | Loaded |
|---|---|---|
| L0 | `CLAUDE.md` and the constitution | Always. Kept short. |
| L1 | Memory index: ids and titles | At session start, capped near 500 tokens. |
| L2 | One memory entry, or a skill reference | On demand. |
| L3 | Git history | Never by default. |

Entry types are `gotcha`, `fix`, `decision` and `preference`. Titles are short; bodies are capped.

Budgets are enforced in CI. `python tools/check_kit.py --tokens` fails if a skill exceeds 2.5 KB, an agent exceeds 3 KB, or a command exceeds 3.8 KB (with one documented exception for `scaffold-project`). The current per-agent preload sizes are in [docs/BASELINE.md](docs/BASELINE.md).

## Development

### Set up

```bash
git clone https://github.com/blackorder-ok/forgekit.git
cd forgekit
python -m pip install pytest
```

### Checks

```bash
python tools/check_kit.py --tokens          # structure, rules, budgets
python -m pytest tests -q                   # 35 tests
claude plugin validate ./plugins/forge      # plugin manifest
```

Expected results: `check_kit: OK`, `35 passed`.

Continuous integration runs the first two on every push and pull request ([`.github/workflows/kit-ci.yml`](.github/workflows/kit-ci.yml)).

### Adding a unit

```text
/forge:kit-new skill <name>      # or agent, command
```

This creates the file from a template inside the repository and registers it in `kit.json`. Then:

1. Fill it in and keep it within its byte budget; put detail in `references/`.
2. Run the checks above.
3. Add a changelog entry.

To add a unit that was first made in `~/.claude`, use `/forge:kit-status` and then `/forge:kit-claim`.

### Repository conventions

- Python in generated projects follows snake_case files, camelCase functions, PascalCase classes and SCREAMING_SNAKE constants.
- Most folders have a guide (`*_GUIDE.md`) that describes its contents and how to change them. Start with the guide in the folder you are editing.

## Updating and versioning

Versions follow Semantic Versioning. The version is recorded in three places that must agree: `kit.json`, `plugins/forge/.claude-plugin/plugin.json`, and the top entry of `CHANGELOG.md`.

Installed plugins do not update automatically. To update:

1. Run `/forge:kit-pull` to see what changed. It changes nothing.
2. After you agree, run `/plugin marketplace update forgekit`, then `/plugin update forge@forgekit`.

To roll back, install the previous tag from the clone (`git checkout v0.3.1`) and update the marketplace again.

Release notes are in [CHANGELOG.md](CHANGELOG.md).

## Status and known limits

forgekit is pre-1.0. Its behaviour is tested, and its commands have been run against a demonstration project. Status by area:

| Area | Status |
|---|---|
| Kit self-check and unit tests | Passing. |
| Plugin install from a marketplace | Verified. |
| Scaffolding, planning, feature build and check on a demonstration project | Verified. |
| Promotion between `develop`, `qa` and `release` | Verified. |
| Release preparation and tagging | Partly verified; the release pull request was opened. |
| Hotfix end to end | Not run; it needs a real production defect. |
| Adopting an existing repository | Steps up to the gap list verified; pull request creation not verified. |
| Auto-update | Setting checked against the documentation; not observed in a live session. |

Known limits:

- Commands that need GitHub (pull requests, tags) depend on `gh` being authenticated.
- The generated Docker and compose templates were verified on one machine; `cap_add` items are marked `TODO-VERIFY` ([docs/FUTURE.md](docs/FUTURE.md)).
- Generated projects with no end-to-end tests pass the QA gate with a warning, not a failure.
- LLM-judge evaluation metrics are not defined yet.
- Load testing and a real AWS deployment step are deferred.

The full record of what was run, what failed and what was waived is in [docs/PROOF_LOG.md](docs/PROOF_LOG.md).

## Contributing

Contributions are welcome. Before opening a pull request:

1. Run the checks in [Development](#development). All must pass.
2. Keep each change to one purpose. Update the relevant folder guide and the changelog.
3. Do not add secrets, personal paths or machine-specific values. `check_kit` rejects them.
4. Describe the change and how you verified it in the pull request.

Report defects and feature requests as issues, with the command you ran, the output, and the version (`/plugin` shows it).

## Licence

Released under the [MIT Licence](LICENSE).
