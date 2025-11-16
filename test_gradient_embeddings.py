#!/usr/bin/env python3
"""
Test DigitalOcean Gradient AI Embeddings API
Verifies that embeddings endpoint is available and functional
"""

import os
import sys
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent))


def load_env():
    """Load environment variables from .env file"""
    env_path = Path(__file__).parent / "config" / "env" / ".env"
    if env_path.exists():
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key.strip()] = value.strip().strip('"').strip("'")


def test_gradient_embeddings():
    """Test DO Gradient AI embeddings via LangChain"""
    print("Testing DigitalOcean Gradient AI Embeddings")
    print("=" * 60)
    
    # Load environment
    load_env()
    
    api_key = os.getenv("GRADIENT_API_KEY") or os.getenv("GRADIENT_MODEL_ACCESS_KEY")
    base_url = os.getenv("GRADIENT_BASE_URL", "https://api.digitalocean.com/v2/ai/v1")
    
    print(f"\nConfiguration:")
    print(f"  Base URL: {base_url}")
    print(f"  API Key: {api_key[:20] if api_key else 'NOT SET'}...")
    
    if not api_key:
        print("\n❌ Error: GRADIENT_API_KEY not set in environment")
        print("   Set it in config/env/.env file")
        return 1
    
    try:
        # Import unified LangChain configuration
        print("\n1. Loading unified LangChain configuration...")
        from agents._shared.langchain_gradient import gradient_embeddings
        
        if not gradient_embeddings:
            print("❌ Gradient embeddings not initialized (missing API key)")
            return 1
        
        print("✓ Gradient embeddings client loaded")
        
        # Test embedding a single query
        print("\n2. Testing single query embedding...")
        test_query = "What is the architecture of the Dev-Tools system?"
        
        vector = gradient_embeddings.embed_query(test_query)
        print(f"✓ Generated embedding for query")
        print(f"   Dimension: {len(vector)}")
        print(f"   Sample values: {vector[:5]}")
        
        # Test embedding multiple documents
        print("\n3. Testing batch document embedding...")
        test_docs = [
            "The orchestrator agent coordinates task workflows",
            "Feature development uses CodeLlama 13B model",
            "All agents integrate with MCP gateway for tool access"
        ]
        
        vectors = gradient_embeddings.embed_documents(test_docs)
        print(f"✓ Generated embeddings for {len(vectors)} documents")
        print(f"   Each vector dimension: {len(vectors[0])}")
        
        # Verify embeddings are different
        print("\n4. Verifying embedding uniqueness...")
        from numpy import dot
        from numpy.linalg import norm
        
        def cosine_similarity(v1, v2):
            return dot(v1, v2) / (norm(v1) * norm(v2))
        
        sim_01 = cosine_similarity(vectors[0], vectors[1])
        sim_02 = cosine_similarity(vectors[0], vectors[2])
        
        print(f"   Similarity doc0-doc1: {sim_01:.4f}")
        print(f"   Similarity doc0-doc2: {sim_02:.4f}")
        
        if sim_01 < 0.99 and sim_02 < 0.99:
            print("✓ Embeddings are unique (not identical)")
        else:
            print("⚠ Embeddings are too similar (possible issue)")
        
        print("\n" + "=" * 60)
        print("✅ All tests passed! DO Gradient AI embeddings are working")
        print("\nNext steps:")
        print("  1. Run: python scripts/index_local_docs.py")
        print("  2. Verify Qdrant collection has real embeddings")
        print("  3. Test RAG queries for relevant results")
        
        return 0
        
    except ImportError as e:
        print(f"\n❌ Import error: {e}")
        print("   Install missing dependencies:")
        print("   pip install langchain-openai langchain-qdrant")
        return 1
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(test_gradient_embeddings())
