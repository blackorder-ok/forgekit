# forge

Claude Code plugin from forgekit: plan, scaffold, build, review and ship production-grade Python/FastAPI apps in your own style with token-lean agents, skills and commands. Everything is namespaced `/forge:<name>`; start with `/forge:route <task>` to pick the smallest track. Install and update steps, the full command list and the memory and learning-loop design are in the repository README one level up.

Setup: `python` on PATH; on Windows, Git Bash on PATH for the project hooks. Set `KIT_HOOKS=minimal` to switch off the test_guard and diff_budget hooks (branch_guard always stays on).

Install: `/plugin marketplace add blackorder-ok/forgekit` then `/plugin install forge --marketplace blackorder-ok/forgekit` (a local clone path works too).
