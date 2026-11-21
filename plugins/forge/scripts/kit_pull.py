"""Fetch tags in the kit repo and show what a newer version would change. Changes no working files."""
import re
import subprocess
import sys

import os

from kit_common import kitRepo, requireRepo


def git(repo, *args):
    return subprocess.run(["git", "-C", repo, *args], capture_output=True, text=True)


def tagKey(t):
    return tuple(int(x) for x in re.findall(r"\d+", t)[:3])


def newerTags(tags, current):
    return sorted([t for t in tags if re.match(r"^v\d+\.\d+\.\d+$", t) and tagKey(t) > tagKey(current)], key=tagKey)


def notice():
    """One quiet line for SessionStart. Never installs, never fails the session."""
    try:
        repo = kitRepo()
        if not repo or not os.path.isdir(repo):
            return
        subprocess.run(["git", "-C", repo, "fetch", "--tags", "--quiet"], capture_output=True, timeout=5)
        cur = git(repo, "describe", "--tags", "--abbrev=0", "HEAD").stdout.strip() or "v0.0.0"
        new = newerTags(git(repo, "tag", "--list", "v*").stdout.split(), cur)
        if new:
            print(f"forge: {len(new)} new kit tag(s) ({new[-1]}). Run /forge:kit-pull to review. Nothing was installed.")
    except Exception:
        pass


def main():
    if "--notice" in sys.argv:
        notice()
        return
    repo = requireRepo()
    f = git(repo, "fetch", "--tags", "--quiet")
    if f.returncode:
        sys.exit("forge: fetch failed: " + f.stderr.strip()[:200])
    cur = git(repo, "describe", "--tags", "--abbrev=0", "HEAD").stdout.strip() or "v0.0.0"
    tags = git(repo, "tag", "--list", "v*").stdout.split()
    new = newerTags(tags, cur)
    if not new:
        print(f"up to date at {cur}")
        return
    latest = new[-1]
    print(f"installed/checked-out: {cur}; newer: {', '.join(new)}")
    print(git(repo, "diff", "--stat", f"{cur}..{latest}").stdout[-1500:])
    print(git(repo, "log", "--oneline", f"{cur}..{latest}").stdout[-1500:])
    print("Nothing was changed. Ask the user before updating.")


if __name__ == "__main__":
    main()
