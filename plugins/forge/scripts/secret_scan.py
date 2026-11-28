"""Secret scanning for the kit (WI-08). Stdlib only.

Layers that call this module:
  precommit   staged changes (gitleaks protect --staged; regex fallback)
  stop        change set since HEAD: tracked diff plus untracked files (gitleaks dir; regex fallback)
  post FILE   one file just written by Write/Edit (regex; warns, never blocks)

Findings report the rule id and the file only. Values are never printed or logged.
A scanner that cannot run is an error for the stop and precommit layers, never a pass.
"""
import fnmatch
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kit_log  # noqa: E402

# Paths never scanned: real secret files (git-ignored) and committed example templates.
ALLOWLIST = ["secrets/*-secrets.properties", "*.example", "secrets/*.example"]
PATTERNS = [
    ("aws-access-key", re.compile(r"\b(AKIA|ASIA)[0-9A-Z]{16}\b")),
    ("private-key", re.compile(r"-----BEGIN (RSA |EC |OPENSSH |DSA |)PRIVATE KEY-----")),
    ("github-token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36}\b")),
    ("generic-secret-assignment",
     re.compile(r"(?i)\b(password|passwd|secret|api[_-]?key|token)\s*[:=]\s*['\"]?[A-Za-z0-9/+_\-]{16,}")),
]
GITLEAKS_CONFIG = ".gitleaks.toml"


def allowed(path):
    n = path.replace("\\", "/")
    return any(fnmatch.fnmatchcase(n, pat) or fnmatch.fnmatchcase(os.path.basename(n), pat) for pat in ALLOWLIST)


def scanText(text):
    """Rule ids found in text. Never returns the matched value."""
    return sorted({rule for rule, rx in PATTERNS if rx.search(text)})


def git(proj, *args):
    r = subprocess.run(["git", "-C", proj, *args], capture_output=True, text=True, encoding="utf-8", errors="replace")
    return r.returncode, r.stdout


def gitleaks():
    return shutil.which("gitleaks")


def runGitleaks(binary, args, reportDir, cwd):
    """Runs gitleaks and returns a list of (rule, file), or raises RuntimeError when the scan did not complete."""
    report = os.path.join(reportDir, "report.json")
    cmd = [binary, *args, "--no-banner", "--redact", "--report-format", "json", "--report-path", report]
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd)
    if r.returncode not in (0, 1):
        raise RuntimeError(f"gitleaks failed with exit {r.returncode}")
    if not os.path.isfile(report):
        if r.returncode == 0:
            return []
        raise RuntimeError("gitleaks left no report")
    with open(report, encoding="utf-8") as f:
        leaks = json.load(f) or []
    return [(leak.get("RuleID", "unknown"), leak.get("File", "")) for leak in leaks]


def changeSet(proj):
    """Files changed since HEAD, tracked and untracked, minus the allowlist."""
    _, tracked = git(proj, "diff", "--name-only", "--diff-filter=ACMR", "HEAD")
    _, untracked = git(proj, "ls-files", "-o", "--exclude-standard")
    names = {p for p in (tracked + untracked).splitlines() if p.strip()}
    return sorted(p for p in names if not allowed(p) and os.path.isfile(os.path.join(proj, p)))


def scanStop(proj):
    """Returns a list of (rule, file) for the change set. Raises RuntimeError if no scanner can finish."""
    files = changeSet(proj)
    if not files:
        return []
    binary = gitleaks()
    if binary:
        with tempfile.TemporaryDirectory(prefix="secret-scan-") as tmp:
            staged = os.path.join(tmp, "tree")
            for rel in files:  # copy only the change set, so the scan is quick and stays inside it
                dst = os.path.join(staged, rel)
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                with open(os.path.join(proj, rel), "rb") as src, open(dst, "wb") as out:
                    out.write(src.read())
            cfg = ["-c", os.path.join(proj, GITLEAKS_CONFIG)] if os.path.isfile(os.path.join(proj, GITLEAKS_CONFIG)) else []
            return runGitleaks(binary, ["dir", staged, *cfg], tmp, proj)
    return regexFindings(proj, files)


def regexFindings(proj, files):
    out = []
    for rel in files:
        try:
            with open(os.path.join(proj, rel), encoding="utf-8", errors="strict") as f:
                text = f.read()
        except (OSError, UnicodeDecodeError):
            continue
        out += [(rule, rel) for rule in scanText(text)]
    return out


def scanStaged(proj):
    """Staged changes only. Raises RuntimeError if the scanner cannot finish."""
    binary = gitleaks()
    if binary:
        with tempfile.TemporaryDirectory(prefix="secret-precommit-") as tmp:
            cfg = ["-c", os.path.join(proj, GITLEAKS_CONFIG)] if os.path.isfile(os.path.join(proj, GITLEAKS_CONFIG)) else []
            found = runGitleaks(binary, ["protect", "--staged", *cfg], tmp, proj)
            return [(rule, path) for rule, path in found if not allowed(path)]  # same allowlist as the stop scan
    _, names = git(proj, "diff", "--cached", "--name-only", "--diff-filter=ACM")
    out = []
    for rel in (n for n in names.splitlines() if n.strip() and not allowed(n)):
        _, text = git(proj, "show", f":{rel}")
        out += [(rule, rel) for rule in scanText(text)]
    return out


def describe(findings):
    return "; ".join(f"{rule} in {path}" for rule, path in findings)


def cmdStop(proj):
    try:
        findings = scanStop(proj)
    except (RuntimeError, OSError) as e:
        print(f"secret scan could not finish: {e}. Stop and report.", file=sys.stderr)
        return 2
    if findings:
        kit_log.event("gate", agent="secret_scan", reason_code="secret_found", severity="block",
                      detail=describe(findings), cwd=proj)
        print(f"secret scan: {describe(findings)}. Remove the secret, rotate it, and do not commit it.", file=sys.stderr)
        return 2
    return 0


def cmdPrecommit(proj):
    try:
        findings = scanStaged(proj)
    except (RuntimeError, OSError) as e:
        print(f"secret scan could not finish: {e}. The commit is blocked.", file=sys.stderr)
        return 1
    if findings:
        kit_log.event("gate", agent="secret_scan", reason_code="secret_found", severity="block",
                      detail=describe(findings), cwd=proj)
        print(f"pre-commit secret scan: {describe(findings)}. Unstage the file, rotate the secret.", file=sys.stderr)
        return 1
    return 0


def cmdPost(proj, path):
    full = path if os.path.isabs(path) else os.path.join(proj, path)
    if allowed(path) or not os.path.isfile(full):
        return 0
    try:
        with open(full, encoding="utf-8") as f:
            rules = scanText(f.read())
    except (OSError, UnicodeDecodeError):
        return 0
    if rules:
        print(f"secret scan: {', '.join(rules)} pattern in {path}. Remove it before the change is committed.")
    return 0


def main(argv):
    proj = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    if argv[:1] == ["stop"]:
        return cmdStop(proj)
    if argv[:1] == ["precommit"]:
        return cmdPrecommit(proj)
    if argv[:1] == ["post"] and len(argv) == 2:
        return cmdPost(proj, argv[1])
    print("usage: secret_scan.py stop | precommit | post FILE", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
