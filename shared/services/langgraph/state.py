"""Shared LangGraph state and validation utilities for Dev-Tools agents."""

from __future__ import annotations

import operator
from datetime import datetime
from typing import Annotated, Any, Dict, Iterable, List, Mapping, Optional, Sequence, TypedDict, cast

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from pydantic import BaseModel, ConfigDict, Field, model_validator


def _append_list(existing: Optional[List[str]], updates: Optional[Iterable[str]]) -> List[str]:
    """Append updates to an existing list while preserving order."""

    base = list(existing or [])
    if not updates:
        return base

    base.extend(str(item) for item in updates if item is not None)
    return base


def _append_unique(existing: Optional[List[str]], updates: Optional[Iterable[str]]) -> List[str]:
    """Append only new values while keeping original order."""

    base = list(existing or [])
    if not updates:
        return base

    for item in updates:
        if item is None:
            continue
        value = str(item)
        if value not in base:
            base.append(value)
    return base


class MultiAgentState(TypedDict):
    """
    Shared state for multi-agent workflows (Phase 6).
    Supports task decomposition, parallel execution, and resource locking.
    """
    task_id: str
    workflow_type: str  # "sequential", "parallel", "map-reduce"

    # Task decomposition
    subtasks: Annotated[Sequence[dict], operator.add]
    subtask_status: dict  # {subtask_id: "pending"|"in_progress"|"completed"|"failed"}

    # Agent assignments
    agent_assignments: dict  # {subtask_id: agent_id}
    agent_status: dict  # {agent_id: "idle"|"busy"}

    # Coordination
    locks: dict  # {resource_id: agent_id}
    checkpoints: Annotated[Sequence[dict], operator.add]

    # Results aggregation
    partial_results: dict  # {subtask_id: result}
    final_result: Optional[dict]

    # Metadata
    started_at: datetime
    updated_at: datetime
    error_log: Annotated[Sequence[str], operator.add]
    _version: int  # Optimistic locking version


class AgentState(TypedDict, total=False):
    """Canonical shared state exchanged between LangGraph nodes."""

    messages: Annotated[List[BaseMessage], add_messages]
    task_description: str
    current_agent: str
    rag_context: Annotated[List[str], _append_list]
    mcp_tools_used: Annotated[List[str], _append_unique]
    linear_issue_id: Optional[str]
    feature_request: Mapping[str, object]
    feature_response: Mapping[str, object]
    code_review_request: Mapping[str, object]
    code_review_response: Mapping[str, object]
    infrastructure_request: Mapping[str, object]
    infrastructure_response: Mapping[str, object]
    cicd_request: Mapping[str, object]
    cicd_response: Mapping[str, object]
    documentation_request: Mapping[str, object]
    documentation_response: Mapping[str, object]
    guardrail_report: Mapping[str, object]
    error: Optional[str]


class AgentStateModel(BaseModel):
    """Pydantic model used to validate and normalize AgentState payloads."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    messages: List[BaseMessage] = Field(default_factory=list, description="Conversation transcript shared across nodes")
    task_description: str = Field(..., min_length=1, description="High-level task request being executed")
    current_agent: str = Field(default="orchestrator", description="Most recent agent/node that handled the task")
    rag_context: List[str] = Field(default_factory=list, description="Retrieved knowledge snippets available to the graph")
    mcp_tools_used: List[str] = Field(default_factory=list, description="Identifiers for MCP tools invoked in this run")
    linear_issue_id: Optional[str] = Field(default=None, description="Optional Linear issue id associated with the task")
    feature_request: Optional[Dict[str, Any]] = Field(default=None, description="Cached feature implementation request payload")
    feature_response: Optional[Dict[str, Any]] = Field(default=None, description="Latest feature implementation response payload")
    code_review_request: Optional[Dict[str, Any]] = Field(default=None, description="Cached code review request payload")
    code_review_response: Optional[Dict[str, Any]] = Field(default=None, description="Latest code review response payload")
    infrastructure_request: Optional[Dict[str, Any]] = Field(default=None, description="Cached infrastructure generation request payload")
    infrastructure_response: Optional[Dict[str, Any]] = Field(default=None, description="Latest infrastructure generation response payload")
    cicd_request: Optional[Dict[str, Any]] = Field(default=None, description="Cached CI/CD generation request payload")
    cicd_response: Optional[Dict[str, Any]] = Field(default=None, description="Latest CI/CD generation response payload")
    documentation_request: Optional[Dict[str, Any]] = Field(default=None, description="Cached documentation generation request payload")
    documentation_response: Optional[Dict[str, Any]] = Field(default=None, description="Latest documentation generation response payload")
    guardrail_report: Optional[Dict[str, Any]] = Field(default=None, description="Most recent guardrail execution report")
    error: Optional[str] = Field(default=None, description="Latest error message, if any")

    @model_validator(mode="after")
    def _normalize_fields(self) -> "AgentStateModel":
        self.task_description = self.task_description.strip()
        if not self.task_description:
            raise ValueError("task_description must be a non-empty string")

        self.current_agent = self.current_agent.strip() or "orchestrator"
        self.rag_context = _append_list([], [item.strip() for item in self.rag_context if item])
        self.mcp_tools_used = _append_unique([], [item.strip() for item in self.mcp_tools_used if item])
        if self.linear_issue_id:
            self.linear_issue_id = self.linear_issue_id.strip() or None
        if self.error:
            self.error = self.error.strip() or None
        return self


def ensure_agent_state(payload: Mapping[str, object]) -> AgentState:
    """Validate arbitrary payloads and coerce them into an AgentState dict."""

    model = AgentStateModel(**payload)
    state: Dict[str, Any] = {
        "messages": list(model.messages),
        "task_description": model.task_description,
        "current_agent": model.current_agent,
        "rag_context": list(model.rag_context),
        "mcp_tools_used": list(model.mcp_tools_used),
        "linear_issue_id": model.linear_issue_id,
    }

    optional_fields = (
        "feature_request",
        "feature_response",
        "code_review_request",
        "code_review_response",
        "infrastructure_request",
        "infrastructure_response",
        "cicd_request",
        "cicd_response",
        "documentation_request",
        "documentation_response",
        "guardrail_report",
        "error",
    )

    for field_name in optional_fields:
        value = getattr(model, field_name)
        if value is not None:
            state[field_name] = dict(value) if isinstance(value, dict) else value

    return cast(AgentState, state)


def empty_agent_state(task_description: str, *, current_agent: str = "orchestrator") -> AgentState:
    """Convenience helper for creating a minimal AgentState record."""

    return ensure_agent_state({
        "messages": [],
        "task_description": task_description,
        "current_agent": current_agent,
        "rag_context": [],
        "mcp_tools_used": [],
        "linear_issue_id": None,
    })
