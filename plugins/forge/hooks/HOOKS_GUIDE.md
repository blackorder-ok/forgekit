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

## Setup

Nothing to configure beyond `python` on `PATH`. On Windows, the hooks run through Git Bash only where a project hook needs it.

## Related

- `../scripts/` — the scripts these hooks call.
- `../templates/project/hooks/` — the project-level hooks.
