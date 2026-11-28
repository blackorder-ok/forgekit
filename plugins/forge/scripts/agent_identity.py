"""SubagentStart / SubagentStop hook: records which subagent is running and checks what it changed (WI-11).

Subagents run one at a time in the foreground, so one marker file is enough to know the acting agent.
  SubagentStart  writes .claude/learn/agent-active.json: the agent name and a digest of every changed file
                 at that moment, so files the user already had modified are not counted as the agent's.
  SubagentStop   compares the digests now against the start. A change outside the agent's privilege
                 (read-only agent changed anything, or a path outside its writeAllow or inside writeDeny,
                 or the protected baseline) blocks the stop with the file names. The marker is removed.
A subagent whose name is not in the payload is recorded as UNKNOWN and treated as read-only by agent_guard.
"""
import hashlib
import json
import os
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import agent_guard  # noqa: E402
import kit_log  # noqa: E402
import kit_policy  # noqa: E402

UNKNOWN = "unknown"
MARKER_REL = os.path.join(".claude", "learn", "agent-active.json")
TTL_SECONDS = 2 * 3600
NAME_KEYS = ("agent_type", "subagent_type", "agent_name", "subagent_name", "name")
MAX_HASH_BYTES = 5 * 1024 * 1024


def markerPath(root):
    return os.path.join(root, MARKER_REL)


def readMarker(root):
    try:
        with open(markerPath(root), encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return None


def activeAgent(root, now=None):
    """Returns the running agent's name, UNKNOWN, or None for the main thread. An old marker is ignored."""
    data = readMarker(root)
    if data is None:
        return None
    now = time.time() if now is None else now
    if now - float(data.get("started_epoch", 0)) > TTL_SECONDS:
        return None
    return data.get("agent") or UNKNOWN


def agentName(payload):
    for key in NAME_KEYS:
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return UNKNOWN


def snapshot(root):
    """Digest of every changed or untracked file, keyed by repo-relative path. The kit's .claude folder is excluded."""
    r = subprocess.run(["git", "-C", root, "status", "--porcelain", "-z", "-uall"], capture_output=True)
    digests = {}
    entries = [e for e in r.stdout.decode("utf-8", errors="replace").split("\0") if e]
    for entry in entries:
        path = entry[3:].replace("\\", "/")
        if path.startswith(".claude/"):
            continue
        full = os.path.join(root, path)
        try:
            if os.path.isdir(full):
                continue
            size = os.path.getsize(full)
            if size > MAX_HASH_BYTES:
                digests[path] = f"big:{size}:{os.path.getmtime(full)}"
                continue
            with open(full, "rb") as f:
                digests[path] = hashlib.sha256(f.read()).hexdigest()
        except OSError:
            digests[path] = "gone"
    return digests


def headSha(root):
    r = subprocess.run(["git", "-C", root, "rev-parse", "HEAD"], capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else ""


def start(root, payload):
    os.makedirs(os.path.dirname(markerPath(root)), exist_ok=True)
    data = {"agent": agentName(payload), "started_epoch": time.time(), "before": snapshot(root)}
    with open(markerPath(root), "w", encoding="utf-8", newline="\n") as f:
        json.dump(data, f)
    return 0


def outOfScope(name, path, spec):
    if any(agent_guard.globMatch(path, p) for p in agent_guard.PROTECTED_FOR_ALL):
        return "protected baseline"
    if spec is None:
        return "no privilege entry"
    if spec["privilege"] == "read":
        return "read-only agent"
    if any(agent_guard.globMatch(path, p) for p in spec.get("writeDeny", [])):
        return "write-denied path"
    if "writeAllow" in spec and not any(agent_guard.globMatch(path, p) for p in spec["writeAllow"]):
        return "outside writeAllow"
    return None


def stop(root):
    data = readMarker(root)
    try:
        os.remove(markerPath(root))
    except OSError:
        pass
    if data is None:
        return 0
    name = data.get("agent") or UNKNOWN
    before = data.get("before") or {}
    now = snapshot(root)
    changed = sorted(p for p in now if before.get(p) != now[p])
    if name == UNKNOWN:
        if changed:
            return report(name, changed, "unknown agent changed files")
        return 0
    try:
        policy = kit_policy.load(overridePath=os.path.join(root, ".claude", "policy.json"))
        spec = (policy.get("agents") or {}).get(name)
    except kit_policy.PolicyError:
        spec = None
    problems = []
    for path in changed:
        reason = outOfScope(name, path, spec)
        if reason:
            problems.append(f"{path} ({reason})")
    if problems:
        return report(name, problems, "changed files outside its privilege")
    return 0


def report(name, items, why):
    text = f"{name}: {why}: " + ", ".join(items[:20]) + (" ..." if len(items) > 20 else "")
    print(f"agent check failed: {text}. Revert those changes; the agent's output is not a pass.", file=sys.stderr)
    kit_log.event("gate", agent="agent_identity", reason_code="agent_out_of_scope", severity="block", detail=text)
    return 2


def main():
    try:
        payload = json.load(sys.stdin)
    except ValueError:
        payload = {}
    if not isinstance(payload, dict):
        payload = {}
    root = os.environ.get("CLAUDE_PROJECT_DIR") or payload.get("cwd") or os.getcwd()
    event = payload.get("hook_event_name", "")
    if event == "SubagentStart":
        return start(root, payload)
    if event == "SubagentStop":
        return stop(root)
    return 0


if __name__ == "__main__":
    sys.exit(main())
