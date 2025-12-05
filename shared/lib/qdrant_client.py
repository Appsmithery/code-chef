"""
Qdrant Cloud Client
Provides unified interface to Qdrant Cloud for vector operations
"""

from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct, Filter, SearchRequest
import os
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class QdrantCloudClient:
    """Wrapper for Qdrant Cloud operations"""
    
    def __init__(self):
        self.url = os.getenv("QDRANT_URL")
        self.api_key = os.getenv("QDRANT_API_KEY")
        self.collection = os.getenv("QDRANT_COLLECTION", "code_patterns")
        self.client = None
        
        if self.url and self.api_key:
            self.client = QdrantClient(
                url=self.url,
                api_key=self.api_key
            )
            logger.info(f"Qdrant Cloud client initialized: {self.url}")
        else:
            logger.warning("Qdrant Cloud not configured (missing URL or API key)")
    
    def is_enabled(self) -> bool:
        """Check if Qdrant Cloud is configured"""
        return self.client is not None
    
    async def search_semantic(
        self, 
        query_vector: List[float], 
        limit: int = 5,
        score_threshold: Optional[float] = None,
        filter_conditions: Optional[Filter] = None
    ) -> List[Dict[str, Any]]:
        """Semantic search using vector similarity"""
        if not self.is_enabled():
            logger.warning("Qdrant Cloud not available")
            return []
        
        try:
            results = self.client.search(
                collection_name=self.collection,
                query_vector=query_vector,
                limit=limit,
                score_threshold=score_threshold,
                query_filter=filter_conditions
            )
            
            return [
                {
                    "id": hit.id,
                    "score": hit.score,
                    "payload": hit.payload
                }
                for hit in results
            ]
        except Exception as e:
            logger.error(f"Qdrant search failed: {e}")
            return []
    
    async def upsert_points(
        self, 
        points: List[PointStruct]
    ) -> bool:
        """Insert or update points in collection"""
        if not self.is_enabled():
            logger.warning("Qdrant Cloud not available")
            return False
        
        try:
            self.client.upsert(
                collection_name=self.collection,
                points=points
            )
            logger.info(f"Upserted {len(points)} points to Qdrant Cloud")
            return True
        except Exception as e:
            logger.error(f"Qdrant upsert failed: {e}")
            return False
    
    async def get_collection_info(self) -> Optional[Dict[str, Any]]:
        """Get collection metadata"""
        if not self.is_enabled():
            return None
        
        try:
            info = self.client.get_collection(self.collection)
            return {
                "vectors_count": info.vectors_count,
                "points_count": info.points_count,
                "status": info.status
            }
        except Exception as e:
            logger.error(f"Failed to get collection info: {e}")
            return None


# Singleton instance
_qdrant_client: Optional[QdrantCloudClient] = None


def get_qdrant_client() -> QdrantCloudClient:
    """Get or create Qdrant Cloud client singleton"""
    global _qdrant_client
    if _qdrant_client is None:
        _qdrant_client = QdrantCloudClient()
    return _qdrant_client
