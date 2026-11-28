"""PreToolUse gate for the Bash tool. Stdlib only.

Reads the hook event on stdin. Prints a permissionDecision (deny or ask) as JSON when the command
crosses a rule, and stays silent (allow) otherwise. Run through hook_launch.sh, so crashes fail closed.

Honest limit: this is a tripwire, not a sandbox. Variables, base64, scripts and eval of computed text
cannot be followed. The sandbox (WI-08) and branch protection in CI are the real barriers.
"""
import fnmatch
import json
import os
import re
import shlex
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kit_log  # noqa: E402
import kit_policy  # noqa: E402

MAX_SEGMENTS = 25
RM_LIMIT = 10
MAX_DEPTH = 5
ENV_BRANCHES = ("qa", "release", "master")
SHELLS = ("sh", "bash", "zsh", "dash")
WRAPPERS = ("env", "nohup", "time", "nice", "command", "exec", "builtin", "xargs")
INLINE = ("python", "python3", "node", "perl", "ruby", "php")
WRITE_ALL = ("tee", "touch", "truncate", "rm", "rmdir", "unlink")
WRITE_LAST = ("cp", "install", "ln")
WRITE_MODE = ("chmod", "chown")
GIT_WRITE = ("commit", "merge", "rebase", "cherry-pick", "am", "revert", "reset", "restore", "checkout",
             "add", "rm", "mv", "stash", "apply", "clean", "pull", "switch")
REDIRECTS = (">", ">>", ">|", "&>", ">&")
READS = ("<",)
HEREDOCS = ("<<", "<<<")
DEFAULT_SECRETS = [".env", ".env.*", "secrets/*", "*/secrets/*", "*-secrets.properties",
                   "*/.ssh/*", "*/.aws/*", "*/.config/gh/*"]
REASONS = {
    "bash_sudo": ("sudo is not allowed from an agent session", "run the command yourself, outside the agent"),
    "bash_push_protected": ("push to a protected branch (qa, release, master) is blocked",
                            "push a feature/* branch and open a PR into develop"),
    "bash_push_mirror": ("--mirror pushes every ref and can overwrite protected branches", "push a named feature branch"),
    "bash_push_delete": ("deleting remote branches is blocked", "ask a maintainer to delete it in the host UI"),
    "bash_force_push": ("force push is blocked", "push a new commit instead"),
    "bash_no_verify": ("--no-verify skips the hooks that guard this repo", "fix the failing check, or ask the user"),
    "bash_tag_delete": ("deleting or force-moving tags is blocked", "create a new tag with a new version"),
    "bash_branch_delete_env": ("deleting qa, release or master is blocked", "leave environment branches alone"),
    "bash_write_protected": ("this writes a protected path (tests, ~/.kit or secrets)",
                             "change the code instead; for tests, ask the user"),
    "bash_read_secret": ("reading a secret or kit path is blocked", "use the value from the environment or ask the user"),
    "bash_write_on_protected_branch": ("this changes files or history on a protected or detached branch",
                                       "switch to develop or a feature/* branch first"),
    "bash_curl_pipe_shell": ("piping a download into a shell is blocked", "download the script, read it, then run it"),
    "bash_policy_deny": ("blocked by policy/gates.json", "see plugins/forge/policy/gates.json"),
    "bash_policy_error": ("the gate policy failed to load; the gate fails closed", "fix policy/gates.json"),
    "bash_push": ("git push needs confirmation", "confirm the branch and remote with the user"),
    "bash_pr_merge": ("gh pr merge needs confirmation", "ask the user to merge"),
    "bash_secret_set": ("setting a secret needs confirmation", "ask the user to set it"),
    "bash_api_write": ("a write through gh api needs confirmation", "confirm the endpoint with the user"),
    "bash_compose_down_volumes": ("docker compose down -v deletes volumes", "run it without -v, or confirm"),
    "bash_reset_hard": ("git reset --hard discards work", "stash or commit first"),
    "bash_bulk_delete": (f"deleting more than {RM_LIMIT} paths needs confirmation", "delete in smaller steps, or confirm"),
    "bash_too_many_segments": (f"more than {MAX_SEGMENTS} command segments", "split the work into smaller commands"),
    "bash_unparsable": ("the command cannot be parsed safely", "simplify the command"),
    "bash_unknown_verb": ("the command name is computed at run time", "write the command literally"),
    "bash_inline_on_protected": ("inline interpreter code on a protected branch needs confirmation", "run the script from develop"),
    "bash_xargs_write": ("xargs feeds paths from stdin into a write command", "name the files explicitly"),
    "bash_no_command": ("the Bash input has no command", "send a command string"),
    "bash_env_dump": ("this prints environment variables or secrets from the process or container",
                      "name the variable you need, e.g. printenv NAME, and ask the user if it is a secret"),
    "bash_fix_marker": ("the fix-run marker is removed only by finishing the run",
                        "run: python <kit>/scripts/kit_fix.py finish"),
}

FIX_MARKER = "fix-active"
DELETE_VERBS = ("rm", "unlink", "rmdir", "del", "mv", "shred", "truncate")


class Finding:
    def __init__(self, verdict, code):
        self.verdict = verdict
        self.code = code


def deny(code):
    return Finding("deny", code)


def ask(code):
    return Finding("ask", code)


def splitHeredocs(text):
    """Remove here-doc bodies. A body fed to a shell is returned as nested text to analyze."""
    lines, kept, nested = text.split("\n"), [], []
    i = 0
    while i < len(lines):
        line = lines[i]
        m = re.search(r"(?<!<)<<-?\s*(['\"]?)([A-Za-z_][A-Za-z0-9_]*)\1", line)
        if not m or "<<<" in line:
            kept.append(line)
            i += 1
            continue
        delim, body, j = m.group(2), [], i + 1
        while j < len(lines) and lines[j].strip() != delim:
            body.append(lines[j])
            j += 1
        first = re.split(r"\s+", line.strip(), 1)[0]
        if os.path.basename(first) in SHELLS:
            nested.append("\n".join(body))
        kept.append(line)
        i = j + 1
    return "\n".join(kept), nested


def matchParen(text, openIndex):
    depth, i, q = 0, openIndex, None
    while i < len(text):
        c = text[i]
        if q:
            if c == q:
                q = None
        elif c in "'\"":
            q = c
        elif c == "(":
            depth += 1
        elif c == ")":
            depth -= 1
            if depth == 0:
                return i
        i += 1
    raise ValueError("unbalanced $(")


def scanSegments(text, nested):
    """Split on unquoted ; & | newline ( ). $(...) and backticks are pulled out as nested text."""
    segs, cur = [], []
    i, q = 0, None
    while i < len(text):
        c = text[i]
        if q == "'":
            cur.append(c)
            q = None if c == "'" else q
            i += 1
            continue
        if c == "\\" and i + 1 < len(text):
            cur.append(text[i:i + 2])
            i += 2
            continue
        if text.startswith("$(", i):
            j = matchParen(text, i + 1)
            nested.append(text[i + 2:j])
            cur.append("SUBST")
            i = j + 1
            continue
        if c == "`":
            j = text.find("`", i + 1)
            if j < 0:
                raise ValueError("unclosed backtick")
            nested.append(text[i + 1:j])
            cur.append("SUBST")
            i = j + 1
            continue
        if q is None and c in "'\"":
            q = c
        elif q == '"' and c == '"':
            q = None
        elif q is None and c in ";&|\n()":
            seg = "".join(cur).strip()
            if seg:
                segs.append(seg)
            cur = []
            i += 1
            continue
        cur.append(c)
        i += 1
    if q is not None:
        raise ValueError("unclosed quote")
    seg = "".join(cur).strip()
    if seg:
        segs.append(seg)
    return segs


def tokens(seg):
    lx = shlex.shlex(seg, posix=True, punctuation_chars=True)
    lx.whitespace_split = True
    return list(lx)


def parseWords(toks):
    """Returns (words, write targets, read targets)."""
    words, writes, reads = [], [], []
    i = 0
    while i < len(toks):
        t = toks[i]
        if t in HEREDOCS:
            i += 2
            continue
        if t in REDIRECTS or t in READS:
            if i + 1 < len(toks) and toks[i + 1] not in ("/dev/null", "&1", "&2"):
                (reads if t in READS else writes).append(toks[i + 1])
            i += 2
            continue
        if t.isdigit() and i + 1 < len(toks) and toks[i + 1] in REDIRECTS:
            i += 1
            continue
        if t in (";", "&", "|", "(", ")"):
            i += 1
            continue
        words.append(t)
        i += 1
    return words, writes, reads


def normPath(p):
    if p.startswith("~") or p.startswith("$HOME") or p.startswith("${HOME}"):
        p = p.replace("${HOME}", "~").replace("$HOME", "~")
        p = os.path.expanduser(p)
    return p.replace("\\", "/")


def globPrefix(p):
    return re.split(r"[*?\[]", p, 1)[0]


def overlaps(target, pattern):
    t = normPath(target)
    if fnmatch.fnmatchcase(t, pattern):
        return True
    lit, base = globPrefix(t), globPrefix(pattern)
    return lit.startswith(base) or base.startswith(lit)


def kitPath(p):
    kit = os.path.join(os.path.expanduser("~"), ".kit").replace("\\", "/")
    n = normPath(p)
    return n == kit or n.startswith(kit + "/")


def isProtectedWrite(p, policy):
    if kitPath(p):
        return True
    return any(overlaps(p, pat) for pat in policy["protectedPaths"])


def resolvedForms(p, root=None):
    """Every form of a path the gate should match: as written, normalised, real (symlinks), and project-relative."""
    base = os.path.expanduser("~") if p.startswith(("~", "$HOME", "${HOME}")) else (root or os.getcwd())
    expanded = os.path.expanduser(p.replace("${HOME}", "~").replace("$HOME", "~"))
    full = os.path.normpath(os.path.join(base, expanded))
    forms = {normPath(p), normPath(full)}
    try:
        forms.add(normPath(os.path.realpath(full)))
    except OSError:
        pass
    if root:
        rootNorm = normPath(os.path.realpath(root)).rstrip("/") + "/"
        for f in list(forms):
            if f.startswith(rootNorm):
                forms.add(f[len(rootNorm):])
    return forms


def isSecret(p, policy, root=None):
    if kitPath(p):
        return True
    secrets = policy.get("secretPaths") or DEFAULT_SECRETS
    for n in resolvedForms(p, root):
        name = os.path.basename(n)
        if name.endswith(".example"):  # committed templates are readable
            continue
        if any(fnmatch.fnmatchcase(n, pat) or fnmatch.fnmatchcase(name, pat) for pat in secrets):
            return True
    return False


def gitSub(args):
    i = 0
    while i < len(args):
        a = args[i]
        if a in ("-C", "-c"):
            i += 2
            continue
        if a.startswith("-"):
            i += 1
            continue
        return a, args[i + 1:]
    return "", []


def verbWrites(verb, args):
    """Returns (is_write, targets) for a command verb."""
    pos = [a for a in args if not a.startswith("-")]
    if verb == "git":
        sub, rest = gitSub(args)
        targets = []
        if sub in ("checkout", "restore") and "--" in rest:
            targets = rest[rest.index("--") + 1:]
        elif sub in ("rm", "mv"):
            targets = [a for a in rest if not a.startswith("-")]
        return sub in GIT_WRITE, targets
    if verb in WRITE_ALL:
        return True, pos
    if verb in WRITE_LAST:
        return True, pos[-1:]
    if verb == "mv":
        return True, pos
    if verb in WRITE_MODE:
        return True, pos[1:]
    if verb == "sed" and any(a == "-i" or a.startswith("-i") or a == "--in-place" for a in args):
        if "-e" in args or "-f" in args:
            return True, pos
        return True, pos[1:]
    if verb == "dd":
        return True, [a[3:] for a in args if a.startswith("of=")]
    if verb == "find" and any(a in ("-delete", "-exec", "-execdir", "-ok") for a in args):
        return True, args
    return False, []


def gitPushFindings(args, ctx):
    out = []
    if "--mirror" in args:
        out.append(deny("bash_push_mirror"))
    if "--delete" in args or "-d" in args or any(re.match(r"^:", a) for a in args):
        out.append(deny("bash_push_delete"))
    if "--force" in args or "-f" in args or any(a.startswith("--force") for a in args):
        out.append(deny("bash_force_push"))
    refs = [a for a in args if not a.startswith("-")][1:]
    for r in refs:
        dst = r.split(":")[-1].lstrip("+").replace("refs/heads/", "")
        if dst in ctx["protected"]:
            out.append(deny("bash_push_protected"))
    out.append(ask("bash_push"))
    return out


def verbFindings(verb, words, ctx, depth):
    args = words[1:]
    out = []
    if verb in ("sudo", "doas"):
        return [deny("bash_sudo")]
    if verb == "git":
        sub, rest = gitSub(args)
        if sub == "push":
            out += gitPushFindings(rest, ctx)
        elif sub == "tag" and any(a in ("-d", "-f", "--delete") for a in rest):
            out.append(deny("bash_tag_delete"))
        elif sub == "branch" and "-D" in rest and any(b in rest for b in ENV_BRANCHES):
            out.append(deny("bash_branch_delete_env"))
        elif sub == "reset" and "--hard" in rest:
            out.append(ask("bash_reset_hard"))
    if verb == "gh" and len(args) >= 2:
        if args[0] == "pr" and args[1] == "merge":
            out.append(ask("bash_pr_merge"))
        if args[0] == "secret" and args[1] == "set":
            out.append(ask("bash_secret_set"))
        if args[0] == "api":
            for i, a in enumerate(args):
                method = args[i + 1].upper() if a in ("-X", "--method") and i + 1 < len(args) else ""
                if a.upper().startswith("-X") and len(a) > 2:
                    method = a[2:].upper()
                if method in ("DELETE", "PUT", "PATCH"):
                    out.append(ask("bash_api_write"))
                    break
    if verb == "docker" and args[:2] == ["compose", "down"] and any(a in ("-v", "--volumes") for a in args):
        out.append(ask("bash_compose_down_volumes"))
    if verb == "rm":
        pos = [a for a in args if not a.startswith("-")]
        if len(pos) > RM_LIMIT:
            out.append(ask("bash_bulk_delete"))
    if verb in INLINE and any(a in ("-c", "-e") for a in args) and ctx["onProtected"]:
        out.append(ask("bash_inline_on_protected"))
    if verb in SHELLS and "-c" in args:
        inner = args[args.index("-c") + 1] if args.index("-c") + 1 < len(args) else ""
        out += analyze(inner, ctx, depth + 1)
    if verb == "eval":
        out += analyze(" ".join(args), ctx, depth + 1)
    return out


def envDumpFindings(verb, words):
    """Commands that print the environment, process secrets or container config."""
    args = words[1:]
    if verb == "printenv" or (verb == "set" and not args):
        return [deny("bash_env_dump")]
    if any(re.match(r"^/proc/([^/]+|\*)/(environ|cmdline)", w) for w in words):
        return [deny("bash_env_dump")]
    if verb == "docker" and args[:1] == ["inspect"]:
        return [deny("bash_env_dump")]
    if verb == "docker" and args[:2] == ["compose", "config"] and "--no-interpolate" not in args:
        return [deny("bash_env_dump")]
    return []


def classifySegment(seg, ctx, depth):
    try:
        toks = tokens(seg)
    except ValueError:
        return [ask("bash_unparsable")]
    words, writes, reads = parseWords(toks)
    while words and re.match(r"^\w+=", words[0]):
        words = words[1:]
    sawXargs = False
    sawEnv = bool(words) and os.path.basename(words[0]) == "env" and all(
        w.startswith("-") or re.match(r"^\w+=", w) for w in words[1:])
    while words and os.path.basename(words[0]) in WRAPPERS:
        sawXargs = sawXargs or os.path.basename(words[0]) == "xargs"
        words = words[1:]
        while words and re.match(r"^\w+=", words[0]):
            words = words[1:]
    if not words:
        return [deny("bash_env_dump")] if sawEnv else []
    verb = os.path.basename(words[0].replace("\\", "/")).lower()
    if verb.endswith(".exe"):
        verb = verb[:-4]
    if "SUBST" in verb or "$" in verb:
        return [ask("bash_unknown_verb")]
    out = []
    if sawXargs and verb in WRITE_ALL + WRITE_LAST + ("sed", "dd", "chmod", "chown"):
        out.append(ask("bash_xargs_write"))  # the paths come from stdin: cannot be checked here
    isWrite, targets = verbWrites(verb, words[1:])
    allWrites = writes + targets
    if verb in ("tee",) or allWrites:
        isWrite = True
    for p in allWrites:
        if isProtectedWrite(p, ctx["policy"]):
            out.append(deny("bash_write_protected"))
    if isWrite and ctx["onProtected"]:
        out.append(deny("bash_write_on_protected_branch"))
    if verb != "git" or gitSub(words[1:])[0] != "commit":
        for p in reads + [w for w in words[1:]]:
            if isSecret(p, ctx["policy"], ctx.get("root")):
                out.append(deny("bash_read_secret"))
                break
    else:
        for p in reads:
            if isSecret(p, ctx["policy"], ctx.get("root")):
                out.append(deny("bash_read_secret"))
    out += envDumpFindings(verb, words)
    if verb in DELETE_VERBS and any(FIX_MARKER in w for w in words[1:]):
        out.append(deny("bash_fix_marker"))
    out += verbFindings(verb, words, ctx, depth)
    return out


def analyze(text, ctx, depth=0):
    if depth > MAX_DEPTH:
        return [ask("bash_unparsable")]
    cleaned, nested = splitHeredocs(text)
    inner = []
    try:
        segs = scanSegments(cleaned, inner)
    except ValueError:
        return [ask("bash_unparsable")]
    nested += inner
    ctx["segments"] += len(segs)
    out = []
    if ctx["segments"] > MAX_SEGMENTS:
        out.append(ask("bash_too_many_segments"))
    for seg in segs:
        out += classifySegment(seg, ctx, depth)
    for n in nested:
        out += analyze(n, ctx, depth + 1)
    return out


def decide(command, branch, policy, root=None):
    """Returns (verdict, code, reason, alternative). Verdict is allow, ask or deny."""
    if policy.get("denyAll"):
        return ("deny", "bash_policy_error") + REASONS["bash_policy_error"]
    ctx = {
        "policy": policy,
        "root": root,
        "branch": branch,
        "protected": set(policy["protectedBranches"]) | set(ENV_BRANCHES),
        "onProtected": branch == "" or branch in policy["protectedBranches"] or branch in ENV_BRANCHES,
        "segments": 0,
    }
    findings = analyze(command, ctx)
    denies = [f for f in findings if f.verdict == "deny"]
    if denies:  # specific reasons first; the policy regexes are the backstop
        code = denies[0].code
        return ("deny", code) + REASONS[code]
    for pat in policy["bash"]["deny"]:
        if re.search(pat, command):
            return ("deny", "bash_policy_deny", f"blocked by rule {pat}", REASONS["bash_policy_deny"][1])
    asks = [f for f in findings if f.verdict == "ask"]
    for pat in policy["bash"]["ask"]:
        if re.search(pat, command):
            asks.append(ask("bash_policy_ask"))
            break
    if asks:
        code = asks[0].code
        if code == "bash_policy_ask":
            return ("ask", code, f"needs confirmation: {pat}", "confirm with the user first")
        return ("ask", code) + REASONS[code]
    return ("allow", "", "", "")


def currentBranch(cwd):
    try:
        r = subprocess.run(["git", "-C", cwd, "branch", "--show-current"], capture_output=True, text=True, timeout=5)
        return r.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return ""


def emit(verdict, code, reason, alt, command, cwd):
    if verdict == "allow":
        return
    body = {"hookEventName": "PreToolUse", "permissionDecision": verdict,
            "permissionDecisionReason": f"{reason}. Instead: {alt}."}
    sys.stdout.write(json.dumps({"hookSpecificOutput": body}) + "\n")
    kit_log.event("gate", agent="bash_gate", reason_code=code, severity="block" if verdict == "deny" else "ask",
                  detail=reason, command=command, cwd=cwd)


def main():
    raw = sys.stdin.read()
    ev = json.loads(raw)
    if not isinstance(ev, dict) or ev.get("tool_name") != "Bash":
        return 0
    command = (ev.get("tool_input") or {}).get("command")
    cwd = ev.get("cwd") or os.getcwd()
    if not isinstance(command, str):
        emit("ask", "bash_no_command", *REASONS["bash_no_command"], "", cwd)
        return 0
    policy = kit_policy.loadOrDeny(overridePath=os.path.join(cwd, ".claude", "policy.json"))
    verdict, code, reason, alt = decide(command, currentBranch(cwd), policy, cwd)
    emit(verdict, code, reason, alt, command, cwd)
    return 0


if __name__ == "__main__":
    sys.exit(main())
