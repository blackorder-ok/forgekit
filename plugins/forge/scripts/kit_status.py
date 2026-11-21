"""Read-only: list ~/.claude units the kit does not know, and kit units whose installed copy drifted."""
import os
import sys

from kit_common import HOME, KINDS, loadKit, localIgnore, requireRepo, unitPath


def listUnits(root):
    found = {k: set() for k in KINDS}
    for kind, folder in KINDS.items():
        d = os.path.join(root, folder)
        if not os.path.isdir(d):
            continue
        for entry in os.listdir(d):
            if kind == "skill" and os.path.isfile(os.path.join(d, entry, "SKILL.md")):
                found[kind].add(entry)
            elif kind != "skill" and entry.endswith(".md"):
                found[kind].add(entry[:-3])
    return found


def status(repo, claudeDir=None):
    claudeDir = claudeDir or os.path.join(HOME, ".claude")
    kit = loadKit(repo).get("units", {})
    ignore = localIgnore()
    local = listUnits(claudeDir)
    orphans, ignored, drifted = [], [], []
    for kind, names in local.items():
        known = kit.get(KINDS[kind], {})
        for n in sorted(names):
            if n in known:
                a = os.path.join(claudeDir, unitPath("", kind, n))
                b = os.path.join(repo, "plugins", "forge", unitPath("", kind, n))
                if os.path.exists(b) and open(a, "rb").read() != open(b, "rb").read():
                    drifted.append(f"{kind}:{n}")
            elif n in ignore or f"{kind}:{n}" in ignore:
                ignored.append(f"{kind}:{n}")
            else:
                orphans.append(f"{kind}:{n}")
    return orphans, ignored, drifted


if __name__ == "__main__":
    o, i, d = status(requireRepo())
    for title, items in (("orphans (not in kit)", o), ("ignored (personal)", i), ("drifted (differs from repo)", d)):
        print(f"{title}: {len(items)}")
        for x in items:
            print(f"  - {x}")
    sys.exit(0)
