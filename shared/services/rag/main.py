"""
RAG Context Manager Service

Provides context retrieval from vector database for AI agents.
Manages embeddings, chunking, and semantic search.
"""

import asyncio

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue
import os
from datetime import datetime
import uuid
import httpx

app = FastAPI(title="RAG Context Manager", version="1.0.0")

# Qdrant client configuration
QDRANT_HOST = os.getenv("QDRANT_HOST", "qdrant")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))
QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
QDRANT_COLLECTION_DEFAULT = os.getenv("QDRANT_COLLECTION", "the-shop")
QDRANT_VECTOR_SIZE = int(os.getenv("QDRANT_VECTOR_SIZE", "1536"))
QDRANT_DISTANCE = os.getenv("QDRANT_DISTANCE", "cosine")

# MCP Gateway configuration
MCP_GATEWAY_URL = os.getenv("MCP_GATEWAY_URL", "http://gateway-mcp:8000")
MCP_TIMEOUT = int(os.getenv("MCP_TIMEOUT", "30"))

# Gradient / embeddings configuration  
GRADIENT_API_KEY = os.getenv("GRADIENT_API_KEY") or os.getenv("GRADIENT_MODEL_ACCESS_KEY") or os.getenv("DIGITALOCEAN_TOKEN") or os.getenv("DIGITAL_OCEAN_PAT")
GRADIENT_BASE_URL = os.getenv("GRADIENT_BASE_URL", "https://api.digitalocean.com/v2/ai")
GRADIENT_EMBEDDING_MODEL = os.getenv("GRADIENT_EMBEDDING_MODEL", "text-embedding-3-large")
EMBEDDING_TIMEOUT = int(os.getenv("EMBEDDING_TIMEOUT", "60"))

def init_qdrant_client() -> Optional[QdrantClient]:
    try:
        if QDRANT_URL:
            client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
            print(f"Connected to Qdrant Cloud at {QDRANT_URL}")
            return client
        client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT, api_key=QDRANT_API_KEY)
        print(f"Connected to Qdrant at {QDRANT_HOST}:{QDRANT_PORT}")
        return client
    except Exception as exc:
        print(f"Warning: Could not connect to Qdrant: {exc}")
        return None


qdrant_client = init_qdrant_client()
COLLECTION_CACHE: set[str] = set()

DISTANCE_MAP = {
    "COSINE": Distance.COSINE,
    "EUCLID": Distance.EUCLID,
    "DOT": Distance.DOT,
    "MANHATTAN": Distance.MANHATTAN,
}


# MCP Tool Invocation Helpers
async def invoke_mcp_tool(server: str, tool: str, params: dict) -> dict:
    """
    Invoke MCP tool via gateway
    
    Args:
        server: MCP server name (e.g., 'memory', 'time')
        tool: Tool name (e.g., 'create_entities', 'get_current_time')
        params: Tool parameters
        
    Returns:
        Tool invocation result
    """
    try:
        async with httpx.AsyncClient(timeout=MCP_TIMEOUT) as client:
            response = await client.post(
                f"{MCP_GATEWAY_URL}/tools/{server}/{tool}",
                json={"params": params}
            )
            response.raise_for_status()
            return response.json()
    except httpx.HTTPError as e:
        print(f"MCP tool invocation failed: {server}/{tool} - {e}")
        return {"success": False, "error": str(e)}
    except Exception as e:
        print(f"Unexpected error invoking MCP tool: {e}")
        return {"success": False, "error": str(e)}


async def get_current_timestamp() -> str:
    """Get current timestamp from MCP time server"""
    result = await invoke_mcp_tool("time", "get_current_time", {})
    if result.get("success"):
        return result.get("result", datetime.utcnow().isoformat())
    return datetime.utcnow().isoformat()


async def log_query_to_memory(query: str, collection: str, results_count: int) -> bool:
    """
    Log query to MCP memory server for analytics and pattern tracking
    
    Args:
        query: Search query text
        collection: Collection name
        results_count: Number of results returned
        
    Returns:
        Success status
    """
    timestamp = await get_current_timestamp()
    
    result = await invoke_mcp_tool(
        server="memory",
        tool="create_entities",
        params={
            "entities": [{
                "name": f"rag-query-{uuid.uuid4().hex[:8]}",
                "type": "rag_query",
                "metadata": {
                    "query": query,
                    "collection": collection,
                    "results_count": results_count,
                    "timestamp": timestamp,
                    "service": "rag-context-manager"
                }
            }]
        }
    )
    
    return result.get("success", False)


async def log_indexing_to_memory(collection: str, doc_count: int) -> bool:
    """
    Log indexing operation to MCP memory server
    
    Args:
        collection: Collection name
        doc_count: Number of documents indexed
        
    Returns:
        Success status
    """
    timestamp = await get_current_timestamp()
    
    result = await invoke_mcp_tool(
        server="memory",
        tool="create_entities",
        params={
            "entities": [{
                "name": f"rag-index-{uuid.uuid4().hex[:8]}",
                "type": "rag_indexing",
                "metadata": {
                    "collection": collection,
                    "document_count": doc_count,
                    "timestamp": timestamp,
                    "service": "rag-context-manager"
                }
            }]
        }
    )
    
    return result.get("success", False)


def get_distance_metric() -> Distance:
    return DISTANCE_MAP.get(QDRANT_DISTANCE.upper(), Distance.COSINE)


def ensure_collection(collection_name: str) -> None:
    if not qdrant_client:
        return
    if collection_name in COLLECTION_CACHE:
        return
    try:
        qdrant_client.get_collection(collection_name)
    except Exception:
        qdrant_client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(size=QDRANT_VECTOR_SIZE, distance=get_distance_metric())
        )
        print(f"Created Qdrant collection '{collection_name}' with size {QDRANT_VECTOR_SIZE}")
    COLLECTION_CACHE.add(collection_name)


def build_metadata_filter(metadata: Optional[Dict[str, Any]]) -> Optional[Filter]:
    if not metadata:
        return None
    must_conditions = []
    should_conditions = []
    for key, value in metadata.items():
        if value is None:
            continue
        if isinstance(value, (list, tuple, set)):
            for item in value:
                should_conditions.append(FieldCondition(key=key, match=MatchValue(value=item)))
        else:
            must_conditions.append(FieldCondition(key=key, match=MatchValue(value=value)))
    if not must_conditions and not should_conditions:
        return None
    return Filter(
        must=must_conditions or None,
        should=should_conditions or None
    )


async def embed_texts(texts: List[str]) -> List[List[float]]:
    if not texts:
        return []
    if not GRADIENT_API_KEY:
        raise HTTPException(status_code=500, detail="Embedding provider not configured (missing Gradient API key)")

    endpoint = f"{GRADIENT_BASE_URL.rstrip('/')}/v1/embeddings"
    headers = {
        "Authorization": f"Bearer {GRADIENT_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": GRADIENT_EMBEDDING_MODEL,
        "input": texts
    }

    try:
        async with httpx.AsyncClient(timeout=EMBEDDING_TIMEOUT) as client:
            response = await client.post(endpoint, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            embeddings = [item.get("embedding") for item in data.get("data", [])]
            if len(embeddings) != len(texts):
                raise ValueError("Embedding response size mismatch")
            return embeddings
    except httpx.HTTPStatusError as exc:
        raise HTTPException(status_code=502, detail=f"Embedding API error: {exc.response.text}") from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to generate embeddings: {exc}") from exc


def extract_payload_content(payload: Dict[str, Any]) -> str:
    preferred_keys = [
        "content",
        "text",
        "chunk",
        "body",
        "excerpt"
    ]
    for key in preferred_keys:
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value
    # Fall back to joining values that look textual
    for value in payload.values():
        if isinstance(value, str) and value.strip():
            return value
    return ""


# Request/Response Models
class QueryRequest(BaseModel):
    """Query for context retrieval"""
    query: str = Field(..., description="Search query text")
    collection: str = Field(default=QDRANT_COLLECTION_DEFAULT, description="Collection to search")
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
    collection: str = Field(default=QDRANT_COLLECTION_DEFAULT)


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
    
    # Check MCP gateway connectivity
    mcp_status = "unknown"
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{MCP_GATEWAY_URL}/health")
            mcp_status = "connected" if response.status_code == 200 else "error"
    except:
        mcp_status = "disconnected"
    
    timestamp = await get_current_timestamp()
    
    return {
        "status": "ok",
        "service": "rag-context-manager",
        "version": "1.0.0",
        "qdrant_status": qdrant_status,
        "mcp_gateway_status": mcp_status,
        "mcp_gateway_url": MCP_GATEWAY_URL,
        "timestamp": timestamp
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
        ensure_collection(request.collection)
        embeddings = await embed_texts([request.query])
        if not embeddings:
            raise HTTPException(status_code=500, detail="Embedding provider returned no vectors")

        search_filter = build_metadata_filter(request.metadata_filter)
        
        # Use query_points method for Qdrant client search
        from qdrant_client.models import SearchRequest
        
        if search_filter is not None:
            search_results = qdrant_client.query_points(
                collection_name=request.collection,
                query=embeddings[0],
                limit=request.n_results,
                with_payload=True,
                query_filter=search_filter
            ).points
        else:
            search_results = qdrant_client.query_points(
                collection_name=request.collection,
                query=embeddings[0],
                limit=request.n_results,
                with_payload=True
            ).points

        context_items: List[ContextItem] = []
        for point in search_results:
            payload = point.payload or {}
            score = float(point.score or 0.0)
            if QDRANT_DISTANCE.lower() == "cosine":
                distance_value = max(0.0, 1 - score)
            else:
                distance_value = score
            context_items.append(ContextItem(
                id=str(point.id),
                content=extract_payload_content(payload),
                metadata=payload,
                distance=round(distance_value, 6),
                relevance_score=round(score, 6)
            ))

        end_time = datetime.utcnow()
        retrieval_time = (end_time - start_time).total_seconds() * 1000

        try:
            await log_query_to_memory(request.query, request.collection, len(context_items))
        except Exception as e:
            print(f"Failed to log query to memory server: {e}")

        return QueryResponse(
            query=request.query,
            results=context_items,
            collection=request.collection,
            total_found=len(context_items),
            retrieval_time_ms=round(retrieval_time, 2)
        )

    except HTTPException:
        raise
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
        return IndexResponse(
            success=True,
            indexed_count=len(request.documents),
            collection=request.collection,
            message="Mock mode: Documents simulated as indexed"
        )

    try:
        ensure_collection(request.collection)

        doc_count = len(request.documents)
        if doc_count == 0:
            return IndexResponse(success=True, indexed_count=0, collection=request.collection, message="No documents provided")

        metadatas = request.metadatas or [{} for _ in range(doc_count)]
        if len(metadatas) != doc_count:
            raise HTTPException(status_code=400, detail="metadatas length must match documents length")

        ids = request.ids or []
        if ids and len(ids) != doc_count:
            raise HTTPException(status_code=400, detail="ids length must match documents length")
        if not ids:
            ids = [str(uuid.uuid4()) for _ in range(doc_count)]

        embeddings = await embed_texts(request.documents)
        points = []
        timestamp = datetime.utcnow().isoformat()
        for idx, vector in enumerate(embeddings):
            payload = dict(metadatas[idx] or {})
            payload.setdefault("content", request.documents[idx])
            payload.setdefault("indexed_at", timestamp)
            points.append(PointStruct(id=ids[idx], vector=vector, payload=payload))

        qdrant_client.upsert(collection_name=request.collection, points=points)

        try:
            await log_indexing_to_memory(request.collection, len(points))
        except Exception as e:
            print(f"Failed to log indexing to memory server: {e}")

        return IndexResponse(
            success=True,
            indexed_count=len(points),
            collection=request.collection,
            message=f"Indexed {len(points)} documents with embedding model {GRADIENT_EMBEDDING_MODEL}."
        )

    except HTTPException:
        raise
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
    
    # Log mock query to memory server for analytics (non-blocking)
    try:
        await log_query_to_memory(request.query, request.collection, len(mock_results))
    except Exception as e:
        print(f"Failed to log mock query to memory server: {e}")
    
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
