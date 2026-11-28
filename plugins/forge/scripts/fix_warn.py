"""PostToolUse hook: warns when a fix run nears its diff budget (WI-07). Never blocks."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kit_fix  # noqa: E402


def main():
    try:
        payload = json.load(sys.stdin)
    except ValueError:
        return 0
    proj = (payload.get("cwd") if isinstance(payload, dict) else None) or os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    try:
        return kit_fix.warn(proj)
    except (OSError, ValueError):
        return 0


if __name__ == "__main__":
    sys.exit(main())
