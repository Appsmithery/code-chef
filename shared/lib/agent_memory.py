"""
Agent Memory Manager for Cross-Agent Knowledge Sharing.

Provides persistent agent memory using RAG service HTTP endpoints.
Replaces deprecated LangChain memory with lightweight HTTP-based implementation.

Architecture Decision (CHEF-199):
- Uses HTTP calls to RAG service endpoints instead of direct Qdrant access
- Centralized monitoring via RAG service logs
- Consistent embedding generation (single OpenAI client in RAG service)
- Easier rate limiting, caching, and metrics

Features:
- Store insights extracted from agent executions
- Retrieve semantically similar insights across agents
- Per-agent history and cross-agent knowledge sharing
- Automatic pruning based on usage and TTL

Issues: CHEF-198 (shared types), CHEF-199 (RAG refactor), CHEF-200 (@traceable)
"""

import os
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field

import httpx
from langsmith import traceable

# Import canonical types from shared location
from .core_types import InsightType, CapturedInsight

logger = logging.getLogger(__name__)


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
        """Convert to JSON payload format for API calls."""
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
            "timestamp": (
                self.timestamp.isoformat()
                if isinstance(self.timestamp, datetime)
                else self.timestamp
            ),
            "usage_count": self.usage_count,
            "relevance_score": self.relevance_score,
            "metadata": self.metadata,
        }

    @classmethod
    def from_payload(cls, payload: Dict[str, Any], score: float = 0.0) -> "Insight":
        """Create Insight from API response payload."""
        timestamp = payload.get("timestamp")
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp)
        elif timestamp is None:
            timestamp = datetime.utcnow()

        insight_type = payload.get("insight_type", "task_resolution")
        if isinstance(insight_type, str):
            try:
                insight_type = InsightType(insight_type)
            except ValueError:
                insight_type = InsightType.TASK_RESOLUTION

        return cls(
            id=payload.get("id", ""),
            agent_id=payload.get("agent_id", ""),
            insight_type=insight_type,
            content=payload.get("content", ""),
            source_workflow_id=payload.get("source_workflow_id"),
            source_task=payload.get("source_task"),
            timestamp=timestamp,
            usage_count=payload.get("usage_count", 0),
            relevance_score=score if score > 0 else payload.get("relevance_score", 0.0),
            metadata=payload.get("metadata", {}),
        )


class AgentMemoryManager:
    """
    Persistent agent memory using RAG service HTTP endpoints.

    Provides cross-agent knowledge sharing by storing and retrieving
    insights extracted from agent executions via centralized RAG service.

    Architecture: HTTP client → RAG service (:8007) → Qdrant Cloud
    """

    def __init__(
        self,
        agent_id: str,
        rag_service_url: Optional[str] = None,
        timeout: float = 30.0,
    ):
        """
        Initialize AgentMemoryManager with RAG service connection.

        Args:
            agent_id: ID of the agent using this memory manager
            rag_service_url: URL of RAG service (default from env)
            timeout: HTTP request timeout in seconds
        """
        self.agent_id = agent_id
        self.rag_url = rag_service_url or os.getenv(
            "RAG_SERVICE_URL", "http://rag-context:8007"
        )
        self._timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None

        # Track last extracted insights for graph.py node collection
        self.last_extracted_insights: List[Dict[str, Any]] = []

        logger.info(
            f"[AgentMemory] Initialized for agent={agent_id}, rag_url={self.rag_url}"
        )

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create async HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=self._timeout)
        return self._client

    async def close(self) -> None:
        """Close HTTP client connection."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    @traceable(name="memory_store_insight", tags=["memory", "rag"])
    async def store_insight(
        self,
        insight_type: InsightType,
        content: str,
        source_workflow_id: Optional[str] = None,
        source_task: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Store an insight extracted from agent execution via RAG service.

        Args:
            insight_type: Type of insight (architectural_decision, error_pattern, etc.)
            content: The insight content
            source_workflow_id: Workflow that generated this insight
            source_task: Task description that led to this insight
            metadata: Additional metadata

        Returns:
            ID of the stored insight
        """
        client = await self._get_client()

        payload = {
            "agent_id": self.agent_id,
            "insight_type": (
                insight_type.value
                if isinstance(insight_type, InsightType)
                else insight_type
            ),
            "content": content,
            "source_workflow_id": source_workflow_id,
            "source_task": source_task,
            "metadata": metadata or {},
        }

        try:
            response = await client.post(
                f"{self.rag_url}/memory/store",
                json=payload,
            )
            response.raise_for_status()
            result = response.json()

            insight_id = result.get("insight_id", result.get("id", ""))
            logger.info(
                f"[AgentMemory] Stored insight {insight_id} from agent {self.agent_id} "
                f"(type: {insight_type}, workflow: {source_workflow_id})"
            )

            # Track for graph.py collection
            self.last_extracted_insights.append(
                {
                    "id": insight_id,
                    "type": (
                        insight_type.value
                        if isinstance(insight_type, InsightType)
                        else insight_type
                    ),
                    "content": content[:500],  # Truncate for state
                    "confidence": 0.8,
                }
            )

            return insight_id

        except httpx.HTTPStatusError as e:
            logger.error(
                f"[AgentMemory] RAG service error storing insight: {e.response.status_code}"
            )
            raise
        except httpx.RequestError as e:
            logger.error(f"[AgentMemory] Failed to connect to RAG service: {e}")
            raise

    @traceable(name="memory_retrieve_relevant", tags=["memory", "rag"])
    async def retrieve_relevant(
        self,
        query: str,
        agent_id: Optional[str] = None,
        insight_types: Optional[List[str]] = None,
        limit: int = 5,
        min_confidence: float = 0.0,
    ) -> List[Insight]:
        """
        Retrieve semantically similar insights via RAG service.

        Args:
            query: Semantic query for relevant insights
            agent_id: Filter by agent ID (None = cross-agent search)
            insight_types: Filter by insight types
            limit: Maximum results to return
            min_confidence: Minimum similarity score threshold

        Returns:
            List of relevant insights sorted by similarity
        """
        client = await self._get_client()

        payload = {
            "query": query,
            "agent_id": agent_id,
            "insight_types": insight_types,
            "limit": limit,
            "min_confidence": min_confidence,
        }

        try:
            response = await client.post(
                f"{self.rag_url}/memory/query",
                json=payload,
            )
            response.raise_for_status()
            result = response.json()

            insights = []
            for item in result.get("insights", []):
                insight = Insight.from_payload(item, score=item.get("score", 0.0))
                if insight.relevance_score >= min_confidence:
                    insights.append(insight)

            logger.debug(
                f"[AgentMemory] Retrieved {len(insights)} insights for query "
                f"(agent: {agent_id}, types: {insight_types})"
            )

            return insights

        except httpx.HTTPStatusError as e:
            logger.error(
                f"[AgentMemory] RAG service error querying insights: {e.response.status_code}"
            )
            return []
        except httpx.RequestError as e:
            logger.error(f"[AgentMemory] Failed to connect to RAG service: {e}")
            return []

    @traceable(name="memory_get_agent_history", tags=["memory", "rag"])
    async def get_agent_history(
        self,
        agent_id: Optional[str] = None,
        limit: int = 20,
    ) -> List[Insight]:
        """
        Get recent insights from a specific agent via RAG service.

        Args:
            agent_id: ID of the agent (defaults to self.agent_id)
            limit: Maximum results to return

        Returns:
            List of recent insights from the agent
        """
        client = await self._get_client()
        target_agent = agent_id or self.agent_id

        try:
            response = await client.get(
                f"{self.rag_url}/memory/agent/{target_agent}",
                params={"limit": limit},
            )
            response.raise_for_status()
            result = response.json()

            insights = [
                Insight.from_payload(item) for item in result.get("insights", [])
            ]

            return insights

        except httpx.HTTPStatusError as e:
            logger.error(
                f"[AgentMemory] RAG service error getting history: {e.response.status_code}"
            )
            return []
        except httpx.RequestError as e:
            logger.error(f"[AgentMemory] Failed to connect to RAG service: {e}")
            return []

    @traceable(name="memory_get_stats", tags=["memory", "rag"])
    async def get_stats(self) -> Dict[str, Any]:
        """Get memory collection statistics from RAG service."""
        client = await self._get_client()

        try:
            response = await client.get(f"{self.rag_url}/memory/stats")
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(
                f"[AgentMemory] RAG service error getting stats: {e.response.status_code}"
            )
            return {"error": str(e)}
        except httpx.RequestError as e:
            logger.error(f"[AgentMemory] Failed to connect to RAG service: {e}")
            return {"error": str(e)}

    @traceable(name="memory_prune_old", tags=["memory", "rag"])
    async def prune_old_insights(self, ttl_days: int = 30) -> int:
        """
        Prune insights that haven't been used within TTL period.

        Args:
            ttl_days: Days before unused insights are pruned

        Returns:
            Number of insights pruned
        """
        client = await self._get_client()

        try:
            response = await client.delete(
                f"{self.rag_url}/memory/prune",
                params={"ttl_days": ttl_days, "agent_id": self.agent_id},
            )
            response.raise_for_status()
            result = response.json()

            pruned_count = result.get("pruned_count", 0)
            logger.info(
                f"[AgentMemory] Pruned {pruned_count} insights (TTL: {ttl_days} days)"
            )

            return pruned_count

        except httpx.HTTPStatusError as e:
            logger.error(
                f"[AgentMemory] RAG service error pruning: {e.response.status_code}"
            )
            return 0
        except httpx.RequestError as e:
            logger.error(f"[AgentMemory] Failed to connect to RAG service: {e}")
            return 0

    def clear_last_insights(self) -> None:
        """Clear the last extracted insights list (called by graph.py after collection)."""
        self.last_extracted_insights = []


# Singleton instances per agent
_memory_managers: Dict[str, AgentMemoryManager] = {}


def get_agent_memory_manager(agent_id: str) -> AgentMemoryManager:
    """
    Get or create AgentMemoryManager for a specific agent.

    Args:
        agent_id: ID of the agent

    Returns:
        AgentMemoryManager instance for the agent
    """
    if agent_id not in _memory_managers:
        _memory_managers[agent_id] = AgentMemoryManager(agent_id=agent_id)
        logger.info(f"[AgentMemory] Created memory manager for agent: {agent_id}")
    return _memory_managers[agent_id]


def init_agent_memory_manager(
    agent_id: str,
    rag_service_url: Optional[str] = None,
    timeout: float = 30.0,
) -> AgentMemoryManager:
    """
    Initialize AgentMemoryManager for a specific agent.

    Args:
        agent_id: ID of the agent
        rag_service_url: Optional override for RAG service URL
        timeout: HTTP timeout in seconds

    Returns:
        Initialized AgentMemoryManager
    """
    manager = AgentMemoryManager(
        agent_id=agent_id,
        rag_service_url=rag_service_url,
        timeout=timeout,
    )
    _memory_managers[agent_id] = manager
    logger.info(f"[AgentMemory] Initialized memory manager for agent: {agent_id}")
    return manager


# Re-export for backward compatibility
__all__ = [
    "AgentMemoryManager",
    "Insight",
    "InsightType",
    "get_agent_memory_manager",
    "init_agent_memory_manager",
]
