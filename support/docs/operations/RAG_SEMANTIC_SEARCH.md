# RAG Semantic Search - Production Guide

**Last Updated**: November 26, 2025  
**Status**: ✅ Production Ready  
**Service**: RAG Context Manager (port 8007)  
**Vector DB**: Qdrant Cloud

---

## Quick Reference

### Health Check
```bash
curl http://45.55.173.72:8007/health
# Expected: {"status":"ok","qdrant_status":"connected","mcp_gateway_status":"connected"}
```

### List Collections
```bash
curl http://45.55.173.72:8007/collections
```

### Query Semantic Search
```bash
curl -X POST http://45.55.173.72:8007/query \
  -H "Content-Type: application/json" \
  -d '{"query": "workflow execution patterns", "collection": "code_patterns", "limit": 5}'
```

---

## Production Collections (1,218 Total Vectors)

| Collection | Vectors | Source | Purpose | Update Frequency |
|------------|---------|--------|---------|------------------|
| **code_patterns** | 505 | Python AST extraction | Codebase patterns, functions, classes | On deployment |
| **issue_tracker** | 155 | Linear GraphQL API | Issue search, project context | On demand |
| **feature_specs** | 4 | Linear Projects | Project specifications | On demand |
| **the-shop** | 460 | DigitalOcean KB | DigitalOcean documentation | Scheduled sync |
| **vendor-docs** | 94 | API documentation | Vendor API references | Manual |
| **task_context** | 0 | Workflow events | Task execution history | Future (needs workflow_events table) |
| **agent_memory** | 0 | Agent conversations | Episodic agent memory | Future |

---

## Qdrant Cloud Configuration

**Cluster Details:**
- **Cluster ID**: `83b61795-7dbd-4477-890e-edce352a00e2`
- **Region**: `us-east4-0.gcp` (Google Cloud Platform)
- **URL**: `https://83b61795-7dbd-4477-890e-edce352a00e2.us-east4-0.gcp.cloud.qdrant.io`
- **Dashboard**: https://cloud.qdrant.io

**API Key:**
- Created: November 26, 2025
- Expiration: **None** (permanent)
- Access: MANAGE CLUSTER (full access)

**Embeddings:**
- Provider: OpenAI
- Model: `text-embedding-3-small`
- Dimensions: 1536
- Distance: Cosine similarity

---

## Indexing Scripts

All scripts located in `support/scripts/rag/`:

### Index Code Patterns (505 vectors)
Extracts patterns from Python codebase using AST analysis.

```bash
cd /opt/Dev-Tools
python support/scripts/rag/index_code_patterns.py
```

**Pattern Types Extracted:**
- Functions and methods with docstrings
- Class definitions with inheritance
- Data retrieval patterns
- MCP integration patterns
- Workflow components
- Error handling patterns

### Index Linear Issues (155 vectors)
Syncs issues from Linear workspace via GraphQL API.

```bash
cd /opt/Dev-Tools
export LINEAR_API_KEY="lin_oauth_..."
python support/scripts/rag/index_issue_tracker.py
```

**Indexed Fields:**
- Issue title and description
- Comments and discussion
- Labels and priority
- State and assignee

### Index Linear Projects (4 vectors)
Syncs project specifications from Linear.

```bash
cd /opt/Dev-Tools
export LINEAR_API_KEY="lin_oauth_..."
python support/scripts/rag/index_feature_specs.py
```

### Index Vendor Documentation (94 vectors)
Indexes external API documentation.

```bash
cd /opt/Dev-Tools
python support/scripts/rag/index_vendor_docs.py
```

---

## Environment Variables

Required in `config/env/.env`:

```bash
# Qdrant Cloud
QDRANT_URL=https://83b61795-7dbd-4477-890e-edce352a00e2.us-east4-0.gcp.cloud.qdrant.io
QDRANT_API_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
QDRANT_COLLECTION=the-shop
QDRANT_VECTOR_SIZE=1536
QDRANT_DISTANCE=cosine

# OpenAI Embeddings (for indexing)
OPENAI_API_KEY=sk-proj-...
```

---

## RAG Service API

### Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Service health with Qdrant connection status |
| `/collections` | GET | List all collections with vector counts |
| `/query` | POST | Semantic search across collections |
| `/index` | POST | Index new documents (internal) |

### Query Request Format

```json
{
  "query": "How do I implement workflow execution?",
  "collection": "code_patterns",
  "limit": 5,
  "score_threshold": 0.7
}
```

### Query Response Format

```json
{
  "results": [
    {
      "content": "async def execute_workflow(self, workflow_id: str)...",
      "metadata": {
        "file_path": "agent_orchestrator/workflows/workflow_engine.py",
        "pattern_type": "workflow_component",
        "lines": "145-200"
      },
      "score": 0.89
    }
  ],
  "collection": "code_patterns",
  "query": "How do I implement workflow execution?",
  "count": 5
}
```

---

## Troubleshooting

### Issue: "403 Forbidden" from Qdrant

**Cause**: API key expired or invalid

**Solution**:
1. Check key in Qdrant Cloud dashboard
2. Generate new key if expired
3. Update `.env` on droplet:
   ```bash
   ssh root@45.55.173.72
   nano /opt/Dev-Tools/config/env/.env
   # Update QDRANT_API_KEY
   ```
4. Restart RAG service:
   ```bash
   cd /opt/Dev-Tools/deploy && docker compose up -d --force-recreate rag-context
   ```

### Issue: "Temporary failure in name resolution"

**Cause**: DNS resolution failure inside container

**Solution**:
1. Check internet connectivity on droplet
2. Verify QDRANT_URL is correct (not localhost)
3. Restart Docker DNS:
   ```bash
   docker compose restart
   ```

### Issue: Empty query results

**Cause**: Collection not indexed or wrong collection name

**Solution**:
1. List collections: `curl http://45.55.173.72:8007/collections`
2. Check vector count > 0
3. Re-index if needed:
   ```bash
   python support/scripts/rag/index_code_patterns.py
   ```

### Issue: Slow queries

**Cause**: Large result set or unoptimized embeddings

**Solution**:
1. Add `score_threshold` to filter low-relevance results
2. Reduce `limit` parameter
3. Check Qdrant Cloud metrics for bottlenecks

---

## Monitoring

### Grafana Dashboard
- URL: https://appsmithery.grafana.net
- Metrics: RAG query latency, Qdrant connection status

### Logs
```bash
# View RAG service logs
ssh root@45.55.173.72 "docker logs deploy-rag-context-1 --tail=100 -f"

# Filter for errors
ssh root@45.55.173.72 "docker logs deploy-rag-context-1 2>&1 | grep -i error"
```

### Health Monitoring
```bash
# Automated health check
curl -s http://45.55.173.72:8007/health | jq .

# Expected response:
{
  "status": "ok",
  "service": "rag-context-manager",
  "qdrant_status": "connected",
  "mcp_gateway_status": "connected"
}
```

---

## Maintenance

### Re-indexing Collections

**When to re-index:**
- After major code changes
- After Linear issue bulk updates
- When vectors seem outdated

**Full re-index:**
```bash
ssh root@45.55.173.72
cd /opt/Dev-Tools
export OPENAI_API_KEY="sk-proj-..."
export LINEAR_API_KEY="lin_oauth_..."

# Index all collections
python support/scripts/rag/index_code_patterns.py
python support/scripts/rag/index_issue_tracker.py
python support/scripts/rag/index_feature_specs.py
```

### Backup & Recovery

**Qdrant Cloud**: Automatic backups enabled

**Manual snapshot:**
```bash
curl -X POST "https://83b61795-7dbd-4477-890e-edce352a00e2.us-east4-0.gcp.cloud.qdrant.io/collections/code_patterns/snapshots" \
  -H "api-key: $QDRANT_API_KEY"
```

---

## Related Documentation

- **Architecture**: `support/docs/architecture/RAG_DOCUMENTATION_AGGREGATION.md`
- **Vector DB Config**: `config/rag/vectordb.config.yaml`
- **Indexing Config**: `config/rag/indexing.yaml`
- **RAG Service Code**: `shared/services/rag/main.py`
- **Copilot Instructions**: `.github/copilot-instructions.md` (RAG section)

---

## Changelog

### November 26, 2025 (DEV-184)
- ✅ Indexed code_patterns (505 vectors)
- ✅ Indexed issue_tracker (155 vectors)
- ✅ Indexed feature_specs (4 vectors)
- ✅ Created new non-expiring API key
- ✅ Fixed index_issue_tracker.py (NoneType comment handling)
- ✅ Fixed index_feature_specs.py (JSON parsing path, metadata keys)
- ✅ Updated production .env with new API key
- ✅ Memory optimization (2GB swap, container limits)
