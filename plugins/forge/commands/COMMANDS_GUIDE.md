# plugins/forge/commands

Slash commands, each a Markdown file. Claude Code exposes each file as `/forge:<file name>`. The frontmatter gives the description and argument hint; the body is the procedure Claude follows, with a "Done when" or "On failure" section.

## Command groups

**Start here**
- `route` — picks the smallest track (quick, standard, full) for a task. Writes nothing.
- `doctor` — preflight: tools, and with `stack` the running services. Run before any feature, release or stack task.

**Plan and build a project**
- `plan-project` — plans a new project from an idea into a `<project>.plan.md`.
- `scaffold-project` — creates the skeleton from a validated plan.
- `adopt-project` — brings an existing repo under the kit without rewriting it.
- `design` — adds a feature and writes its design doc, then stops for approval.
- `feature` — builds an approved feature end to end: tests, code, review, gates, docs.
- `ship` — orchestrates plan, scaffold, design, build and promotion, one stage at a time.
- `converge` — checks that design, tests and code still agree; at most two rounds.

**Fix and check**
- `fix` — one bug on `develop` or `feature/*`: failing test first, one root-cause change, inside the diff budget.
- `hotfix` — a production bug from `master` (`hotfix/<name>`), same reproduce-first flow, then a back-merge to `develop`.
- `check` — the devops check sequence for one environment; GREEN or RED.
- `review`, `security-review` — run the reviewer or security reviewer on the current diff (or the whole repo).
- `docs-sync` — brings docs and the changelog in line with the branch.

**Test, promote and release**
- `qa` — e2e and uat levels against a deployed environment; writes a QA report.
- `eval` — runs the AI eval set and compares against the baseline.
- `promote` — opens a pull request between environment branches after the source checks pass.
- `release` — prepares a version branch and PR from `master`; tags after the PR merges.

**Memory and kit maintenance**
- `mem` — search and show project and kit memory.
- `learn-style` — learns your Python style from your own repos into `~/.kit/style.md`.
- `kit-status`, `kit-pull`, `kit-review`, `kit-new`, `kit-claim` — inspect, update, review lessons, create and claim kit units. Each asks before writing.

## How they work

- A command does its preconditions first and stops before any change if one fails.
- Stop rules are explicit: `RED` stops, `NOT READY` stops, a diff over budget stops.
- Commands never push to `qa`, `release` or `master`. Promotion and release open a PR; a person merges.
- Commands that touch the repo name the branch they run on and refuse other branches.

## Editing a command

- Keep the frontmatter `description` to one sentence; `check_kit` requires it.
- Name only agents and commands that exist.
- Keep each file within its byte budget in `kit.json` (default 3,800 bytes; `scaffold-project` has an override).
- Run `python tools/check_kit.py --tokens` and `python -m pytest tests -q`.

## Related

- `../agents/` — the agents these commands launch.
- `../skills/` — the rules they follow.
