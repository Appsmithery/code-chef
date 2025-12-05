"""
Context7 Library ID Cache Middleware

Provides cache-first library ID lookups to reduce Context7 API calls
and achieve 80-90% token savings on documentation retrieval.

Related: DEV-194 - Context7 Library ID RAG Cache Implementation

Usage:
    from shared.lib.context7_cache import Context7CacheClient, get_context7_cache

    cache = get_context7_cache()
    library_id = await cache.get_library_id("langchain")
    # Returns cached ID or falls back to Context7 resolve
"""

import os
import asyncio
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List, Callable, Awaitable
from dataclasses import dataclass
import httpx
import logging

logger = logging.getLogger(__name__)

# Configuration
RAG_SERVICE_URL = os.environ.get("RAG_SERVICE_URL", "http://rag:8007")
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
        fallback_resolver: Optional[Callable[[str], Awaitable[Optional[str]]]] = None,
    ):
        self.rag_url = rag_url
        self.fallback_resolver = fallback_resolver
        self._local_cache: Dict[str, CachedLibrary] = {}
        self._cache_hits = 0
        self._cache_misses = 0

    async def get_library_id(
        self, library_name: str, use_fallback: bool = True
    ) -> Optional[str]:
        """
        Get library ID with cache-first strategy.

        Args:
            library_name: Library name to resolve (e.g., "langchain")
            use_fallback: If True, fall back to Context7 on cache miss

        Returns:
            Library ID string if found, None otherwise
        """
        normalized_name = library_name.lower().strip()

        # Check in-memory cache first (fastest)
        if normalized_name in self._local_cache:
            entry = self._local_cache[normalized_name]
            self._cache_hits += 1
            logger.debug(f"Local cache hit: {library_name} → {entry.library_id}")
            return entry.library_id

        # Query Qdrant cache
        cached = await self._query_rag_cache(library_name)

        if cached and cached.relevance_score >= SIMILARITY_THRESHOLD:
            # Cache hit - store locally and return
            self._local_cache[normalized_name] = cached
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

    async def _query_rag_cache(self, library_name: str) -> Optional[CachedLibrary]:
        """Query RAG service for cached library ID."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    f"{self.rag_url}/query",
                    json={
                        "query": library_name,
                        "collection": COLLECTION_NAME,
                        "n_results": 1,
                    },
                )

                if response.status_code != 200:
                    logger.warning(f"RAG query failed: {response.status_code}")
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
                    try:
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
                    except (ValueError, TypeError):
                        pass  # If we can't parse date, don't invalidate

                return CachedLibrary(
                    library_name=metadata.get("library_name", ""),
                    library_id=metadata.get("library_id", ""),
                    aliases=metadata.get("aliases", []),
                    category=metadata.get("category", ""),
                    last_verified=last_verified,
                    usage_count=metadata.get("usage_count", 0),
                    relevance_score=result.get("relevance_score", 0.0),
                )

        except Exception as e:
            logger.error(f"RAG cache query error: {e}")
            return None

    async def _cache_library(
        self,
        library_name: str,
        library_id: str,
        aliases: Optional[List[str]] = None,
        category: str = "unknown",
    ) -> bool:
        """Cache a newly resolved library ID."""
        timestamp = datetime.now(timezone.utc).isoformat()

        searchable_text = (
            f"{library_name} {' '.join(aliases or [])} {category} library documentation"
        )

        metadata = {
            "library_name": library_name,
            "library_id": library_id,
            "aliases": aliases or [],
            "category": category,
            "last_verified": timestamp,
            "usage_count": 1,
            "source": "context7-live-resolve",
        }

        # Generate deterministic UUID from library name for consistent IDs
        # (Qdrant requires UUIDs or unsigned integers, not arbitrary strings)
        point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"library-{library_name}"))

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.rag_url}/index",
                    json={
                        "documents": [searchable_text],
                        "metadatas": [metadata],
                        "ids": [point_id],
                        "collection": COLLECTION_NAME,
                    },
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
                        relevance_score=1.0,
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
            "estimated_tokens_saved": self._cache_hits * 1000,  # ~1000 tokens per hit
        }

    def clear_local_cache(self) -> None:
        """Clear the in-memory cache."""
        self._local_cache.clear()
        logger.info("Local cache cleared")

    def get_cached_libraries(self) -> List[str]:
        """Get list of locally cached library names."""
        return list(self._local_cache.keys())


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
    context7_resolve_fn: Optional[Callable[[str], Awaitable[Optional[str]]]] = None,
    context7_docs_fn: Optional[Callable[[str], Awaitable[Optional[str]]]] = None,
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


# Convenience function for quick lookups
async def lookup_library_id(library_name: str) -> Optional[str]:
    """
    Quick lookup of library ID from cache.

    Does not use fallback resolver - just checks cache.

    Args:
        library_name: Library to look up

    Returns:
        Library ID if cached, None otherwise
    """
    cache = get_context7_cache()
    return await cache.get_library_id(library_name, use_fallback=False)
