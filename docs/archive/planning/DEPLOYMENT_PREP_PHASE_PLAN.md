# Deployment Prep Phase - Action Plan

**Target Platform**: DigitalOcean Droplets + Gradient AI Platform  
**Timeline**: 2-3 weeks  
**Status**: 📋 Planning

---

## Phase Overview

Prepare Dev-Tools for production deployment with advanced orchestration, monitoring, and hybrid cloud integration. This phase bridges local development with DigitalOcean's managed services while maintaining the flexibility of custom MCP tooling.

---

## Implementation Tracks

### Track 1: Advanced Orchestration (Week 1)

#### 1.1 Parallel Subtask Execution

**Goal**: Execute independent subtasks concurrently to reduce workflow latency

**Tasks**:

- [ ] Refactor orchestrator `/execute` to use `asyncio.gather()` for parallel groups
- [ ] Implement dependency resolution algorithm (topological sort)
- [ ] Add parallelization metadata to `SubTask` model
- [ ] Create parallel execution coordinator
- [ ] Test: Feature-dev + Infrastructure run simultaneously
- [ ] Benchmark: Sequential vs parallel execution times

**Implementation Details**:

```python
# agents/orchestrator/main.py
async def execute_parallel_group(subtasks: List[SubTask]) -> List[Dict]:
    """Execute subtasks without dependencies in parallel"""
    tasks = [execute_single_subtask(st) for st in subtasks]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return process_results(results)
```

**Files to Modify**:

- `agents/orchestrator/main.py` - Add parallel execution logic
- `agents/orchestrator/requirements.txt` - Ensure asyncio compatibility

**Success Criteria**:

- [ ] Parallel subtasks complete in 40-60% less time than sequential
- [ ] Error in one subtask doesn't block others
- [ ] Execution results maintain correct ordering

---

#### 1.2 Conditional Workflow Branching

**Goal**: Route based on agent responses (e.g., code-review rejection triggers refactor loop)

**Tasks**:

- [ ] Define workflow branching rules in routing config
- [ ] Implement decision engine in orchestrator
- [ ] Add `on_failure`, `on_success` handlers to subtasks
- [ ] Create retry mechanism with exponential backoff
- [ ] Test: Code-review rejection → feature-dev revision → re-review
- [ ] Add max retry limit (prevent infinite loops)

**Implementation Details**:

```yaml
# configs/routing/workflow-branches.yaml
workflows:
  feature_implementation:
    steps:
      - agent: feature-dev
        on_success: code-review
        on_failure: log_and_notify
      - agent: code-review
        on_approval: cicd
        on_rejection:
          action: retry
          target: feature-dev
          max_attempts: 3
```

**Files to Create**:

- `configs/routing/workflow-branches.yaml` - Branching rules
- `agents/orchestrator/decision_engine.py` - Conditional logic

**Success Criteria**:

- [ ] Failed code-review triggers automatic refactor
- [ ] Max retry prevents infinite loops
- [ ] Branch execution tracked in state DB

---

#### 1.3 Workflow Checkpointing & Resumption

**Goal**: Resume workflows from last successful step after failures

**Tasks**:

- [ ] Add checkpoint states to PostgreSQL schema
- [ ] Implement checkpoint save after each subtask completion
- [ ] Create `/resume/{task_id}` endpoint in orchestrator
- [ ] Add workflow recovery logic on service restart
- [ ] Test: Kill orchestrator mid-workflow, resume successfully
- [ ] Document recovery procedures

**Implementation Details**:

```sql
-- configs/state/schema.sql
ALTER TABLE workflows ADD COLUMN checkpoint_data JSONB;
ALTER TABLE workflows ADD COLUMN last_checkpoint TIMESTAMP;
CREATE INDEX idx_workflows_status ON workflows(status) WHERE status = 'in_progress';
```

**Files to Modify**:

- `configs/state/schema.sql` - Add checkpoint columns
- `services/state/main.py` - Checkpoint CRUD operations
- `agents/orchestrator/main.py` - Save/load checkpoints

**Success Criteria**:

- [ ] Workflows resume from exact checkpoint after crash
- [ ] No duplicate subtask execution
- [ ] Checkpoint data includes all context for resumption

---

### Track 2: Service Mesh Integration (Week 2)

#### 2.1 Service Discovery with Consul

**Goal**: Dynamic agent endpoint resolution (no hardcoded URLs)

**Tasks**:

- [ ] Add Consul service to docker-compose
- [ ] Register all agents with Consul on startup
- [ ] Implement service discovery client in orchestrator
- [ ] Replace hardcoded `AGENT_ENDPOINTS` with Consul lookups
- [ ] Add health check registration
- [ ] Test: Agent discovery after dynamic port changes

**Implementation Details**:

```yaml
# compose/docker-compose.yml
consul:
  image: consul:1.17
  ports:
    - "8500:8500"
  command: agent -dev -ui -client=0.0.0.0

orchestrator:
  environment:
    - CONSUL_HOST=consul
    - CONSUL_PORT=8500
  depends_on:
    - consul
```

**Files to Create**:

- `services/discovery/consul_client.py` - Service discovery wrapper

**Success Criteria**:

- [ ] Agents auto-register with Consul on startup
- [ ] Orchestrator resolves endpoints dynamically
- [ ] Failed agents automatically deregistered

---

#### 2.2 Circuit Breaker Pattern

**Goal**: Prevent cascading failures from overloaded/failing agents

**Tasks**:

- [ ] Implement circuit breaker for inter-agent calls
- [ ] Add failure threshold configuration (e.g., 5 failures = open circuit)
- [ ] Create half-open state with retry backoff
- [ ] Add circuit state to monitoring metrics
- [ ] Test: Simulate agent overload, verify circuit opens
- [ ] Document circuit breaker thresholds

**Implementation Details**:

```python
# services/resilience/circuit_breaker.py
from pybreaker import CircuitBreaker

agent_breakers = {
    "feature-dev": CircuitBreaker(fail_max=5, timeout_duration=60),
    "code-review": CircuitBreaker(fail_max=3, timeout_duration=30),
}

async def call_with_breaker(agent: str, endpoint: str, payload: dict):
    breaker = agent_breakers[agent]
    return await breaker.call_async(http_client.post, endpoint, json=payload)
```

**Dependencies**:

- `pybreaker==1.0.2` - Circuit breaker library

**Success Criteria**:

- [ ] Circuit opens after threshold failures
- [ ] Half-open state attempts recovery
- [ ] Fallback responses prevent client errors

---

#### 2.3 Request Tracing with OpenTelemetry

**Goal**: Trace requests across all agent hops for debugging

**Tasks**:

- [ ] Add OpenTelemetry SDK to all agents
- [ ] Configure Jaeger exporter
- [ ] Add Jaeger service to docker-compose
- [ ] Instrument inter-agent HTTP calls with trace context
- [ ] Create trace visualization dashboard
- [ ] Test: View complete trace for multi-agent workflow

**Implementation Details**:

```yaml
# compose/docker-compose.yml
jaeger:
  image: jaegertracing/all-in-one:1.51
  ports:
    - "16686:16686" # UI
    - "4318:4318" # OTLP HTTP receiver
  environment:
    - COLLECTOR_OTLP_ENABLED=true
```

**Dependencies**:

- `opentelemetry-api==1.21.0`
- `opentelemetry-sdk==1.21.0`
- `opentelemetry-instrumentation-fastapi==0.42b0`
- `opentelemetry-exporter-otlp==1.21.0`

**Success Criteria**:

- [ ] Full request trace visible in Jaeger UI
- [ ] Span timing shows agent processing duration
- [ ] Error spans highlight failure points

---

### Track 3: Monitoring & Observability (Week 2-3)

#### 3.1 Metrics Collection with Prometheus

**Goal**: Collect and aggregate performance metrics from all services

**Tasks**:

- [ ] Add Prometheus service to docker-compose
- [ ] Instrument agents with `prometheus_client`
- [ ] Expose `/metrics` endpoint on all agents
- [ ] Configure Prometheus scrape targets
- [ ] Create custom metrics (workflow_duration, subtask_success_rate)
- [ ] Test: Query metrics via Prometheus UI

**Implementation Details**:

```python
# agents/orchestrator/metrics.py
from prometheus_client import Counter, Histogram, generate_latest

workflow_counter = Counter('workflows_total', 'Total workflows executed', ['status'])
workflow_duration = Histogram('workflow_duration_seconds', 'Workflow execution time')

@app.get("/metrics")
async def metrics():
    return Response(content=generate_latest(), media_type="text/plain")
```

**Metrics to Track**:

- `workflows_total{status="completed|failed"}`
- `workflow_duration_seconds` (histogram)
- `agent_calls_total{agent="...", status="..."}`
- `rag_query_duration_seconds`
- `code_review_findings{severity="..."}`

**Success Criteria**:

- [ ] All agents expose Prometheus-compatible metrics
- [ ] Metrics scraped every 15 seconds
- [ ] Historical data retained for 30 days

---

#### 3.2 Grafana Dashboards

**Goal**: Visual monitoring of system health and performance

**Tasks**:

- [ ] Add Grafana service to docker-compose
- [ ] Configure Prometheus as data source
- [ ] Create "System Overview" dashboard (all services health)
- [ ] Create "Workflow Performance" dashboard (latency, throughput)
- [ ] Create "Agent Activity" dashboard (per-agent metrics)
- [ ] Export dashboard JSON to version control
- [ ] Test: Trigger workflows, observe real-time metrics

**Dashboard Panels**:

1. **System Overview**:

   - Service uptime gauge
   - Total workflows (24h)
   - Success rate percentage
   - Active workflows graph

2. **Workflow Performance**:

   - P50/P95/P99 latency
   - Throughput (workflows/hour)
   - Parallel vs sequential comparison
   - Failure rate by agent

3. **Agent Activity**:
   - Request rate per agent
   - Average response time
   - Circuit breaker states
   - RAG query performance

**Files to Create**:

- `monitoring/grafana/dashboards/system-overview.json`
- `monitoring/grafana/dashboards/workflow-performance.json`
- `monitoring/grafana/dashboards/agent-activity.json`

**Success Criteria**:

- [ ] Dashboards load within 2 seconds
- [ ] Real-time data updates every 5 seconds
- [ ] Alerts trigger on service failures

---

#### 3.3 Alerting & Notification

**Goal**: Automated alerts for critical failures and performance degradation

**Tasks**:

- [ ] Configure Grafana alert rules
- [ ] Set up notification channels (email, Slack, Discord)
- [ ] Create alert policies (severity levels, escalation)
- [ ] Add alert annotations to dashboards
- [ ] Test: Trigger failure condition, verify alert fires
- [ ] Document alert runbooks

**Alert Rules**:

```yaml
# monitoring/alerts/critical.yaml
groups:
  - name: service_health
    interval: 1m
    rules:
      - alert: ServiceDown
        expr: up{job="agents"} == 0
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "Service {{ $labels.instance }} is down"

      - alert: HighWorkflowFailureRate
        expr: rate(workflows_total{status="failed"}[5m]) > 0.2
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Workflow failure rate above 20%"
```

**Success Criteria**:

- [ ] Critical alerts delivered within 1 minute
- [ ] False positive rate < 5%
- [ ] Alert resolution tracked in dashboard

---

### Track 4: DigitalOcean Integration (Week 3)

#### 4.1 Droplet Deployment Automation

**Goal**: One-command deployment to DigitalOcean droplet

**Tasks**:

- [ ] Create Terraform configuration for droplet provisioning
- [ ] Add Docker installation script
- [ ] Configure firewall rules (ports 8000-8008, 6333, 5432)
- [ ] Add SSH key management
- [ ] Create deployment script (`scripts/deploy_to_do.sh`)
- [ ] Test: Deploy fresh instance from local machine
- [ ] Document deployment process

**Implementation Details**:

```hcl
# terraform/droplet.tf
resource "digitalocean_droplet" "dev_tools" {
  image    = "docker-20-04"
  name     = "dev-tools-prod"
  region   = "nyc3"
  size     = "s-4vcpu-8gb"  # $48/month
  ssh_keys = [var.ssh_key_fingerprint]

  user_data = file("${path.module}/cloud-init.yaml")

  tags = ["dev-tools", "production"]
}

resource "digitalocean_firewall" "dev_tools" {
  name = "dev-tools-firewall"
  droplet_ids = [digitalocean_droplet.dev_tools.id]

  inbound_rule {
    protocol         = "tcp"
    port_range       = "22"
    source_addresses = [var.admin_ip]
  }

  inbound_rule {
    protocol         = "tcp"
    port_range       = "8000-8008"
    source_addresses = ["0.0.0.0/0"]
  }
}
```

**Files to Create**:

- `terraform/droplet.tf` - Infrastructure as code
- `terraform/variables.tf` - Configuration variables
- `terraform/outputs.tf` - Droplet IP, connection info
- `scripts/deploy_to_do.sh` - Deployment automation
- `docs/DIGITALOCEAN_DEPLOYMENT.md` - Deployment guide

**Success Criteria**:

- [ ] Droplet provisions in < 5 minutes
- [ ] All services start automatically
- [ ] Health checks pass within 2 minutes

---

#### 4.2 Gradient AI Platform Integration

**Goal**: Hybrid architecture with managed agents for standard tasks

**Tasks**:

- [ ] Create DigitalOcean Gradient workspace
- [ ] Build knowledge base from Dev-Tools docs (auto-indexing)
- [ ] Deploy parent orchestrator agent to Gradient
- [ ] Configure function routes to self-hosted MCP gateway
- [ ] Test: Gradient agent calls Docker-hosted feature-dev
- [ ] Document hybrid routing patterns

**Architecture**:

```
User Request
    ↓
Gradient Platform (Parent Orchestrator)
    ├─→ Managed Child Agent (documentation queries)
    ├─→ Serverless Inference API (code review)
    └─→ Function Route → Docker MCP Gateway
            ├─→ feature-dev (custom)
            ├─→ infrastructure (custom)
            └─→ cicd (custom)
```

**Integration Points**:

- Gradient knowledge base: Auto-sync from GitHub repo
- Function routes: HTTP callbacks to droplet endpoints
- LangChain integration: `langchain-gradient` for custom workflows

**Files to Create**:

- `gradient/parent_agent_config.yaml` - Agent workspace definition
- `gradient/function_routes.json` - MCP gateway endpoints
- `docs/GRADIENT_INTEGRATION.md` - Hybrid architecture guide

**Success Criteria**:

- [ ] Gradient agent successfully routes to custom MCP servers
- [ ] Knowledge base searches return Dev-Tools docs
- [ ] Cost reduced by 60% vs all-GPU approach

---

#### 4.3 VS Code Remote Development Setup

**Goal**: Seamless IDE integration with droplet deployment

**Tasks**:

- [ ] Install DigitalOcean MCP Server in VS Code
- [ ] Configure Remote-SSH for droplet connection
- [ ] Test devcontainer on droplet
- [ ] Create workspace settings for remote development
- [ ] Document IDE setup process
- [ ] Add VS Code tasks for remote deployment

**VS Code Configuration**:

```json
// .vscode/tasks.json
{
  "version": "2.0.0",
  "tasks": [
    {
      "label": "Deploy to DigitalOcean",
      "type": "shell",
      "command": "./scripts/deploy_to_do.sh",
      "group": "build"
    },
    {
      "label": "SSH to Droplet",
      "type": "shell",
      "command": "ssh root@${input:dropletIP}"
    }
  ]
}
```

**Files to Create**:

- `.vscode/settings.json` - Remote development settings
- `.vscode/tasks.json` - Deployment tasks
- `docs/VSCODE_REMOTE_SETUP.md` - IDE configuration guide

**Success Criteria**:

- [ ] One-click SSH connection from VS Code
- [ ] Remote debugging works for all agents
- [ ] File sync < 2 seconds for typical edits

---

### Track 5: Production Hardening (Week 3)

#### 5.1 Security Enhancements

**Tasks**:

- [ ] Add authentication to agent endpoints (API keys)
- [ ] Implement rate limiting (10 req/sec per client)
- [ ] Enable HTTPS with Let's Encrypt certificates
- [ ] Add request/response validation middleware
- [ ] Scan Docker images for vulnerabilities
- [ ] Document security best practices

**Implementation**:

```python
# services/security/auth_middleware.py
from fastapi import Security, HTTPException
from fastapi.security import HTTPBearer

security = HTTPBearer()

async def verify_api_key(credentials: HTTPAuthorizationCredentials = Security(security)):
    if credentials.credentials != os.getenv("API_KEY"):
        raise HTTPException(status_code=401, detail="Invalid API key")
    return credentials.credentials
```

---

#### 5.2 Backup & Disaster Recovery

**Tasks**:

- [ ] Automate nightly backups (volumes + PostgreSQL)
- [ ] Configure DigitalOcean Spaces for backup storage
- [ ] Test restore procedure from backups
- [ ] Add backup monitoring to Grafana
- [ ] Document recovery runbooks
- [ ] Set up cross-region backup replication

**Backup Strategy**:

- **Frequency**: Daily at 02:00 UTC
- **Retention**: 7 daily, 4 weekly, 3 monthly
- **Storage**: DigitalOcean Spaces (S3-compatible)
- **RTO**: 4 hours
- **RPO**: 24 hours

---

#### 5.3 Performance Optimization

**Tasks**:

- [ ] Add Redis caching for RAG queries
- [ ] Implement connection pooling for PostgreSQL
- [ ] Enable HTTP/2 for inter-agent communication
- [ ] Optimize Docker image sizes (multi-stage builds)
- [ ] Add CDN for static assets (if any)
- [ ] Load test with 100 concurrent workflows

**Performance Targets**:

- Workflow latency (p95): < 2 seconds
- RAG query time: < 100ms
- Database query time: < 50ms
- Service startup: < 10 seconds
- Memory per service: < 512MB

---

## Testing Strategy

### Integration Tests

```python
# tests/integration/test_parallel_execution.py
async def test_parallel_subtasks():
    """Verify independent subtasks execute concurrently"""
    task = await orchestrate({
        "description": "Build feature X AND deploy infrastructure Y"
    })

    start = time.time()
    result = await execute_workflow(task.task_id)
    duration = time.time() - start

    assert result.status == "completed"
    assert duration < 3.0  # Both subtasks finish in parallel
```

### Load Tests

```bash
# tests/load/workflow_load_test.sh
# Simulate 50 concurrent workflows
for i in {1..50}; do
  curl -X POST http://localhost:8001/orchestrate \
    -H "Content-Type: application/json" \
    -d '{"description":"Test workflow '$i'"}' &
done
wait
```

### Monitoring Validation

- [ ] All dashboards display without errors
- [ ] Alert rules trigger correctly
- [ ] Traces visible in Jaeger for all workflows

---

## Documentation Deliverables

1. **DEPLOYMENT_GUIDE.md**: Step-by-step droplet setup
2. **MONITORING_GUIDE.md**: Dashboard usage and alerting
3. **ARCHITECTURE_ADVANCED.md**: Service mesh and orchestration
4. **GRADIENT_INTEGRATION.md**: Hybrid cloud patterns
5. **RUNBOOKS.md**: Operational procedures and troubleshooting

---

## Success Metrics

### Performance

- [ ] Parallel execution 50% faster than sequential
- [ ] P95 latency < 2 seconds end-to-end
- [ ] Service uptime > 99.5%

### Reliability

- [ ] Circuit breakers prevent cascading failures
- [ ] Checkpoint recovery works 100% of time
- [ ] Zero data loss in state persistence

### Observability

- [ ] 100% of workflows traced in Jaeger
- [ ] All critical metrics tracked in Grafana
- [ ] Alert response time < 5 minutes

### Cost Efficiency

- [ ] Hybrid architecture 60% cheaper than all-GPU
- [ ] Droplet cost < $50/month for dev environment
- [ ] Gradient usage < $100/month for production

---

## Risk Mitigation

| Risk                            | Impact | Mitigation                           |
| ------------------------------- | ------ | ------------------------------------ |
| Service discovery adds latency  | Medium | Cache lookups, fallback to hardcoded |
| Circuit breaker false positives | Low    | Tune thresholds based on load tests  |
| Monitoring overhead             | Low    | Sample 10% of traces in production   |
| DigitalOcean API rate limits    | Medium | Implement exponential backoff        |
| Network partitions              | High   | Add timeout + retry to all calls     |

---

## Next Steps (Post-Deployment)

1. **Phase 6: ML Integration**

   - Fine-tune models on DigitalOcean GPU Droplets
   - Deploy custom models to Gradient inference API
   - Add model versioning and A/B testing

2. **Phase 7: Multi-Tenancy**

   - Per-project agent workspaces
   - Resource isolation and quotas
   - Billing and usage tracking

3. **Phase 8: Advanced AI Features**
   - Agent learning from user feedback
   - Automated workflow optimization
   - Predictive resource scaling

---

**Estimated Total Timeline**: 15-20 days  
**Required Skills**: Docker, Python async, Terraform, Prometheus/Grafana, DigitalOcean API  
**Budget**: ~$150/month (droplet + monitoring + Gradient usage)
