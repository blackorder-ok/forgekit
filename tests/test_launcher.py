"""Unit tests for the fail-closed hook runner (hook_main.py): payloads, break-glass, selfcheck, exit mapping."""
import contextlib
import datetime
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.join(HERE, "..", "plugins", "forge", "scripts")
sys.path.insert(0, SCRIPTS)

import hook_main  # noqa: E402
import kit_common  # noqa: E402

MAIN = os.path.join(SCRIPTS, "hook_main.py")


class TmpCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="launch test ")  # a space in the path, on purpose
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.kit = os.path.join(self.tmp, "kit")
        os.makedirs(self.kit)
        kc = mock.patch.object(kit_common, "KIT_DIR", self.kit)
        kc.start()
        self.addCleanup(kc.stop)


class PayloadTests(unittest.TestCase):
    def test_accepts_a_pretooluse_event(self):
        doc, problem = hook_main.readPayload(json.dumps({"hook_event_name": "PreToolUse", "tool_name": "Edit"}))
        self.assertEqual((doc["tool_name"], problem), ("Edit", ""))

    def test_rejects_bad_json_and_wrong_shapes(self):
        for raw, why in (("{not json", "not JSON"), ("[]", "not an object"),
                         ('{"tool_name": "Edit"}', "no hook_event_name"),
                         ('{"hook_event_name": "PreToolUse"}', "PreToolUse without tool_name")):
            self.assertEqual(hook_main.readPayload(raw), (None, why), raw)


class BreakglassTests(TmpCase):
    def write(self, text):
        with open(os.path.join(self.kit, "breakglass"), "w", encoding="utf-8") as f:
            f.write(text)

    def ts(self, hours):
        return (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=hours)).strftime("%Y-%m-%dT%H:%M:%SZ")

    def test_active_within_four_hours(self):
        self.write(self.ts(1))
        self.assertTrue(hook_main.breakglassActive())

    def test_expired_or_too_long_or_unzoned_is_inactive(self):
        for text in (self.ts(-1), self.ts(5), "2099-01-01T00:00:00"):
            self.write(text)
            self.assertFalse(hook_main.breakglassActive(), text)

    def test_missing_or_garbage_is_inactive(self):
        self.assertFalse(hook_main.breakglassActive())
        self.write("tomorrow")
        self.assertFalse(hook_main.breakglassActive())


class SelfcheckTests(TmpCase):
    def project(self, settings):
        proj = os.path.join(self.tmp, "proj")
        os.makedirs(os.path.join(proj, ".claude"))
        os.makedirs(os.path.join(proj, "scripts", "hooks"))
        open(os.path.join(proj, "scripts", "hooks", "gate.py"), "w").close()
        if settings is not None:
            with open(os.path.join(proj, ".claude", "settings.json"), "w", encoding="utf-8") as f:
                json.dump(settings, f)
        return proj

    def wired(self, cmd):
        return {"hooks": {"PreToolUse": [{"matcher": "Edit", "hooks": [{"type": "command", "command": cmd}]}]}}

    def runCheck(self, proj):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = hook_main.selfcheck(proj)
        return code, out.getvalue()

    def test_ok_project_clears_sentinel_and_exits_zero(self):
        proj = self.project(self.wired('bash "x/hook_launch.sh" "$CLAUDE_PROJECT_DIR/scripts/hooks/gate.py"'))
        os.makedirs(os.path.join(proj, ".claude", "learn"))
        open(os.path.join(proj, ".claude", "learn", "selfcheck.failed"), "w").close()
        code, out = self.runCheck(proj)
        self.assertEqual(code, 0)
        self.assertIn("ok", out)
        self.assertFalse(os.path.exists(os.path.join(proj, ".claude", "learn", "selfcheck.failed")))

    def test_unwrapped_hook_writes_sentinel_and_warns(self):
        proj = self.project(self.wired('python "$CLAUDE_PROJECT_DIR/scripts/hooks/gate.py"'))
        code, out = self.runCheck(proj)
        self.assertEqual(code, 0)  # SessionStart is never blocked
        self.assertIn("FAILED", out)
        self.assertIn("not wrapped", open(os.path.join(proj, ".claude", "learn", "selfcheck.failed"), encoding="utf-8").read())

    def test_missing_hook_file_is_reported(self):
        proj = self.project(self.wired('bash "x/hook_launch.sh" "$CLAUDE_PROJECT_DIR/scripts/hooks/gone.sh"'))
        _, out = self.runCheck(proj)
        self.assertIn("missing scripts/hooks/gone.sh", out)

    def test_missing_settings_is_reported(self):
        _, out = self.runCheck(self.project(None))
        self.assertIn("cannot read .claude/settings.json", out)


class RunnerTests(TmpCase):
    """Runs hook_main.py as a real process, the way the launcher does."""

    def runner(self, hook_src, payload=None, env=None, proj=None):
        proj = proj or os.path.join(self.tmp, "proj")
        os.makedirs(proj, exist_ok=True)
        hook = os.path.join(proj, "hook.py")
        with open(hook, "w", encoding="utf-8") as f:
            f.write(hook_src)
        raw = json.dumps(payload or {"hook_event_name": "PreToolUse", "tool_name": "Edit"})
        e = dict(os.environ, FORGE_HOME=self.kit, CLAUDE_PROJECT_DIR=proj, KIT_HOOK_TIMEOUT="1")
        e.update(env or {})
        r = subprocess.run([sys.executable, MAIN, "run", hook], input=raw.encode(), capture_output=True, env=e, timeout=30)
        return r.returncode, r.stdout.decode(), r.stderr.decode()

    def test_hook_exit_0_passes_through(self):
        code, _, _ = self.runner("print('fine')")
        self.assertEqual(code, 0)

    def test_hook_exit_2_is_a_denial_with_its_reason(self):
        code, _, err = self.runner("import sys\nsys.stderr.write('no way')\nsys.exit(2)")
        self.assertEqual((code, err), (2, "no way"))

    def test_crash_becomes_exit_2_with_fix(self):
        code, _, err = self.runner("raise RuntimeError('boom')")
        self.assertEqual(code, 2)
        self.assertIn("hook hook failed (crash)", err)

    def test_timeout_becomes_exit_2_with_fix(self):
        code, _, err = self.runner("import time\ntime.sleep(10)")
        self.assertEqual(code, 2)
        self.assertIn("(timeout)", err)

    def test_bad_stdin_becomes_exit_2(self):
        proj = os.path.join(self.tmp, "p2")
        os.makedirs(proj)
        hook = os.path.join(proj, "hook.py")
        open(hook, "w").write("raise SystemExit(0)")
        r = subprocess.run([sys.executable, MAIN, "run", hook], input=b"{bad", capture_output=True,
                           env=dict(os.environ, FORGE_HOME=self.kit), timeout=30)
        self.assertEqual(r.returncode, 2)
        self.assertIn("(invalid input)", r.stderr.decode())

    def test_sentinel_denies_pretooluse_until_selfcheck_passes(self):
        proj = os.path.join(self.tmp, "proj")
        os.makedirs(os.path.join(proj, ".claude", "learn"))
        open(os.path.join(proj, ".claude", "learn", "selfcheck.failed"), "w").write("missing x")
        code, _, err = self.runner("raise SystemExit(0)", proj=proj)
        self.assertEqual(code, 2)
        self.assertIn("(selfcheck)", err)
        self.assertIn("missing x", err)

    def test_sentinel_does_not_block_stop_events(self):
        proj = os.path.join(self.tmp, "proj")
        os.makedirs(os.path.join(proj, ".claude", "learn"))
        open(os.path.join(proj, ".claude", "learn", "selfcheck.failed"), "w").write("missing x")
        code, _, _ = self.runner("raise SystemExit(0)", payload={"hook_event_name": "Stop"}, proj=proj)
        self.assertEqual(code, 0)

    def test_breakglass_downgrades_errors_only(self):
        future = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
        open(os.path.join(self.kit, "breakglass"), "w").write(future)
        code, _, err = self.runner("raise RuntimeError('boom')")
        self.assertEqual(code, 0)
        self.assertIn("WARNING breakglass", err)
        code, _, _ = self.runner("raise SystemExit(2)")
        self.assertEqual(code, 2)  # a real denial still stands

    def test_stdout_is_capped(self):
        code, out, _ = self.runner("print('x' * 200000)")
        self.assertEqual(code, 0)
        self.assertLessEqual(len(out), hook_main.STDOUT_CAP + 1)


if __name__ == "__main__":
    unittest.main()
