# Deployment Architecture - Dev-Tools v2.0

## Updated: November 15, 2025

## Architecture Overview

**Dev-Tools uses a HYBRID deployment model:**

```
┌─────────────────────────────────────────────────────────────────┐
│                     DigitalOcean Droplet                        │
│                      45.55.173.72                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐        │
│  │ Orchestrator │  │ Feature Dev  │  │ Code Review  │        │
│  │ Agent        │  │ Agent        │  │ Agent        │        │
│  │ :8001        │  │ :8002        │  │ :8003        │        │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘        │
│         │                 │                 │                  │
│  ┌──────┴─────────────────┴─────────────────┴─────┐           │
│  │     Infrastructure     │     CI/CD      │  Doc  │           │
│  │     Agent :8004        │  Agent :8005   │ :8006 │           │
│  └────────────────────────┴────────────────┴───────┘           │
│                           │                                     │
│         All agents connect to ↓                                │
│                                                                 │
│  ┌─────────────────────────────────────────────────┐           │
│  │         MCP Gateway (port 8000)                 │           │
│  │  - Docker MCP Toolkit (150+ tools)              │           │
│  │  - Linear integration                           │           │
│  │  - DigitalOcean API tools                       │           │
│  └─────────────────────────────────────────────────┘           │
│                                                                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐           │
│  │ RAG Context │  │   State     │  │ Prometheus  │           │
│  │    :8007    │  │ Persist     │  │    :9090    │           │
│  │             │  │    :8008    │  │             │           │
│  └─────────────┘  └─────────────┘  └─────────────┘           │
│                                                                 │
│  ┌─────────────┐  ┌─────────────┐                             │
│  │   Qdrant    │  │ PostgreSQL  │                             │
│  │    :6333    │  │    :5432    │                             │
│  └─────────────┘  └─────────────┘                             │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
                           │
                           │ All agents call external APIs:
                           ↓
        ┌──────────────────┬───────────────────┬─────────────────┐
        │                  │                   │                 │
   ┌────▼────┐      ┌──────▼──────┐     ┌──────▼──────┐  ┌─────▼─────┐
   │ Gradient│      │  Langfuse   │     │   Linear    │  │  Qdrant   │
   │   AI    │      │  Tracing    │     │    API      │  │   Cloud   │
   │Serverless│     │   (SaaS)    │     │   (SaaS)    │  │   (SaaS)  │
   └─────────┘      └─────────────┘     └─────────────┘  └───────────┘
```

## Components

### 1. Agent Services (FastAPI Containers)

**6 agents deployed as Docker containers on droplet:**

- **Orchestrator** (port 8001)

  - Routes tasks to appropriate agents
  - Manages workflow state
  - Model: llama-3.1-70b-instruct (complex reasoning)

- **Feature Development** (port 8002)

  - Implements new features
  - Code generation
  - Model: codellama-13b-instruct (code-specialized)

- **Code Review** (port 8003)

  - Reviews pull requests
  - Security analysis
  - Model: llama-3.1-70b-instruct (thorough analysis)

- **Infrastructure** (port 8004)

  - Docker, Kubernetes, Terraform
  - Model: llama-3.1-8b-instruct (efficient for structured tasks)

- **CI/CD** (port 8005)

  - Pipeline configuration
  - Model: llama-3.1-8b-instruct

- **Documentation** (port 8006)
  - Generate/update docs
  - Model: mistral-7b-instruct (fast, cost-effective)

**All agents:**

- Use `agents/_shared/gradient_client.py` for LLM inference
- Connect to MCP Gateway at `http://gateway-mcp:8000` (Docker network)
- Connect to RAG service at `http://rag-context:8007`
- Connect to State service at `http://state-persistence:8008`

### 2. Infrastructure Services (Docker Containers)

- **MCP Gateway** (port 8000)

  - Routes tool calls to 17 MCP servers (150+ tools)
  - Docker MCP Toolkit v0.27.0
  - Linear API integration

- **RAG Context Service** (port 8007)

  - Vector search against Qdrant Cloud
  - Embeddings generation

- **State Persistence** (port 8008)

  - Workflow state management
  - PostgreSQL-backed

- **Qdrant** (port 6333)

  - Local vector database (optional)
  - Main vector store is Qdrant Cloud

- **PostgreSQL** (port 5432)

  - Workflow state storage

- **Prometheus** (port 9090)
  - Metrics collection from all agents

### 3. External Services (SaaS)

- **DigitalOcean Gradient AI**

  - Serverless LLM inference
  - Models: llama-3.1-70b, codellama-13b, mistral-7b, etc.
  - Cost: $0.20-0.60/1M tokens (150x cheaper than GPT-4)

- **Langfuse** (https://us.cloud.langfuse.com)

  - Automatic LLM tracing
  - Token usage tracking
  - Cost analysis

- **Linear** (https://linear.app)

  - Issue tracking
  - Project management

- **Qdrant Cloud** (cluster: 83b61795-7dbd-4477-890e-edce352a00e2)
  - Production vector database
  - Document embeddings

## Configuration Flow

### Environment Variables (Single Source of Truth)

All configuration in `config/env/.env` on droplet:

```bash
# Gradient AI Serverless Inference
GRADIENT_MODEL_ACCESS_KEY=sk-do-hqyE...  # For LLM inference
GRADIENT_API_KEY=dop_v1_21565d5f...      # For DO API operations

# Langfuse Tracing
LANGFUSE_SECRET_KEY=sk-lf-51d46621...
LANGFUSE_PUBLIC_KEY=pk-lf-7029904c...
LANGFUSE_HOST=https://us.cloud.langfuse.com

# Linear Integration
LINEAR_API_KEY=lin_oauth_8f8990917b7e520efcd51f8ebe84055a251f53f8738bb526c8f2fac8ff0a1571

# Qdrant Cloud
QDRANT_URL=https://83b61795-7dbd-4477-890e-edce352a00e2.us-east4-0.gcp.cloud.qdrant.io:6333
QDRANT_API_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

# MCP Gateway URL (for agents)
MCP_GATEWAY_URL=http://gateway-mcp:8000

# Service URLs (Docker internal network)
RAG_SERVICE_URL=http://rag-context:8007
STATE_SERVICE_URL=http://state-persistence:8008
```

### Docker Compose Inheritance

All services in `compose/docker-compose.yml` inherit from `.env` file:

```yaml
services:
  orchestrator:
    env_file:
      - ../config/env/.env
    environment:
      - AGENT_NAME=orchestrator
      - GRADIENT_MODEL=llama-3.1-70b-instruct
      - MCP_GATEWAY_URL=http://gateway-mcp:8000
```

## Deployment Steps

### 1. Local Environment Setup

```powershell
# Copy and populate .env file
Copy-Item config/env/.env.template config/env/.env
# Edit .env and add all API keys

# Verify configuration
.\scripts\validate-env.ps1
```

### 2. Deploy to Droplet

**Option A: Full Automated Deploy**

```powershell
.\scripts\deploy.ps1 -Target remote
```

**Option B: Manual SSH Deploy**

```bash
# SSH to droplet
ssh root@45.55.173.72

# Navigate to project
cd /opt/Dev-Tools

# Pull latest changes
git pull origin main

# Rebuild and restart services
docker-compose -f compose/docker-compose.yml down
docker-compose -f compose/docker-compose.yml build
docker-compose -f compose/docker-compose.yml up -d

# Verify health
docker-compose ps
curl http://localhost:8000/health  # MCP Gateway
curl http://localhost:8001/health  # Orchestrator
```

### 3. Verify Deployment

**Check all services:**

```powershell
$services = @(
    @{Name="MCP Gateway"; Port=8000},
    @{Name="Orchestrator"; Port=8001},
    @{Name="Feature Dev"; Port=8002},
    @{Name="Code Review"; Port=8003},
    @{Name="Infrastructure"; Port=8004},
    @{Name="CI/CD"; Port=8005},
    @{Name="Documentation"; Port=8006},
    @{Name="RAG Context"; Port=8007},
    @{Name="State Persist"; Port=8008}
)

foreach ($svc in $services) {
    try {
        $response = Invoke-RestMethod "http://45.55.173.72:$($svc.Port)/health"
        Write-Host "✅ $($svc.Name): $($response.status)" -ForegroundColor Green
    } catch {
        Write-Host "❌ $($svc.Name): Offline" -ForegroundColor Red
    }
}
```

**Check Langfuse tracing:**

1. Go to https://us.cloud.langfuse.com
2. Look for traces from agents
3. Verify token counts and costs

**Check Linear integration:**

```powershell
curl http://45.55.173.72:8000/api/linear-issues
```

## Integration Testing

### Test Orchestrator → MCP Gateway

```powershell
$task = @{
    description = "List all Docker containers"
    project_context = @{}
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://45.55.173.72:8001/tasks" -Method POST -Body $task -ContentType "application/json"
```

### Test Agent → Gradient AI

```powershell
# Check agent health (includes Gradient connection status)
Invoke-RestMethod "http://45.55.173.72:8001/health"
```

Expected response:

```json
{
  "status": "healthy",
  "agent": "orchestrator",
  "gradient": {
    "enabled": true,
    "model": "llama-3.1-70b-instruct"
  },
  "mcp_gateway": "connected",
  "langfuse_tracing": "enabled"
}
```

## Troubleshooting

### Agent Can't Connect to MCP Gateway

**Symptom:** `health.mcp_gateway: "disconnected"`

**Fix:**

```bash
# Check gateway is running
docker ps | grep gateway-mcp

# Check Docker network
docker network inspect dev-tools_default

# Verify env var
docker exec orchestrator env | grep MCP_GATEWAY_URL
```

### Gradient API Errors

**Symptom:** `"Gradient client not initialized (missing API key)"`

**Fix:**

```bash
# Verify key in .env
grep GRADIENT_MODEL_ACCESS_KEY /opt/Dev-Tools/config/env/.env

# Restart agent
docker-compose restart orchestrator
```

### Langfuse Not Tracing

**Symptom:** No traces appear in Langfuse dashboard

**Fix:**

```bash
# Verify all three env vars are set
docker exec orchestrator env | grep LANGFUSE

# Check logs for tracing init
docker logs orchestrator | grep -i langfuse
```

### Linear Integration Fails

**Symptom:** `401 Unauthorized` from Linear API

**Fix:**

```bash
# Verify OAuth token
cat /opt/Dev-Tools/config/env/secrets/linear_oauth_token.txt

# Test token directly
curl -H "Authorization: Bearer lin_oauth_..." https://api.linear.app/graphql
```

## Cost Optimization

### Model Selection by Agent

| Agent          | Model         | Cost/1M Tokens | Reasoning                  |
| -------------- | ------------- | -------------- | -------------------------- |
| Orchestrator   | llama-3.1-70b | $0.60          | Complex routing decisions  |
| Code Review    | llama-3.1-70b | $0.60          | Thorough analysis required |
| Feature Dev    | codellama-13b | $0.30          | Code-specialized           |
| Infrastructure | llama-3.1-8b  | $0.20          | Structured tasks           |
| CI/CD          | llama-3.1-8b  | $0.20          | Template-based             |
| Documentation  | mistral-7b    | $0.15          | Fast, simple tasks         |

**Average cost: ~$0.35/1M tokens**

### Langfuse Cost Tracking

View costs in Langfuse dashboard:

1. Go to https://us.cloud.langfuse.com
2. Click "Cost Insights"
3. Group by `langfuse_user_id` (agent name)
4. View per-agent spending

## Security

### Secrets Management

- **Never commit `.env` file to git** (in `.gitignore`)
- Docker secrets for OAuth tokens: `config/env/secrets/*.txt`
- Environment variables mounted at runtime
- Rotate keys quarterly

### API Key Hierarchy

```
GRADIENT_MODEL_ACCESS_KEY  → LLM inference (agents)
GRADIENT_API_KEY           → DO API operations (scripts)
LINEAR_API_KEY             → Linear OAuth token (agents + gateway)
LANGFUSE_SECRET_KEY        → Langfuse tracing (agents)
```

## Next Steps

1. ✅ Deploy all 6 agents to droplet
2. ✅ Verify MCP Gateway connection
3. ✅ Confirm Langfuse tracing
4. ✅ Test Linear integration
5. ⏳ Create frontend UI for task submission
6. ⏳ Set up monitoring alerts (Prometheus + Grafana)
7. ⏳ Implement agent-to-agent routing (multi-agent workflows)

## References

- [Gradient AI Serverless Inference](https://docs.digitalocean.com/products/gradient-ai-platform/how-to/use-serverless-inference/)
- [Docker MCP Toolkit](https://github.com/modelcontextprotocol/servers/tree/main/src/docker)
- [Langfuse Tracing](https://langfuse.com/docs/integrations/openai)
- [Linear API](https://developers.linear.app/docs/graphql/working-with-the-graphql-api)
