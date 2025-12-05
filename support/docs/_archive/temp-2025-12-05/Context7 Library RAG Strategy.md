# Context7 Library ID RAG Cache Strategy

### Current State

Your agents use Context7's two tools:

- **`resolve-library-id`**: Converts library name → specific library ID (e.g., "langchain" → `/langchain-ai/langchain/libs/langchain`)
- **`get-library-docs`**: Fetches documentation using the resolved library ID

### The Problem

Every time an agent needs library docs (e.g., LangChain, FastAPI, Pydantic), it must:

1. Call `resolve-library-id` with the library name → **~500-1000 tokens per call**
2. Wait for Context7 API response
3. Then call `get-library-docs` with the resolved ID

For frequently-used libraries (LangChain, FastAPI, Docker, etc.), this resolution step is **redundant and expensive**.

### Proposed Solution: Library ID Registry + RAG Cache

```
┌─────────────────────────────────────────────────────────────────┐
│                    CURRENT WORKFLOW (Expensive)                 │
├─────────────────────────────────────────────────────────────────┤
│  Agent → resolve-library-id("langchain") → Context7 API        │
│       → get-library-docs("/langchain-ai/...") → Context7 API   │
│  Cost: 2 API calls + ~1500 tokens per library lookup           │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                  OPTIMIZED WORKFLOW (Cached)                    │
├─────────────────────────────────────────────────────────────────┤
│  Agent → RAG Query("langchain patterns") → Qdrant              │
│       ↳ Hit? Return cached ID + relevant doc chunks            │
│       ↳ Miss? resolve-library-id → cache result → Qdrant       │
│  Cost: 1 vector query (~50 tokens) OR 1 API call + cache       │
└─────────────────────────────────────────────────────────────────┘
```

### Viability Assessment

| Factor                    | Assessment            | Notes                                       |
| ------------------------- | --------------------- | ------------------------------------------- |
| **Token Savings**         | ✅ **High**           | 80-90% reduction for repeat library lookups |
| **Implementation Effort** | ⚠️ **Medium**         | New collection, indexing script, middleware |
| **Qdrant Infrastructure** | ✅ **Already exists** | Just add `library_registry` collection      |
| **Maintenance**           | ⚠️ **Low-Medium**     | Library IDs rarely change; monthly refresh  |
| **Risk**                  | ✅ **Low**            | Fallback to live Context7 on cache miss     |

### Recommended Architecture

```yaml
# New collection in config/rag/vectordb.config.yaml
collections:
  - name: "library_registry"
    description: "Context7 library ID cache with semantic aliases"
    schema:
      library_name: string # "langchain", "fastapi"
      library_id: string # "/langchain-ai/langchain/libs/langchain"
      aliases: string[] # ["lc", "langchain-core", "langchain python"]
      category: string # "ai-ml", "web-framework", "devops"
      last_verified: timestamp # TTL for cache refresh
      usage_count: int # Prioritize frequently-used libraries
```

### Implementation Steps

1. **Create Library Registry Collection** - Add to Qdrant with 50-100 commonly-used libraries pre-seeded
2. **Build Indexing Script** - `support/scripts/rag/index_library_registry.py` that:
   - Calls `resolve-library-id` for each library in seed list
   - Embeds library name + aliases for semantic matching
   - Stores resolved ID with TTL metadata
3. **Add RAG Middleware** - Intercept Context7 calls, check cache first:
   ```python
   async def get_library_docs_cached(library_name: str) -> str:
       # 1. Semantic search in library_registry
       cached = await rag_client.query("library_registry", library_name, limit=1)
       if cached and cached.score > 0.9:
           library_id = cached.payload["library_id"]
       else:
           # 2. Cache miss - resolve and cache
           library_id = await context7.resolve_library_id(library_name)
           await rag_client.upsert("library_registry", {...})
       # 3. Fetch docs with cached/resolved ID
       return await context7.get_library_docs(library_id)
   ```
4. **Seed Common Libraries** - Pre-populate with your stack:
   - AI/ML: langchain, langgraph, langsmith, openai, anthropic, huggingface
   - Web: fastapi, pydantic, httpx, requests, aiohttp
   - DevOps: docker, kubernetes, terraform, github-actions
   - Data: pandas, numpy, sqlalchemy, asyncpg

### Token Savings Estimate

| Scenario                 | Current Cost  | With Cache   | Savings        |
| ------------------------ | ------------- | ------------ | -------------- |
| 10 LangChain lookups/day | 15,000 tokens | 500 tokens   | **97%**        |
| 5 FastAPI lookups/day    | 7,500 tokens  | 250 tokens   | **97%**        |
| Cache miss (new library) | 1,500 tokens  | 1,600 tokens | -7% (one-time) |

### Recommendation: **Proceed with Implementation**

**Value**: High - directly reduces token costs for a frequently-used pattern  
**Effort**: Medium - leverages existing Qdrant infrastructure  
**Priority**: After LangSmith trace evaluation (this supports measuring the savings)

### Next Steps (When Ready)

1. Add `library_registry` collection to vectordb.config.yaml
2. Create seed list of 50-100 libraries in `config/rag/library-seed.yaml`
3. Build indexing script `support/scripts/rag/index_library_registry.py`
4. Add caching middleware to Context7 tool calls in agent base class
5. Add LangSmith custom metric to track cache hit rate
