"""Layer 2 of the fail-closed hook launcher. Stdlib only.

run <hook>   Read the hook event on stdin and run the hook. Every failure becomes exit 2 with a
             reason and a fix. A hook's own exit 2 is forwarded as a denial.
selfcheck    SessionStart: check Python, the hook files and that settings wire every hook through the
             launcher. On failure write .claude/learn/selfcheck.failed; while it exists, PreToolUse denies.
Break-glass: ~/.kit/breakglass holds one ISO-8601 expiry, at most 4 hours ahead. While it is active,
             errors (never denials) become warnings and are logged as gate.breakglass.
Minimal:     KIT_HOOKS=minimal skips hooks off protected branches only.
"""
import datetime
import json
import os
import re
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import kit_common  # noqa: E402
import kit_log  # noqa: E402
import kit_policy  # noqa: E402

DEFAULT_TIMEOUT = 10.0
STDOUT_CAP = 64 * 1024
MAX_BREAKGLASS = datetime.timedelta(hours=4)
MIN_PYTHON = (3, 9)
SENTINEL = os.path.join(".claude", "learn", "selfcheck.failed")
FIXES = {
    "invalid input": "the hook got bad JSON on stdin. Run the hook by hand with a sample event to see what it expects.",
    "timeout": "the hook ran longer than the limit. Fix the slow step or raise KIT_HOOK_TIMEOUT.",
    "crash": "the hook exited without deciding. Run the script by hand to see the traceback.",
    "missing script": "the hook file is gone. Restore scripts/hooks from the kit templates.",
    "missing bash": "install Git for Windows (Git Bash) or put bash on PATH, or set KIT_BASH.",
    "selfcheck": "the session self-check failed. Run: python <kit>/scripts/hook_main.py selfcheck",
}


def readSentinel(path):
    try:
        with open(path, encoding="utf-8") as f:
            return f.read().strip()
    except OSError:
        return ""


def hookName(path):
    return os.path.splitext(os.path.basename(path))[0]


def failureMessage(name, cls, extra=""):
    return f"hook {name} failed ({cls}): {FIXES[cls]}" + (f" [{extra}]" if extra else "")


def readPayload(raw):
    """Minimal schema for the hook event. Returns (payload, problem)."""
    try:
        doc = json.loads(raw)
    except ValueError:
        return None, "not JSON"
    if not isinstance(doc, dict):
        return None, "not an object"
    if not isinstance(doc.get("hook_event_name"), str):
        return None, "no hook_event_name"
    if doc["hook_event_name"] == "PreToolUse" and not isinstance(doc.get("tool_name"), str):
        return None, "PreToolUse without tool_name"
    return doc, ""


def breakglassActive(now=None):
    try:
        with open(os.path.join(kit_common.KIT_DIR, "breakglass"), encoding="utf-8") as f:
            text = f.read().strip()
        until = datetime.datetime.fromisoformat(text.replace("Z", "+00:00"))
    except (OSError, ValueError):
        return False
    if until.tzinfo is None:
        return False  # an expiry without a zone is ambiguous: not active
    now = now or datetime.datetime.now(datetime.timezone.utc)
    return now < until <= now + MAX_BREAKGLASS


def currentBranch(cwd):
    try:
        out = subprocess.run(["git", "-C", cwd, "branch", "--show-current"], capture_output=True, text=True, timeout=5)
        return out.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return ""


def bashPath():
    return os.environ.get("KIT_BASH") or shutil.which("bash")


def runHook(hookPath, raw, cwd, env):
    """Returns (status, stdout, stderr, cls). status is ok, deny or error."""
    if hookPath.endswith(".sh"):
        bash = bashPath()
        if not bash:
            return "error", "", "", "missing bash"
        argv = [bash, hookPath]
    else:
        argv = [sys.executable, hookPath]
    try:
        timeout = float(env.get("KIT_HOOK_TIMEOUT") or DEFAULT_TIMEOUT)
        r = subprocess.run(argv, input=raw.encode("utf-8"), capture_output=True, cwd=cwd, env=env, timeout=timeout)
    except subprocess.TimeoutExpired:
        return "error", "", "", "timeout"
    except OSError:
        return "error", "", "", "missing script"
    out = r.stdout.decode("utf-8", errors="replace")[:STDOUT_CAP]
    err = r.stderr.decode("utf-8", errors="replace")
    if r.returncode == 0:
        return "ok", out, err, ""
    if r.returncode == 2:
        return "deny", out, err, ""
    return "error", out, err, "crash"


def cmdRun(hookPath):
    raw = sys.stdin.buffer.read().decode("utf-8", errors="replace")
    name = hookName(hookPath)
    env = dict(os.environ)
    cwd = env.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    if env.get("KIT_HOOKS") == "minimal":
        policy = kit_policy.loadOrDeny()
        if not kit_policy.isProtectedBranch(policy, currentBranch(cwd)):
            return 0  # minimal is local-only: protected branches always run every hook
    payload, problem = readPayload(raw)
    sentinel = os.path.join(cwd, SENTINEL)
    if not os.path.isfile(hookPath):
        status, out, err, cls = "error", "", "", "missing script"
    elif payload is None:
        status, out, err, cls = "error", "", "", "invalid input"
    elif payload.get("hook_event_name") == "PreToolUse" and os.path.isfile(sentinel):
        status, out, err, cls = "error", "", "", "selfcheck"
    else:
        status, out, err, cls = runHook(hookPath, raw, cwd, env)
    if status == "ok":
        sys.stdout.write(out)
        return 0
    if status == "deny":
        sys.stdout.write(out)
        sys.stderr.write(err)
        return 2
    msg = failureMessage(name, cls, readSentinel(sentinel) if cls == "selfcheck" else problem)
    if breakglassActive():
        sys.stderr.write("WARNING breakglass: " + msg + " (allowed while breakglass is active)\n")
        kit_log.event("gate.breakglass", agent=name, reason_code=cls, severity="warn", detail=msg, cwd=cwd)
        return 0
    sys.stderr.write(msg + "\n")
    kit_log.event("gate", agent=name, reason_code=cls, severity="block", detail=msg, cwd=cwd)
    return 2


def hookCommands(settings):
    for event, groups in settings.get("hooks", {}).items():
        for group in groups:
            for h in group.get("hooks", []):
                if h.get("type") == "command":
                    yield event, h.get("command", "")


def selfcheck(projectDir):
    """Writes or clears the sentinel. Always exits 0 so the session is never blocked."""
    problems = []
    if sys.version_info < MIN_PYTHON:
        problems.append(f"Python {sys.version_info[0]}.{sys.version_info[1]} is older than {MIN_PYTHON[0]}.{MIN_PYTHON[1]}")
    settingsPath = os.path.join(projectDir, ".claude", "settings.json")
    try:
        with open(settingsPath, encoding="utf-8") as f:
            settings = json.load(f)
    except (OSError, ValueError) as e:
        settings = None
        problems.append(f"cannot read .claude/settings.json ({e.__class__.__name__})")
    if settings is not None:
        for event, cmd in hookCommands(settings):
            if "hook_launch.sh" not in cmd:
                problems.append(f"{event} hook is not wrapped by hook_launch.sh")
            for rel in re.findall(r"\$CLAUDE_PROJECT_DIR/([^\"'\s]+)", cmd):
                if not os.path.isfile(os.path.join(projectDir, rel)):
                    problems.append(f"missing {rel}")
    sentinel = os.path.join(projectDir, SENTINEL)
    if problems:
        text = "; ".join(problems)
        os.makedirs(os.path.dirname(sentinel), exist_ok=True)
        with open(sentinel, "w", encoding="utf-8", newline="\n") as f:
            f.write(text + "\n")
        sys.stdout.write(f"forgekit selfcheck FAILED: {text}. Tool calls are denied until this passes.\n")
        kit_log.event("gate", agent="selfcheck", reason_code="selfcheck", severity="block", detail=text, cwd=projectDir)
    else:
        if os.path.isfile(sentinel):
            os.remove(sentinel)
        sys.stdout.write("forgekit selfcheck: ok\n")
    return 0


def main(argv):
    try:
        if len(argv) == 2 and argv[0] == "run":
            return cmdRun(argv[1])
        if argv == ["selfcheck"]:
            return selfcheck(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd())
    except Exception as e:  # an unexpected error in the wrapper is a failed gate, never an allow
        if argv and argv[0] == "run":
            sys.stderr.write(failureMessage(hookName(argv[1]), "crash", e.__class__.__name__) + "\n")
            return 2
        sys.stdout.write(f"forgekit selfcheck FAILED: {e.__class__.__name__}\n")
        return 0
    sys.stderr.write("usage: hook_main.py run <hook> | selfcheck\n")
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
