# DigitalOcean Quick Deploy Guide

**Target Droplet**: `mcp-gateway` (45.55.173.72)  
**Specs**: 2 GB RAM / 50 GB Disk / Ubuntu 22.04 LTS x64  
**Location**: NYC3  
**Estimated Time**: 30-45 minutes

---

## Phase 1: Deploy Core Services (Required)

### Step 1: Verify Droplet Prerequisites

SSH into your droplet:

```bash
ssh root@45.55.173.72
```

Check Docker installation:

```bash
docker --version
docker-compose --version
```

**If Docker not installed**, run:

```bash
# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Verify
docker-compose --version
```

Check available resources:

```bash
free -h        # Should show ~2GB RAM
df -h          # Should show ~50GB disk
```

---

### Step 2: Clone Repository

```bash
# Create working directory
mkdir -p /opt/dev-tools
cd /opt/dev-tools

# Clone your repo
git clone https://github.com/Appsmithery/Dev-Tools.git
cd Dev-Tools

# Checkout your current branch
git checkout feature/phase1-low-inference
```

---

### Step 3: Configure Environment Variables

Create production environment file:

```bash
cd config/env
cp .env.example .env
nano .env
```

**Update these values**:

```bash
# Core Services
NODE_ENV=production
SERVICE_NAME=gateway-mcp

# API Endpoints (use private IP for internal communication)
FEATURE_DEV_URL=http://10.108.0.2:8002
CODE_REVIEW_URL=http://10.108.0.2:8003
INFRASTRUCTURE_URL=http://10.108.0.2:8004
CICD_URL=http://10.108.0.2:8005
DOCUMENTATION_URL=http://10.108.0.2:8006
RAG_SERVICE_URL=http://10.108.0.2:8007
STATE_SERVICE_URL=http://10.108.0.2:8008

# Database
POSTGRES_PASSWORD=<generate-strong-password>
POSTGRES_DB=devtools_state
POSTGRES_USER=devtools

# Qdrant
QDRANT_HOST=qdrant
QDRANT_PORT=6333

# Optional: Add your GitHub secrets if needed
# SUPABASE_TOKEN=<from-github-secrets>
# VERCEL_TOKEN=<from-github-secrets>
```

**Generate strong password**:

```bash
openssl rand -base64 32
```

---

### Step 4: Configure Firewall

```bash
# Install UFW if not present
apt-get update
apt-get install -y ufw

# Allow SSH (CRITICAL - do this first!)
ufw allow 22/tcp

# Allow agent services
ufw allow 8000:8008/tcp

# Allow Qdrant
ufw allow 6333:6334/tcp

# Allow PostgreSQL (only if you need external access)
# ufw allow 5432/tcp

# Enable firewall
ufw --force enable

# Check status
ufw status verbose
```

---

### Step 5: Optimize for 2GB RAM

Your droplet has limited RAM. Update docker-compose to set memory limits:

```bash
cd /opt/dev-tools/Dev-Tools/compose
nano docker-compose.yml
```

Add to each service (example for orchestrator):

```yaml
orchestrator:
  # ... existing config ...
  deploy:
    resources:
      limits:
        memory: 256M
      reservations:
        memory: 128M
```

**Recommended memory allocation** (total ~1.8GB, leaving 200MB for system):

- gateway-mcp: 200M
- orchestrator: 256M
- feature-dev: 256M
- code-review: 128M
- infrastructure: 128M
- cicd: 128M
- documentation: 128M
- rag-context: 256M
- state-persistence: 128M
- qdrant: 256M
- postgres: 200M

---

### Step 6: Deploy Services

```bash
cd /opt/dev-tools/Dev-Tools/compose

# Build all images
docker-compose build

# Start services
docker-compose up -d

# Monitor startup
docker-compose logs -f
```

Wait 1-2 minutes for all services to initialize.

---

### Step 7: Verify Deployment

Check all services are running:

```bash
docker-compose ps
```

**All services should show "Up"**.

Test health endpoints:

```bash
# From the droplet
curl http://localhost:8000/health  # MCP Gateway
curl http://localhost:8001/health  # Orchestrator
curl http://localhost:8002/health  # Feature-Dev
curl http://localhost:8003/health  # Code-Review
curl http://localhost:8007/health  # RAG Context
curl http://localhost:8008/health  # State Persistence

# Test from your local machine
curl http://45.55.173.72:8000/health
curl http://45.55.173.72:8001/health
```

**Expected response**:

```json
{
  "status": "ok",
  "service": "orchestrator",
  "timestamp": "2025-11-13T...",
  "version": "1.0.0"
}
```

---

### Step 8: Test End-to-End Workflow

From your local machine:

```powershell
# Create a task
$body = @{
    description = 'Create user authentication module'
    priority = 'high'
} | ConvertTo-Json

$task = Invoke-RestMethod -Uri http://45.55.173.72:8001/orchestrate -Method Post -ContentType 'application/json' -Body $body

# Execute workflow
$result = Invoke-RestMethod -Uri "http://45.55.173.72:8001/execute/$($task.task_id)" -Method Post

# Check result
$result | ConvertTo-Json -Depth 5
```

**Success indicators**:

- `status: "completed"`
- Both feature-dev and code-review subtasks completed
- No error messages

---

### Step 9: Initialize Database Schema

```bash
# Initialize PostgreSQL schema
curl -X POST http://localhost:8008/init

# Verify
curl http://localhost:8008/health
```

---

### Step 10: Set Up Auto-Restart on Boot

```bash
# Create systemd service
cat > /etc/systemd/system/dev-tools.service <<EOF
[Unit]
Description=Dev-Tools Docker Compose Stack
After=docker.service
Requires=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/opt/dev-tools/Dev-Tools/compose
ExecStart=/usr/local/bin/docker-compose up -d
ExecStop=/usr/local/bin/docker-compose down
TimeoutStartSec=0

[Install]
WantedBy=multi-user.target
EOF

# Enable service
systemctl daemon-reload
systemctl enable dev-tools.service

# Test (optional - this will restart services)
# systemctl restart dev-tools.service
```

---

## Phase 2: Gradient Platform Integration (Optional)

### Prerequisites

- DigitalOcean Gradient workspace created
- Function routes configured to point to `45.55.173.72`

### Step 1: Create Gradient Workspace

Via DigitalOcean console or API:

```bash
# Install doctl CLI
snap install doctl

# Authenticate
doctl auth init

# Create Gradient workspace (when available)
# doctl gradient workspace create dev-tools-prod
```

### Step 2: Build Knowledge Base

1. Go to DigitalOcean Gradient Platform
2. Create new knowledge base: "Dev-Tools Documentation"
3. Add data source: GitHub repository
   - Repository: `Appsmithery/Dev-Tools`
   - Branch: `feature/phase1-low-inference`
   - Path: `docs/`
4. Enable auto-indexing
5. Wait for initial index (5-10 minutes)

### Step 2b: Sync KB Exports into Qdrant Cloud

Once Gradient finishes an indexing job, mirror the vectors into your managed Qdrant cluster so on-prem agents can query locally:

1. Populate the new env variables in `config/env/.env`:

```dotenv
QDRANT_URL=https://<cluster-id>.gcp.cloud.qdrant.io
QDRANT_API_KEY=<qdrant-api-key>
QDRANT_COLLECTION=the-shop
QDRANT_VECTOR_SIZE=1536

DIGITALOCEAN_KB_UUID=3120c1c2-c1c0-11f0-b074-4e013e2ddde4
DIGITALOCEAN_KB_REF=the-shop
DIGITALOCEAN_KB_DOWNLOAD_DIR=./tmp/kb-sync
```

2. Run the sync tool from the repo root whenever you need a fresh export:

```bash
python3 scripts/sync_kb_to_qdrant.py --start-job --poll-interval 60 --batch-size 128
```

- Omit `--start-job` if you only want to ingest the latest completed job.
- Add `--dry-run` to validate parsing without writing to Qdrant.
- Raw exports land under `tmp/kb-sync/<job>.json` for auditing.

3. Confirm vectors exist:

```bash
curl http://localhost:8007/collections | jq
```

The `the-shop` collection should show a non-zero `count` and the RAG service will automatically serve queries from Qdrant Cloud.

### Step 3: Configure Function Routes

Create function route configuration:

```json
{
  "routes": [
    {
      "name": "feature-dev",
      "url": "http://45.55.173.72:8002/implement",
      "method": "POST",
      "description": "Custom code generation agent"
    },
    {
      "name": "infrastructure",
      "url": "http://45.55.173.72:8004/generate",
      "method": "POST",
      "description": "Infrastructure as code generation"
    },
    {
      "name": "cicd",
      "url": "http://45.55.173.72:8005/configure",
      "method": "POST",
      "description": "CI/CD pipeline configuration"
    }
  ]
}
```

### Step 4: Create Parent Orchestrator Agent

In Gradient Platform:

1. Create new agent: "Dev-Tools Orchestrator"
2. Attach knowledge base
3. Add function routes from Step 3
4. Configure routing logic:
   - Documentation queries → Gradient knowledge base
   - Code review → Gradient serverless inference
   - Custom tasks → Function routes to your droplet

### Step 5: Test Hybrid Workflow

```bash
# Test Gradient agent calling your droplet
curl -X POST https://api.gradient.digitalocean.com/v1/agents/<agent-id>/invoke \
  -H "Authorization: Bearer $DO_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Implement user login feature",
    "context": {
      "project": "dev-tools"
    }
  }'
```

---

## Monitoring & Maintenance

### View Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f orchestrator

# Last 100 lines
docker-compose logs --tail=100
```

### Check Resource Usage

```bash
# Container stats
docker stats

# Disk usage
docker system df

# Clean up unused images
docker system prune -a
```

### Update Deployment

```bash
cd /opt/dev-tools/Dev-Tools
git pull origin feature/phase1-low-inference
cd compose
docker-compose build
docker-compose up -d
```

### Backup Data

```bash
# Create backup directory
mkdir -p /opt/backups

# Backup PostgreSQL
docker exec compose-postgres-1 pg_dump -U devtools devtools_state > /opt/backups/postgres_$(date +%Y%m%d).sql

# Backup Qdrant data
docker run --rm -v compose_qdrant-data:/data -v /opt/backups:/backup alpine tar czf /backup/qdrant_$(date +%Y%m%d).tar.gz -C /data .

# Backup volumes (script already exists)
cd /opt/dev-tools/Dev-Tools
./scripts/backup_volumes.sh
```

---

## Troubleshooting

### Services Won't Start

```bash
# Check logs
docker-compose logs

# Check available memory
free -h

# If out of memory, restart with fewer services
docker-compose up -d orchestrator feature-dev code-review rag-context state-persistence postgres qdrant
```

### Can't Connect from External

```bash
# Check firewall
ufw status

# Check service is listening
netstat -tlnp | grep 8001

# Check docker network
docker network inspect devtools-network
```

### Database Connection Errors

```bash
# Check PostgreSQL is running
docker-compose ps postgres

# Check connection
docker exec -it compose-postgres-1 psql -U devtools -d devtools_state -c "SELECT 1;"

# Re-initialize schema if needed
curl -X POST http://localhost:8008/init
```

### Memory Issues

```bash
# Check current usage
docker stats --no-stream

# Restart high-memory services
docker-compose restart orchestrator feature-dev rag-context

# If persistent, consider upgrading droplet to 4GB
```

---

## Security Hardening (Recommended)

### 1. Enable HTTPS with Let's Encrypt

```bash
# Install certbot
apt-get install -y certbot

# Get certificate (requires domain name)
certbot certonly --standalone -d your-domain.com

# Configure nginx reverse proxy (optional)
apt-get install -y nginx

# Nginx config for SSL termination
cat > /etc/nginx/sites-available/dev-tools <<EOF
server {
    listen 443 ssl;
    server_name your-domain.com;

    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;

    location / {
        proxy_pass http://localhost:8001;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
    }
}
EOF

ln -s /etc/nginx/sites-available/dev-tools /etc/nginx/sites-enabled/
nginx -t && systemctl restart nginx
```

### 2. Add API Authentication

Add to docker-compose environment:

```yaml
orchestrator:
  environment:
    - API_KEY=${API_KEY}
```

Generate API key:

```bash
export API_KEY=$(openssl rand -hex 32)
echo "API_KEY=$API_KEY" >> config/env/.env
```

### 3. Restrict Database Access

Ensure PostgreSQL is only accessible internally:

```bash
# Remove external firewall rule if you added it
ufw delete allow 5432/tcp
```

---

## Performance Optimization

### Add Swap Space (Helps with 2GB RAM)

```bash
# Create 2GB swap
fallocate -l 2G /swapfile
chmod 600 /swapfile
mkswap /swapfile
swapon /swapfile

# Make permanent
echo '/swapfile none swap sw 0 0' >> /etc/fstab
```

### Enable Docker BuildKit Cache

```bash
export DOCKER_BUILDKIT=1
export COMPOSE_DOCKER_CLI_BUILD=1

# Add to /etc/environment for persistence
echo "DOCKER_BUILDKIT=1" >> /etc/environment
```

---

## Next Steps

1. **Monitor for 24-48 hours**

   - Check logs for errors
   - Monitor memory usage
   - Verify workflows complete successfully

2. **Consider upgrading** if needed

   - 4GB RAM droplet ($24/month) for more headroom
   - Add monitoring (Prometheus + Grafana)

3. **Integrate Gradient Platform** when ready

   - Offload inference to Gradient
   - Reduce local compute needs
   - Use knowledge bases for documentation

4. **Add domain + HTTPS** for production use
   - Point domain to 45.55.173.72
   - Configure Let's Encrypt
   - Update CORS settings

---

## Quick Reference

**Droplet Access**:

```bash
ssh root@45.55.173.72
```

**Service URLs**:

- Orchestrator: http://45.55.173.72:8001
- Feature-Dev: http://45.55.173.72:8002
- Code-Review: http://45.55.173.72:8003
- RAG Context: http://45.55.173.72:8007
- State: http://45.55.173.72:8008

**Essential Commands**:

```bash
# View all services
docker-compose ps

# Restart all
docker-compose restart

# Stop all
docker-compose down

# View logs
docker-compose logs -f

# Update code
cd /opt/dev-tools/Dev-Tools && git pull && cd compose && docker-compose up -d --build
```

---

**Estimated Costs**:

- Current droplet: $12/month (2GB)
- Upgraded droplet: $24/month (4GB) - recommended
- Gradient Platform: ~$50-100/month (usage-based)
- **Total**: $36-124/month depending on configuration

**Support**:

- Repository: https://github.com/Appsmithery/Dev-Tools
- Issues: https://github.com/Appsmithery/Dev-Tools/issues
