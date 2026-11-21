<!-- Reference for the dependency-policy skill. Ported from setting-up-claude/dependency-policy (v0.1.0); read only when the digest is not enough. -->

# Dependency policy

## Pinning
- Direct dependencies are listed in `backend/requirements.in` and `backend/requirements-dev.in`.
- The compiled `backend/requirements.txt` and `backend/requirements-dev.txt` pin every package, including transitive ones, with hashes.
- Compile with `pip-compile --generate-hashes`, or `uv pip compile --generate-hashes --python-version 3.11 <file>.in -o <file>.txt` where pip-tools is too slow. Both write the same hashed format. Commit the `.in` and `.txt` files together.
- Install only with `pip install --require-hashes`. Docker and CI never install unpinned packages.
- Python is pinned to 3.11. Docker base images are pinned by tag, and by digest once the project is live.

## Adding a dependency
Before adding a package, record in the pull request:
- Why the standard library or an existing dependency is not enough.
- Its license. Allowed: MIT, BSD, Apache-2.0, PSF, ISC. Anything else needs a person's approval.
- Its maintenance status: a release in the last 12 months, and no open security advisory.
- Its transitive footprint: the output of `pipdeptree` for that package.

## Removing a dependency
- Remove it from the `.in` file, recompile, and confirm no import remains (`ruff` reports unused imports).

## Updating
- Dependabot opens update pull requests weekly, grouped by type: patch and minor together, major separately.
- Patch updates may merge when `verify` is green and a reviewer has read the changelog.
- Minor updates need a reviewer to read the changelog.
- Major updates need a person to approve, and a note on what changed in the code.
- Dependabot pull requests that change only `.txt` files are checked by running the same compile again (pip-compile or uv, as the project uses). If the result differs, the pull request is wrong: close it and reopen the update from the `.in` file.

## Vulnerabilities
- `pip-audit` runs on every pull request, and a finding blocks the merge.
- Response times: high severity within 7 days, medium within 30 days.
- If no fixed version exists, the finding is waived under `security-waivers`, with the reason and the expiry date.
- GitHub Actions versions are updated by Dependabot. A third-party action with a known advisory is replaced, not waived.

## Dependabot configuration
The template is `the block below`. It covers pip in `/backend`, npm in `/frontend`, and GitHub Actions. `/scaffold-project` writes it to `.github/dependabot.yml` unchanged.

## Checks for the reviewer
- No dependency added without the justification above.
- No `.txt` file changed without its `.in` file changing, or a Dependabot update.
- No unpinned package in a Dockerfile or workflow.

## Generated: dependabot.yml and .gitattributes
Scaffold writes `.github/dependabot.yml` and `.gitattributes` at the project root, unchanged. Remove the `frontend` entry when the plan has no page.

```yaml
version: 2
updates:
  - package-ecosystem: "pip"
    directory: "/backend"
    schedule:
      interval: "weekly"
    open-pull-requests-limit: 5
    groups:
      minor-and-patch:
        update-types: ["minor", "patch"]
  - package-ecosystem: "npm"
    directory: "/frontend"
    schedule:
      interval: "weekly"
    open-pull-requests-limit: 5
    groups:
      minor-and-patch:
        update-types: ["minor", "patch"]
  - package-ecosystem: "github-actions"
    directory: "/"
    schedule:
      interval: "weekly"
    open-pull-requests-limit: 5
```

```
* text=auto eol=lf
*.sh text eol=lf
```
