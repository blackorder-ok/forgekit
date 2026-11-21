"""Print counts that describe a person's Python style. No code is printed. Reads at most 40 files."""
import os
import re
import sys
from collections import Counter

MAX_FILES = 40


def pyFiles(roots):
    out = []
    for r in roots:
        for dp, dn, fn in os.walk(r):
            dn[:] = [d for d in dn if d not in {".git", "node_modules", "venv", ".venv", "__pycache__"}]
            out += [os.path.join(dp, f) for f in fn if f.endswith(".py")]
            if len(out) >= MAX_FILES:
                return out[:MAX_FILES]
    return out


def sample(files):
    c = Counter()
    lengths = []
    for p in files:
        try:
            t = open(p, encoding="utf-8").read()
        except (OSError, UnicodeDecodeError):
            continue
        c["files"] += 1
        for name in re.findall(r"^\s*def\s+([A-Za-z_][A-Za-z0-9_]*)", t, re.M):
            if name.startswith("__"):
                continue
            c["fn_camel" if re.match(r"^[a-z]+([A-Z][a-z0-9]*)+$", name) else "fn_snake" if "_" in name else "fn_single"] += 1
        c["cls_pascal"] += len(re.findall(r"^class\s+[A-Z][A-Za-z0-9]*", t, re.M))
        c["hint_fn"] += len(re.findall(r"def\s+\w+\([^)]*\)\s*->", t))
        c["def_total"] += len(re.findall(r"^\s*def\s", t, re.M))
        c["docstring"] += len(re.findall(r'def\s+\w+\([^)]*\)[^:]*:\s*\n\s*("""|\'\'\')', t))
        c["logging_std"] += len(re.findall(r"logging\.getLogger", t))
        c["logging_custom"] += len(re.findall(r"LoggingHandler|getLogs", t))
        c["print_calls"] += len(re.findall(r"^\s*print\(", t, re.M))
        c["fstrings"] += len(re.findall(r"\bf['\"]", t))
        c["singleton"] += len(re.findall(r"Singleton", t))
        c["dataclass"] += len(re.findall(r"@dataclass", t))
        c["pydantic"] += len(re.findall(r"BaseModel", t))
        lengths += [len(l) for l in t.splitlines()]
    c["max_line"] = max(lengths) if lengths else 0
    c["avg_line"] = round(sum(lengths) / len(lengths), 1) if lengths else 0
    return c


if __name__ == "__main__":
    roots = sys.argv[1:] or ["."]
    c = sample(pyFiles(roots))
    for k in sorted(c):
        print(f"{k}: {c[k]}")
