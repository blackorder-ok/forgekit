# BUILD-LOG

Chronological record of how forgekit was built: what was done, why, what failed, what was deliberately left out.
Date of build: 2026-11-21. Builder: Claude (session with file bridge only; see "Environment").

## Environment and constraints
- **Request:** build the new kit from the approved plan, "claude code mode with unrestricted access", keep this log and keep README current.
- **Reality:** this session has no shell on your computer. It can stage files from your connected folder, build in a cloud workspace, and write files back. So "unrestricted shell access" was not available. Consequences:
  - Everything was authored and tested in the cloud workspace (Python 3, git, bash available), then copied into `minusOneWorkspace\forgekit`.
  - No `git init`, no `claude plugin validate`, no Docker run on your machine. These are the first steps in README section 2.
- The old folder `setting-up-claude` was only read, never changed.

## Decisions (and why)
| # | Decision | Why |
|---|---|---|
| D1 | Name: **forgekit**, plugin **forge**, commands `/forge:*` | Short, distinct from the old kit and from everything-claude-code; `forge` types fast. |
| D2 | One plugin, not four | The plan floated splitting (core/stack/memory/learn). One plugin has one version, one install, one update path; splitting is listed as optional in docs/FUTURE.md. |
| D3 | Local git marketplace + version tags, auto-update off | Junctions and symlinks have documented bugs (auto-update removing symlinked skills; Windows junction skills missing from the desktop menu). Marketplace gives approval-gated updates. |
| D4 | 13 agents → 9 | Folded `dev`/`frontend-dev`/`fixer` → `developer`; `qa-engineer` → `tester`; `devops`/`sre` → `ops`. Each fold removes a preload and a duplicated role. Reviewer and security-reviewer stayed separate: different skills, different verdicts. |
| D5 | Skills → digests (≤ 2.5 KB) + `references/` | Agents preload the digest only. Old per-agent preload 1.5-4.5k tokens; now 0.8-2.3k (measured by `check_kit --tokens`, bytes/4). |
| D6 | `coding-rules` and `branch-flow` removed as skills | Karpathy's four rules now sit in the project `CLAUDE.md` (always loaded once) instead of being preloaded into 3 agents; branch map moved into `release-standards`; hard rules in `constitution.md`. `enforcement` skill became real files in `templates/project/`. |
| D7 | One-way flow repo → plugin; nothing enters the repo unasked | Your requirement. Implemented as `kit-new` (born in repo), `kit-claim` (scan + dry run + yes), `kit-review` (branch + yes), `kit.json` registry, `~/.kit/local-ignore`. |
| D8 | Memory = typed files + 500-token index + layered search | claude-mem's 3-layer idea without a database or daemon: stdlib script, plain markdown. |
| D9 | Hooks log blocks to `~/.kit/inbox` | Gives `kit-review` real evidence of repeated mistakes without any model call. |
| D10 | Hook scripts and plugin scripts in Python/bash, stdlib only | Nothing to install. |
| D11 | Templates (Docker/CI) copied unchanged | They were your tested-in-design assets; rewriting without running them would add risk. Added only `templates/project/`. |
| D12 | No LICENSE | Your choice to make; noted in FUTURE.md. |
| D13 | Version 0.2.0 | Continues from the old kit's v0.1.0. |

## Timeline
1. **Read source.** Staged and read the old kit: 13 agents, 17 commands, 17 skills, 11 templates, scripts. Measured sizes.
2. **Skills.** Generated `references/` from the old SKILL.md bodies by script (full text kept, header added), then hand-wrote 14 digests. `branch-flow` body kept as `release-standards/references/branch-flow.md`. `python-style` generated-config block extracted to its reference.
3. **Agents.** Wrote 9 agents merging the old ones; added read limits and 40-line report limits.
4. **Templates.** Copied docker/, ci/, root/ unchanged; wrote `templates/project/` (settings.json, 3 hooks, CLAUDE.md, constitution.md).
5. **Commands.** Ported the 17 old commands by script (agent renames, `/x` → `/forge:x`, skill renames), then hand-fixed leftovers (`branch-flow`, `enforcement`, `frontend-dev`). Wrote 9 new commands.
6. **Scripts.** kit_common, kit_mem, kit_new, kit_claim, kit_status, kit_pull, style_sample; plugin hooks.json.
7. **Manifests.** plugin.json, marketplace.json, kit.json (generated from disk), .gitignore.
8. **Self-check.** `tools/check_kit.py` (+ `--tokens`).
9. **Tests.** 15 unit tests including real bash runs of branch-guard and diff-budget against temporary git repos.
10. **Docs.** README, CHANGELOG, docs/FUTURE.md, kit-ci workflow.
11. **Docs check.** Fetched the Claude Code plugin reference to confirm manifest fields, `hooks/hooks.json` wrapper, namespacing, and agent frontmatter support.
12. **Delivery.** Copied into `minusOneWorkspace\forgekit` in batches.

## Failures and fixes
| What failed | Cause | Fix |
|---|---|---|
| First `check_kit` run: "mentions /forge:doctor-related" | My regex read the words "doctor-related" in ops.md as a command | Reworded the sentence. |
| Test run: `UnicodeDecodeError` in `check_kit` | Importing the hook test module created `__pycache__/*.pyc` under `templates/`, which the placeholder scan tried to read as text | Scan skips `__pycache__`; caches deleted before delivery. |
| Bulk-ported commands had stale names | Mechanical rename missed prose forms (`branch-flow`, `frontend-dev`, `enforcement`, "devops" in a description) | Hand-fixed; `check_kit` now catches dangling agents, commands and template paths. |
| Could not follow "unrestricted access" | No shell on your machine | Built in cloud workspace; install steps are yours (README section 2). |

## Verified vs not verified
**Verified here (cloud workspace):** `check_kit --tokens` passes; 15 unit tests pass, including hook behaviour in real git repos on Linux.
**Checked against docs only:** plugin.json fields, marketplace entry shape, `hooks/hooks.json` wrapper, `${CLAUDE_PLUGIN_ROOT}` inside command and hook text, SessionStart output, agent `skills` field support.
**Not verified:**
- Whether an agent's `skills:` accepts plain names for skills of the same plugin or needs `forge:<name>`. Fix if needed: prefix each name in the agents' `skills:` line with `forge:` and teach `check_kit` to strip the prefix (one line).
- Windows behaviour of the bash hooks (needs Git Bash on PATH) and `python` vs `py` launcher.
- Docker, compose, CI templates: unchanged from the old kit and not run.
- The 17 ported commands: renamed, not exercised.
- `claude plugin validate` and `/plugin marketplace add` on your machine.

## Deviations from the plan
- Single plugin instead of 4 (D2).
- Agents 9 (plan said 9; mapping in D4).
- No periodic "new version" notice: `kit-pull` is manual only.
- Hook JSON and exit-code format follow the old kit's (exit 2 blocks); not re-verified against the installed Claude Code.
- `docs/` has FUTURE.md only; the old `PLUGIN-PLAN.md`/`REBUILD-PLAN.md` were not carried over (superseded by this README and the plan artifact).

## Update log
- 2026-11-21 v0.2.0: initial build.
