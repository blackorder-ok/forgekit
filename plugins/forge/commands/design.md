---
description: Add a feature to the project plan, run the architect to produce its design doc, then stop for approval.
argument-hint: <feature name and goal>
---

Feature: $ARGUMENTS

1. Run `git branch --show-current`. It must be `develop` or `feature/*`. Otherwise stop and report the branch.
2. Read `docs/plan.md`. If it does not exist, stop: the project was not scaffolded.
3. **Record the feature in the plan.** Add an entry to the `features` list in the front matter:
   - `id`: the next free `F<NN>` (for example `F07`). Never reuse an id.
   - `name` and `goal`: from the request. If the goal is missing, ask for it and stop until answered.
   - `depends_on`: the earlier features the feature needs. Leave it empty if none. Never list the feature itself or a later one.
   - `environments`: all four.
   - `touches` and `tests`: provisional. The architect confirms them in step 4.
   Validate the list after the edit: ids are unique, every `depends_on` refers to an earlier id, and no cycle exists. If validation fails, undo the edit and report.
4. Launch the `architect` agent with the feature and the plan. It writes `docs/design/<id>.md` (the feature id only, for example `F01.md`; never add the feature name), naming the branch and the environments affected. If its design changes `depends_on`, `touches`, or `tests`, it updates that entry in `docs/plan.md` too, and validation runs again.
5. Show the user the design's modules section, the open questions, and the plan entry as changed.
6. Stop. Do not start any implementation. The user approves by changing the first line of the design doc to `status: approved`.

## On failure
- Plan validation fails: undo the plan edit, report the failing rule, and stop. Never leave an invalid plan.
- Architect cannot fill a section: write `none` or the open question in that section, and continue. Never skip a section.
- Stop after the design is written. Do not start implementation without the user's approval.
