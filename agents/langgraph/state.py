"""Shared LangGraph state and validation utilities for Dev-Tools agents."""

from __future__ import annotations

from typing import Annotated, Iterable, List, Mapping, Optional, TypedDict, cast

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


class AgentState(TypedDict, total=False):
    """Canonical shared state exchanged between LangGraph nodes."""

    messages: Annotated[List[BaseMessage], add_messages]
    task_description: str
    current_agent: str
    rag_context: Annotated[List[str], _append_list]
    mcp_tools_used: Annotated[List[str], _append_unique]
    linear_issue_id: Optional[str]


class AgentStateModel(BaseModel):
    """Pydantic model used to validate and normalize AgentState payloads."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    messages: List[BaseMessage] = Field(default_factory=list, description="Conversation transcript shared across nodes")
    task_description: str = Field(..., min_length=1, description="High-level task request being executed")
    current_agent: str = Field(default="orchestrator", description="Most recent agent/node that handled the task")
    rag_context: List[str] = Field(default_factory=list, description="Retrieved knowledge snippets available to the graph")
    mcp_tools_used: List[str] = Field(default_factory=list, description="Identifiers for MCP tools invoked in this run")
    linear_issue_id: Optional[str] = Field(default=None, description="Optional Linear issue id associated with the task")

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
        return self


def ensure_agent_state(payload: Mapping[str, object]) -> AgentState:
    """Validate arbitrary payloads and coerce them into an AgentState dict."""

    model = AgentStateModel(**payload)
    return cast(
        AgentState,
        {
            "messages": list(model.messages),
            "task_description": model.task_description,
            "current_agent": model.current_agent,
            "rag_context": list(model.rag_context),
            "mcp_tools_used": list(model.mcp_tools_used),
            "linear_issue_id": model.linear_issue_id,
        },
    )


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
