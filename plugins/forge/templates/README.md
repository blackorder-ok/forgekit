# Templates

After Phase 2, only the files that must be byte-exact are kept here. `/scaffold-project` copies them and replaces the placeholders below. Everything else is generated from a skill (see the table at the end).

## Placeholders (complete list)

| Placeholder | Source in the plan |
|---|---|
| `{{PROJECT}}` | `project` |
| `{{ENV}}` | each environment in turn |
| `{{AWS_EMULATOR_IMAGE}}` | `aws_emulator.image` (pinned) |
| `{{AWS_EMULATOR_PORT}}` | `aws_emulator.ports.<env>` |
| `{{APP_PORT}}` | `app_ports.<env>` |

## Layout
```
templates/
  README.md
  root/            .gitignore, .dockerignore
  docker/          app.Dockerfile, backend.Dockerfile, frontend.Dockerfile (page only),
                   compose.stack.yml, supervisord.conf, nginx.conf, entrypoint.sh
  ci/              ci.yml, env-tests.yml
```

## Generated instead of copied

| File written into the project | Generated from |
|---|---|
| `pytest.ini` | `test-levels` (Generated: pytest.ini) |
| `ruff.toml`, `mypy.ini` | `python-style` (Generated: ruff.toml and mypy.ini) |
| `.gitattributes`, `.github/dependabot.yml` | `dependency-policy` |
| `config/*.properties`, `secrets/*.example` | `config-db` (Generated config and secrets files) |
| `backend/`, `tests/` | Foundation feature F01, built with `/design` and `/feature` |

Dropped in Phase 2: `docs/floci.md` (the pin lives in the plan), `scripts/export_openapi.py` (comes with the first frontend feature), `frontend/placeholder/` (the frontend stage is optional).

## Status of each template
- Verified by reading: Python syntax, YAML syntax, and the file layout.
- Not built or run yet. Anything marked `TODO-VERIFY` in a file must be checked on the first run. These include the MySQL apt repository and key, the Ollama release checksum, the capability list in compose, the AWS emulator settings that disable RDS and EC2, and the AWS emulator internal port.

## Verified pins (checked 2026-11-07)
| Component | Pin | How it was verified |
|---|---|---|
| AWS emulator (Floci) | `floci/floci:2.4.0@sha256:5ee85db604c4aa74ac76e07ea5cc83086f37bb472bf3dbb97e34019e48efae9c` | Docker Hub tag and amd64 digest |
| MySQL | 8.0.46, SHA-256 `0fcdb2e88b5bb151118420745070a34621463dd85a50e1eacd7c3aa1b9d1f4a2` | Downloaded and checked; GPG signature from MySQL Release Engineering verified. Pending move to 8.4 LTS (see `changelog-custom.md`). |
| Ollama | 0.40.15, SHA-256 `628c018404a4206493efd38e46251c154ede5141b8b8dc85c659b3b027c47379` | GitHub release digest; confirmed by download before the first build |

Re-check these when you update a pin.

## Project files (added in forgekit 0.2)
`templates/project/` holds files copied unchanged into every scaffolded project: `settings.json` (to `.claude/settings.json`), `hooks/*` (to `scripts/hooks/`), `CLAUDE.md` (placeholder `{{PROJECT}}`, to the project root) and `constitution.md` (to `.claude/constitution.md`).
