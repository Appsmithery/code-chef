# Grafana Dashboard Guide

## Current Setup (November 2025)

### Prometheus Configuration

- **Single Prometheus instance**: `prometheus:9090` (correctly configured)
- **Scrape targets**: orchestrator:8001, gateway-mcp:8000, rag-context:8007, state-persistence:8008, agent-registry:8009
- **Scrape interval**: 15s (30s for RAG)
- **Data source**: Configured in Grafana Cloud

### Available Dashboards

#### 1. **Agent Performance** ✅ WORKING

- **Purpose**: HTTP request metrics, response times, error rates
- **Data Source**: Prometheus (orchestrator + services)
- **Key Panels**:
  - Request rate by agent (`http_requests_total`)
  - Response time P95 (`http_request_duration_seconds`)
  - Error rate (5xx responses)
  - MCP Gateway connection status

**Status**: ✅ Working immediately - uses HTTP metrics from prometheus-fastapi-instrumentator

#### 2. **LLM Token Metrics & Cost Attribution** ⏳ WAITING FOR DATA

- **Purpose**: Token usage, cost tracking, latency monitoring
- **Data Source**: Prometheus (orchestrator LLM metrics)
- **Key Panels**:
  - Token usage rate by agent
  - Cost breakdown (pie chart)
  - LLM latency distribution (P50, P95, P99)
  - Total cost/tokens/calls (24h)
  - Average tokens per call
  - Cost trend over time
  - Token type distribution (prompt vs completion)

**Status**: ⏳ **Metrics defined but NO DATA YET**

- Metric names exist: `llm_tokens_total`, `llm_cost_usd_total`, `llm_calls_total`, `llm_latency_seconds`
- Counters are at zero (waiting for actual LLM calls)
- **Will populate once orchestrator makes LLM calls**

#### 3. **Prometheus Stats** (Generic)

- **Purpose**: Prometheus self-monitoring
- **Recommendation**: Keep "Prometheus 2.0 Stats", delete duplicate "Prometheus Stats"

---

## Verification Steps

### 1. Check Metrics Availability

**On droplet:**

```bash
# Check HTTP metrics (should have data)
ssh do-mcp-gateway "curl -s http://localhost:8001/metrics | grep http_requests_total"

# Check LLM metrics (defined but may be zero)
ssh do-mcp-gateway "curl -s http://localhost:8001/metrics | grep llm_"
```

### 2. Test LLM Metrics Collection

**Trigger LLM call via API:**

```bash
# Example: Make orchestrator decompose a task (this will call LLM)
curl -X POST https://codechef.appsmithery.co/api/v1/decompose \
  -H "Content-Type: application/json" \
  -d '{"task": "Create a simple Python hello world script"}'
```

**Watch metrics update:**

```bash
ssh do-mcp-gateway "watch -n 5 'curl -s http://localhost:8001/metrics | grep llm_'"
```

### 3. Validate in Grafana

**Grafana Cloud Dashboard:**

1. Navigate to https://appsmithery.grafana.net
2. Open "Agent Performance" - should show HTTP traffic immediately
3. Open "LLM Token Metrics" - will populate after LLM calls

**Prometheus Direct:**

1. Navigate to Prometheus (via SSH tunnel or internal: http://localhost:9090/graph)
2. Query examples:

   ```promql
   # HTTP request rate
   rate(http_requests_total[5m])

   # LLM token usage (will be empty until LLM calls made)
   rate(llm_tokens_total[5m])

   # Response time P95
   histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))
   ```

---

## Dashboard Cleanup Recommendations

### Keep:

1. ✅ **Agent Performance** - Working now with HTTP metrics
2. ✅ **LLM Token Metrics** - Will work once LLM calls are made
3. ✅ **Prometheus 2.0 Stats** - Prometheus self-monitoring

### Remove/Consolidate:

1. ❌ **Prometheus Stats** (duplicate) - Keep only "Prometheus 2.0 Stats"
2. ❓ **Alert Groups Insights**, **Incident Insights**, **Grafana metrics** - If not actively used

---

## Custom LLM Dashboard Question

**Q: Do we still need a custom LLM token metrics dashboard if Grafana creates one by default?**

**A: YES, keep the custom dashboard** because:

1. **Grafana does NOT create LLM dashboards by default** - Only generic Prometheus/Loki dashboards
2. **Your custom dashboard is tailored** to your metrics:
   - Specific metric names (`llm_tokens_total`, `llm_cost_usd_total`)
   - Agent-specific labels
   - Cost attribution and token efficiency analysis
3. **The dashboard exists and is correct** - Just waiting for data

**The dashboard will automatically populate once your orchestrator makes LLM calls**

---

## Troubleshooting

### "LLM Token Metrics dashboard is empty"

**Expected behavior**: Metrics are defined but counters are zero until LLM calls are made

**Solution:**

1. Make a test LLM call via orchestrator API
2. Check metrics: `curl -s http://localhost:8001/metrics | grep llm_`
3. Verify counters increment
4. Refresh Grafana dashboard

### "Agent Performance shows no data"

**Check:**

1. Prometheus scraping: Access via SSH tunnel (`ssh -L 9090:localhost:9090 do-mcp-gateway`, then http://localhost:9090/targets)
2. Grafana data source: Settings > Data Sources > Prometheus (should be healthy)
3. Time range: Try "Last 6 hours" or "Last 24 hours"

### "Duplicate Prometheus dashboards"

**Action**: In Grafana, navigate to Dashboards > Filter by "prometheus" > Delete older "Prometheus Stats", keep "Prometheus 2.0 Stats"

---

## Next Steps

1. ✅ Keep current dashboard configuration
2. 🔄 Make test LLM call to populate metrics
3. ✅ Validate "Agent Performance" dashboard (should work now)
4. ⏳ Validate "LLM Token Metrics" dashboard (after LLM call)
5. 🧹 Clean up duplicate Prometheus dashboards

---

## Metrics Instrumentation Reference

**HTTP Metrics** (prometheus-fastapi-instrumentator):

```python
# Already instrumented in all FastAPI services
from prometheus_fastapi_instrumentator import Instrumentator

instrumentator = Instrumentator()
instrumentator.instrument(app).expose(app)
```

**LLM Metrics** (custom, in orchestrator):

```python
# Metrics defined but need actual LLM calls to populate
from prometheus_client import Counter, Histogram

llm_tokens_total = Counter('llm_tokens_total', 'Total LLM tokens', ['agent', 'type'])
llm_cost_usd_total = Counter('llm_cost_usd_total', 'Total LLM cost USD', ['agent'])
llm_calls_total = Counter('llm_calls_total', 'Total LLM calls', ['agent'])
llm_latency_seconds = Histogram('llm_latency_seconds', 'LLM latency', ['agent'])
```

---

**Updated**: November 25, 2025
