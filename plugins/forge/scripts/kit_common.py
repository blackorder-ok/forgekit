"""Shared helpers for forgekit scripts. Stdlib only."""
import json
import os
import re
import sys

HOME = os.path.expanduser("~")
KIT_DIR = os.environ.get("FORGE_HOME", os.path.join(HOME, ".kit"))
KINDS = {"skill": "skills", "agent": "agents", "command": "commands"}
NAME_RE = re.compile(r"^[a-z][a-z0-9-]{0,40}$")


def kitRepo():
    """Path of the user's kit clone, from $FORGE_REPO or ~/.kit/repo."""
    env = os.environ.get("FORGE_REPO")
    if env:
        return env
    p = os.path.join(KIT_DIR, "repo")
    if os.path.exists(p):
        return open(p, encoding="utf-8").read().strip()
    return None


def requireRepo():
    repo = kitRepo()
    if not repo or not os.path.isdir(repo):
        sys.exit("forge: kit repo unknown. Write its path into ~/.kit/repo (or set FORGE_REPO).")
    return repo


def loadKit(repo):
    with open(os.path.join(repo, "kit.json"), encoding="utf-8") as f:
        return json.load(f)


def saveKit(repo, data):
    with open(os.path.join(repo, "kit.json"), "w", encoding="utf-8", newline="\n") as f:
        json.dump(data, f, indent=2)
        f.write("\n")


def unitPath(root, kind, name):
    """Relative path of a unit inside a plugin or ~/.claude root."""
    folder = KINDS[kind]
    return f"{folder}/{name}/SKILL.md" if kind == "skill" else f"{folder}/{name}.md"


def localIgnore():
    p = os.path.join(KIT_DIR, "local-ignore")
    if not os.path.exists(p):
        return set()
    return {l.strip() for l in open(p, encoding="utf-8") if l.strip() and not l.startswith("#")}
