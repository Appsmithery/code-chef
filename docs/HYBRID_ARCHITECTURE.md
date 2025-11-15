# Hybrid Architecture: Gradient AI + Docker

## Overview

Dev-Tools uses a **hybrid deployment architecture** that combines:

1. **Gradient AI Managed Agents** - AI agents run as managed services in DigitalOcean's Gradient AI platform
2. **Docker Infrastructure** - Supporting services (gateway, databases, RAG) run in Docker containers on a droplet

This architecture provides:

- ✅ Auto-scaling and managed AI inference (Gradient AI handles LLM compute)
- ✅ Cost optimization (pay-per-use for agents, fixed cost for infrastructure)
- ✅ Simplified operations (no need to manage agent containers/scaling)
- ✅ Full observability (Langfuse tracing + Prometheus metrics)

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                   DigitalOcean Gradient AI                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │ Orchestrator │  │ Feature Dev  │  │ Code Review  │         │
│  │    Agent     │  │    Agent     │  │    Agent     │         │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘         │
│         │                  │                  │                  │
│  ┌──────┴───────┐  ┌──────┴───────┐  ┌──────┴───────┐         │
│  │Infrastructure│  │    CI/CD     │  │Documentation │         │
│  │    Agent     │  │    Agent     │  │    Agent     │         │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘         │
│         │                  │                  │                  │
│         └──────────────────┼──────────────────┘                 │
│                            │                                     │
└────────────────────────────┼─────────────────────────────────────┘
                             │ HTTP/REST
                             ▼
                  ┌────────────────────┐
                  │   MCP Gateway      │
                  │  (Port 8000)       │
                  └─────────┬──────────┘
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
        ▼                   ▼                   ▼
┌────────────┐    ┌──────────────┐    ┌────────────┐
│ RAG Context│    │    State     │    │  Databases │
│ (Port 8007)│    │ Persistence  │    │  - Qdrant  │
└────────────┘    │ (Port 8008)  │    │  - Postgres│
                  └──────────────┘    └────────────┘

                  All running on Droplet: 45.55.173.72
```

## Components

### Gradient AI Managed Agents

**Location:** `.agents.do-ai.run` (managed by DigitalOcean)

| Agent                 | Purpose                          | Model                  | Endpoint                                           |
| --------------------- | -------------------------------- | ---------------------- | -------------------------------------------------- |
| DevTools Orchestrator | Task coordination, planning      | llama-3.1-70b-instruct | https://zqavbvjov22wijsmbqtkqy4r.agents.do-ai.run  |
| Feature Development   | Code generation, implementation  | codellama-13b-instruct | https://mdu2tzvveslhs6spm36znwul.agents.do-ai.run  |
| Code Review           | Quality analysis, suggestions    | llama-3.1-70b-instruct | https://miml4tgrdvjufzudn5udh2sp.agents.do-ai.run  |
| Infrastructure        | Terraform, Kubernetes, cloud ops | llama-3.1-8b-instruct  | https://r2eqzfrjao62mdzdbtolmq3sa.agents.do-ai.run |
| CI/CD                 | Pipeline generation, automation  | llama-3.1-8b-instruct  | https://dxoc7qrjjgbvj7ybct7nogbp.agents.do-ai.run  |
| Documentation         | Docs generation, wikis           | mistral-7b-instruct    | https://tzyvehgqf3pgl4z46rrzbbs.agents.do-ai.run   |

**Key Features:**

- Managed scaling (DigitalOcean handles replicas)
- Built-in LLM inference (no need to manage model endpoints)
- Automatic health checks and restarts
- Per-request billing (no idle costs)

### Docker Infrastructure (Droplet)

**Location:** Droplet `45.55.173.72`

| Service           | Purpose                                       | Port | Technology             |
| ----------------- | --------------------------------------------- | ---- | ---------------------- |
| MCP Gateway       | Tool orchestration, Linear/GitHub integration | 8000 | Node.js + FastAPI      |
| RAG Context       | Vector search, knowledge retrieval            | 8007 | Python + Qdrant client |
| State Persistence | Workflow state management                     | 8008 | Python + PostgreSQL    |
| Qdrant            | Vector database                               | 6333 | Qdrant                 |
| PostgreSQL        | Relational database                           | 5432 | PostgreSQL 16          |
| Prometheus        | Metrics collection                            | 9090 | Prometheus             |

## Deployment

### Quick Deploy

```powershell
# Deploy infrastructure to droplet
.\scripts\deploy-hybrid.ps1

# Or skip building images (faster)
.\scripts\deploy-hybrid.ps1 -SkipBuild
```

### Manual Steps

1. **Deploy Docker Infrastructure:**

   ```bash
   ssh root@45.55.173.72
   cd /opt/Dev-Tools
   git pull origin main

   # Start only infrastructure services
   docker compose -f compose/docker-compose.yml up -d \
     gateway-mcp \
     rag-context \
     state-persistence \
     qdrant \
     postgres \
     prometheus
   ```

2. **Verify Gateway:**

   ```bash
   curl http://45.55.173.72:8000/health
   ```

3. **Configure Gradient AI Agents:**

   - Each agent should have `MCP_GATEWAY_URL=http://45.55.173.72:8000` in their environment
   - This is configured through the DigitalOcean Gradient AI dashboard

4. **Test Agent Communication:**
   ```bash
   # Call an agent endpoint
   curl https://zqavbvjov22wijsmbqtkqy4r.agents.do-ai.run/health
   ```

## Environment Configuration

### Required Variables

Add these to `config/env/.env`:

```bash
# Gradient AI
GRADIENT_MODEL_ACCESS_KEY=sk-do-...
GRADIENT_API_KEY=dop_v1_...

# Observability
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_HOST=https://us.cloud.langfuse.com

# Databases
QDRANT_CLOUD_API_KEY=...
QDRANT_CLUSTER_ENDPOINT=https://....gcp.cloud.qdrant.io

# Integrations
DIGITAL_OCEAN_PAT=dop_v1_...
LINEAR_API_KEY=lin_oauth_...
```

## Monitoring

### Langfuse (LLM Tracing)

- **URL:** https://us.cloud.langfuse.com
- **Traces:** All agent LLM calls automatically traced
- **Grouping:** By `task_id` (session) and `agent_name` (user)

### Prometheus (Metrics)

- **URL:** http://45.55.173.72:9090
- **Metrics:** HTTP request rates, latencies, error rates
- **Targets:** Gateway, RAG, State services

### Health Checks

```bash
# Gateway
curl http://45.55.173.72:8000/health

# Agents (example)
curl https://zqavbvjov22wijsmbqtkqy4r.agents.do-ai.run/health

# Prometheus
curl http://45.55.173.72:9090/-/healthy
```

## Cost Optimization

### Gradient AI Agents (Pay-per-use)

- **No idle costs** - Only charged for actual inference requests
- **Auto-scaling** - DigitalOcean handles replicas based on load
- **Model pricing:**
  - llama-3.1-70b: ~$0.50/1M tokens
  - codellama-13b: ~$0.30/1M tokens
  - llama-3.1-8b: ~$0.20/1M tokens
  - mistral-7b: ~$0.20/1M tokens

### Droplet Infrastructure (Fixed)

- **Droplet:** $12-48/month (depends on size)
- **Managed Databases:** $15-60/month (optional, using Qdrant Cloud)
- **Total:** ~$30-100/month for infrastructure

**Comparison to Self-Hosted:**

- Self-hosting all 6 agents would require GPU instances: $500-2000/month
- Hybrid approach: **90% cost reduction** for typical usage

## Troubleshooting

### Agent Can't Connect to Gateway

1. **Check gateway is running:**

   ```bash
   ssh root@45.55.173.72 "docker ps | grep gateway"
   ```

2. **Verify firewall:**

   ```bash
   ssh root@45.55.173.72 "ufw status | grep 8000"
   ```

3. **Test from agent's perspective:**
   ```bash
   curl http://45.55.173.72:8000/health
   ```

### Gateway MCP Tools Not Available

1. **Check Docker MCP Toolkit:**

   ```bash
   ssh root@45.55.173.72 "docker mcp --version"
   ```

2. **Restart gateway:**
   ```bash
   ssh root@45.55.173.72 "cd /opt/Dev-Tools && docker compose -f compose/docker-compose.yml restart gateway-mcp"
   ```

### Database Connection Issues

1. **Check Qdrant:**

   ```bash
   curl http://45.55.173.72:6333/health
   ```

2. **Check PostgreSQL:**
   ```bash
   ssh root@45.55.173.72 "docker exec -it postgres psql -U admin -d devtools -c 'SELECT 1;'"
   ```

## Migration from Self-Hosted

If you're currently running all services in Docker:

1. **Export agent configurations:**

   ```bash
   docker inspect orchestrator > orchestrator-config.json
   # Repeat for each agent
   ```

2. **Create Gradient AI agents in DigitalOcean dashboard:**

   - Use exported environment variables
   - Set `MCP_GATEWAY_URL=http://45.55.173.72:8000`

3. **Stop Docker agent containers:**

   ```bash
   docker compose -f compose/docker-compose.yml stop orchestrator feature-dev code-review infrastructure cicd documentation
   ```

4. **Keep infrastructure running:**

   ```bash
   docker compose -f compose/docker-compose.yml up -d gateway-mcp rag-context state-persistence qdrant postgres
   ```

5. **Test agent endpoints:**
   ```bash
   curl https://YOUR-AGENT.agents.do-ai.run/health
   ```

## Best Practices

1. **Use environment-specific configs:**

   - Production: Gradient AI agents
   - Development: Local Docker (all services)
   - Staging: Hybrid (subset of agents in Gradient)

2. **Monitor costs:**

   - Check Gradient AI usage daily
   - Set budget alerts in DigitalOcean dashboard
   - Use Langfuse to track token consumption per agent

3. **Version control:**

   - Agent code in `agents/*/` directories
   - Infrastructure code in `containers/*/` directories
   - Use git tags for deployments

4. **Security:**
   - Rotate `GRADIENT_API_KEY` quarterly
   - Use Docker secrets for sensitive configs
   - Enable firewall rules (only ports 8000, 8007, 8008 exposed)

## Related Documentation

- [Gradient AI Quick Start](./GRADIENT_QUICK_START.md)
- [MCP Integration](./MCP_INTEGRATION.md)
- [Langfuse Tracing](./LANGFUSE_TRACING.md)
- [Deployment Guide](./DEPLOYMENT.md)
