# Docker Hub Deployment Guide

Complete guide for deploying Dev-Tools using Docker Hub as the container registry.

## Overview

v2.0 architecture uses Docker Hub for container distribution with MECE compartmentalization:

- **Containers/Orchestration**: Docker Hub (unlimited public repos)
- **Storage/State**: DigitalOcean Droplet (Qdrant, PostgreSQL)
- **Observability**: Langfuse (SaaS) + Prometheus (optional)
- **LLM Inference**: DigitalOcean Gradient AI (serverless)

---

## Prerequisites

### System Requirements

- Docker Engine 24.0+
- Docker Compose 2.20+
- 4GB RAM (8GB recommended)
- 10GB disk space
- Git configured with SSH or PAT

### Docker Hub Account

1. Create account at https://hub.docker.com
2. Generate Personal Access Token:
   - Settings → Security → New Access Token
   - Permissions: Read, Write, Delete
3. Login locally:
   ```bash
   docker login
   ```

### Required Secrets

Create these GitHub repository secrets (Settings → Secrets → Actions):

- `DOCKER_USERNAME` - Your Docker Hub username
- `DOCKER_HUB_TOKEN` - Personal Access Token from Docker Hub
- `DROPLET_SSH_KEY` - SSH private key for droplet access
- `LANGFUSE_SECRET_KEY` - From https://cloud.langfuse.com
- `LANGFUSE_PUBLIC_KEY` - From https://cloud.langfuse.com
- `GRADIENT_API_KEY` - DigitalOcean Personal Access Token
- `LINEAR_OAUTH_DEV_TOKEN` - (Optional) Linear API token
- `QDRANT_API_KEY` - (Optional) Qdrant Cloud API key
- `QDRANT_URL` - (Optional) Qdrant cluster URL
- `DB_PASSWORD` - PostgreSQL password

---

## Configuration

### 1. Environment Setup

Copy template and configure:

```bash
cp config/env/.env.template config/env/.env
```

Edit `config/env/.env` and set:

```ini
# Docker Hub
DOCKER_USERNAME=yourusername
IMAGE_TAG=latest

# Langfuse (Required)
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_HOST=https://us.cloud.langfuse.com

# Gradient AI (Required)
GRADIENT_API_KEY=dop_v1_...
GRADIENT_BASE_URL=https://api.digitalocean.com/v2/ai

# Linear (Optional)
LINEAR_OAUTH_DEV_TOKEN=lin_api_...

# Qdrant (Optional for RAG)
QDRANT_URL=https://your-cluster.gcp.cloud.qdrant.io
QDRANT_API_KEY=...

# Database
DB_PASSWORD=secure-password-here
```

### 2. Secrets Setup (for Linear)

```bash
./scripts/setup_secrets.sh
```

Or manually create:

- `config/env/secrets/linear_oauth_token.txt`
- `config/env/secrets/linear_webhook_secret.txt`

---

## Local Development

### Build and Push

```powershell
# Build all services and push to Docker Hub
./scripts/push-dockerhub.ps1

# Build specific services
./scripts/push-dockerhub.ps1 -Services "orchestrator,feature-dev"

# Tag with version
./scripts/push-dockerhub.ps1 -ImageTag "v1.2.3"
```

### Run Locally

```bash
cd compose
docker compose pull  # Pull from Docker Hub
docker compose up -d
```

Verify:

```bash
docker compose ps
curl http://localhost:8000/health
```

---

## Remote Deployment (DigitalOcean)

### Droplet Setup

1. **Provision Droplet**

   - Ubuntu 24.04 LTS
   - 4GB RAM minimum (8GB recommended)
   - Attach SSH key

2. **Install Docker**

   ```bash
   ssh root@45.55.173.72
   curl -fsSL https://get.docker.com | sh
   systemctl enable docker
   systemctl start docker
   ```

3. **Clone Repository**

   ```bash
   mkdir -p /opt
   cd /opt
   git clone https://github.com/Appsmithery/Dev-Tools.git
   cd Dev-Tools
   ```

4. **Configure Environment**
   ```bash
   cp config/env/.env.template config/env/.env
   # Edit config/env/.env with production values
   ```

### Manual Deploy

```powershell
# Deploy from local machine
./scripts/deploy.ps1 -Target remote
```

This will:

1. Sync local `.env` and secrets to droplet
2. Configure git credentials (if GitHub PAT available)
3. Pull latest code
4. Pull images from Docker Hub
5. Deploy with `docker compose up -d`
6. Validate health checks

### CI/CD Deploy (GitHub Actions)

Push to `main` or `develop` triggers:

1. Build all service images
2. Push to Docker Hub with git SHA tag
3. SSH to droplet
4. Pull images and restart services
5. Run health checks

View workflow: `.github/workflows/docker-hub-deploy.yml`

---

## Service Ports

| Service           | Port   | Description                    |
| ----------------- | ------ | ------------------------------ |
| gateway-mcp       | 8000   | MCP tool router + Linear OAuth |
| orchestrator      | 8001   | Task decomposition             |
| feature-dev       | 8002   | Code generation                |
| code-review       | 8003   | PR analysis                    |
| infrastructure    | 8004   | Docker/K8s/Terraform           |
| cicd              | 8005   | Pipeline config                |
| documentation     | 8006   | Docs generation                |
| rag-context       | 8007   | Vector search                  |
| state-persistence | 8008   | Workflow state                 |
| langgraph         | 8009   | Workflow orchestration         |
| prometheus        | 9090   | Metrics                        |
| caddy             | 80/443 | Reverse proxy                  |

---

## Health Checks

### All Services

```bash
# Linux/Mac
for port in {8000..8008}; do
  curl -f http://localhost:$port/health || echo "Port $port DOWN"
done

# Windows
8000..8008 | ForEach-Object {
  Invoke-RestMethod "http://localhost:$_/health"
}
```

### Individual Service

```bash
curl http://localhost:8001/health
```

Expected response:

```json
{
  "status": "healthy",
  "agent_name": "orchestrator",
  "mcp_gateway": "connected",
  "timestamp": "2025-11-17T12:34:56Z"
}
```

---

## Troubleshooting

### Container Won't Start

```bash
# Check logs
docker compose logs <service-name>

# Recent logs
docker compose logs --tail=100 <service-name>

# Follow logs
docker compose logs -f <service-name>
```

### Image Pull Failures

```bash
# Verify Docker Hub auth
docker login

# Check image exists
docker pull yourusername/dev-tools-orchestrator:latest

# Force pull
docker compose pull --ignore-pull-failures
```

### Environment Variables Missing

```bash
# Validate .env file
grep -v "^#" config/env/.env | grep "="

# Recreate from template
cp config/env/.env.template config/env/.env
# Fill in values
```

### MCP Gateway Not Connected

Check agent logs for MCP connectivity:

```bash
docker compose logs orchestrator | grep -i mcp
```

Ensure `MCP_GATEWAY_URL=http://gateway-mcp:8000` is set.

### Langfuse Tracing Not Working

Verify keys in `.env`:

```bash
grep LANGFUSE_ config/env/.env
```

Check traces at https://us.cloud.langfuse.com

---

## Maintenance

### Update Services

```bash
# Pull latest images
docker compose pull

# Restart with new images
docker compose up -d

# Remove orphaned containers
docker compose down --remove-orphans
```

### Backup Volumes

```bash
./scripts/backup_volumes.sh
```

Creates tarballs in `./backups/`:

- `orchestrator-data`
- `mcp-config`
- `postgres-data`
- `qdrant-data`

### Restore Volumes

```bash
./scripts/restore_volumes.sh <timestamp>
```

### Clean Up

```bash
# Stop all services
docker compose down

# Remove volumes (⚠️ deletes data)
docker compose down -v

# Prune unused resources
docker system prune -f
docker builder prune -f
```

---

## Cost Optimization

### Docker Hub Free Tier

- Unlimited public repositories
- Unlimited pulls
- 200 container pushes/month (team size \* 200)
- No bandwidth charges

vs. DOCR:

- $20/month for 500GB storage
- $0.02/GB outbound transfer
- ~$50-100/month for active development

### DigitalOcean Gradient AI

- Llama 3.1 70B: $0.60/1M tokens
- Llama 3.1 8B: $0.20/1M tokens
- CodeLlama 13B: $0.40/1M tokens
- Mistral 7B: $0.30/1M tokens

Typical usage: <$10/month for development workloads

### Droplet Costs

- 4GB RAM: $24/month
- 8GB RAM: $48/month
- Block storage: +$10/100GB

**Total monthly cost**: ~$35-60 (vs. $100-150 with DOCR + GPT-4)

---

## Next Steps

- **Local Development**: See `docs/SETUP_GUIDE.md`
- **Agent Configuration**: See `docs/CONFIGURE_AGENTS_UI.md`
- **Observability**: See `docs/LANGFUSE_TRACING.md`
- **Secrets Management**: See `docs/SECRETS_MANAGEMENT.md`
