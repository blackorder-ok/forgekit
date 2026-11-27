# plugins/forge/hooks

Plugin-level hooks: they run in every Claude Code session where the plugin is installed.

## Contents

| File | Purpose |
|---|---|
| `hooks.json` | Declares two `SessionStart` hooks. |

## What runs

On `SessionStart`, Claude Code runs both commands from `hooks.json`:

1. `python "${CLAUDE_PLUGIN_ROOT}/scripts/kit_mem.py" index` prints a short memory index (ids and titles, capped near 500 tokens) so Claude knows what memory exists without loading it.
2. `python "${CLAUDE_PLUGIN_ROOT}/scripts/kit_pull.py" --notice` fetches kit tags and prints one line if a newer version exists. It never installs anything.

Both are stdlib-only Python and fail quietly, so a broken hook never blocks a session.

## Project hooks are different

The three enforcement hooks (`branch_guard`, `diff_budget`, `test_guard`) are not here. They are copied into each generated project from `templates/project/hooks/` and wired by that project's `.claude/settings.json`. See `../templates/project/hooks/`.

## Fail-closed launcher

Project hooks run through `scripts/hook_launch.sh`, which finds Python 3.9+ and hands off to `scripts/hook_main.py`. Any failure in a `PreToolUse` or `Stop` hook (crash, timeout, bad JSON, missing script or interpreter) becomes exit 2 with the reason and a fix. A hook's own exit 2 is still a denial.

- `SessionStart` runs `--selfcheck`: it checks Python, the hook files and that the settings wire every hook through the launcher. On failure it writes `.claude/learn/selfcheck.failed`, and `PreToolUse` denies until the check passes. It never blocks the session.
- Break-glass: a file `~/.kit/breakglass` containing an ISO-8601 UTC expiry at most 4 hours ahead downgrades errors to warnings. It never downgrades denials and is logged as `gate.breakglass`.
- `KIT_HOOKS=minimal` skips hooks on feature branches only. Protected branches (`master`, `qa`, `release`) always run every hook. It is local-only and is not for shared work.
- `KIT_HOOK_TIMEOUT` sets the per-hook limit in seconds (default 10).

## Setup

Nothing to configure beyond Python 3.9+ on `PATH`. On Windows, the project hooks need Git Bash; set `KIT_BASH` if `bash` is not on `PATH`.

## Related

- `../scripts/` — the scripts these hooks call.
- `../templates/project/hooks/` — the project-level hooks.
