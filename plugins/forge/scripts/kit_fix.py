"""Fix-run marker and diff budget (WI-07). Stdlib only.

A /forge:fix or /forge:hotfix run is marked by .claude/fix-active, a JSON file written by the
UserPromptSubmit hook (fix_prompt.py) or by `kit_fix.py start`. It records the base commit, so
commits made during the fix do not reset the budget. The budget counts, against that base:
  tracked changes  git diff --numstat <base>  (committed, staged and unstaged)
  untracked files  git ls-files -o --exclude-standard (counted as added lines)
Test files have their own cap, so a regression test does not use up the code budget.

Commands:  start | measure | check (Stop hook) | warn (PostToolUse) | finish | clear-stale
Exit codes: 0 ok, 2 over budget (check, finish), 3 precondition failed (start).
"""
import datetime
import json
import os
import re
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kit_log  # noqa: E402

MARKER_REL = os.path.join(".claude", "fix-active")
TTL_HOURS = 12
BUDGET = {"code": {"files": 3, "lines": 20}, "tests": {"files": 1, "lines": 60}}
WARN_RATIO = 0.8
BIG_UNTRACKED_LINES = 1000
TEST_RE = re.compile(r"(^|/)(tests?/|test_[^/]*$|[^/]*_test\.py$|[^/]*\.(test|spec)\.[cm]?[jt]sx?$)")


def git(proj, *args):
    r = subprocess.run(["git", "-C", proj, *args], capture_output=True, text=True, encoding="utf-8", errors="replace")
    return r.returncode, r.stdout


def markerPath(proj):
    return os.path.join(proj, MARKER_REL)


def readMarker(proj):
    """Returns None when no run is active, a dict for a valid marker, or {} for a legacy empty file."""
    path = markerPath(proj)
    if not os.path.isfile(path):
        return None
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def writeMarker(proj, data):
    os.makedirs(os.path.dirname(markerPath(proj)), exist_ok=True)
    with open(markerPath(proj), "w", encoding="utf-8", newline="\n") as f:
        json.dump(data, f, indent=2)
        f.write("\n")


def isKitState(path):
    """The .claude folder holds the kit's own state (marker, learn store); it is not part of a change."""
    return path.replace("\\", "/").startswith(".claude/")


def isTest(path):
    return bool(TEST_RE.search(path.replace("\\", "/")))


def bump(totals, path, lines, flagged=False):
    bucket = totals["tests" if isTest(path) else "code"]
    bucket["files"] += 1
    bucket["lines"] += lines
    if flagged:
        totals["flagged"].append(path)


def measure(proj, base):
    """Counts changes since base. Returns {"code", "tests", "flagged"}; flagged lists binary or huge new files."""
    totals = {"code": {"files": 0, "lines": 0}, "tests": {"files": 0, "lines": 0}, "flagged": []}
    rc, out = git(proj, "diff", "--numstat", base)
    if rc != 0:
        raise ValueError(f"cannot diff against base {base!r}")
    for line in out.splitlines():
        parts = line.split("\t")
        if len(parts) < 3 or isKitState(parts[2]):
            continue
        added, removed, path = parts[0], parts[1], parts[2]
        if added == "-":  # binary: no line count, always over budget
            bump(totals, path, 0, flagged=True)
        else:
            bump(totals, path, int(added) + int(removed))
    rc, out = git(proj, "ls-files", "-o", "--exclude-standard")
    for path in out.splitlines():
        if isKitState(path):
            continue
        full = os.path.join(proj, path)
        try:
            with open(full, "rb") as f:
                data = f.read()
        except OSError:
            continue
        if b"\0" in data[:8000]:
            bump(totals, path, 0, flagged=True)
            continue
        lines = data.count(b"\n") + (1 if data and not data.endswith(b"\n") else 0)
        bump(totals, path, lines, flagged=lines > BIG_UNTRACKED_LINES)
    return totals


def overBudget(totals):
    """Returns the list of reasons the run is over budget; empty when it is within budget."""
    reasons = []
    for kind in ("code", "tests"):
        cap, got = BUDGET[kind], totals[kind]
        if got["files"] > cap["files"]:
            reasons.append(f"{kind}: {got['files']} files, the budget is {cap['files']}")
        if got["lines"] > cap["lines"]:
            reasons.append(f"{kind}: {got['lines']} lines, the budget is {cap['lines']}")
    for path in totals["flagged"]:
        reasons.append(f"{path}: binary or over {BIG_UNTRACKED_LINES} lines")
    return reasons


def nearBudget(totals):
    for kind in ("code", "tests"):
        cap, got = BUDGET[kind], totals[kind]
        if got["files"] >= cap["files"] * WARN_RATIO or got["lines"] >= cap["lines"] * WARN_RATIO:
            return True
    return False


def summary(totals):
    return (f"code {totals['code']['files']} files / {totals['code']['lines']} lines "
            f"(budget {BUDGET['code']['files']} / {BUDGET['code']['lines']}); "
            f"tests {totals['tests']['files']} files / {totals['tests']['lines']} lines "
            f"(budget {BUDGET['tests']['files']} / {BUDGET['tests']['lines']})")


def isStale(data, currentBranch, now=None):
    """A stale marker is legacy (no base), older than its TTL, or from another branch."""
    if not data or "base_sha" not in data or "started_epoch" not in data:
        return True
    now = time.time() if now is None else now
    if now - float(data["started_epoch"]) > float(data.get("ttl_h", TTL_HOURS)) * 3600:
        return True
    return bool(currentBranch) and bool(data.get("branch")) and data["branch"] != currentBranch


def currentBranch(proj):
    rc, out = git(proj, "branch", "--show-current")
    return out.strip() if rc == 0 else ""


def start(proj, command="", session=""):
    data = readMarker(proj)
    branch = currentBranch(proj)
    if data is not None and not isStale(data, branch):
        print(f"forge fix run already active on {data.get('branch')}; budget {summary(measure(proj, data['base_sha']))}")
        return 0
    if data is not None:
        clearMarker(proj, "fix_marker_stale", "stale marker cleared before a new run")
    rc, status = git(proj, "status", "--porcelain", "--", ".", ":(exclude).claude")
    if rc != 0 or status.strip():
        print("forge fix run not started: the working tree is not clean. Commit or stash first.")
        return 3
    rc, head = git(proj, "rev-parse", "HEAD")
    if rc != 0:
        print("forge fix run not started: the repository has no commit yet.")
        return 3
    now = time.time()
    base = head.strip()
    writeMarker(proj, {
        "command": command,
        "base_sha": base,
        "branch": branch,
        "started": datetime.datetime.fromtimestamp(now).isoformat(timespec="seconds"),
        "started_epoch": now,
        "ttl_h": TTL_HOURS,
        "budget": BUDGET,
        "session_id": session,
    })
    kit_log.event("gate", agent="fix_budget", reason_code="fix_started", severity="info", branch=branch, cwd=proj)
    print(f"forge fix run started on {branch or 'detached HEAD'} at {base[:7]}; budget {summary(BUDGET_ZERO)}.")
    return 0


BUDGET_ZERO = {"code": {"files": 0, "lines": 0}, "tests": {"files": 0, "lines": 0}, "flagged": []}


def check(proj):
    """Stop hook: 2 when the run is over budget, else 0. Stale markers are cleared, not enforced."""
    data = readMarker(proj)
    if data is None:
        return 0
    if isStale(data, currentBranch(proj)):
        clearMarker(proj, "fix_marker_stale", "stale marker cleared at stop")
        return 0
    try:
        totals = measure(proj, data["base_sha"])
    except ValueError as e:  # the base commit is gone (history rewritten): fail closed
        print(f"diff_budget: {e}. Stop and report; the fix run needs a new /forge:fix.", file=sys.stderr)
        return 2
    reasons = overBudget(totals)
    if not reasons:
        return 0
    kit_log.event("gate", agent="fix_budget", reason_code="diff_budget", severity="block",
                  branch=data.get("branch", ""), detail="fix over budget " + "; ".join(reasons), cwd=proj)
    print("diff_budget: " + "; ".join(reasons) + ". Stop, report, and recommend /forge:design.", file=sys.stderr)
    return 2


def warn(proj):
    """PostToolUse: prints a warning at 80% of budget. Never blocks."""
    data = readMarker(proj)
    if data is None or isStale(data, currentBranch(proj)):
        return 0
    totals = measure(proj, data["base_sha"])
    if nearBudget(totals) and not overBudget(totals):
        print(f"diff_budget: near the limit: {summary(totals)}.")
    return 0


def finish(proj, abandon=False):
    """Removes the marker when the run is within budget. --abandon removes it for a run that stopped on a failure."""
    data = readMarker(proj)
    if data is None:
        print("no forge fix run is active.")
        return 0
    if abandon:
        clearMarker(proj, "fix_abandoned", "fix run abandoned by the user or after a failed gate")
        print("forge fix run abandoned; the marker is removed.")
        return 0
    if isStale(data, currentBranch(proj)):
        clearMarker(proj, "fix_marker_stale", "stale marker cleared at finish")
        return 0
    try:
        totals = measure(proj, data["base_sha"])
    except ValueError as e:
        print(f"forge fix run not finished: {e}. Use finish --abandon to drop it.", file=sys.stderr)
        return 2
    reasons = overBudget(totals)
    if reasons:
        print("forge fix run not finished: " + "; ".join(reasons) + ". The marker stays.", file=sys.stderr)
        return 2
    clearMarker(proj, "fix_finished", f"fix finished: {summary(totals)}")
    print(f"forge fix run finished: {summary(totals)}.")
    return 0


def clearMarker(proj, reason, detail):
    try:
        os.remove(markerPath(proj))
    except OSError:
        return
    kit_log.event("gate", agent="fix_budget", reason_code=reason, severity="info",
                  branch=currentBranch(proj), detail=detail, cwd=proj)


def clearStale(proj):
    """SessionStart: clears a marker that is legacy, expired or from another branch."""
    data = readMarker(proj)
    if data is not None and isStale(data, currentBranch(proj)):
        clearMarker(proj, "fix_marker_stale", "stale marker cleared at session start")


def projectDir(argv):
    if "--project" in argv:
        return argv[argv.index("--project") + 1]
    return os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()


def main(argv):
    if not argv:
        print("usage: kit_fix.py start|measure|check|warn|finish|clear-stale [--project DIR]", file=sys.stderr)
        return 1
    proj = projectDir(argv)
    cmd = argv[0]
    if cmd == "start":
        command = argv[argv.index("--command") + 1] if "--command" in argv else ""
        session = argv[argv.index("--session") + 1] if "--session" in argv else ""
        return start(proj, command, session)
    if cmd == "measure":
        data = readMarker(proj)
        if data is None or "base_sha" not in data:
            print("no forge fix run is active.")
            return 0
        print(summary(measure(proj, data["base_sha"])))
        return 0
    if cmd == "check":
        return check(proj)
    if cmd == "warn":
        return warn(proj)
    if cmd == "finish":
        return finish(proj, abandon="--abandon" in argv)
    if cmd == "clear-stale":
        clearStale(proj)
        return 0
    print(f"unknown command: {cmd}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
