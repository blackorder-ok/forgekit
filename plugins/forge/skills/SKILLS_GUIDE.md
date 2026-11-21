# plugins/forge/skills

Rule digests. A skill is a folder with a `SKILL.md` (the digest, under 2.5 KB) and optional `references/` files (the full detail, read on demand).

## Skills

| Skill | Covers | Preloaded by |
|---|---|---|
| `ci-pipeline` | GitHub Actions for develop, qa, release and master, and the reusable env-test workflow. | `ops` |
| `config-db` | Config files, secrets, database and vector-store settings per environment. | none; read on demand by commands and agents |
| `dependency-policy` | Adding, pinning and removing dependencies; Dependabot. | none; read on demand |
| `docker-prod` | One app container per environment, nginx, backend, MySQL, Ollama, and the AWS emulator. | `ops` |
| `frontend` | React, TypeScript, Vite, TanStack Query, Vitest, Playwright, nginx in the app container. | `developer` |
| `genai-client` | The one pattern for LLM and embedding calls, local or cloud. | none; read on demand |
| `llm-eval` | Eval case format, metrics, baseline and regression rules. | `ai-evaluator` |
| `llm-security` | Security rules for LLM features, mapped to the OWASP LLM Top 10. | `security-reviewer` |
| `project-plan` | Plan file format, team defaults, validation checklist and feature order. | `architect`, `product-owner` |
| `python-security` | FastAPI and Python security rules and the scanners that enforce them. | `security-reviewer`, `reviewer` |
| `python-style` | Naming, logging, structure and tooling conventions. | `developer` |
| `release-standards` | Branch flow, versioning, commits, changelog, tags, rollback. | `doc-updater` |
| `security-waivers` | How to accept a known finding with a reason, owner and expiry. | `security-reviewer` |
| `test-levels` | Test levels, their pytest markers, where each runs and the pass rules. | `tester` |

## How it works

- Agents preload digests through their `skills:` field. The digest is the rule set; `references/` holds examples and scanner details.
- A skill is loaded only when a listed agent or command needs it. Keep digests short so every preload stays inside the budget.
- Each `SKILL.md` has frontmatter with `name`, `pack` and `description`. The description says when to use the skill, so it can be found by name.

## Editing a skill

1. Keep the digest under 2.5 KB; move examples into `references/`.
2. Change `description` only if the trigger changes.
3. Run `python tools/check_kit.py --tokens` to confirm the budget.
4. If the rule changes behaviour, update the docs and `CHANGELOG.md`.

## Related

- `../agents/` — the agents that preload these skills.
- `../../../docs/BASELINE.md` — the token numbers per agent.
