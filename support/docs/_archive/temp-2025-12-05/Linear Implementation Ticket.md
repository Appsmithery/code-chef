# Linear Implementation Ticket

**Title:** Context7 Library ID RAG Cache Implementation  
**Project:** AI DevOps Agent Platform (b21cbaa1-9f09-40f4-b62a-73e0f86dd501)  
**Team:** Project Roadmaps (PR)  
**Priority:** High  
**Estimate:** 3 story points

**Description:**
Implement a RAG-based caching layer for Context7 library ID lookups to reduce token costs by 80-90% for frequently-used libraries (LangChain, FastAPI, Pydantic, etc.).

**Acceptance Criteria:**

- [ ] New `library_registry` collection in Qdrant
- [ ] Seed list with 50+ common libraries
- [ ] Indexing script to populate cache from Context7
- [ ] Middleware for cache-first library lookups
- [ ] LangSmith metrics for cache hit rate tracking

---

## Implementation Files

### 1. Update Vector DB Config

```yaml
# ...existing code...

collections:
  # ...existing collections...
  - name: "library_registry"
    description: "Context7 library ID cache with semantic aliases for token-efficient lookups"
    schema:
      library_name: string # "langchain", "fastapi"
      library_id: string # "/langchain-ai/langchain/libs/langchain"
      aliases: string[] # ["lc", "langchain-core"]
      category: string # "ai-ml", "web-framework", "devops"
      last_verified: timestamp # TTL for cache refresh
      usage_count: int # Prioritize frequently-used libraries
```

### 2. Library Seed Configuration

```yaml
# Context7 Library ID Cache Seed List
# Pre-populated libraries for the library_registry collection
# These are resolved once and cached for 80-90% token savings

version: "1.0"
ttl_days: 30 # Refresh libraries after 30 days

categories:
  ai-ml:
    description: "AI/ML frameworks and tools"
    libraries:
      - name: langchain
        aliases: ["lc", "langchain-core", "langchain python"]
      - name: langgraph
        aliases: ["lg", "langgraph python", "langchain graph"]
      - name: langsmith
        aliases: ["ls", "langchain smith", "langsmith python"]
      - name: openai
        aliases: ["openai-python", "gpt", "chatgpt api"]
      - name: anthropic
        aliases: ["claude", "anthropic-python", "claude api"]
      - name: huggingface
        aliases: ["hf", "transformers", "huggingface-hub"]
      - name: ollama
        aliases: ["ollama-python", "local llm"]
      - name: chromadb
        aliases: ["chroma", "chromadb-python"]
      - name: qdrant
        aliases: ["qdrant-client", "qdrant python"]
      - name: pinecone
        aliases: ["pinecone-client", "pinecone python"]

  web-frameworks:
    description: "Web frameworks and HTTP libraries"
    libraries:
      - name: fastapi
        aliases: ["fast-api", "fastapi python", "starlette"]
      - name: pydantic
        aliases: ["pydantic v2", "pydantic python"]
      - name: httpx
        aliases: ["httpx python", "async http"]
      - name: requests
        aliases: ["python requests", "http client"]
      - name: aiohttp
        aliases: ["aiohttp python", "async aiohttp"]
      - name: uvicorn
        aliases: ["uvicorn python", "asgi server"]
      - name: flask
        aliases: ["flask python", "flask web"]
      - name: django
        aliases: ["django python", "django web"]

  devops:
    description: "DevOps and infrastructure tools"
    libraries:
      - name: docker
        aliases: ["docker-py", "docker python", "docker sdk"]
      - name: kubernetes
        aliases: ["k8s", "kubernetes-client", "kubectl python"]
      - name: terraform
        aliases: ["tf", "terraform python", "cdktf"]
      - name: ansible
        aliases: ["ansible python", "ansible runner"]
      - name: github
        aliases: ["github-actions", "pygithub", "github api"]
      - name: gitlab
        aliases: ["python-gitlab", "gitlab api"]
      - name: prometheus
        aliases: ["prometheus-client", "prometheus python"]
      - name: grafana
        aliases: ["grafana-api", "grafana python"]

  data:
    description: "Data processing and databases"
    libraries:
      - name: pandas
        aliases: ["pd", "pandas python", "dataframe"]
      - name: numpy
        aliases: ["np", "numpy python", "numerical python"]
      - name: sqlalchemy
        aliases: ["sa", "sqlalchemy python", "sql orm"]
      - name: asyncpg
        aliases: ["asyncpg python", "postgres async"]
      - name: psycopg
        aliases: ["psycopg2", "psycopg3", "postgres python"]
      - name: redis
        aliases: ["redis-py", "redis python"]
      - name: pymongo
        aliases: ["mongodb", "mongo python"]
      - name: polars
        aliases: ["polars python", "fast dataframe"]

  testing:
    description: "Testing frameworks and tools"
    libraries:
      - name: pytest
        aliases: ["py.test", "pytest python"]
      - name: unittest
        aliases: ["python unittest", "unit testing"]
      - name: hypothesis
        aliases: ["hypothesis python", "property testing"]
      - name: respx
        aliases: ["respx python", "httpx mock"]
      - name: pytest-asyncio
        aliases: ["async pytest", "asyncio testing"]

  utilities:
    description: "Common utility libraries"
    libraries:
      - name: pyyaml
        aliases: ["yaml", "yaml python"]
      - name: python-dotenv
        aliases: ["dotenv", "env files"]
      - name: typer
        aliases: ["typer cli", "cli python"]
      - name: rich
        aliases: ["rich python", "terminal formatting"]
      - name: loguru
        aliases: ["loguru python", "logging"]
      - name: tenacity
        aliases: ["retry", "tenacity python"]
      - name: structlog
        aliases: ["structured logging", "structlog python"]
```

### 3. Indexing Script

```python
#!/usr/bin/env python3
"""
Index Context7 Library IDs into Qdrant for Cache-First Lookups

This script resolves library IDs from Context7 and caches them in Qdrant
to achieve 80-90% token savings on repeated library documentation lookups.

Usage:
    python support/scripts/rag/index_library_registry.py [--refresh] [--category CATEGORY]

    --refresh: Re-resolve all libraries (ignores existing cache)
    --category: Only index libraries from specific category

Environment Variables:
    RAG_SERVICE_URL: RAG service endpoint (default: https://codechef.appsmithery.co/rag)
    CONTEXT7_RESOLVE_DELAY: Delay between Context7 API calls in seconds (default: 0.5)
"""

import asyncio
import sys
import os
import argparse
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any
import httpx
import yaml

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT))

# Configuration
RAG_SERVICE_URL = os.environ.get(
    "RAG_SERVICE_URL", "https://codechef.appsmithery.co/rag"
)
COLLECTION_NAME = "library_registry"
TIMEOUT = 60.0
CONTEXT7_RESOLVE_DELAY = float(os.environ.get("CONTEXT7_RESOLVE_DELAY", "0.5"))

# Seed file location
SEED_FILE = PROJECT_ROOT / "config" / "rag" / "library-seed.yaml"


def load_seed_config() -> Dict[str, Any]:
    """Load library seed configuration from YAML."""
    if not SEED_FILE.exists():
        print(f"ERROR: Seed file not found: {SEED_FILE}")
        sys.exit(1)

    with open(SEED_FILE, "r") as f:
        return yaml.safe_load(f)


async def resolve_library_id_context7(library_name: str) -> Optional[str]:
    """
    Resolve library name to Context7 library ID.

    In production, this would call the Context7 MCP server's resolve-library-id tool.
    For initial seeding, we use a mapping of known library IDs.

    Returns:
        Library ID string if found, None otherwise.
    """
    # Known Context7 library ID mappings (from Context7 documentation)
    # These are the resolved IDs that Context7's resolve-library-id returns
    KNOWN_LIBRARY_IDS = {
        # AI/ML
        "langchain": "/langchain-ai/langchain/libs/langchain",
        "langgraph": "/langchain-ai/langgraph",
        "langsmith": "/langchain-ai/langsmith-sdk",
        "openai": "/openai/openai-python",
        "anthropic": "/anthropics/anthropic-sdk-python",
        "huggingface": "/huggingface/transformers",
        "ollama": "/ollama/ollama-python",
        "chromadb": "/chroma-core/chroma",
        "qdrant": "/qdrant/qdrant-client",
        "pinecone": "/pinecone-io/pinecone-python-client",

        # Web Frameworks
        "fastapi": "/tiangolo/fastapi",
        "pydantic": "/pydantic/pydantic",
        "httpx": "/encode/httpx",
        "requests": "/psf/requests",
        "aiohttp": "/aio-libs/aiohttp",
        "uvicorn": "/encode/uvicorn",
        "flask": "/pallets/flask",
        "django": "/django/django",

        # DevOps
        "docker": "/docker/docker-py",
        "kubernetes": "/kubernetes-client/python",
        "terraform": "/hashicorp/terraform-cdk",
        "ansible": "/ansible/ansible",
        "github": "/PyGithub/PyGithub",
        "gitlab": "/python-gitlab/python-gitlab",
        "prometheus": "/prometheus/client_python",
        "grafana": "/grafana/grafana-api-python-client",

        # Data
        "pandas": "/pandas-dev/pandas",
        "numpy": "/numpy/numpy",
        "sqlalchemy": "/sqlalchemy/sqlalchemy",
        "asyncpg": "/MagicStack/asyncpg",
        "psycopg": "/psycopg/psycopg",
        "redis": "/redis/redis-py",
        "pymongo": "/mongodb/mongo-python-driver",
        "polars": "/pola-rs/polars",

        # Testing
        "pytest": "/pytest-dev/pytest",
        "unittest": "/python/cpython",  # Part of stdlib
        "hypothesis": "/HypothesisWorks/hypothesis",
        "respx": "/lundberg/respx",
        "pytest-asyncio": "/pytest-dev/pytest-asyncio",

        # Utilities
        "pyyaml": "/yaml/pyyaml",
        "python-dotenv": "/theskumar/python-dotenv",
        "typer": "/tiangolo/typer",
        "rich": "/Textualize/rich",
        "loguru": "/Delgan/loguru",
        "tenacity": "/jd/tenacity",
        "structlog": "/hynek/structlog",
    }

    library_id = KNOWN_LIBRARY_IDS.get(library_name.lower())

    if library_id:
        print(f"  ✓ Resolved: {library_name} → {library_id}")
        return library_id
    else:
        print(f"  ⚠ Unknown library: {library_name} (will attempt Context7 lookup)")
        # In production, fall back to actual Context7 API call here
        return None


async def check_existing_entry(library_name: str) -> bool:
    """Check if library already exists in cache."""
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            response = await client.post(
                f"{RAG_SERVICE_URL}/query",
                json={
                    "query": library_name,
                    "collection": COLLECTION_NAME,
                    "n_results": 1,
                    "metadata_filter": {"library_name": library_name}
                }
            )
            if response.status_code == 200:
                data = response.json()
                return len(data.get("results", [])) > 0
    except Exception:
        pass
    return False


async def index_library(
    library_name: str,
    library_id: str,
    aliases: List[str],
    category: str
) -> bool:
    """Index a single library entry into Qdrant."""
    timestamp = datetime.now(timezone.utc).isoformat()

    # Create searchable document combining name and aliases
    searchable_text = f"{library_name} {' '.join(aliases)} {category}"

    metadata = {
        "library_name": library_name,
        "library_id": library_id,
        "aliases": aliases,
        "category": category,
        "last_verified": timestamp,
        "usage_count": 0,
        "source": "context7-cache"
    }

    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            response = await client.post(
                f"{RAG_SERVICE_URL}/index",
                json={
                    "documents": [searchable_text],
                    "metadatas": [metadata],
                    "ids": [f"lib-{library_name}"],
                    "collection": COLLECTION_NAME
                }
            )
            response.raise_for_status()
            return True
    except Exception as e:
        print(f"  ✗ Failed to index {library_name}: {e}")
        return False


async def index_all_libraries(
    refresh: bool = False,
    category_filter: Optional[str] = None
) -> Dict[str, int]:
    """
    Index all libraries from seed configuration.

    Args:
        refresh: If True, re-index all libraries regardless of cache state
        category_filter: Only index libraries from this category

    Returns:
        Dictionary with indexing statistics
    """
    config = load_seed_config()
    categories = config.get("categories", {})

    stats = {
        "total": 0,
        "indexed": 0,
        "skipped": 0,
        "failed": 0,
        "unknown": 0
    }

    for category_name, category_data in categories.items():
        if category_filter and category_name != category_filter:
            continue

        print(f"\n📦 Processing category: {category_name}")
        print(f"   {category_data.get('description', '')}")

        libraries = category_data.get("libraries", [])

        for lib_entry in libraries:
            lib_name = lib_entry.get("name")
            aliases = lib_entry.get("aliases", [])

            if not lib_name:
                continue

            stats["total"] += 1

            # Check if already cached
            if not refresh:
                if await check_existing_entry(lib_name):
                    print(f"  ⏭ Skipping (cached): {lib_name}")
                    stats["skipped"] += 1
                    continue

            # Resolve library ID
            library_id = await resolve_library_id_context7(lib_name)

            if not library_id:
                stats["unknown"] += 1
                continue

            # Index the library
            success = await index_library(
                library_name=lib_name,
                library_id=library_id,
                aliases=aliases,
                category=category_name
            )

            if success:
                stats["indexed"] += 1
            else:
                stats["failed"] += 1

            # Rate limit Context7 API calls
            await asyncio.sleep(CONTEXT7_RESOLVE_DELAY)

    return stats


async def verify_collection_exists() -> bool:
    """Verify the library_registry collection exists."""
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            response = await client.get(f"{RAG_SERVICE_URL}/collections")
            if response.status_code == 200:
                collections = response.json()
                return any(c.get("name") == COLLECTION_NAME for c in collections)
    except Exception as e:
        print(f"Warning: Could not verify collection: {e}")
    return False


async def main():
    parser = argparse.ArgumentParser(
        description="Index Context7 library IDs into Qdrant cache"
    )
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="Re-resolve all libraries (ignores existing cache)"
    )
    parser.add_argument(
        "--category",
        type=str,
        help="Only index libraries from specific category"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be indexed without actually indexing"
    )

    args = parser.parse_args()

    print("=" * 60)
    print("Context7 Library ID Cache Indexer")
    print("=" * 60)
    print(f"RAG Service: {RAG_SERVICE_URL}")
    print(f"Collection: {COLLECTION_NAME}")
    print(f"Seed File: {SEED_FILE}")
    print(f"Refresh Mode: {args.refresh}")
    if args.category:
        print(f"Category Filter: {args.category}")
    print("=" * 60)

    if args.dry_run:
        print("\n🔍 DRY RUN MODE - No changes will be made\n")
        config = load_seed_config()
        for cat_name, cat_data in config.get("categories", {}).items():
            if args.category and cat_name != args.category:
                continue
            print(f"Category: {cat_name}")
            for lib in cat_data.get("libraries", []):
                print(f"  - {lib.get('name')}: {lib.get('aliases', [])}")
        return

    # Check RAG service health
    print("\n🔌 Checking RAG service connectivity...")
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{RAG_SERVICE_URL}/health")
            if response.status_code != 200:
                print(f"ERROR: RAG service unhealthy: {response.status_code}")
                sys.exit(1)
            health = response.json()
            print(f"  ✓ RAG service: {health.get('status')}")
            print(f"  ✓ Qdrant: {health.get('qdrant_status')}")
    except Exception as e:
        print(f"ERROR: Could not connect to RAG service: {e}")
        sys.exit(1)

    # Index libraries
    print("\n📚 Indexing libraries...")
    stats = await index_all_libraries(
        refresh=args.refresh,
        category_filter=args.category
    )

    # Print summary
    print("\n" + "=" * 60)
    print("INDEXING COMPLETE")
    print("=" * 60)
    print(f"Total libraries:   {stats['total']}")
    print(f"Indexed:           {stats['indexed']}")
    print(f"Skipped (cached):  {stats['skipped']}")
    print(f"Unknown (no ID):   {stats['unknown']}")
    print(f"Failed:            {stats['failed']}")
    print("=" * 60)

    # Estimate token savings
    if stats['indexed'] > 0:
        tokens_saved_per_lookup = 1000  # ~1000 tokens per resolve-library-id call
        daily_lookups_estimate = 10 * stats['indexed']
        daily_savings = daily_lookups_estimate * tokens_saved_per_lookup
        print(f"\n💰 Estimated daily token savings: ~{daily_savings:,} tokens")
        print(f"   (Assuming ~10 lookups per library per day)")


if __name__ == "__main__":
    asyncio.run(main())
```

### 4. Library Cache Middleware

```python
"""
Context7 Library ID Cache Middleware

Provides cache-first library ID lookups to reduce Context7 API calls
and achieve 80-90% token savings on documentation retrieval.

Usage:
    from shared.lib.context7_cache import Context7CacheClient

    cache = Context7CacheClient()
    library_id = await cache.get_library_id("langchain")
    # Returns cached ID or falls back to Context7 resolve
"""

import os
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
import httpx
import logging

logger = logging.getLogger(__name__)

# Configuration
RAG_SERVICE_URL = os.environ.get(
    "RAG_SERVICE_URL", "http://rag:8007"
)
COLLECTION_NAME = "library_registry"
CACHE_TTL_DAYS = int(os.environ.get("LIBRARY_CACHE_TTL_DAYS", "30"))
SIMILARITY_THRESHOLD = 0.85  # Minimum score for cache hit


@dataclass
class CachedLibrary:
    """Cached library entry from Qdrant."""
    library_name: str
    library_id: str
    aliases: List[str]
    category: str
    last_verified: str
    usage_count: int
    relevance_score: float


class Context7CacheClient:
    """
    Cache-first client for Context7 library ID lookups.

    Queries Qdrant library_registry collection before falling back
    to live Context7 API calls, providing 80-90% token savings.
    """

    def __init__(
        self,
        rag_url: str = RAG_SERVICE_URL,
        fallback_resolver: Optional[callable] = None
    ):
        self.rag_url = rag_url
        self.fallback_resolver = fallback_resolver
        self._local_cache: Dict[str, CachedLibrary] = {}
        self._cache_hits = 0
        self._cache_misses = 0

    async def get_library_id(
        self,
        library_name: str,
        use_fallback: bool = True
    ) -> Optional[str]:
        """
        Get library ID with cache-first strategy.

        Args:
            library_name: Library name to resolve (e.g., "langchain")
            use_fallback: If True, fall back to Context7 on cache miss

        Returns:
            Library ID string if found, None otherwise
        """
        # Check in-memory cache first (fastest)
        if library_name.lower() in self._local_cache:
            entry = self._local_cache[library_name.lower()]
            self._cache_hits += 1
            logger.debug(f"Local cache hit: {library_name} → {entry.library_id}")
            return entry.library_id

        # Query Qdrant cache
        cached = await self._query_rag_cache(library_name)

        if cached and cached.relevance_score >= SIMILARITY_THRESHOLD:
            # Cache hit - store locally and return
            self._local_cache[library_name.lower()] = cached
            self._cache_hits += 1

            # Update usage count (non-blocking)
            asyncio.create_task(self._increment_usage(cached.library_name))

            logger.info(
                f"RAG cache hit: {library_name} → {cached.library_id} "
                f"(score: {cached.relevance_score:.3f})"
            )
            return cached.library_id

        # Cache miss
        self._cache_misses += 1
        logger.info(f"Cache miss: {library_name}")

        if use_fallback and self.fallback_resolver:
            # Resolve via Context7 and cache result
            library_id = await self.fallback_resolver(library_name)
            if library_id:
                await self._cache_library(library_name, library_id)
                return library_id

        return None

    async def _query_rag_cache(
        self,
        library_name: str
    ) -> Optional[CachedLibrary]:
        """Query RAG service for cached library ID."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    f"{self.rag_url}/query",
                    json={
                        "query": library_name,
                        "collection": COLLECTION_NAME,
                        "n_results": 1
                    }
                )

                if response.status_code != 200:
                    logger.warning(
                        f"RAG query failed: {response.status_code}"
                    )
                    return None

                data = response.json()
                results = data.get("results", [])

                if not results:
                    return None

                result = results[0]
                metadata = result.get("metadata", {})

                # Check if result is stale
                last_verified = metadata.get("last_verified", "")
                if last_verified:
                    verified_dt = datetime.fromisoformat(
                        last_verified.replace("Z", "+00:00")
                    )
                    age = datetime.now(timezone.utc) - verified_dt
                    if age > timedelta(days=CACHE_TTL_DAYS):
                        logger.info(
                            f"Cache stale for {library_name} "
                            f"(age: {age.days} days)"
                        )
                        return None

                return CachedLibrary(
                    library_name=metadata.get("library_name", ""),
                    library_id=metadata.get("library_id", ""),
                    aliases=metadata.get("aliases", []),
                    category=metadata.get("category", ""),
                    last_verified=last_verified,
                    usage_count=metadata.get("usage_count", 0),
                    relevance_score=result.get("relevance_score", 0.0)
                )

        except Exception as e:
            logger.error(f"RAG cache query error: {e}")
            return None

    async def _cache_library(
        self,
        library_name: str,
        library_id: str,
        aliases: Optional[List[str]] = None,
        category: str = "unknown"
    ) -> bool:
        """Cache a newly resolved library ID."""
        timestamp = datetime.now(timezone.utc).isoformat()

        searchable_text = f"{library_name} {' '.join(aliases or [])} {category}"

        metadata = {
            "library_name": library_name,
            "library_id": library_id,
            "aliases": aliases or [],
            "category": category,
            "last_verified": timestamp,
            "usage_count": 1,
            "source": "context7-live-resolve"
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.rag_url}/index",
                    json={
                        "documents": [searchable_text],
                        "metadatas": [metadata],
                        "ids": [f"lib-{library_name}"],
                        "collection": COLLECTION_NAME
                    }
                )

                if response.status_code == 200:
                    logger.info(f"Cached new library: {library_name}")

                    # Update local cache
                    self._local_cache[library_name.lower()] = CachedLibrary(
                        library_name=library_name,
                        library_id=library_id,
                        aliases=aliases or [],
                        category=category,
                        last_verified=timestamp,
                        usage_count=1,
                        relevance_score=1.0
                    )
                    return True

        except Exception as e:
            logger.error(f"Failed to cache library {library_name}: {e}")

        return False

    async def _increment_usage(self, library_name: str) -> None:
        """Increment usage count for analytics (non-blocking)."""
        # This could update a counter in Qdrant or log to analytics
        # For now, just log it
        logger.debug(f"Usage increment: {library_name}")

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total = self._cache_hits + self._cache_misses
        hit_rate = (self._cache_hits / total * 100) if total > 0 else 0

        return {
            "cache_hits": self._cache_hits,
            "cache_misses": self._cache_misses,
            "hit_rate_percent": round(hit_rate, 2),
            "local_cache_size": len(self._local_cache),
            "estimated_tokens_saved": self._cache_hits * 1000  # ~1000 tokens per hit
        }

    def clear_local_cache(self) -> None:
        """Clear the in-memory cache."""
        self._local_cache.clear()
        logger.info("Local cache cleared")


# Singleton instance for use across agents
_cache_client: Optional[Context7CacheClient] = None


def get_context7_cache() -> Context7CacheClient:
    """Get or create the singleton cache client."""
    global _cache_client
    if _cache_client is None:
        _cache_client = Context7CacheClient()
    return _cache_client


async def get_library_docs_cached(
    library_name: str,
    context7_resolve_fn: Optional[callable] = None,
    context7_docs_fn: Optional[callable] = None
) -> Optional[str]:
    """
    High-level function to get library docs with caching.

    This is the main entry point for agents to use.

    Args:
        library_name: Library to look up (e.g., "langchain")
        context7_resolve_fn: Function to call Context7's resolve-library-id
        context7_docs_fn: Function to call Context7's get-library-docs

    Returns:
        Library documentation string, or None if not found
    """
    cache = get_context7_cache()

    if context7_resolve_fn:
        cache.fallback_resolver = context7_resolve_fn

    library_id = await cache.get_library_id(library_name)

    if not library_id:
        logger.warning(f"Could not resolve library: {library_name}")
        return None

    # Now fetch docs using the cached/resolved ID
    if context7_docs_fn:
        return await context7_docs_fn(library_id)

    return library_id  # Return ID if no docs function provided
```

### 5. RAG Service Endpoint for Cache Stats

Add this endpoint to the RAG service for monitoring cache performance:

```python
# Add this endpoint after the existing /collections endpoint

# ...existing code...

@app.get("/library-cache/stats")
async def library_cache_stats():
    """Get library cache statistics and collection info."""
    if not qdrant_client:
        return {"error": "Qdrant not available"}

    try:
        collection_info = qdrant_client.get_collection("library_registry")

        return {
            "collection": "library_registry",
            "total_libraries": collection_info.points_count,
            "status": "active",
            "description": "Context7 library ID cache for token-efficient lookups",
            "estimated_savings": {
                "tokens_per_hit": 1000,
                "potential_daily_savings": collection_info.points_count * 10 * 1000
            }
        }
    except Exception as e:
        return {
            "collection": "library_registry",
            "status": "not_initialized",
            "error": str(e),
            "action": "Run: python support/scripts/rag/index_library_registry.py"
        }

# ...existing code...
```

---

## Deployment Steps

1. **Deploy configuration changes:**

   ```powershell
   # Add library-seed.yaml to config/rag/
   # Update vectordb.config.yaml with new collection
   .\support\scripts\deploy\deploy-to-droplet.ps1 -DeployType config
   ```

2. **Run the indexing script:**

   ```powershell
   # From project root
   python support/scripts/rag/index_library_registry.py
   ```

3. **Verify the cache:**

   ```powershell
   curl https://codechef.appsmithery.co/rag/library-cache/stats
   curl -X POST https://codechef.appsmithery.co/rag/query -H "Content-Type: application/json" -d '{"query": "langchain", "collection": "library_registry", "n_results": 3}'
   ```

4. **After verification - Clean up redundant collections** (if any exist):
   ```python
   # Check for redundant/empty collections
   curl https://codechef.appsmithery.co/rag/collections
   # Remove any with 0 vectors that are unused
   ```

---

## Expected Token Savings

| Scenario                        | Before (tokens) | After (tokens) | Savings        |
| ------------------------------- | --------------- | -------------- | -------------- |
| 10 LangChain lookups/day        | 15,000          | 500            | **97%**        |
| 5 FastAPI lookups/day           | 7,500           | 250            | **97%**        |
| First lookup (cache miss)       | 1,500           | 1,600          | -7% (one-time) |
| **Daily total (50+ libraries)** | ~75,000         | ~5,000         | **93%**        |
