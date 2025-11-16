#!/usr/bin/env python3
"""Test Qdrant Cloud connectivity and list collections."""

import os
import sys
from qdrant_client import QdrantClient

def test_cloud_access():
    """Test Qdrant Cloud connection."""
    
    # Read from env
    qdrant_url = os.getenv("QDRANT_URL")
    qdrant_api_key = os.getenv("QDRANT_API_KEY")
    
    if not qdrant_url or not qdrant_api_key:
        print("❌ QDRANT_URL or QDRANT_API_KEY not set in environment")
        sys.exit(1)
    
    print(f"Connecting to: {qdrant_url}")
    
    try:
        # Connect to Qdrant Cloud
        client = QdrantClient(
            url=qdrant_url,
            api_key=qdrant_api_key,
            timeout=10
        )
        
        # List collections
        collections = client.get_collections()
        
        print(f"✅ Connected successfully!")
        print(f"Collections found: {len(collections.collections)}")
        
        for collection in collections.collections:
            print(f"  - {collection.name} ({collection.points_count} points)")
        
        return True
        
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False

if __name__ == "__main__":
    success = test_cloud_access()
    sys.exit(0 if success else 1)
