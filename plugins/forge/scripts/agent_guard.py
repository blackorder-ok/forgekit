"""PreToolUse hook (plugin-level): applies each subagent's privilege from policy/gates.json (WI-11).

The acting agent comes from the marker that agent_identity.py writes at SubagentStart. With no marker
the main thread is not restricted here (the other gates still apply). With a marker whose agent is
unknown, writes and Bash are denied: an unidentified subagent is treated as read-only.

Decisions: allow, or deny with a reason on stdout (hookSpecificOutput). Never prints file contents.
"""
import fnmatch
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kit_log  # noqa: E402
import kit_policy  # noqa: E402
import agent_identity  # noqa: E402

WRITE_TOOLS = ("Write", "Edit", "MultiEdit", "NotebookEdit")
# Protected for every agent: the ai-evaluator baseline is changed by a human decision, never by an agent.
PROTECTED_FOR_ALL = ["evals/baseline.json"]
# Shell features that let an allowed command do more than its pattern shows.
SHELL_META = re.compile(r"[;&|<>$`()\n]")
# Flags that write files even on an otherwise read-only command.
WRITE_FLAGS = re.compile(r"(--output|--report|--fix|--write|--in-place|\s-i\b|\s-o\s)")


def globMatch(path, pattern):
    if fnmatch.fnmatchcase(path, pattern):
        return True
    if pattern.startswith("**/"):  # "**/x" also matches a top-level x
        return fnmatch.fnmatchcase(path, pattern[3:])
    return False


def relPath(path, root):
    full = path if os.path.isabs(path) else os.path.join(root, path)
    rel = os.path.relpath(os.path.normpath(full), root)
    return rel.replace("\\", "/")


def writeTargets(tool, tin):
    if tool == "NotebookEdit":
        return [tin.get("notebook_path", "")]
    return [tin.get("file_path", "")]


def deny(reason):
    return ("deny", reason)


def decide(identity, tool, tin, root, policy):
    """Returns (verdict, reason). verdict is allow or deny. Pure: no I/O besides path arithmetic."""
    if not identity or identity == "main":
        return ("allow", "")
    if identity == agent_identity.UNKNOWN:
        if tool in WRITE_TOOLS or tool == "Bash":
            return deny("the acting subagent could not be identified; writes and shell are denied")
        return ("allow", "")
    spec = (policy.get("agents") or {}).get(identity)
    if spec is None:
        return deny(f"agent {identity} has no privilege entry in policy")
    if tool in WRITE_TOOLS:
        if spec["privilege"] == "read":
            return deny(f"{identity} is read-only")
        for raw in writeTargets(tool, tin):
            rel = relPath(raw, root)
            if any(globMatch(rel, p) for p in PROTECTED_FOR_ALL):
                return deny(f"{rel} is protected: only a person changes it")
            if any(globMatch(rel, p) for p in spec.get("writeDeny", [])):
                return deny(f"{identity} may not write {rel}")
            if "writeAllow" in spec and not any(globMatch(rel, p) for p in spec["writeAllow"]):
                return deny(f"{identity} may not write {rel}")
        return ("allow", "")
    if tool == "Bash":
        cmd = (tin.get("command") or "").strip()
        if "bashAllow" in spec:
            if not spec["bashAllow"]:
                return deny(f"{identity} may not run shell commands")
            if SHELL_META.search(cmd) or WRITE_FLAGS.search(" " + cmd):
                return deny(f"{identity} may run only plain read commands; this one chains or writes")
            if not any(re.fullmatch(p, cmd) for p in spec["bashAllow"]):
                return deny(f"{identity} may not run: {cmd.split()[0] if cmd else '(empty)'}")
            return ("allow", "")
        if spec["privilege"] == "read":
            return deny(f"{identity} is read-only and has no shell allow-list")
    return ("allow", "")


def emit(verdict, reason, identity, tool, cwd):
    if verdict == "allow":
        return
    body = {"hookEventName": "PreToolUse", "permissionDecision": verdict,
            "permissionDecisionReason": f"{reason}. Instead: use the tool or path your role allows."}
    sys.stdout.write(json.dumps({"hookSpecificOutput": body}) + "\n")
    kit_log.event("gate", agent="agent_guard", reason_code="agent_privilege", severity="block",
                  detail=f"{identity} {tool}: {reason}", cwd=cwd)


def main():
    try:
        ev = json.load(sys.stdin)
    except ValueError:
        return 0  # the launcher handles unreadable payloads
    if not isinstance(ev, dict) or ev.get("tool_name") not in WRITE_TOOLS + ("Bash",):
        return 0
    cwd = ev.get("cwd") or os.getcwd()
    root = os.environ.get("CLAUDE_PROJECT_DIR") or cwd
    identity = agent_identity.activeAgent(root)
    if identity is None:
        return 0
    try:
        policy = kit_policy.loadOrDeny(overridePath=os.path.join(root, ".claude", "policy.json"))
    except Exception:  # fail closed for an identified agent
        verdict, reason = deny("the policy failed to load")
        emit(verdict, reason, identity, ev.get("tool_name"), cwd)
        return 0
    verdict, reason = decide(identity, ev.get("tool_name"), ev.get("tool_input") or {}, root, policy)
    emit(verdict, reason, identity, ev.get("tool_name"), cwd)
    return 0


if __name__ == "__main__":
    sys.exit(main())
