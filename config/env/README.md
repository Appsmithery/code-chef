# Runtime Secrets Directory

The `config/env` directory now holds both runtime credentials (ignored at commit time) and the declarative schema used to validate them. Use this folder as the single source of truth for anything related to secrets.

## Layout

| Path                                  | Purpose                                                                                                                                                     | Tracked?        |
| ------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------- |
| `config/env/.env`                     | Canonical runtime environment for Docker Compose and deploy scripts. Copy from `.env.template` and fill with real keys before running `scripts/deploy.ps1`. | ❌ (gitignored) |
| `config/env/.env.template`            | Safe template checked into git so teammates know which keys are required.                                                                                   | ✅              |
| `config/env/secrets/`                 | Per-service secret files mounted as Docker secrets (e.g., `linear_oauth_token.txt`). Managed via `scripts/setup_secrets.sh`.                                | ❌ (gitignored) |
| `config/env/secrets.template.json`    | JSON scaffold for teams that prefer storing secrets in a single file before splitting into `.txt` files.                                                    | ✅              |
| `config/env/schema/secrets.core.json` | Core schema enumerating shared secrets and provenance metadata.                                                                                             | ✅              |
| `config/env/schema/overlays/*.json`   | Service-specific overlays extending the core schema.                                                                                                        | ✅              |
| `config/env/schema/*.ts`              | Tooling that merges/validates schemas and regenerates agent manifests.                                                                                      | ✅              |

## Storage Guidance

| Secret class                                                         | Storage location                                                           | Notes                                                                  |
| -------------------------------------------------------------------- | -------------------------------------------------------------------------- | ---------------------------------------------------------------------- | ------------ |
| Runtime credentials for agents (Langfuse, Gradient, DB, OAuth, etc.) | `config/env/.env` on each machine/droplet                                  | Keep in password manager. Use `config/env/.env.template` as reference. |
| Docker secret files (Linear tokens, PATs)                            | `config/env/secrets/*.txt` locally, then copy to droplet via deploy script | Generated via `scripts/setup_secrets.sh`.                              |
| Declarative schema definitions                                       | `config/env/schema` (tracked)                                              | Updated whenever new secrets or overlays are introduced.               |
| CI/CD secrets                                                        | GitHub Actions secrets / environment variables                             | Validated through `npm run secrets:validate[:json                      | :discover]`. |
| Codespaces/devcontainer secrets                                      | GitHub Codespaces secrets                                                  | Provide same keys as `.env` for parity.                                |

## Syncing to the Droplet

`scripts/deploy.ps1 -Target remote` now uploads `config/env/.env` and the entire `config/env/secrets/` directory automatically. To push changes manually:

```powershell
scp config/env/.env root@45.55.173.72:/opt/Dev-Tools/config/env/.env
scp -r config/env/secrets/* root@45.55.173.72:/opt/Dev-Tools/config/env/secrets/
```

Run `scripts/deploy.ps1 -Target remote` afterward to rebuild and restart the stack with the new credentials.
