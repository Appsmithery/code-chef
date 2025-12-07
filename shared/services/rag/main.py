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
from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue,
)
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
QDRANT_COLLECTION_DEFAULT = os.getenv("QDRANT_COLLECTION", "code_patterns")
QDRANT_VECTOR_SIZE = int(os.getenv("QDRANT_VECTOR_SIZE", "1536"))
QDRANT_DISTANCE = os.getenv("QDRANT_DISTANCE", "cosine")

# MCP Gateway configuration
MCP_GATEWAY_URL = os.getenv("MCP_GATEWAY_URL", "http://gateway-mcp:8000")
MCP_TIMEOUT = int(os.getenv("MCP_TIMEOUT", "30"))

# Embedding configuration - Hybrid approach (OpenAI primary, Ollama fallback)
from langchain_openai import OpenAIEmbeddings
from langchain_community.embeddings import OllamaEmbeddings
from typing import Optional
import logging

logger = logging.getLogger(__name__)

# OpenAI Configuration (primary)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_EMBEDDING_MODEL = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")

# Ollama Configuration (fallback)
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://ollama:11434")
OLLAMA_EMBEDDING_MODEL = os.getenv("OLLAMA_EMBEDDING_MODEL", "nomic-embed-text")


def init_embedding_model():
    """Initialize embedding model with fallback chain: OpenAI → Ollama."""
    try:
        if OPENAI_API_KEY:
            logger.info(f"Using OpenAI embeddings: {OPENAI_EMBEDDING_MODEL}")
            return OpenAIEmbeddings(
                model=OPENAI_EMBEDDING_MODEL, openai_api_key=OPENAI_API_KEY
            )
        else:
            logger.info(
                f"Using Ollama embeddings at {OLLAMA_URL}: {OLLAMA_EMBEDDING_MODEL}"
            )
            return OllamaEmbeddings(model=OLLAMA_EMBEDDING_MODEL, base_url=OLLAMA_URL)
    except Exception as exc:
        logger.error(f"Failed to initialize embedding model: {exc}")
        raise


def init_qdrant_client() -> Optional[QdrantClient]:
    try:
        if QDRANT_URL:
            client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
            print(f"Connected to Qdrant Cloud at {QDRANT_URL}")
            return client
        client = QdrantClient(
            host=QDRANT_HOST, port=QDRANT_PORT, api_key=QDRANT_API_KEY
        )
        print(f"Connected to Qdrant at {QDRANT_HOST}:{QDRANT_PORT}")
        return client
    except Exception as exc:
        print(f"Warning: Could not connect to Qdrant: {exc}")
        return None


qdrant_client = init_qdrant_client()
embedding_model = init_embedding_model()
COLLECTION_CACHE: set[str] = set()

logger.info(
    f"RAG Service initialized with embedding model: {type(embedding_model).__name__}"
)

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
                f"{MCP_GATEWAY_URL}/tools/{server}/{tool}", json={"params": params}
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
            "entities": [
                {
                    "name": f"rag-query-{uuid.uuid4().hex[:8]}",
                    "type": "rag_query",
                    "metadata": {
                        "query": query,
                        "collection": collection,
                        "results_count": results_count,
                        "timestamp": timestamp,
                        "service": "rag-context-manager",
                    },
                }
            ]
        },
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
            "entities": [
                {
                    "name": f"rag-index-{uuid.uuid4().hex[:8]}",
                    "type": "rag_indexing",
                    "metadata": {
                        "collection": collection,
                        "document_count": doc_count,
                        "timestamp": timestamp,
                        "service": "rag-context-manager",
                    },
                }
            ]
        },
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
            vectors_config=VectorParams(
                size=QDRANT_VECTOR_SIZE, distance=get_distance_metric()
            ),
        )
        print(
            f"Created Qdrant collection '{collection_name}' with size {QDRANT_VECTOR_SIZE}"
        )
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
                should_conditions.append(
                    FieldCondition(key=key, match=MatchValue(value=item))
                )
        else:
            must_conditions.append(
                FieldCondition(key=key, match=MatchValue(value=value))
            )
    if not must_conditions and not should_conditions:
        return None
    return Filter(must=must_conditions or None, should=should_conditions or None)


async def embed_texts(texts: List[str]) -> List[List[float]]:
    """Generate embeddings using LangChain (OpenAI or Ollama)."""
    if not texts:
        return []

    try:
        # Use LangChain's async embedding method
        embeddings = await embedding_model.aembed_documents(texts)
        logger.info(
            f"Generated {len(embeddings)} embeddings using {type(embedding_model).__name__}"
        )
        return embeddings
    except Exception as exc:
        logger.error(f"Embedding generation failed: {exc}")
        raise HTTPException(
            status_code=500, detail=f"Failed to generate embeddings: {str(exc)}"
        ) from exc


def extract_payload_content(payload: Dict[str, Any]) -> str:
    preferred_keys = ["content", "text", "chunk", "body", "excerpt"]
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
    collection: str = Field(
        default=QDRANT_COLLECTION_DEFAULT, description="Collection to search"
    )
    n_results: int = Field(default=5, description="Number of results to return")
    metadata_filter: Optional[Dict[str, Any]] = Field(
        default=None, description="Metadata filters"
    )


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


# ============================================================================
# Agent Memory Models (Cross-Agent Knowledge Sharing)
# ============================================================================

from enum import Enum


class InsightType(str, Enum):
    """Types of insights agents can capture and share"""

    ARCHITECTURAL_DECISION = "architectural_decision"
    ERROR_PATTERN = "error_pattern"
    CODE_PATTERN = "code_pattern"
    TASK_RESOLUTION = "task_resolution"
    SECURITY_FINDING = "security_finding"


class StoreInsightRequest(BaseModel):
    """Request to store an agent insight"""

    agent_id: str = Field(..., description="ID of the agent storing the insight")
    insight_type: InsightType = Field(..., description="Category of the insight")
    content: str = Field(..., description="The insight content (max 2000 chars)")
    context: Optional[str] = Field(
        None, description="Additional context about when/why this insight was captured"
    )
    resolution: Optional[str] = Field(
        None, description="How the issue was resolved (for error_pattern/task_resolution)"
    )
    confidence: float = Field(
        default=0.8, ge=0.0, le=1.0, description="Confidence score for the insight"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default=None, description="Additional metadata (file_path, workflow_id, etc.)"
    )


class StoreInsightResponse(BaseModel):
    """Response after storing an insight"""

    success: bool
    insight_id: str
    agent_id: str
    message: str


class QueryMemoryRequest(BaseModel):
    """Request to query agent memory"""

    query: str = Field(..., description="Semantic search query")
    agent_id: Optional[str] = Field(
        None, description="Filter to specific agent's insights"
    )
    insight_types: Optional[List[InsightType]] = Field(
        None, description="Filter by insight types"
    )
    n_results: int = Field(default=5, ge=1, le=20, description="Number of results")
    min_confidence: float = Field(
        default=0.5, ge=0.0, le=1.0, description="Minimum confidence threshold"
    )


class MemoryInsight(BaseModel):
    """A single insight from agent memory"""

    id: str
    agent_id: str
    insight_type: InsightType
    content: str
    context: Optional[str]
    resolution: Optional[str]
    confidence: float
    relevance_score: float
    timestamp: str
    usage_count: int
    metadata: Dict[str, Any]


class QueryMemoryResponse(BaseModel):
    """Response from memory query"""

    query: str
    results: List[MemoryInsight]
    total_found: int
    retrieval_time_ms: float


class AgentMemoryStats(BaseModel):
    """Statistics for agent memory"""

    total_insights: int
    insights_by_type: Dict[str, int]
    insights_by_agent: Dict[str, int]
    avg_confidence: float
    oldest_insight: Optional[str]
    newest_insight: Optional[str]


AGENT_MEMORY_COLLECTION = "agent_memory"


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
        "timestamp": timestamp,
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
            detail="Qdrant not available. Service running in mock mode.",
        )

    start_time = datetime.utcnow()

    try:
        ensure_collection(request.collection)
        embeddings = await embed_texts([request.query])
        if not embeddings:
            raise HTTPException(
                status_code=500, detail="Embedding provider returned no vectors"
            )

        search_filter = build_metadata_filter(request.metadata_filter)

        # Use query_points method for Qdrant client search
        from qdrant_client.models import SearchRequest

        if search_filter is not None:
            search_results = qdrant_client.query_points(
                collection_name=request.collection,
                query=embeddings[0],
                limit=request.n_results,
                with_payload=True,
                query_filter=search_filter,
            ).points
        else:
            search_results = qdrant_client.query_points(
                collection_name=request.collection,
                query=embeddings[0],
                limit=request.n_results,
                with_payload=True,
            ).points

        context_items: List[ContextItem] = []
        for point in search_results:
            payload = point.payload or {}
            score = float(point.score or 0.0)
            if QDRANT_DISTANCE.lower() == "cosine":
                distance_value = max(0.0, 1 - score)
            else:
                distance_value = score
            context_items.append(
                ContextItem(
                    id=str(point.id),
                    content=extract_payload_content(payload),
                    metadata=payload,
                    distance=round(distance_value, 6),
                    relevance_score=round(score, 6),
                )
            )

        end_time = datetime.utcnow()
        retrieval_time = (end_time - start_time).total_seconds() * 1000

        try:
            await log_query_to_memory(
                request.query, request.collection, len(context_items)
            )
        except Exception as e:
            print(f"Failed to log query to memory server: {e}")

        return QueryResponse(
            query=request.query,
            results=context_items,
            collection=request.collection,
            total_found=len(context_items),
            retrieval_time_ms=round(retrieval_time, 2),
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
            message="Mock mode: Documents simulated as indexed",
        )

    try:
        ensure_collection(request.collection)

        doc_count = len(request.documents)
        if doc_count == 0:
            return IndexResponse(
                success=True,
                indexed_count=0,
                collection=request.collection,
                message="No documents provided",
            )

        metadatas = request.metadatas or [{} for _ in range(doc_count)]
        if len(metadatas) != doc_count:
            raise HTTPException(
                status_code=400, detail="metadatas length must match documents length"
            )

        ids = request.ids or []
        if ids and len(ids) != doc_count:
            raise HTTPException(
                status_code=400, detail="ids length must match documents length"
            )
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

        embedding_model_name = (
            OPENAI_EMBEDDING_MODEL if OPENAI_API_KEY else OLLAMA_EMBEDDING_MODEL
        )
        return IndexResponse(
            success=True,
            indexed_count=len(points),
            collection=request.collection,
            message=f"Indexed {len(points)} documents with {type(embedding_model).__name__} ({embedding_model_name}).",
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
            result.append(
                CollectionInfo(name=col.name, count=col_info.points_count, metadata={})
            )
        return result
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to list collections: {str(e)}"
        )


# Library cache stats endpoint (DEV-194)
@app.get("/library-cache/stats")
async def library_cache_stats():
    """
    Get library cache statistics and collection info.

    Returns information about the library_registry collection
    used for Context7 library ID caching.
    """
    if not qdrant_client:
        return {"error": "Qdrant not available", "status": "disconnected"}

    try:
        collection_info = qdrant_client.get_collection("library_registry")

        return {
            "collection": "library_registry",
            "total_libraries": collection_info.points_count,
            "status": "active",
            "description": "Context7 library ID cache for token-efficient lookups",
            "related_issue": "DEV-194",
            "estimated_savings": {
                "tokens_per_hit": 1000,
                "potential_daily_savings": collection_info.points_count * 10 * 1000,
                "note": "Assuming ~10 lookups per library per day",
            },
        }
    except Exception as e:
        return {
            "collection": "library_registry",
            "status": "not_initialized",
            "error": str(e),
            "action": "Run: python support/scripts/rag/index_library_registry.py",
        }


# ============================================================================
# Agent Memory Endpoints (Cross-Agent Knowledge Sharing)
# ============================================================================


@app.post("/memory/store", response_model=StoreInsightResponse)
async def store_insight(request: StoreInsightRequest):
    """
    Store an agent insight for cross-agent knowledge sharing.

    Insights are semantically indexed and can be retrieved by other agents
    to benefit from collective learning.
    """
    if not qdrant_client:
        raise HTTPException(
            status_code=503,
            detail="Qdrant not available. Cannot store insights.",
        )

    try:
        ensure_collection(AGENT_MEMORY_COLLECTION)

        # Generate embedding for the insight content
        content_for_embedding = f"{request.insight_type.value}: {request.content}"
        if request.context:
            content_for_embedding += f" Context: {request.context}"
        if request.resolution:
            content_for_embedding += f" Resolution: {request.resolution}"

        embeddings = await embed_texts([content_for_embedding])
        if not embeddings:
            raise HTTPException(
                status_code=500, detail="Failed to generate embedding for insight"
            )

        insight_id = str(uuid.uuid4())
        timestamp = datetime.utcnow().isoformat()

        payload = {
            "agent_id": request.agent_id,
            "insight_type": request.insight_type.value,
            "content": request.content[:2000],  # Enforce max length
            "context": request.context,
            "resolution": request.resolution,
            "confidence": request.confidence,
            "timestamp": timestamp,
            "usage_count": 0,
            "relevance_decay": 1.0,
            **(request.metadata or {}),
        }

        point = PointStruct(id=insight_id, vector=embeddings[0], payload=payload)
        qdrant_client.upsert(collection_name=AGENT_MEMORY_COLLECTION, points=[point])

        logger.info(
            f"Stored insight {insight_id} from {request.agent_id}: {request.insight_type.value}"
        )

        return StoreInsightResponse(
            success=True,
            insight_id=insight_id,
            agent_id=request.agent_id,
            message=f"Insight stored successfully as {request.insight_type.value}",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to store insight: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to store insight: {str(e)}")


@app.post("/memory/query", response_model=QueryMemoryResponse)
async def query_memory(request: QueryMemoryRequest):
    """
    Query agent memory for relevant insights.

    Performs semantic search across all agent insights with optional filters.
    """
    if not qdrant_client:
        raise HTTPException(
            status_code=503,
            detail="Qdrant not available. Cannot query insights.",
        )

    start_time = datetime.utcnow()

    try:
        ensure_collection(AGENT_MEMORY_COLLECTION)

        embeddings = await embed_texts([request.query])
        if not embeddings:
            raise HTTPException(
                status_code=500, detail="Failed to generate query embedding"
            )

        # Build filters
        must_conditions = []

        if request.agent_id:
            must_conditions.append(
                FieldCondition(key="agent_id", match=MatchValue(value=request.agent_id))
            )

        if request.insight_types:
            # Should match any of the specified types
            should_type_conditions = [
                FieldCondition(
                    key="insight_type", match=MatchValue(value=it.value)
                )
                for it in request.insight_types
            ]
            # Use a nested filter for OR logic on types
            if len(should_type_conditions) == 1:
                must_conditions.append(should_type_conditions[0])
            else:
                must_conditions.append(
                    Filter(should=should_type_conditions, min_should=1)
                )

        search_filter = Filter(must=must_conditions) if must_conditions else None

        # Query with filter
        if search_filter:
            search_results = qdrant_client.query_points(
                collection_name=AGENT_MEMORY_COLLECTION,
                query=embeddings[0],
                limit=request.n_results * 2,  # Fetch extra for confidence filtering
                with_payload=True,
                query_filter=search_filter,
            ).points
        else:
            search_results = qdrant_client.query_points(
                collection_name=AGENT_MEMORY_COLLECTION,
                query=embeddings[0],
                limit=request.n_results * 2,
                with_payload=True,
            ).points

        # Filter by confidence and build response
        insights: List[MemoryInsight] = []
        for point in search_results:
            payload = point.payload or {}
            confidence = float(payload.get("confidence", 0.8))

            if confidence < request.min_confidence:
                continue

            score = float(point.score or 0.0)

            insights.append(
                MemoryInsight(
                    id=str(point.id),
                    agent_id=payload.get("agent_id", "unknown"),
                    insight_type=InsightType(payload.get("insight_type", "code_pattern")),
                    content=payload.get("content", ""),
                    context=payload.get("context"),
                    resolution=payload.get("resolution"),
                    confidence=confidence,
                    relevance_score=round(score, 4),
                    timestamp=payload.get("timestamp", ""),
                    usage_count=int(payload.get("usage_count", 0)),
                    metadata={
                        k: v
                        for k, v in payload.items()
                        if k
                        not in {
                            "agent_id",
                            "insight_type",
                            "content",
                            "context",
                            "resolution",
                            "confidence",
                            "timestamp",
                            "usage_count",
                            "relevance_decay",
                        }
                    },
                )
            )

            if len(insights) >= request.n_results:
                break

        end_time = datetime.utcnow()
        retrieval_time = (end_time - start_time).total_seconds() * 1000

        return QueryMemoryResponse(
            query=request.query,
            results=insights,
            total_found=len(insights),
            retrieval_time_ms=round(retrieval_time, 2),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to query memory: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to query memory: {str(e)}")


@app.get("/memory/agent/{agent_id}", response_model=QueryMemoryResponse)
async def get_agent_insights(
    agent_id: str, limit: int = 10, insight_type: Optional[InsightType] = None
):
    """
    Get insights stored by a specific agent.

    Returns the most recent insights from the specified agent.
    """
    if not qdrant_client:
        raise HTTPException(
            status_code=503,
            detail="Qdrant not available.",
        )

    start_time = datetime.utcnow()

    try:
        ensure_collection(AGENT_MEMORY_COLLECTION)

        # Build filter for agent_id
        must_conditions = [
            FieldCondition(key="agent_id", match=MatchValue(value=agent_id))
        ]

        if insight_type:
            must_conditions.append(
                FieldCondition(
                    key="insight_type", match=MatchValue(value=insight_type.value)
                )
            )

        search_filter = Filter(must=must_conditions)

        # Scroll through points (no query vector needed)
        scroll_results = qdrant_client.scroll(
            collection_name=AGENT_MEMORY_COLLECTION,
            scroll_filter=search_filter,
            limit=limit,
            with_payload=True,
            with_vectors=False,
        )

        insights: List[MemoryInsight] = []
        for point in scroll_results[0]:
            payload = point.payload or {}
            insights.append(
                MemoryInsight(
                    id=str(point.id),
                    agent_id=payload.get("agent_id", agent_id),
                    insight_type=InsightType(payload.get("insight_type", "code_pattern")),
                    content=payload.get("content", ""),
                    context=payload.get("context"),
                    resolution=payload.get("resolution"),
                    confidence=float(payload.get("confidence", 0.8)),
                    relevance_score=1.0,  # No query-based relevance
                    timestamp=payload.get("timestamp", ""),
                    usage_count=int(payload.get("usage_count", 0)),
                    metadata={
                        k: v
                        for k, v in payload.items()
                        if k
                        not in {
                            "agent_id",
                            "insight_type",
                            "content",
                            "context",
                            "resolution",
                            "confidence",
                            "timestamp",
                            "usage_count",
                            "relevance_decay",
                        }
                    },
                )
            )

        # Sort by timestamp descending
        insights.sort(key=lambda x: x.timestamp, reverse=True)

        end_time = datetime.utcnow()
        retrieval_time = (end_time - start_time).total_seconds() * 1000

        return QueryMemoryResponse(
            query=f"agent:{agent_id}",
            results=insights[:limit],
            total_found=len(insights),
            retrieval_time_ms=round(retrieval_time, 2),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get agent insights: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to get agent insights: {str(e)}"
        )


@app.get("/memory/stats", response_model=AgentMemoryStats)
async def get_memory_stats():
    """
    Get statistics about agent memory.

    Returns aggregate statistics across all agents and insight types.
    """
    if not qdrant_client:
        raise HTTPException(
            status_code=503,
            detail="Qdrant not available.",
        )

    try:
        ensure_collection(AGENT_MEMORY_COLLECTION)

        collection_info = qdrant_client.get_collection(AGENT_MEMORY_COLLECTION)
        total_insights = collection_info.points_count

        if total_insights == 0:
            return AgentMemoryStats(
                total_insights=0,
                insights_by_type={},
                insights_by_agent={},
                avg_confidence=0.0,
                oldest_insight=None,
                newest_insight=None,
            )

        # Scroll through all points to calculate stats
        # Note: For large collections, this should be optimized with aggregations
        all_points, _ = qdrant_client.scroll(
            collection_name=AGENT_MEMORY_COLLECTION,
            limit=1000,  # Cap for performance
            with_payload=True,
            with_vectors=False,
        )

        insights_by_type: Dict[str, int] = {}
        insights_by_agent: Dict[str, int] = {}
        confidences: List[float] = []
        timestamps: List[str] = []

        for point in all_points:
            payload = point.payload or {}

            insight_type = payload.get("insight_type", "unknown")
            insights_by_type[insight_type] = insights_by_type.get(insight_type, 0) + 1

            agent_id = payload.get("agent_id", "unknown")
            insights_by_agent[agent_id] = insights_by_agent.get(agent_id, 0) + 1

            if "confidence" in payload:
                confidences.append(float(payload["confidence"]))

            if "timestamp" in payload:
                timestamps.append(payload["timestamp"])

        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
        timestamps.sort()

        return AgentMemoryStats(
            total_insights=total_insights,
            insights_by_type=insights_by_type,
            insights_by_agent=insights_by_agent,
            avg_confidence=round(avg_confidence, 3),
            oldest_insight=timestamps[0] if timestamps else None,
            newest_insight=timestamps[-1] if timestamps else None,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get memory stats: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to get memory stats: {str(e)}"
        )


@app.delete("/memory/prune")
async def prune_old_insights(max_age_days: int = 30, max_per_agent: int = 1000):
    """
    Prune old or excessive insights from agent memory.

    Removes insights older than max_age_days and caps per-agent count.
    """
    if not qdrant_client:
        raise HTTPException(
            status_code=503,
            detail="Qdrant not available.",
        )

    try:
        ensure_collection(AGENT_MEMORY_COLLECTION)

        from datetime import timedelta

        cutoff_date = (datetime.utcnow() - timedelta(days=max_age_days)).isoformat()

        # Get all points to evaluate
        all_points, _ = qdrant_client.scroll(
            collection_name=AGENT_MEMORY_COLLECTION,
            limit=10000,
            with_payload=True,
            with_vectors=False,
        )

        points_to_delete: List[str] = []
        agent_counts: Dict[str, List[tuple]] = {}  # agent_id -> [(id, timestamp)]

        for point in all_points:
            payload = point.payload or {}
            point_id = str(point.id)
            timestamp = payload.get("timestamp", "")
            agent_id = payload.get("agent_id", "unknown")

            # Mark for deletion if too old
            if timestamp and timestamp < cutoff_date:
                points_to_delete.append(point_id)
                continue

            # Track per-agent counts
            if agent_id not in agent_counts:
                agent_counts[agent_id] = []
            agent_counts[agent_id].append((point_id, timestamp))

        # Enforce per-agent cap
        for agent_id, point_list in agent_counts.items():
            if len(point_list) > max_per_agent:
                # Sort by timestamp and delete oldest
                point_list.sort(key=lambda x: x[1])
                excess = len(point_list) - max_per_agent
                for i in range(excess):
                    points_to_delete.append(point_list[i][0])

        # Delete points
        if points_to_delete:
            qdrant_client.delete(
                collection_name=AGENT_MEMORY_COLLECTION,
                points_selector=points_to_delete,
            )

        logger.info(f"Pruned {len(points_to_delete)} insights from agent memory")

        return {
            "success": True,
            "pruned_count": len(points_to_delete),
            "max_age_days": max_age_days,
            "max_per_agent": max_per_agent,
            "message": f"Pruned {len(points_to_delete)} old or excess insights",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to prune insights: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to prune insights: {str(e)}"
        )


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
        mock_results.append(
            ContextItem(
                id="mock-auth-1",
                content="JWT authentication implementation using FastAPI dependencies. Use OAuth2PasswordBearer for token validation.",
                metadata={"source": "auth_patterns.py", "type": "code"},
                distance=0.15,
                relevance_score=0.87,
            )
        )
        mock_results.append(
            ContextItem(
                id="mock-auth-2",
                content="User authentication flow: 1) Client sends credentials, 2) Server validates and generates JWT, 3) Client includes JWT in Authorization header",
                metadata={"source": "auth_workflow.md", "type": "documentation"},
                distance=0.22,
                relevance_score=0.82,
            )
        )

    if "api" in request.query.lower() or "endpoint" in request.query.lower():
        mock_results.append(
            ContextItem(
                id="mock-api-1",
                content="FastAPI endpoint pattern: @app.post('/endpoint') with Pydantic request/response models. Include error handling and logging.",
                metadata={"source": "api_patterns.py", "type": "code"},
                distance=0.18,
                relevance_score=0.85,
            )
        )

    if "docker" in request.query.lower() or "deployment" in request.query.lower():
        mock_results.append(
            ContextItem(
                id="mock-deploy-1",
                content="Docker deployment using multi-stage builds. Python 3.11-slim base, copy requirements first for caching, then application code.",
                metadata={"source": "docker_patterns.md", "type": "documentation"},
                distance=0.20,
                relevance_score=0.83,
            )
        )

    # Default fallback
    if not mock_results:
        mock_results.append(
            ContextItem(
                id="mock-default-1",
                content=f"Context related to: {request.query}. This is mock data for development.",
                metadata={"source": "mock_data", "type": "synthetic"},
                distance=0.30,
                relevance_score=0.77,
            )
        )

    # Log mock query to memory server for analytics (non-blocking)
    try:
        await log_query_to_memory(request.query, request.collection, len(mock_results))
    except Exception as e:
        print(f"Failed to log mock query to memory server: {e}")

    return QueryResponse(
        query=request.query,
        results=mock_results[: request.n_results],
        collection=request.collection,
        total_found=len(mock_results),
        retrieval_time_ms=5.0,
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8007)
