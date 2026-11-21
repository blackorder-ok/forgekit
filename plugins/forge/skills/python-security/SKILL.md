---
name: python-security
description: Python and FastAPI security rules for request handling, SQL, files, outbound calls, secrets and dependencies, with the scanners that enforce them. Use when writing or reviewing backend code.
pack: stack
---

# Python security

1. **Input** — validate every body, query, path param and header with Pydantic and `Field` limits; `extra="forbid"`.
2. **SQL** — bound parameters only (`text()` with named params or the ORM). Table or column names from users: allowlist.
3. **Commands** — no `shell=True`, `os.system`, or `eval`/`exec` on outside data. Pass argument lists.
4. **Deserialization** — no pickle, marshal or shelve on outside data; `yaml.safe_load` only; JSON on the wire.
5. **Files** — resolve user paths against a fixed base and confirm the result stays inside. Uploads: check size, sniff content type, store under a generated name, never execute.
6. **Outbound URLs (SSRF)** — allowlist hosts, block private, loopback and link-local (also after DNS), set timeouts.
7. **Secrets and randomness** — `secrets` not `random`; argon2 or bcrypt for passwords; `secrets.compare_digest`.
8. **Errors and logs** — clients get a short message and request id; tracebacks only in logs; never log secrets or full personal data; `debug=False` outside local.
9. **Config** — secrets only through the `config-db` loader; no secret defaults.
10. **Dependencies and containers** — hashed installs, `pip-audit` on every PR, non-root containers.

## Scanners
bandit `-ll`, pip-audit, ruff `S` rules, gitleaks on every PR; semgrep (`p/python`, `p/owasp-top-ten`) on qa and release. Waive only via `security-waivers`; an inline suppression without a waiver is a finding.

## Review checklist
Endpoints validate input with a model. No string-built SQL, `shell=True`, unsafe loaders, or `random` for secrets. Every path and outbound URL checked. No secrets or tracebacks in logs or responses.

Bad/good code examples: `references/examples-and-scanners.md`.
