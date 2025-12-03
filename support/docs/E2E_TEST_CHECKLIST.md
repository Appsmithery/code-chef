# End-to-End Testing Checklist

**Version**: 1.0  
**Date**: November 26, 2025  
**Purpose**: Validate all new functionality post-deployment

---

## Pre-Test Setup

### 1. Environment Verification

```powershell
# Check all services are healthy via HTTPS
curl https://codechef.appsmithery.co/api/health    # Orchestrator
curl https://codechef.appsmithery.co/rag/health    # RAG
curl https://codechef.appsmithery.co/state/health  # State

# Or via SSH for internal ports
ssh do-codechef-droplet "curl -s http://localhost:8001/health"  # Orchestrator
ssh do-codechef-droplet "curl -s http://localhost:8000/health"  # Gateway
ssh do-codechef-droplet "curl -s http://localhost:8007/health"  # RAG
ssh do-codechef-droplet "curl -s http://localhost:8008/health"  # State
```

### 2. Container Status

```powershell
ssh do-codechef-droplet "docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'"
```

Expected: 13 containers running

---

## Test Categories

## 1. RAG Semantic Search (DEV-184) ✅

### 1.1 Qdrant Cloud Connection

- [ ] **Health check shows qdrant_status: connected**
  ```bash
  curl https://codechef.appsmithery.co/rag/health | jq '.qdrant_status'
  # Expected: "connected"
  ```

### 1.2 Collection Verification

- [ ] **All 7 collections exist with correct counts**
  ```bash
  curl https://codechef.appsmithery.co/rag/collections | jq .
  # Expected counts:
  # - code_patterns: 505
  # - issue_tracker: 155
  # - feature_specs: 4
  # - the-shop: 460
  # - vendor-docs: 94
  # - task_context: 0
  # - agent_memory: 0
  ```

### 1.3 Semantic Search Queries

- [ ] **Query code_patterns**

  ```bash
  curl -X POST https://codechef.appsmithery.co/rag/query \
    -H "Content-Type: application/json" \
    -d '{"query": "workflow execution", "collection": "code_patterns", "limit": 3}'
  # Expected: 3 results with scores > 0.5
  ```

- [ ] **Query issue_tracker**

  ```bash
  curl -X POST https://codechef.appsmithery.co/rag/query \
    -H "Content-Type: application/json" \
    -d '{"query": "deployment automation", "collection": "issue_tracker", "limit": 3}'
  # Expected: Results with issue metadata
  ```

- [ ] **Query feature_specs**
  ```bash
  curl -X POST https://codechef.appsmithery.co/rag/query \
    -H "Content-Type: application/json" \
    -d '{"query": "AI DevOps agent platform", "collection": "feature_specs", "limit": 2}'
  # Expected: Project specifications returned
  ```

---

## 2. Memory Optimization

### 2.1 Swap Enabled

- [ ] **2GB swap active**
  ```bash
  ssh do-codechef-droplet "free -h | grep Swap"
  # Expected: Swap: 2.0Gi (some amount used)
  ```

### 2.2 Container Memory Limits

- [ ] **All containers within limits**
  ```bash
  ssh do-codechef-droplet "docker stats --no-stream --format 'table {{.Name}}\t{{.MemUsage}}'"
  # Expected: No container exceeding its limit
  # - gateway-mcp: < 256MB
  # - rag-context: < 512MB
  # - postgres: < 256MB
  # - redis: < 128MB
  ```

### 2.3 System Memory

- [ ] **Available memory > 500MB**
  ```bash
  ssh do-codechef-droplet "free -h"
  # Expected: available > 500Mi
  ```

---

## 3. Orchestrator & LangGraph

### 3.1 Health Endpoints

- [ ] **Orchestrator healthy**
  ```bash
  curl https://codechef.appsmithery.co/api/health
  # Expected: {"status":"ok","service":"orchestrator"}
  ```

### 3.2 Token Metrics

- [ ] **Token tracking endpoint accessible**
  ```bash
  curl https://codechef.appsmithery.co/api/metrics/tokens | jq '.totals'
  # Expected: JSON with total_tokens, total_cost, total_calls
  ```

### 3.3 Prometheus Metrics

- [ ] **Prometheus metrics exposed**
  ```bash
  ssh do-codechef-droplet "curl -s http://localhost:8001/metrics | grep llm_"
  # Expected: llm_tokens_total, llm_cost_usd_total metrics
  ```

---

## 4. MCP Gateway

### 4.1 Gateway Health

- [ ] **Gateway operational**
  ```bash
  ssh do-codechef-droplet "curl http://localhost:8000/health"
  # Expected: {"status":"ok","service":"mcp-gateway"}
  ```

### 4.2 Tool Discovery

- [ ] **Tools available**
  ```bash
  ssh do-codechef-droplet "curl http://localhost:8000/tools | jq '. | length'"
  # Expected: 150+ tools
  ```

---

## 5. Linear Integration

### 5.1 Linear API Connection

- [ ] **Verify Linear API key works**
  ```bash
  curl -X POST https://api.linear.app/graphql \
    -H "Authorization: lin_oauth_8f8990917b7e520efcd51f8ebe84055a251f53f8738bb526c8f2fac8ff0a1571" \
    -H "Content-Type: application/json" \
    -d '{"query": "{ viewer { id name } }"}'
  # Expected: User data returned
  ```

### 5.2 HITL Hub Active

- [ ] **DEV-68 exists and is In Progress**
  ```bash
  # Check via Linear UI or API
  # Expected: DEV-68 status = "In Progress"
  ```

---

## 6. Observability

### 6.1 LangSmith Tracing

- [ ] **LangSmith receiving traces**
  - Open: https://smith.langchain.com/o/5029c640-3f73-480c-82f3-58e402ed4207/projects/p/f967bb5e-2e61-434f-8ee1-0df8c22bc046
  - Expected: Recent traces visible (within last hour if agents active)

### 6.2 Grafana Cloud

- [ ] **Metrics visible in Grafana**
  - Open: https://appsmithery.grafana.net/explore
  - Query: `up{cluster="dev-tools"}`
  - Expected: 4+ services reporting

### 6.3 Prometheus Scraping

- [ ] **All services being scraped**
  ```bash
  ssh do-codechef-droplet "curl -s http://localhost:9090/api/v1/targets" | jq '.data.activeTargets | length'
  # Expected: 4+ active targets
  ```

---

## 7. State Persistence

### 7.1 PostgreSQL

- [ ] **Database accessible**
  ```bash
  ssh do-codechef-droplet "docker exec deploy-postgres-1 pg_isready"
  # Expected: accepting connections
  ```

### 7.2 Redis

- [ ] **Redis operational**
  ```bash
  ssh do-codechef-droplet "docker exec deploy-redis-1 redis-cli ping"
  # Expected: PONG
  ```

---

## 8. Workflow Engine (Zen Patterns)

### 8.1 TTL Configuration

- [ ] **WORKFLOW_TTL_HOURS set**
  ```bash
  ssh do-codechef-droplet "grep WORKFLOW_TTL_HOURS /opt/Dev-Tools/config/env/.env"
  # Expected: WORKFLOW_TTL_HOURS=24
  ```

### 8.2 Event Schema

- [ ] **workflow_events table exists (if deployed)**
  ```bash
  ssh do-codechef-droplet "docker exec deploy-postgres-1 psql -U devtools -c '\dt workflow_*'"
  # Expected: Tables listed (or error if not yet migrated)
  ```

---

## Test Execution Log

### Test Run: [DATE]

| Category      | Test                | Result | Notes |
| ------------- | ------------------- | ------ | ----- |
| RAG           | Health check        | ⬜     |       |
| RAG           | Collections exist   | ⬜     |       |
| RAG           | Query code_patterns | ⬜     |       |
| RAG           | Query issue_tracker | ⬜     |       |
| Memory        | Swap enabled        | ⬜     |       |
| Memory        | Container limits    | ⬜     |       |
| Orchestrator  | Health              | ⬜     |       |
| Orchestrator  | Token metrics       | ⬜     |       |
| Gateway       | Health              | ⬜     |       |
| Gateway       | Tools available     | ⬜     |       |
| Linear        | API connection      | ⬜     |       |
| Observability | LangSmith           | ⬜     |       |
| Observability | Grafana             | ⬜     |       |
| State         | PostgreSQL          | ⬜     |       |
| State         | Redis               | ⬜     |       |

**Legend:** ✅ Pass | ❌ Fail | ⬜ Not tested

---

## Troubleshooting Quick Reference

### Common Issues

1. **RAG returns 403**

   - Cause: Qdrant API key expired
   - Fix: Generate new key in Qdrant Cloud, update .env, recreate rag-context

2. **Container OOM killed**

   - Cause: Memory limit exceeded
   - Fix: Check limits in docker-compose.yml, increase if needed

3. **No LangSmith traces**

   - Cause: LANGSMITH_TRACING not set or API key invalid
   - Fix: Check .env, verify key at smith.langchain.com

4. **Metrics not appearing in Grafana**
   - Cause: Alloy not scraping
   - Fix: `ssh do-codechef-droplet "systemctl restart alloy"`

---

## Post-Test Actions

- [ ] Document any failures in Linear
- [ ] Create issues for broken functionality
- [ ] Update this checklist if tests need modification
- [ ] Commit test results to repo (if applicable)

---

## Related Documents

- **RAG Guide**: `support/docs/operations/RAG_SEMANTIC_SEARCH.md`
- **Deployment Guide**: `support/docs/DEPLOYMENT.md`
- **Observability Guide**: `support/docs/OBSERVABILITY_GUIDE.md`
- **Architecture**: `support/docs/ARCHITECTURE.md`
