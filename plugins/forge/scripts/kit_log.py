"""Append-only, redacted event log for forgekit. Stdlib only.

Stores:
  project  <project>/.claude/learn/events.jsonl   (gitignored)
  global   ~/.kit/events.jsonl                    (project events mirrored here)
Project ids are hashes of the git origin URL (fallback: absolute path), never folder names.
Command text is never stored: only the first token, its class and a hash.

CLI: kit_log.py event --type T [--agent A] [--reason-code R] [--severity S] [--outcome O]
                      [--detail D] [--branch B] [--command C]
     kit_log.py import-legacy
Opt-out: KIT_LEARN=off keeps only gate events, and only locally. KIT_LOG=off writes nothing.
"""
import argparse
import contextlib
import hashlib
import json
import os
import re
import subprocess
import sys
import time
import uuid
from datetime import datetime, timezone

import kit_common
from kit_claim import PATH_PATTERNS, SECRET_PATTERNS

VERSION = 1
MAX_BYTES = 5 * 1024 * 1024  # rotate at 5 MB into archive/
LINE_LIMIT = 4096  # one write() per line below this keeps O_APPEND atomic on POSIX
DETAIL_LIMIT = 200
FIELD_LIMITS = {"session_id": 64, "branch": 80, "agent": 40, "reason_code": 40, "outcome": 40}
GATE_TYPES = ("gate",)
LOCK_TIMEOUT = 15.0  # 50 concurrent writers on Windows need more than 2 s; a dropped event is worse than a short wait
LOCK_STALE = 10.0
CLASSES = {"git": "vcs", "pytest": "test", "python": "run", "node": "run", "npm": "build", "make": "build"}


def kitDir():
    return kit_common.KIT_DIR


def globalPath():
    return os.path.join(kitDir(), "events.jsonl")


def projectPath(cwd=None):
    return os.path.join(cwd or os.getcwd(), ".claude", "learn", "events.jsonl")


def projectId(cwd=None):
    """Hash of the origin URL, cached in .claude/learn/project_id."""
    cwd = cwd or os.getcwd()
    cache = os.path.join(cwd, ".claude", "learn", "project_id")
    try:
        with open(cache, encoding="utf-8") as f:
            cached = f.read().strip()
        if cached:
            return cached
    except OSError:
        pass
    try:
        url = subprocess.run(["git", "-C", cwd, "config", "--get", "remote.origin.url"],
                             capture_output=True, text=True, timeout=5).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        url = ""
    pid = hashlib.sha256((url or os.path.abspath(cwd)).encode("utf-8")).hexdigest()[:12]
    try:
        os.makedirs(os.path.dirname(cache), exist_ok=True)
        with open(cache, "w", encoding="utf-8", newline="\n") as f:
            f.write(pid + "\n")
    except OSError:
        pass
    return pid


def fingerprint(text, branch=None):
    """Group key: same wording with different numbers, paths, hashes, branches or quotes gives one key."""
    t = str(text).lower()
    if branch:
        t = re.sub(r"(?<![\w-])" + re.escape(branch.lower()) + r"(?![\w-])", " <branch> ", t)
    t = re.sub(r"\"[^\"]*\"|'[^']*'|`[^`]*`", " <q> ", t)
    t = re.sub(r"\b(?:feature|bugfix|hotfix|release|fix)/\S+", " <branch> ", t)
    t = re.sub(r"[\w.\-]*[/\\][\w./\\\-]*|\b[\w\-]+\.(?:py|sh|md|json|js|ts|txt|toml|yml|yaml)\b", " <path> ", t)
    t = re.sub(r"\b(?=[0-9a-f]*\d)[0-9a-f]{7,64}\b", " <hash> ", t)
    t = re.sub(r"\d+", "<n>", t)
    return hashlib.sha256(" ".join(t.split()).encode("utf-8")).hexdigest()[:16]


def redact(text):
    out = str(text)
    for pat, _ in SECRET_PATTERNS:
        out = re.sub(pat, "<secret>", out)
    for pat, _ in PATH_PATTERNS:
        out = re.sub(pat, "<home>", out)
    out = re.sub(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+", "<email>", out)
    out = re.sub(r"\b[0-9a-fA-F]{32,}\b", "<hex>", out)
    out = re.sub(r"[A-Za-z0-9+/_\-]{40,}={0,2}", "<b64>", out)
    return " ".join(out.split())[:DETAIL_LIMIT]


def commandParts(cmd):
    """Only the first token, its class and a hash of the full text. Never the arguments."""
    parts = (cmd or "").strip().split()
    if not parts:
        return {}
    token = os.path.basename(parts[0].replace("\\", "/"))
    if token.lower().endswith(".exe"):
        token = token[:-4]
    return {
        "command": redact(token)[:40],
        "command_class": CLASSES.get(token, "other"),
        "command_hash": hashlib.sha256(cmd.encode("utf-8")).hexdigest()[:12],
    }


def makeRecord(type, projectIdValue="", ts=None, **fields):
    detail = redact(fields.get("detail") or "")
    rec = {
        "id": uuid.uuid4().hex[:16],
        "ts": ts or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "v": VERSION,
        "session_id": redact(fields.get("session_id") or os.environ.get("CLAUDE_SESSION_ID", "")),
        "project_id": projectIdValue,
        "branch": redact(fields.get("branch") or ""),
        "agent": redact(fields.get("agent") or ""),
        "type": type,
        "fingerprint": fingerprint(detail, fields.get("branch") or None) if detail else "",
        "severity": fields.get("severity") or "info",
        "reason_code": redact(fields.get("reason_code") or ""),
        "detail": detail,
        "outcome": redact(fields.get("outcome") or ""),
    }
    for key, limit in FIELD_LIMITS.items():
        rec[key] = rec[key][:limit]
    rec.update(commandParts(fields.get("command")))
    return rec


def encodeLine(rec):
    line = (json.dumps(rec, separators=(",", ":"), ensure_ascii=True) + "\n").encode("utf-8")
    if len(line) > LINE_LIMIT:
        raise ValueError("event line over 4 KB")
    return line


def rotateIfNeeded(path):
    try:
        if os.path.getsize(path) < MAX_BYTES:
            return
    except OSError:
        return
    arch = os.path.join(os.path.dirname(path), "archive")
    os.makedirs(arch, exist_ok=True)
    name = "events-" + time.strftime("%Y%m%dT%H%M%S") + "-" + uuid.uuid4().hex[:6] + ".jsonl"
    os.replace(path, os.path.join(arch, name))


@contextlib.contextmanager
def lockFile(path):
    """Cross-process lock via O_EXCL lock file, with short retries and stale-lock recovery."""
    lock = path + ".lock"
    deadline = time.time() + LOCK_TIMEOUT
    while True:
        try:
            os.close(os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY))
            break
        except (FileExistsError, PermissionError):  # Windows reports a lock file being deleted as PermissionError: busy, retry
            try:
                if time.time() - os.path.getmtime(lock) > LOCK_STALE:
                    os.remove(lock)
                    continue
            except OSError:
                pass
            if time.time() > deadline:
                raise TimeoutError(lock)
            time.sleep(0.003)
    try:
        yield
    finally:
        try:
            os.remove(lock)
        except OSError:
            pass


def appendLine(path, line):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if os.name == "nt":
        # Windows O_APPEND is not reliable across processes: serialize writers with a lock file.
        with lockFile(path):
            rotateIfNeeded(path)
            with open(path, "ab") as f:
                f.write(line)
    else:
        rotateIfNeeded(path)
        fd = os.open(path, os.O_CREAT | os.O_WRONLY | os.O_APPEND, 0o644)
        try:
            os.write(fd, line)
        finally:
            os.close(fd)


def writeQuietly(path, line):
    try:
        appendLine(path, line)
        return True
    except (OSError, TimeoutError):
        return False  # logging must never break a hook


def event(type, **fields):
    """Log one event to the project and global stores. Returns the record, or None when off."""
    if os.environ.get("KIT_LOG", "on") == "off":
        return None
    learnOff = os.environ.get("KIT_LEARN", "on") == "off"
    if learnOff and type not in GATE_TYPES:
        return None
    cwd = fields.pop("cwd", None)
    rec = makeRecord(type, projectIdValue=projectId(cwd), **fields)
    line = encodeLine(rec)
    writeQuietly(projectPath(cwd), line)
    if not learnOff:
        writeQuietly(globalPath(), line)
    return rec


def read(since=None, path=None):
    path = path or globalPath()
    rows = []
    if not os.path.exists(path):
        return rows
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            try:
                r = json.loads(line)
            except ValueError:
                continue
            if since and r.get("ts", "") < since:
                continue
            rows.append(r)
    return rows


def archive(ids, path=None):
    """Move events with these ids into archive/. Returns how many moved."""
    path = path or globalPath()
    ids = set(ids)
    if not os.path.exists(path):
        return 0
    moved, kept = [], []
    with lockFile(path):
        with open(path, encoding="utf-8") as f:
            for line in f:
                try:
                    rid = json.loads(line).get("id")
                except ValueError:
                    rid = None
                (moved if rid in ids else kept).append(line)
        if moved:
            arch = os.path.join(os.path.dirname(path), "archive")
            os.makedirs(arch, exist_ok=True)
            with open(os.path.join(arch, "archived-" + uuid.uuid4().hex[:8] + ".jsonl"), "w", encoding="utf-8", newline="\n") as f:
                f.writelines(moved)
            tmp = path + ".tmp"
            with open(tmp, "w", encoding="utf-8", newline="\n") as f:
                f.writelines(kept)
            os.replace(tmp, path)
    return len(moved)


def importLegacy(src=None, dst=None):
    """One-shot import of the old ~/.kit/inbox TSV. The original is kept as inbox.v0.bak."""
    src = src or os.path.join(kitDir(), "inbox")
    dst = dst or globalPath()
    if not os.path.exists(src):
        return 0
    count = 0
    with open(src, encoding="utf-8") as f:
        for line in f:
            p = line.rstrip("\n").split("\t")
            if len(p) < 4:
                continue
            date, source, project, text = p[:4]
            pid = hashlib.sha256(project.encode("utf-8")).hexdigest()[:12]
            rec = makeRecord("legacy", projectIdValue=pid, ts=date + "T00:00:00Z", agent=source, detail=text)
            appendLine(dst, encodeLine(rec))
            count += 1
    bak = src + ".v0.bak"
    if os.path.exists(bak):
        bak = src + "." + time.strftime("%Y%m%dT%H%M%S") + ".v0.bak"
    os.replace(src, bak)
    return count


def main(argv):
    p = argparse.ArgumentParser(prog="kit_log")
    sub = p.add_subparsers(dest="cmd", required=True)
    e = sub.add_parser("event")
    e.add_argument("--type", required=True)
    for name in ("agent", "reason-code", "severity", "outcome", "detail", "branch", "command"):
        e.add_argument("--" + name, default="")
    sub.add_parser("import-legacy")
    a = p.parse_args(argv)
    try:
        if a.cmd == "event":
            event(a.type, agent=a.agent, reason_code=a.reason_code, severity=a.severity or "info",
                  outcome=a.outcome, detail=a.detail, branch=a.branch, command=a.command)
        else:
            print(f"imported {importLegacy()} legacy lines")
    except Exception:  # hooks call this; never fail them
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
