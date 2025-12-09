# RAG-Powered Documentation Aggregation Strategy

**Status**: Ready to Implement  
**Priority**: High  
**Implementation Phase**: Quick Win (1-2 hours)  
**Approach**: Extend existing RAG service (no new infrastructure needed)

## Overview

Leverage existing RAG infrastructure (Qdrant Vector DB + RAG service on port 8007) to index vendor documentation for instant semantic search. **No new services required** - simply add documentation sources to existing configuration.

## Problem Statement

Current challenges with vendor documentation:

- **Scattered across multiple sources**: DigitalOcean, Linear, LangSmith, GitHub
- **Manual lookup required**: Developers must context-switch to find API details
- **Token-expensive**: Pasting full docs into LLM context wastes tokens
- **Stale knowledge**: Models lack recent API updates or vendor changes
- **No semantic search**: Can't find relevant sections with natural language queries

## Simplified Solution: Extend Existing RAG Service

**Infrastructure Already Available:**

- ✅ Qdrant Vector DB (running at Qdrant Cloud)
- ✅ RAG Context Service (port 8007)
- ✅ Embedding models configured
- ✅ MCP gateway for tool access

**Implementation Steps:**

1. **Add vendor doc sources** to `config/rag/indexing.yaml`
2. **Index documentation** via existing RAG service endpoints
3. **Query via MCP tools** already exposed by gateway
4. **Optional**: Schedule periodic re-indexing via cron/GitHub Actions

### Data Sources (Curated & Prioritized)

| Category                | Source                        | URL                                                                                            | Priority    | Update Frequency |
| ----------------------- | ----------------------------- | ---------------------------------------------------------------------------------------------- | ----------- | ---------------- |
| **LLM Inference**       | Gradient AI Platform          | `https://docs.digitalocean.com/products/gradient-ai-platform/`                                 | ✅ **High** | Weekly           |
|                         | Gradient Python SDK           | `https://raw.githubusercontent.com/digitalocean/gradient-python/main/README.md`                | ✅ **High** | Weekly           |
|                         | Gradient Serverless Inference | `https://docs.digitalocean.com/products/gradient-ai-platform/how-to/use-serverless-inference/` | ✅ **High** | Weekly           |
| **Project Management**  | Linear GraphQL API            | `https://linear.app/developers/graphql`                                                        | ✅ **High** | Monthly          |
|                         | Linear SDK Docs               | `https://linear.app/developers/sdk`                                                            | ✅ **High** | Monthly          |
|                         | Linear OAuth 2.0              | `https://linear.app/developers/oauth-2-0-authentication`                                       | ⏭️ Medium   | Monthly          |
|                         | Linear Agents API             | `https://linear.app/developers/agents`                                                         | ⏭️ Low      | As needed        |
| **Observability**       | LangSmith API Docs            | `https://api.smith.langchain.com/redoc`                                                        | ✅ **High** | Monthly          |
|                         | LangSmith SDK Reference       | `https://reference.langchain.com/python/langsmith/deployment/sdk/`                             | ⏭️ Medium   | Monthly          |
| **LangChain/LangGraph** | LangGraph Reference           | `https://reference.langchain.com/python/langgraph/`                                            | ✅ **High** | Weekly           |
|                         | LangChain Python Reference    | `https://reference.langchain.com/python/langchain/`                                            | ⏭️ Medium   | Weekly           |
|                         | LangChain MCP Docs            | `https://docs.langchain.com/mcp`                                                               | ✅ **High** | Weekly           |
| **Vector DB**           | Qdrant API Reference          | `https://api.qdrant.tech/api-reference`                                                        | ✅ **High** | Monthly          |
| **Infrastructure**      | DigitalOcean API              | `https://docs.digitalocean.com/reference/api/digitalocean/`                                    | ⏭️ Medium   | Monthly          |
|                         | Docker MCP Toolkit            | `https://docs.docker.com/ai/mcp-catalog-and-toolkit/toolkit/`                                  | ⏭️ Low      | As needed        |
|                         | Taskfile Schema               | `https://taskfile.dev/docs/reference/schema`                                                   | ⏭️ Low      | As needed        |

**Removed (Redundant/Low Value):**

- ~~`reference.langchain.com/python/deepagents`~~ - Rarely used
- ~~`github.com/langchain-ai/docs`~~ - GitHub repo, use official docs instead
- ~~`github.com/hfyydd/langgraphv`~~ - Community repo, not official
- ~~`docs.mermaidchart.com`~~ - Diagram syntax, not agent-relevant
- ~~`github.com/postmanlabs/postman-mcp-server`~~ - Not currently integrated
- ~~`docs.docker.com/ai/mcp-catalog-and-toolkit/hub-mcp/`~~ - Covered by main toolkit docs
- ~~`taskfile.dev/docs/reference/environment`~~ - Already in schema docs
- ~~`taskfile.dev/docs/reference/config`~~ - Already in schema docs
- ~~`taskfile.dev/docs/reference/cli`~~ - Already in schema docs

**Implementation Order:**

1. **Phase 1 (High Priority)**: Gradient AI, Linear GraphQL/SDK, LangSmith API, LangGraph, Qdrant, LangChain MCP (~6 sources)
2. **Phase 2 (Medium Priority)**: LangChain Python, LangSmith SDK, DigitalOcean API, Linear OAuth (~4 sources)
3. **Phase 3 (Low Priority)**: Docker MCP, Taskfile, Linear Agents (~3 sources)

## Implementation Guide

### Step 1: Update RAG Configuration (5 minutes)

Add vendor documentation sources to `config/rag/indexing.yaml`:

```yaml
# config/rag/indexing.yaml
sources:
  # Existing sources...

  # NEW: Vendor Documentation Sources (Phase 1 - High Priority)
  - name: "gradient-ai"
    type: "web"
    collection: "vendor-docs"
    urls:
      - "https://docs.digitalocean.com/products/gradient-ai-platform/"
      - "https://docs.digitalocean.com/products/gradient-ai-platform/how-to/use-serverless-inference/"
      - "https://raw.githubusercontent.com/digitalocean/gradient-python/main/README.md"
    chunk_size: 1000
    overlap: 200
    tags: ["digitalocean", "gradient-ai", "llm", "inference"]

  - name: "linear-api"
    type: "web"
    collection: "vendor-docs"
    urls:
      - "https://linear.app/developers/graphql"
      - "https://linear.app/developers/sdk"
    chunk_size: 1500
    overlap: 200
    tags: ["linear", "graphql", "sdk", "project-management"]

  - name: "langsmith-api"
    type: "web"
    collection: "vendor-docs"
    urls:
      - "https://api.smith.langchain.com/redoc"
    chunk_size: 1000
    overlap: 200
    tags: ["langsmith", "api", "observability", "tracing"]

  - name: "langgraph-reference"
    type: "web"
    collection: "vendor-docs"
    urls:
      - "https://reference.langchain.com/python/langgraph/"
    chunk_size: 1200
    overlap: 200
    tags: ["langgraph", "langchain", "agents", "workflows"]

  - name: "langchain-mcp"
    type: "web"
    collection: "vendor-docs"
    urls:
      - "https://docs.langchain.com/mcp"
    chunk_size: 1000
    overlap: 200
    tags: ["langchain", "mcp", "protocol", "tools"]

  - name: "qdrant-api"
    type: "web"
    collection: "vendor-docs"
    urls:
      - "https://api.qdrant.tech/api-reference"
    chunk_size: 1200
    overlap: 200
    tags: ["qdrant", "vector-db", "api", "search"]

  # Phase 2 - Medium Priority (add later)
  - name: "langchain-python"
    type: "web"
    collection: "vendor-docs"
    urls:
      - "https://reference.langchain.com/python/langchain/"
    chunk_size: 1200
    overlap: 200
    tags: ["langchain", "python", "reference"]
    enabled: false # Enable after Phase 1 validation

  - name: "digitalocean-api"
    type: "web"
    collection: "vendor-docs"
    urls:
      - "https://docs.digitalocean.com/reference/api/digitalocean/"
    chunk_size: 1000
    overlap: 200
    tags: ["digitalocean", "api", "infrastructure"]
    enabled: false

# Qdrant configuration
qdrant:
  url: ${QDRANT_CLUSTER_ENDPOINT}
  api_key: ${QDRANT_CLUSTER_KEY}
  collections:
    - name: "vendor-docs"
      vector_size: 1536 # text-embedding-ada-002 dimensions
      distance: "cosine"
```

### Step 2: Index Documentation (30-60 minutes one-time)

Trigger indexing via existing RAG service:

```bash
# Phase 1: Core APIs (High Priority - Index First)
curl -X POST http://45.55.173.72:8007/index \
  -H "Content-Type: application/json" \
  -d '{"source": "gradient-ai"}'

curl -X POST http://45.55.173.72:8007/index \
  -H "Content-Type: application/json" \
  -d '{"source": "linear-api"}'

curl -X POST http://45.55.173.72:8007/index \
  -H "Content-Type: application/json" \
  -d '{"source": "langsmith-api"}'

curl -X POST http://45.55.173.72:8007/index \
  -H "Content-Type: application/json" \
  -d '{"source": "langgraph-reference"}'

curl -X POST http://45.55.173.72:8007/index \
  -H "Content-Type: application/json" \
  -d '{"source": "langchain-mcp"}'

curl -X POST http://45.55.173.72:8007/index \
  -H "Content-Type: application/json" \
  -d '{"source": "qdrant-api"}'
```

**Expected Response:**

```json
{
  "status": "success",
  "source": "gradient-api-docs",
  "chunks_indexed": 147,
  "collection": "vendor-docs",
  "duration_seconds": 45.3
}
```

### Step 3: Query Vendor Documentation (Immediate Use)

Agents can now query via existing RAG endpoints:

```bash
# Query Gradient documentation
curl -X POST http://45.55.173.72:8007/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "How do I use streaming with Gradient AI?",
    "collection": "vendor-docs",
    "top_k": 3,
    "filter": {"tags": ["gradient-ai"]}
  }'
```

**Response:**

```json
{
  "results": [
    {
      "text": "To enable streaming responses, set stream=True in your completion call...",
      "score": 0.89,
      "metadata": {
        "source": "gradient-api-docs",
        "url": "https://docs.digitalocean.com/products/gradient-ai-platform/...",
        "tags": ["gradient-ai", "api"]
      }
    }
  ]
}
```

### Step 4: Integrate with Orchestrator (15 minutes)

Update orchestrator to inject vendor docs when relevant:

```python
# agent_orchestrator/main.py

@app.post("/orchestrate")
async def orchestrate_task(request: TaskRequest):
    """Orchestrate task with optional vendor doc context."""

    # Detect vendor mentions
    vendor_keywords = {
        "gradient": ["gradient", "digitalocean", "llm", "model", "inference"],
        "linear": ["linear", "issue", "project", "roadmap", "graphql"],
        "langsmith": ["langsmith", "trace", "monitor", "evaluate"]
    }

    relevant_tags = []
    for vendor, keywords in vendor_keywords.items():
        if any(kw in request.description.lower() for kw in keywords):
            relevant_tags.append(vendor)

    # Query RAG if vendor context needed
    docs_context = ""
    if relevant_tags:
        try:
            response = await httpx.post(
                "http://rag-context:8007/query",
                json={
                    "query": request.description,
                    "collection": "vendor-docs",
                    "top_k": 2,
                    "filter": {"tags": relevant_tags}
                },
                timeout=5.0
            )
            if response.status_code == 200:
                results = response.json()["results"]
                docs_context = "\n\n".join([
                    f"**{r['metadata']['source']}**: {r['text'][:300]}..."
                    for r in results
                ])
        except Exception as e:
            logger.warning(f"RAG query failed: {e}")

    # Inject into LLM prompt
    enhanced_prompt = request.description
    if docs_context:
        enhanced_prompt = f"""
Task: {request.description}

Relevant API Documentation:
{docs_context}

Consider the documentation above when planning this task.
"""

    # Continue with normal orchestration...
    response = await gradient_client.complete(
        prompt=enhanced_prompt,
        temperature=0.3
    )
```

## Benefits

1. **Zero New Infrastructure**: Uses existing RAG service (port 8007) and Qdrant
2. **Instant Context**: Agents get vendor docs injected into LLM context automatically
3. **Cost Efficient**: RAG reduces token usage vs. pasting full docs (saves ~$0.50/1K tasks)
4. **Semantic Search**: Find relevant sections even with imprecise queries
5. **Multi-Source**: Query across DigitalOcean, Linear, LangSmith simultaneously
6. **Tag-Based Filtering**: Filter by vendor, API type, language
7. **Fast Implementation**: < 2 hours total (config + indexing + integration)

## Usage Examples

### Example 1: Query Gradient API Details

```bash
# Agent asks: "What Gradient models support streaming?"
curl -X POST http://45.55.173.72:8007/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "streaming support gradient models",
    "collection": "vendor-docs",
    "top_k": 2,
    "filter": {"tags": ["gradient-ai"]}
  }'
```

**Response:**

```json
{
  "results": [
    {
      "text": "Streaming is supported for llama-3.1-70b, llama-3.1-8b, and codellama models. Set stream=True in your completion request...",
      "score": 0.91,
      "metadata": { "source": "gradient-api-docs", "url": "https://..." }
    }
  ]
}
```

### Example 2: Orchestrator Auto-Injects Context

```bash
# User submits task mentioning Linear
curl -X POST http://45.55.173.72:8001/orchestrate \
  -H "Content-Type: application/json" \
  -d '{
    "description": "Create a Linear issue for Phase 7 completion",
    "user_id": "alex"
  }'

# Orchestrator detects "Linear" keyword → queries RAG → injects GraphQL docs into LLM prompt
```

### Example 3: Manual Re-Index (Weekly Maintenance)

```bash
# Re-index all vendor docs (run weekly via cron)
curl -X POST http://45.55.173.72:8007/index \
  -H "Content-Type: application/json" \
  -d '{"source": "gradient-api-docs"}'

curl -X POST http://45.55.173.72:8007/index \
  -H "Content-Type: application/json" \
  -d '{"source": "linear-graphql"}'
```

## Implementation Checklist (1-2 Hours)

### Phase 1: Configuration (5 minutes)

- [ ] Update `config/rag/indexing.yaml` with vendor doc sources
- [ ] Verify RAG service environment variables (`QDRANT_CLUSTER_ENDPOINT`, etc.)

### Phase 2: Initial Indexing (30-60 minutes)

- [ ] Index Gradient AI docs (10 min)
- [ ] Index Linear API docs (10 min)
- [ ] Index LangSmith API docs (5 min)
- [ ] Index LangGraph reference (10 min)
- [ ] Index LangChain MCP docs (5 min)
- [ ] Index Qdrant API docs (10 min)
- [ ] Verify Qdrant collection created: `curl http://45.55.173.72:6333/collections/vendor-docs`
- [ ] Test query: `curl -X POST http://45.55.173.72:8007/query -d '{"query":"gradient streaming"}'`

### Phase 3: Orchestrator Integration (15 minutes)

- [ ] Add vendor keyword detection to orchestrator
- [ ] Add RAG query before LLM prompt construction
- [ ] Test with sample task mentioning "Gradient"

### Phase 4: Validation (10 minutes)

- [ ] Query RAG directly: verify results
- [ ] Test orchestrator task with vendor mention
- [ ] Check LangSmith traces for RAG context injection

### Phase 5: Automation (Optional, 30 minutes)

- [ ] Create GitHub Action to re-index weekly
- [ ] Add Prometheus metrics for query latency
- [ ] Document RAG query patterns for other agents

## Success Metrics

After implementation, measure:

- **Query Accuracy**: >85% relevant results in top-2 RAG queries (manually test 20 queries)
- **Performance**: <500ms query latency (check RAG service logs)
- **Adoption**: Orchestrator uses RAG context in >30% of tasks mentioning vendors
- **Token Savings**: Estimate ~200-500 tokens saved per vendor-related task
- **Coverage**: 3 priority vendor docs indexed (Gradient, Linear, LangSmith)

## Maintenance Schedule

- **Weekly**: Re-index Gradient docs (APIs may update)
- **Monthly**: Re-index Linear and LangSmith docs
- **Quarterly**: Review RAG query logs, add new sources if needed
- **As-Needed**: Re-index when major vendor API changes announced

## Optional Enhancements (Future)

Once basic implementation is validated:

- **GitHub Action**: Automate weekly re-indexing via scheduled workflow
- **Metrics Dashboard**: Add RAG query stats to Grafana (query count, latency, sources)
- **Feedback Loop**: Log when agents get irrelevant results, tune chunking strategy
- **More Sources**: Add MCP protocol spec, AWS SDK docs, Docker API reference
- **Cross-Agent Access**: Expose RAG query endpoint via MCP tools for all agents

## Dependencies

- ✅ **Already Exist**: Qdrant Vector DB, RAG service (port 8007), embedding models
- 🆕 **New Requirements**: None - use existing infrastructure
- 📦 **Optional**: BeautifulSoup4 (if RAG service needs better HTML parsing)

## Why This Approach Works

1. **Leverages Existing Infrastructure**: No new services, containers, or MCP servers
2. **Minimal Code Changes**: < 30 lines added to orchestrator
3. **Fast Implementation**: Configuration-first approach (YAML + API calls)
4. **Low Maintenance**: Weekly cron job or manual re-indexing sufficient
5. **Measurable Impact**: Easy to A/B test (with vs. without RAG context)
6. **Incremental**: Start with 3 sources, expand only if proven valuable

## Related Documentation

- **RAG Service**: `shared/services/rag/README.md` (check for existing endpoints)
- **Qdrant Config**: `config/rag/vectordb.config.yaml`
- **Indexing Config**: `config/rag/indexing.yaml`
- **Orchestrator**: `agent_orchestrator/main.py`

---

**Next Step**: Update `config/rag/indexing.yaml` and run initial indexing (30-60 minutes total).
