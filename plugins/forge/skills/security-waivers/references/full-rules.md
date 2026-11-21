<!-- Reference for the security-waivers skill. Ported from setting-up-claude/security-waivers (v0.1.0); read only when the digest is not enough. -->

# Security waivers

A waiver is a recorded decision to accept one specific finding for a limited time. It is never a way to make a failing check pass silently.

## File
- Location: `security-waivers.md` at the project root, committed to git.
- Format: one YAML block, so tools and reviewers read the same data.

```yaml
waivers:
  - id: W001
    tool: bandit            # bandit | pip-audit | semgrep | security-reviewer
    rule: B608              # scanner rule, advisory ID, or finding title
    location: backend/app/reports/query.py:42   # or "dependency:<package>" for pip-audit
    severity: low           # low | medium | high (critical cannot be waived)
    reason: >
      Input is an integer enum from the config loader, never user text.
      Verified in backend/app/reports/query.py and its test.
    owner: <name>
    approved_by: <name>     # a different person than the owner
    created: 2026-11-07
    expires: 2027-02-05     # at most 90 days after created
    branch: develop
```

## Rules
- **Who may waive:** the owner proposes the waiver. A different person approves it. A solo developer approves their own waiver but must state it in the reason.
- **Severity:** `critical` findings are never waivable. `high` needs approval from the user, named in `approved_by`.
- **Gitleaks findings are never waivable.** A leaked secret is rotated, not waived. Remove it from history as well.
- **Reason:** must say why the finding does not apply here, with a file or test as evidence. "False positive" alone is rejected.
- **Expiry:** at most 90 days after `created`. A waiver past `expires` is an open finding, and the verify job fails until it is fixed or renewed.
- **Renewal:** a renewal is a new entry with a new id and a new reason. Editing an old expiry date is not allowed.
- **Scope:** one finding per waiver. Never waive a rule across the whole project.
- **Dependencies:** a `pip-audit` waiver is only valid while the vulnerable version is pinned. Upgrading the package closes the waiver.
- **Review:** the security reviewer checks every new or changed waiver in the diff. The user reviews all active waivers at each release.

## How scanners honour waivers
- `bandit`: an inline `# nosec <rule>` comment on the exact line, with the waiver id in a comment.
- `semgrep`: an inline `# nosemgrep: <rule>` comment, with the waiver id.
- `pip-audit`: `--ignore-vuln <advisory id>` for each active waiver. Expired waivers are not passed.
- `security-reviewer`: reports the finding as `WAIVED <id>` and leaves it out of the verdict. An expired waiver counts as an open finding.

## Checks
- Every inline suppression has a matching active entry in `security-waivers.md`, and every active entry has a matching suppression or advisory.
- No entry has `expires` in the past.
- No entry is `critical`, and no `gitleaks` entry exists.
- Every entry has a non-empty `reason`, `owner`, `created`, and `expires`.

Any failure fails the `devops` check and the `verify` job.
