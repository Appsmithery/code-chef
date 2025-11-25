"""LangGraph multi-agent workflow for orchestrator.

This module defines the stateful workflow graph that coordinates multiple
specialized agents (supervisor, feature-dev, code-review, infrastructure, cicd, documentation).

Architecture:
- Supervisor agent routes tasks to specialized agents
- Conditional edges based on LLM routing decisions
- HITL approval nodes for high-risk operations
- PostgreSQL checkpointing for workflow resume
"""

import sys
import uuid
import logging
from datetime import datetime
from pathlib import Path
from typing import TypedDict, List, Literal, Annotated
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.postgres import PostgresSaver
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage, AIMessage

logger = logging.getLogger(__name__)

# Add shared modules to path
sys.path.insert(0, str(Path(__file__).parent.parent / "shared"))

# Note: Agent implementations are in shared/services/langgraph/nodes/
# These are workflow nodes, not separate agent services
# Importing node functions directly would create circular dependencies,
# so we'll use dynamic imports or stub implementations


# Define workflow state
class WorkflowState(TypedDict):
    """State passed between agents in the workflow.
    
    Fields:
        messages: Conversation history (including task description)
        current_agent: Name of agent currently processing task
        next_agent: Name of next agent to route to (decided by supervisor)
        task_result: Result from current agent's execution
        approvals: List of approval IDs for HITL operations
        requires_approval: Whether current operation requires HITL approval
    """
    messages: Annotated[List[BaseMessage], "append"]  # Append-only message history
    current_agent: str
    next_agent: str
    task_result: dict
    approvals: List[str]
    requires_approval: bool


# Initialize all agents (lazy loaded on first use)
_agents = {}

def get_agent(agent_name: str):
    """Get or create agent instance.
    
    Note: This is a stub implementation. Actual agent logic should be
    implemented in shared/services/langgraph/nodes/{agent_name}.py
    
    Args:
        agent_name: Name of agent (supervisor, feature-dev, code-review, etc.)
    
    Returns:
        Stub agent dict with invoke method
    """
    if agent_name not in _agents:
        # Create stub agent with minimal invoke method
        class StubAgent:
            def __init__(self, name):
                self.name = name
            
            async def invoke(self, messages):
                # Return stub response
                from langchain_core.messages import AIMessage
                return AIMessage(content=f"Stub response from {self.name} agent. Implement actual logic in shared/services/langgraph/nodes/{self.name.replace('-', '_')}.py")
        
        _agents[agent_name] = StubAgent(agent_name)
    
    return _agents[agent_name]


# Define agent nodes
async def supervisor_node(state: WorkflowState) -> WorkflowState:
    """Supervisor agent node - routes tasks to specialized agents.
    
    Analyzes the task and decides which agent should handle it next.
    Also determines if HITL approval is required.
    """
    supervisor = get_agent("supervisor")
    
    # Add routing instruction to messages
    routing_prompt = """Analyze this task and determine:
1. Which specialized agent should handle it (feature-dev, code-review, infrastructure, cicd, documentation)
2. Whether it requires HITL approval (high-risk operations like production deployments, infrastructure changes)

Respond in this format:
NEXT_AGENT: <agent-name>
REQUIRES_APPROVAL: <true|false>
REASONING: <your analysis>
"""
    
    messages = state["messages"] + [HumanMessage(content=routing_prompt)]
    response = await supervisor.invoke(messages)
    
    # Parse supervisor's routing decision
    response_text = response.content if hasattr(response, "content") else str(response)
    
    # Extract next agent
    next_agent = "end"  # Default to end
    requires_approval = False
    
    for line in response_text.split("\n"):
        if line.startswith("NEXT_AGENT:"):
            next_agent = line.split(":", 1)[1].strip().lower()
        elif line.startswith("REQUIRES_APPROVAL:"):
            requires_approval = "true" in line.lower()
    
    return {
        "messages": [response],
        "current_agent": "supervisor",
        "next_agent": next_agent,
        "requires_approval": requires_approval,
    }


async def feature_dev_node(state: WorkflowState) -> WorkflowState:
    """Feature development agent node - implements code."""
    agent = get_agent("feature-dev")
    response = await agent.invoke(state["messages"])
    
    return {
        "messages": [response],
        "current_agent": "feature-dev",
        "next_agent": "supervisor",  # Always return to supervisor
        "task_result": {"agent": "feature-dev", "completed": True},
    }


async def code_review_node(state: WorkflowState) -> WorkflowState:
    """Code review agent node - analyzes code quality."""
    agent = get_agent("code-review")
    response = await agent.invoke(state["messages"])
    
    return {
        "messages": [response],
        "current_agent": "code-review",
        "next_agent": "supervisor",
        "task_result": {"agent": "code-review", "completed": True},
    }


async def infrastructure_node(state: WorkflowState) -> WorkflowState:
    """Infrastructure agent node - manages cloud resources."""
    agent = get_agent("infrastructure")
    response = await agent.invoke(state["messages"])
    
    return {
        "messages": [response],
        "current_agent": "infrastructure",
        "next_agent": "supervisor",
        "task_result": {"agent": "infrastructure", "completed": True},
    }


async def cicd_node(state: WorkflowState) -> WorkflowState:
    """CI/CD agent node - handles deployments."""
    agent = get_agent("cicd")
    response = await agent.invoke(state["messages"])
    
    return {
        "messages": [response],
        "current_agent": "cicd",
        "next_agent": "supervisor",
        "task_result": {"agent": "cicd", "completed": True},
    }


async def documentation_node(state: WorkflowState) -> WorkflowState:
    """Documentation agent node - writes technical docs."""
    agent = get_agent("documentation")
    response = await agent.invoke(state["messages"])
    
    return {
        "messages": [response],
        "current_agent": "documentation",
        "next_agent": "supervisor",
        "task_result": {"agent": "documentation", "completed": True},
    }


async def approval_node(state: WorkflowState) -> WorkflowState:
    """HITL approval node - creates Linear issue and waits for approval.
    
    This node interrupts the graph execution and requires external approval
    before the workflow can continue.
    """
    # Import LinearWorkspaceClient only when needed (avoid import-time dependencies)
    try:
        from lib.linear_workspace_client import LinearWorkspaceClient
        linear_client = LinearWorkspaceClient()
    except ImportError:
        # Fallback if Linear client unavailable
        linear_client = None
    
    # Extract task description from messages
    task_description = "Unknown task"
    for msg in reversed(state["messages"]):
        if isinstance(msg, HumanMessage):
            task_description = msg.content[:500]  # First 500 chars
            break
    
    # Create approval sub-issue in Linear
    approval_id = f"approval-{uuid.uuid4()}"
    if linear_client:
        try:
            approval_issue = await linear_client.create_approval_subissue(
                approval_id=approval_id,
                task_description=task_description,
                risk_level="high",  # Determined by supervisor
                project_name="Dev-Tools",
                agent_name="orchestrator",
                metadata={
                    "timestamp": datetime.now().isoformat(),
                    "workflow_id": state.get("workflow_id", "unknown")
                }
            )
            # Use Linear issue identifier for tracking
            approval_id = approval_issue.get("identifier") if approval_issue else approval_id
            logger.info(f"Created HITL approval sub-issue: {approval_id}")
        except Exception as e:
            logger.error(f"Failed to create approval sub-issue: {e}")
            # Keep the UUID approval_id as fallback
    
    return {
        "messages": [AIMessage(content=f"Approval requested: {approval_id}")],
        "approvals": [approval_id] if approval_id else [],
        "requires_approval": False,  # Approval created, can proceed
    }


# Define routing logic
def route_from_supervisor(state: WorkflowState) -> str:
    """Conditional edge from supervisor to next agent.
    
    Routes based on supervisor's decision in state["next_agent"].
    """
    next_agent = state.get("next_agent", "end")
    
    # Check if approval required first
    if state.get("requires_approval", False):
        return "approval"
    
    # Route to next agent or end
    if next_agent in ["feature-dev", "code-review", "infrastructure", "cicd", "documentation"]:
        return next_agent
    
    return "end"


def should_continue(state: WorkflowState) -> str:
    """Decide if workflow should continue or end.
    
    Checks if there are more agents to route to.
    """
    next_agent = state.get("next_agent", "end")
    return "supervisor" if next_agent != "end" else "end"


# Build the workflow graph
def create_workflow(checkpoint_conn_string: str = None) -> StateGraph:
    """Create the LangGraph workflow with all agent nodes.
    
    Args:
        checkpoint_conn_string: PostgreSQL connection string for checkpointing
            Format: postgresql://user:pass@host:port/db
    
    Returns:
        Compiled StateGraph workflow
    """
    # Create graph
    workflow = StateGraph(WorkflowState)
    
    # Add all agent nodes
    workflow.add_node("supervisor", supervisor_node)
    workflow.add_node("feature-dev", feature_dev_node)
    workflow.add_node("code-review", code_review_node)
    workflow.add_node("infrastructure", infrastructure_node)
    workflow.add_node("cicd", cicd_node)
    workflow.add_node("documentation", documentation_node)
    workflow.add_node("approval", approval_node)
    
    # Set entry point
    workflow.set_entry_point("supervisor")
    
    # Add conditional edges from supervisor to agents
    workflow.add_conditional_edges(
        "supervisor",
        route_from_supervisor,
        {
            "feature-dev": "feature-dev",
            "code-review": "code-review",
            "infrastructure": "infrastructure",
            "cicd": "cicd",
            "documentation": "documentation",
            "approval": "approval",
            "end": END,
        }
    )
    
    # All agents route back to supervisor
    workflow.add_edge("feature-dev", "supervisor")
    workflow.add_edge("code-review", "supervisor")
    workflow.add_edge("infrastructure", "supervisor")
    workflow.add_edge("cicd", "supervisor")
    workflow.add_edge("documentation", "supervisor")
    workflow.add_edge("approval", "supervisor")
    
    # Compile workflow with checkpointing
    if checkpoint_conn_string:
        checkpointer = PostgresSaver(checkpoint_conn_string)
        return workflow.compile(checkpointer=checkpointer)
    else:
        return workflow.compile()


# Export compiled workflow
app = create_workflow()
