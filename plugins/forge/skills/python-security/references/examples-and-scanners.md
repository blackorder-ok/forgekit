<!-- Reference for the python-security skill. Ported from setting-up-claude/python-security (v0.1.0); read only when the digest is not enough. -->

# Python security

Every rule has a reason, a bad example, and a good example. Scanners catch some of these. The rest are checked by the security reviewer.

## 1. Input at the edge
- Validate every request body, query, path parameter, and header with Pydantic models. Use `Field` limits on strings and numbers.
- Reject unknown fields with `model_config = ConfigDict(extra="forbid")`.

```python
# ❌ raw dict, no limits
@app.post("/notes")
async def create(body: dict): ...

# ✅ typed, bounded, extra fields rejected
class NoteIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str = Field(min_length=1, max_length=200)

@app.post("/notes")
async def create(body: NoteIn): ...
```

## 2. SQL
- Bound parameters only. Use SQLAlchemy `text()` with named parameters, or the ORM.

```python
# ❌ string formatting
db.execute(f"SELECT * FROM users WHERE email = '{email}'")

# ✅ bound parameter
db.execute(text("SELECT * FROM users WHERE email = :email"), {"email": email})
```

- Table and column names from user input are never allowed. Use an allowlist.

## 3. Commands
- No `shell=True`. Pass arguments as a list.
- No `os.system`, `os.popen`, or `eval`/`exec` on anything that came from outside the process.

```python
# ❌
subprocess.run(f"convert {filename} out.png", shell=True)

# ✅
subprocess.run(["convert", filename, "out.png"], check=True)
```

## 4. Deserialization
- No `pickle`, `marshal`, or `shelve` on data from outside the process.
- `yaml.safe_load` only. Never `yaml.load`.
- JSON is the wire format.

## 5. Files and paths
- Resolve user-supplied paths against a fixed base directory, then check the result stays inside it.

```python
# ✅
base = Path(settings.downloads_dir).resolve()
target = (base / name).resolve()
if base not in target.parents:
    raise ValueError("path outside allowed directory")
```

- Uploads: check size before reading, check the content type by reading the bytes, and store under a generated name. Never run or import an uploaded file.

## 6. Outbound requests (SSRF)
- A URL supplied by a user or a model is checked against an allowlist of hosts.
- Block private, loopback, and link-local addresses, including after DNS resolution.
- Set timeouts on every outbound client call.

## 7. Randomness and secrets
- Tokens, IDs used for access, and reset codes use `secrets`, never `random`.
- Passwords are hashed with argon2 or bcrypt. MD5, SHA-1, and plain SHA-256 are not password hashes.
- Comparing secrets uses `secrets.compare_digest`.

```python
# ❌
token = str(random.random())
# ✅
token = secrets.token_urlsafe(32)
```

## 8. Errors and logging
- Clients get a short error message and a request ID. Tracebacks and internal messages go to logs only.
- Never log passwords, tokens, keys, or full personal data.
- `debug=False` and no reload flags outside local development.

## 9. Configuration
- Secrets come from the secrets file through the `config-db` loader only.
- No secret default values in code.

## 10. Dependencies and containers
- Install only from hashed requirements files (`--require-hashes`).
- `pip-audit` runs on every pull request. A finding blocks the merge until fixed or waived under `security-waivers`.
- Containers run as a non-root user.

## Scanners and where they run

| Tool | Rule set | Runs on |
|---|---|---|
| `bandit -r backend -ll` | medium and high severity | every pull request, in `devops` checks |
| `pip-audit -r backend/requirements.txt` | known advisories | every pull request, in `devops` checks |
| `ruff` with `S` rules | security lint | every pull request |
| `semgrep` with `p/python` and `p/owasp-top-ten` | pattern rules | `qa` and `release` |
| `gitleaks` | committed secrets | every pull request |

## Waivers
A scanner finding can be waived only as described in the `security-waivers` skill. Inline suppressions without a matching waiver are findings.

## Review checklist
- Every endpoint validates its input with a model.
- No string-built SQL, no `shell=True`, no unsafe loaders, no `random` for secrets.
- Every file path and outbound URL is checked before use.
- Errors and logs contain no secrets and no tracebacks for clients.
