# tools

Maintenance scripts for the kit repository. These run on the kit itself, not on generated projects.

## Contents

| File | Purpose |
|---|---|
| `check_kit.py` | The kit self-check. |

## check_kit.py

Run from anywhere:

```
python tools/check_kit.py           # structure and rule checks
python tools/check_kit.py --tokens  # plus byte and token budgets
```

It checks, and exits 1 on any problem:

- manifests parse (`kit.json`, `plugin.json`, `marketplace.json`);
- every agent's skills exist, and every skill has `name`, `pack` and `description`;
- commands name only real agents and commands;
- template placeholders are documented;
- `kit.json` matches the files on disk;
- no secrets or personal paths are committed;
- naming follows the lint rules;
- with `--tokens`: each file is within its byte budget and each agent's preloaded skills are within the agent budget.

## Setup

Python 3 with the standard library. No install step.

## Changing it

Add each new rule with a test in `tests/test_forge.py`. A rule that fails on the current repo must be fixed in the same change, not waived.
