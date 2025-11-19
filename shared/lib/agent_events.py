"""
Agent-to-agent event protocol schemas.

This module defines the event types used for inter-agent communication:
- AgentRequestEvent: Request from one agent to another
- AgentResponseEvent: Response to an agent request
- AgentBroadcastEvent: Broadcast message to multiple agents

Usage:
    from shared.lib.agent_events import AgentRequestEvent, AgentResponseEvent
    from shared.lib.event_bus import EventBus
    
    # Request help from another agent
    request = AgentRequestEvent(
        source_agent="orchestrator",
        target_agent="code-review",
        request_type="review_code",
        payload={"file_path": "main.py", "changes": "..."}
    )
    response = await event_bus.request_agent(request, timeout=30.0)
"""

from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class AgentRequestType(str, Enum):
    """Standard request types for inter-agent communication."""
    
    # Code-related requests
    REVIEW_CODE = "review_code"
    GENERATE_CODE = "generate_code"
    REFACTOR_CODE = "refactor_code"
    
    # Infrastructure requests
    DEPLOY_SERVICE = "deploy_service"
    UPDATE_CONFIG = "update_config"
    HEALTH_CHECK = "health_check"
    
    # CI/CD requests
    RUN_PIPELINE = "run_pipeline"
    VALIDATE_BUILD = "validate_build"
    DEPLOY_ARTIFACT = "deploy_artifact"
    
    # Documentation requests
    GENERATE_DOCS = "generate_docs"
    UPDATE_README = "update_readme"
    EXPLAIN_CODE = "explain_code"
    
    # Orchestration requests
    DECOMPOSE_TASK = "decompose_task"
    ROUTE_REQUEST = "route_request"
    AGGREGATE_RESULTS = "aggregate_results"
    
    # General requests
    QUERY_CAPABILITY = "query_capability"
    GET_STATUS = "get_status"
    EXECUTE_TASK = "execute_task"


class AgentRequestPriority(str, Enum):
    """Priority levels for agent requests."""
    
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class AgentRequestEvent(BaseModel):
    """
    Event schema for requests between agents.
    
    Attributes:
        request_id: Unique identifier for correlation
        source_agent: Name of requesting agent
        target_agent: Name of target agent (or "any" for capability-based routing)
        request_type: Type of request (from AgentRequestType enum)
        payload: Request-specific data
        priority: Request priority level
        timeout_seconds: Maximum time to wait for response
        correlation_id: Optional ID for grouping related requests
        metadata: Additional context (user_id, task_id, etc.)
        created_at: Timestamp of request creation
    """
    
    request_id: str = Field(default_factory=lambda: str(uuid4()))
    source_agent: str
    target_agent: str  # "any" for capability-based routing
    request_type: AgentRequestType
    payload: Dict[str, Any] = Field(default_factory=dict)
    priority: AgentRequestPriority = AgentRequestPriority.NORMAL
    timeout_seconds: float = 30.0
    correlation_id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    @property
    def expires_at(self) -> datetime:
        """Calculate expiration timestamp based on timeout."""
        return self.created_at + timedelta(seconds=self.timeout_seconds)
    
    @property
    def is_expired(self) -> bool:
        """Check if request has timed out."""
        return datetime.now(timezone.utc) > self.expires_at
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        data = self.model_dump()
        data["created_at"] = self.created_at.isoformat()
        return data


class AgentResponseStatus(str, Enum):
    """Response status codes."""
    
    SUCCESS = "success"
    ERROR = "error"
    TIMEOUT = "timeout"
    REJECTED = "rejected"
    PARTIAL = "partial"


class AgentResponseEvent(BaseModel):
    """
    Event schema for responses to agent requests.
    
    Attributes:
        response_id: Unique response identifier
        request_id: ID of the request being responded to
        source_agent: Name of responding agent
        target_agent: Name of original requesting agent
        status: Response status (success, error, etc.)
        result: Response data
        error: Error details if status is ERROR
        metadata: Additional context
        created_at: Timestamp of response creation
        processing_time_ms: Time taken to process request
    """
    
    response_id: str = Field(default_factory=lambda: str(uuid4()))
    request_id: str  # Correlation to original request
    source_agent: str
    target_agent: str
    status: AgentResponseStatus
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    processing_time_ms: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        data = self.model_dump()
        data["created_at"] = self.created_at.isoformat()
        return data


class AgentBroadcastEvent(BaseModel):
    """
    Event schema for broadcast messages to multiple agents.
    
    Use this for notifications, state changes, or announcements
    that multiple agents should be aware of.
    
    Attributes:
        broadcast_id: Unique identifier
        source_agent: Name of broadcasting agent
        target_agents: List of target agents ("all" for everyone)
        event_type: Type of broadcast event
        payload: Event data
        priority: Broadcast priority
        metadata: Additional context
        created_at: Timestamp of broadcast
    """
    
    broadcast_id: str = Field(default_factory=lambda: str(uuid4()))
    source_agent: str
    target_agents: List[str] = Field(default_factory=lambda: ["all"])
    event_type: str  # e.g., "task_completed", "config_updated", "alert"
    payload: Dict[str, Any] = Field(default_factory=dict)
    priority: AgentRequestPriority = AgentRequestPriority.NORMAL
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        data = self.model_dump()
        data["created_at"] = self.created_at.isoformat()
        return data


class AgentCapabilityQuery(BaseModel):
    """
    Query schema for finding agents by capability.
    
    Used by orchestrator to route requests to appropriate agents.
    """
    
    capability_keywords: List[str]
    required_all: bool = False  # True = AND, False = OR
    exclude_agents: List[str] = Field(default_factory=list)
    min_confidence: float = 0.0


class AgentRoutingResult(BaseModel):
    """
    Result of capability-based agent routing.
    
    Attributes:
        matched_agents: List of agents matching the capability query
        confidence_scores: Confidence score for each match (0.0-1.0)
        selected_agent: Agent selected for routing (highest confidence)
    """
    
    matched_agents: List[str]
    confidence_scores: Dict[str, float] = Field(default_factory=dict)
    selected_agent: Optional[str] = None
    
    def select_best(self) -> Optional[str]:
        """Select agent with highest confidence score."""
        if not self.confidence_scores:
            return self.matched_agents[0] if self.matched_agents else None
        
        best_agent = max(self.confidence_scores.items(), key=lambda x: x[1])
        self.selected_agent = best_agent[0]
        return self.selected_agent
