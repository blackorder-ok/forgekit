# Changelog

## [0.4.0] - 2026-11-21
### Added
- MIT `LICENSE`, plugin icon, `license` in plugin.json; install line in the plugin README. `claude plugin validate --profile directory` passes clean.
### Fixed
- `/forge:adopt-project` no longer runs `/forge:doctor` (its checks assume a kit-scaffolded stack and started containers in a plain repo); it checks only git and Python.
### Tested
- Isolated marketplace install; headless runs of `route`, `scaffold-project`, `adopt-project`, `kit-review`, `learn-style`, `converge`; live `branch_guard` block on `qa`. See PROGRESS.md.

## [0.3.1] - 2026-11-21
### Changed
- Naming rules enforced: snake_case file names (hooks renamed to `branch_guard.sh`, `diff_budget.sh`, `test_guard.py`), camelCase functions and variables, PascalCase classes, SCREAMING_SNAKE_CASE constants and globals. `check_kit` lints them; `python-style` states them.

## [0.3.0] - 2026-11-21
### Added
- `KIT_HOOKS=minimal` switch for test-guard and diff-budget (branch-guard always on).
- SessionStart "new kit tag" notice (`kit_pull.py --notice`); never installs.
- `docs/STATE.md` and `docs/decisions.md` project templates; `docs/BASELINE.md`; `docs/settings-snippet.json`.
- Plugin `README.md`, marketplace description; `check_kit` rules: skills must not require other skills, agents preload at most 4 skills.
- Tests: 20 (hook profile, notice, independence rule, 8k feature-preload gate).
### Changed
- Agent preloads trimmed: rarely used skills are now on demand through the Skill tool. Full /feature preload about 7.9k tokens (was about 10.6k).
- Windows: tests use Git Bash and clear read-only git files.

## [0.2.0] - 2026-11-21
First forgekit release, a rebuild of `setting-up-claude` v0.1.0. See BUILD-LOG.md for every decision.
### Added
- Plugin `forge` with 9 agents, 26 commands, 14 skill digests (details in `references/`).
- New commands: `route`, `converge`, `mem`, `learn-style`, `kit-new`, `kit-claim`, `kit-status`, `kit-pull`, `kit-review`.
- Scripts: `kit_mem`, `kit_new`, `kit_claim`, `kit_status`, `kit_pull`, `style_sample`; `tools/check_kit.py` with `--tokens`.
- Project templates: `CLAUDE.md` (Karpathy's four rules), `constitution.md`, enforcement hooks that also log to the lesson inbox.
- Unit tests (15) and a CI workflow for the kit itself.
### Changed
- 13 agents folded to 9; skills condensed to digests; `coding-rules` and `branch-flow` moved into project `CLAUDE.md`, constitution and `release-standards`.
- Distribution: marketplace + plugin instead of copying/junctions.
