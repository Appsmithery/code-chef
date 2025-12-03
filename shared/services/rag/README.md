# RAG Context Manager Service

Semantic search and context retrieval service for AI agents. Provides vector database integration with Qdrant Cloud and OpenAI embeddings.

## Overview

| Property       | Value                                             |
| -------------- | ------------------------------------------------- |
| **Port**       | 8007                                              |
| **Vector DB**  | Qdrant Cloud                                      |
| **Embeddings** | OpenAI `text-embedding-3-small` (1536 dimensions) |
| **Framework**  | FastAPI                                           |

## Quick Reference

```bash
# Health check
curl http://localhost:8007/health

# List collections
curl http://localhost:8007/collections

# Semantic search
curl -X POST http://localhost:8007/query \
  -H "Content-Type: application/json" \
  -d '{"query": "workflow patterns", "collection": "code_patterns", "n_results": 5}'

# Index documents
curl -X POST http://localhost:8007/index \
  -H "Content-Type: application/json" \
  -d '{"documents": ["content here"], "collection": "my_collection"}'
```

## Collections

| Collection      | Vectors | Description                         | Indexing Script                              |
| --------------- | ------- | ----------------------------------- | -------------------------------------------- |
| `code_patterns` | ~505    | Python AST extraction from codebase | `support/scripts/rag/index_code_patterns.py` |
| `issue_tracker` | ~155    | Linear issues                       | `support/scripts/rag/index_issue_tracker.py` |
| `feature_specs` | ~4      | Linear project descriptions         | `support/scripts/rag/index_feature_specs.py` |
| `vendor-docs`   | ~94     | API documentation                   | `support/scripts/rag/index_vendor_docs.py`   |
| `the-shop`      | ~460    | DigitalOcean knowledge base         | External sync                                |
| `task_context`  | 0       | Workflow events (future)            | N/A                                          |
| `agent_memory`  | 0       | Agent conversations (future)        | N/A                                          |

## Configuration

### Required Environment Variables

```bash
# Qdrant Cloud (production)
QDRANT_URL=https://83b61795-7dbd-4477-890e-edce352a00e2.us-east4-0.gcp.cloud.qdrant.io:6333
QDRANT_API_KEY=<full-jwt-token>  # Starts with eyJ..., non-expiring

# OpenAI Embeddings
OPENAI_API_KEY=sk-...
OPENAI_EMBEDDING_MODEL=text-embedding-3-small  # 1536 dimensions, $0.02/1M tokens

# Optional: MCP Gateway integration
MCP_GATEWAY_URL=http://gateway-mcp:8000
```

### Fallback Configuration (Development)

If `OPENAI_API_KEY` is not set, the service falls back to Ollama:

```bash
OLLAMA_URL=http://ollama:11434
OLLAMA_EMBEDDING_MODEL=nomic-embed-text
```

## API Endpoints

### `GET /health`

Health check with Qdrant and MCP Gateway connectivity status.

**Response:**

```json
{
  "status": "ok",
  "service": "rag-context-manager",
  "version": "1.0.0",
  "qdrant_status": "connected",
  "mcp_gateway_status": "connected"
}
```

### `POST /query`

Semantic search across a collection.

**Request:**

```json
{
  "query": "search text",
  "collection": "code_patterns",
  "n_results": 5,
  "metadata_filter": { "type": "function" } // optional
}
```

**Response:**

```json
{
  "query": "search text",
  "results": [
    {
      "id": "uuid",
      "content": "matched content",
      "metadata": { "source": "file.py", "type": "function" },
      "distance": 0.15,
      "relevance_score": 0.85
    }
  ],
  "collection": "code_patterns",
  "total_found": 5,
  "retrieval_time_ms": 45.2
}
```

### `POST /index`

Index new documents into a collection.

**Request:**

```json
{
  "documents": ["content 1", "content 2"],
  "metadatas": [{ "source": "file1.py" }, { "source": "file2.py" }],
  "ids": ["id1", "id2"], // optional, auto-generated if not provided
  "collection": "code_patterns"
}
```

### `GET /collections`

List all collections with document counts.

### `POST /query/mock`

Mock endpoint for testing without Qdrant connection.

## Indexing Scripts

All indexing scripts are in `support/scripts/rag/`:

```bash
# Index Python codebase (AST extraction)
python support/scripts/rag/index_code_patterns.py

# Index Linear issues
python support/scripts/rag/index_issue_tracker.py

# Index Linear projects
python support/scripts/rag/index_feature_specs.py

# Index vendor API docs
python support/scripts/rag/index_vendor_docs.py
```

### Re-indexing

To re-index a collection:

1. The indexing scripts use `upsert` operations (existing IDs are updated)
2. For full re-index, delete the collection first via Qdrant API

## Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Orchestrator   │────▶│  RAG Service     │────▶│  Qdrant Cloud   │
│  (port 8001)    │     │  (port 8007)     │     │  (external)     │
└─────────────────┘     └──────────────────┘     └─────────────────┘
                               │
                               ▼
                        ┌──────────────────┐
                        │  OpenAI API      │
                        │  (embeddings)    │
                        └──────────────────┘
```

## MCP Integration

The service logs queries and indexing operations to the MCP memory server for analytics:

- Query logging: tracks search patterns, collections accessed, result counts
- Indexing logging: tracks document counts per collection

## Troubleshooting

### Qdrant Connection Issues

```bash
# Check Qdrant health
curl http://localhost:8007/health

# Verify API key (should be full JWT, not truncated)
echo $QDRANT_API_KEY | head -c 20  # Should start with "eyJ"
```

### Embedding Errors

```bash
# Verify OpenAI API key
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY"
```

### Collection Not Found

Collections are auto-created on first index or query. If a collection is missing:

1. Run the appropriate indexing script
2. Or create manually via `/index` endpoint

## Development

```bash
# Run locally
cd shared/services/rag
pip install -r requirements.txt
python main.py

# Docker build
docker build -t rag-service .
docker run -p 8007:8007 --env-file ../../../config/env/.env rag-service
```

## Related Documentation

- [RAG Indexing Configuration](../../../config/rag/indexing.yaml)
- [Vector DB Schema](../../../config/rag/vectordb.config.yaml)
- [Copilot Instructions - RAG Section](../../../.github/copilot-instructions.md#rag-semantic-search-dev-184-completed-november-2025)
