# plugins/forge/agents

The nine subagents that do focused work for the commands. Each agent is one Markdown file with frontmatter (`name`, `description`, `tools`, `model`, `skills`) and a body that gives its role, process, rules and "done when" test.

## Agents

| Agent | Role | Typical caller |
|---|---|---|
| `product-owner` | Turns an idea into users, acceptance criteria and at most four open questions. | `/forge:plan-project`, `/forge:ship` |
| `architect` | Writes the project plan or one feature's design doc. Never writes application code. | `/forge:design`, `/forge:plan-project` |
| `tester` | Writes failing tests before the code, and regression tests for bugs. Runs e2e, smoke and uat levels. | `/forge:feature`, `/forge:fix`, `/forge:qa` |
| `developer` | Makes the failing tests pass with the minimum code, or fixes one bug with the smallest change. | `/forge:feature`, `/forge:fix` |
| `reviewer` | Read-only review of a diff against its design and team standards. | `/forge:review`, `/forge:feature`, `/forge:fix` |
| `security-reviewer` | Read-only security review of a diff or the whole repo. | `/forge:security-review`, `/forge:feature` |
| `ops` | Owns Docker, compose, CI and one environment's health. Runs the check sequence to GREEN or RED. | `/forge:check`, `/forge:doctor`, `/forge:feature` |
| `ai-evaluator` | Writes eval cases and runs `/forge:eval` for LLM features. | `/forge:eval` |
| `doc-updater` | Keeps docs and the changelog's Unreleased section in step with the code. Never changes code. | `/forge:docs-sync`, `/forge:feature` |

## How they work

- A command launches an agent with the task and the files it needs. Agents do not launch each other, so each one can be run alone.
- Agents preload only the skill digests listed in their `skills:` field. Detail stays in `skills/*/references/` and is read on demand.
- Agents return a verdict and a file path, not a narrative. Commands rely on that format.
- Token size is budgeted. `tools/check_kit.py --tokens` fails if an agent plus its preloads exceeds the budget in `kit.json`. The current numbers are in `docs/BASELINE.md`.

## Editing an agent

1. Keep the frontmatter valid; `check_kit` reads `name`, `description` and `skills`.
2. Only list skills that exist in `skills/`.
3. Run `python tools/check_kit.py --tokens` and `python -m pytest tests -q`.
4. Note the change in `CHANGELOG.md`.

## Related

- `../commands/` — the commands that launch these agents.
- `../skills/` — the rule digests agents preload.
