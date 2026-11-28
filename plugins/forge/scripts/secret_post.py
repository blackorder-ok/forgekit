"""PostToolUse hook for Write, Edit and MultiEdit: warns on a secret pattern in the file just written (WI-08)."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import secret_scan  # noqa: E402


def main():
    try:
        payload = json.load(sys.stdin)
    except ValueError:
        return 0
    if not isinstance(payload, dict):
        return 0
    path = (payload.get("tool_input") or {}).get("file_path")
    proj = payload.get("cwd") or os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    if not isinstance(path, str):
        return 0
    return secret_scan.cmdPost(proj, path)


if __name__ == "__main__":
    sys.exit(main())
