import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SCRIPTS = os.path.join(ROOT, "plugins", "forge", "scripts")
HOOKS = os.path.join(ROOT, "plugins", "forge", "templates", "project", "hooks")
# On Windows, plain "bash" can resolve to WSL's bash.exe, which cannot see Windows paths.
# Prefer Git Bash when it is installed, else fall back to PATH.
def _rmRo(func, path, _exc):
    # Windows: git marks object files read-only, so plain rmtree fails on cleanup.
    os.chmod(path, 0o666)
    func(path)


BASH = next((p for p in (r"C:\Program Files\Git\usr\bin\bash.exe", r"C:\Program Files\Git\bin\bash.exe") if os.path.exists(p)), "bash")
sys.path.insert(0, SCRIPTS)
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, HOOKS)

import kit_mem  # noqa: E402
import kit_new  # noqa: E402
import kit_claim  # noqa: E402
import kit_status  # noqa: E402
import kit_pull  # noqa: E402
import style_sample  # noqa: E402
import check_kit  # noqa: E402
import importlib.util  # noqa: E402

SPEC = importlib.util.spec_from_file_location("test_guard", os.path.join(HOOKS, "test_guard.py"))
TEST_GUARD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(TEST_GUARD)


class TmpCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, True)


class MemTests(TmpCase):
    def test_add_search_show(self):
        mid = kit_mem.add("gotcha", "Alembic needs APP_ENV", "Set APP_ENV first.", self.tmp)
        self.assertEqual(mid, "m001")
        self.assertEqual(kit_mem.nextId(self.tmp), "m002")
        self.assertIn("m001", kit_mem.search(["alembic"], self.tmp)[0])
        self.assertIn("Set APP_ENV", kit_mem.show("m001", self.tmp))

    def test_title_and_body_limits(self):
        with self.assertRaises(SystemExit):
            kit_mem.add("fix", " ".join(["w"] * 11), "x", self.tmp)
        with self.assertRaises(SystemExit):
            kit_mem.add("fix", "ok", "x" * 700, self.tmp)
        with self.assertRaises(SystemExit):
            kit_mem.add("nonsense", "ok", "x", self.tmp)

    def test_index_stays_in_budget(self):
        for i in range(120):
            kit_mem.add("fix", f"entry number {i} about something", "b", self.tmp)
        out = kit_mem.index(self.tmp)
        self.assertLessEqual(len(out.encode()), kit_mem.INDEX_BYTES + 200)
        self.assertIn("more:", out)
        self.assertEqual(kit_mem.index(tempfile.mkdtemp()), "")

    def test_inbox_group_promote_and_clear(self):
        p = os.path.join(self.tmp, "inbox")
        with open(p, "w") as f:
            for proj in ("a", "b", "b"):
                f.write(f"2026-11-01\tbranch_guard\t{proj}\tedit blocked on qa\n")
            f.write("2026-11-02\ttest_guard\ta\tremoves asserts\n")
        out = kit_mem.inbox(path=p)
        self.assertIn("3x branch_guard:edit blocked on qa", out)
        self.assertIn("PROMOTE?", out.splitlines()[0])
        self.assertNotIn("PROMOTE?", out.splitlines()[1])
        kit_mem.inbox(clear="branch_guard:edit blocked on qa", path=p)
        self.assertEqual(len(kit_mem.readInbox(p)), 1)


def makeRepo(tmp):
    repo = os.path.join(tmp, "repo")
    os.makedirs(os.path.join(repo, "plugins", "forge"))
    json.dump({"units": {"skills": {}, "agents": {"a1": {}}, "commands": {}}}, open(os.path.join(repo, "kit.json"), "w"))
    return repo


class NewClaimStatusTests(TmpCase):
    def test_new_registers_and_refuses_duplicates(self):
        repo = makeRepo(self.tmp)
        path = kit_new.create(repo, "skill", "my-skill")
        self.assertTrue(os.path.exists(path))
        self.assertIn("my-skill", json.load(open(os.path.join(repo, "kit.json")))["units"]["skills"])
        with self.assertRaises(SystemExit):
            kit_new.create(repo, "skill", "my-skill")
        with self.assertRaises(SystemExit):
            kit_new.create(repo, "agent", "Bad Name")

    def _claudeDir(self, text):
        d = os.path.join(self.tmp, "claude")
        os.makedirs(os.path.join(d, "agents"))
        open(os.path.join(d, "agents", "mine.md"), "w").write(text)
        return d

    def test_claim_dry_run_then_apply(self):
        repo = makeRepo(self.tmp)
        d = self._claudeDir("---\nname: mine\n---\nhello\n")
        info = kit_claim.claim(repo, "agent", "mine", apply=False, claudeDir=d)
        self.assertEqual(info["hits"], [])
        self.assertFalse(os.path.exists(info["target"]))
        info = kit_claim.claim(repo, "agent", "mine", apply=True, claudeDir=d)
        self.assertTrue(os.path.exists(info["target"]))
        self.assertIn("mine", json.load(open(os.path.join(repo, "kit.json")))["units"]["agents"])
        self.assertTrue(os.path.exists(os.path.join(d, "agents", "mine.md")))  # original stays

    def test_claim_blocks_on_secret_or_path(self):
        repo = makeRepo(self.tmp)
        d = self._claudeDir("path C:\\Users\\Someone\\x and AKIAABCDEFGHIJKLMNOP")
        info = kit_claim.claim(repo, "agent", "mine", apply=True, claudeDir=d)
        self.assertTrue(info["hits"])
        self.assertFalse(os.path.exists(info["target"]))

    def test_status_lists_orphans_ignored_drifted(self):
        repo = makeRepo(self.tmp)
        d = os.path.join(self.tmp, "claude")
        os.makedirs(os.path.join(d, "agents"))
        os.makedirs(os.path.join(d, "skills", "s1"))
        open(os.path.join(d, "agents", "a1.md"), "w").write("local edit")
        os.makedirs(os.path.join(repo, "plugins", "forge", "agents"))
        open(os.path.join(repo, "plugins", "forge", "agents", "a1.md"), "w").write("repo version")
        open(os.path.join(d, "agents", "stray.md"), "w").write("x")
        open(os.path.join(d, "skills", "s1", "SKILL.md"), "w").write("x")
        os.environ["FORGE_HOME"] = self.tmp
        import kit_common
        kit_common.KIT_DIR = self.tmp
        open(os.path.join(self.tmp, "local-ignore"), "w").write("skill:s1\n")
        o, i, dr = kit_status.status(repo, d)
        self.assertEqual(o, ["agent:stray"])
        self.assertEqual(i, ["skill:s1"])
        self.assertEqual(dr, ["agent:a1"])


class PullStyleTests(TmpCase):
    def test_newer_tags(self):
        tags = ["v0.1.0", "v0.2.0", "v0.10.0", "v0.2.0-rc1", "junk"]
        self.assertEqual(kit_pull.newerTags(tags, "v0.2.0"), ["v0.10.0"])

    def test_style_sample_counts_and_prints_no_code(self):
        p = os.path.join(self.tmp, "m.py")
        open(p, "w").write("import logging\nclass Foo:\n    def getName(self) -> str:\n        '''d'''\n        return 'secret-code'\n")
        c = style_sample.sample([p])
        self.assertEqual(c["fn_camel"], 1)
        self.assertEqual(c["cls_pascal"], 1)


class HookTests(TmpCase):
    def test_test_guard_blocks_assert_removal_and_skips(self):
        ti = {"file_path": "x/tests/unit/test_a.py", "old_string": "assert a == 1", "new_string": "pass"}
        self.assertIn("removes assert", TEST_GUARD.check(ti))
        ti = {"file_path": "x/tests/unit/test_a.py", "old_string": "x", "new_string": "@pytest.mark.skip"}
        self.assertIn("adds", TEST_GUARD.check(ti))
        ti = {"file_path": "x/app/a.py", "old_string": "assert a", "new_string": "pass"}
        self.assertIsNone(TEST_GUARD.check(ti))
        ti = {"file_path": "x/tests/unit/test_a.py", "old_string": "assert a", "new_string": "assert a\nassert b"}
        self.assertIsNone(TEST_GUARD.check(ti))

    def _git(self, branch):
        d = os.path.join(self.tmp, "g")
        os.makedirs(d, exist_ok=True)
        subprocess.run(["git", "init", "-q", "-b", branch, d], check=True)
        subprocess.run(["git", "-C", d, "-c", "user.email=a@b", "-c", "user.name=t", "commit", "-q", "--allow-empty", "-m", "i"], check=True)
        return d

    def test_branch_guard(self):
        env = dict(os.environ, HOME=self.tmp)
        for branch, code in (("master", 2), ("qa", 2), ("develop", 0)):
            d = self._git(branch)
            r = subprocess.run([BASH, os.path.join(HOOKS, "branch_guard.sh")], cwd=d, env=env, capture_output=True)
            self.assertEqual(r.returncode, code, branch)
            shutil.rmtree(d, onerror=_rmRo)
        self.assertTrue(os.path.exists(os.path.join(self.tmp, ".kit", "inbox")))

    def test_diff_budget(self):
        d = self._git("develop")
        env = dict(os.environ, HOME=self.tmp)
        run = lambda: subprocess.run([BASH, os.path.join(HOOKS, "diff_budget.sh")], cwd=d, env=env, input=b"{}", capture_output=True).returncode
        self.assertEqual(run(), 0)  # no marker file
        os.makedirs(os.path.join(d, ".claude"))
        open(os.path.join(d, ".claude", "fix-active"), "w").close()
        open(os.path.join(d, "a.txt"), "w").write("1\n")
        subprocess.run(["git", "-C", d, "add", "a.txt"], check=True)
        subprocess.run(["git", "-C", d, "-c", "user.email=a@b", "-c", "user.name=t", "commit", "-q", "-m", "a"], check=True)
        open(os.path.join(d, "a.txt"), "w").write("\n".join(str(i) for i in range(30)) + "\n")
        self.assertEqual(run(), 2)  # 30 lines changed > 20
        open(os.path.join(d, "a.txt"), "w").write("1\n2\n")
        self.assertEqual(run(), 0)


class KitIntegrity(unittest.TestCase):
    def test_check_kit_clean_on_this_repo(self):
        probs, info = check_kit.checkAll(tokens=True, plugin=os.path.join(ROOT, "plugins", "forge"), root=ROOT)
        self.assertEqual(probs, [])
        self.assertEqual(len(info), 9)

    def test_check_kit_detects_problems(self):
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp, True)
        shutil.copytree(ROOT, os.path.join(tmp, "k"), ignore=shutil.ignore_patterns(".git", "__pycache__"))
        k = os.path.join(tmp, "k")
        open(os.path.join(k, "plugins", "forge", "agents", "reviewer.md"), "a").write("\nlaunch `ghost` agent. See /forge:nothing. C:\\Users\\Bob\\x\n")
        probs, _ = check_kit.checkAll(tokens=False, plugin=os.path.join(k, "plugins", "forge"), root=k)
        joined = "\n".join(probs)
        self.assertIn("ghost", joined)
        self.assertIn("/forge:nothing", joined)
        self.assertIn("Windows home path", joined)


class V03Tests(unittest.TestCase):
    def test_kit_hooks_minimal_disables_test_guard_and_diff_budget(self):
        os.environ["KIT_HOOKS"] = "minimal"
        try:
            bad = {"file_path": "tests/test_x.py", "old_string": "assert x == 1", "new_string": "pass"}
            self.assertIsNone(TEST_GUARD.check(bad))
        finally:
            del os.environ["KIT_HOOKS"]
        self.assertIsNotNone(TEST_GUARD.check({"file_path": "tests/test_x.py", "old_string": "assert x == 1", "new_string": "pass"}))

    def test_notice_is_silent_without_repo(self):
        env = dict(os.environ, FORGE_HOME=tempfile.mkdtemp())
        env.pop("FORGE_REPO", None)
        r = subprocess.run([sys.executable, os.path.join(SCRIPTS, "kit_pull.py"), "--notice"], env=env, capture_output=True, text=True)
        self.assertEqual((r.returncode, r.stdout.strip()), (0, ""))

    def test_session_start_runs_index_and_notice(self):
        cmds = json.load(open(os.path.join(ROOT, "plugins", "forge", "hooks", "hooks.json")))["hooks"]["SessionStart"][0]["hooks"]
        joined = " ".join(c["command"] for c in cmds)
        self.assertIn("kit_mem.py", joined)
        self.assertIn("--notice", joined)

    def test_skill_requiring_another_skill_is_flagged(self):
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp, True)
        shutil.copytree(ROOT, os.path.join(tmp, "k"), ignore=shutil.ignore_patterns(".git", "__pycache__"))
        k = os.path.join(tmp, "k")
        with open(os.path.join(k, "plugins", "forge", "skills", "python-style", "SKILL.md"), "a", encoding="utf-8") as f:
            f.write("\nRequires the `config-db` skill.\n")
        probs, _ = check_kit.checkAll(tokens=False, plugin=os.path.join(k, "plugins", "forge"), root=k)
        self.assertTrue(any("depends on skill 'config-db'" in p for p in probs))

    def test_full_feature_preload_under_8k_tokens(self):
        _, info = check_kit.checkAll(tokens=True, plugin=os.path.join(ROOT, "plugins", "forge"), root=ROOT)
        feature = ["tester", "developer", "reviewer", "security-reviewer", "ops", "ai-evaluator", "doc-updater"]
        self.assertLess(sum(info[a] for a in feature), 8200)  # plan target: about 8k


class NamingTests(unittest.TestCase):
    def test_naming_lint_flags_violations(self):
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp, True)
        shutil.copytree(ROOT, os.path.join(tmp, "k"), ignore=shutil.ignore_patterns(".git", "__pycache__"))
        k = os.path.join(tmp, "k")
        with open(os.path.join(k, "tools", "bad-name.py"), "w", encoding="utf-8") as f:
            f.write("my_var = 1\ndef do_thing():\n    pass\n")
        probs, _ = check_kit.checkAll(tokens=False, plugin=os.path.join(k, "plugins", "forge"), root=k)
        joined = "\n".join(probs)
        self.assertIn("must be snake_case", joined)
        self.assertIn("function do_thing must be camelCase", joined)
        self.assertIn("variable my_var must be SCREAMING_SNAKE_CASE", joined)


class CommandRegressionTests(unittest.TestCase):
    def test_ci_frontend_job_survives_a_missing_frontend_dir(self):
        ci = open(os.path.join(ROOT, "plugins", "forge", "templates", "ci", "ci.yml"), encoding="utf-8").read()
        job = ci[ci.index("  frontend:"):ci.index("  develop:")]
        self.assertNotIn("defaults:", job)
        self.assertIn("frontend/package.json", job)
        dep = open(os.path.join(ROOT, "plugins", "forge", "skills", "dependency-policy", "SKILL.md"), encoding="utf-8").read()
        self.assertIn("ruff, mypy, bandit, pip-audit", dep)

    def test_secret_deny_rule_still_lets_reviewers_read_examples(self):
        s = open(os.path.join(ROOT, "plugins", "forge", "templates", "project", "settings.json"), encoding="utf-8").read()
        self.assertIn("secrets/*-secrets.properties)", s)
        self.assertNotIn("secrets/**", s)

    def test_uvicorn_target_follows_naming_rule(self):
        sup = open(os.path.join(ROOT, "plugins", "forge", "templates", "docker", "supervisord.conf"), encoding="utf-8").read()
        self.assertIn("app.main:APP", sup)

    def test_config_tests_never_read_secrets_and_nginx_404s_without_frontend(self):
        base = os.path.join(ROOT, "plugins", "forge")
        self.assertIn("never read `secrets/*`", open(os.path.join(base, "skills", "test-levels", "SKILL.md"), encoding="utf-8").read())
        self.assertIn("=404", open(os.path.join(base, "templates", "docker", "nginx.conf"), encoding="utf-8").read())

    def test_baseline_gate_skip_uses_git_ls_files(self):
        self.assertIn("git ls-files backend", self.read("feature.md"))

    def read(self, name):
        return open(os.path.join(ROOT, "plugins", "forge", "commands", name), encoding="utf-8").read()

    def test_doctor_does_not_curl_the_internal_emulator_port(self):
        t = self.read("doctor.md")
        self.assertNotIn("curl -s -o /dev/null", t)
        self.assertIn("{{.Health}}", t)
        self.assertIn("test -f secrets/", t)

    def test_feature_runs_tool_doctor_and_fix_runs_stack_doctor(self):
        self.assertNotIn("Run `/forge:doctor`", self.read("feature.md"))
        self.assertIn("docker compose version", self.read("feature.md"))
        self.assertIn("/forge:doctor stack", self.read("fix.md"))

    def test_design_file_is_named_by_id_only(self):
        self.assertIn("docs/design/<id>.md", self.read("design.md"))

    def test_adopt_project_does_not_call_doctor(self):
        self.assertNotIn("Run `/forge:doctor`", self.read("adopt-project.md"))


if __name__ == "__main__":
    unittest.main()
