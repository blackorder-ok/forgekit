"""Minimal-token memory for forgekit.

Layers: index (ids + titles, <= ~500 tokens) -> search (ids + titles) -> show (one entry) -> timeline (neighbours).
Project memory: <project>/.claude/memory/<id>.md. Lesson inbox: ~/.kit/inbox (tab separated, appended by hooks).
Stdlib only.
"""
import os
import re
import sys
from collections import defaultdict

from kit_common import KIT_DIR

TYPES = ("gotcha", "fix", "decision", "preference")
INDEX_BYTES = 2000  # about 500 tokens at 4 bytes per token
TITLE_WORDS = 10
BODY_BYTES = 600  # about 150 tokens


def memDir(root=None):
    return os.path.join(root or os.getcwd(), ".claude", "memory")


def parse(path):
    t = open(path, encoding="utf-8").read()
    m = re.match(r"^---\n(.*?)\n---\n?(.*)$", t, re.S)
    meta, body = {}, t
    if m:
        for line in m.group(1).splitlines():
            k, _, v = line.partition(":")
            meta[k.strip()] = v.strip()
        body = m.group(2).strip()
    meta["id"] = os.path.basename(path)[:-3]
    return meta, body


def entries(root=None):
    d = memDir(root)
    if not os.path.isdir(d):
        return []
    out = []
    for f in sorted(os.listdir(d)):
        if f.endswith(".md") and f != "README.md":
            meta, body = parse(os.path.join(d, f))
            out.append((meta, body))
    return out


def nextId(root=None):
    ids = [int(m["id"][1:]) for m, _ in entries(root) if re.match(r"^m\d+$", m["id"])]
    return f"m{(max(ids) + 1) if ids else 1:03d}"


def add(typ, title, body, root=None):
    if typ not in TYPES:
        sys.exit("forge-mem: type must be one of " + ", ".join(TYPES))
    if len(title.split()) > TITLE_WORDS:
        sys.exit(f"forge-mem: title must be {TITLE_WORDS} words or fewer")
    if len(body.encode("utf-8")) > BODY_BYTES:
        sys.exit(f"forge-mem: body must be {BODY_BYTES} bytes or fewer (about 150 tokens)")
    d = memDir(root)
    os.makedirs(d, exist_ok=True)
    mid = nextId(root)
    from datetime import date
    with open(os.path.join(d, mid + ".md"), "w", encoding="utf-8", newline="\n") as f:
        f.write(f"---\ntype: {typ}\ntitle: {title}\ndate: {date.today().isoformat()}\n---\n{body}\n")
    return mid


def index(root=None):
    """Newest first, until the byte budget is reached."""
    lines, used = [], 0
    es = entries(root)
    for meta, _ in reversed(es):
        line = f"{meta['id']} [{meta.get('type', '?')}] {meta.get('title', '')}"
        if used + len(line) + 1 > INDEX_BYTES:
            lines.append(f"... {len(es) - len(lines)} more: /forge:mem search <words>")
            break
        lines.append(line)
        used += len(line) + 1
    if not lines:
        return ""
    return "forge memory (ids; /forge:mem show <id>):\n" + "\n".join(lines)


def search(words, root=None):
    ws = [w.lower() for w in words]
    hits = []
    for meta, body in entries(root):
        hay = (meta.get("title", "") + " " + body + " " + meta.get("type", "")).lower()
        score = sum(hay.count(w) for w in ws)
        if score and all(w in hay for w in ws):
            hits.append((score, meta))
    hits.sort(key=lambda x: -x[0])
    return [f"{m['id']} [{m.get('type', '?')}] {m.get('title', '')}" for _, m in hits[:15]]


def show(mid, root=None):
    for meta, body in entries(root):
        if meta["id"] == mid:
            return f"{mid} [{meta.get('type')}] {meta.get('title')} ({meta.get('date')})\n{body}"
    return f"forge-mem: no entry {mid}"


def timeline(mid, root=None):
    es = [m for m, _ in entries(root)]
    ids = [m["id"] for m in es]
    if mid not in ids:
        return f"forge-mem: no entry {mid}"
    i = ids.index(mid)
    return "\n".join(f"{m['id']} {m.get('date', '')} [{m.get('type')}] {m.get('title')}" for m in es[max(0, i - 2): i + 3])


def inboxPath():
    return os.path.join(KIT_DIR, "inbox")


def readInbox(path=None):
    path = path or inboxPath()
    if not os.path.exists(path):
        return []
    rows = []
    for line in open(path, encoding="utf-8"):
        p = line.rstrip("\n").split("\t")
        if len(p) >= 4:
            rows.append(p[:4])
    return rows


def groupInbox(rows):
    g = defaultdict(lambda: {"count": 0, "projects": set(), "last": ""})
    for date, source, project, text in rows:
        k = f"{source}:{text}"
        g[k]["count"] += 1
        g[k]["projects"].add(project)
        g[k]["last"] = date
    return g


def inbox(clear=None, path=None):
    path = path or inboxPath()
    rows = readInbox(path)
    if clear:
        keep = [r for r in rows if f"{r[1]}:{r[3]}" != clear]
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            for r in keep:
                f.write("\t".join(r) + "\n")
        return f"cleared {len(rows) - len(keep)} lines for {clear}"
    g = groupInbox(rows)
    if not g:
        return "inbox empty"
    out = []
    for k, v in sorted(g.items(), key=lambda kv: -kv[1]["count"]):
        flag = "PROMOTE?" if v["count"] >= 3 and len(v["projects"]) >= 2 else ""
        out.append(f"{v['count']}x {k} projects={len(v['projects'])} last={v['last']} {flag}".rstrip())
    return "\n".join(out)


def main(argv):
    if not argv:
        sys.exit("usage: kit_mem.py index|search|show|timeline|add|inbox ...")
    cmd, rest = argv[0], argv[1:]
    if cmd == "index":
        print(index())
    elif cmd == "search":
        print("\n".join(search(rest)) or "no match")
    elif cmd == "show" and rest:
        print(show(rest[0]))
    elif cmd == "timeline" and rest:
        print(timeline(rest[0]))
    elif cmd == "add" and len(rest) == 3:
        print(add(rest[0], rest[1], rest[2]))
    elif cmd == "inbox":
        clear = rest[1] if len(rest) == 2 and rest[0] == "--clear" else None
        print(inbox(clear))
    else:
        sys.exit("usage: kit_mem.py index|search <words>|show <id>|timeline <id>|add <type> <title> <body>|inbox [--clear <group>]")


if __name__ == "__main__":
    main(sys.argv[1:])
