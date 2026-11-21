"""Self-check for forgekit. Stdlib only. Exit 1 on any problem.

Run from anywhere: python tools/check_kit.py [--tokens]
Checks: manifests parse; agents' skills exist; skills have name/pack/description; commands launch real agents and
mention real /forge:commands; templates paths exist and placeholders are documented; kit.json matches the files on disk;
no secrets or personal paths; with --tokens: per-file byte budgets and per-agent preload size.
"""
import glob
import json
import os
import re
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PLUGIN = os.path.join(ROOT, "plugins", "forge")
PROBLEMS = []


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def rel(p):
    return os.path.relpath(p, PLUGIN).replace("\\", "/")


def front(text):
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    out = {}
    if m:
        for line in m.group(1).splitlines():
            k, _, v = line.partition(":")
            out[k.strip()] = v.strip()
    return out


def checkAll(tokens=False, plugin=PLUGIN, root=ROOT):
    global PLUGIN, ROOT
    PLUGIN, ROOT = plugin, root
    PROBLEMS.clear()
    info = {}
    for jf in ("kit.json", ".claude-plugin/marketplace.json", "plugins/forge/.claude-plugin/plugin.json", "plugins/forge/hooks/hooks.json"):
        p = os.path.join(root, jf)
        try:
            json.loads(read(p))
        except (OSError, ValueError) as e:
            PROBLEMS.append(f"{jf}: cannot parse ({e})")
    agents = {os.path.basename(p)[:-3]: p for p in glob.glob(os.path.join(plugin, "agents", "*.md"))}
    commands = {os.path.basename(p)[:-3]: p for p in glob.glob(os.path.join(plugin, "commands", "*.md"))}
    skills = {os.path.basename(os.path.dirname(p)): p for p in glob.glob(os.path.join(plugin, "skills", "*", "SKILL.md"))}

    for name, p in skills.items():
        fm = front(read(p))
        if fm.get("name") != name:
            PROBLEMS.append(f"skills/{name}: frontmatter name must be '{name}'")
        if not fm.get("description"):
            PROBLEMS.append(f"skills/{name}: missing description")
        if fm.get("pack") not in ("core", "stack"):
            PROBLEMS.append(f"skills/{name}: pack must be core or stack")
    for name, p in agents.items():
        t = read(p)
        fm = front(t)
        if fm.get("name") != name:
            PROBLEMS.append(f"agents/{name}: frontmatter name must be '{name}'")
        for f in ("description", "tools", "model"):
            if not fm.get(f):
                PROBLEMS.append(f"agents/{name}: missing {f}")
        m = re.search(r"^skills: \[(.*)\]$", t, re.M)
        for s in [x.strip() for x in (m.group(1).split(",") if m else []) if x.strip()]:
            if s not in skills:
                PROBLEMS.append(f"agents/{name}: skills entry '{s}' has no skills/{s}/SKILL.md")
    for name, p in list(commands.items()) + list(agents.items()):
        t = read(p)
        for g in re.findall(r"[Ll]aunch[a-z]* (?:the )?`([a-z-]+)`(?: agent)?", t):
            if g not in agents:
                PROBLEMS.append(f"{rel(p)}: launches '{g}', which has no agents/{g}.md")
        for c in re.findall(r"`?/forge:([a-z-]+)", t):
            if c not in commands:
                PROBLEMS.append(f"{rel(p)}: mentions /forge:{c}, which has no commands/{c}.md")
        for tp in re.findall(r"`(templates/[^`\s*]+)`", t):
            if not os.path.exists(os.path.join(plugin, tp)):
                PROBLEMS.append(f"{rel(p)}: names {tp}, which does not exist")
    for name, p in skills.items():
        for ref in re.findall(r"`(references/[^`\s]+)`", read(p)):
            if not os.path.exists(os.path.join(os.path.dirname(p), ref)):
                PROBLEMS.append(f"skills/{name}: names {ref}, which does not exist")
    # independence: a skill may require nothing; only commands orchestrate commands and agents
    for name, p in skills.items():
        tx = read(p)
        # naming a command as a pointer is fine; requiring another skill is not
        for other in skills:
            if other != name and re.search(r"`" + re.escape(other) + r"` skill", tx):
                PROBLEMS.append(f"skills/{name}: depends on skill '{other}'; skills must stand alone")
    for name, p in agents.items():
        m = re.search(r"^skills: \[(.*)\]$", read(p), re.M)
        if len([x for x in (m.group(1).split(",") if m else []) if x.strip()]) > 4:
            PROBLEMS.append(f"agents/{name}: preloads more than 4 skills")
    # naming: snake_case file names; camelCase functions; SCREAMING_SNAKE module-level variables
    for p in glob.glob(os.path.join(root, "**", "*"), recursive=True):
        if not os.path.isfile(p) or ".git" + os.sep in p or "__pycache__" in p or "node_modules" in p:
            continue
        base = os.path.basename(p)
        if base.endswith((".py", ".sh")) and not re.match(r"^[a-z][a-z0-9]*(_[a-z0-9]+)*\.(py|sh)$", base):
            PROBLEMS.append(f"naming: file {os.path.relpath(p, root)} must be snake_case")
        if base.endswith(".py"):
            src = read(p)
            for fn in re.findall(r"^\s*def ([A-Za-z_][A-Za-z0-9_]*)", src, re.M):
                if not fn.startswith(("test_", "__")) and "_" in fn.strip("_"):
                    PROBLEMS.append(f"naming: {os.path.relpath(p, root)}: function {fn} must be camelCase")
            for v in re.findall(r"^([a-z_][A-Za-z0-9_]*) = ", src, re.M):
                PROBLEMS.append(f"naming: {os.path.relpath(p, root)}: module-level variable {v} must be SCREAMING_SNAKE_CASE")
    # placeholders
    tr = os.path.join(plugin, "templates", "README.md")
    docs = read(tr) if os.path.exists(tr) else ""
    ph = set()
    for p in glob.glob(os.path.join(plugin, "templates", "**", "*"), recursive=True):
        if os.path.isfile(p) and not p.endswith("README.md") and "__pycache__" not in p:
            ph |= set(re.findall(r"\{\{([A-Z_]+)\}\}", read(p)))
    for x in sorted(ph):
        if "{{" + x + "}}" not in docs:
            PROBLEMS.append(f"templates: placeholder {{{{{x}}}}} is not in templates/README.md")
    # kit.json registry
    try:
        reg = json.loads(read(os.path.join(root, "kit.json")))["units"]
        disk = {"skills": set(skills), "agents": set(agents), "commands": set(commands)}
        for k in disk:
            for n in sorted(disk[k] - set(reg.get(k, {}))):
                PROBLEMS.append(f"kit.json: {k}/{n} exists on disk but is not registered (orphan)")
            for n in sorted(set(reg.get(k, {})) - disk[k]):
                PROBLEMS.append(f"kit.json: {k}/{n} is registered but missing on disk")
    except (OSError, KeyError, ValueError):
        pass
    # secrets / personal paths
    bad = [(r"AKIA[0-9A-Z]{16}", "AWS key"), (r"-----BEGIN [A-Z ]*PRIVATE KEY-----", "private key"),
           (r"ghp_[A-Za-z0-9]{20,}", "GitHub token"), (r"[A-Za-z]:\\Users\\[A-Za-z0-9._-]+", "Windows home path"),
           (r"/(?:Users|home)/(?!claude\b|runner\b|user\b)[A-Za-z0-9._-]+/", "home path")]
    for p in glob.glob(os.path.join(plugin, "**", "*"), recursive=True):
        if os.path.isfile(p) and "__pycache__" not in p:
            try:
                t = read(p)
            except UnicodeDecodeError:
                continue
            for pat, label in bad:
                if re.search(pat, t):
                    PROBLEMS.append(f"{rel(p)}: contains a {label}")
    # budgets
    if tokens:
        kit = json.loads(read(os.path.join(root, "kit.json")))
        b = kit.get("budgets", {})
        over = b.get("overrides", {})

        def lim(path, default):
            o = over.get(path)
            return o["bytes"] if o else default
        for name, p in skills.items():
            n = os.path.getsize(p)
            if n > lim(f"skills/{name}/SKILL.md", b.get("skill_bytes", 2500)):
                PROBLEMS.append(f"budget: skills/{name}/SKILL.md is {n} bytes")
        for name, p in agents.items():
            n = os.path.getsize(p)
            if n > lim(f"agents/{name}.md", b.get("agent_bytes", 3000)):
                PROBLEMS.append(f"budget: agents/{name}.md is {n} bytes")
        for name, p in commands.items():
            n = os.path.getsize(p)
            if n > lim(f"commands/{name}.md", b.get("command_bytes", 3500)):
                PROBLEMS.append(f"budget: commands/{name}.md is {n} bytes")
        for name, p in agents.items():
            t = read(p)
            m = re.search(r"^skills: \[(.*)\]$", t, re.M)
            total = os.path.getsize(p)
            for s in [x.strip() for x in (m.group(1).split(",") if m else []) if x.strip()]:
                if s in skills:
                    total += os.path.getsize(skills[s])
            info[name] = total // 4
    return list(PROBLEMS), info


if __name__ == "__main__":
    tokens = "--tokens" in sys.argv
    probs, info = checkAll(tokens)
    if probs:
        print("check_kit: FAIL")
        for x in probs:
            print("  - " + x)
        sys.exit(1)
    n = lambda d: len(glob.glob(os.path.join(PLUGIN, d)))
    print(f"check_kit: OK ({n('agents/*.md')} agents, {n('commands/*.md')} commands, {n('skills/*/SKILL.md')} skills)")
    if tokens:
        print("preload per agent (approx tokens, agent + preloaded skill digests):")
        for k, v in sorted(info.items(), key=lambda kv: -kv[1]):
            print(f"  {k}: ~{v}")
