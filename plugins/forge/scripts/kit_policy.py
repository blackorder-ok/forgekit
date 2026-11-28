"""Load and validate the gate policy. Stdlib only.

Base policy: plugins/forge/policy/gates.json (shipped with the kit).
Project override: <project>/.claude/policy.json. An override may only tighten:
  lists add entries (no removals are expressible), agents may only lower their privilege.
Any error raises PolicyError. loadOrDeny() returns a deny-all policy instead, so hooks fail closed.
"""
import fnmatch
import json
import os
import re
import sys

PRIVILEGES = ("read", "edit", "full")  # ordered from least to most
TOP_KEYS = {"version", "protectedBranches", "protectedPaths", "bash", "secretPaths", "agents"}
BASH_KEYS = {"deny", "ask"}
AGENT_KEYS = {"privilege", "writeAllow", "writeDeny", "bashAllow"}
OVERRIDE_AGENT_KEYS = {"privilege"}  # a project may only change an agent's privilege level
LIST_KEYS = ("protectedBranches", "protectedPaths", "secretPaths")
MAX_BYTES = 64 * 1024
MAX_ITEMS = 200
MAX_STR = 200
PLUGIN = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
BASE_PATH = os.path.join(PLUGIN, "policy", "gates.json")


class PolicyError(ValueError):
    pass


def _fail(where, msg):
    raise PolicyError(f"{where}: {msg}")


def _strList(where, value, regex=False):
    if not isinstance(value, list):
        _fail(where, "must be a list")
    if len(value) > MAX_ITEMS:
        _fail(where, f"more than {MAX_ITEMS} entries")
    for item in value:
        if not isinstance(item, str) or not item or len(item) > MAX_STR:
            _fail(where, f"entries must be non-empty strings of at most {MAX_STR} characters")
        if regex:
            try:
                re.compile(item)
            except re.error as e:
                _fail(where, f"bad regex {item!r}: {e}")
    return list(value)


def validate(doc, where="policy", base=True):
    """Return a normalized copy. Unknown keys are rejected; the base must set every list."""
    if not isinstance(doc, dict):
        _fail(where, "must be a JSON object")
    unknown = set(doc) - TOP_KEYS
    if unknown:
        _fail(where, f"unknown keys {sorted(unknown)}")
    if doc.get("version") != 1:
        _fail(where, "version must be 1")
    out = {"version": 1}
    for key in LIST_KEYS:
        if key in doc:
            out[key] = _strList(f"{where}.{key}", doc[key], regex=False)
        elif base:
            _fail(where, f"missing {key}")
    if "bash" in doc:
        bash = doc["bash"]
        if not isinstance(bash, dict) or set(bash) - BASH_KEYS:
            _fail(f"{where}.bash", f"only {sorted(BASH_KEYS)} allowed")
        out["bash"] = {k: _strList(f"{where}.bash.{k}", bash.get(k, []), regex=True) for k in BASH_KEYS}
    elif base:
        _fail(where, "missing bash")
    if "agents" in doc:
        agents = doc["agents"]
        if not isinstance(agents, dict) or len(agents) > MAX_ITEMS:
            _fail(f"{where}.agents", "must be an object of at most 200 agents")
        out["agents"] = {}
        for name, spec in agents.items():
            if not re.fullmatch(r"[a-z][a-z0-9-]{0,40}", name):
                _fail(f"{where}.agents", f"bad agent name {name!r}")
            allowedKeys = AGENT_KEYS if base else OVERRIDE_AGENT_KEYS
            if not isinstance(spec, dict) or set(spec) - allowedKeys:
                _fail(f"{where}.agents.{name}", f"only {sorted(allowedKeys)} allowed")
            if spec.get("privilege") not in PRIVILEGES:
                _fail(f"{where}.agents.{name}", f"privilege must be one of {PRIVILEGES}")
            entry = {"privilege": spec["privilege"]}
            for key in ("writeAllow", "writeDeny"):
                if key in spec:
                    entry[key] = _strList(f"{where}.agents.{name}.{key}", spec[key], regex=False)
            if "bashAllow" in spec:
                entry["bashAllow"] = _strList(f"{where}.agents.{name}.bashAllow", spec["bashAllow"], regex=True)
            out["agents"][name] = entry
    elif base:
        _fail(where, "missing agents")
    return out


def readJson(path):
    size = os.path.getsize(path)
    if size > MAX_BYTES:
        _fail(path, f"larger than {MAX_BYTES} bytes")
    with open(path, encoding="utf-8") as f:
        try:
            return json.load(f)
        except ValueError as e:
            _fail(path, f"invalid JSON ({e})")


def tighten(base, override):
    """Merge an override that can only tighten. Raises PolicyError on any loosening."""
    out = {"version": 1}
    for key in LIST_KEYS:
        out[key] = list(dict.fromkeys(base[key] + override.get(key, [])))
    out["bash"] = {k: list(dict.fromkeys(base["bash"][k] + override.get("bash", {}).get(k, []))) for k in BASH_KEYS}
    agents = {name: dict(spec) for name, spec in base["agents"].items()}
    for name, spec in override.get("agents", {}).items():
        allowed = agents.get(name, {"privilege": "full"})["privilege"]  # an agent absent from the base is unrestricted
        if PRIVILEGES.index(spec["privilege"]) > PRIVILEGES.index(allowed):
            _fail(f"override.agents.{name}", f"privilege {spec['privilege']} loosens base {allowed}")
        agents[name] = {**agents.get(name, {}), "privilege": spec["privilege"]}
    out["agents"] = agents
    return out


def load(basePath=None, overridePath=None):
    """Return the effective policy. Raises PolicyError on any problem."""
    base = validate(readJson(basePath or BASE_PATH), "base")
    if not overridePath or not os.path.exists(overridePath):
        return base
    override = validate(readJson(overridePath), "override", base=False)
    return tighten(base, override)


def denyAll(error):
    return {"denyAll": True, "error": str(error)}


def loadOrDeny(basePath=None, overridePath=None):
    """Hooks use this: any failure becomes a deny-all policy, never an allow."""
    try:
        return load(basePath, overridePath)
    except (OSError, PolicyError) as e:
        return denyAll(e)


def isProtectedBranch(policy, branch):
    if policy.get("denyAll"):
        return True
    return any(fnmatch.fnmatchcase(branch or "", pat) for pat in policy["protectedBranches"])


def privilegeTable(policy):
    """Rows of (agent, privilege) for the guides."""
    return sorted((name, spec["privilege"]) for name, spec in policy["agents"].items())


def privilegeMarkdown(policy):
    lines = ["| Agent | Privilege |", "| --- | --- |"]
    lines += [f"| {name} | {priv} |" for name, priv in privilegeTable(policy)]
    return "\n".join(lines)


def main(argv):
    base = os.path.join(os.getcwd(), ".claude", "policy.json")
    override = base if os.path.exists(base) else None
    try:
        policy = load(overridePath=override)
    except (OSError, PolicyError) as e:
        print(f"kit_policy: {e}")
        return 1
    print(f"kit_policy: OK ({len(policy['agents'])} agents, {len(policy['protectedBranches'])} protected branches)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
