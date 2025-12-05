# Context7 Tools Usage Guide

## When to Use

- Looking up library documentation (LangChain, FastAPI, Pydantic, etc.)
- Resolving library IDs for documentation queries
- Finding API patterns and code examples from vendor docs
- Understanding how to use third-party libraries

## Available Tools (context7 MCP server)

### `resolve-library-id`

```json
{
  "libraryName": "langchain"
}
```

**Returns**: Resolved library ID for documentation lookup.

**Use when**: Before calling `get-library-docs`, you need the official library ID.

**Common library mappings** (cached in RAG):

- `langchain` → LangChain core + ecosystem docs
- `fastapi` → FastAPI web framework
- `pydantic` → Pydantic data validation
- `docker` → Docker CLI and compose
- `kubernetes` → Kubernetes API and kubectl
- `terraform` → Terraform providers and resources
- `pytest` → pytest testing framework
- `openai` → OpenAI API client
- `anthropic` → Anthropic Claude API
- `qdrant` → Qdrant vector database

### `get-library-docs`

```json
{
  "libraryId": "/langchain/python/langchain-ai",
  "topic": "tool binding"
}
```

**Returns**: Relevant documentation snippets for the topic.

**Use when**: You need to understand how a library works or find code examples.

**Example topics**:

- `"tool binding"` - How to bind tools to LLMs
- `"chain composition"` - Building LangChain chains
- `"async patterns"` - Async/await usage
- `"error handling"` - Exception patterns
- `"configuration"` - Setup and configuration

### `search-library`

```json
{
  "query": "langchain memory management",
  "maxResults": 5
}
```

**Returns**: Search results across all indexed library documentation.

**Use when**: You need to find documentation without knowing the exact library.

## Integration with RAG Cache

The Context7 cache (`shared/lib/context7_cache.py`) provides:

1. **Local RAG lookup first**: Checks `library_registry` collection in Qdrant
2. **Cache hit**: Returns cached library ID (no API call needed)
3. **Cache miss**: Falls back to Context7 MCP for resolution
4. **In-memory cache**: 1-hour TTL for repeated lookups

**Token savings**: 80-90% reduction by avoiding repeated library ID resolutions.

## Usage Patterns

### Pattern 1: Quick Library Lookup

```
Task: "How do I use LangChain agents?"

1. resolve-library-id("langchain")
2. get-library-docs(libraryId, topic="agents")
```

### Pattern 2: Cross-Library Research

```
Task: "Compare FastAPI and Flask for async support"

1. resolve-library-id("fastapi")
2. resolve-library-id("flask")
3. get-library-docs(fastApiId, topic="async")
4. get-library-docs(flaskId, topic="async")
```

### Pattern 3: Cached Lookup (via code)

```python
from shared.lib.context7_cache import Context7CacheClient

cache = Context7CacheClient()
library_id = await cache.resolve_library_id("langchain")
# First call: RAG lookup + potential fallback
# Subsequent calls: In-memory cache (instant)
```

## Best Practices

1. **Use RAG cache for common libraries**: 56 libraries pre-indexed
2. **Be specific with topics**: "tool binding" is better than "tools"
3. **Batch related lookups**: Resolve all library IDs before fetching docs
4. **Check cache first**: Use `context7_cache.py` for programmatic access
5. **Fallback gracefully**: If Context7 is unavailable, use web search

## Indexed Libraries (library_registry collection)

**AI/ML**: langchain, openai, anthropic, huggingface, pytorch, tensorflow, scikit-learn
**Web Frameworks**: fastapi, flask, django, nextjs, react, vue, express, nestjs
**DevOps**: docker, kubernetes, terraform, ansible, prometheus, grafana
**Data**: pandas, numpy, postgresql, mongodb, redis, elasticsearch, qdrant
**Testing**: pytest, playwright, jest, cypress
**Utilities**: pydantic, httpx, aiohttp, requests, typer, click, rich
