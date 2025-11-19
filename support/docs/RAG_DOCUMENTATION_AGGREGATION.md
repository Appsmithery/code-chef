# RAG-Powered Documentation Aggregation Strategy

**Status**: Planned  
**Priority**: Medium  
**Implementation Phase**: Future Enhancement

## Overview

Leverage existing RAG infrastructure (Qdrant Vector DB + embedding models) to aggregate and index external vendor documentation for instant semantic search and context injection into agent workflows.

## Problem Statement

Current challenges with vendor documentation:

- **Scattered across multiple sources**: DigitalOcean, Linear, LangSmith, AWS, GitHub
- **Manual lookup required**: Developers must context-switch to find API details
- **Token-expensive**: Pasting full docs into LLM context wastes tokens
- **Stale knowledge**: Models lack recent API updates or vendor changes
- **No semantic search**: Can't find relevant sections with natural language queries

## Proposed Solution

### Architecture: MCP Documentation Sync Server

Create a dedicated MCP server that:

1. **Fetches** vendor documentation via HTTP scraping/API calls
2. **Chunks** content into semantic segments (1000 tokens with 200 overlap)
3. **Embeds** using DigitalOcean's `text-embedding-ada-002` model
4. **Indexes** into Qdrant `vendor-docs` collection
5. **Syncs** on schedule (daily cron) or manual trigger
6. **Queries** via semantic search for agent context injection

### Data Sources (Initial)

| Vendor                   | Source Type           | Update Frequency | Priority |
| ------------------------ | --------------------- | ---------------- | -------- |
| DigitalOcean Gradient AI | Web scraping + GitHub | Daily            | **High** |
| Linear GraphQL API       | GitHub schema file    | Weekly           | **High** |
| LangSmith SDK            | Docs site scraping    | Weekly           | Medium   |
| MCP Protocol Spec        | GitHub markdown       | As needed        | Medium   |
| AWS SDK (Python)         | Read the Docs API     | Weekly           | Low      |

### Technical Implementation

#### 1. MCP Server: `documentation-sync`

```python
"""
MCP Server: Documentation Sync

Automatically ingests and indexes vendor documentation into Qdrant for RAG queries.
"""

import asyncio
import httpx
from typing import List, Dict
from qdrant_client import QdrantClient
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.embeddings import OpenAIEmbeddings

class DocumentationSyncServer:
    """Syncs external documentation into vector DB."""

    SOURCES = {
        "digitalocean-gradient": {
            "base_url": "https://docs.digitalocean.com/products/gradient-ai-platform/",
            "pages": [
                "details/models/",
                "how-to/use-serverless-inference/",
                "reference/api/",
                "getting-started/quickstart/"
            ],
            "github_fallback": "https://raw.githubusercontent.com/digitalocean/gradient-python/main/api.md",
            "collection": "vendor-docs",
            "tags": ["digitalocean", "gradient-ai", "llm", "serverless"]
        },
        "linear-graphql": {
            "github_schema": "https://raw.githubusercontent.com/linear/linear/main/packages/sdk/src/schema.graphql",
            "docs_url": "https://developers.linear.app/docs/graphql/working-with-the-graphql-api",
            "collection": "vendor-docs",
            "tags": ["linear", "graphql", "project-management", "api"]
        },
        "langsmith-sdk": {
            "base_url": "https://docs.smith.langchain.com/",
            "pages": [
                "tracing",
                "evaluation",
                "monitoring",
                "how_to_guides/tracing/trace_with_langchain"
            ],
            "collection": "vendor-docs",
            "tags": ["langsmith", "langchain", "observability", "tracing"]
        },
        "mcp-protocol": {
            "github_docs": "https://raw.githubusercontent.com/modelcontextprotocol/specification/main/README.md",
            "collection": "vendor-docs",
            "tags": ["mcp", "protocol", "tools", "context"]
        }
    }

    def __init__(self, qdrant_url: str, qdrant_api_key: str):
        self.qdrant = QdrantClient(url=qdrant_url, api_key=qdrant_api_key)
        self.embeddings = OpenAIEmbeddings()  # or use Gradient embeddings
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            separators=["\n## ", "\n### ", "\n#### ", "\n\n", "\n", " "]
        )

    async def sync_source(self, source_name: str) -> Dict:
        """Fetch and index documentation from a source."""
        source = self.SOURCES[source_name]
        docs_indexed = 0
        errors = []

        async with httpx.AsyncClient(timeout=30.0) as client:
            for page in source.get("pages", []):
                try:
                    url = f"{source['base_url']}{page}"
                    response = await client.get(url)
                    response.raise_for_status()
                    content = response.text

                    # Extract main content (strip HTML if needed)
                    from bs4 import BeautifulSoup
                    soup = BeautifulSoup(content, 'html.parser')
                    text = soup.get_text(separator="\n", strip=True)

                    # Split into chunks
                    chunks = self.text_splitter.split_text(text)

                    # Generate embeddings and upsert
                    for i, chunk in enumerate(chunks):
                        embedding = self.embeddings.embed_query(chunk)
                        self.qdrant.upsert(
                            collection_name=source["collection"],
                            points=[{
                                "id": f"{source_name}-{page.replace('/', '-')}-{i}",
                                "vector": embedding,
                                "payload": {
                                    "text": chunk,
                                    "source": source_name,
                                    "url": url,
                                    "page": page,
                                    "tags": source["tags"],
                                    "indexed_at": datetime.utcnow().isoformat()
                                }
                            }]
                        )
                        docs_indexed += 1

                except Exception as e:
                    errors.append(f"{page}: {str(e)}")

        return {
            "source": source_name,
            "chunks_indexed": docs_indexed,
            "errors": errors,
            "status": "success" if not errors else "partial"
        }

    async def query_docs(
        self,
        query: str,
        source_filter: List[str] = None,
        limit: int = 5
    ) -> List[Dict]:
        """Query indexed documentation with semantic search."""
        query_embedding = self.embeddings.embed_query(query)

        filter_conditions = None
        if source_filter:
            filter_conditions = {
                "must": [{"key": "source", "match": {"any": source_filter}}]
            }

        results = self.qdrant.search(
            collection_name="vendor-docs",
            query_vector=query_embedding,
            limit=limit,
            query_filter=filter_conditions
        )

        return [
            {
                "text": hit.payload["text"],
                "url": hit.payload["url"],
                "source": hit.payload["source"],
                "tags": hit.payload["tags"],
                "relevance_score": hit.score
            }
            for hit in results
        ]


# MCP Tool Definitions
async def sync_vendor_docs(source: str) -> str:
    """Sync vendor documentation into RAG."""
    server = DocumentationSyncServer(
        qdrant_url=os.getenv("QDRANT_CLUSTER_ENDPOINT"),
        qdrant_api_key=os.getenv("QDRANT_CLUSTER_KEY")
    )
    result = await server.sync_source(source)
    return json.dumps(result, indent=2)


async def query_vendor_docs(query: str, sources: List[str] = None) -> str:
    """Query vendor documentation via RAG."""
    server = DocumentationSyncServer(
        qdrant_url=os.getenv("QDRANT_CLUSTER_ENDPOINT"),
        qdrant_api_key=os.getenv("QDRANT_CLUSTER_KEY")
    )
    results = await server.query_docs(query, sources)

    formatted = []
    for r in results:
        formatted.append(
            f"**Source:** {r['source']} ({r['url']})\n"
            f"**Relevance:** {r['relevance_score']:.2f}\n"
            f"**Tags:** {', '.join(r['tags'])}\n\n"
            f"{r['text']}\n"
            f"{'='*80}"
        )

    return "\n\n".join(formatted)
```

#### 2. Orchestrator Integration

Inject vendor docs into LLM context when relevant:

```python
@app.post("/orchestrate")
async def orchestrate_task(request: TaskRequest):
    """Enhanced orchestrator with RAG-powered vendor docs."""

    # Detect if task requires vendor documentation
    vendor_keywords = {
        "gradient": ["gradient", "digitalocean", "llm", "model", "inference"],
        "linear": ["linear", "issue", "project", "roadmap", "graphql"],
        "langsmith": ["langsmith", "trace", "monitor", "evaluate"]
    }

    relevant_sources = []
    for source, keywords in vendor_keywords.items():
        if any(kw in request.description.lower() for kw in keywords):
            relevant_sources.append(source)

    # Query RAG if relevant sources detected
    docs_context = ""
    if relevant_sources:
        docs_context = await mcp_client.call_tool(
            "documentation-sync",
            "query_vendor_docs",
            {
                "query": request.description,
                "sources": relevant_sources,
                "limit": 3
            }
        )

    # Inject docs into LLM prompt
    system_prompt = """You are an expert DevOps orchestrator with access to vendor documentation.
Use the provided documentation context to make accurate technical decisions."""

    if docs_context:
        enhanced_prompt = f"""
Task: {request.description}

Relevant Vendor Documentation:
{docs_context}

Decompose this task considering the documentation above.
"""
    else:
        enhanced_prompt = request.description

    response = await gradient_client.complete(
        prompt=enhanced_prompt,
        system_prompt=system_prompt,
        temperature=0.3
    )

    # ...rest of orchestration logic...
```

#### 3. Docker Compose Service

```yaml
documentation-sync:
  build:
    context: ..
    dockerfile: shared/mcp/servers/documentation-sync/Dockerfile
  container_name: documentation-sync
  environment:
    - QDRANT_CLUSTER_ENDPOINT=${QDRANT_CLUSTER_ENDPOINT}
    - QDRANT_CLUSTER_KEY=${QDRANT_CLUSTER_KEY}
    - GRADIENT_MODEL_ACCESS_KEY=${GRADIENT_MODEL_ACCESS_KEY}
    - GRADIENT_MODEL=text-embedding-ada-002
    - LOG_LEVEL=info
  networks:
    - devtools-network
  restart: unless-stopped
  volumes:
    - ./cron.d/doc-sync:/etc/cron.d/doc-sync:ro
  # Run sync daily at 2 AM UTC
  entrypoint: ["crond", "-f", "-d", "8"]
```

#### 4. Cron Schedule

```bash
# /etc/cron.d/doc-sync
0 2 * * * root python /app/sync_all.py >> /var/log/doc-sync.log 2>&1
```

### Benefits

1. **Instant Context**: Agents get vendor docs injected into LLM context automatically
2. **Always Up-to-Date**: Scheduled syncs keep documentation fresh (daily/weekly)
3. **Multi-Source**: Query across DigitalOcean, Linear, LangSmith, AWS, etc.
4. **Cost Efficient**: RAG reduces token usage vs. pasting full docs
5. **Semantic Search**: Find relevant sections even with imprecise queries
6. **Version Tracking**: Track when docs were last indexed
7. **Tag-Based Filtering**: Filter by vendor, API type, language, etc.

### Usage Examples

#### Manual Sync

```bash
# Sync DigitalOcean Gradient docs
curl -X POST http://localhost:8000/tools/documentation-sync/sync_vendor_docs \
  -H "Content-Type: application/json" \
  -d '{"source": "digitalocean-gradient"}'

# Response:
{
  "source": "digitalocean-gradient",
  "chunks_indexed": 247,
  "errors": [],
  "status": "success"
}
```

#### Query from Orchestrator

```bash
# Agent automatically queries docs when task mentions Gradient
curl -X POST http://localhost:8001/orchestrate \
  -H "Content-Type: application/json" \
  -d '{
    "description": "How do I use streaming with Gradient AI?",
    "agent_type": "feature-dev"
  }'

# Orchestrator injects relevant docs before LLM call
```

#### Direct RAG Query

```bash
curl -X POST http://localhost:8000/tools/documentation-sync/query_vendor_docs \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What models are available for serverless inference?",
    "sources": ["digitalocean-gradient"],
    "limit": 3
  }'
```

## Implementation Roadmap

### Phase 1: Core Infrastructure (Week 1)

- [ ] Create `documentation-sync` MCP server
- [ ] Implement web scraping + GitHub fetching
- [ ] Set up Qdrant `vendor-docs` collection
- [ ] Add embedding generation (Gradient or OpenAI)
- [ ] Basic sync/query MCP tools

### Phase 2: Source Integration (Week 2)

- [ ] DigitalOcean Gradient AI docs
- [ ] Linear GraphQL schema + docs
- [ ] LangSmith tracing docs
- [ ] MCP protocol specification

### Phase 3: Orchestrator Integration (Week 3)

- [ ] Auto-detect vendor mentions in tasks
- [ ] Inject RAG results into LLM context
- [ ] Add confidence scoring for doc relevance
- [ ] Implement caching for frequent queries

### Phase 4: Automation & Monitoring (Week 4)

- [ ] Cron-based scheduled syncs
- [ ] Webhook triggers for doc updates
- [ ] Sync status dashboard
- [ ] Prometheus metrics (docs indexed, query latency)
- [ ] Alerting for stale/failed syncs

## Success Metrics

- **Coverage**: 80%+ of vendor API surface indexed
- **Freshness**: Docs synced within 24 hours of vendor updates
- **Accuracy**: 90%+ relevant results in top-3 RAG queries
- **Performance**: <500ms query latency
- **Adoption**: 50%+ of orchestration tasks use vendor docs

## Future Enhancements

- **Multi-modal docs**: Index code examples, diagrams, API schemas separately
- **Change detection**: Track vendor doc changes and notify agents
- **Versioned docs**: Maintain historical versions (e.g., API v1 vs v2)
- **Interactive learning**: Agents provide feedback on doc relevance
- **Cross-vendor linking**: Detect relationships between vendor docs

## Dependencies

- **Existing**: Qdrant Vector DB, embedding models, MCP gateway
- **New**: BeautifulSoup4 (HTML parsing), httpx (async HTTP), cron (scheduling)

## Notes

- This approach transforms RAG infrastructure into a **documentation aggregation layer**
- Reduces dependency on manual lookups and ChatGPT for vendor-specific questions
- Makes agents "self-documenting" by always having latest API references
- Can extend to internal docs, runbooks, and architectural decision records (ADRs)

## Related Documents

- `support/docs/RAG_CONTEXT_SERVICE.md` - Existing RAG implementation
- `config/rag/indexing.yaml` - Vector DB configuration
- `shared/mcp/servers/` - MCP server directory structure
