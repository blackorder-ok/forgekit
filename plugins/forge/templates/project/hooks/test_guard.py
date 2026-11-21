"""PreToolUse hook: block edits to tests that delete assertions or add skips. Exit 2 blocks."""
import json
import os
import re
import sys
import time

SKIP_MARKERS = ["pytest.mark.skip", "pytest.mark.xfail", "pytest.skip(", "pytest.xfail("]


def note(msg):
    try:
        inbox = os.path.join(os.path.expanduser("~"), ".kit", "inbox")
        os.makedirs(os.path.dirname(inbox), exist_ok=True)
        with open(inbox, "a", encoding="utf-8") as f:
            f.write(f"{time.strftime('%F')}\ttest_guard\t{os.path.basename(os.getcwd())}\t{msg}\n")
    except OSError:
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
