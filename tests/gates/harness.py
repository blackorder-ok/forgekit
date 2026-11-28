"""Attack-test harness for forgekit gates. Stdlib only.

A case is a synthetic hook event (event name, tool, tool input, branch, optional fixtures).
The harness builds a throwaway project from the template hooks, runs every hook that the
project settings.json wires for that event and tool, and reports what the runtime does:

  exit 2                      -> deny
  every hook exit 0, or none  -> allow
  anything else (crash, timeout, missing interpreter, bad stdin) -> error

Claude Code treats a non-2 exit as a non-blocking error, so "error" lets the action through.
A gate that should block must therefore exit 2 itself; "error" fails every expectation.
"""
import json
import os
import re
import shlex
import shutil
import subprocess
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
PLUGIN = os.path.join(ROOT, "plugins", "forge")
TEMPLATE_HOOKS = os.path.join(PLUGIN, "templates", "project", "hooks")
TEMPLATE_SETTINGS = os.path.join(PLUGIN, "templates", "project", "settings.json")
GIT_USR_BIN = r"C:\Program Files\Git\usr\bin"
BASH = next((p for p in (r"C:\Program Files\Git\usr\bin\bash.exe", r"C:\Program Files\Git\bin\bash.exe") if os.path.exists(p)), "bash")
GIT_ID = ["-c", "user.email=gate@test", "-c", "user.name=gate"]
INJECTIONS = {"malformed_stdin", "missing_interpreter", "crash", "hang", "unreadable_home", "wrong_cwd",
              "missing_script", "spaces_path"}
PLUGIN_POSIX = PLUGIN.replace("\\", "/")
LAUNCHER_ROOT = "${CLAUDE_PLUGIN_ROOT:-$HOME/.kit/repo/plugins/forge}"


class HarnessSkip(Exception):
    """A fixture cannot be built on this machine (for example, python is not removable from PATH)."""


def loadSettings(settings=None):
    if settings is not None:
        return settings
    with open(TEMPLATE_SETTINGS, encoding="utf-8") as f:
        return json.load(f)


def hooksFor(settings, event, tool=None):
    """Commands the settings wire for this event. A matcher is a full regex on the tool name."""
    out = []
    for group in settings.get("hooks", {}).get(event, []):
        matcher = group.get("matcher")
        if matcher and (tool is None or not re.fullmatch(matcher, tool)):
            continue
        out += [h["command"] for h in group.get("hooks", []) if h.get("type") == "command"]
    return out


def permissionDecision(stdout):
    """A hook may answer with JSON on stdout (the Bash gate does). Returns deny, ask or None."""
    try:
        doc = json.loads(stdout.decode("utf-8", errors="replace"))
    except ValueError:
        return None
    if not isinstance(doc, dict):
        return None
    return (doc.get("hookSpecificOutput") or {}).get("permissionDecision")


def combine(codes):
    if not codes:
        return "allow"
    if 2 in codes:
        return "deny"
    if all(c == 0 for c in codes):
        return "allow"
    return "error"


def pathWithoutPython():
    dirs = [os.path.dirname(BASH)]
    git = shutil.which("git")
    if git:
        dirs.append(os.path.dirname(git))
    path = os.pathsep.join(dirs)
    if shutil.which("python", path=path):
        raise HarnessSkip("python is on the bash/git dirs; cannot simulate a missing interpreter")
    return path


def rmTree(path):
    """Windows marks git objects read-only; clear the bit so cleanup succeeds."""
    def clear(func, p, _exc):
        os.chmod(p, 0o666)
        func(p)
    shutil.rmtree(path, onerror=clear)


def gitRun(proj, *args):
    subprocess.run(["git", "-C", proj, *GIT_ID, *args], check=True, capture_output=True)


def stubFor(name, mode):
    """Replacement script for injected failures. Bash hooks exit 1 or hang; Python hooks raise or hang."""
    isBash = name.endswith(".sh")
    if mode == "crash":
        return "exit 1\n" if isBash else 'raise RuntimeError("injected crash")\n'
    if mode == "hang":
        return "sleep 30\n" if isBash else "import time\ntime.sleep(30)\n"
    raise ValueError(mode)


def makeProject(case, inject):
    base = tempfile.mkdtemp(prefix="gate base ") if "spaces_path" in inject else None
    proj = tempfile.mkdtemp(prefix="gate-proj-", dir=base)
    hooks = os.path.join(proj, "scripts", "hooks")
    os.makedirs(hooks)
    for name in os.listdir(TEMPLATE_HOOKS):
        shutil.copyfile(os.path.join(TEMPLATE_HOOKS, name), os.path.join(hooks, name))
    if "missing_script" in inject:
        for name in os.listdir(hooks):
            os.remove(os.path.join(hooks, name))
    if "crash" in inject or "hang" in inject:
        mode = "crash" if "crash" in inject else "hang"
        for name in os.listdir(hooks):
            with open(os.path.join(hooks, name), "w", encoding="utf-8") as f:
                f.write(stubFor(name, mode))
    for name, text in (case.get("scripts") or {}).items():  # self-tests supply their own hook scripts
        with open(os.path.join(hooks, name), "w", encoding="utf-8") as f:
            f.write(text)
    if "wrong_cwd" not in inject and not case.get("not_repo"):
        gitRun(proj, "init", "-q", "-b", "main", ".")
        with open(os.path.join(proj, "app.py"), "w", encoding="utf-8") as f:
            f.write("x = 1\n")
        with open(os.path.join(proj, "README.md"), "w", encoding="utf-8") as f:
            f.write("readme\n")
        gitRun(proj, "add", ".")
        gitRun(proj, "commit", "-q", "-m", "init")
        branch = case.get("branch")
        if branch:
            gitRun(proj, "checkout", "-q", "-B", branch)
        else:
            gitRun(proj, "checkout", "-q", "--detach")
    for name, text in (case.get("untracked") or {}).items():
        full = os.path.join(proj, name)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w", encoding="utf-8") as f:
            f.write(text)
    if case.get("fix_active"):  # a marker as kit_fix.py start writes it, based on the initial commit
        head = subprocess.run(["git", "-C", proj, "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
        os.makedirs(os.path.join(proj, ".claude"), exist_ok=True)
        with open(os.path.join(proj, ".claude", "fix-active"), "w", encoding="utf-8") as f:
            json.dump({"command": "/forge:fix", "base_sha": head, "branch": case.get("branch") or "",
                       "started_epoch": time.time(), "ttl_h": 12}, f)
    return proj


def parseCommand(cmd, projPosix):
    cmd = cmd.replace(LAUNCHER_ROOT, PLUGIN_POSIX).replace("$CLAUDE_PLUGIN_ROOT", PLUGIN_POSIX)
    argv = shlex.split(cmd.replace("$CLAUDE_PROJECT_DIR", projPosix), posix=True)
    if argv and argv[0] == "bash":
        argv[0] = BASH
    return argv


def lastReason(kitHome):
    path = os.path.join(kitHome, "events.jsonl")
    if not os.path.isfile(path):
        return ""
    reason = ""
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            try:
                rec = json.loads(line)
            except ValueError:
                continue
            if rec.get("type") == "gate":
                reason = rec.get("reason_code", "")
    return reason


def runCase(case, settings=None):
    """Run one case. Returns {"decision", "codes", "reason"}; decision is allow, deny or error."""
    settings = loadSettings(settings)
    event = case.get("event", "PreToolUse")
    tool = case.get("tool")
    inject = set(case.get("inject", []))
    unknown = inject - INJECTIONS
    if unknown:
        raise ValueError(f"unknown injection: {unknown}")
    path = None
    if "missing_interpreter" in inject:
        path = pathWithoutPython()
    proj = makeProject(case, inject)
    projPosix = proj.replace("\\", "/")
    home = os.path.join(proj, "home")
    os.makedirs(home, exist_ok=True)
    kitHome = os.path.join(proj, "kit")
    if "unreadable_home" in inject:
        kitHome = os.path.join(proj, "kit-is-a-file")
        open(kitHome, "w").close()
        kitHome = os.path.join(kitHome, "sub")  # a path under a regular file cannot be written
    cwd = proj
    if "wrong_cwd" in inject:
        cwd = tempfile.mkdtemp(prefix="gate-plain-")
    payload = {"hook_event_name": event, "session_id": "gate-test", "cwd": cwd}
    if event == "Stop":
        payload["stop_hook_active"] = False
    else:
        payload.update({"tool_name": tool, "tool_input": case.get("input", {})})
    stdin = "{not json" if "malformed_stdin" in inject else json.dumps(payload)
    env = dict(os.environ)
    env.update({"HOME": home, "USERPROFILE": home, "FORGE_HOME": kitHome,
                "CLAUDE_PLUGIN_ROOT": PLUGIN, "CLAUDE_PROJECT_DIR": projPosix})
    env.pop("CLAUDE_SESSION_ID", None)
    env.pop("KIT_HOOKS", None)
    env.update(case.get("env") or {})
    if path is not None:
        env["PATH"] = path
    if "unreadable_home" not in inject:
        os.makedirs(kitHome, exist_ok=True)
    for name, text in (case.get("kit_files") or {}).items():  # e.g. a breakglass file in the kit home
        with open(os.path.join(kitHome, name), "w", encoding="utf-8") as f:
            f.write(text)
    timeout = case.get("timeout", 20 if "hang" in inject else 10)
    codes, verdicts = [], []
    try:
        for cmd in hooksFor(settings, event, tool):
            argv = parseCommand(cmd, projPosix)
            if argv[0] == "python" and path is not None and not shutil.which("python", path=path):
                codes.append("missing")
                continue
            try:
                r = subprocess.run(argv, input=stdin.encode("utf-8"), capture_output=True,
                                   cwd=cwd, env=env, timeout=timeout)
                codes.append(r.returncode)
                verdicts.append(permissionDecision(r.stdout))
            except subprocess.TimeoutExpired:
                codes.append("timeout")
            except OSError:
                codes.append("missing")
        decision = combine(codes)
        if decision == "allow":  # a JSON permissionDecision refines an exit-0 hook
            decision = "deny" if "deny" in verdicts else "ask" if "ask" in verdicts else "allow"
        return {"decision": decision, "codes": codes, "reason": lastReason(kitHome)}
    finally:
        rmTree(os.path.dirname(proj) if "spaces_path" in inject else proj)
        if cwd != proj:
            rmTree(cwd)


def check(case, settings=None):
    """Return (ok, message). A case passes when the decision and, if given, the reason code match."""
    got = runCase(case, settings)
    problems = []
    if got["decision"] != case["expect"]:
        problems.append(f"expected {case['expect']}, got {got['decision']} (exit codes {got['codes']})")
    if "reason" in case and got["reason"] != case["reason"]:
        problems.append(f"expected reason {case['reason']!r}, got {got['reason']!r}")
    return (not problems, "; ".join(problems) or "ok")
