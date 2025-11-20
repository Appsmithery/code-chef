# Prometheus Metrics Integration

## Overview

All Dev-Tools agents are instrumented with **Prometheus** for comprehensive system monitoring. Prometheus provides:

- 📊 **HTTP metrics**: Request rates, latencies, status codes
- 🔄 **System metrics**: CPU, memory, connections
- ⚡ **Performance tracking**: P50/P95/P99 latencies
- 🎯 **Service health**: Uptime, error rates, throughput

## Architecture

- **Auto-instrumentation**: Uses `prometheus-fastapi-instrumentator` for zero-config metrics
- **Pull model**: Prometheus scrapes `/metrics` endpoints every 15s
- **Docker native**: Service discovery via Docker Compose network
- **Persistent storage**: Metrics stored in `prometheus-data` volume

## Quick Start

### 1. Validate Setup

```powershell
./support/scripts/setup-prometheus.ps1
```

This script verifies:

- Prometheus configuration file exists
- Docker Compose service defined
- All 6 agents have instrumentation
- Scrape targets configured

### 2. Start Prometheus

```bash
docker-compose -f deploy/docker-compose.yml up -d prometheus
```

Access Prometheus UI: http://localhost:9090

### 3. Enable Agent Metrics

```bash
# Rebuild agents with prometheus-fastapi-instrumentator
docker-compose -f deploy/docker-compose.yml build

# Restart agents
docker-compose -f deploy/docker-compose.yml restart orchestrator feature-dev code-review infrastructure cicd documentation
```

### 4. Verify Metrics

Open http://localhost:9090/targets to see all scrape targets:

- **orchestrator** (8001) - Task routing metrics
- **feature-dev** (8002) - Code generation metrics
- **code-review** (8003) - Review analysis metrics
- **infrastructure** (8004) - IaC generation metrics
- **cicd** (8005) - Pipeline automation metrics
- **documentation** (8006) - Doc generation metrics
- **gateway-mcp** (8000) - MCP tool proxy metrics
- **prometheus** (9090) - Self-monitoring

## Configuration

### Scrape Configuration

File: `config/prometheus/prometheus.yml`

```yaml
global:
  scrape_interval: 15s # Collect metrics every 15 seconds
  evaluation_interval: 15s
  external_labels:
    cluster: "dev-tools"
    environment: "development"

scrape_configs:
  - job_name: "orchestrator"
    static_configs:
      - targets: ["orchestrator:8001"]
        labels:
          service: "orchestrator"
          agent_type: "coordinator"
```

### Agent Instrumentation

Each agent's `main.py` includes:

```python
from prometheus_fastapi_instrumentator import Instrumentator

app = FastAPI(title="Agent Name")

# Enable Prometheus metrics collection
Instrumentator().instrument(app).expose(app)
```

This automatically exposes:

- `/metrics` - Prometheus-formatted metrics endpoint
- Request duration histograms
- Request count by method/path/status
- In-progress request gauge
- Request body size histograms
- Response body size histograms

## Available Metrics

### HTTP Metrics (Auto-generated)

```promql
# Request rate (requests/sec)
rate(http_requests_total[5m])

# Request latency (P50, P95, P99)
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))

# Error rate (5xx responses)
rate(http_requests_total{status=~"5.."}[5m])

# Requests by agent
http_requests_total{service="orchestrator"}

# Active requests
http_requests_inprogress
```

### System Metrics

```promql
# CPU usage
rate(process_cpu_seconds_total[5m])

# Memory usage
process_resident_memory_bytes

# Open file descriptors
process_open_fds
```

## Example Queries

### 1. Agent Request Rate

```promql
sum(rate(http_requests_total[5m])) by (service)
```

Shows requests/sec for each agent.

### 2. Response Time P95

```promql
histogram_quantile(0.95,
  sum(rate(http_request_duration_seconds_bucket[5m])) by (le, service)
)
```

95th percentile latency per agent.

### 3. Error Rate by Agent

```promql
sum(rate(http_requests_total{status=~"5.."}[5m])) by (service) /
sum(rate(http_requests_total[5m])) by (service)
```

Percentage of 5xx errors.

### 4. Top Slowest Endpoints

```promql
topk(5,
  http_request_duration_seconds_sum{handler!="/metrics"}
)
```

Endpoints with highest cumulative latency.

### 5. MCP Gateway Throughput

```promql
rate(http_requests_total{service="gateway-mcp"}[5m])
```

Tool invocations per second through MCP.

## Dashboards

### Built-in Prometheus UI

1. **Graph**: http://localhost:9090/graph
2. **Targets**: http://localhost:9090/targets (health checks)
3. **Alerts**: http://localhost:9090/alerts (when rules configured)

### Grafana Integration (Optional)

To add Grafana dashboards:

```yaml
# deploy/docker-compose.yml
grafana:
  image: grafana/grafana:latest
  ports: ["3001:3000"]
  environment:
    - GF_SECURITY_ADMIN_PASSWORD=admin
  volumes:
    - grafana-data:/var/lib/grafana
```

Import community dashboards:

- FastAPI: Dashboard ID 16097
- Node Exporter: Dashboard ID 1860
- Prometheus Stats: Dashboard ID 2

## MCP Prometheus Server (Future)

The [prometheus-mcp-server](https://github.com/pab1it0/prometheus-mcp-server) will allow **agents to query Prometheus metrics via MCP tools**.

Example use case:

```python
# Agent queries its own performance
metrics = await mcp_client.invoke_tool(
    server="prometheus",
    tool="query_metrics",
    params={"query": "rate(http_requests_total{service='orchestrator'}[5m])"}
)

# Self-optimization based on metrics
if metrics["value"] > 100:  # High load
    await scale_down_complexity()
```

This enables **self-monitoring agents** that adjust behavior based on real-time performance data.

## Alerting (Future Enhancement)

Create `config/prometheus/alerts.yml`:

```yaml
groups:
  - name: agent_alerts
    rules:
      - alert: HighErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.05
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High error rate on {{ $labels.service }}"

      - alert: SlowResponseTime
        expr: histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) > 5
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Slow responses on {{ $labels.service }}"
```

Reference in `prometheus.yml`:

```yaml
rule_files:
  - "alerts.yml"
```

## Troubleshooting

### Targets showing "DOWN"

```bash
# Check agent health
curl http://localhost:8001/health

# Check if metrics endpoint exists
curl http://localhost:8001/metrics

# View agent logs
docker logs compose-orchestrator-1 --tail 50
```

### No metrics appearing

```bash
# Verify Prometheus config
docker exec prometheus promtool check config /etc/prometheus/prometheus.yml

# Reload Prometheus config
curl -X POST http://localhost:9090/-/reload
```

### High memory usage

```bash
# Check Prometheus storage
docker exec prometheus du -sh /prometheus

# Limit retention (in prometheus.yml command)
--storage.tsdb.retention.time=7d
```

## Integration with Langfuse

Prometheus and Langfuse provide complementary observability:

- **Prometheus**: System metrics (CPU, requests, latencies)
- **Langfuse**: LLM metrics (tokens, costs, prompts)

Together:

```promql
# Correlation: High request rate + High token usage
http_requests_total * on(service) langfuse_token_count
```

## Best Practices

1. **Keep scrape intervals reasonable**: 15s default, 30s for low-traffic services
2. **Use labels for filtering**: `service`, `agent_type`, `environment`
3. **Monitor P95/P99 latencies**: P50 can hide issues
4. **Set up alerts for critical paths**: Orchestrator routing, MCP gateway
5. **Export metrics for long-term storage**: Use remote_write to external TSDB

## References

- [Prometheus Documentation](https://prometheus.io/docs/)
- [prometheus-fastapi-instrumentator](https://github.com/trallnag/prometheus-fastapi-instrumentator)
- [PromQL Basics](https://prometheus.io/docs/prometheus/latest/querying/basics/)
- [Dev-Tools Tracing Plan](../config/tracing-plan-v2.md)
