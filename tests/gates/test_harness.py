"""Self-tests for the gate harness: the decision mapping and each failure injection."""
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import harness  # noqa: E402


def settingsWith(command, matcher="Edit"):
    return {"hooks": {"PreToolUse": [{"matcher": matcher, "hooks": [{"type": "command", "command": command}]}]}}


PY_STUB = "python \"$CLAUDE_PROJECT_DIR/scripts/hooks/stub.py\""
EDIT = {"tool": "Edit", "input": {"file_path": "app.py", "old_string": "a", "new_string": "b"}, "branch": "develop"}


def stubCase(script, **extra):
    case = dict(EDIT, scripts={"stub.py": script}, **extra)
    return case


class DecisionMappingTests(unittest.TestCase):
    def run_(self, script, settings=None, **extra):
        return harness.runCase(stubCase(script, **extra), settings or settingsWith(PY_STUB))

    def test_exit_2_is_deny(self):
        self.assertEqual(self.run_("raise SystemExit(2)")["decision"], "deny")

    def test_exit_0_is_allow(self):
        self.assertEqual(self.run_("raise SystemExit(0)")["decision"], "allow")

    def test_other_exit_is_error_not_deny(self):
        got = self.run_("raise SystemExit(1)")
        self.assertEqual(got["decision"], "error")
        self.assertEqual(got["codes"], [1])

    def test_no_matching_hook_is_allow_with_no_codes(self):
        got = harness.runCase(dict(EDIT, tool="Bash", input={"command": "ls"}), settingsWith(PY_STUB))
        self.assertEqual((got["decision"], got["codes"]), ("allow", []))

    def test_matcher_is_a_full_match(self):
        got = harness.runCase(dict(EDIT, tool="EditX"), settingsWith(PY_STUB))
        self.assertEqual(got["codes"], [])

    def test_timeout_is_recorded_as_error(self):
        got = self.run_("import time\ntime.sleep(30)\n", timeout=2)
        self.assertEqual(got["codes"], ["timeout"])
        self.assertEqual(got["decision"], "error")

    def test_stub_reads_the_malformed_stdin(self):
        script = "import json, sys\ntry:\n    json.load(sys.stdin)\nexcept ValueError:\n    raise SystemExit(2)\nraise SystemExit(0)\n"
        self.assertEqual(self.run_(script, inject=["malformed_stdin"])["decision"], "deny")
        self.assertEqual(self.run_(script)["decision"], "allow")

    def test_reason_code_comes_from_the_event_store(self):
        script = ("import json, os\n"
                  "p = os.path.join(os.environ['FORGE_HOME'], 'events.jsonl')\n"
                  "os.makedirs(os.path.dirname(p), exist_ok=True)\n"
                  "open(p, 'a').write(json.dumps({'type': 'gate', 'reason_code': 'stub_reason'}) + '\\n')\n"
                  "raise SystemExit(2)\n")
        got = self.run_(script)
        self.assertEqual((got["decision"], got["reason"]), ("deny", "stub_reason"))

    def test_check_reports_mismatch(self):
        ok, msg = harness.check(stubCase("raise SystemExit(0)", expect="deny"), settingsWith(PY_STUB))
        self.assertFalse(ok)
        self.assertIn("expected deny, got allow", msg)

    def test_unknown_injection_is_rejected(self):
        with self.assertRaises(ValueError):
            harness.runCase(dict(EDIT, inject=["nonsense"]), settingsWith(PY_STUB))


class InjectionTests(unittest.TestCase):
    def test_missing_interpreter_makes_python_hooks_error(self):
        try:
            got = harness.runCase(dict(EDIT, scripts={"stub.py": "raise SystemExit(2)"}, inject=["missing_interpreter"]),
                                  settingsWith(PY_STUB))
        except harness.HarnessSkip as e:
            self.skipTest(str(e))
        self.assertEqual(got["codes"], ["missing"])
        self.assertEqual(got["decision"], "error")

    def test_crash_injection_replaces_the_real_gates(self):
        case = dict(EDIT, tool="Edit", input={"file_path": "tests/unit/test_a.py", "old_string": "assert a", "new_string": "pass"},
                    inject=["crash"])
        got = harness.runCase(case)
        self.assertEqual(got["codes"], [1, 1])  # branch_guard.sh and test_guard.py both crash
        self.assertEqual(got["decision"], "error")

    def test_real_gates_still_deny_on_master_with_unreadable_home(self):
        got = harness.runCase(dict(EDIT, branch="master", inject=["unreadable_home"]))
        self.assertEqual(got["decision"], "deny")

    def test_wrong_cwd_still_denies_edit_on_master(self):
        got = harness.runCase(dict(EDIT, branch="master", inject=["wrong_cwd"]))
        self.assertEqual(got["decision"], "deny")


class FixtureTests(unittest.TestCase):
    def test_project_directory_is_removed_after_run(self):
        before = set(os.listdir(os.environ.get("TEMP", "/tmp")))
        harness.runCase(dict(EDIT, scripts={"stub.py": "raise SystemExit(0)"}), settingsWith(PY_STUB))
        after = set(os.listdir(os.environ.get("TEMP", "/tmp")))
        self.assertEqual({n for n in after - before if n.startswith("gate-")}, set())


if __name__ == "__main__":
    unittest.main()
