---
description: Plan a new project from an idea and write <project>.plan.md, ready for /scaffold-project. Creates no folder, repo, or branch.
argument-hint: <project idea or name>
---

Idea: $ARGUMENTS

If no idea was given, ask the user for one and stop until they answer.

1. Read the `project-plan` skill. It defines the file format, team defaults, and the validation checklist.
2. Launch the `product-owner` agent with the idea. It returns users, acceptance criteria, out-of-scope items, and questions. Work out which facts are still missing: users, main features, cloud LLM provider, monthly token budget per environment, and whether personal data is stored. Ask for all of them in one batch, with at most four questions per call. Skip any the idea or the product owner already answers.
3. Launch the `architect` agent with the idea and the answers. It writes `./<project>.plan.md` in the current directory, following the skill exactly.
4. Run the validation checklist from the skill on the file. If it fails, send the failures back to `architect` and repeat, at most twice.
5. Show the user: the project name, the features in build order with their `depends_on`, the open decisions, and the token budgets.
6. Stop. Create nothing else. The next step is `/forge:scaffold-project ./<project>.plan.md`.

## On failure
- Plan validation fails: rewrite only the failing field, validate again. After two failed attempts, stop and report the rule.
- Missing answer to a required question (name, goal, environments): ask once, then stop until it is answered.
