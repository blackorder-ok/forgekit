"""Verdict contract (WI-12): verdict-bearing agents end with a VERDICT line; commands resume once, then stop."""
import os
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.join(HERE, "..", "plugins", "forge")

# agent -> the verdict line it must end with
AGENT_VERDICTS = {
    "ops": "VERDICT: GREEN",
    "reviewer": "VERDICT: APPROVE",
    "security-reviewer": "VERDICT: <verdict>",
}
# command -> agents whose verdict it requires
COMMAND_AGENTS = {
    "check": ["ops"],
    "fix": ["ops", "reviewer"],
    "hotfix": ["ops"],
    "feature": ["ops", "reviewer", "security-reviewer"],
    "review": ["reviewer"],
    "security-review": ["security-reviewer"],
}


def read(*parts):
    with open(os.path.join(BASE, *parts), encoding="utf-8") as f:
        return f.read()


class VerdictContract(unittest.TestCase):
    def test_agents_end_with_a_verdict_line(self):
        for agent, marker in AGENT_VERDICTS.items():
            self.assertIn(marker, read("agents", f"{agent}.md"), agent)

    def test_commands_require_a_verdict_and_resume_once(self):
        for cmd, agents in COMMAND_AGENTS.items():
            text = read("commands", f"{cmd}.md")
            self.assertIn("**Missing verdict.**", text, cmd)
            self.assertIn("once with `SendMessage`", text, cmd)
            self.assertIn("`INCOMPLETE`", text, cmd)
            self.assertIn("Never make a third attempt", text, cmd)
            for agent in agents:
                self.assertIn(f"`{agent}`", text, f"{cmd} must launch {agent}")

    def test_every_verdict_agent_is_used_by_a_command(self):
        used = {a for agents in COMMAND_AGENTS.values() for a in agents}
        self.assertEqual(used, set(AGENT_VERDICTS))


if __name__ == "__main__":
    unittest.main()
