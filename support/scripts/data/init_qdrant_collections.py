#!/usr/bin/env python3
"""
Initialize Qdrant Cloud Collections
Creates recommended collections for memory, context, and RAG operations
"""

import os
import sys
from pathlib import Path
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams

# Add parent to path for env loading
sys.path.insert(0, str(Path(__file__).parent))

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
                # Remove quotes if present
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
    """Initialize Qdrant Cloud client from environment"""
    # Try to load from .env file
    env_path = Path(__file__).parent.parent / "config" / "env" / ".env"
    env_vars = load_env_from_file(env_path)
    
    # Get credentials (prefer env vars, fallback to loaded file)
    url = os.getenv("QDRANT_URL") or env_vars.get("QDRANT_URL")
    api_key = os.getenv("QDRANT_API_KEY") or env_vars.get("QDRANT_API_KEY")
    
    if not url or not api_key:
        raise ValueError(
            "QDRANT_URL and QDRANT_API_KEY must be set. "
            f"URL: {url}, API Key: {'***' if api_key else 'MISSING'}"
        )
    
    print(f"Connecting to Qdrant Cloud: {url}")
    return QdrantClient(url=url, api_key=api_key)


def create_collection_if_not_exists(
    client: QdrantClient,
    collection_name: str,
    vector_size: int = 1536,
    distance: Distance = Distance.COSINE,
    description: str = ""
):
    """Create collection if it doesn't exist"""
    try:
        existing = client.get_collection(collection_name)
        print(f"✅ Collection '{collection_name}' already exists ({existing.points_count} points)")
        return False
    except Exception:
        # Collection doesn't exist, create it
        client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(size=vector_size, distance=distance)
        )
        print(f"🆕 Created collection '{collection_name}' ({vector_size} dims, {distance})")
        if description:
            print(f"   → {description}")
        return True


def main():
    """Initialize all recommended Qdrant collections"""
    print("Initializing Qdrant Cloud Collections...")
    print("=" * 60)
    
    try:
        client = init_qdrant_client()
        
        # Test connection
        collections = client.get_collections()
        print(f"Connected! Found {len(collections.collections)} existing collection(s)\n")
        
        # Collection definitions
        # Using 1536 dimensions for OpenAI text-embedding-3-large compatibility
        # Using 768 for smaller models like all-MiniLM-L6-v2
        
        collections_to_create = [
            {
                "name": "the-shop",
                "vector_size": 1536,
                "distance": Distance.COSINE,
                "description": "Main knowledge base: workspace documentation, code context, patterns"
            },
            {
                "name": "agent_memory",
                "vector_size": 1536,
                "distance": Distance.COSINE,
                "description": "Agent conversation history and episodic memory"
            },
            {
                "name": "task_context",
                "vector_size": 1536,
                "distance": Distance.COSINE,
                "description": "Task-specific context, requirements, and execution history"
            },
            {
                "name": "code_patterns",
                "vector_size": 1536,
                "distance": Distance.COSINE,
                "description": "Code snippets, architectural patterns, and best practices"
            },
            {
                "name": "feature_specs",
                "vector_size": 1536,
                "distance": Distance.COSINE,
                "description": "Feature specifications, PRDs, and requirements documents"
            },
            {
                "name": "issue_tracker",
                "vector_size": 1536,
                "distance": Distance.COSINE,
                "description": "Linear issues, bugs, and project management context"
            }
        ]
        
        print("Creating collections...")
        print("-" * 60)
        
        created_count = 0
        for config in collections_to_create:
            was_created = create_collection_if_not_exists(
                client,
                config["name"],
                config["vector_size"],
                config["distance"],
                config["description"]
            )
            if was_created:
                created_count += 1
        
        print("-" * 60)
        print(f"\n✅ Setup complete! Created {created_count} new collection(s)")
        
        # List all collections
        print("\nAll collections:")
        all_collections = client.get_collections()
        for col in all_collections.collections:
            col_info = client.get_collection(col.name)
            print(f"  • {col.name}: {col_info.points_count} points")
        
        return 0
    
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
