# RAG & Qdrant Configuration Alignment

**Date**: November 26, 2025  
**Status**: ✅ Aligned  
**Services**: RAG Context Manager (port 8007), Qdrant Cloud

## Current Production State

### Qdrant Cloud Collections

| Collection      | Points | Status    | Purpose                          |
| --------------- | ------ | --------- | -------------------------------- |
| `the-shop`      | 460    | ✅ Active | Main knowledge base (DO KB sync) |
| `vendor-docs`   | 94     | ✅ Active | Vendor API documentation         |
| `agent_memory`  | 0      | ⚠️ Empty  | Agent conversation memory        |
| `task_context`  | 0      | ⚠️ Empty  | Task-specific context            |
| `code_patterns` | 0      | ⚠️ Empty  | Code examples and patterns       |
| `feature_specs` | 0      | ⚠️ Empty  | Feature specifications           |
| `issue_tracker` | 0      | ⚠️ Empty  | Issue tracking context           |

### Configuration Stack

**Qdrant Cloud:**

- **Cluster ID**: `83b61795-7dbd-4477-890e-edce352a00e2`
- **Region**: `us-east4-0.gcp` (Google Cloud Platform)
- **URL**: `https://83b61795-7dbd-4477-890e-edce352a00e2.us-east4-0.gcp.cloud.qdrant.io`
- **Vector Size**: 1536 dimensions
- **Distance Metric**: Cosine similarity

**Embedding Provider:**

- **Provider**: DigitalOcean Gradient AI
- **Model**: `text-embedding-ada-002` (OpenAI-compatible)
- **Endpoint**: `https://inference.do-ai.run/v1`
- **Dimensions**: 1536
- **Timeout**: 60 seconds

**RAG Service (port 8007):**

- **Status**: ✅ Connected to Qdrant Cloud
- **MCP Gateway**: ✅ Connected (http://gateway-mcp:8000)
- **Default Collection**: `the-shop`
- **Health**: http://45.55.173.72:8007/health

## Changes Made (November 26, 2025)

### 1. Security Fix: Remove Hardcoded Credentials

**Before** (`deploy/docker-compose.yml`):

```yaml
- QDRANT_URL=https://83b61795-7dbd-4477-890e-edce352a00e2.us-east4-0.gcp.cloud.qdrant.io
- QDRANT_API_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
- GRADIENT_API_KEY=sk-proj-ecSwAaYNrv1BHlnn0whUVxqiByZY2sPII-17n...
- GRADIENT_BASE_URL=https://api.openai.com
- GRADIENT_EMBEDDING_MODEL=text-embedding-3-small
```

**After** (`deploy/docker-compose.yml`):

```yaml
- QDRANT_URL=${QDRANT_URL}
- QDRANT_API_KEY=${QDRANT_API_KEY}
- GRADIENT_API_KEY=${GRADIENT_MODEL_ACCESS_KEY}
- GRADIENT_BASE_URL=${GRADIENT_BASE_URL:-https://inference.do-ai.run/v1}
- GRADIENT_EMBEDDING_MODEL=${GRADIENT_EMBEDDING_MODEL:-text-embedding-ada-002}
env_file:
  - ../config/env/.env
```

**Impact**:

- ✅ Credentials now loaded from `.env` (gitignored)
- ✅ Consistent with orchestrator and other services
- ✅ Easier to rotate keys and manage environments

### 2. Standardize Embedding Provider

**Changed**: OpenAI → DigitalOcean Gradient AI  
**Reason**:

- Cost savings (150x cheaper: $0.20/1M tokens vs $30/1M)
- <50ms latency (same datacenter)
- OpenAI-compatible API
- Consistent with orchestrator LLM provider

**Model Mapping**:

- Old: `text-embedding-3-small` (OpenAI direct)
- New: `text-embedding-ada-002` (DO Gradient proxy)
- Both produce 1536-dimensional vectors ✅

### 3. Update Configuration Template

**File**: `config/env/.env.template`

**Added**:

- Clearer Qdrant URL format documentation
- `QDRANT_HOST` and `QDRANT_PORT` for local dev
- `EMBEDDING_TIMEOUT` variable
- Deprecated old variables (with migration notes)

**Removed Ambiguity**:

- Consolidated `QDRANT_CLUSTER_*` → use `QDRANT_URL` + `QDRANT_API_KEY`
- Added comments explaining where to get credentials

## Deployment Steps

### 1. Update Production `.env`

SSH to droplet and update `/opt/Dev-Tools/config/env/.env`:

```bash
ssh root@45.55.173.72

# Edit .env file
cd /opt/Dev-Tools
nano config/env/.env

# Add/update these lines:
QDRANT_URL=https://83b61795-7dbd-4477-890e-edce352a00e2.us-east4-0.gcp.cloud.qdrant.io
QDRANT_API_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhY2Nlc3MiOiJtIn0.et1YNe6_k9mcf7B47VN63WpQYvhaOk74ZQnP-zdgV0E
GRADIENT_MODEL_ACCESS_KEY=<your-gradient-api-key>
GRADIENT_BASE_URL=https://inference.do-ai.run/v1
GRADIENT_EMBEDDING_MODEL=text-embedding-ada-002
EMBEDDING_TIMEOUT=60
```

### 2. Deploy Changes

From local machine:

```powershell
# Option A: Full rebuild (recommended for dependency changes)
.\support\scripts\deploy\deploy-to-droplet.ps1 -DeployType full

# Option B: Quick restart (if only env vars changed)
.\support\scripts\deploy\deploy-to-droplet.ps1 -DeployType config
```

### 3. Verify Deployment

```bash
# Check RAG service health
curl http://45.55.173.72:8007/health

# Should show:
# - qdrant_status: "connected"
# - mcp_gateway_status: "connected"

# Test embeddings with Gradient
curl -X POST http://45.55.173.72:8007/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "How do I use Gradient AI for embeddings?",
    "collection": "vendor-docs",
    "n_results": 3
  }'
```

## Vendor Documentation Indexing

### Current State

**`vendor-docs` Collection**: 94 points indexed

Likely sources (based on `config/rag/indexing.yaml`):

- Linear GraphQL API documentation
- Gradient AI platform docs
- Other vendor APIs

### To Index More Documentation

Use the existing indexing script:

```bash
# Index all Phase 1 sources (recommended)
python support/scripts/rag/index_vendor_docs.py

# Or index specific source
python support/scripts/rag/index_vendor_docs.py --source gradient-ai
python support/scripts/rag/index_vendor_docs.py --source linear-api
python support/scripts/rag/index_vendor_docs.py --source langsmith-api
```

**Sources Available** (see `config/rag/indexing.yaml`):

1. **gradient-ai**: DigitalOcean Gradient platform docs
2. **linear-api**: Linear GraphQL + SDK
3. **langsmith-api**: LangSmith observability
4. **langgraph-reference**: LangGraph agents
5. **langchain-mcp**: LangChain MCP integration
6. **qdrant-api**: Qdrant vector DB API

## Monitoring & Maintenance

### Health Checks

```bash
# RAG service status
curl http://45.55.173.72:8007/health

# List collections
curl http://45.55.173.72:8007/collections

# Query vendor docs
curl -X POST http://45.55.173.72:8007/query \
  -H "Content-Type: application/json" \
  -d '{"query": "test", "collection": "vendor-docs", "n_results": 1}'
```

### Logs

```bash
# View RAG service logs
ssh root@45.55.173.72
cd /opt/Dev-Tools/deploy
docker compose logs rag-context --tail=100 -f

# Check for errors
docker compose logs rag-context --tail=100 | grep -i error
```

### Metrics

**Grafana Dashboard**: https://appsmithery.grafana.net  
**Metrics to Monitor**:

- RAG query latency (`/query` endpoint)
- Embedding generation time
- Qdrant connection status
- Collection sizes over time

### Backup & Recovery

**Qdrant Cloud**: Automatic backups enabled  
**Recovery**: Collections can be re-indexed from source URLs

**Manual Backup** (via Qdrant API):

```bash
# Export collection snapshot
curl -X POST "https://83b61795-7dbd-4477-890e-edce352a00e2.us-east4-0.gcp.cloud.qdrant.io/collections/the-shop/snapshots" \
  -H "api-key: <QDRANT_API_KEY>"
```

## Troubleshooting

### Issue: "Qdrant not available"

**Check**:

1. `QDRANT_URL` and `QDRANT_API_KEY` set in `.env`
2. Network connectivity to Qdrant Cloud
3. RAG service logs: `docker compose logs rag-context`

**Solution**:

```bash
# Test Qdrant connection directly
curl "https://83b61795-7dbd-4477-890e-edce352a00e2.us-east4-0.gcp.cloud.qdrant.io/collections" \
  -H "api-key: <QDRANT_API_KEY>"
```

### Issue: "Embedding API error"

**Check**:

1. `GRADIENT_MODEL_ACCESS_KEY` set in `.env`
2. `GRADIENT_BASE_URL` points to DO Gradient endpoint
3. Embedding timeout not too aggressive

**Solution**:

```bash
# Test embeddings directly
python support/scripts/rag/test_embeddings.py
```

### Issue: Empty Collections

**Check**:

```bash
curl http://45.55.173.72:8007/collections
```

**Solution**:

- For `the-shop`: Should sync from DigitalOcean Knowledge Base (460 points)
- For `vendor-docs`: Run `index_vendor_docs.py` script
- For other collections: Will populate as agents use them

## Next Steps

### Recommended Actions

1. **✅ Deploy Configuration Changes** (see Deployment Steps above)
2. **Index Remaining Vendor Docs** (Phase 1 sources)
3. **Setup Monitoring Alerts** (Grafana for RAG metrics)
4. **Test Agent Context Retrieval** (verify agents query correctly)
5. **Document Query Patterns** (track common queries for optimization)

### Future Enhancements

- **Auto-refresh**: Schedule vendor doc re-indexing (weekly cron)
- **Hybrid Search**: Combine semantic + keyword search
- **Multi-model Embeddings**: Test different embedding models
- **Collection Management**: Auto-prune old/stale vectors
- **Query Caching**: Cache frequent queries in Redis

## References

- **Qdrant Cloud Dashboard**: https://cloud.qdrant.io/
- **RAG Service Code**: `shared/services/rag/main.py`
- **Indexing Config**: `config/rag/indexing.yaml`
- **Vector DB Config**: `config/rag/vectordb.config.yaml`
- **Indexing Script**: `support/scripts/rag/index_vendor_docs.py`
- **Gradient AI Docs**: https://docs.digitalocean.com/products/gradient-ai-platform/
