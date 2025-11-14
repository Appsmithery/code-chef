# Gradient AI Integration - Quick Start Guide

## ✅ What Was Done

### Files Created

- `scripts/setup-gradient.ps1` - Automated setup and validation script
- `agents/_shared/gradient_client.py` - OpenAI-compatible Gradient client with Langfuse tracing
- `agents/_shared/gradient_warmup.py` - Cold start prevention module

### Files Updated

- `compose/docker-compose.yml` - Added Gradient environment variables to all 6 agents (18 total)
- `agents/orchestrator/main.py` - Added LLM-powered task decomposition
- `agents/feature-dev/main.py` - Added LLM-powered code generation
- `config/env/.env` - Will be updated by setup script with API key

### Agent Model Configuration

| Agent          | Model                  | Purpose                              |
| -------------- | ---------------------- | ------------------------------------ |
| orchestrator   | llama-3.1-70b-instruct | Complex task decomposition & routing |
| feature-dev    | codellama-13b-instruct | Code generation & implementation     |
| code-review    | llama-3.1-70b-instruct | Deep analysis & security scanning    |
| infrastructure | llama-3.1-8b-instruct  | Fast IaC generation                  |
| cicd           | llama-3.1-8b-instruct  | Pipeline configuration               |
| documentation  | mistral-7b-instruct    | Fast documentation generation        |

---

## 🚀 Getting Started

### Step 1: Get Gradient API Key

1. Visit: https://cloud.digitalocean.com/ai
2. Click **"Get Started"** or **"Generate API Key"**
3. Copy your API key (format: `do-api-XXXXXXXXXXXXXXXX`)

### Step 2: Run Setup Script

```powershell
# Set environment variable
$env:GRADIENT_API_KEY = 'do-api-XXXXXXXXXXXXXXXX'

# Run setup
./scripts/setup-gradient.ps1
```

The script will:

- Validate your API key
- Update `.env` with Gradient configuration
- Verify agent code files
- Create warmup module
- Display next steps

### Step 3: Deploy to Droplet

```bash
# SSH to droplet
ssh root@45.55.173.72

# Navigate to project
cd /opt/Dev-Tools

# Pull latest changes
git pull origin main

# Set Gradient API key
export GRADIENT_API_KEY='do-api-XXXXXXXXXXXXXXXX'

# Update .env file
echo "GRADIENT_API_KEY=$GRADIENT_API_KEY" >> config/env/.env
echo "GRADIENT_BASE_URL=https://api.digitalocean.com/v2/ai" >> config/env/.env
echo "GRADIENT_MODEL=llama-3.1-8b-instruct" >> config/env/.env

# Rebuild agents
docker-compose -f compose/docker-compose.yml build

# Restart services
docker-compose -f compose/docker-compose.yml up -d

# Verify deployment
curl http://localhost:8001/health | jq .
curl http://localhost:8002/health | jq .
```

### Step 4: Test LLM Integration

```bash
# Test orchestrator (task decomposition)
curl -X POST http://localhost:8001/orchestrate \
  -H "Content-Type: application/json" \
  -d '{
    "description": "Build a REST API for user management with CRUD operations",
    "priority": "high"
  }' | jq .

# Test feature-dev (code generation)
curl -X POST http://localhost:8002/implement \
  -H "Content-Type: application/json" \
  -d '{
    "description": "Create a user login endpoint with JWT authentication",
    "context_refs": ["auth", "api"],
    "task_id": "test-123"
  }' | jq .
```

### Step 5: Monitor in Langfuse

1. Open: https://us.cloud.langfuse.com
2. Navigate to **Traces**
3. Filter by:
   - User ID: `orchestrator`, `feature-dev`, etc.
   - Tags: `gradient`, `production`
4. View:
   - Prompts and completions
   - Token usage
   - Latencies
   - Costs (calculated automatically)

### Step 6: Monitor in Prometheus

1. Open: http://45.55.173.72:9090
2. Query metrics:

   ```promql
   # Request rate per agent
   sum(rate(http_requests_total[5m])) by (service)

   # LLM call latency (P95)
   histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))

   # Error rate
   rate(http_requests_total{status=~"5.."}[5m])
   ```

---

## 💡 How It Works

### Architecture Flow

```
User Request
    ↓
Orchestrator Agent (llama-3.1-70b)
    ├─ Analyzes task
    ├─ Calls Gradient API for decomposition
    ├─ Langfuse traces the call
    └─ Routes subtasks to agents

Feature-Dev Agent (codellama-13b)
    ├─ Receives subtask
    ├─ Queries RAG for context
    ├─ Calls Gradient API for code generation
    ├─ Langfuse traces the call
    └─ Returns generated code

Gradient AI Platform
    ├─ Processes LLM inference on GPU
    ├─ Returns completion
    └─ <50ms latency (same datacenter)

Langfuse Cloud
    └─ Stores traces, tokens, costs
```

### Code Integration Pattern

```python
# agents/feature-dev/main.py

from agents._shared.gradient_client import get_gradient_client

# Initialize client (reads GRADIENT_* env vars)
gradient_client = get_gradient_client("feature-dev")

async def implement_feature(request):
    # Check if Gradient is configured
    if gradient_client.is_enabled():
        # Generate code with LLM + automatic Langfuse tracing
        result = await gradient_client.complete(
            prompt=f"Implement: {request.description}",
            system_prompt="You are an expert software engineer.",
            temperature=0.7,
            max_tokens=2000,
            metadata={"task_id": request.task_id}  # Langfuse metadata
        )
        code = result["content"]
        tokens = result["tokens"]
    else:
        # Fallback to mock (for testing without API key)
        code = "# Mock implementation"
        tokens = 0

    return {"code": code, "tokens": tokens}
```

### Automatic Langfuse Tracing

The `gradient_client` automatically wraps OpenAI-compatible calls with Langfuse:

- ✅ Prompts and completions captured
- ✅ Token usage tracked
- ✅ Latencies measured
- ✅ Costs calculated (based on Gradient pricing)
- ✅ Metadata tagged (agent, task_id, tags)

No additional code needed!

---

## 📊 Cost Comparison

| Scenario          | OpenAI GPT-4 | OpenAI GPT-3.5 | Gradient Llama 3.1 8B | Savings             |
| ----------------- | ------------ | -------------- | --------------------- | ------------------- |
| 1M tokens         | $30.00       | $1.50          | $0.20                 | **150x** vs GPT-4   |
| 10M tokens/month  | $300.00      | $15.00         | $2.00                 | **7.5x** vs GPT-3.5 |
| 100M tokens/month | $3,000.00    | $150.00        | $20.00                | **150x** vs GPT-4   |

**Additional Benefits:**

- ✅ <50ms latency (same datacenter vs 200-500ms for OpenAI)
- ✅ No egress fees (stays within DigitalOcean network)
- ✅ Data sovereignty (never leaves your DO account)

---

## 🔧 Troubleshooting

### Issue: "GRADIENT_API_KEY not set"

**Solution:** Run setup script with API key:

```powershell
$env:GRADIENT_API_KEY = 'do-api-XXXXXXXX'
./scripts/setup-gradient.ps1
```

### Issue: "Gradient client not initialized"

**Solution:** Check agent logs:

```bash
docker logs compose-feature-dev-1 | grep GRADIENT
```

Ensure environment variables are set in docker-compose.yml.

### Issue: Cold starts (2-5 second delay)

**Solution:** Implement warmup (already created):

```python
from agents._shared.gradient_warmup import start_warmup_task

@app.on_event("startup")
async def startup():
    start_warmup_task(app, models=["codellama-13b-instruct"])
```

### Issue: Rate limits exceeded

**Solution:** Implement exponential backoff (tenacity library):

```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
async def call_gradient():
    return await gradient_client.complete(...)
```

### Issue: No traces in Langfuse

**Solution:** Verify Langfuse credentials:

```bash
docker exec compose-feature-dev-1 env | grep LANGFUSE
```

Check: https://us.cloud.langfuse.com for API key status.

---

## 📚 Additional Resources

- **Gradient Documentation:** https://docs.digitalocean.com/products/gradient-ai-platform/
- **Integration Plan:** `docs/DigitalOcean-Gradient-Integration.md`
- **Langfuse Examples:** `docs/LANGFUSE_EXAMPLES.md`
- **Prometheus Metrics:** `docs/PROMETHEUS_METRICS.md`

---

## ✅ Validation Checklist

- [ ] Gradient API key obtained from DigitalOcean
- [ ] Setup script executed successfully (`./scripts/setup-gradient.ps1`)
- [ ] `.env` file updated with Gradient credentials
- [ ] Docker containers rebuilt with new code
- [ ] Services restarted and health checks passing
- [ ] Test requests return LLM-generated responses (not mocks)
- [ ] Langfuse traces appearing at https://us.cloud.langfuse.com
- [ ] Prometheus metrics showing request counts at http://45.55.173.72:9090

---

**Estimated Setup Time:** 15-20 minutes
**Ready to Deploy!** 🚀
