#!/usr/bin/env python3
"""
Index Vendor Documentation into Qdrant via RAG Service

Fetches vendor documentation from URLs and indexes into vector database
for agent context retrieval.

Usage:
    python support/scripts/rag/index_vendor_docs.py [--source SOURCE_NAME]

    If no source specified, indexes all Phase 1 sources.
"""

import asyncio
import sys
import os
import httpx
from bs4 import BeautifulSoup
from typing import List, Dict
import argparse


# Configuration
# Use domain for HTTPS access via Caddy, or localhost for local development
RAG_SERVICE_URL = os.environ.get(
    "RAG_SERVICE_URL", "https://codechef.appsmithery.co/rag"
)
TIMEOUT = 120.0

# Phase 1 Sources (High Priority)
SOURCES = {
    "gradient-ai": {
        "urls": [
            "https://docs.digitalocean.com/products/gradient-ai-platform/",
            "https://docs.digitalocean.com/products/gradient-ai-platform/how-to/use-serverless-inference/",
            "https://raw.githubusercontent.com/digitalocean/gradient-python/main/README.md",
        ],
        "tags": ["digitalocean", "gradient-ai", "llm", "inference"],
        "chunk_size": 1000,
    },
    "linear-api": {
        "urls": [
            "https://linear.app/developers/graphql",
            "https://linear.app/developers/sdk",
        ],
        "tags": ["linear", "graphql", "sdk", "project-management"],
        "chunk_size": 1500,
    },
    "langsmith-api": {
        "urls": [
            "https://api.smith.langchain.com/redoc",
        ],
        "tags": ["langsmith", "api", "observability", "tracing"],
        "chunk_size": 1000,
    },
    "langgraph-reference": {
        "urls": [
            "https://reference.langchain.com/python/langgraph/",
        ],
        "tags": ["langgraph", "langchain", "agents", "workflows"],
        "chunk_size": 1200,
    },
    "langchain-mcp": {
        "urls": [
            "https://python.langchain.com/docs/concepts/mcp/",
        ],
        "tags": ["langchain", "mcp", "protocol", "tools"],
        "chunk_size": 1000,
    },
    "qdrant-api": {
        "urls": [
            "https://api.qdrant.tech/api-reference",
        ],
        "tags": ["qdrant", "vector-db", "api", "search"],
        "chunk_size": 1200,
    },
}


def extract_text_from_html(html: str) -> str:
    """Extract clean text from HTML."""
    soup = BeautifulSoup(html, "html.parser")

    # Remove script and style elements
    for script in soup(["script", "style", "nav", "footer", "header"]):
        script.decompose()

    # Get text
    text = soup.get_text(separator="\n", strip=True)

    # Clean up whitespace
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return "\n".join(lines)


def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
    """
    Split text into overlapping chunks with semantic awareness.

    Improvements:
    - Preserves code blocks (```...```) as complete units
    - Respects heading boundaries (##, ###)
    - Prioritizes paragraph breaks over sentence breaks
    - Maintains context through intelligent overlap
    """
    if len(text) <= chunk_size:
        return [text]

    # Extract code blocks to preserve them
    code_blocks = []
    code_placeholder_pattern = "<<<CODE_BLOCK_{}>>>"

    # Find and replace code blocks with placeholders
    import re

    code_block_regex = r"```[\s\S]*?```"
    for i, match in enumerate(re.finditer(code_block_regex, text)):
        placeholder = code_placeholder_pattern.format(i)
        code_blocks.append(match.group())
        text = text[: match.start()] + placeholder + text[match.end() :]

    chunks = []
    start = 0

    while start < len(text):
        end = start + chunk_size

        # Try to break at semantic boundaries
        if end < len(text):
            # Priority 1: Heading boundary (## or ###)
            heading_break = max(
                text.rfind("\n## ", start, end),
                text.rfind("\n### ", start, end),
            )
            if heading_break > start + chunk_size // 3:
                end = heading_break + 1
            else:
                # Priority 2: Paragraph break (double newline)
                para_break = text.rfind("\n\n", start, end)
                if para_break > start + chunk_size // 2:
                    end = para_break + 2
                else:
                    # Priority 3: Sentence break
                    sentence_break = max(
                        text.rfind(". ", start, end),
                        text.rfind(".\n", start, end),
                        text.rfind("! ", start, end),
                        text.rfind("? ", start, end),
                    )
                    if sentence_break > start + chunk_size // 2:
                        end = sentence_break + 1

        chunk = text[start:end].strip()

        # Restore code blocks in this chunk
        for i, code_block in enumerate(code_blocks):
            placeholder = code_placeholder_pattern.format(i)
            if placeholder in chunk:
                chunk = chunk.replace(placeholder, code_block)

        if chunk:
            chunks.append(chunk)

        # Move start position with overlap (ensure context continuity)
        start = end - overlap
        if start >= len(text):
            break

    return chunks


async def fetch_url(url: str) -> str:
    """Fetch content from URL."""
    print(f"  Fetching: {url}")

    async with httpx.AsyncClient(timeout=TIMEOUT, follow_redirects=True) as client:
        response = await client.get(url)
        response.raise_for_status()

        # If it's a raw text file (like GitHub README), return as-is
        if "raw.githubusercontent.com" in url or "text/plain" in response.headers.get(
            "content-type", ""
        ):
            return response.text

        # Otherwise, extract text from HTML
        return extract_text_from_html(response.text)


async def index_documents(
    documents: List[str], metadatas: List[Dict], collection: str = "vendor-docs"
):
    """Index documents into RAG service."""
    print(f"  Indexing {len(documents)} chunks into collection '{collection}'...")

    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        response = await client.post(
            f"{RAG_SERVICE_URL}/index",
            json={
                "documents": documents,
                "metadatas": metadatas,
                "collection": collection,
            },
        )
        response.raise_for_status()
        result = response.json()

        print(f"  ✅ Indexed: {result.get('count', len(documents))} chunks")
        print(f"     Collection: {result.get('collection')}")
        if "ids" in result:
            print(f"     IDs: {result['ids'][:3]}... (showing first 3)")

        return result


async def index_source(source_name: str, source_config: Dict):
    """Index a single documentation source."""
    print(f"\n{'='*60}")
    print(f"Indexing: {source_name}")
    print(f"{'='*60}")

    all_documents = []
    all_metadatas = []

    for url in source_config["urls"]:
        try:
            # Fetch content
            content = await fetch_url(url)

            # Chunk content
            chunks = chunk_text(
                content, chunk_size=source_config.get("chunk_size", 1000), overlap=200
            )

            print(f"  Generated {len(chunks)} chunks from {url}")

            # Create metadata for each chunk
            for i, chunk in enumerate(chunks):
                all_documents.append(chunk)
                all_metadatas.append(
                    {
                        "source": source_name,
                        "url": url,
                        "chunk_index": i,
                        "tags": source_config["tags"],
                    }
                )

        except Exception as e:
            print(f"  ❌ Error fetching {url}: {e}")
            continue

    if not all_documents:
        print(f"  ⚠️  No documents to index for {source_name}")
        return

    # Index all documents from this source
    try:
        await index_documents(all_documents, all_metadatas)
        print(f"✅ Successfully indexed {source_name}")
    except Exception as e:
        print(f"❌ Failed to index {source_name}: {e}")


async def main(source_name: str = None):
    """Main indexing function."""
    print(f"\n🚀 Vendor Documentation Indexing")
    print(f"RAG Service: {RAG_SERVICE_URL}")
    print(f"Target Collection: vendor-docs")

    # Check RAG service health
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{RAG_SERVICE_URL}/health")
            response.raise_for_status()
            health = response.json()
            print(f"\n✅ RAG Service Status: {health.get('status')}")
            print(f"   Qdrant Status: {health.get('qdrant_status')}")
    except Exception as e:
        print(f"\n❌ RAG Service not available: {e}")
        sys.exit(1)

    # Index sources
    if source_name:
        if source_name not in SOURCES:
            print(f"❌ Unknown source: {source_name}")
            print(f"Available sources: {', '.join(SOURCES.keys())}")
            sys.exit(1)

        await index_source(source_name, SOURCES[source_name])
    else:
        # Index all Phase 1 sources
        print(f"\nIndexing {len(SOURCES)} Phase 1 sources...")

        for name, config in SOURCES.items():
            await index_source(name, config)
            await asyncio.sleep(2)  # Brief pause between sources

    print(f"\n{'='*60}")
    print("✅ Indexing Complete!")
    print(f"{'='*60}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Index vendor documentation into RAG")
    parser.add_argument(
        "--source",
        type=str,
        help="Specific source to index (e.g., 'gradient-ai'). If not specified, indexes all Phase 1 sources.",
    )

    args = parser.parse_args()

    asyncio.run(main(args.source))
