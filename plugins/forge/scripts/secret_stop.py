"""Stop hook: blocks the stop when the change set holds a secret (WI-08). Loop guard on stop_hook_active."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import secret_scan  # noqa: E402


def main():
    try:
        payload = json.load(sys.stdin)
    except ValueError:
        payload = {}
    if isinstance(payload, dict) and payload.get("stop_hook_active"):
        return 0  # a retry from this hook: do not loop
    proj = (payload.get("cwd") if isinstance(payload, dict) else None) or os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    return secret_scan.cmdStop(proj)


if __name__ == "__main__":
    sys.exit(main())
