# Secrets Management System

Dev-Tools implements a modular, overlay-based secrets management system with provenance tracking for secure agent orchestration.

## Overview

The secrets system provides:

- **Modular Schema Architecture**: Core schema with service-specific overlays
- **Provenance Tracking**: Track which schema file defines each secret
- **Automated Validation**: CLI and CI/CD validation with detailed reporting
- **Environment Hydration**: Automated setup of development environments

## Architecture

### Schema Structure

```
config/
└── env/
  ├── .env                   # Runtime credentials (gitignored)
  ├── .env.template          # Tracked template for teammates
  ├── secrets/               # Docker-mounted secret files (gitignored)
  └── schema/                # Declarative schema + overlays
    ├── secrets.core.json
    └── overlays/
      ├── agent-ops.json
      ├── supabase.json
      ├── supabase-advanced.json
      └── vercel.json
```

### Core Schema (`secrets.core.json`)

Defines fundamental secrets required by all agents:

```json
{
  "version": "1.0.0",
  "secrets": [
    {
      "name": "GITHUB_TOKEN",
      "required": false,
      "description": "GitHub API token for agent operations",
      "sources": ["GitHub Secrets", "Codespaces auto-injected"]
    },
    {
      "name": "NODE_ENV",
      "required": true,
      "description": "Runtime environment (development|staging|production)",
      "sources": [".env", "agents/.env.agent.local"]
    }
  ]
}
```

### Overlay System

Service-specific overlays extend the core schema:

- **agent-ops.json**: Agent memory, logging, and Playwright configuration
- **supabase.json**: Basic Supabase URL and anonymous key
- **supabase-advanced.json**: Advanced Supabase features (project refs, JWT tokens)
- **vercel.json**: Vercel project IDs for deployment environments

## Validation

### CLI Commands

```bash
# Basic validation
npm run secrets:validate

# Validation with overlay discovery
npm run secrets:validate:discover

# JSON output for automation
npm run secrets:validate:json

# Environment hydration with validation
npm run secrets:hydrate
```

### Task Orchestration

```bash
# Validate secrets via Task
task toolchain:secrets:validate

# Hydrate environment
task toolchain:env:hydrate
```

### Validation Output

The validator provides detailed output including:

- **Schema Sources**: Lists core and discovered overlay files
- **Secret Counts**: Total secrets found vs. required
- **Provenance Tracking**: Shows which file defines each secret
- **Missing Secrets**: Detailed list with descriptions and sources

Example output:

```bash
=== Secrets Validation (Merged Schema) ===

Schema Sources:
  Core: config/env/schema/secrets.core.json
  Overlays: 4 discovered
    - agent-ops.json
    - supabase-advanced.json
    - supabase.json
    - vercel.json

Found Secrets:
  ✓ GITHUB_TOKEN (from secrets.core.json)

Missing Required Secrets:
  ❌ NODE_ENV (from secrets.core.json)
     Runtime environment (development|staging|production)
```

## Environment Setup

### Development Environment

1. **Create agent environment file**:

   ```bash
   cp .env.example agents/.env.agent.local
   ```

2. **Configure secrets** in `agents/.env.agent.local`:

   ```bash
   # Required
   NODE_ENV=development

   # Service-specific (examples)
   SUPABASE_URL=https://your-project.supabase.co
   SUPABASE_ANON_KEY=your-anon-key
   HIGHLIGHT_PROJECT_ID=your-project-id
   ```

3. **Hydrate environment**:

   ```bash
   npm run secrets:hydrate
   ```

### Runtime Stack Environment

Copy the tracked template into the runtime location whenever the Docker stack needs new credentials:

```bash
cp config/env/.env.template config/env/.env
```

Update `config/env/.env` with values for Langfuse, Gradient (including `GRADIENT_MODEL_ACCESS_KEY`), Supabase, and any other stack-level integrations described in `config/env/README.md`.

### CI/CD Environment

GitHub Actions automatically validates secrets:

```yaml
- name: Validate secrets with overlay discovery
  env:
    HIGHLIGHT_PROJECT_ID: ${{ secrets.HIGHLIGHT_PROJECT_ID }}
    SUPABASE_URL: ${{ secrets.SUPABASE_URL }}
    SUPABASE_ANON_KEY: ${{ secrets.SUPABASE_ANON_KEY }}
    NODE_ENV: ci
  run: npm run secrets:validate:discover
```

## Agent Manifest Integration

The agent manifest (`agents/agents-manifest.json`) tracks which secrets each agent profile requires:

```json
{
  "name": "development-workflow",
  "requiredSecrets": ["ALLOWED_PATH", "MCP_MEMORY_FILE_PATH"],
  "secretsWithProvenance": [
    {
      "name": "ALLOWED_PATH",
      "provenance": "agent-ops.json"
    }
  ]
}
```

## Adding New Secrets

### 1. Determine Schema Location

- **Core secrets**: Add to `config/env/schema/secrets.core.json`
- **Service-specific**: Create new overlay in `config/env/schema/overlays/`

### 2. Schema Format

```json
{
  "name": "YOUR_SECRET_NAME",
  "required": true,
  "description": "Description of what this secret is for",
  "sources": ["GitHub Secrets", ".env.agent.local"]
}
```

### 3. Update Environment Files

Add the new secret to the relevant template (agent-specific values in `.env.example`, runtime stack credentials in `config/env/.env.template`) and document it in setup guides.

### 4. Update Agent Manifests

Run `npm run agents:manifest` to regenerate the manifest with new secrets.

## Deployment-Specific Secrets

### GitHub Deployment PAT

- **Path**: `config/env/secrets/github_pat.txt` (gitignored)
- **Purpose**: Enables automated `git pull` on the droplet by configuring a stored credential via the deployment script.
- **Scopes**: `repo` is sufficient. Add `workflow` if deployments need to trigger actions.
- **Usage**: The deployment script copies this file to the droplet and configures `~/.git-credentials`. If the file is absent or empty, it logs a warning and skips the configuration.

> ⚠️ Never commit this file. Store it securely (password manager or secret store) and rotate routinely.

### OAuth2 Proxy (GitHub Provider)

Add the following fields to `.env` (or your preferred secret store) when wiring the new `oauth2-proxy` service that protects Prometheus behind Caddy:

| Variable                      | Description                                          |
| ----------------------------- | ---------------------------------------------------- |
| `OAUTH2_PROXY_CLIENT_ID`      | GitHub OAuth App client ID                           |
| `OAUTH2_PROXY_CLIENT_SECRET`  | GitHub OAuth App client secret                       |
| `OAUTH2_PROXY_COOKIE_SECRET`  | 32-byte base64 string securing oauth2-proxy cookies  |
| `OAUTH2_PROXY_REDIRECT_URL`   | Callback URL (`https://your-domain/oauth2/callback`) |
| `OAUTH2_PROXY_ALLOWED_EMAILS` | Comma-separated allowlist or `*`                     |
| `OAUTH2_PROXY_GITHUB_ORG`     | Optional org/team restriction                        |

These values flow into Docker Compose automatically and should be managed like any other sensitive credential.

## DigitalOcean Gradient Storage Map

Gradient introduces three distinct credential classes plus a bit of metadata. Keep them separated so rotations stay painless and you can regenerate assets programmatically.

| Category                                     | Where it lives                                                                                                                           | Purpose                                                                                                                                                                                                     |
| -------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Control-plane + model access**             | `config/env/.env` (`DIGITALOCEAN_TOKEN`, `DIGITAL_OCEAN_PAT`, `GRADIENT_API_KEY`, `GRADIENT_MODEL_ACCESS_KEY`, Langfuse, Supabase, etc.) | Lets the stack talk to Gradient + observability services. These settings deploy with `scripts/deploy.ps1`.                                                                                                  |
| **Partner provider keys (OpenAI/Anthropic)** | `config/env/secrets/openai_api_key.txt`, `config/env/secrets/anthropic_api_key.txt` (or extend `secrets.template.json`)                  | Raw vendor keys you register in the Gradient UI/API. Keeping them as standalone files mirrors the Linear/GitHub secrets pattern and keeps `.env` slim.                                                      |
| **Agent endpoint API keys**                  | `config/env/secrets/agent-access/<workspace>/<agent>.txt` (JSON blob)                                                                    | Each exposed agent endpoint issues one or more API keys via `/v2/gen-ai/agents/{agent_uuid}/api_keys`. Treat them like per-agent secrets so rotation is a file delete/regenerate instead of editing `.env`. |
| **Workspace + knowledge base metadata**      | `config/env/workspaces/*.json`                                                                                                           | Tracked manifests that describe workspaces, knowledge bases, and the agents that should exist. These files are lintable alongside the main schema and make automation repeatable.                           |

### Agent key file format

Agent access files are simple JSON documents. Example (`config/env/secrets/agent-access/the-shop/orchestrator-default.txt`):

```
{
  "workspace": "the shop",
  "agent_name": "DevTools Orchestrator",
  "agent_uuid": "uuid-from-gradient",
  "api_key_uuid": "api-key-uuid",
  "api_key_name": "devtools-orchestrator-default",
  "secret": "sk-agent-secret",
  "written_at": 1731544750
}
```

These files stay gitignored yet deploy via the existing secrets sync. Delete + rerun the automation script when you need to rotate keys.

### Workspace manifests + automation

1. Describe the workspace in `config/env/workspaces/<name>.json`. The tracked `the-shop.json` file includes:

- Workspace metadata (`name`, `uuid`, `project_id`, `region`)
- Knowledge base refs + UUID placeholders
- Agent definitions (model UUID, instructions, knowledge base refs, API key targets)

2. Run `python scripts/gradient_workspace_sync.py` (or `python ... --dry-run`) after updating `.env` and the manifest. The script:

- Reads `DIGITALOCEAN_TOKEN`/`DIGITAL_OCEAN_PAT` plus Gradient URLs from `.env`
- Ensures the workspace exists (creating it if needed)
- Resolves knowledge base UUIDs by name
- Creates/syncs agents and attaches the requested knowledge bases
- Generates agent API keys and writes them under `config/env/secrets/agent-access/...`

> ℹ️ The script only mutates Gradient when **not** run with `--dry-run`, and it automatically writes new UUIDs back into the manifest so future runs stay idempotent.

## Troubleshooting

### Validation Fails

**Missing required secrets**:

```bash
# Check what secrets are missing
npm run secrets:validate:json | jq '.details.missing[]'

# Add missing secrets to environment
echo "NODE_ENV=development" >> agents/.env.agent.local
```

**Schema discovery issues**:

```bash
# Force overlay discovery
npm run secrets:validate:discover

# Check overlay files exist
ls -la config/env/schema/overlays/
```

### Environment Issues

**Hydration fails**:

```bash
# Check environment file exists
ls -la agents/.env.agent.local

# Validate file syntax
cat agents/.env.agent.local
```

**Codespaces secrets not available**:

- Ensure secrets are configured in GitHub repository settings
- Check Codespaces environment variables: `env | grep GITHUB`

## Security Considerations

- **Never commit secrets** to version control
- **Use GitHub Secrets** for CI/CD environments
- **Validate regularly** to catch configuration drift
- **Monitor provenance** to ensure secrets come from expected sources

## Migration from Legacy System

The system automatically migrated from a monolithic `secrets.schema.json` file to the overlay system. Legacy references have been archived to `workspace/archive/schemas/`.

## API Reference

### Schema Merger Library

```typescript
import {
  discoverSchemas,
  mergeSchemas,
} from "./scripts/automation/lib/schema-merger";

// Discover all schemas
const { core, overlays } = discoverSchemas();

// Merge with provenance tracking
const mergedSchema = mergeSchemas(core, overlays);
```

### Validation Library

```typescript
import { validateSecrets } from "./scripts/automation/validate-secrets";

// Validate with options
await validateSecrets({
  discoverOverlays: true,
  jsonOutput: false,
});
```

---

**Version**: 1.0.0
**Last Updated**: 2025-11-03
