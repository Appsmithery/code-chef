# **Revised Architecture: Docker Hub + MECE Compartmentalization**

### **Containers/Orchestration (Docker Hub)**

- All agent images: `yourdockerhubuser/dev-tools-orchestrator:latest`, etc.
- MCP Gateway + servers
- Models (if using local inference)

### **Storage/State (DigitalOcean Droplet)**

- Qdrant vector DB (persistent volume)
- PostgreSQL workflow state
- Config/secrets mounts

### **Observability (External SaaS)**

- Langfuse (cloud.langfuse.com) for LLM tracing
- Prometheus + Grafana (optional self-host or cloud)

### **LLM Inference (DigitalOcean Gradient AI)**

- Serverless API calls (no local models)
- OpenAI-compatible endpoint

---

## Implementation Changes

### 1. Update CI Workflow to Use Docker Hub

```yaml
name: Build and Push to Docker Hub

on:
  push:
    branches: [main, develop]
  workflow_dispatch:

env:
  DOCKER_USERNAME: ${{ secrets.DOCKER_USERNAME }}
  IMAGE_TAG: ${{ github.sha }}

jobs:
  build-and-push:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Login to Docker Hub
        uses: docker/login-action@v3
        with:
          username: ${{ secrets.DOCKER_USERNAME }}
          password: ${{ secrets.DOCKER_HUB_TOKEN }}

      - name: Prepare .env file
        run: |
          cat > compose/.env << EOF
          IMAGE_TAG=${{ env.IMAGE_TAG }}
          LANGFUSE_SECRET_KEY=${{ secrets.LANGFUSE_SECRET_KEY }}
          LANGFUSE_PUBLIC_KEY=${{ secrets.LANGFUSE_PUBLIC_KEY }}
          LANGFUSE_HOST=https://us.cloud.langfuse.com
          GRADIENT_API_KEY=${{ secrets.GRADIENT_API_KEY }}
          GRADIENT_BASE_URL=https://inference.do-ai.run/v1
          LINEAR_OAUTH_DEV_TOKEN=${{ secrets.LINEAR_OAUTH_DEV_TOKEN }}
          QDRANT_API_KEY=${{ secrets.QDRANT_API_KEY }}
          QDRANT_URL=${{ secrets.QDRANT_URL }}
          EOF

      - name: Build and push all services
        run: |
          cd compose
          docker compose build
          docker compose push

      - name: Cleanup
        if: always()
        run: |
          docker builder prune -f
          docker image prune -f

  deploy:
    needs: build-and-push
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - name: Configure SSH
        run: |
          mkdir -p ~/.ssh
          echo "${{ secrets.DROPLET_SSH_KEY }}" > ~/.ssh/deploy_key
          chmod 600 ~/.ssh/deploy_key
          ssh-keyscan -H 45.55.173.72 >> ~/.ssh/known_hosts

      - name: Deploy to droplet
        run: |
          ssh -i ~/.ssh/deploy_key root@45.55.173.72 << 'EOF'
            cd /opt/Dev-Tools
            git pull origin main
            
            # Update .env with image tag
            sed -i "s/^IMAGE_TAG=.*/IMAGE_TAG=${{ github.sha }}/" compose/.env
            
            # Pull latest images from Docker Hub
            docker compose -f compose/docker-compose.yml pull
            
            # Deploy with zero-downtime
            docker compose -f compose/docker-compose.yml up -d --remove-orphans
            
            # Wait for services to initialize
            sleep 15
            
            # Validate health
            bash scripts/validate-tracing.sh || {
              echo "Health check failed, streaming logs..."
              docker compose -f compose/docker-compose.yml logs --tail=50
              exit 1
            }
          EOF

      - name: Cleanup on failure
        if: failure()
        run: |
          ssh -i ~/.ssh/deploy_key root@45.55.173.72 << 'EOF'
            cd /opt/Dev-Tools
            docker compose -f compose/docker-compose.yml down --remove-orphans
            docker system prune -f
          EOF
```

### 2. Update docker-compose.yml for Docker Hub

```yaml
# ...existing code...

services:
  gateway-mcp:
    image: ${DOCKER_USERNAME:-yourusername}/dev-tools-gateway:${IMAGE_TAG:-latest}
    build:
      context: ..
      dockerfile: containers/gateway-mcp/Dockerfile
    # ...existing config...

  orchestrator:
    image: ${DOCKER_USERNAME:-yourusername}/dev-tools-orchestrator:${IMAGE_TAG:-latest}
    build:
      context: ..
      dockerfile: containers/orchestrator/Dockerfile
    # ...existing config...

  feature-dev:
    image: ${DOCKER_USERNAME:-yourusername}/dev-tools-feature-dev:${IMAGE_TAG:-latest}
    build:
      context: ..
      dockerfile: containers/feature-dev/Dockerfile
    # ...existing config...

  code-review:
    image: ${DOCKER_USERNAME:-yourusername}/dev-tools-code-review:${IMAGE_TAG:-latest}
    build:
      context: ..
      dockerfile: containers/code-review/Dockerfile
    # ...existing config...

  infrastructure:
    image: ${DOCKER_USERNAME:-yourusername}/dev-tools-infrastructure:${IMAGE_TAG:-latest}
    build:
      context: ..
      dockerfile: containers/infrastructure/Dockerfile
    # ...existing config...

  cicd:
    image: ${DOCKER_USERNAME:-yourusername}/dev-tools-cicd:${IMAGE_TAG:-latest}
    build:
      context: ..
      dockerfile: containers/cicd/Dockerfile
    # ...existing config...

  documentation:
    image: ${DOCKER_USERNAME:-yourusername}/dev-tools-documentation:${IMAGE_TAG:-latest}
    build:
      context: ..
      dockerfile: containers/documentation/Dockerfile
    # ...existing config...

  # Storage layer (droplet-hosted)
  postgres:
    image: postgres:15-alpine
    volumes:
      - postgres-data:/var/lib/postgresql/data
    # ...existing config...

  qdrant:
    image: qdrant/qdrant:latest
    volumes:
      - qdrant-data:/qdrant/storage
    # ...existing config...

volumes:
  postgres-data:
  qdrant-data:
  orchestrator-data:
  mcp-config:
# ...existing code...
```

### 3. Update push-docr.ps1 → push-dockerhub.ps1

```powershell
<#
.SYNOPSIS
    Build and push Dev-Tools images to Docker Hub
.PARAMETER Services
    Comma-separated service names to build/push (default: all)
.PARAMETER ImageTag
    Tag for images (default: git SHA)
.PARAMETER CleanupOnFailure
    Prune layers if build/push fails (default: $true in CI)
#>
param(
    [string]$Services = "all",
    [string]$ImageTag = "",
    [bool]$CleanupOnFailure = $true
)

$ErrorActionPreference = "Stop"

# Resolve image tag
if (-not $ImageTag) {
    $ImageTag = (git rev-parse --short HEAD).Trim()
}

$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
Write-Host "[$timestamp] Starting Docker Hub push: tag=$ImageTag" -ForegroundColor Cyan

# Validate Docker Hub auth
try {
    $username = docker info --format '{{.Username}}'
    if (-not $username) {
        throw "Not logged into Docker Hub. Run: docker login"
    }
    Write-Host "✓ Docker Hub authenticated as: $username" -ForegroundColor Green
} catch {
    Write-Host "✗ Docker Hub auth failed: $_" -ForegroundColor Red
    exit 1
}

# Prepare environment
Push-Location (Join-Path $PSScriptRoot ".." "compose")
try {
    # Set env vars
    $env:IMAGE_TAG = $ImageTag
    $env:DOCKER_USERNAME = $username

    # Build and push
    Write-Host "`n[$timestamp] Building services..." -ForegroundColor Yellow
    if ($Services -eq "all") {
        docker compose build
    } else {
        docker compose build $Services.Split(",")
    }

    if ($LASTEXITCODE -ne 0) {
        throw "Build failed with exit code $LASTEXITCODE"
    }

    Write-Host "`n[$timestamp] Pushing to Docker Hub..." -ForegroundColor Yellow
    if ($Services -eq "all") {
        docker compose push
    } else {
        docker compose push $Services.Split(",")
    }

    if ($LASTEXITCODE -ne 0) {
        throw "Push failed with exit code $LASTEXITCODE"
    }

    # Emit metadata
    $reportsDir = Join-Path $PSScriptRoot ".." "reports"
    if (-not (Test-Path $reportsDir)) {
        New-Item -ItemType Directory -Path $reportsDir | Out-Null
    }

    $metadata = @{
        timestamp = $timestamp
        image_tag = $ImageTag
        username = $username
        services = if ($Services -eq "all") { "all" } else { $Services.Split(",") }
    } | ConvertTo-Json -Depth 3

    $metadata | Out-File (Join-Path $reportsDir "push-dockerhub-metadata.json") -Encoding UTF8

    Write-Host "`n✓ Push complete: $username/dev-tools-*:$ImageTag" -ForegroundColor Green

} catch {
    Write-Host "`n✗ Push failed: $_" -ForegroundColor Red

    if ($CleanupOnFailure) {
        Write-Host "Cleaning up partial layers..." -ForegroundColor Yellow
        docker builder prune -f
        docker image prune -f
    }

    exit 1
} finally {
    Pop-Location
    docker builder prune -f
}
```

### 4. Update deploy-to-droplet.ps1

```powershell
# ...existing code...

# Deploy sequence
try {
    Write-Host "`n[$(Get-Date -Format 'HH:mm:ss')] Pulling images from Docker Hub..." -ForegroundColor Yellow
    Invoke-SSHCommand "docker compose -f $composeFile pull" $sshSession

    # ...existing code (down, up, validate)...

} catch {
    Write-Host "`n✗ Deploy failed: $_" -ForegroundColor Red

    if ($CleanupOnFailure) {
        Write-Host "Tearing down and pruning..." -ForegroundColor Yellow
        Invoke-SSHCommand "docker compose -f $composeFile down --remove-orphans" $sshSession
        Invoke-SSHCommand "docker system prune -f" $sshSession
    }

    exit 1
}

# ...existing code...
```

### 5. Update .env

```ini
# ...existing code...

# Docker Hub Configuration
DOCKER_USERNAME=yourusername
IMAGE_TAG=latest

# Remove DOCR variables
# DOCR_REGISTRY, DOCR_PAT, DOCR_ID no longer needed

# ...existing code...
```

### 6. Required GitHub Secrets

Update your repo secrets to:

- `DOCKER_USERNAME` - Your Docker Hub username
- `DOCKER_HUB_TOKEN` - Personal Access Token from https://hub.docker.com/settings/security
- Remove: `DIGITALOCEAN_ACCESS_TOKEN` (no longer needed for registry)
- Keep: All other secrets (Langfuse, Gradient, Linear, SSH key, Qdrant)

---

## Benefits of This Approach

✅ **No registry limits** - Docker Hub free tier: unlimited public repos  
✅ **MECE compartments** - Containers (Docker Hub), Storage (Droplet), Observability (SaaS), Compute (Gradient AI)  
✅ **Easier debugging** - Pull any image version locally: `docker pull yourusername/dev-tools-orchestrator:abc123`  
✅ **Portable** - Entire stack can run on any Docker host (local, AWS, GCP, Azure)  
✅ **Cost efficient** - Droplet only pays for compute + storage, not registry bandwidth
