"""Agent privilege (WI-11): table-driven decisions per agent, confused-deputy cases, frontmatter and identity checks."""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
PLUGIN = os.path.join(ROOT, "plugins", "forge")
sys.path.insert(0, os.path.join(PLUGIN, "scripts"))

import agent_guard  # noqa: E402
import agent_identity  # noqa: E402
import kit_policy  # noqa: E402

POLICY = kit_policy.load()
PROJ = "/proj"  # decisions are path arithmetic: no file needs to exist


def w(path):
    return ("Write", {"file_path": path})


def e(path):
    return ("Edit", {"file_path": path})


def b(cmd):
    return ("Bash", {"command": cmd})


# (agent, (tool, input), expected verdict)
TABLE = [
    ("product-owner", w("docs/x.md"), "deny"),
    ("product-owner", b("git status"), "deny"),
    ("product-owner", ("Read", {"file_path": "docs/x.md"}), "allow"),
    ("architect", w("docs/design/feature.md"), "allow"),
    ("architect", w("docs/plan.md"), "allow"),
    ("architect", w("app/main.py"), "deny"),
    ("architect", w("tests/test_a.py"), "deny"),
    ("architect", b("git status"), "deny"),
    ("developer", w("app/service.py"), "allow"),
    ("developer", e("app/service.py"), "allow"),
    ("developer", w("tests/test_a.py"), "deny"),
    ("developer", w(".github/workflows/ci.yml"), "deny"),
    ("developer", w("docker/Dockerfile"), "deny"),
    ("developer", w(".claude/policy.json"), "deny"),
    ("developer", w("plugins/forge/policy/gates.json"), "deny"),
    ("developer", b("pytest -q"), "allow"),
    ("tester", w("tests/test_a.py"), "allow"),
    ("tester", w("docs/qa/report.md"), "allow"),
    ("tester", w("app/service.py"), "deny"),
    ("tester", b("pytest -q"), "allow"),
    ("ops", w("docker/Dockerfile"), "allow"),
    ("ops", w(".github/workflows/ci.yml"), "allow"),
    ("ops", w("app/service.py"), "deny"),
    ("ops", w("tests/test_a.py"), "deny"),
    ("reviewer", b("git diff HEAD~1"), "allow"),
    ("reviewer", b("git log --oneline -5"), "allow"),
    ("reviewer", b("pip-audit -r backend/requirements.txt"), "allow"),
    ("reviewer", w("app/service.py"), "deny"),
    ("reviewer", e("app/service.py"), "deny"),
    ("reviewer", ("NotebookEdit", {"notebook_path": "a.ipynb"}), "deny"),
    ("reviewer", b("pytest -q"), "deny"),  # not allow-listed: pytest runs code that can write
    ("security-reviewer", b("git diff main...HEAD"), "allow"),
    ("security-reviewer", b("bandit -r backend -ll"), "allow"),
    ("security-reviewer", b("gitleaks detect --no-banner"), "allow"),
    ("security-reviewer", w("app/service.py"), "deny"),
    ("ai-evaluator", w("evals/cases.jsonl"), "allow"),
    ("ai-evaluator", w("evals/baseline.json"), "deny"),
    ("ai-evaluator", w("app/service.py"), "deny"),
    ("doc-updater", w("README.md"), "allow"),
    ("doc-updater", w("docs/runbook.md"), "allow"),
    ("doc-updater", e("CHANGELOG.md"), "allow"),
    ("doc-updater", w("app/service.py"), "deny"),
    ("doc-updater", b("git diff --stat"), "allow"),
    ("doc-updater", b("rg TODO docs"), "allow"),
    ("doc-updater", b("curl https://example.com"), "deny"),
    # confused-deputy routes a read-only agent must not reach
    ("reviewer", b("git apply patch.diff"), "deny"),
    ("reviewer", b("git diff --output=out.txt"), "deny"),
    ("reviewer", b("git diff | sh"), "deny"),
    ("reviewer", b("git diff; rm app.py"), "deny"),
    ("reviewer", b("sed -i s/a/b/ app.py"), "deny"),
    ("reviewer", b("tee app.py"), "deny"),
    ("reviewer", b("python -c 'open(\"x\",\"w\").write(\"1\")'"), "deny"),
    ("reviewer", b("git checkout -- app.py"), "deny"),
    ("security-reviewer", b("gitleaks detect --report-path out.json"), "deny"),
    ("doc-updater", b("rg TODO > notes.txt"), "deny"),
    ("doc-updater", b("git log -1 && rm app.py"), "deny"),
    # an unidentified subagent is read-only
    ("unknown", w("app/service.py"), "deny"),
    ("unknown", b("git status"), "deny"),
    ("unknown", ("Read", {"file_path": "app/service.py"}), "allow"),
    # the main thread is not restricted by agent rules
    ("main", w("app/service.py"), "allow"),
    ("main", b("git push origin feature/x"), "allow"),
]

# Frontmatter expected from the privilege table.
FRONTMATTER = {
    "product-owner": {"disallowed": "Write, Edit, Bash", "maxTurns": "8", "effort": "low", "model": "sonnet"},
    "architect": {"disallowed": "Edit, Bash", "maxTurns": "25", "effort": "high", "model": "opus"},
    "developer": {"disallowed": None, "maxTurns": "40", "effort": "medium", "model": "sonnet"},
    "tester": {"disallowed": None, "maxTurns": "30", "effort": "medium", "model": "sonnet"},
    "ops": {"disallowed": None, "maxTurns": "30", "effort": "medium", "model": "sonnet"},
    "reviewer": {"disallowed": "Write, Edit, MultiEdit, NotebookEdit, Skill", "maxTurns": "20", "effort": "medium", "model": "sonnet"},
    "security-reviewer": {"disallowed": "Write, Edit, MultiEdit, NotebookEdit", "maxTurns": "25", "effort": "high", "model": "sonnet"},
    "ai-evaluator": {"disallowed": None, "maxTurns": "20", "effort": "medium", "model": "sonnet"},
    "doc-updater": {"disallowed": None, "maxTurns": "15", "effort": "low", "model": "haiku"},
}


def verdictOf(agent, call):
    tool, tin = call
    identity = None if agent == "main" else agent
    if identity == "unknown":
        identity = agent_identity.UNKNOWN
    return agent_guard.decide(identity, tool, tin, PROJ, POLICY)[0]


class PrivilegeTable(unittest.TestCase):
    def test_table(self):
        failures = []
        for agent, call, want in TABLE:
            got = verdictOf(agent, call)
            if got != want:
                failures.append(f"{agent} {call[0]} {call[1]}: want {want}, got {got}")
        self.assertEqual(failures, [])

    def test_every_agent_has_an_allow_and_a_deny(self):
        for agent in FRONTMATTER:
            verdicts = {verdictOf(agent, call) for a, call, _ in TABLE if a == agent}
            self.assertEqual(verdicts, {"allow", "deny"}, agent)

    def test_every_policy_agent_is_in_the_table(self):
        self.assertEqual(set(POLICY["agents"]), set(FRONTMATTER))


class Frontmatter(unittest.TestCase):
    def fm(self, name):
        text = open(os.path.join(PLUGIN, "agents", f"{name}.md"), encoding="utf-8").read()
        block = text.split("---\n", 2)[1]
        return dict(re.findall(r"^(\w+): (.*)$", block, re.M))

    def test_values_match_the_privilege_table(self):
        for name, want in FRONTMATTER.items():
            got = self.fm(name)
            self.assertEqual(got.get("maxTurns"), want["maxTurns"], name)
            self.assertEqual(got.get("effort"), want["effort"], name)
            self.assertEqual(got.get("model"), want["model"], name)
            self.assertEqual(got.get("disallowedTools"), want["disallowed"], name)

    def test_read_only_agents_cannot_write(self):
        for name in ("product-owner", "reviewer", "security-reviewer"):
            tools = {t.strip() for t in self.fm(name)["tools"].split(",")}
            self.assertFalse(tools & {"Write", "Edit", "MultiEdit", "NotebookEdit"}, name)


class Identity(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp(prefix="agent-id-")
        self.addCleanup(shutil.rmtree, self.d, True)
        git(self.d, "init", "-q", "-b", "develop")
        write(self.d, "app.py", "x = 1\n")
        write(self.d, "notes.txt", "mine\n")
        git(self.d, "add", ".")
        subprocess.run(["git", "-C", self.d, "-c", "user.email=a@b", "-c", "user.name=t", "commit", "-q", "-m", "init"],
                       check=True, capture_output=True)
        write(self.d, "notes.txt", "user edit already in progress\n")  # the user's own change

    def runAgent(self, name, change):
        agent_identity.start(self.d, {"agent_type": name} if name else {})
        change()
        return agent_identity.stop(self.d)

    def test_user_edit_before_start_is_not_blamed(self):
        self.assertEqual(self.runAgent("reviewer", lambda: None), 0)

    def test_reviewer_change_blocks_stop(self):
        self.assertEqual(self.runAgent("reviewer", lambda: write(self.d, "app.py", "x = 2\n")), 2)

    def test_developer_change_in_scope_passes(self):
        self.assertEqual(self.runAgent("developer", lambda: write(self.d, "app.py", "x = 2\n")), 0)

    def test_developer_change_to_tests_blocks_stop(self):
        self.assertEqual(self.runAgent("developer", lambda: write(self.d, "tests/test_a.py", "x\n")), 2)

    def test_unknown_agent_change_blocks_stop(self):
        self.assertEqual(self.runAgent(None, lambda: write(self.d, "app.py", "x = 2\n")), 2)

    def test_marker_is_removed_on_stop(self):
        self.runAgent("doc-updater", lambda: write(self.d, "README.md", "r\n"))
        self.assertIsNone(agent_identity.readMarker(self.d))

    def test_stale_marker_is_ignored(self):
        agent_identity.start(self.d, {"agent_type": "reviewer"})
        self.assertEqual(agent_identity.activeAgent(self.d, now=time.time() + 3 * 3600), None)


def git(d, *args):
    subprocess.run(["git", "-C", d, *args], check=True, capture_output=True)


def write(d, rel, text):
    full = os.path.join(d, rel)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w", encoding="utf-8") as f:
        f.write(text)


if __name__ == "__main__":
    unittest.main()
