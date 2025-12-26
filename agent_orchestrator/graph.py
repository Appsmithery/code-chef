"""LangGraph multi-agent workflow for orchestrator.

This module defines the stateful workflow graph that coordinates multiple
specialized agents (supervisor, feature-dev, code-review, infrastructure, cicd, documentation).

Architecture:
- Supervisor agent routes tasks to specialized agents
- Conditional edges based on LLM routing decisions
- HITL approval nodes for high-risk operations
- PostgreSQL checkpointing for workflow resume
- **WorkflowEngine integration for declarative YAML templates** (Phase 6 - CHEF-110)

Workflow Execution Modes:
1. **Supervisor-driven**: Dynamic LLM routing via supervisor node (default)
2. **Template-driven**: Declarative YAML workflows via WorkflowEngine

The template-driven mode enables:
- Deterministic step execution from YAML templates
- LLM decision gates at strategic points
- Event-sourced state for auditability
- Resource locking for concurrent operation prevention
"""

import hashlib
import logging
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Annotated, Any, Dict, List, Literal, Optional, TypedDict

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.graph import END, StateGraph
from langgraph.types import interrupt
from langsmith import traceable
from pydantic import BaseModel, Field, model_validator

logger = logging.getLogger(__name__)

# Add shared modules to path
sys.path.insert(0, str(Path(__file__).parent.parent / "shared"))

# Import real agent classes from agents module
from agents import get_agent as get_real_agent

# Import WorkflowEngine for template-driven execution (Phase 6 - CHEF-110)
from workflows.workflow_engine import WorkflowEngine
from workflows.workflow_engine import WorkflowStatus as WFStatus
from workflows.workflow_router import WorkflowRouter, get_workflow_router

# Import error recovery decorator for agent-level resilience (CHEF-Error-Handling)
try:
    from shared.lib.error_recovery_engine import RecoveryTier, with_recovery

    ERROR_RECOVERY_ENABLED = True
    logger.info("[LangGraph] Error recovery decorator available for agent nodes")
except ImportError:
    ERROR_RECOVERY_ENABLED = False

    # Fallback no-op decorator
    def with_recovery(*args, **kwargs):
        def decorator(func):
            return func

        return decorator

    from enum import IntEnum

    class RecoveryTier(IntEnum):
        TIER_0 = 0
        TIER_1 = 1

    logger.warning("[LangGraph] Error recovery decorator not available")


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

    Template-Driven Workflow Fields (CHEF-110):
        workflow_template: Name of YAML template to execute (e.g., "pr-deployment.workflow.yaml")
        workflow_context: Initial context variables for template rendering
        use_template_engine: Whether to use WorkflowEngine instead of supervisor routing

    Project Context Fields (RAG Isolation):
        project_context: Project identification for RAG query isolation
            - project_id: Linear project ID or GitHub repo URL
            - repository_url: GitHub repository URL
            - workspace_name: VS Code workspace name
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
    # Template-driven workflow fields (CHEF-110)
    workflow_template: Optional[
        str
    ]  # YAML template name (e.g., "pr-deployment.workflow.yaml")
    workflow_context: Optional[Dict[str, Any]]  # Template context variables
    use_template_engine: bool  # If True, use WorkflowEngine instead of supervisor
    # Project context for RAG isolation
    project_context: Optional[
        Dict[str, Any]
    ]  # project_id, repository_url, workspace_name
    # Routing decision (structured output from supervisor)
    routing_decision: Optional[Dict[str, Any]]  # Routing metadata (not user-facing)


class RoutingDecision(BaseModel):
    """Structured output from supervisor agent routing decision."""

    agent_name: str = Field(
        description="Name of the specialist agent to route to (feature-dev, code-review, infrastructure, cicd, documentation) or 'end' to finish"
    )
    requires_approval: bool = Field(
        default=False,
        description="Whether this operation requires human approval (HITL)",
    )
    reasoning: str = Field(
        description="Brief explanation of routing decision in conversational tone"
    )

    @model_validator(mode="before")
    @classmethod
    def handle_aliases(cls, data: Any) -> Any:
        """Handle hallucinated field names from LLM (e.g. next_agent instead of agent_name)."""
        if isinstance(data, dict):
            if "next_agent" in data and "agent_name" not in data:
                data["agent_name"] = data["next_agent"]
        return data

    routing_metadata: Optional[Dict[str, Any]] = Field(
        default=None, description="Internal routing metadata (not shown to user)"
    )


# Agent cache with bound LLM instances
_agent_cache: Dict[str, Any] = {}

# WorkflowEngine instance for template-driven execution (Phase 6 - CHEF-110)
_workflow_engine: Optional[WorkflowEngine] = None
_workflow_router: Optional[WorkflowRouter] = None


def get_workflow_engine() -> WorkflowEngine:
    """Get or create WorkflowEngine singleton.

    Provides template-driven workflow execution as an alternative to
    supervisor-based dynamic routing.

    Returns:
        WorkflowEngine instance
    """
    global _workflow_engine
    if _workflow_engine is None:
        _workflow_engine = WorkflowEngine(
            templates_dir="agent_orchestrator/workflows/templates"
        )
        logger.info(
            "[LangGraph] Initialized WorkflowEngine for template-driven execution"
        )
    return _workflow_engine


def get_router() -> WorkflowRouter:
    """Get or create WorkflowRouter singleton.

    Routes incoming tasks to appropriate workflow templates based on
    heuristic pattern matching with LLM fallback.

    Returns:
        WorkflowRouter instance
    """
    global _workflow_router
    if _workflow_router is None:
        _workflow_router = get_workflow_router()
        logger.info("[LangGraph] Initialized WorkflowRouter for task→workflow matching")
    return _workflow_router


def get_agent(agent_name: str, project_context: Optional[Dict[str, Any]] = None):
    """Get or create agent instance using real BaseAgent implementations.

    Uses the agent registry from agents/__init__.py which provides:
    - SupervisorAgent, FeatureDevAgent, CodeReviewAgent, etc.
    - Each agent has LLM, MCP tools, and system prompts configured

    Args:
        agent_name: Name of agent (supervisor, feature-dev, code-review, etc.)
        project_context: Project context dict with project_id, repository_url, workspace_name

    Returns:
        BaseAgent instance with invoke() method
    """
    # Create cache key including project context for isolation
    cache_key = agent_name
    if project_context:
        project_id = project_context.get("project_id", "")
        cache_key = f"{agent_name}:{project_id}"

    if cache_key not in _agent_cache:
        try:
            _agent_cache[cache_key] = get_real_agent(
                agent_name, project_context=project_context
            )
            logger.info(
                f"[LangGraph] Initialized agent: {agent_name} (project: {project_context.get('project_id') if project_context else 'none'})"
            )
        except Exception as e:
            logger.error(f"[LangGraph] Failed to initialize agent {agent_name}: {e}")
            raise

    return _agent_cache[cache_key]


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


# Define agent nodes with error recovery decorators (CHEF-Error-Handling)
# @with_recovery handles Tier 0-1 errors locally with configurable retry counts


@traceable(
    name="conversational_handler_node",
    tags=["langgraph", "node", "conversational", "ask-mode"],
)
async def conversational_handler_node(state: WorkflowState) -> WorkflowState:
    """Conversational handler for Ask mode - Q&A with information-gathering tools.

    This node provides responses for questions, status queries, and clarifications.
    It CAN use read-only tools for accurate information (MCP servers, status checks).

    Use Cases:
    - "What can you do?" → Lists available MCP tools and capabilities
    - "What's the status of task-123?" → Queries database/Linear
    - "Which files use authentication?" → Searches codebase via MCP
    - General questions requiring workspace context

    Allows:
    - Read-only tool invocations (MCP filesystem search, memory queries, status checks)
    - Multi-turn conversations with context

    Blocks:
    - Task execution (use supervisor_node → agent routing)
    - Write operations (file edits, deployments, Linear issue creation)
    """
    from agents.supervisor import SupervisorAgent
    from langchain_core.messages import AIMessage, HumanMessage
    from lib.llm_client import get_llm_client

    try:
        # Get supervisor agent WITH tool access (read-only tools available)
        supervisor = SupervisorAgent()

        # Extract last user message
        last_message = state["messages"][-1] if state["messages"] else None
        if not last_message:
            return {
                "messages": [
                    AIMessage(
                        content="I didn't receive any message. How can I help you?"
                    )
                ],
                "current_agent": "conversational",
                "next_agent": None,
                "task_result": {"agent": "conversational", "completed": True},
            }

        user_query = (
            last_message.content
            if hasattr(last_message, "content")
            else str(last_message)
        )

        # Invoke supervisor with Ask mode constraints
        # Supervisor will use its v4.0 system prompt which includes MCP awareness
        response = await supervisor.invoke(
            messages=[HumanMessage(content=user_query)],
            config={"configurable": {"mode": "ask", "current_agent": "supervisor"}},
        )

        # Response is a BaseMessage (AIMessage from supervisor)
        response_content = (
            response.content if hasattr(response, "content") else str(response)
        )

        logger.info(
            f"[LangGraph] Conversational handler (Ask mode) completed. Response length: {len(response_content)}"
        )

        return {
            "messages": [response],
            "current_agent": "conversational",
            "next_agent": None,  # Terminal node
            "task_result": {
                "agent": "conversational",
                "completed": True,
                "output_length": len(response_content),
                "mode": "ask",
            },
        }
    except Exception as e:
        logger.error(f"[LangGraph] Conversational handler failed: {e}", exc_info=True)
        return {
            "messages": [
                AIMessage(
                    content=f"I encountered an error: {str(e)}. Please try rephrasing your question."
                )
            ],
            "current_agent": "conversational",
            "next_agent": None,
            "task_result": {
                "agent": "conversational",
                "completed": False,
                "error": str(e),
            },
        }


@traceable(name="supervisor_node", tags=["langgraph", "node", "supervisor"])
@with_recovery(
    max_retries=2,
    max_tier=RecoveryTier.TIER_1,
    step_id="supervisor",
    agent_name="supervisor",
)
async def supervisor_node(state: WorkflowState) -> WorkflowState:
    """Supervisor agent node - routes tasks to specialized agents.

    Uses the real SupervisorAgent with LLM to analyze the task and decide:
    1. Which specialized agent should handle it
    2. Whether it requires HITL approval (high-risk operations)

    Uses Pydantic structured output to get clean JSON routing decisions
    instead of text parsing. Routing metadata is kept separate from
    user-facing messages.
    """
    project_context = state.get("project_context")
    supervisor = get_agent("supervisor", project_context=project_context)

    # Add routing instruction to messages
    routing_prompt = """You're having a conversation with a developer. Based on their message, decide:

1. Which specialist should help them:
   - feature-dev: Writing/fixing code, implementing features
   - code-review: Checking security, code quality, best practices
   - infrastructure: Cloud setup, Docker, Kubernetes, IaC
   - cicd: Build pipelines, deployments, automation
   - documentation: README, API docs, code comments
   - conversational: General questions, greetings, status queries, "what can you do?"

2. Is this risky enough to need human approval?
   - Production deployments, infrastructure changes, DB migrations, destructive operations → YES
   - Code generation, reviews, docs, local testing, conversations → NO

Provide:
- agent_name: The specialist name (or 'conversational' for chat, or 'end' if done)
- requires_approval: true/false for HITL approval
- reasoning: Brief explanation in conversational tone

If the request is unclear, set agent_name='conversational' and ask for clarification in reasoning.
"""

    messages = state["messages"] + [HumanMessage(content=routing_prompt)]

    try:
        # Get supervisor agent with structured output
        from langchain_core.output_parsers import PydanticOutputParser

        # Configure LLM to return structured output
        # CHEF-208: Use more robust parsing for supervisor routing
        try:
            llm_with_structure = supervisor.llm.with_structured_output(RoutingDecision)
            routing_decision: RoutingDecision = await llm_with_structure.ainvoke(
                messages
            )
        except Exception as e:
            logger.warning(
                f"[LangGraph] Structured output failed for supervisor, attempting manual parse: {e}"
            )
            # Fallback: get raw output and parse manually
            raw_res = await supervisor.llm.ainvoke(messages)
            content = raw_res.content

            # Simple JSON extraction
            import json
            import re

            json_match = re.search(r"\{.*\}", content, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                # Fix common issues like trailing braces
                try:
                    data = json.loads(json_str)
                except json.JSONDecodeError:
                    # Try to fix trailing characters (common with some models)
                    if json_str.count("{") < json_str.count("}"):
                        json_str = json_str.rsplit("}", 1)[0]
                        data = json.loads(json_str)
                    else:
                        raise

                routing_decision = RoutingDecision(**data)
            else:
                # Last resort: default to conversational
                logger.error(
                    f"[LangGraph] Failed to parse supervisor output: {content}"
                )
                routing_decision = RoutingDecision(
                    agent_name="conversational",
                    requires_approval=False,
                    reasoning="I encountered an error processing your request. How can I help you?",
                )

        logger.info(
            f"[LangGraph] Supervisor routed to: {routing_decision.agent_name}, "
            f"approval_required: {routing_decision.requires_approval}"
        )

        # Create a user-facing message with just the reasoning (no routing metadata)
        conversational_response = AIMessage(
            content=routing_decision.reasoning,
            additional_kwargs={"routing_decision": routing_decision.model_dump()},
        )

        return {
            "messages": [conversational_response],
            "current_agent": "supervisor",
            "next_agent": routing_decision.agent_name.lower(),
            "requires_approval": routing_decision.requires_approval,
            "pending_operation": routing_decision.reasoning,
            "routing_decision": routing_decision.model_dump(),  # Store in state for debugging
        }

    except Exception as e:
        logger.error(f"[LangGraph] Supervisor invoke failed: {e}")
        # Fallback to end state on error
        return {
            "messages": [
                AIMessage(
                    content=f"I encountered an error routing your request. Let me try again or please rephrase."
                )
            ],
            "current_agent": "supervisor",
            "next_agent": "end",
            "requires_approval": False,
            "task_result": {"error": str(e)},
        }


@traceable(name="feature_dev_node", tags=["langgraph", "node", "feature-dev"])
@with_recovery(
    max_retries=3,
    max_tier=RecoveryTier.TIER_1,
    step_id="feature-dev",
    agent_name="feature-dev",
)
async def feature_dev_node(state: WorkflowState) -> WorkflowState:
    """Feature development agent node - implements code.

    Uses FeatureDevAgent with Qwen 2.5 Coder 32B (OpenRouter) for:
    - Code implementation
    - Refactoring
    - Bug fixes

    CHEF-208: Captures insights to state for checkpoint persistence.
    Phase 3: Performs risk assessment for code changes and routes to approval if needed.
    """
    project_context = state.get("project_context")
    agent = get_agent("feature-dev", project_context=project_context)

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

        # Phase 3: Perform risk assessment for code changes
        risk_context = {
            "operation": "code_modification",
            "environment": state.get("environment", "production"),
            "description": state.get("pending_operation", "Code implementation"),
            "files_changed": state.get("files_changed", 0),
            "agent_name": "feature-dev",
        }

        from lib.risk_assessor import get_risk_assessor

        risk_assessor = get_risk_assessor()
        risk_level = risk_assessor.assess_task(risk_context)
        requires_approval = risk_assessor.requires_approval(risk_level)

        # If high-risk code changes, route to approval node
        if requires_approval:
            logger.info(
                f"[LangGraph] feature-dev: High-risk code changes detected ({risk_level}), routing to approval"
            )
            return {
                "messages": [response],
                "current_agent": "feature-dev",
                "next_agent": "approval",  # Route to approval instead of supervisor
                "requires_approval": True,
                "pending_operation": f"Deploy code changes: {result_content[:200]}",
                "pr_context": state.get("pr_context", {}),  # Pass through PR context
                "task_result": {
                    "agent": "feature-dev",
                    "completed": True,
                    "output_length": len(result_content),
                    "risk_level": risk_level,
                },
                "captured_insights": captured_insights,
            }

        return {
            "messages": [response],
            "current_agent": "feature-dev",
            "next_agent": "supervisor",  # Low risk: return to supervisor
            "requires_approval": False,
            "task_result": {
                "agent": "feature-dev",
                "completed": True,
                "output_length": len(result_content),
                "risk_level": risk_level,
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
@with_recovery(
    max_retries=3,
    max_tier=RecoveryTier.TIER_1,
    step_id="code-review",
    agent_name="code-review",
)
async def code_review_node(state: WorkflowState) -> WorkflowState:
    """Code review agent node - analyzes code quality.

    Uses CodeReviewAgent with DeepSeek V3 (OpenRouter) for:
    - OWASP Top 10 security analysis
    - Code quality checks
    - Best practices validation

    CHEF-208: Captures insights to state for checkpoint persistence.
    """
    project_context = state.get("project_context")
    agent = get_agent("code-review", project_context=project_context)

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
@with_recovery(
    max_retries=2,
    max_tier=RecoveryTier.TIER_1,
    step_id="infrastructure",
    agent_name="infrastructure",
)
async def infrastructure_node(state: WorkflowState) -> WorkflowState:
    """Infrastructure agent node - manages cloud resources.

    Uses InfrastructureAgent with Gemini 2.0 Flash (OpenRouter) for:
    - Terraform/IaC changes
    - Docker/Compose configurations
    - Cloud resource management

    CHEF-208: Captures insights to state for checkpoint persistence.
    Phase 3: Performs risk assessment for infrastructure changes and routes to approval if needed.
    """
    project_context = state.get("project_context")
    agent = get_agent("infrastructure", project_context=project_context)

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

        # Phase 3: Perform risk assessment for infrastructure changes
        risk_context = {
            "operation": "infrastructure_modification",
            "environment": state.get("environment", "production"),
            "description": state.get("pending_operation", "Infrastructure change"),
            "resource_type": "infrastructure",
            "agent_name": "infrastructure",
        }

        from lib.risk_assessor import get_risk_assessor

        risk_assessor = get_risk_assessor()
        risk_level = risk_assessor.assess_task(risk_context)
        requires_approval = risk_assessor.requires_approval(risk_level)

        # If high-risk infrastructure changes, route to approval node
        if requires_approval:
            logger.info(
                f"[LangGraph] infrastructure: High-risk changes detected ({risk_level}), routing to approval"
            )
            return {
                "messages": [response],
                "current_agent": "infrastructure",
                "next_agent": "approval",  # Route to approval instead of supervisor
                "requires_approval": True,
                "pending_operation": f"Deploy infrastructure changes: {result_content[:200]}",
                "pr_context": state.get("pr_context", {}),  # Pass through PR context
                "task_result": {
                    "agent": "infrastructure",
                    "completed": True,
                    "output_length": len(result_content),
                    "risk_level": risk_level,
                },
                "captured_insights": captured_insights,
            }

        return {
            "messages": [response],
            "current_agent": "infrastructure",
            "next_agent": "supervisor",  # Low risk: return to supervisor
            "requires_approval": False,
            "task_result": {
                "agent": "infrastructure",
                "completed": True,
                "output_length": len(result_content),
                "risk_level": risk_level,
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
@with_recovery(
    max_retries=2, max_tier=RecoveryTier.TIER_1, step_id="cicd", agent_name="cicd"
)
async def cicd_node(state: WorkflowState) -> WorkflowState:
    """CI/CD agent node - handles deployments.

    Uses CICDAgent with Gemini 2.0 Flash (OpenRouter) for:
    - GitHub Actions workflows
    - Deployment pipelines
    - CI configuration

    CHEF-208: Captures insights to state for checkpoint persistence.
    Phase 3: Performs risk assessment for deployments and extracts PR context from state.
    """
    project_context = state.get("project_context")
    agent = get_agent("cicd", project_context=project_context)

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

        # Phase 3: Perform risk assessment for deployments
        # CI/CD is particularly important as it handles production deployments
        risk_context = {
            "operation": "deploy",
            "environment": state.get("environment", "production"),
            "description": state.get("pending_operation", "Deployment"),
            "resource_type": "deployment",
            "agent_name": "cicd",
        }

        from lib.risk_assessor import get_risk_assessor

        risk_assessor = get_risk_assessor()
        risk_level = risk_assessor.assess_task(risk_context)
        requires_approval = risk_assessor.requires_approval(risk_level)

        # If high-risk deployment (e.g., production), route to approval node
        if requires_approval:
            logger.info(
                f"[LangGraph] cicd: High-risk deployment detected ({risk_level}), routing to approval"
            )
            return {
                "messages": [response],
                "current_agent": "cicd",
                "next_agent": "approval",  # Route to approval instead of supervisor
                "requires_approval": True,
                "pending_operation": f"Deploy to {risk_context['environment']}: {result_content[:200]}",
                "pr_context": state.get("pr_context", {}),  # Pass through PR context
                "task_result": {
                    "agent": "cicd",
                    "completed": True,
                    "output_length": len(result_content),
                    "risk_level": risk_level,
                },
                "captured_insights": captured_insights,
            }

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
@with_recovery(
    max_retries=3,
    max_tier=RecoveryTier.TIER_1,
    step_id="documentation",
    agent_name="documentation",
)
async def documentation_node(state: WorkflowState) -> WorkflowState:
    """Documentation agent node - writes technical docs.

    Uses DocumentationAgent with mistral-nemo model for:
    - API documentation
    - README generation
    - JSDoc/docstrings

    CHEF-208: Captures insights to state for checkpoint persistence.
    """
    project_context = state.get("project_context")
    agent = get_agent("documentation", project_context=project_context)

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
    - pr_context (if available) for GitHub PR comment integration
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
            # Extract PR context if available (Phase 3 enhancement)
            pr_context = state.get("pr_context", {})
            pr_number = pr_context.get("pr_number")
            pr_url = pr_context.get("pr_url")
            github_repo = pr_context.get("github_repo")

            request_id = await hitl_manager.create_approval_request(
                workflow_id=state.get("workflow_id", str(uuid.uuid4())),
                thread_id=state.get("thread_id", ""),
                checkpoint_id=f"checkpoint-{uuid.uuid4()}",
                task=risk_context,
                agent_name=state.get("current_agent", "orchestrator"),
                pr_number=pr_number,  # Phase 3: PR context
                pr_url=pr_url,  # Phase 3: PR context
                github_repo=github_repo,  # Phase 3: PR context
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


# =========================================================================
# TEMPLATE-DRIVEN WORKFLOW EXECUTION (Phase 6 - CHEF-110)
# =========================================================================


@traceable(
    name="workflow_router_node", tags=["langgraph", "node", "workflow", "router"]
)
async def workflow_router_node(state: WorkflowState) -> WorkflowState:
    """Route incoming task to appropriate workflow template.

    Uses WorkflowRouter to match task description against available YAML
    workflow templates. Falls back to supervisor-based routing if no
    template matches with sufficient confidence.

    This node runs at the start of the graph when use_template_engine=True,
    selecting the right workflow template for the task.
    """
    router = get_router()

    # Extract task description from messages
    task_description = ""
    for msg in state["messages"]:
        if isinstance(msg, HumanMessage):
            task_description = msg.content
            break

    if not task_description:
        logger.warning(
            "[WorkflowRouter] No task description found, falling back to supervisor"
        )
        return {
            "messages": [],
            "current_agent": "workflow_router",
            "next_agent": "supervisor",
            "use_template_engine": False,
        }

    try:
        # Route task to workflow template
        selection = await router.route(task_description)

        if selection.confidence >= 0.7:
            logger.info(
                f"[WorkflowRouter] Matched '{selection.workflow_id}' "
                f"(confidence={selection.confidence:.2f}, method={selection.method})"
            )
            return {
                "messages": [
                    AIMessage(
                        content=f"Routed to workflow template: {selection.workflow_id} "
                        f"(confidence: {selection.confidence:.2f})"
                    )
                ],
                "current_agent": "workflow_router",
                "next_agent": "workflow_executor",
                "workflow_template": f"{selection.workflow_id}.workflow.yaml",
                "use_template_engine": True,
            }
        else:
            # Low confidence - fall back to supervisor
            logger.info(
                f"[WorkflowRouter] Low confidence ({selection.confidence:.2f}), "
                f"falling back to supervisor routing"
            )
            return {
                "messages": [
                    AIMessage(
                        content=f"Workflow routing uncertain (confidence: {selection.confidence:.2f}). "
                        f"Using supervisor for dynamic routing."
                    )
                ],
                "current_agent": "workflow_router",
                "next_agent": "supervisor",
                "use_template_engine": False,
            }

    except Exception as e:
        logger.error(f"[WorkflowRouter] Routing failed: {e}")
        return {
            "messages": [AIMessage(content=f"Workflow routing error: {e}")],
            "current_agent": "workflow_router",
            "next_agent": "supervisor",
            "use_template_engine": False,
        }


@traceable(
    name="workflow_executor_node", tags=["langgraph", "node", "workflow", "executor"]
)
async def workflow_executor_node(state: WorkflowState) -> WorkflowState:
    """Execute workflow using declarative YAML template.

    Runs the full workflow template via WorkflowEngine, which handles:
    - Sequential step execution
    - LLM decision gates
    - HITL approval integration
    - Resource locking
    - Event-sourced state persistence

    This replaces the supervisor→agent→supervisor loop with a single
    template-driven execution.
    """
    engine = get_workflow_engine()

    template_name = state.get("workflow_template")
    if not template_name:
        logger.error("[WorkflowExecutor] No workflow template specified")
        return {
            "messages": [AIMessage(content="No workflow template specified")],
            "current_agent": "workflow_executor",
            "next_agent": "end",
            "task_result": {"error": "No workflow template specified"},
        }

    # Build context from messages and existing workflow_context
    context = dict(state.get("workflow_context") or {})

    # Extract additional context from messages
    for msg in state["messages"]:
        if isinstance(msg, HumanMessage):
            context["task_description"] = msg.content
            break

    context["workflow_id"] = state.get("workflow_id", str(uuid.uuid4()))
    context["thread_id"] = state.get("thread_id", "")

    logger.info(
        f"[WorkflowExecutor] Executing template '{template_name}' "
        f"with context keys: {list(context.keys())}"
    )

    try:
        # Execute workflow via WorkflowEngine
        workflow_state = await engine.execute_workflow(
            template_name=template_name,
            context=context,
        )

        # Check workflow result
        if workflow_state.status == WFStatus.COMPLETED:
            logger.info(f"[WorkflowExecutor] Workflow completed successfully")
            return {
                "messages": [
                    AIMessage(
                        content=f"Workflow '{workflow_state.definition.name}' completed. "
                        f"Steps executed: {len(workflow_state.outputs)}"
                    )
                ],
                "current_agent": "workflow_executor",
                "next_agent": "end",
                "task_result": {
                    "workflow_name": workflow_state.definition.name,
                    "status": "completed",
                    "outputs": workflow_state.outputs,
                    "steps_completed": len(
                        [
                            s
                            for s, st in workflow_state.step_statuses.items()
                            if st.value == "completed"
                        ]
                    ),
                },
            }

        elif workflow_state.status == WFStatus.PAUSED:
            # HITL approval required - interrupt for resume
            logger.info(f"[WorkflowExecutor] Workflow paused for HITL approval")
            return {
                "messages": [
                    AIMessage(
                        content=f"Workflow paused at step '{workflow_state.current_step}' "
                        f"awaiting HITL approval."
                    )
                ],
                "current_agent": "workflow_executor",
                "next_agent": "approval",
                "requires_approval": True,
                "pending_operation": f"Workflow '{workflow_state.definition.name}' step: {workflow_state.current_step}",
            }

        else:
            # Workflow failed
            logger.error(
                f"[WorkflowExecutor] Workflow failed: {workflow_state.error_message}"
            )
            return {
                "messages": [
                    AIMessage(
                        content=f"Workflow failed at step '{workflow_state.failed_step}': "
                        f"{workflow_state.error_message}"
                    )
                ],
                "current_agent": "workflow_executor",
                "next_agent": "end",
                "task_result": {
                    "status": "failed",
                    "error": workflow_state.error_message,
                    "failed_step": workflow_state.failed_step,
                },
            }

    except Exception as e:
        logger.error(f"[WorkflowExecutor] Execution failed: {e}", exc_info=True)
        return {
            "messages": [AIMessage(content=f"Workflow execution error: {e}")],
            "current_agent": "workflow_executor",
            "next_agent": "end",
            "task_result": {"status": "error", "error": str(e)},
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

    # Route to specialized agents
    if next_agent in [
        "feature-dev",
        "code-review",
        "infrastructure",
        "cicd",
        "documentation",
    ]:
        return next_agent

    # Route general queries to conversational handler
    if next_agent in [
        "conversational",
        "supervisor",
    ]:  # Handle supervisor as conversational
        return "conversational"

    return "end"


def should_continue(state: WorkflowState) -> str:
    """Decide if workflow should continue or end.

    Checks if there are more agents to route to.
    """
    next_agent = state.get("next_agent", "end")
    return "supervisor" if next_agent != "end" else "end"


def route_entry_point(state: WorkflowState) -> str:
    """Route from entry point to either workflow router or supervisor.

    Determines whether to use template-driven (WorkflowEngine) or
    supervisor-driven (LLM dynamic) routing based on state flags.

    Phase 6 - CHEF-110: Enables declarative workflow templates.
    """
    # Explicit template mode
    if state.get("use_template_engine", False) and state.get("workflow_template"):
        return "workflow_executor"

    # Check if we should try workflow routing first
    # (can be enabled globally or per-request)
    if state.get("use_template_engine", False):
        return "workflow_router"

    # Default: supervisor-based dynamic routing
    return "supervisor"


def route_from_workflow_router(state: WorkflowState) -> str:
    """Route from workflow router to executor or supervisor.

    After WorkflowRouter attempts to match a template:
    - If matched with confidence >= 0.7 → workflow_executor
    - Otherwise → supervisor (fallback to dynamic routing)
    """
    next_agent = state.get("next_agent", "supervisor")

    if next_agent == "workflow_executor" and state.get("workflow_template"):
        return "workflow_executor"

    return "supervisor"


def route_from_workflow_executor(state: WorkflowState) -> str:
    """Route from workflow executor after template execution.

    After WorkflowEngine executes a template:
    - If completed → end
    - If paused for HITL → approval
    - If failed → end (with error in task_result)
    """
    if state.get("requires_approval", False):
        return "approval"

    return "end"


# Build the workflow graph
def create_workflow(checkpoint_conn_string: str = None) -> StateGraph:
    """Create the LangGraph workflow with all agent nodes.

    Supports two execution modes (CHEF-110):
    1. **Supervisor-driven**: Dynamic LLM routing via supervisor node (default)
    2. **Template-driven**: Declarative YAML workflows via WorkflowEngine

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
    workflow.add_node("conversational", conversational_handler_node)
    workflow.add_node("feature-dev", feature_dev_node)
    workflow.add_node("code-review", code_review_node)
    workflow.add_node("infrastructure", infrastructure_node)
    workflow.add_node("cicd", cicd_node)
    workflow.add_node("documentation", documentation_node)
    workflow.add_node("approval", approval_node)

    # Add template-driven workflow nodes (CHEF-110)
    workflow.add_node("workflow_router", workflow_router_node)
    workflow.add_node("workflow_executor", workflow_executor_node)

    # Set entry point with conditional routing
    workflow.set_entry_point("entry_router")

    # Entry router: Choose between template-driven or supervisor-driven
    workflow.add_node("entry_router", lambda state: state)  # Pass-through node
    workflow.add_conditional_edges(
        "entry_router",
        route_entry_point,
        {
            "workflow_router": "workflow_router",
            "workflow_executor": "workflow_executor",
            "supervisor": "supervisor",
        },
    )

    # Workflow router routes to executor or falls back to supervisor
    workflow.add_conditional_edges(
        "workflow_router",
        route_from_workflow_router,
        {
            "workflow_executor": "workflow_executor",
            "supervisor": "supervisor",
        },
    )

    # Workflow executor routes to approval or end
    workflow.add_conditional_edges(
        "workflow_executor",
        route_from_workflow_executor,
        {
            "approval": "approval",
            "end": END,
        },
    )

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
            "conversational": "conversational",
            "approval": "approval",
            "end": END,
        },
    )

    # Phase 3: Add conditional routing from agents to approval or supervisor
    def route_from_agent(state: WorkflowState) -> str:
        """Route from agent node based on requires_approval flag."""
        if state.get("requires_approval", False):
            return "approval"
        return "supervisor"

    # Conditional edges for agents that can route to approval
    workflow.add_conditional_edges(
        "feature-dev",
        route_from_agent,
        {"approval": "approval", "supervisor": "supervisor"},
    )
    workflow.add_conditional_edges(
        "infrastructure",
        route_from_agent,
        {"approval": "approval", "supervisor": "supervisor"},
    )
    workflow.add_conditional_edges(
        "cicd",
        route_from_agent,
        {"approval": "approval", "supervisor": "supervisor"},
    )

    # These agents still route directly back to supervisor
    workflow.add_edge("code-review", "supervisor")
    workflow.add_edge("documentation", "supervisor")
    workflow.add_edge("approval", "supervisor")

    # Conversational handler is terminal - goes directly to END
    workflow.add_edge("conversational", END)

    # Compile workflow with checkpointing
    if checkpoint_conn_string:
        checkpointer = PostgresSaver(checkpoint_conn_string)
        return workflow.compile(checkpointer=checkpointer)
    else:
        return workflow.compile()


# Cached graph instance for streaming
_compiled_graph = None


@traceable(name="get_graph", tags=["langgraph", "graph", "initialization"])
def get_graph():
    """Get the compiled LangGraph workflow (singleton).

    Returns cached graph instance WITHOUT checkpointing for streaming.

    Note:
        PostgresSaver doesn't support async aget_tuple needed for astream_events.
        For streaming endpoints, we use a graph without checkpointing.
        For regular execution with ainvoke, use the 'app' export which has checkpointing.
    """
    global _compiled_graph
    if _compiled_graph is None:
        logger.info(
            "[LangGraph] Initializing graph without checkpointing (for streaming)"
        )
        _compiled_graph = create_workflow()  # No checkpointing for streaming
    return _compiled_graph


# Export compiled workflow (with checkpointing if available)
import os

checkpoint_conn = os.getenv("POSTGRES_CHECKPOINT_URI")
app = create_workflow(checkpoint_conn) if checkpoint_conn else create_workflow()
