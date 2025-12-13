# Production Deployment & Distribution Optimization Plan

**Date**: December 13, 2025  
**Version**: 1.0.0  
**Status**: Ready for UAT  
**Security Level**: API Key Gated (Private Alpha)

---

## 🎯 Phase 1: Full Production Update

### Recommended Workflow Execution Sequence

#### Step 1: Deploy Backend Services (~3 min)

```bash
# Trigger via GitHub UI
Actions → Intelligent Deploy to Droplet → Run workflow
  branch: main
  deploy_type: full  # Complete rebuild for clean state
```

**What This Does:**

- ✅ Pulls latest code to droplet (45.55.173.72)
- ✅ Rebuilds all Docker containers with BuildKit caching
- ✅ Restarts services: orchestrator, rag-context, state-persist, agent-registry, langgraph
- ✅ Runs health checks on all 5 services (90s timeout)
- ✅ Validates PostgreSQL, Qdrant connections

**Expected Duration**: ~3 minutes  
**Health Check Endpoints**:

- http://45.55.173.72:8001/health (orchestrator)
- http://45.55.173.72:8007/health (rag-context)
- http://45.55.173.72:8008/health (state-persist)
- http://45.55.173.72:8009/health (agent-registry)
- http://45.55.173.72:8010/health (langgraph)

---

#### Step 2: Deploy Frontend (~2 min)

```bash
# Wait for backend health checks to pass, then:
Actions → Deploy Frontend to Production → Run workflow
```

**What This Does:**

- ✅ Builds React production bundle
- ✅ Syncs dist/ to /opt/Dev-Tools/support/frontend/dist/
- ✅ Restarts Caddy reverse proxy
- ✅ Serves at https://codechef.appsmithery.co

**Expected Duration**: ~2 minutes  
**Verify**: Open https://codechef.appsmithery.co in browser

---

#### Step 3: Publish VS Code Extension (~4 min)

```bash
# After backend + frontend verified, publish extension:
Actions → Publish VS Code Extension → Run workflow
  version: 1.0.0  # Or 1.0.1 if updating
  version_bump: none
```

**What This Does:**

- ✅ Updates package.json version
- ✅ Compiles TypeScript
- ✅ Packages .vsix file
- ✅ Publishes to VS Code Marketplace
- ✅ Creates Git tag (v1.0.0)
- ✅ Uploads VSIX to GitHub workflow artifacts

**Expected Duration**: ~4 minutes  
**Verify**: Search "code-chef" in VS Code Extensions Marketplace

---

#### Step 4: Post-Deployment Cleanup (~2 min)

```bash
# Optional but recommended after full deployment:
Actions → Cleanup Docker Resources → Run workflow
  cleanup_type: standard
```

**What This Does:**

- ✅ Removes stopped containers
- ✅ Prunes dangling images
- ✅ Frees up disk space (~500MB-2GB)

**Expected Duration**: ~2 minutes

---

### Total Deployment Time

**~11 minutes** for complete production update (backend + frontend + extension + cleanup)

---

## 📦 Phase 2: GitHub Releases Strategy

### Current State

- ✅ Extension publishes to VS Code Marketplace
- ❌ No GitHub Releases created
- ❌ No versioned VSIX downloads
- ❌ No release notes automation

### Recommended: Automated Release Creation

#### 1. Update `publish-extension.yml` to Create GitHub Release

Add after VSIX upload step:

````yaml
- name: Create GitHub Release
  uses: softprops/action-gh-release@v1
  with:
    tag_name: v${{ github.event.inputs.version }}
    name: code-chef v${{ github.event.inputs.version }}
    body: |
      ## 🎉 code-chef v${{ github.event.inputs.version }}

      **Your AI DevOps Team, Orchestrated by the Head Chef**

      ### What's New
      - Multi-agent orchestration via LangGraph
      - 150+ MCP tools integration
      - Progressive tool loading (token-efficient)
      - ModelOps extension for model training/deployment

      ### Installation

      **Option 1: VS Code Marketplace** (Recommended)
      ```bash
      code --install-extension appsmithery.vscode-codechef
      ```

      **Option 2: Manual VSIX Install**
      1. Download `vscode-codechef-${{ github.event.inputs.version }}.vsix` below
      2. In VS Code: Extensions → ⋯ → Install from VSIX

      ### Requirements
      - **API Key Required**: Set `ORCHESTRATOR_API_KEY` in VS Code settings
      - Get your API key: Contact @alextorelli28 (Private Alpha)

      ### Documentation
      - [Setup Guide](https://github.com/Appsmithery/code-chef/blob/main/README.md)
      - [Architecture](https://github.com/Appsmithery/code-chef/blob/main/support/docs/architecture-and-platform/ARCHITECTURE.md)
      - [API Reference](https://codechef.appsmithery.co)

      ---

      **⚠️ Private Alpha**: This release is gated behind API key authentication. Unauthorized usage will be blocked.
    files: |
      extensions/vscode-codechef/vscode-codechef-*.vsix
    draft: false
    prerelease: false
    generate_release_notes: true
  env:
    GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
````

#### 2. Enable Release Immutability

In GitHub repo settings:

- Navigate to: **Settings → General → Pull Requests**
- Enable: ✅ **"Disallow assets and tags from being modified once a release is published"**

This prevents accidental overwrites and ensures release integrity.

---

## 📦 Phase 3: GitHub Packages (npm Registry) Strategy

### Architecture Overview

```
code-chef (monorepo)
├── @appsmithery/code-chef-core       # Shared lib (MCP client, tools)
├── @appsmithery/code-chef-agents     # Agent base classes
├── @appsmithery/code-chef-workflows  # Workflow templates
└── @appsmithery/vscode-codechef      # VS Code extension (references above)
```

### Benefits of GitHub Packages

1. **Private registry** - Control access via GitHub Personal Access Tokens (PAT)
2. **Scoped packages** - `@appsmithery/*` namespace
3. **Version pinning** - Strict semver for reproducible builds
4. **Dependency sharing** - Reuse core lib across projects
5. **API key enforcement** - Runtime validation in shared lib

---

### Implementation Plan

#### 1. Create Shared Core Package

**New File**: `packages/core/package.json`

```json
{
  "name": "@appsmithery/code-chef-core",
  "version": "1.0.0",
  "description": "Core library for code-chef multi-agent platform",
  "private": false,
  "publishConfig": {
    "registry": "https://npm.pkg.github.com/@appsmithery",
    "access": "restricted"
  },
  "repository": {
    "type": "git",
    "url": "https://github.com/Appsmithery/code-chef.git",
    "directory": "packages/core"
  },
  "main": "dist/index.js",
  "types": "dist/index.d.ts",
  "files": ["dist", "README.md"],
  "exports": {
    ".": "./dist/index.js",
    "./mcp": "./dist/mcp/index.js",
    "./auth": "./dist/auth/index.js"
  },
  "scripts": {
    "build": "tsc",
    "prepublishOnly": "npm run build"
  },
  "dependencies": {
    "axios": "^1.6.0"
  },
  "peerDependencies": {
    "typescript": "^5.0.0"
  }
}
```

**New File**: `packages/core/src/index.ts`

```typescript
export { MCPToolClient } from "./mcp/client";
export { AuthValidator } from "./auth/validator";
export { ProgressiveMCPLoader } from "./mcp/loader";

// Re-export types
export type { AgentConfig, WorkflowState } from "./types";
```

**New File**: `packages/core/src/auth/validator.ts`

```typescript
/**
 * API Key Validation - Enforces authentication for all operations
 *
 * Usage:
 *   import { AuthValidator } from '@appsmithery/code-chef-core/auth';
 *   const validator = new AuthValidator();
 *   await validator.validate(apiKey);
 */

export class AuthValidator {
  private readonly orchestratorUrl: string;

  constructor(
    orchestratorUrl: string = "https://codechef.appsmithery.co/api/v1"
  ) {
    this.orchestratorUrl = orchestratorUrl;
  }

  /**
   * Validates API key against orchestrator service.
   *
   * @param apiKey - User's API key (format: chef_<uuid>)
   * @returns Promise<boolean> - true if valid, throws error if invalid
   * @throws {AuthenticationError} - If key is invalid or expired
   */
  async validate(apiKey: string): Promise<boolean> {
    if (!apiKey || !apiKey.startsWith("chef_")) {
      throw new AuthenticationError(
        'Invalid API key format. Must start with "chef_"'
      );
    }

    try {
      const response = await fetch(`${this.orchestratorUrl}/auth/validate`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${apiKey}`,
        },
      });

      if (!response.ok) {
        if (response.status === 401) {
          throw new AuthenticationError("API key is invalid or expired");
        }
        if (response.status === 403) {
          throw new AuthenticationError(
            "API key does not have required permissions"
          );
        }
        throw new AuthenticationError(
          `Validation failed: ${response.statusText}`
        );
      }

      const data = await response.json();
      return data.valid === true;
    } catch (error) {
      if (error instanceof AuthenticationError) {
        throw error;
      }
      throw new AuthenticationError(
        `Failed to validate API key: ${error.message}`
      );
    }
  }

  /**
   * Validates and caches result for 5 minutes.
   * Use for frequent operations to reduce validation calls.
   */
  private validationCache = new Map<
    string,
    { valid: boolean; expires: number }
  >();

  async validateCached(apiKey: string): Promise<boolean> {
    const cached = this.validationCache.get(apiKey);
    const now = Date.now();

    if (cached && cached.expires > now) {
      if (!cached.valid) {
        throw new AuthenticationError("API key is invalid (cached)");
      }
      return true;
    }

    const valid = await this.validate(apiKey);
    this.validationCache.set(apiKey, {
      valid,
      expires: now + 5 * 60 * 1000, // 5 minutes
    });

    return valid;
  }
}

export class AuthenticationError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "AuthenticationError";
  }
}
```

---

#### 2. Update Extension to Use Shared Package

**Update**: `extensions/vscode-codechef/package.json`

```json
{
  "dependencies": {
    "@appsmithery/code-chef-core": "^1.0.0"
    // ... other deps
  }
}
```

**Update**: `extensions/vscode-codechef/src/extension.ts`

```typescript
import { AuthValidator } from "@appsmithery/code-chef-core/auth";

export async function activate(context: vscode.ExtensionContext) {
  // Get API key from settings
  const config = vscode.workspace.getConfiguration("codechef");
  const apiKey = config.get<string>("orchestratorApiKey");

  if (!apiKey) {
    vscode.window
      .showErrorMessage(
        'code-chef: API key not configured. Set "codechef.orchestratorApiKey" in settings.',
        "Open Settings"
      )
      .then((selection) => {
        if (selection === "Open Settings") {
          vscode.commands.executeCommand(
            "workbench.action.openSettings",
            "codechef.orchestratorApiKey"
          );
        }
      });
    return;
  }

  // Validate API key on activation
  const validator = new AuthValidator();
  try {
    await validator.validate(apiKey);
    vscode.window.showInformationMessage(
      "code-chef: API key validated successfully"
    );
  } catch (error) {
    vscode.window
      .showErrorMessage(
        `code-chef: ${error.message}. Contact @alextorelli28 for access.`,
        "Get API Key"
      )
      .then((selection) => {
        if (selection === "Get API Key") {
          vscode.env.openExternal(
            vscode.Uri.parse(
              "https://github.com/Appsmithery/code-chef/issues/new?template=api-access-request.md"
            )
          );
        }
      });
    return;
  }

  // Rest of activation logic...
}
```

---

#### 3. Create Publishing Workflow for Packages

**New File**: `.github/workflows/publish-packages.yml`

```yaml
name: Publish Packages to GitHub Registry

on:
  workflow_dispatch:
    inputs:
      package:
        description: "Package to publish"
        required: true
        type: choice
        options:
          - core
          - agents
          - workflows
          - all
      version:
        description: "Version to publish"
        required: true
        type: string

jobs:
  publish:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: "20"
          registry-url: "https://npm.pkg.github.com"
          scope: "@appsmithery"

      - name: Configure npm for GitHub Packages
        run: |
          echo "@appsmithery:registry=https://npm.pkg.github.com" >> .npmrc
          echo "//npm.pkg.github.com/:_authToken=${{ secrets.GITHUB_TOKEN }}" >> .npmrc

      - name: Publish @appsmithery/code-chef-core
        if: github.event.inputs.package == 'core' || github.event.inputs.package == 'all'
        working-directory: packages/core
        run: |
          npm version ${{ github.event.inputs.version }} --no-git-tag-version
          npm install
          npm run build
          npm publish
        env:
          NODE_AUTH_TOKEN: ${{ secrets.GITHUB_TOKEN }}

      - name: Create Git tag
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git tag -a "packages/core/v${{ github.event.inputs.version }}" -m "Release @appsmithery/code-chef-core@${{ github.event.inputs.version }}"
          git push origin "packages/core/v${{ github.event.inputs.version }}"
```

---

#### 4. Consumer Installation (Other Projects)

**For Other Repos to Use code-chef Packages:**

**Step 1**: Create `.npmrc` in project root:

```ini
@appsmithery:registry=https://npm.pkg.github.com
//npm.pkg.github.com/:_authToken=${GITHUB_TOKEN}
```

**Step 2**: Set environment variable:

```bash
# In CI/CD
export GITHUB_TOKEN=<your-github-pat>

# Or add to .env (don't commit!)
echo "GITHUB_TOKEN=<your-pat>" >> .env
```

**Step 3**: Install package:

```bash
npm install @appsmithery/code-chef-core@^1.0.0
```

**Step 4**: Use in code:

```typescript
import { AuthValidator } from "@appsmithery/code-chef-core/auth";

const validator = new AuthValidator();
await validator.validate(process.env.CHEF_API_KEY);
```

---

## 🔐 Phase 4: Multi-Layer API Key Gating

### Security Architecture

```
User Request
    ↓
[Layer 1] VS Code Extension - Validates API key on activation
    ↓
[Layer 2] Caddy Reverse Proxy - Rate limiting (optional)
    ↓
[Layer 3] Orchestrator FastAPI - Bearer token validation
    ↓
[Layer 4] Agent Nodes - Per-request validation (optional)
    ↓
[Layer 5] LLM Providers - OpenRouter API key (separate)
```

---

### Implementation

#### Layer 1: VS Code Extension (Client-Side)

**Location**: `extensions/vscode-codechef/src/extension.ts`

- ✅ Validates API key on activation
- ✅ Shows error if missing or invalid
- ✅ Caches validation for 5 minutes
- ✅ Includes API key in all HTTP requests to orchestrator

---

#### Layer 2: Caddy Rate Limiting (Optional)

**Location**: `config/caddy/Caddyfile`

```caddyfile
codechef.appsmithery.co {
    # Rate limiting: 100 requests per minute per IP
    rate_limit {
        zone api {
            key {remote_host}
            events 100
            window 1m
        }
    }

    # API routes
    route /api/v1/* {
        rate_limit api

        reverse_proxy orchestrator:8001
    }

    # Static files (no rate limit)
    route /* {
        root * /srv/frontend
        try_files {path} /index.html
        file_server
    }
}
```

---

#### Layer 3: Orchestrator API Key Validation

**New File**: `agent_orchestrator/auth/middleware.py`

```python
"""
FastAPI middleware for API key authentication.
Validates Bearer tokens against allowed keys database.
"""

from fastapi import Request, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
import secrets
import hashlib

security = HTTPBearer()

# In production, store in PostgreSQL with hashed keys
VALID_API_KEYS = {
    "chef_dev_test_key": {
        "user": "alextorelli",
        "email": "alex@appsmithery.co",
        "tier": "admin",
        "created_at": "2025-12-13"
    }
}

def hash_api_key(key: str) -> str:
    """Hash API key for secure storage."""
    return hashlib.sha256(key.encode()).hexdigest()

async def validate_api_key(
    credentials: HTTPAuthorizationCredentials
) -> dict:
    """
    Validates API key from Authorization header.

    Args:
        credentials: HTTPAuthorizationCredentials from FastAPI

    Returns:
        dict: User metadata if valid

    Raises:
        HTTPException: 401 if invalid
    """
    api_key = credentials.credentials

    # Check format
    if not api_key.startswith("chef_"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key format"
        )

    # Lookup in database (simplified - use PostgreSQL in production)
    user_data = VALID_API_KEYS.get(api_key)

    if not user_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired API key"
        )

    return user_data

# Middleware function
async def verify_api_key(request: Request):
    """
    Middleware to validate API key on all requests.
    Exempt paths: /health, /docs
    """
    # Exempt health checks and docs
    if request.url.path in ["/health", "/docs", "/openapi.json"]:
        return

    # Get Authorization header
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key. Set 'codechef.orchestratorApiKey' in VS Code settings."
        )

    # Extract Bearer token
    if not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Authorization header format"
        )

    api_key = auth_header.replace("Bearer ", "")
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=api_key)

    # Validate
    user_data = await validate_api_key(credentials)

    # Attach user data to request state for logging
    request.state.user = user_data
```

**Update**: `agent_orchestrator/main.py`

```python
from fastapi import FastAPI, Depends
from agent_orchestrator.auth.middleware import verify_api_key, validate_api_key
from fastapi.security import HTTPBearer

app = FastAPI()
security = HTTPBearer()

# Add global dependency
@app.middleware("http")
async def auth_middleware(request, call_next):
    await verify_api_key(request)
    response = await call_next(request)
    return response

@app.post("/api/v1/execute")
async def execute_workflow(
    message: str,
    credentials = Depends(security)
):
    # User already validated by middleware
    user_data = await validate_api_key(credentials)

    # Log usage for billing/monitoring
    logger.info(f"Request from user: {user_data['user']}, tier: {user_data['tier']}")

    # Execute workflow...
    return {"status": "ok"}
```

---

#### Layer 4: Database-Backed API Keys

**New Migration**: `config/state/api_keys.sql`

```sql
CREATE TABLE api_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    key_hash VARCHAR(64) NOT NULL UNIQUE,  -- SHA-256 hash
    key_prefix VARCHAR(20) NOT NULL,       -- First 8 chars (chef_dev)
    user_id VARCHAR(255) NOT NULL,
    email VARCHAR(255),
    tier VARCHAR(50) DEFAULT 'free',       -- free, pro, admin
    status VARCHAR(20) DEFAULT 'active',   -- active, suspended, revoked
    rate_limit_rpm INTEGER DEFAULT 60,     -- Requests per minute
    created_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP,
    last_used_at TIMESTAMP,
    usage_count INTEGER DEFAULT 0
);

CREATE INDEX idx_api_keys_hash ON api_keys(key_hash);
CREATE INDEX idx_api_keys_user ON api_keys(user_id);
CREATE INDEX idx_api_keys_status ON api_keys(status);

-- Insert admin key for alextorelli
INSERT INTO api_keys (
    key_hash,
    key_prefix,
    user_id,
    email,
    tier,
    status,
    rate_limit_rpm
) VALUES (
    'INSERT_HASHED_KEY_HERE',
    'chef_adm',
    'alextorelli',
    'alex@appsmithery.co',
    'admin',
    'active',
    1000
);
```

---

## 📊 Phase 5: Usage Tracking & Monitoring

### Metrics to Track

**New Table**: `config/state/api_usage.sql`

```sql
CREATE TABLE api_usage (
    id BIGSERIAL PRIMARY KEY,
    api_key_id UUID REFERENCES api_keys(id),
    endpoint VARCHAR(255) NOT NULL,
    method VARCHAR(10) NOT NULL,
    status_code INTEGER,
    latency_ms INTEGER,
    tokens_used INTEGER,
    cost_usd DECIMAL(10, 6),
    error_message TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_api_usage_key ON api_usage(api_key_id);
CREATE INDEX idx_api_usage_date ON api_usage(created_at);

-- Materialized view for daily usage
CREATE MATERIALIZED VIEW api_usage_daily AS
SELECT
    api_key_id,
    DATE(created_at) as usage_date,
    COUNT(*) as request_count,
    AVG(latency_ms) as avg_latency_ms,
    SUM(tokens_used) as total_tokens,
    SUM(cost_usd) as total_cost_usd
FROM api_usage
GROUP BY api_key_id, DATE(created_at);

-- Refresh daily at 1 AM
CREATE OR REPLACE FUNCTION refresh_api_usage_daily()
RETURNS void AS $$
BEGIN
    REFRESH MATERIALIZED VIEW api_usage_daily;
END;
$$ LANGUAGE plpgsql;
```

---

## 🚀 Phase 6: Deployment Checklist

### Pre-Deployment

- [ ] **Backup current production state**

  ```bash
  ssh root@45.55.173.72
  cd /opt/Dev-Tools
  docker compose exec state-persist pg_dump -U postgres codechef > backup-$(date +%Y%m%d).sql
  ```

- [ ] **Verify all secrets are set**

  ```bash
  # Check GitHub secrets via UI
  Settings → Secrets and variables → Actions
  ```

- [ ] **Test API key validation locally**
  ```bash
  curl -X POST https://codechef.appsmithery.co/api/v1/auth/validate \
    -H "Authorization: Bearer chef_test_key"
  ```

### Deployment Execution

1. ✅ **Run deploy-intelligent.yml** (deploy_type: full)
2. ✅ **Wait for health checks to pass** (~90 seconds)
3. ✅ **Run deploy-frontend.yml**
4. ✅ **Verify frontend loads** (https://codechef.appsmithery.co)
5. ✅ **Run publish-extension.yml** (version: 1.0.0)
6. ✅ **Wait for marketplace publication** (~10 minutes)
7. ✅ **Test extension installation**
   ```bash
   code --install-extension appsmithery.vscode-codechef
   ```
8. ✅ **Configure API key in VS Code**
   - Settings → Search "codechef"
   - Set "codechef.orchestratorApiKey"
9. ✅ **Test workflow execution**
10. ✅ **Run cleanup-docker-resources.yml** (cleanup_type: standard)

### Post-Deployment

- [ ] **Monitor logs for 30 minutes**

  ```bash
  ssh root@45.55.173.72
  cd /opt/Dev-Tools
  docker compose logs -f --tail=100
  ```

- [ ] **Check LangSmith traces**

  - Project: code-chef-production
  - Filter: start_time > now-1h

- [ ] **Verify metrics**

  ```bash
  curl http://45.55.173.72:8001/metrics/tokens
  ```

- [ ] **Create GitHub Release** (auto via publish-extension.yml)

- [ ] **Update Linear issue** (CHEF-255) → Status: Deployed

---

## 📚 Phase 7: Documentation Updates

### User-Facing Docs

**Update**: `README.md`

````markdown
## 🔐 Private Alpha Access

code-chef is currently in **Private Alpha** and requires an API key.

### Getting Started

1. **Request Access**: Open an issue with template [API Access Request](https://github.com/Appsmithery/code-chef/issues/new?template=api-access-request.md)
2. **Receive API Key**: You'll get a key in format `chef_<uuid>`
3. **Install Extension**:
   ```bash
   code --install-extension appsmithery.vscode-codechef
   ```
````

4. **Configure API Key**:
   - Open VS Code Settings (Ctrl+,)
   - Search: "codechef.orchestratorApiKey"
   - Paste your API key

### Troubleshooting

**"Invalid API key" error?**

- Verify key format: `chef_<uuid>`
- Check expiration date
- Contact @alextorelli28 for renewal

**Extension not loading?**

- Check Output panel: View → Output → code-chef
- Verify orchestrator health: https://codechef.appsmithery.co/api/v1/health

```

---

## 🎯 Summary

### Deployment Order (Full Update)

| Step | Workflow | Duration | Critical |
|------|----------|----------|----------|
| 1 | deploy-intelligent.yml (full) | ~3 min | ✅ Yes |
| 2 | deploy-frontend.yml | ~2 min | ✅ Yes |
| 3 | publish-extension.yml | ~4 min | ✅ Yes |
| 4 | cleanup-docker-resources.yml | ~2 min | ⚠️ Optional |

**Total**: ~11 minutes for complete production update

### Distribution Strategy

| Component | Distribution | Access Control |
|-----------|--------------|----------------|
| Backend Services | Docker (Droplet) | Network isolation + API keys |
| Frontend | Caddy (HTTPS) | Public read, API gated writes |
| VS Code Extension | Marketplace + VSIX | API key required at runtime |
| Shared Packages | GitHub Packages | GitHub PAT required |
| Releases | GitHub Releases | Public read, immutable |

### Security Layers

1. ✅ **Extension activation** - API key validation
2. ✅ **HTTP requests** - Bearer token in Authorization header
3. ✅ **Orchestrator middleware** - FastAPI dependency injection
4. ✅ **Database storage** - Hashed keys, expiration, rate limits
5. ✅ **Usage tracking** - Monitoring, alerting, billing-ready

---

**Next Actions**:
1. Execute deployment sequence (Steps 1-4)
2. Test API key validation end-to-end
3. Create API key for alextorelli (admin tier)
4. Document API key request process
5. Monitor usage for 24 hours
6. Enable rate limiting if needed

**Status**: Ready for UAT with API key gating 🔐
```
