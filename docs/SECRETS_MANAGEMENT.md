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
├── secrets.core.json          # Core secrets (GitHub, Node.js, Highlight.io)
└── secrets.overlays/          # Service-specific overlays
    ├── agent-ops.json         # Agent operation secrets
    ├── supabase.json          # Supabase configuration
    ├── supabase-advanced.json # Advanced Supabase features
    └── vercel.json            # Vercel deployment secrets
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
  Core: config/secrets.core.json
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

1. **Create environment file**:

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

- **Core secrets**: Add to `config/secrets.core.json`
- **Service-specific**: Create new overlay in `config/secrets.overlays/`

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

Add the new secret to `.env.example` and document in setup guides.

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
ls -la config/secrets.overlays/
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
