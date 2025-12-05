#!/usr/bin/env python3
"""
Index Context7 Library IDs into Qdrant for Cache-First Lookups

This script resolves library IDs from Context7 and caches them in Qdrant
to achieve 80-90% token savings on repeated library documentation lookups.

Related: DEV-194 - Context7 Library ID RAG Cache Implementation

Usage:
    python support/scripts/rag/index_library_registry.py [--refresh] [--category CATEGORY]

    --refresh: Re-resolve all libraries (ignores existing cache)
    --category: Only index libraries from specific category
    --dry-run: Show what would be indexed without actually indexing

Environment Variables:
    RAG_SERVICE_URL: RAG service endpoint (default: https://codechef.appsmithery.co/rag)
    CONTEXT7_RESOLVE_DELAY: Delay between Context7 API calls in seconds (default: 0.5)
"""

import asyncio
import sys
import os
import argparse
import uuid
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

    with open(SEED_FILE, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


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
                    "metadata_filter": {"library_name": library_name},
                },
            )
            if response.status_code == 200:
                data = response.json()
                results = data.get("results", [])
                # Check if we have a result with matching library_name
                for result in results:
                    if result.get("metadata", {}).get("library_name") == library_name:
                        return True
    except Exception as e:
        print(f"  ⚠ Warning: Could not check cache for {library_name}: {e}")
    return False


async def index_library(
    library_name: str, library_id: str, aliases: List[str], category: str
) -> bool:
    """Index a single library entry into Qdrant."""
    timestamp = datetime.now(timezone.utc).isoformat()

    # Create searchable document combining name and aliases
    searchable_text = (
        f"{library_name} {' '.join(aliases)} {category} library documentation"
    )

    metadata = {
        "library_name": library_name,
        "library_id": library_id,
        "aliases": aliases,
        "category": category,
        "last_verified": timestamp,
        "usage_count": 0,
        "source": "context7-cache",
    }

    # Generate deterministic UUID from library name for consistent IDs
    # (Qdrant requires UUIDs or unsigned integers, not arbitrary strings)
    point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"library-{library_name}"))

    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            response = await client.post(
                f"{RAG_SERVICE_URL}/index",
                json={
                    "documents": [searchable_text],
                    "metadatas": [metadata],
                    "ids": [point_id],
                    "collection": COLLECTION_NAME,
                },
            )
            response.raise_for_status()
            print(f"  ✓ Indexed: {library_name} → {library_id}")
            return True
    except Exception as e:
        print(f"  ✗ Failed to index {library_name}: {e}")
        return False


async def index_all_libraries(
    refresh: bool = False, category_filter: Optional[str] = None
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
            library_id = lib_entry.get("library_id")

            if not lib_name or not library_id:
                print(f"  ⚠ Skipping invalid entry: {lib_entry}")
                continue

            stats["total"] += 1

            # Check if already cached
            if not refresh:
                if await check_existing_entry(lib_name):
                    print(f"  ⏭ Skipping (cached): {lib_name}")
                    stats["skipped"] += 1
                    continue

            # Index the library
            success = await index_library(
                library_name=lib_name,
                library_id=library_id,
                aliases=aliases,
                category=category_name,
            )

            if success:
                stats["indexed"] += 1
            else:
                stats["failed"] += 1

            # Small delay to avoid overwhelming the service
            await asyncio.sleep(CONTEXT7_RESOLVE_DELAY)

    return stats


async def verify_rag_service() -> bool:
    """Verify the RAG service is accessible."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{RAG_SERVICE_URL}/health")
            if response.status_code == 200:
                health = response.json()
                print(f"  ✓ RAG service: {health.get('status')}")
                print(f"  ✓ Qdrant: {health.get('qdrant_status')}")
                return health.get("qdrant_status") == "connected"
            else:
                print(f"  ✗ RAG service returned: {response.status_code}")
                return False
    except Exception as e:
        print(f"  ✗ Could not connect to RAG service: {e}")
        return False


def show_dry_run(category_filter: Optional[str] = None):
    """Show what would be indexed without making changes."""
    config = load_seed_config()
    total = 0

    for cat_name, cat_data in config.get("categories", {}).items():
        if category_filter and cat_name != category_filter:
            continue

        libraries = cat_data.get("libraries", [])
        print(f"\n📦 {cat_name} ({len(libraries)} libraries)")
        print(f"   {cat_data.get('description', '')}")

        for lib in libraries:
            name = lib.get("name", "?")
            lib_id = lib.get("library_id", "?")
            aliases = lib.get("aliases", [])
            print(f"   • {name}")
            print(f"     ID: {lib_id}")
            print(f"     Aliases: {', '.join(aliases)}")
            total += 1

    print(f"\n📊 Total libraries: {total}")


async def main():
    parser = argparse.ArgumentParser(
        description="Index Context7 library IDs into Qdrant cache"
    )
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="Re-index all libraries (ignores existing cache)",
    )
    parser.add_argument(
        "--category", type=str, help="Only index libraries from specific category"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be indexed without actually indexing",
    )

    args = parser.parse_args()

    print("=" * 60)
    print("Context7 Library ID Cache Indexer")
    print("DEV-194: Context7 Library ID RAG Cache Implementation")
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
        show_dry_run(args.category)
        return

    # Check RAG service health
    print("\n🔌 Checking RAG service connectivity...")
    if not await verify_rag_service():
        print("\n❌ Cannot proceed without RAG service connection.")
        print("   Make sure the RAG service is running and accessible.")
        sys.exit(1)

    # Index libraries
    print("\n📚 Indexing libraries...")
    stats = await index_all_libraries(
        refresh=args.refresh, category_filter=args.category
    )

    # Print summary
    print("\n" + "=" * 60)
    print("INDEXING COMPLETE")
    print("=" * 60)
    print(f"Total libraries:   {stats['total']}")
    print(f"Indexed:           {stats['indexed']}")
    print(f"Skipped (cached):  {stats['skipped']}")
    print(f"Failed:            {stats['failed']}")
    print("=" * 60)

    # Estimate token savings
    if stats["indexed"] > 0:
        tokens_saved_per_lookup = 1000  # ~1000 tokens per resolve-library-id call
        daily_lookups_estimate = 10 * stats["total"]
        daily_savings = daily_lookups_estimate * tokens_saved_per_lookup
        print(f"\n💰 Estimated daily token savings: ~{daily_savings:,} tokens")
        print(f"   (Assuming ~10 lookups per library per day)")

    # Exit with error if any failures
    if stats["failed"] > 0:
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
