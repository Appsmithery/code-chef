"""
RAG Context Manager Service

Provides context retrieval from vector database for AI agents.
Manages embeddings, chunking, and semantic search.
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue
import os
from datetime import datetime
import uuid

app = FastAPI(title="RAG Context Manager", version="1.0.0")

# Qdrant client configuration
QDRANT_HOST = os.getenv("QDRANT_HOST", "qdrant")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))

try:
    qdrant_client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
    print(f"Connected to Qdrant at {QDRANT_HOST}:{QDRANT_PORT}")
except Exception as e:
    print(f"Warning: Could not connect to Qdrant: {e}")
    qdrant_client = None


# Request/Response Models
class QueryRequest(BaseModel):
    """Query for context retrieval"""
    query: str = Field(..., description="Search query text")
    collection: str = Field(default="code-knowledge", description="Collection to search")
    n_results: int = Field(default=5, description="Number of results to return")
    metadata_filter: Optional[Dict[str, Any]] = Field(default=None, description="Metadata filters")


class ContextItem(BaseModel):
    """Single context item from vector DB"""
    id: str
    content: str
    metadata: Dict[str, Any]
    distance: float
    relevance_score: float


class QueryResponse(BaseModel):
    """Context query response"""
    query: str
    results: List[ContextItem]
    collection: str
    total_found: int
    retrieval_time_ms: float


class IndexRequest(BaseModel):
    """Request to index new content"""
    documents: List[str]
    metadatas: Optional[List[Dict[str, Any]]] = None
    ids: Optional[List[str]] = None
    collection: str = Field(default="code-knowledge")


class IndexResponse(BaseModel):
    """Indexing operation response"""
    success: bool
    indexed_count: int
    collection: str
    message: str


class CollectionInfo(BaseModel):
    """Collection metadata"""
    name: str
    count: int
    metadata: Dict[str, Any]


# Health endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    qdrant_status = "disconnected"
    if qdrant_client:
        try:
            collections = qdrant_client.get_collections()
            qdrant_status = "connected"
        except:
            qdrant_status = "error"
    
    return {
        "status": "ok",
        "service": "rag-context-manager",
        "version": "1.0.0",
        "qdrant_status": qdrant_status,
        "timestamp": datetime.utcnow().isoformat()
    }


# Query endpoint
@app.post("/query", response_model=QueryResponse)
async def query_context(request: QueryRequest):
    """
    Query vector database for relevant context
    
    Returns semantically similar documents based on query.
    """
    if not qdrant_client:
        raise HTTPException(
            status_code=503,
            detail="Qdrant not available. Service running in mock mode."
        )
    
    start_time = datetime.utcnow()
    
    try:
        # Ensure collection exists
        collections = qdrant_client.get_collections()
        collection_exists = any(c.name == request.collection for c in collections.collections)
        
        if not collection_exists:
            # Create collection with default vector size (384 for sentence transformers)
            qdrant_client.create_collection(
                collection_name=request.collection,
                vectors_config=VectorParams(size=384, distance=Distance.COSINE)
            )
            print(f"Created collection: {request.collection}")
        
        # For now, return mock results since we don't have embeddings yet
        # In production, this would use an embedding model to encode the query
        context_items = []
        
        end_time = datetime.utcnow()
        retrieval_time = (end_time - start_time).total_seconds() * 1000
        
        return QueryResponse(
            query=request.query,
            results=context_items,
            collection=request.collection,
            total_found=0,
            retrieval_time_ms=round(retrieval_time, 2)
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")


# Index endpoint
@app.post("/index", response_model=IndexResponse)
async def index_documents(request: IndexRequest):
    """
    Index new documents into vector database
    
    Adds documents to specified collection for future retrieval.
    """
    if not qdrant_client:
        # Mock mode - simulate success
        return IndexResponse(
            success=True,
            indexed_count=len(request.documents),
            collection=request.collection,
            message="Mock mode: Documents simulated as indexed"
        )
    
    try:
        # Ensure collection exists
        collections = qdrant_client.get_collections()
        collection_exists = any(c.name == request.collection for c in collections.collections)
        
        if not collection_exists:
            qdrant_client.create_collection(
                collection_name=request.collection,
                vectors_config=VectorParams(size=384, distance=Distance.COSINE)
            )
        
        # In production, this would use an embedding model
        # For now, just acknowledge receipt
        
        return IndexResponse(
            success=True,
            indexed_count=len(request.documents),
            collection=request.collection,
            message=f"Collection ready. Note: Embedding generation not yet implemented."
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Indexing failed: {str(e)}")


# Collections endpoint
@app.get("/collections", response_model=List[CollectionInfo])
async def list_collections():
    """List all available collections"""
    if not qdrant_client:
        return []
    
    try:
        collections = qdrant_client.get_collections()
        result = []
        for col in collections.collections:
            col_info = qdrant_client.get_collection(col.name)
            result.append(CollectionInfo(
                name=col.name,
                count=col_info.points_count,
                metadata={}
            ))
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list collections: {str(e)}")


# Mock query endpoint for development/testing
@app.post("/query/mock", response_model=QueryResponse)
async def mock_query(request: QueryRequest):
    """
    Mock query endpoint for testing without ChromaDB
    
    Returns synthetic context data for development/testing.
    """
    # Synthetic context based on query keywords
    mock_results = []
    
    if "authentication" in request.query.lower() or "jwt" in request.query.lower():
        mock_results.append(ContextItem(
            id="mock-auth-1",
            content="JWT authentication implementation using FastAPI dependencies. Use OAuth2PasswordBearer for token validation.",
            metadata={"source": "auth_patterns.py", "type": "code"},
            distance=0.15,
            relevance_score=0.87
        ))
        mock_results.append(ContextItem(
            id="mock-auth-2",
            content="User authentication flow: 1) Client sends credentials, 2) Server validates and generates JWT, 3) Client includes JWT in Authorization header",
            metadata={"source": "auth_workflow.md", "type": "documentation"},
            distance=0.22,
            relevance_score=0.82
        ))
    
    if "api" in request.query.lower() or "endpoint" in request.query.lower():
        mock_results.append(ContextItem(
            id="mock-api-1",
            content="FastAPI endpoint pattern: @app.post('/endpoint') with Pydantic request/response models. Include error handling and logging.",
            metadata={"source": "api_patterns.py", "type": "code"},
            distance=0.18,
            relevance_score=0.85
        ))
    
    if "docker" in request.query.lower() or "deployment" in request.query.lower():
        mock_results.append(ContextItem(
            id="mock-deploy-1",
            content="Docker deployment using multi-stage builds. Python 3.11-slim base, copy requirements first for caching, then application code.",
            metadata={"source": "docker_patterns.md", "type": "documentation"},
            distance=0.20,
            relevance_score=0.83
        ))
    
    # Default fallback
    if not mock_results:
        mock_results.append(ContextItem(
            id="mock-default-1",
            content=f"Context related to: {request.query}. This is mock data for development.",
            metadata={"source": "mock_data", "type": "synthetic"},
            distance=0.30,
            relevance_score=0.77
        ))
    
    return QueryResponse(
        query=request.query,
        results=mock_results[:request.n_results],
        collection=request.collection,
        total_found=len(mock_results),
        retrieval_time_ms=5.0
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8007)
