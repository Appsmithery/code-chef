#!/usr/bin/env python3
"""
Index vendor documentation URLs into Qdrant via RAG service.
Reads from config/rag/indexing.yaml and indexes enabled sources.
"""
import argparse
import asyncio
import sys
from pathlib import Path
from typing import List, Dict, Any
import httpx
import yaml
from bs4 import BeautifulSoup

# Add repo root to path for imports
SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

# Configuration
RAG_SERVICE_URL = "http://45.55.173.72:8007"
INDEXING_CONFIG = REPO_ROOT / "config" / "rag" / "indexing.yaml"


def load_config() -> Dict[str, Any]:
    """Load indexing configuration from YAML."""
    if not INDEXING_CONFIG.exists():
        raise FileNotFoundError(f"Config not found: {INDEXING_CONFIG}")
    with open(INDEXING_CONFIG, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


async def fetch_url_content(url: str, timeout: int = 30) -> str:
    """Fetch and extract text content from URL."""
    print(f"  Fetching: {url}")
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        response = await client.get(url)
        response.raise_for_status()
        
        # Parse HTML and extract text
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Remove script and style elements
        for script in soup(["script", "style", "nav", "header", "footer"]):
            script.decompose()
        
        # Get text
        text = soup.get_text(separator='\n', strip=True)
        
        # Clean up extra whitespace
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = '\n'.join(chunk for chunk in chunks if chunk)
        
        return text


def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
    """Split text into overlapping chunks."""
    if len(text) <= chunk_size:
        return [text]
    
    chunks = []
    start = 0
    
    while start < len(text):
        end = start + chunk_size
        
        # Try to break at sentence boundary
        if end < len(text):
            # Look for period, newline, or question mark
            for break_char in ['. ', '\n', '? ', '! ']:
                last_break = text.rfind(break_char, start, end)
                if last_break != -1:
                    end = last_break + len(break_char)
                    break
        
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        
        start = end - overlap if end < len(text) else end
    
    return chunks


async def index_source(source: Dict[str, Any], rag_url: str) -> Dict[str, Any]:
    """Index a single documentation source."""
    name = source.get('name', 'unknown')
    urls = source.get('urls', [])
    collection = source.get('collection', 'vendor-docs')
    chunk_size = source.get('chunk_size', 1000)
    overlap = source.get('overlap', 200)
    tags = source.get('tags', [])
    
    print(f"\n{'='*60}")
    print(f"Indexing: {name}")
    print(f"URLs: {len(urls)}")
    print(f"Collection: {collection}")
    print(f"Chunk size: {chunk_size}, Overlap: {overlap}")
    print(f"{'='*60}")
    
    all_documents = []
    all_metadatas = []
    
    for url in urls:
        try:
            # Fetch content
            content = await fetch_url_content(url, timeout=60)
            print(f"  ✓ Fetched {len(content)} chars from {url}")
            
            # Chunk content
            chunks = chunk_text(content, chunk_size=chunk_size, overlap=overlap)
            print(f"  ✓ Split into {len(chunks)} chunks")
            
            # Add to batch
            for i, chunk in enumerate(chunks):
                all_documents.append(chunk)
                all_metadatas.append({
                    "source": name,
                    "url": url,
                    "chunk_index": i,
                    "total_chunks": len(chunks),
                    "tags": tags
                })
        
        except Exception as e:
            print(f"  ✗ Error fetching {url}: {e}")
            continue
    
    if not all_documents:
        return {"success": False, "error": "No documents to index", "source": name}
    
    # Index all documents
    print(f"\n  Indexing {len(all_documents)} chunks to RAG service...")
    
    try:
        async with httpx.AsyncClient(timeout=300) as client:
            response = await client.post(
                f"{rag_url}/index",
                json={
                    "documents": all_documents,
                    "metadatas": all_metadatas,
                    "collection": collection
                }
            )
            response.raise_for_status()
            result = response.json()
            print(f"  ✓ Indexed {result.get('indexed_count', 0)} documents")
            print(f"  Message: {result.get('message', 'N/A')}")
            return {"success": True, "source": name, "indexed_count": result.get('indexed_count', 0)}
    
    except Exception as e:
        print(f"  ✗ Indexing failed: {e}")
        return {"success": False, "error": str(e), "source": name}


async def main():
    parser = argparse.ArgumentParser(description="Index vendor documentation into Qdrant")
    parser.add_argument("--source", help="Index only specific source by name")
    parser.add_argument("--rag-url", default=RAG_SERVICE_URL, help="RAG service URL")
    parser.add_argument("--dry-run", action="store_true", help="Fetch URLs but don't index")
    args = parser.parse_args()
    
    # Load configuration
    config = load_config()
    sources = config.get('sources', [])
    
    # Filter to vendor docs sources with type="web"
    vendor_sources = [
        s for s in sources 
        if s.get('type') == 'web' and s.get('enabled', False)
    ]
    
    if args.source:
        vendor_sources = [s for s in vendor_sources if s.get('name') == args.source]
        if not vendor_sources:
            print(f"Error: Source '{args.source}' not found or not enabled")
            sys.exit(1)
    
    if not vendor_sources:
        print("No enabled vendor documentation sources found in config")
        sys.exit(1)
    
    print(f"Found {len(vendor_sources)} enabled source(s) to index")
    
    # Index each source
    results = []
    for source in vendor_sources:
        result = await index_source(source, args.rag_url)
        results.append(result)
    
    # Summary
    print(f"\n{'='*60}")
    print("INDEXING SUMMARY")
    print(f"{'='*60}")
    successful = sum(1 for r in results if r.get('success'))
    total_indexed = sum(r.get('indexed_count', 0) for r in results if r.get('success'))
    
    print(f"Successful: {successful}/{len(results)}")
    print(f"Total documents indexed: {total_indexed}")
    
    for result in results:
        status = "✓" if result.get('success') else "✗"
        source_name = result.get('source', 'unknown')
        if result.get('success'):
            count = result.get('indexed_count', 0)
            print(f"{status} {source_name}: {count} documents")
        else:
            error = result.get('error', 'Unknown error')
            print(f"{status} {source_name}: {error}")


if __name__ == "__main__":
    asyncio.run(main())
