"""Create a new kit unit from a template inside the kit repo and register it in kit.json."""
import os
import sys

from kit_common import KINDS, NAME_RE, loadKit, requireRepo, saveKit, unitPath

TEMPLATES = {
    "skill": "---\nname: {name}\ndescription: TODO one sentence: what it covers and when to use it.\npack: core\n---\n\n# {name}\n\nTODO digest. Keep under 2.5 KB; put detail in references/.\n",
    "agent": "---\nname: {name}\ndescription: TODO what it does and when to use it.\ntools: Read, Grep, Glob\nmodel: sonnet\nskills: []\n---\n\nYou are the {name}. TODO role in one line.\n\n## Process\nTODO\n\n## Rules\n- Read at most 15 files.\n\n## Done when\nTODO\n",
    "command": "---\ndescription: TODO one sentence.\nargument-hint: <args>\n---\n\nRequest: $ARGUMENTS\n\nTODO steps.\n\n## On failure\n- TODO\n",
}


def create(repo, kind, name):
    if kind not in KINDS:
        sys.exit("forge: kind must be skill, agent or command")
    if not NAME_RE.match(name):
        sys.exit("forge: name must be lowercase letters, digits and hyphens")
    rel = unitPath("", kind, name)
    target = os.path.join(repo, "plugins", "forge", rel)
    if os.path.exists(target):
        sys.exit(f"forge: {rel} already exists")
    kit = loadKit(repo)
    kit.setdefault("units", {}).setdefault(KINDS[kind], {})
    if name in kit["units"][KINDS[kind]]:
        sys.exit(f"forge: {name} is already registered")
    os.makedirs(os.path.dirname(target), exist_ok=True)
    with open(target, "w", encoding="utf-8", newline="\n") as f:
        f.write(TEMPLATES[kind].format(name=name))
    kit["units"][KINDS[kind]][name] = {"origin": "kit-new"}
    saveKit(repo, kit)
    return target


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit("usage: kit_new.py <skill|agent|command> <name>")
    print(create(requireRepo(), sys.argv[1], sys.argv[2]))
