"""UserPromptSubmit hook: starts a fix run when the prompt is /forge:fix or /forge:hotfix (WI-07).

Reads the hook payload on stdin. Never blocks the prompt: a failed precondition is reported
by kit_fix.start on stdout and the command's own preconditions still apply.
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kit_fix  # noqa: E402

FIX_PROMPT = re.compile(r"^\s*/forge:(fix|hotfix)\b\s*(.*)", re.S)


def main():
    try:
        payload = json.load(sys.stdin)
    except ValueError:
        return 0
    prompt = payload.get("prompt") if isinstance(payload, dict) else None
    match = FIX_PROMPT.match(prompt or "")
    if not match:
        return 0
    proj = payload.get("cwd") or os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    kit_fix.start(proj, command=f"/forge:{match.group(1)}", session=str(payload.get("session_id", "")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
