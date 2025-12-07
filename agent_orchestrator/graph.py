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
import hashlib
import logging
from datetime import datetime
from pathlib import Path
from typing import TypedDict, List, Literal, Annotated, Dict, Any, Optional
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.types import interrupt
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage, AIMessage
from langsmith import traceable

logger = logging.getLogger(__name__)

# Add shared modules to path
sys.path.insert(0, str(Path(__file__).parent.parent / "shared"))

# Import real agent classes from agents module
from agents import get_agent as get_real_agent


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
        workflow_id: Unique workflow identifier for checkpointing
        thread_id: LangGraph thread ID for state persistence
        pending_operation: Description of operation requiring approval

    Cross-Agent Memory Fields (CHEF-206):
        captured_insights: Insights extracted during workflow, persisted in checkpoint
        memory_context: Retrieved context at checkpoint time for injection on resume
    """

    messages: Annotated[List[BaseMessage], "append"]  # Append-only message history
    current_agent: str
    next_agent: str
    task_result: dict
    approvals: List[str]
    requires_approval: bool
    workflow_id: str
    thread_id: str
    pending_operation: str
    # Cross-agent memory fields (JSON-serializable for PostgresSaver)
    captured_insights: List[Dict[str, Any]]  # Insights from agents during workflow
    memory_context: Optional[str]  # Retrieved context on resume


# Agent cache with bound LLM instances
_agent_cache: Dict[str, Any] = {}


def get_agent(agent_name: str):
    """Get or create agent instance using real BaseAgent implementations.

    Uses the agent registry from agents/__init__.py which provides:
    - SupervisorAgent, FeatureDevAgent, CodeReviewAgent, etc.
    - Each agent has LLM, MCP tools, and system prompts configured

    Args:
        agent_name: Name of agent (supervisor, feature-dev, code-review, etc.)

    Returns:
        BaseAgent instance with invoke() method
    """
    if agent_name not in _agent_cache:
        try:
            _agent_cache[agent_name] = get_real_agent(agent_name)
            logger.info(f"[LangGraph] Initialized agent: {agent_name}")
        except Exception as e:
            logger.error(f"[LangGraph] Failed to initialize agent {agent_name}: {e}")
            raise

    return _agent_cache[agent_name]


def _collect_agent_insights(
    agent, state: WorkflowState, agent_name: str
) -> List[Dict[str, Any]]:
    """Collect insights from agent's last execution and add to workflow state.

    CHEF-208: Implements insight persistence to checkpoint state.

    Args:
        agent: BaseAgent instance with potential last_extracted_insights
        state: Current workflow state
        agent_name: Name of the agent for labeling

    Returns:
        Updated captured_insights list
    """
    new_insights = list(state.get("captured_insights") or [])

    # Check if agent has memory manager with insights
    if hasattr(agent, "memory_manager") and agent.memory_manager:
        memory_mgr = agent.memory_manager
        if (
            hasattr(memory_mgr, "last_extracted_insights")
            and memory_mgr.last_extracted_insights
        ):
            for insight in memory_mgr.last_extracted_insights:
                new_insights.append(
                    {
                        "agent_id": agent_name,
                        "insight_type": insight.get("type"),
                        "content": insight.get("content", "")[:500],
                        "confidence": insight.get("confidence", 0.8),
                        "timestamp": datetime.utcnow().isoformat(),
                        "workflow_id": state.get("workflow_id"),
                    }
                )
            # Clear after collection
            memory_mgr.clear_last_insights()
            logger.debug(
                f"[LangGraph] Collected {len(memory_mgr.last_extracted_insights)} insights from {agent_name}"
            )

    return new_insights


# Define agent nodes
@traceable(name="supervisor_node", tags=["langgraph", "node", "supervisor"])
async def supervisor_node(state: WorkflowState) -> WorkflowState:
    """Supervisor agent node - routes tasks to specialized agents.

    Uses the real SupervisorAgent with LLM to analyze the task and decide:
    1. Which specialized agent should handle it
    2. Whether it requires HITL approval (high-risk operations)
    """
    supervisor = get_agent("supervisor")

    # Add routing instruction to messages
    routing_prompt = """Analyze this task and determine:
1. Which specialized agent should handle it (feature-dev, code-review, infrastructure, cicd, documentation)
2. Whether it requires HITL approval (high-risk operations like production deployments, infrastructure changes, database migrations)

Respond in this format:
NEXT_AGENT: <agent-name>
REQUIRES_APPROVAL: <true|false>
REASONING: <your analysis>

If the task is complete or no further action is needed, respond with:
NEXT_AGENT: end
REQUIRES_APPROVAL: false
REASONING: Task completed
"""

    messages = state["messages"] + [HumanMessage(content=routing_prompt)]

    try:
        response = await supervisor.invoke(messages)
        response_text = (
            response.content if hasattr(response, "content") else str(response)
        )
    except Exception as e:
        logger.error(f"[LangGraph] Supervisor invoke failed: {e}")
        # Fallback to end state on error
        return {
            "messages": [AIMessage(content=f"Supervisor error: {e}")],
            "current_agent": "supervisor",
            "next_agent": "end",
            "requires_approval": False,
            "task_result": {"error": str(e)},
        }

    # Parse supervisor's routing decision
    next_agent = "end"  # Default to end
    requires_approval = False
    pending_operation = ""

    for line in response_text.split("\n"):
        if line.startswith("NEXT_AGENT:"):
            next_agent = line.split(":", 1)[1].strip().lower()
        elif line.startswith("REQUIRES_APPROVAL:"):
            requires_approval = "true" in line.lower()
        elif line.startswith("REASONING:"):
            pending_operation = line.split(":", 1)[1].strip()

    logger.info(
        f"[LangGraph] Supervisor routed to: {next_agent}, approval_required: {requires_approval}"
    )

    return {
        "messages": [response],
        "current_agent": "supervisor",
        "next_agent": next_agent,
        "requires_approval": requires_approval,
        "pending_operation": pending_operation,
    }


@traceable(name="feature_dev_node", tags=["langgraph", "node", "feature-dev"])
async def feature_dev_node(state: WorkflowState) -> WorkflowState:
    """Feature development agent node - implements code.

    Uses FeatureDevAgent with codellama model for:
    - Code implementation
    - Refactoring
    - Bug fixes

    CHEF-208: Captures insights to state for checkpoint persistence.
    """
    agent = get_agent("feature-dev")

    try:
        response = await agent.invoke(state["messages"])
        result_content = (
            response.content if hasattr(response, "content") else str(response)
        )
        logger.info(
            f"[LangGraph] feature-dev completed. Response length: {len(result_content)}"
        )

        # Collect insights for checkpoint persistence (CHEF-208)
        captured_insights = _collect_agent_insights(agent, state, "feature-dev")

        return {
            "messages": [response],
            "current_agent": "feature-dev",
            "next_agent": "supervisor",  # Always return to supervisor
            "task_result": {
                "agent": "feature-dev",
                "completed": True,
                "output_length": len(result_content),
            },
            "captured_insights": captured_insights,
        }
    except Exception as e:
        logger.error(f"[LangGraph] feature-dev failed: {e}")
        return {
            "messages": [AIMessage(content=f"Feature development error: {e}")],
            "current_agent": "feature-dev",
            "next_agent": "supervisor",
            "task_result": {
                "agent": "feature-dev",
                "completed": False,
                "error": str(e),
            },
        }


@traceable(name="code_review_node", tags=["langgraph", "node", "code-review"])
async def code_review_node(state: WorkflowState) -> WorkflowState:
    """Code review agent node - analyzes code quality.

    Uses CodeReviewAgent with llama3.3-70b model for:
    - OWASP Top 10 security analysis
    - Code quality checks
    - Best practices validation

    CHEF-208: Captures insights to state for checkpoint persistence.
    """
    agent = get_agent("code-review")

    try:
        response = await agent.invoke(state["messages"])
        result_content = (
            response.content if hasattr(response, "content") else str(response)
        )
        logger.info(
            f"[LangGraph] code-review completed. Response length: {len(result_content)}"
        )

        # Collect insights for checkpoint persistence (CHEF-208)
        captured_insights = _collect_agent_insights(agent, state, "code-review")

        return {
            "messages": [response],
            "current_agent": "code-review",
            "next_agent": "supervisor",
            "task_result": {
                "agent": "code-review",
                "completed": True,
                "output_length": len(result_content),
            },
            "captured_insights": captured_insights,
        }
    except Exception as e:
        logger.error(f"[LangGraph] code-review failed: {e}")
        return {
            "messages": [AIMessage(content=f"Code review error: {e}")],
            "current_agent": "code-review",
            "next_agent": "supervisor",
            "task_result": {
                "agent": "code-review",
                "completed": False,
                "error": str(e),
            },
        }


@traceable(name="infrastructure_node", tags=["langgraph", "node", "infrastructure"])
async def infrastructure_node(state: WorkflowState) -> WorkflowState:
    """Infrastructure agent node - manages cloud resources.

    Uses InfrastructureAgent with llama3-8b model for:
    - Terraform/IaC changes
    - Docker/Compose configurations
    - Cloud resource management

    CHEF-208: Captures insights to state for checkpoint persistence.
    """
    agent = get_agent("infrastructure")

    try:
        response = await agent.invoke(state["messages"])
        result_content = (
            response.content if hasattr(response, "content") else str(response)
        )
        logger.info(
            f"[LangGraph] infrastructure completed. Response length: {len(result_content)}"
        )

        # Collect insights for checkpoint persistence (CHEF-208)
        captured_insights = _collect_agent_insights(agent, state, "infrastructure")

        return {
            "messages": [response],
            "current_agent": "infrastructure",
            "next_agent": "supervisor",
            "task_result": {
                "agent": "infrastructure",
                "completed": True,
                "output_length": len(result_content),
            },
            "captured_insights": captured_insights,
        }
    except Exception as e:
        logger.error(f"[LangGraph] infrastructure failed: {e}")
        return {
            "messages": [AIMessage(content=f"Infrastructure error: {e}")],
            "current_agent": "infrastructure",
            "next_agent": "supervisor",
            "task_result": {
                "agent": "infrastructure",
                "completed": False,
                "error": str(e),
            },
        }


@traceable(name="cicd_node", tags=["langgraph", "node", "cicd"])
async def cicd_node(state: WorkflowState) -> WorkflowState:
    """CI/CD agent node - handles deployments.

    Uses CICDAgent with llama3-8b model for:
    - GitHub Actions workflows
    - Deployment pipelines
    - CI configuration

    CHEF-208: Captures insights to state for checkpoint persistence.
    """
    agent = get_agent("cicd")

    try:
        response = await agent.invoke(state["messages"])
        result_content = (
            response.content if hasattr(response, "content") else str(response)
        )
        logger.info(
            f"[LangGraph] cicd completed. Response length: {len(result_content)}"
        )

        # Collect insights for checkpoint persistence (CHEF-208)
        captured_insights = _collect_agent_insights(agent, state, "cicd")

        return {
            "messages": [response],
            "current_agent": "cicd",
            "next_agent": "supervisor",
            "task_result": {
                "agent": "cicd",
                "completed": True,
                "output_length": len(result_content),
            },
            "captured_insights": captured_insights,
        }
    except Exception as e:
        logger.error(f"[LangGraph] cicd failed: {e}")
        return {
            "messages": [AIMessage(content=f"CI/CD error: {e}")],
            "current_agent": "cicd",
            "next_agent": "supervisor",
            "task_result": {"agent": "cicd", "completed": False, "error": str(e)},
        }


@traceable(name="documentation_node", tags=["langgraph", "node", "documentation"])
async def documentation_node(state: WorkflowState) -> WorkflowState:
    """Documentation agent node - writes technical docs.

    Uses DocumentationAgent with mistral-nemo model for:
    - API documentation
    - README generation
    - JSDoc/docstrings

    CHEF-208: Captures insights to state for checkpoint persistence.
    """
    agent = get_agent("documentation")

    try:
        response = await agent.invoke(state["messages"])
        result_content = (
            response.content if hasattr(response, "content") else str(response)
        )
        logger.info(
            f"[LangGraph] documentation completed. Response length: {len(result_content)}"
        )

        # Collect insights for checkpoint persistence (CHEF-208)
        captured_insights = _collect_agent_insights(agent, state, "documentation")

        return {
            "messages": [response],
            "current_agent": "documentation",
            "next_agent": "supervisor",
            "task_result": {
                "agent": "documentation",
                "completed": True,
                "output_length": len(result_content),
            },
            "captured_insights": captured_insights,
        }
    except Exception as e:
        logger.error(f"[LangGraph] documentation failed: {e}")
        return {
            "messages": [AIMessage(content=f"Documentation error: {e}")],
            "current_agent": "documentation",
            "next_agent": "supervisor",
            "task_result": {
                "agent": "documentation",
                "completed": False,
                "error": str(e),
            },
        }


@traceable(name="approval_node", tags=["langgraph", "node", "hitl", "approval"])
async def approval_node(state: WorkflowState) -> WorkflowState:
    """HITL approval node - interrupts workflow for human approval.

    Uses LangGraph interrupt() to pause execution and save state.
    Workflow resumes via:
    1. Linear webhook (primary) - instant notification when approval emoji added
    2. Polling fallback (secondary) - catches missed webhooks every 30s

    The interrupt saves checkpoint state including:
    - approval_request_id for tracking
    - risk_level for audit trail
    - pending_operation description
    """
    from lib.hitl_manager import get_hitl_manager
    from lib.risk_assessor import get_risk_assessor

    hitl_manager = get_hitl_manager()
    risk_assessor = get_risk_assessor()

    # Extract task description from messages
    task_description = state.get("pending_operation", "")
    if not task_description:
        for msg in reversed(state["messages"]):
            if isinstance(msg, HumanMessage):
                task_description = msg.content[:500]
                break

    # Build risk context
    risk_context = {
        "operation": "workflow_execution",
        "description": task_description,
        "environment": "production",  # Conservative default
        "resource_type": "workflow",
        "agent_name": state.get("current_agent", "unknown"),
    }

    # Assess risk level
    risk_level = risk_assessor.assess_task(risk_context)
    requires_hitl = risk_assessor.requires_approval(risk_level)

    if requires_hitl:
        # Create approval request in database
        try:
            request_id = await hitl_manager.create_approval_request(
                workflow_id=state.get("workflow_id", str(uuid.uuid4())),
                thread_id=state.get("thread_id", ""),
                checkpoint_id=f"checkpoint-{uuid.uuid4()}",
                task=risk_context,
                agent_name=state.get("current_agent", "orchestrator"),
            )

            if request_id:
                logger.info(
                    f"[HITL] Created approval request {request_id} "
                    f"(risk={risk_level}, operation={task_description[:100]})"
                )

                # LangGraph interrupt - saves state and exits workflow
                # Resume happens via webhook or polling in main.py
                interrupt(
                    {
                        "approval_request_id": request_id,
                        "risk_level": risk_level,
                        "pending_operation": task_description,
                        "message": f"Workflow paused for HITL approval. Request ID: {request_id}",
                    }
                )

        except Exception as e:
            logger.error(f"[HITL] Failed to create approval request: {e}")
            # On failure, log and continue (fail-open for non-critical)
            return {
                "messages": [
                    AIMessage(
                        content=f"HITL approval creation failed: {e}. Proceeding with caution."
                    )
                ],
                "current_agent": "approval",
                "next_agent": state.get("next_agent", "supervisor"),
                "approvals": [],
                "requires_approval": False,
            }

    # If we reach here, either no approval needed or interrupt didn't block
    return {
        "messages": [AIMessage(content=f"Approval granted (risk_level={risk_level})")],
        "current_agent": "approval",
        "next_agent": state.get("next_agent", "supervisor"),
        "approvals": [],
        "requires_approval": False,
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
    if next_agent in [
        "feature-dev",
        "code-review",
        "infrastructure",
        "cicd",
        "documentation",
    ]:
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
        },
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
