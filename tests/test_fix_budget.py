"""Fix-run marker and diff budget (WI-07): base-commit counting, renames, binaries, stale markers, the hook start."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
PLUGIN = os.path.join(ROOT, "plugins", "forge")
SCRIPTS = os.path.join(PLUGIN, "scripts")
HOOKS = os.path.join(PLUGIN, "templates", "project", "hooks")
sys.path.insert(0, SCRIPTS)

import kit_fix  # noqa: E402

GIT = ["git", "-c", "user.email=a@b", "-c", "user.name=t"]
# Git for Windows bash; a bare "bash" can resolve to WSL on Windows.
BASH = next((p for p in (r"C:\Program Files\Git\usr\bin\bash.exe", r"C:\Program Files\Git\bin\bash.exe") if os.path.exists(p)), "bash")


def git(d, *args):
    subprocess.run(["git", "-C", d, *args], check=True, capture_output=True)


def newRepo(branch="develop"):
    d = tempfile.mkdtemp(prefix="fix-budget-")
    git(d, "init", "-q", "-b", branch)
    write(d, "a.txt", "1\n")
    write(d, "README.md", "r\n")
    git(d, "add", ".")
    subprocess.run([*GIT, "-C", d, "commit", "-q", "-m", "init"], check=True, capture_output=True)
    return d


def write(d, rel, text, mode="w"):
    full = os.path.join(d, rel)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    if "b" in mode:
        with open(full, mode) as f:
            f.write(text)
    else:
        with open(full, mode, encoding="utf-8") as f:
            f.write(text)


def commit(d, msg="wip"):
    git(d, "add", "-A")
    subprocess.run([*GIT, "-C", d, "commit", "-q", "-m", msg], check=True, capture_output=True)


class FixBudget(unittest.TestCase):
    def setUp(self):
        self.d = newRepo()
        self.addCleanup(shutil.rmtree, self.d, True)
        self.assertEqual(kit_fix.start(self.d), 0)

    def test_marker_records_base_and_branch(self):
        data = kit_fix.readMarker(self.d)
        self.assertEqual(data["branch"], "develop")
        self.assertEqual(len(data["base_sha"]), 40)
        self.assertEqual(data["budget"]["code"], {"files": 3, "lines": 20})

    def test_mid_fix_commit_does_not_reset_the_count(self):
        write(self.d, "a.txt", "\n".join(str(i) for i in range(30)) + "\n")
        commit(self.d)
        totals = kit_fix.measure(self.d, kit_fix.readMarker(self.d)["base_sha"])
        self.assertGreater(totals["code"]["lines"], 20)  # the commit did not reset the base
        self.assertEqual(kit_fix.check(self.d), 2)

    def test_untracked_files_count(self):
        for i in range(4):
            write(self.d, f"new_{i}.py", "x = 1\n")
        self.assertEqual(kit_fix.check(self.d), 2)

    def test_untracked_large_file_is_flagged(self):
        write(self.d, "big.py", "\n".join(str(i) for i in range(kit_fix.BIG_UNTRACKED_LINES + 5)) + "\n")
        self.assertEqual(kit_fix.check(self.d), 2)

    def test_binary_file_is_flagged(self):
        write(self.d, "img.bin", b"\0\1\2", mode="wb")
        self.assertEqual(kit_fix.check(self.d), 2)

    def test_rename_counts_as_one_file(self):
        git(self.d, "mv", "a.txt", "b.txt")
        totals = kit_fix.measure(self.d, kit_fix.readMarker(self.d)["base_sha"])
        self.assertEqual(totals["code"]["files"], 1)
        self.assertEqual(kit_fix.check(self.d), 0)

    def test_tests_have_their_own_cap(self):
        write(self.d, "tests/test_a.py", "\n".join(str(i) for i in range(50)) + "\n")
        self.assertEqual(kit_fix.check(self.d), 0)  # 50 test lines fit the 60-line test cap
        write(self.d, "tests/test_b.py", "x\n")
        self.assertEqual(kit_fix.check(self.d), 2)  # a second test file is over the 1-file cap

    def test_finish_refuses_over_budget_and_keeps_marker(self):
        write(self.d, "a.txt", "\n".join(str(i) for i in range(30)) + "\n")
        self.assertEqual(kit_fix.finish(self.d), 2)
        self.assertIsNotNone(kit_fix.readMarker(self.d))

    def test_finish_removes_marker_within_budget(self):
        write(self.d, "a.txt", "2\n")
        self.assertEqual(kit_fix.finish(self.d), 0)
        self.assertIsNone(kit_fix.readMarker(self.d))

    def test_stale_marker_is_cleared_not_enforced(self):
        data = kit_fix.readMarker(self.d)
        data["started_epoch"] = time.time() - 13 * 3600
        kit_fix.writeMarker(self.d, data)
        write(self.d, "a.txt", "\n".join(str(i) for i in range(30)) + "\n")
        self.assertEqual(kit_fix.check(self.d), 0)
        self.assertIsNone(kit_fix.readMarker(self.d))

    def test_marker_from_another_branch_is_stale(self):
        data = kit_fix.readMarker(self.d)
        data["branch"] = "feature/other"
        self.assertTrue(kit_fix.isStale(data, "develop"))

    def test_legacy_empty_marker_is_stale(self):
        kit_fix.writeMarker(self.d, {})
        kit_fix.clearStale(self.d)
        self.assertIsNone(kit_fix.readMarker(self.d))

    def test_start_refuses_dirty_tree(self):
        os.remove(kit_fix.markerPath(self.d))
        write(self.d, "a.txt", "dirty\n")
        self.assertEqual(kit_fix.start(self.d), 3)
        self.assertIsNone(kit_fix.readMarker(self.d))

    def test_prompt_hook_creates_marker(self):
        os.remove(kit_fix.markerPath(self.d))
        payload = json.dumps({"prompt": "/forge:hotfix login broke", "cwd": self.d, "session_id": "s1"})
        subprocess.run([sys.executable, os.path.join(SCRIPTS, "fix_prompt.py")], input=payload.encode(), check=True, capture_output=True)
        data = kit_fix.readMarker(self.d)
        self.assertEqual(data["command"], "/forge:hotfix")
        self.assertEqual(data["session_id"], "s1")

    def test_prompt_hook_ignores_other_prompts(self):
        os.remove(kit_fix.markerPath(self.d))
        payload = json.dumps({"prompt": "please fix the login", "cwd": self.d})
        subprocess.run([sys.executable, os.path.join(SCRIPTS, "fix_prompt.py")], input=payload.encode(), check=True, capture_output=True)
        self.assertIsNone(kit_fix.readMarker(self.d))

    def test_h5_untracked_new_files_count_against_budget(self):
        for i in range(5):
            write(self.d, f"new_{i}.py", "x = 1\n")
        self.assertEqual(self.stop(), 2)

    def test_h6_commit_mid_fix_does_not_reset_budget(self):
        write(self.d, "a.txt", "\n".join(str(i) for i in range(30)) + "\n")
        commit(self.d, "partial fix")
        self.assertEqual(self.stop(), 2)

    def test_h7_hook_starts_run_even_if_model_skips_step_one(self):
        # The model never creates the marker itself: the prompt hook does, so the budget applies.
        os.remove(kit_fix.markerPath(self.d))
        payload = json.dumps({"prompt": "/forge:fix login broke", "cwd": self.d, "session_id": "s2"})
        subprocess.run([sys.executable, os.path.join(SCRIPTS, "fix_prompt.py")], input=payload.encode(), check=True, capture_output=True)
        for i in range(5):
            write(self.d, f"new_{i}.py", "x = 1\n")
        self.assertEqual(self.stop(), 2)

    def stop(self):
        env = dict(os.environ, CLAUDE_PLUGIN_ROOT=PLUGIN)
        return subprocess.run([BASH, os.path.join(HOOKS, "diff_budget.sh")], cwd=self.d, env=env,
                              input=b"{}", capture_output=True).returncode

    def test_stop_loop_guard_lets_a_retry_finish(self):
        write(self.d, "a.txt", "\n".join(str(i) for i in range(30)) + "\n")
        env = dict(os.environ, CLAUDE_PLUGIN_ROOT=PLUGIN)
        r = subprocess.run([BASH, os.path.join(HOOKS, "diff_budget.sh")], cwd=self.d, env=env,
                           input=b'{"stop_hook_active": true}', capture_output=True)
        self.assertEqual(r.returncode, 0)
        r = subprocess.run([BASH, os.path.join(HOOKS, "diff_budget.sh")], cwd=self.d, env=env,
                           input=b"{}", capture_output=True)
        self.assertEqual(r.returncode, 2)


if __name__ == "__main__":
    unittest.main()
