# LLM Observability Guide

**Last Updated**: December 5, 2025  
**Audience**: DevOps Engineers, SREs, Platform Team

---

## Overview

This guide covers observability for LLM token usage, cost attribution, RAG performance, and agent monitoring across the Dev-Tools platform.

**Key Capabilities**:

- Real-time token/cost tracking via `/metrics/tokens` endpoint
- RAG collection health and query latency metrics
- Prometheus metrics for historical analysis
- Grafana dashboards for visualization (Grafana Cloud: `appsmithery.grafana.net`)
- LangSmith tracing for LLM call inspection
- Automated alerts for cost anomalies and performance degradation

**Related Documentation**:

- Model configuration: `config/agents/models.yaml` (single source of truth)
- Tracing setup: See "LangSmith Tracing" section
- RAG collections: `config/rag/indexing.yaml`

---

## Architecture

### Token Tracking Flow

```
Agent makes LLM call
  ↓
GradientClient.complete() / complete_structured()
  ↓
Extract token usage from response metadata
  ↓
Calculate cost from YAML config (cost_per_1m_tokens)
  ↓
TokenTracker.track(agent, prompt_tokens, completion_tokens, cost, latency)
  ↓
├── Update in-memory aggregates (per-agent stats)
└── Export to Prometheus (counters + histograms)
  ↓
Grafana queries Prometheus for visualization
```

### Configuration

**Cost Metadata** (Single Source of Truth):

All agent models and cost metadata are defined in `config/agents/models.yaml`. This enables:

- Model-agnostic agent definitions (swap models without code changes)
- Environment-specific overrides (dev uses cheaper models)
- Automatic cost calculation based on `cost_per_1m_tokens`

```yaml
# config/agents/models.yaml (excerpt)
agents:
  orchestrator:
    model: <model-name> # Model-agnostic
    cost_per_1m_tokens: 0.60 # Used for automatic cost calculation
    context_window: 128000
    langsmith_project: code-chef-orchestrator
    # ... see full config for all agents
```

**Cost Calculation**:

```python
# In gradient_client.py (automatic)
total_tokens = prompt_tokens + completion_tokens
cost = (total_tokens / 1_000_000) * agent_config.cost_per_1m_tokens
```

**Validate Configuration**:

```bash
python shared/lib/validate_config.py config/agents/models.yaml
```

---

## Metrics Endpoints

### Service Health

| Service      | Port | Endpoint  | Description                         |
| ------------ | ---- | --------- | ----------------------------------- |
| orchestrator | 8001 | `/health` | Agent orchestrator status           |
| rag          | 8007 | `/health` | RAG service + Qdrant connection     |
| state        | 8008 | `/health` | State persistence service           |
| langgraph    | 8010 | `/health` | LangGraph + PostgreSQL checkpointer |

**Note**: MCP Gateway (port 8000) is deprecated. MCP tools are now accessed via Docker MCP Toolkit in VS Code.

### `/metrics/tokens` (JSON API)

**Purpose**: Real-time token/cost summary for programmatic access

**Endpoint**: `GET http://localhost:8001/metrics/tokens`

**Response Format**:

```json
{
  "per_agent": {
    "orchestrator": {
      "prompt_tokens": 1500,
      "completion_tokens": 2000,
      "total_tokens": 3500,
      "total_cost": 0.0021,
      "call_count": 10,
      "model": "<model-name>",
      "avg_tokens_per_call": 350.0,
      "avg_cost_per_call": 0.00021,
      "avg_latency_seconds": 0.85,
      "total_latency": 8.5
    }
  },
  "totals": {
    "total_tokens": 8500,
    "total_cost": 0.0045,
    "total_calls": 25,
    "total_latency": 20.3
  },
  "tracking_since": "2025-12-05T19:00:00.000Z",
  "uptime_seconds": 3600,
  "timestamp": "2025-12-05T20:00:00.000Z",
  "note": "Cost calculated from config/agents/models.yaml"
}
```

**Use Cases**:

- CI/CD cost validation ("did this PR increase token usage?")
- Budget alerts ("notify if daily cost > $50")
- Cost attribution reports ("which agent costs the most?")

**Example Queries**:

```bash
# Get current summary
curl http://localhost:8001/metrics/tokens | jq .

# Check orchestrator cost
curl http://localhost:8001/metrics/tokens | jq '.per_agent.orchestrator.total_cost'

# List agents by cost (descending)
curl http://localhost:8001/metrics/tokens | jq '.per_agent | to_entries | sort_by(.value.total_cost) | reverse | .[].key'
```

---

### RAG Service Endpoints

**Health Check**: `GET http://localhost:8007/health`

```json
{
  "status": "healthy",
  "qdrant_status": "connected",
  "collections": 6,
  "total_vectors": 814
}
```

**Collections List**: `GET http://localhost:8007/collections`

```json
[
  { "name": "code_patterns", "count": 505 },
  { "name": "issue_tracker", "count": 155 },
  { "name": "library_registry", "count": 56 },
  { "name": "vendor-docs", "count": 94 },
  { "name": "feature_specs", "count": 4 },
  { "name": "task_context", "count": 0 }
]
```

**Semantic Search**: `POST http://localhost:8007/query`

```bash
curl -X POST http://localhost:8007/query \
  -H "Content-Type: application/json" \
  -d '{"query": "workflow patterns", "collection": "code_patterns", "limit": 5}'
```

**Configuration**: `config/rag/indexing.yaml`

---

### `/metrics` (Prometheus Format)

**Purpose**: Time-series data for historical analysis and alerting

**Endpoint**: `GET http://localhost:8001/metrics`

**Metrics Exported**:

| Metric                | Type      | Labels                              | Description                    |
| --------------------- | --------- | ----------------------------------- | ------------------------------ |
| `llm_tokens_total`    | Counter   | `agent`, `type` (prompt/completion) | Total tokens used              |
| `llm_cost_usd_total`  | Counter   | `agent`                             | Total cost in USD              |
| `llm_latency_seconds` | Histogram | `agent`                             | Inference latency distribution |
| `llm_calls_total`     | Counter   | `agent`                             | Total LLM calls                |

**Example Prometheus Queries**:

```promql
# Token usage rate (tokens/hour)
rate(llm_tokens_total[1h]) * 3600

# Cost per agent (last 24h)
increase(llm_cost_usd_total[24h]) by (agent)

# Average latency per agent
rate(llm_latency_seconds_sum[5m]) / rate(llm_latency_seconds_count[5m])

# P99 latency
histogram_quantile(0.99, rate(llm_latency_seconds_bucket[5m]))

# Avg tokens per call
sum by (agent) (increase(llm_tokens_total[1h])) / sum by (agent) (increase(llm_calls_total[1h]))

# Top 5 most expensive agents
topk(5, sum by (agent) (llm_cost_usd_total))
```

---

## Grafana Cloud Dashboards

**Dashboard URL**: https://appsmithery.grafana.net
**Prometheus Datasource**: `grafanacloud-appsmithery-prom`

### LLM Token Metrics Dashboard

**Location**: `config/grafana/dashboards/llm-token-metrics.json`

**Panels**:

1. **Token Usage Rate by Agent** (Timeseries)

   - Query: `rate(llm_tokens_total[1h]) * 3600`
   - Unit: tokens/hour
   - Shows real-time token consumption trends

2. **Cost Breakdown by Agent** (Pie Chart)

   - Query: `increase(llm_cost_usd_total[24h])`
   - Unit: USD
   - Identifies most expensive agents

3. **LLM Latency Distribution** (Timeseries)

   - Queries: P50, P95, P99 latencies
   - Unit: seconds
   - Monitors performance degradation

4. **Total Cost (Last 24h)** (Stat Panel)

   - Query: `sum(increase(llm_cost_usd_total[24h]))`
   - Thresholds: Green <$5, Yellow <$10, Red ≥$10

5. **Total Tokens (Last 24h)** (Stat Panel)

   - Query: `sum(increase(llm_tokens_total[24h]))`
   - Quick sanity check for usage

6. **Avg Tokens per Call by Agent** (Bar Gauge)

   - Identifies verbose prompts or inefficient agents

7. **Cost Trend Over Time** (Timeseries Stacked)

   - Stacked area chart showing cost accumulation

8. **Token Type Distribution** (Timeseries Bars)

   - Prompt vs completion token breakdown

9. **Top 5 Most Expensive Agents** (Table)
   - Sortable table with cumulative costs

**Importing Dashboard**:

```bash
# Via Grafana API
curl -X POST http://localhost:3000/api/dashboards/db \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $GRAFANA_API_KEY" \
  -d @config/grafana/dashboards/llm-token-metrics.json

# Via Grafana UI
1. Navigate to Dashboards → Import
2. Upload config/grafana/dashboards/llm-token-metrics.json
3. Select Prometheus datasource
4. Click Import
```

---

## Prometheus Alerts

**Location**: `config/prometheus/alerts/llm-metrics.yml`

### Cost Alerts

**HighLLMCostPerAgent** (Warning)

- **Trigger**: Cost rate > $10/hour for any agent
- **Duration**: 5 minutes
- **Action**: Review usage patterns, consider cheaper model

**TotalDailyCostExceeded** (Critical)

- **Trigger**: Total cost > $50 in 24 hours
- **Duration**: 10 minutes
- **Action**: Emergency review, possible rate limiting

### Anomaly Alerts

**TokenAnomalyDetected** (Warning)

- **Trigger**: Token usage > 3x rolling average
- **Duration**: 5 minutes
- **Action**: Check for retry loops, prompt expansion

**TokensPerCallTooHigh** (Info)

- **Trigger**: Avg tokens/call > 4000
- **Duration**: 10 minutes
- **Action**: Review prompt templates, RAG context size

### Performance Alerts

**LLMLatencyHigh** (Warning)

- **Trigger**: P99 latency > 5 seconds
- **Duration**: 5 minutes
- **Action**: Check Gradient AI status, review max_tokens

**LLMLatencyP95Degraded** (Info)

- **Trigger**: P95 latency 2x higher than 1 hour ago
- **Duration**: 10 minutes
- **Action**: Monitor for continued degradation

### Availability Alerts

**LLMNoRecentCalls** (Warning)

- **Trigger**: No LLM calls for 15 minutes
- **Duration**: 15 minutes
- **Action**: Check agent health, API key validity

---

## Recording Rules

**Purpose**: Pre-aggregate expensive queries for faster dashboard performance

**Rules in `llm-metrics.yml`**:

```yaml
# Avg tokens per call (1h rate)
- record: llm:tokens_per_call:rate1h
  expr: sum by (agent) (rate(llm_tokens_total[1h])) / sum by (agent) (rate(llm_calls_total[1h]))

# Avg cost per call (1h rate)
- record: llm:cost_per_call:rate1h
  expr: sum by (agent) (rate(llm_cost_usd_total[1h])) / sum by (agent) (rate(llm_calls_total[1h]))

# Latency percentiles (5m rate)
- record: llm:latency_p50:rate5m
  expr: histogram_quantile(0.50, rate(llm_latency_seconds_bucket[5m]))

- record: llm:latency_p95:rate5m
  expr: histogram_quantile(0.95, rate(llm_latency_seconds_bucket[5m]))

- record: llm:latency_p99:rate5m
  expr: histogram_quantile(0.99, rate(llm_latency_seconds_bucket[5m]))

# Daily totals (24h increase)
- record: llm:total_cost:increase24h
  expr: sum(increase(llm_cost_usd_total[24h]))

- record: llm:total_tokens:increase24h
  expr: sum(increase(llm_tokens_total[24h]))
```

**Using Recording Rules**:

```promql
# Instead of complex query
sum by (agent) (rate(llm_tokens_total[1h])) / sum by (agent) (rate(llm_calls_total[1h]))

# Use pre-aggregated rule
llm:tokens_per_call:rate1h
```

---

## Troubleshooting

### High Cost Alerts

**Symptom**: `HighLLMCostPerAgent` alert firing

**Investigation Steps**:

1. Check `/metrics/tokens` endpoint:
   ```bash
   curl http://localhost:8001/metrics/tokens | jq '.per_agent.orchestrator'
   ```
2. Review `avg_tokens_per_call` (should be <2000 for most agents)
3. Check LangSmith traces for verbose prompts
4. Review recent code changes (new features, RAG expansions)

**Resolution**:

- Switch to cheaper model in `config/agents/models.yaml` (model-agnostic):
  ```yaml
  # Use development environment override for cheaper testing
  environments:
    development:
      orchestrator:
        model: <cheaper-model>
  ```
- Restart service: `docker compose restart orchestrator` (30s)
- Monitor cost drop in Grafana Cloud: `appsmithery.grafana.net`

---

### Token Anomaly Detection

**Symptom**: `TokenAnomalyDetected` alert firing

**Investigation Steps**:

1. Check Grafana "Token Usage Rate" panel for spikes
2. Query Prometheus for anomaly pattern:
   ```promql
   rate(llm_tokens_total{agent="orchestrator"}[5m]) * 60
   ```
3. Review orchestrator logs for error retries
4. Check `/metrics/tokens` for `call_count` spikes

**Common Causes**:

- **Retry Storm**: Failing LLM calls being retried exponentially
- **Batch Processing**: Large job suddenly hitting platform
- **Prompt Expansion**: New feature added verbose system messages
- **Infinite Loop**: Agent stuck in recursive task decomposition

**Resolution**:

- Implement exponential backoff with max retries
- Add rate limiting for batch jobs
- Review and compress system prompts
- Add circuit breaker for recursive calls

---

### Latency Degradation

**Symptom**: `LLMLatencyP95Degraded` alert firing

**Investigation Steps**:

1. Check Grafana "LLM Latency Distribution" panel
2. Query Prometheus for latency trend:
   ```promql
   llm:latency_p95:rate5m offset 1h
   ```
3. Check Gradient AI status: https://status.digitalocean.com
4. Review `max_tokens` setting (higher = slower)

**Resolution**:

- If Gradient AI issue: Wait for resolution, or switch to fallback provider
- If `max_tokens` too high: Reduce in `config/agents/models.yaml`
- If network issue: Check droplet → Gradient AI latency

---

## Best Practices

### Cost Optimization

1. **Use cheaper models for simple tasks**:

   ```yaml
   # For basic routing/classification
   documentation:
     model: mistral-nemo-instruct-2407 # $0.20/1M vs $0.60/1M
   ```

2. **Environment-specific overrides**:

   ```yaml
   environments:
     development:
       orchestrator:
         model: llama3-8b-instruct # 3x cheaper for testing
   ```

3. **Monitor avg tokens/call**:

   - Target: <2000 tokens/call for most agents
   - Code-review can be higher (4000) for thorough analysis

4. **Set cost budgets**:
   - Configure alert thresholds in `llm-metrics.yml`
   - Review weekly cost reports in Grafana

### Performance Optimization

1. **Set appropriate `max_tokens`**:

   - Orchestrator: 2000 (routing decisions)
   - Code-review: 4000 (detailed feedback)
   - Documentation: 2000 (concise explanations)

2. **Monitor P95/P99 latencies**:

   - Target P95: <2s for interactive agents
   - Target P99: <5s (acceptable for background agents)

3. **Use recording rules for dashboards**:
   - Pre-aggregate expensive queries
   - Reduce Prometheus query load

---

## Validation Scripts

Run these scripts to validate observability setup:

```powershell
# Full stack validation (bash, run on droplet)
./support/scripts/validation/validate-tracing.sh

# PowerShell health checks (Windows, remote)
./support/scripts/validation/test-tracing.ps1

# Token tracking validation
python support/scripts/validation/test-token-tracking.py

# RAG/Qdrant connectivity
python support/scripts/validation/test_qdrant_cloud.py

# LLM provider connectivity
python support/scripts/validation/test_llm_provider.py
```

---

## See Also

- [Model Configuration](../../config/agents/models.yaml) - LLM settings (single source of truth)
- [RAG Configuration](../../config/rag/indexing.yaml) - Collection definitions
- [Testing Guide](../../support/tests/TESTING_GUIDE.md) - Test suite documentation
- [Deployment Guide](DEPLOYMENT.md) - Deploy procedures
- [LangSmith Dashboard](https://smith.langchain.com/) - LLM tracing
- [Grafana Cloud](https://appsmithery.grafana.net) - Metrics dashboards

---

**Questions?** Contact Platform Team or file an issue in Linear (team: DevOps)
