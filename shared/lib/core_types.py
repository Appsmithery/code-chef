"""
Canonical shared types for code-chef multi-agent platform.

Single source of truth for types used across:
- Agent memory (agent_memory.py)
- RAG service (services/rag/main.py)
- Workflow engine (workflow_engine.py)
- Agent nodes (graph.py)

Issue: CHEF-198
"""

from enum import Enum
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime


class InsightType(str, Enum):
    """Types of insights that agents can capture and share.

    Used for cross-agent knowledge sharing via AgentMemoryManager.
    """

    ARCHITECTURAL_DECISION = "architectural_decision"
    ERROR_PATTERN = "error_pattern"
    CODE_PATTERN = "code_pattern"
    TASK_RESOLUTION = "task_resolution"
    SECURITY_FINDING = "security_finding"


class WorkflowAction(str, Enum):
    """Actions that can occur during workflow execution.

    Used for event sourcing in workflow_engine.py.
    """

    START = "start"
    STEP_START = "step_start"
    STEP_COMPLETE = "step_complete"
    STEP_FAIL = "step_fail"
    AGENT_CALL = "agent_call"
    AGENT_RESPONSE = "agent_response"
    HITL_REQUEST = "hitl_request"
    HITL_APPROVED = "hitl_approved"
    HITL_REJECTED = "hitl_rejected"
    DECISION = "decision"
    CAPTURE_INSIGHT = "capture_insight"  # New: for insight persistence
    COMPLETE = "complete"
    FAIL = "fail"
    RESUME = "resume"


class RiskLevel(str, Enum):
    """Risk levels for HITL approval decisions."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class CapturedInsight:
    """Represents an insight captured during workflow execution.

    Stored in WorkflowState.captured_insights for checkpoint persistence.
    """

    agent_id: str
    insight_type: InsightType
    content: str
    confidence: float = 0.8
    timestamp: datetime = field(default_factory=datetime.utcnow)
    workflow_id: Optional[str] = None
    source_task: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dict for checkpoint persistence."""
        return {
            "agent_id": self.agent_id,
            "insight_type": (
                self.insight_type.value
                if isinstance(self.insight_type, InsightType)
                else self.insight_type
            ),
            "content": self.content,
            "confidence": self.confidence,
            "timestamp": (
                self.timestamp.isoformat()
                if isinstance(self.timestamp, datetime)
                else self.timestamp
            ),
            "workflow_id": self.workflow_id,
            "source_task": self.source_task,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CapturedInsight":
        """Create from dict (for checkpoint restoration)."""
        timestamp = data.get("timestamp")
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp)
        elif timestamp is None:
            timestamp = datetime.utcnow()

        insight_type = data.get("insight_type")
        if isinstance(insight_type, str):
            try:
                insight_type = InsightType(insight_type)
            except ValueError:
                insight_type = InsightType.TASK_RESOLUTION  # Default fallback

        return cls(
            agent_id=data.get("agent_id", "unknown"),
            insight_type=insight_type,
            content=data.get("content", ""),
            confidence=data.get("confidence", 0.8),
            timestamp=timestamp,
            workflow_id=data.get("workflow_id"),
            source_task=data.get("source_task"),
            metadata=data.get("metadata", {}),
        )
