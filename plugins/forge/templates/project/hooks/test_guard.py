"""PreToolUse hook: block edits to tests that delete assertions or add skips. Exit 2 blocks."""
import json
import os
import re
import sys
import time

SKIP_MARKERS = ["pytest.mark.skip", "pytest.mark.xfail", "pytest.skip(", "pytest.xfail("]


def note(msg):
    """Log the gate decision to the event store via kit_log.py. Never raises."""
    try:
        root = os.environ.get("CLAUDE_PLUGIN_ROOT", "")
        scripts = os.path.join(root, "scripts") if root else os.path.join(os.path.expanduser("~"), ".kit", "repo", "plugins", "forge", "scripts")
        sys.path.insert(0, scripts)
        import kit_log
        kit_log.event("gate", agent="test_guard", reason_code="test_edit_blocked", severity="block", detail=msg, cwd=os.getcwd())
    except Exception:
        pass


def check(ti):
    if os.environ.get("KIT_HOOKS", "standard") == "minimal":
        return None
    path = ti.get("file_path", "").replace("\\", "/")
    if not re.search(r"(^|/)tests/", path):
        return None
    if "edits" in ti:
        pairs = [(e.get("old_string", ""), e.get("new_string", "")) for e in ti["edits"]]
    elif "old_string" in ti:
        pairs = [(ti["old_string"], ti.get("new_string", ""))]
    else:
        old = open(path, encoding="utf-8").read() if os.path.exists(path) else ""
        pairs = [(old, ti.get("content", ""))]
    for old, new in pairs:
        if len(re.findall(r"\bassert\b", old)) > len(re.findall(r"\bassert\b", new)):
            return "test_guard: this edit removes assert lines from a test. Fix the code, not the test."
        for marker in SKIP_MARKERS:
            if new.count(marker) > old.count(marker):
                return f"test_guard: this edit adds {marker}. Tests may not be skipped or marked xfail."
    return None


if __name__ == "__main__":
    msg = check(json.load(sys.stdin).get("tool_input", {}))
    if msg:
        note(msg.split(":", 1)[1].strip()[:80])
        print(msg, file=sys.stderr)
        sys.exit(2)
    sys.exit(0)
