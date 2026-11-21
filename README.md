# forgekit

A Claude Code kit that plans, scaffolds, builds, reviews and ships production-grade Python/FastAPI apps in your coding style, on your own machine, with the fewest tokens it can manage.

It ships as one plugin, **`forge`**, from a local git marketplace, **`forgekit`**. Everything is namespaced `/forge:<name>`.

- Version: 0.2.0 · Replaces: `setting-up-claude` v0.1.0 (left untouched) · Build story: [BUILD-LOG.md](BUILD-LOG.md)

## Contents
1. [What you get](#1-what-you-get)
2. [Install and first run](#2-install-and-first-run)
3. [Which command, when](#3-which-command-when)
4. [Typical flows](#4-typical-flows)
5. [Agents](#5-agents)
6. [Skills](#6-skills)
7. [Memory and tokens](#7-memory-and-tokens)
8. [Learning loop: global vs project](#8-learning-loop-global-vs-project)
9. [Adding your own units](#9-adding-your-own-units)
10. [Updating the kit](#10-updating-the-kit)
11. [Guardrails (hooks)](#11-guardrails-hooks)
12. [Repo layout](#12-repo-layout)
13. [Checks and tests](#13-checks-and-tests)
14. [Known limits](#14-known-limits)

---

## 1. What you get

| Thing | Count | Where |
|---|---|---|
| Commands | 26 | `plugins/forge/commands/` |
| Agents | 9 | `plugins/forge/agents/` |
| Skill digests | 14 (each with `references/` for detail) | `plugins/forge/skills/` |
| Project templates (Docker, CI, hooks, CLAUDE.md, constitution) | 17 files | `plugins/forge/templates/` |
| Scripts (memory, kit management, style) | 7 | `plugins/forge/scripts/` |
| Kit self-check and tests | 1 + 15 tests | `tools/`, `tests/` |

Design rules the kit follows itself: Karpathy's four rules (think first, simplest thing, surgical changes, goal-driven) and token budgets enforced by `tools/check_kit.py --tokens` (skill digest ≤ 2.5 KB, agent ≤ 3 KB, command ≤ 3.5 KB; one documented exception).

Every agent, skill and command works on its own: nothing requires `/forge:ship`.

## 2. Install and first run

You need Claude Code, git, Python 3.11, and (for generated projects) Docker.

```bash
cd <path-to>\forgekit
git init -b main
git add .
git commit -m "forgekit 0.2.0"
git tag v0.2.0
```

Check the plugin files with Claude Code's own validator:

```bash
claude plugin validate ./plugins/forge
```

Install from the local marketplace, inside Claude Code:

```
/plugin marketplace add <path-to>\forgekit
/plugin install forge@forgekit
```

Tell the scripts where your kit clone is (used by `kit-new`, `kit-claim`, `kit-status`, `kit-pull`):

```bash
mkdir %USERPROFILE%\.kit
echo <path-to>\forgekit > %USERPROFILE%\.kit\repo
```

Developing the kit itself: run `claude --plugin-dir <path-to>\forgekit\plugins\forge` so edits show up after `/reload-plugins` with no reinstall.

Auto-update is off for this marketplace. Updates are manual: see [section 10](#10-updating-the-kit).

First run in any folder: `/forge:doctor` (checks Docker, git, gh, Python, emulator).

## 3. Which command, when

### Start here
| Command | Use it when | What it does |
|---|---|---|
| `/forge:route <task>` | You are unsure how much process the task needs | Picks the track (quick / standard / full) and names the first command. Writes nothing. |
| `/forge:doctor` | Before any feature, release or stack run | Read-only preflight of Docker, compose, emulator, Ollama, git, gh, secrets file, Python. `READY` or `NOT READY`. |
| `/forge:ship <idea>` | New project, hands-off | Orchestrates product → plan → scaffold → F01 → features → promote, one stage at a time, stops at every decision. |

### Plan and scaffold
| Command | Use it when | What it does |
|---|---|---|
| `/forge:plan-project <idea>` | New project | `product-owner` asks up to 4 questions; `architect` writes `<project>.plan.md`; validated. Creates nothing else. |
| `/forge:scaffold-project <plan>` | A validated `mode: new` plan exists | Creates the repo skeleton: Docker, CI, config, docs, hooks, `CLAUDE.md`, constitution, four branches. GitHub steps each need your yes. |
| `/forge:adopt-project <path>` | You have an existing repo | Surveys read-only, writes `docs/plan.md` from reality, lists gaps, closes them one small branch each. Never rewrites working code. |

### Build
| Command | Use it when | What it does |
|---|---|---|
| `/forge:design <feature>` | Adding a feature | Adds it to the plan, `architect` writes `docs/design/<feature>.md`, stops for your approval (`status: approved`). |
| `/forge:feature <feature>` | Design approved | Gate → red tests → green code → review → security → evals (if LLM) → final gate → docs. Never merges. |
| `/forge:converge <feature>` | After a build, or drift suspected | Checks design ↔ tests ↔ code, fixes the smallest mismatch, max 2 rounds. |
| `/forge:fix <bug>` | One bug on develop/feature | Failing regression test first, one root-cause change, diff budget 3 files / 20 lines, review, gate. Explicit verdicts. |
| `/forge:hotfix <bug>` | Production bug | Same as fix, cut from `master`, prepares two PRs (master and develop). |

### Check and ship
| Command | Use it when | What it does |
|---|---|---|
| `/forge:check <env>` | Any time | `ops` runs build, health, tests, logs and scans for one env → `GREEN` / `RED`. |
| `/forge:review [feature]` | Before merging | Read-only code review of the diff → `APPROVE` / `CHANGES REQUIRED`. |
| `/forge:security-review [all]` | Before merging | Read-only security review → `PASS` / `PASS WITH FINDINGS` / `FAIL`. |
| `/forge:eval <env>` | LLM feature changed | Runs eval set vs thresholds and baseline; never updates the baseline. |
| `/forge:qa <env>` | After deploy | e2e / smoke runs and UAT list, writes `docs/qa/<env>-<date>.md`. |
| `/forge:docs-sync` | After a merge | `doc-updater` aligns docs and changelog with the code. |
| `/forge:promote <from> <to>` | Moving up the flow | Opens the PR for `develop→qa`, `qa→release`, `release→master` after a green check. |
| `/forge:release X.Y.Z` / `tag X.Y.Z` | Releasing | Prepares the version branch + PR; after merge, tags the merge commit. |

### Memory and style
| Command | Use it when | What it does |
|---|---|---|
| `/forge:mem search\|show\|timeline\|add` | Before re-deriving a known fix; after learning one | Cheap layered memory (ids → one entry). |
| `/forge:learn-style <folders>` | Once, and after your style shifts | Samples your own Python (counts only), proposes `~/.kit/style.md`, saves after your yes. |

### Kit management (you maintain the kit)
| Command | Use it when | What it does |
|---|---|---|
| `/forge:kit-new <kind> <name>` | You want a new skill/agent/command in the kit | Creates it in the repo from a template and registers it. Born in the repo, nothing to claim. |
| `/forge:kit-status` | Curious what is in `~/.claude` | Read-only: orphans, ignored, drifted. |
| `/forge:kit-claim <kind> <name>` | A unit made elsewhere belongs in the kit | Scans for secrets and personal paths, shows a dry run, copies only after your yes. |
| `/forge:kit-review` | Now and then | Groups the lesson inbox, proposes global lessons on a `learn/<date>` branch for approval. |
| `/forge:kit-pull` | You want updates | Fetches tags, shows what changed, changes nothing. |

## 4. Typical flows

**New project:** `/forge:route "…"` → `/forge:plan-project "…"` → `/forge:scaffold-project ./name.plan.md` → `/forge:design F01` (approve) → `/forge:feature F01` → repeat for each feature → `/forge:promote develop qa`. Or run `/forge:ship "…"` and answer its stops.

**Existing project:** `/forge:adopt-project <path>` → review the `kit/*` branches → then `design` / `feature` / `fix` as usual.

**Small bug:** `/forge:fix "…"` (budget 3 files / 20 lines; over budget means `/forge:design`).

**Production bug:** `/forge:hotfix "…"` → two PRs you open.

**Release:** `/forge:promote qa release` → `/forge:promote release master` → merge → `/forge:release 1.2.0` → merge → `/forge:release tag 1.2.0`.

Three tracks, from `/forge:route`:

| Track | For | Path |
|---|---|---|
| quick | one bug or tweak | `fix` |
| standard | one feature | `design` → `feature` |
| full | new project or subsystem | `ship` |

## 5. Agents

Nine, each usable alone (`@forge:<name>` or through its command). Preload = agent file plus its skill digests, approx tokens.

| Agent | Model | Does | Preload |
|---|---|---|---|
| product-owner | sonnet | users, acceptance criteria, ≤ 4 questions | ~0.8k |
| architect | opus | plan file or design doc | ~1.9k |
| developer | sonnet | green code (backend and frontend); fix mode for one bug | ~1.7k |
| tester | sonnet | red tests, regression tests, e2e / smoke / uat runs | ~1.3k |
| ops | sonnet | Docker, CI, env check, health, rollback, backup | ~2.3k |
| reviewer | sonnet | read-only code review | ~1.2k |
| security-reviewer | sonnet | read-only security review, waivers | ~1.9k |
| ai-evaluator | sonnet | eval cases and failure explanations | ~1.5k |
| doc-updater | haiku | docs and changelog | ~0.8k |

Folded from the old 13: `dev` + `frontend-dev` + `fixer` → `developer`; `qa-engineer` → `tester`; `devops` + `sre` → `ops`.

## 6. Skills

Digests are loaded by agents; the long version sits in `references/` and is read only when needed.

| Skill | Pack | Covers |
|---|---|---|
| project-plan | core | plan format, defaults, validation |
| test-levels | core | markers, levels, pass rules, layout |
| release-standards | core | branch flow, commits, versions, changelog, rollback |
| security-waivers | core | waiver format and rules |
| ci-pipeline | core | CI rules for the four branches |
| dependency-policy | core | pinning, updates, vulnerabilities |
| config-db | stack | config files, secrets, DB, vector store |
| python-style | stack | your naming, logging, structure, tools |
| python-security | stack | 10 security rules and scanners |
| docker-prod | stack | one stack per environment |
| genai-client | stack | one pattern for LLM calls |
| llm-security | stack | OWASP LLM Top 10 mapping |
| llm-eval | stack | eval cases, metrics, thresholds |
| frontend | stack | React / TS / Vite rules |

`coding-rules` and `branch-flow` are no longer skills: the four rules live in each project's `CLAUDE.md`, the hard rules in `constitution.md`, the branch map in `release-standards`.

## 7. Memory and tokens

| Tier | What | Cost | Where |
|---|---|---|---|
| L0 | `CLAUDE.md` (about 25 lines incl. Karpathy's four) + constitution (10 rules) | always loaded, ~700 tokens | project root, `.claude/` |
| L1 | memory index: ids and titles, newest first | ≤ ~500 tokens, printed at session start by a plugin hook | `.claude/memory/` |
| L2 | `/forge:mem show <id>` or a skill's `references/` | on demand, ≤ ~150 tokens per entry | same |
| L3 | git history | never loaded | repo |

Entry types: `gotcha`, `fix`, `decision`, `preference`. Titles ≤ 10 words, bodies ≤ 600 bytes. Search returns ids and titles only.

Other token rules: skills preload as digests; agents report under 40 lines; read-limits per agent (10–25 files); `check_kit --tokens` fails the build if a file outgrows its budget.

## 8. Learning loop: global vs project

```
hooks (branch-guard, test-guard, diff-budget) ─► ~/.kit/inbox (one line per block)
                                                 │  /forge:kit-review
                      project lesson ◄───────────┤  (≥3 times in ≥2 projects = promote candidate)
              .claude/memory/ (stays in project)  └─► global lesson ─► branch learn/<date> in the kit repo ─► you approve
```

- Project lessons never reach the kit.
- Nothing enters the kit repo except through `kit-new` (born there), `kit-claim` (your yes) or `kit-review` (your yes, on a branch).
- Nothing in `~/.claude` is ever read into the repo automatically. `~/.kit/local-ignore` lists personal units the kit should ignore.
- Your personal style lives in `~/.kit/style.md` (outside the repo); a project can override it in `.claude/style.local.md`.

## 9. Adding your own units

1. `/forge:kit-new skill my-skill` (or `agent`, `command`). It creates the file in the repo and registers it in `kit.json`.
2. Fill it in; keep to the byte budgets; put detail in `references/`.
3. `python tools/check_kit.py --tokens` and `python -m unittest discover -s tests`.
4. Commit, bump `version` in `plugins/forge/.claude-plugin/plugin.json` and `kit.json`, tag.

If you already made a unit under `~/.claude`: `/forge:kit-status`, then `/forge:kit-claim`, or add its name to `~/.kit/local-ignore` to keep it personal.

## 10. Updating the kit

The plugin `version` is set, so Claude Code keeps you on an installed version until it changes. To update:

1. `/forge:kit-pull`: fetches tags and shows what changed. It changes nothing.
2. After you agree: `/plugin marketplace update forgekit`, then `/plugin update forge@forgekit`.

Rolling back: install the earlier tag (`git checkout v0.2.0` in the kit clone, then update the marketplace).

## 11. Guardrails (hooks)

Copied into every scaffolded project (`.claude/settings.json`, `scripts/hooks/`):

| Hook | When | Blocks |
|---|---|---|
| `branch-guard.sh` | before Edit/Write | edits on `qa`, `release`, `master`, detached HEAD |
| `test-guard.py` | before Edit/Write | edits to tests that remove `assert` lines or add skip/xfail |
| `diff-budget.sh` | on Stop, only during fix/hotfix | finishing with more than 3 files or 20 changed lines |

`settings.json` also denies reading `secrets/**` and force-pushes. Each block appends one line to `~/.kit/inbox`.

The plugin adds a `SessionStart` hook that prints the memory index.

## 12. Repo layout

```
forgekit/
├── README.md, BUILD-LOG.md, CHANGELOG.md, kit.json
├── .claude-plugin/marketplace.json
├── plugins/forge/
│   ├── .claude-plugin/plugin.json
│   ├── agents/ (9)   commands/ (26)   skills/ (14, each with references/)
│   ├── hooks/hooks.json
│   ├── scripts/ kit_mem, kit_new, kit_claim, kit_status, kit_pull, style_sample, kit_common
│   └── templates/ docker/, ci/, root/, project/
├── tools/check_kit.py
├── tests/test_forge.py
├── docs/FUTURE.md
└── .github/workflows/kit-ci.yml
```

`kit.json` is the registry of what belongs to the kit; `check_kit` fails on any unit that exists on disk but is not registered, or the reverse.

## 13. Checks and tests

```bash
python tools/check_kit.py --tokens
python -m unittest discover -s tests -v
claude plugin validate ./plugins/forge
```

`check_kit` verifies manifests parse, agents' skills exist, commands launch real agents and mention real commands, template paths and placeholders, registry consistency, no secrets or personal paths, and the byte budgets. The 15 tests cover memory, kit-new/claim/status/pull, style sampling, the three hooks and `check_kit` itself.

## 14. Known limits

Honest list; details in BUILD-LOG.md.

- **Not run against a live Claude Code.** Plugin and hook formats were checked against the docs only; run `claude plugin validate` first.
- **Skill names in agent `skills:`** use plain names (`python-style`). If plugin skills need the prefix, change them to `forge:<name>` (one `sed`), then rerun `check_kit`.
- **Templates (Docker, CI, compose, nginx, supervisord) were carried over unchanged and not run.** `cap_add` items are `TODO-VERIFY`.
- **Command text for the 17 ported commands was only mechanically renamed**, not re-tested end to end.
- No LICENSE yet; add one before publishing.
- Judge-based evals, load tests, real-AWS deploy are deferred ([docs/FUTURE.md](docs/FUTURE.md)).
