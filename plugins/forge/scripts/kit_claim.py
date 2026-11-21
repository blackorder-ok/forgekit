"""Move one unit from ~/.claude into the kit repo, after a scan. Dry run by default."""
import os
import re
import shutil
import sys

from kit_common import HOME, KINDS, NAME_RE, loadKit, localIgnore, requireRepo, saveKit, unitPath

SECRET_PATTERNS = [
    (r"AKIA[0-9A-Z]{16}", "AWS access key"),
    (r"(?i)(api[_-]?key|secret|token|password)\s*[:=]\s*['\"]?[A-Za-z0-9/+_\-]{16,}", "credential-like value"),
    (r"-----BEGIN [A-Z ]*PRIVATE KEY-----", "private key"),
    (r"sk-[A-Za-z0-9]{20,}", "API key"),
    (r"ghp_[A-Za-z0-9]{20,}", "GitHub token"),
]
PATH_PATTERNS = [
    (r"[A-Za-z]:\\Users\\[^\\\s]+", "Windows home path"),
    (r"/(?:Users|home)/[A-Za-z0-9._-]+/", "home path"),
]


def scan(text, extra_words=()):
    hits = []
    for pat, label in SECRET_PATTERNS + PATH_PATTERNS:
        for m in re.finditer(pat, text):
            hits.append((label, m.group(0)[:6] + "…"))
    for w in extra_words:
        if w and w.lower() in text.lower():
            hits.append(("ignore-list word", w))
    return hits


def claim(repo, kind, name, apply=False, claudeDir=None):
    if kind not in KINDS or not NAME_RE.match(name):
        sys.exit("forge: bad kind or name")
    claudeDir = claudeDir or os.path.join(HOME, ".claude")
    rel = unitPath("", kind, name)
    src = os.path.join(claudeDir, rel)
    if not os.path.exists(src):
        sys.exit(f"forge: {src} not found")
    kit = loadKit(repo)
    if name in kit.get("units", {}).get(KINDS[kind], {}):
        sys.exit(f"forge: {name} is already in the kit")
    text = open(src, encoding="utf-8").read()
    hits = scan(text, localIgnore())
    dst = os.path.join(repo, "plugins", "forge", rel)
    info = {"source": src, "target": dst, "bytes": len(text.encode("utf-8")), "hits": hits}
    if hits or not apply:
        return info
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copyfile(src, dst)
    kit.setdefault("units", {}).setdefault(KINDS[kind], {})[name] = {"origin": "claimed"}
    saveKit(repo, kit)
    info["applied"] = True
    return info


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) != 2:
        sys.exit("usage: kit_claim.py <skill|agent|command> <name> [--dry-run|--apply]")
    res = claim(requireRepo(), args[0], args[1], apply="--apply" in sys.argv)
    print(f"source: {res['source']}\ntarget: {res['target']}\nbytes: {res['bytes']}")
    for label, snippet in res["hits"]:
        print(f"HIT: {label} ({snippet})")
    if res["hits"]:
        sys.exit(1)
    print("claimed" if res.get("applied") else "dry run ok: re-run with --apply after approval")
