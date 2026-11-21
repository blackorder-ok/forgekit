---
name: security-waivers
description: How to accept a known security finding with a reason, owner and expiry in security-waivers.md. Use when a scanner or reviewer reports an accepted finding or a waiver must be checked.
pack: core
---

# Security waivers

A waiver accepts one specific finding for a limited time. It never silences a failing check.

## File
`security-waivers.md` at the project root, one YAML block: `waivers: [{id, tool, rule, location, severity, reason, owner, approved_by, created, expires, branch}]`.

## Rules
- Critical findings and any gitleaks finding are never waivable. Rotate the secret instead.
- High severity needs the user named in `approved_by`.
- The reason says why the finding does not apply here, with a file or test as evidence. "False positive" alone is rejected.
- Expiry at most 90 days after `created`. An expired waiver is an open finding.
- A renewal is a new entry with a new id. Never edit an old expiry.
- One finding per waiver. Never waive a rule project-wide.
- A `pip-audit` waiver lasts only while the vulnerable version is pinned.

## How scanners honour them
bandit `# nosec <rule>` and semgrep `# nosemgrep: <rule>` on the exact line with the waiver id; pip-audit `--ignore-vuln <id>`; the security reviewer reports `WAIVED <id>`.

## Checks
Every inline suppression has an active entry and the reverse. No expired entry. Every entry has reason, owner, created, expires. Any failure fails the ops check.

Full text: `references/full-rules.md`.
