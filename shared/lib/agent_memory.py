"""
Agent Memory Manager for Cross-Agent Knowledge Sharing.

Provides persistent agent memory using Qdrant semantic search.
Replaces deprecated LangChain memory with lightweight implementation.

Features:
- Store insights extracted from agent executions
- Retrieve semantically similar insights across agents
- Per-agent history and cross-agent knowledge sharing
- Automatic pruning based on usage and TTL
"""

import logging
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum

from pydantic import BaseModel, Field
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue,
    Range,
    UpdateStatus,
)

logger = logging.getLogger(__name__)


class InsightType(str, Enum):
    """Types of insights that agents can capture."""

    ARCHITECTURAL_DECISION = "architectural_decision"
    ERROR_PATTERN = "error_pattern"
    CODE_PATTERN = "code_pattern"
    TASK_RESOLUTION = "task_resolution"
    SECURITY_FINDING = "security_finding"


@dataclass
class Insight:
    """Represents a stored agent insight."""

    id: str
    agent_id: str
    insight_type: InsightType
    content: str
    source_workflow_id: Optional[str] = None
    source_task: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    usage_count: int = 0
    relevance_score: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_payload(self) -> Dict[str, Any]:
        """Convert to Qdrant payload format."""
        return {
            "id": self.id,
            "agent_id": self.agent_id,
            "insight_type": (
                self.insight_type.value
                if isinstance(self.insight_type, InsightType)
                else self.insight_type
            ),
            "content": self.content,
            "source_workflow_id": self.source_workflow_id,
            "source_task": self.source_task,
            "timestamp": self.timestamp.isoformat(),
            "usage_count": self.usage_count,
            "relevance_score": self.relevance_score,
            "metadata": self.metadata,
        }

    @classmethod
    def from_payload(cls, payload: Dict[str, Any], score: float = 0.0) -> "Insight":
        """Create Insight from Qdrant payload."""
        return cls(
            id=payload.get("id", ""),
            agent_id=payload.get("agent_id", ""),
            insight_type=payload.get("insight_type", ""),
            content=payload.get("content", ""),
            source_workflow_id=payload.get("source_workflow_id"),
            source_task=payload.get("source_task"),
            timestamp=(
                datetime.fromisoformat(payload["timestamp"])
                if payload.get("timestamp")
                else datetime.utcnow()
            ),
            usage_count=payload.get("usage_count", 0),
            relevance_score=score,
            metadata=payload.get("metadata", {}),
        )


class StoreInsightRequest(BaseModel):
    """Request model for storing an insight."""

    agent_id: str = Field(..., description="ID of the agent storing the insight")
    insight_type: str = Field(..., description="Type of insight")
    content: str = Field(..., description="The insight content")
    source_workflow_id: Optional[str] = Field(
        None, description="Workflow that generated this insight"
    )
    source_task: Optional[str] = Field(
        None, description="Task description that led to this insight"
    )
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)


class QueryInsightsRequest(BaseModel):
    """Request model for querying insights."""

    query: str = Field(..., description="Semantic query for relevant insights")
    agent_id: Optional[str] = Field(
        None, description="Filter by agent ID (None = cross-agent)"
    )
    insight_types: Optional[List[str]] = Field(
        None, description="Filter by insight types"
    )
    limit: int = Field(5, ge=1, le=20, description="Max results to return")


class AgentMemoryManager:
    """
    Persistent agent memory using Qdrant semantic search.

    Provides cross-agent knowledge sharing by storing and retrieving
    insights extracted from agent executions.
    """

    COLLECTION_NAME = "agent_memory"
    VECTOR_SIZE = 1536  # text-embedding-3-small

    def __init__(
        self,
        qdrant_client: QdrantClient,
        embedding_model: Any,  # LangChain embedding model
        max_insights_per_agent: int = 1000,
        ttl_days: int = 30,
    ):
        """
        Initialize AgentMemoryManager.

        Args:
            qdrant_client: Initialized Qdrant client
            embedding_model: LangChain embedding model for vectorization
            max_insights_per_agent: Maximum insights to keep per agent
            ttl_days: Days before unused insights are pruned
        """
        self.client = qdrant_client
        self.embedding_model = embedding_model
        self.max_insights_per_agent = max_insights_per_agent
        self.ttl_days = ttl_days

        # Ensure collection exists
        self._ensure_collection()

    def _ensure_collection(self) -> None:
        """Create agent_memory collection if it doesn't exist."""
        try:
            collections = self.client.get_collections().collections
            collection_names = [c.name for c in collections]

            if self.COLLECTION_NAME not in collection_names:
                logger.info(f"Creating collection: {self.COLLECTION_NAME}")
                self.client.create_collection(
                    collection_name=self.COLLECTION_NAME,
                    vectors_config=VectorParams(
                        size=self.VECTOR_SIZE,
                        distance=Distance.COSINE,
                    ),
                )
                logger.info(f"Collection {self.COLLECTION_NAME} created successfully")
            else:
                logger.debug(f"Collection {self.COLLECTION_NAME} already exists")
        except Exception as e:
            logger.error(f"Failed to ensure collection: {e}")
            raise

    async def store_insight(
        self,
        agent_id: str,
        insight_type: str,
        content: str,
        source_workflow_id: Optional[str] = None,
        source_task: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Store an insight extracted from agent execution.

        Args:
            agent_id: ID of the agent storing the insight
            insight_type: Type of insight (architectural_decision, error_pattern, etc.)
            content: The insight content
            source_workflow_id: Workflow that generated this insight
            source_task: Task description that led to this insight
            metadata: Additional metadata

        Returns:
            ID of the stored insight
        """
        insight_id = str(uuid.uuid4())

        # Create insight object
        insight = Insight(
            id=insight_id,
            agent_id=agent_id,
            insight_type=insight_type,
            content=content,
            source_workflow_id=source_workflow_id,
            source_task=source_task,
            timestamp=datetime.utcnow(),
            usage_count=0,
            relevance_score=0.0,
            metadata=metadata or {},
        )

        try:
            # Generate embedding for the content
            embedding = await self._get_embedding(content)

            # Store in Qdrant
            self.client.upsert(
                collection_name=self.COLLECTION_NAME,
                points=[
                    PointStruct(
                        id=insight_id,
                        vector=embedding,
                        payload=insight.to_payload(),
                    )
                ],
            )

            logger.info(
                f"Stored insight {insight_id} from agent {agent_id} "
                f"(type: {insight_type}, workflow: {source_workflow_id})"
            )

            # Check if pruning is needed
            await self._maybe_prune_agent_insights(agent_id)

            return insight_id

        except Exception as e:
            logger.error(f"Failed to store insight: {e}")
            raise

    async def retrieve_relevant(
        self,
        query: str,
        agent_id: Optional[str] = None,
        insight_types: Optional[List[str]] = None,
        limit: int = 5,
    ) -> List[Insight]:
        """
        Retrieve semantically similar insights.

        Args:
            query: Semantic query for relevant insights
            agent_id: Filter by agent ID (None = cross-agent search)
            insight_types: Filter by insight types
            limit: Maximum results to return

        Returns:
            List of relevant insights sorted by similarity
        """
        try:
            # Generate query embedding
            query_embedding = await self._get_embedding(query)

            # Build filter conditions
            filter_conditions = []

            if agent_id:
                filter_conditions.append(
                    FieldCondition(
                        key="agent_id",
                        match=MatchValue(value=agent_id),
                    )
                )

            if insight_types:
                # Match any of the specified types
                for insight_type in insight_types:
                    filter_conditions.append(
                        FieldCondition(
                            key="insight_type",
                            match=MatchValue(value=insight_type),
                        )
                    )

            # Build filter
            search_filter = None
            if filter_conditions:
                search_filter = Filter(must=filter_conditions)

            # Search for similar insights
            results = self.client.search(
                collection_name=self.COLLECTION_NAME,
                query_vector=query_embedding,
                query_filter=search_filter,
                limit=limit,
            )

            # Convert to Insight objects and increment usage
            insights = []
            for result in results:
                insight = Insight.from_payload(result.payload, score=result.score)
                insights.append(insight)

                # Increment usage count asynchronously
                await self._increment_usage_count(result.id)

            logger.debug(
                f"Retrieved {len(insights)} insights for query "
                f"(agent: {agent_id}, types: {insight_types})"
            )

            return insights

        except Exception as e:
            logger.error(f"Failed to retrieve insights: {e}")
            return []

    async def get_agent_history(
        self,
        agent_id: str,
        limit: int = 20,
    ) -> List[Insight]:
        """
        Get recent insights from a specific agent.

        Args:
            agent_id: ID of the agent
            limit: Maximum results to return

        Returns:
            List of recent insights from the agent
        """
        try:
            # Scroll through agent's insights (no vector search needed)
            results, _ = self.client.scroll(
                collection_name=self.COLLECTION_NAME,
                scroll_filter=Filter(
                    must=[
                        FieldCondition(
                            key="agent_id",
                            match=MatchValue(value=agent_id),
                        )
                    ]
                ),
                limit=limit,
                with_payload=True,
                with_vectors=False,
            )

            # Convert to Insight objects and sort by timestamp
            insights = [Insight.from_payload(r.payload) for r in results]
            insights.sort(key=lambda x: x.timestamp, reverse=True)

            return insights[:limit]

        except Exception as e:
            logger.error(f"Failed to get agent history: {e}")
            return []

    async def get_stats(self) -> Dict[str, Any]:
        """Get memory collection statistics."""
        try:
            collection_info = self.client.get_collection(self.COLLECTION_NAME)

            # Get per-agent counts by scrolling
            all_points, _ = self.client.scroll(
                collection_name=self.COLLECTION_NAME,
                limit=10000,
                with_payload=True,
                with_vectors=False,
            )

            # Aggregate stats
            agent_counts: Dict[str, int] = {}
            type_counts: Dict[str, int] = {}

            for point in all_points:
                agent_id = point.payload.get("agent_id", "unknown")
                insight_type = point.payload.get("insight_type", "unknown")

                agent_counts[agent_id] = agent_counts.get(agent_id, 0) + 1
                type_counts[insight_type] = type_counts.get(insight_type, 0) + 1

            return {
                "collection": self.COLLECTION_NAME,
                "total_insights": collection_info.points_count,
                "per_agent": agent_counts,
                "per_type": type_counts,
                "vector_size": self.VECTOR_SIZE,
                "max_per_agent": self.max_insights_per_agent,
                "ttl_days": self.ttl_days,
            }

        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            return {"error": str(e)}

    async def _get_embedding(self, text: str) -> List[float]:
        """Generate embedding for text."""
        try:
            # LangChain embeddings support both sync and async
            if hasattr(self.embedding_model, "aembed_query"):
                embedding = await self.embedding_model.aembed_query(text)
            else:
                embedding = self.embedding_model.embed_query(text)
            return embedding
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            raise

    async def _increment_usage_count(self, point_id: str) -> None:
        """Increment usage count for an insight."""
        try:
            # Get current payload
            points = self.client.retrieve(
                collection_name=self.COLLECTION_NAME,
                ids=[point_id],
                with_payload=True,
            )

            if points:
                payload = points[0].payload
                payload["usage_count"] = payload.get("usage_count", 0) + 1

                # Update payload
                self.client.set_payload(
                    collection_name=self.COLLECTION_NAME,
                    payload={"usage_count": payload["usage_count"]},
                    points=[point_id],
                )
        except Exception as e:
            logger.debug(f"Failed to increment usage count: {e}")

    async def _maybe_prune_agent_insights(self, agent_id: str) -> None:
        """Prune oldest insights if agent exceeds max limit."""
        try:
            # Get count for this agent
            results, _ = self.client.scroll(
                collection_name=self.COLLECTION_NAME,
                scroll_filter=Filter(
                    must=[
                        FieldCondition(
                            key="agent_id",
                            match=MatchValue(value=agent_id),
                        )
                    ]
                ),
                limit=self.max_insights_per_agent + 100,  # Get extras to check
                with_payload=True,
                with_vectors=False,
            )

            if len(results) > self.max_insights_per_agent:
                # Sort by usage count (ascending) then timestamp (oldest first)
                results.sort(
                    key=lambda x: (
                        x.payload.get("usage_count", 0),
                        x.payload.get("timestamp", ""),
                    )
                )

                # Delete excess insights
                excess_count = len(results) - self.max_insights_per_agent
                to_delete = [r.id for r in results[:excess_count]]

                self.client.delete(
                    collection_name=self.COLLECTION_NAME,
                    points_selector=to_delete,
                )

                logger.info(
                    f"Pruned {excess_count} insights from agent {agent_id} "
                    f"(exceeded max {self.max_insights_per_agent})"
                )

        except Exception as e:
            logger.warning(f"Failed to prune agent insights: {e}")

    async def prune_expired_insights(self) -> int:
        """
        Prune insights that haven't been used within TTL period.
        Should be called periodically (e.g., daily cron job).

        Returns:
            Number of insights pruned
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=self.ttl_days)
            cutoff_iso = cutoff_date.isoformat()

            # Find expired insights with low usage
            results, _ = self.client.scroll(
                collection_name=self.COLLECTION_NAME,
                scroll_filter=Filter(
                    must=[
                        FieldCondition(
                            key="usage_count",
                            range=Range(lte=1),  # Rarely used
                        )
                    ]
                ),
                limit=10000,
                with_payload=True,
                with_vectors=False,
            )

            # Filter by timestamp
            to_delete = []
            for r in results:
                timestamp_str = r.payload.get("timestamp", "")
                if timestamp_str and timestamp_str < cutoff_iso:
                    to_delete.append(r.id)

            if to_delete:
                self.client.delete(
                    collection_name=self.COLLECTION_NAME,
                    points_selector=to_delete,
                )
                logger.info(
                    f"Pruned {len(to_delete)} expired insights (TTL: {self.ttl_days} days)"
                )

            return len(to_delete)

        except Exception as e:
            logger.error(f"Failed to prune expired insights: {e}")
            return 0


# Singleton instance
_memory_manager: Optional[AgentMemoryManager] = None


def get_agent_memory_manager() -> Optional[AgentMemoryManager]:
    """Get the singleton AgentMemoryManager instance."""
    return _memory_manager


def init_agent_memory_manager(
    qdrant_client: QdrantClient,
    embedding_model: Any,
    max_insights_per_agent: int = 1000,
    ttl_days: int = 30,
) -> AgentMemoryManager:
    """
    Initialize the singleton AgentMemoryManager.

    Args:
        qdrant_client: Initialized Qdrant client
        embedding_model: LangChain embedding model
        max_insights_per_agent: Maximum insights per agent
        ttl_days: TTL for unused insights

    Returns:
        Initialized AgentMemoryManager
    """
    global _memory_manager
    _memory_manager = AgentMemoryManager(
        qdrant_client=qdrant_client,
        embedding_model=embedding_model,
        max_insights_per_agent=max_insights_per_agent,
        ttl_days=ttl_days,
    )
    logger.info("AgentMemoryManager initialized")
    return _memory_manager
