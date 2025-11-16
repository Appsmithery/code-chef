#!/usr/bin/env python3
"""
Index Local Documentation to Qdrant
Reads workspace documentation and indexes it directly to the-shop collection
"""

import os
import sys
from pathlib import Path
from typing import List, Dict, Any
import glob

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent))

from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct
import uuid


def load_env_from_file(env_path: Path) -> dict:
    """Load environment variables from .env file with variable substitution"""
    env_vars = {}
    if not env_path.exists():
        print(f"Warning: {env_path} not found")
        return env_vars
    
    # First pass: load all raw values
    with open(env_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if '=' in line:
                key, value = line.split('=', 1)
                value = value.strip().strip('"').strip("'")
                env_vars[key.strip()] = value
    
    # Second pass: resolve variable substitutions
    for key, value in list(env_vars.items()):
        if value.startswith("${") and value.endswith("}"):
            var_name = value[2:-1]
            resolved = env_vars.get(var_name) or os.getenv(var_name) or value
            env_vars[key] = resolved
    
    return env_vars


def init_qdrant_client() -> QdrantClient:
    """Initialize Qdrant Cloud client"""
    env_path = Path(__file__).parent.parent / "config" / "env" / ".env"
    env_vars = load_env_from_file(env_path)
    
    url = os.getenv("QDRANT_URL") or env_vars.get("QDRANT_URL")
    api_key = os.getenv("QDRANT_API_KEY") or env_vars.get("QDRANT_API_KEY")
    
    if not url or not api_key:
        raise ValueError(f"QDRANT_URL and QDRANT_API_KEY must be set")
    
    print(f"Connecting to Qdrant Cloud: {url}")
    return QdrantClient(url=url, api_key=api_key)


def read_markdown_files(base_path: Path) -> List[Dict[str, Any]]:
    """Read all markdown files from docs directory"""
    documents = []
    
    # Priority documentation files
    priority_files = [
        "README.md",
        "docs/ARCHITECTURE.md",
        "docs/DEPLOYMENT.md",
        "docs/SETUP_GUIDE.md",
        "docs/HANDBOOK.md",
        "docs/MCP_INTEGRATION.md",
        "docs/TASK_ORCHESTRATION.md",
        "docs/LANGFUSE_TRACING.md",
        "docs/PROMETHEUS_METRICS.md",
        "docs/AGENT_ENDPOINTS.md",
        "docs/QDRANT_COLLECTIONS.md",
        ".github/copilot-instructions.md"
    ]
    
    # Read priority files first
    for file_path in priority_files:
        full_path = base_path / file_path
        if full_path.exists():
            try:
                content = full_path.read_text(encoding='utf-8')
                documents.append({
                    "content": content,
                    "source_file": file_path,
                    "file_type": "markdown",
                    "category": "documentation",
                    "priority": "high"
                })
                print(f"✓ Loaded: {file_path} ({len(content)} chars)")
            except Exception as e:
                print(f"⚠ Failed to read {file_path}: {e}")
    
    # Read all other docs/*.md files
    docs_pattern = str(base_path / "docs" / "*.md")
    for file_path in glob.glob(docs_pattern):
        rel_path = str(Path(file_path).relative_to(base_path))
        
        # Skip if already loaded as priority
        if rel_path in priority_files:
            continue
        
        try:
            content = Path(file_path).read_text(encoding='utf-8')
            documents.append({
                "content": content,
                "source_file": rel_path,
                "file_type": "markdown",
                "category": "documentation",
                "priority": "medium"
            })
            print(f"✓ Loaded: {rel_path} ({len(content)} chars)")
        except Exception as e:
            print(f"⚠ Failed to read {file_path}: {e}")
    
    return documents


def chunk_document(content: str, metadata: Dict[str, Any], chunk_size: int = 1000, overlap: int = 200) -> List[Dict[str, Any]]:
    """Split document into overlapping chunks"""
    chunks = []
    lines = content.split('\n')
    
    current_chunk = []
    current_size = 0
    
    for line in lines:
        line_size = len(line)
        
        if current_size + line_size > chunk_size and current_chunk:
            # Save current chunk
            chunk_text = '\n'.join(current_chunk)
            chunks.append({
                "content": chunk_text,
                **metadata,
                "chunk_index": len(chunks)
            })
            
            # Start new chunk with overlap
            overlap_lines = []
            overlap_size = 0
            for prev_line in reversed(current_chunk):
                if overlap_size + len(prev_line) <= overlap:
                    overlap_lines.insert(0, prev_line)
                    overlap_size += len(prev_line)
                else:
                    break
            
            current_chunk = overlap_lines + [line]
            current_size = sum(len(l) for l in current_chunk)
        else:
            current_chunk.append(line)
            current_size += line_size
    
    # Add final chunk
    if current_chunk:
        chunk_text = '\n'.join(current_chunk)
        chunks.append({
            "content": chunk_text,
            **metadata,
            "chunk_index": len(chunks)
        })
    
    return chunks


def create_mock_embeddings(text: str, dimension: int = 1536) -> List[float]:
    """Create deterministic mock embeddings from text hash"""
    import hashlib
    
    # Create hash from text
    text_hash = hashlib.sha256(text.encode()).digest()
    
    # Convert to floats in range [-1, 1]
    embeddings = []
    for i in range(0, dimension * 2, 2):
        byte_idx = i % len(text_hash)
        value = (text_hash[byte_idx] / 127.5) - 1.0
        embeddings.append(value)
    
    # Normalize to unit vector for cosine similarity
    magnitude = sum(x**2 for x in embeddings) ** 0.5
    if magnitude > 0:
        embeddings = [x / magnitude for x in embeddings]
    
    return embeddings[:dimension]


def index_documents(client: QdrantClient, documents: List[Dict[str, Any]], collection: str = "the-shop"):
    """Index documents to Qdrant collection"""
    print(f"\nIndexing {len(documents)} documents to '{collection}' collection...")
    
    # Create chunks from documents
    all_chunks = []
    for doc in documents:
        content = doc.pop("content")
        chunks = chunk_document(content, doc)
        all_chunks.extend(chunks)
    
    print(f"Created {len(all_chunks)} chunks")
    
    # Convert to Qdrant points with mock embeddings
    # NOTE: In production, use real embeddings from Gradient AI
    points = []
    for i, chunk in enumerate(all_chunks):
        content = chunk.pop("content")
        
        # Create mock embedding (replace with real embedding API call)
        embedding = create_mock_embeddings(content)
        
        point = PointStruct(
            id=str(uuid.uuid4()),
            vector=embedding,
            payload={
                "content": content,
                "indexed_at": "2025-11-16T00:00:00Z",
                "embedding_model": "mock-deterministic-hash",
                **chunk
            }
        )
        points.append(point)
        
        if (i + 1) % 10 == 0:
            print(f"  Processed {i + 1}/{len(all_chunks)} chunks...")
    
    # Upsert in batches
    batch_size = 64
    for i in range(0, len(points), batch_size):
        batch = points[i:i + batch_size]
        client.upsert(collection_name=collection, points=batch)
        print(f"  Upserted batch {i // batch_size + 1}/{(len(points) + batch_size - 1) // batch_size}")
    
    print(f"✅ Successfully indexed {len(points)} chunks to '{collection}'")


def main():
    """Main indexing workflow"""
    print("Local Documentation Indexer")
    print("=" * 60)
    
    try:
        # Initialize Qdrant
        client = init_qdrant_client()
        
        # Load documents
        repo_root = Path(__file__).parent.parent
        print(f"\nScanning documentation in: {repo_root}")
        documents = read_markdown_files(repo_root)
        
        if not documents:
            print("❌ No documents found to index")
            return 1
        
        print(f"\n📚 Found {len(documents)} documents")
        
        # Index to Qdrant
        index_documents(client, documents)
        
        # Verify
        collection_info = client.get_collection("the-shop")
        print(f"\n✅ Collection 'the-shop' now has {collection_info.points_count} points")
        
        print("\n⚠ NOTE: Using mock embeddings for testing!")
        print("   For production, integrate Gradient AI embedding API:")
        print("   POST https://api.digitalocean.com/v2/ai/v1/embeddings")
        
        return 0
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
