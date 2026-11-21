---
description: Pick the smallest track for a task (quick, standard or full) so you do not pay for ceremony you do not need. Writes nothing.
argument-hint: <task description>
---

Task: $ARGUMENTS

Classify the task using only the task text and, if it exists, `docs/plan.md` (read nothing else):

| Track | When | Path |
|---|---|---|
| **quick** | one bug, one small tweak, a doc or config change, 3 files / 20 lines or less | `/forge:fix` (bug) or edit directly with a test |
| **standard** | one feature in an existing plan | `/forge:design` → approve → `/forge:feature` |
| **full** | new project, new subsystem, several features, unclear scope | `/forge:ship` (or `/forge:plan-project` → `/forge:scaffold-project` → features) |

Reply in at most 6 lines: the track, the first command to run, and the one fact that decided it. If two tracks fit, give the smaller one and say what would move it up. If the task is not about a kit project, say so.

If `docs/plan.md` exists, you may set `track:` in its front matter only when the user says to. Do not start the work.
