"""
Custom LangSmith evaluators for code-chef agent quality metrics.

Evaluates traces against IB-Agent Platform development scenarios:
- Agent routing accuracy
- Token efficiency by task complexity
- Latency thresholds
- Workflow completeness
- MCP integration quality

Usage:
    from support.tests.evaluation.evaluators import (
        agent_routing_accuracy,
        token_efficiency,
        latency_threshold,
        workflow_completeness,
        mcp_integration_quality,
    )

Linear Issue: DEV-195
Test Project: https://github.com/Appsmithery/IB-Agent
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Set

# Type checking imports (no runtime impact)
if TYPE_CHECKING:
    from langsmith.evaluation import EvaluationResult as EvalResult
    from langsmith.schemas import Example as ExampleType
    from langsmith.schemas import Run as RunType

    Run = RunType
    Example = ExampleType
    EvaluationResult = EvalResult

# Lazy import to avoid errors when langsmith not installed
try:
    from langsmith.evaluation import EvaluationResult
    from langsmith.schemas import Example, Run

    LANGSMITH_AVAILABLE = True
except ImportError:
    LANGSMITH_AVAILABLE = False

    # Define stub classes for runtime
    @dataclass
    class EvaluationResult:  # type: ignore[no-redef]
        key: str
        score: float
        comment: str = ""

    class Run:  # type: ignore[no-redef]
        """Stub Run class when langsmith not installed."""

        pass

    class Example:  # type: ignore[no-redef]
        """Stub Example class when langsmith not installed."""

        pass


logger = logging.getLogger(__name__)


# =============================================================================
# TOKEN THRESHOLDS BY TASK COMPLEXITY
# Based on IB-Agent Platform task types
# =============================================================================

TOKEN_THRESHOLDS = {
    # Complex agent workflows (LangGraph, multi-step)
    "complex": {
        "keywords": ["langgraph", "compsagent", "rag", "workflow", "stategraph"],
        "threshold": 6000,
    },
    # Security and code review (needs full context)
    "security": {
        "keywords": ["security", "owasp", "code_review", "vulnerability", "audit"],
        "threshold": 4000,
    },
    # ModelOps training and evaluation workflows
    "modelops": {
        "keywords": [
            "modelops",
            "training",
            "evaluation",
            "deployment",
            "model_registry",
            "huggingface",
            "autotrain",
        ],
        "threshold": 4500,
    },
    # UI and frontend tasks
    "ui": {
        "keywords": ["excel", "manifest", "office.js", "chainlit", "react", "ui"],
        "threshold": 3000,
    },
    # Infrastructure tasks
    "infrastructure": {
        "keywords": ["docker", "compose", "qdrant", "terraform", "kubernetes"],
        "threshold": 2500,
    },
    # Default for simple tasks
    "default": {"keywords": [], "threshold": 2000},
}


# =============================================================================
# IB-AGENT PHASE WORKFLOW STEPS
# Expected steps for each implementation phase
# =============================================================================

PHASE_WORKFLOW_STEPS = {
    "1.": {  # Phase 1: Data Layer
        "expected": ["infrastructure_check", "docker_validate", "mcp_health"],
        "description": "Data Layer Foundation",
    },
    "2.": {  # Phase 2: Core Agents
        "expected": ["feature_dev_node", "code_review_node", "test_generate"],
        "description": "Core Agent Development",
    },
    "3.": {  # Phase 3: UI Integration
        "expected": ["feature_dev_node", "ui_validate"],
        "description": "UI Integration",
    },
    "4.": {  # Phase 4: Excel Add-in (high risk)
        "expected": ["feature_dev_node", "code_review_node", "security_scan"],
        "description": "Excel Add-in",
    },
}


def agent_routing_accuracy(run: Run, example: Example) -> EvaluationResult:
    """
    Evaluate if the correct agent was routed to.

    Compares actual agent execution to expected agents from the dataset.
    Score = overlap / expected_agents count.

    Args:
        run: LangSmith run containing trace data
        example: Dataset example with expected_agents in outputs

    Returns:
        EvaluationResult with score 0.0-1.0
    """
    expected_agents = set(example.outputs.get("expected_agents", []))

    if not expected_agents:
        return EvaluationResult(
            key="agent_routing_accuracy",
            score=1.0,
            comment="No expected agents defined",
        )

    actual_agents = _extract_agents_from_run(run)

    # Calculate overlap
    overlap = expected_agents & actual_agents
    score = len(overlap) / len(expected_agents)

    return EvaluationResult(
        key="agent_routing_accuracy",
        score=score,
        comment=f"Expected: {sorted(expected_agents)}, Actual: {sorted(actual_agents)}, Overlap: {sorted(overlap)}",
    )


def token_efficiency(run: Run, example: Example) -> EvaluationResult:
    """
    Evaluate token usage efficiency for IB-Agent tasks.

    Dynamically determines threshold based on task complexity:
    - Complex (LangGraph, RAG): 6000 tokens
    - Security review: 4000 tokens
    - UI/Excel: 3000 tokens
    - Infrastructure: 2500 tokens
    - Default: 2000 tokens

    Args:
        run: LangSmith run with token usage data
        example: Dataset example with task input

    Returns:
        EvaluationResult with score based on threshold ratio
    """
    total_tokens = run.total_tokens or 0

    if total_tokens == 0:
        return EvaluationResult(
            key="token_efficiency", score=1.0, comment="No token data available"
        )

    # Determine threshold based on task
    task = str(example.inputs.get("task", "")).lower()
    threshold = _get_token_threshold(task)

    # Score: 1.0 if under threshold, decreasing ratio if over
    if total_tokens <= threshold:
        score = 1.0
    else:
        # Gradual decrease: 50% over = 0.67, 100% over = 0.5
        score = threshold / total_tokens

    return EvaluationResult(
        key="token_efficiency",
        score=score,
        comment=f"Used {total_tokens:,} tokens (threshold: {threshold:,}, efficiency: {score:.1%})",
    )


def latency_threshold(run: Run, example: Example) -> EvaluationResult:
    """
    Evaluate response latency against P95 target.

    Default target: 5 seconds
    Complex tasks (LangGraph, security): 10 seconds

    Args:
        run: LangSmith run with timing data
        example: Dataset example

    Returns:
        EvaluationResult with latency score
    """
    if not run.end_time or not run.start_time:
        return EvaluationResult(
            key="latency_threshold", score=0.0, comment="Missing timestamps"
        )

    latency = (run.end_time - run.start_time).total_seconds()

    # Determine threshold based on task complexity
    task = str(example.inputs.get("task", "")).lower()
    if any(kw in task for kw in ["langgraph", "compsagent", "security", "audit"]):
        threshold = 10.0
    else:
        threshold = 5.0

    # Score: 1.0 if under threshold
    if latency <= threshold:
        score = 1.0
    else:
        # Gradual decrease
        score = max(0.0, threshold / latency)

    return EvaluationResult(
        key="latency_threshold",
        score=score,
        comment=f"Latency: {latency:.2f}s (threshold: {threshold}s)",
    )


def workflow_completeness(run: Run, example: Example) -> EvaluationResult:
    """
    Evaluate if IB-Agent workflow completed all expected steps.

    Uses phase-specific step definitions from PHASE_WORKFLOW_STEPS.
    Falls back to example.outputs["expected_steps"] if available.

    Args:
        run: LangSmith run with child runs
        example: Dataset example with ib_agent_step

    Returns:
        EvaluationResult with completion rate score
    """
    # Get expected steps from example or phase definition
    expected_steps = example.outputs.get("expected_steps", [])
    ib_agent_step = example.outputs.get("ib_agent_step", "")

    if not expected_steps and ib_agent_step:
        # Lookup phase-specific steps
        for phase_prefix, phase_info in PHASE_WORKFLOW_STEPS.items():
            if ib_agent_step.startswith(phase_prefix):
                expected_steps = phase_info["expected"]
                break

    if not expected_steps:
        return EvaluationResult(
            key="workflow_completeness", score=1.0, comment="No expected steps defined"
        )

    # Extract completed steps from child runs
    completed_steps = []
    if hasattr(run, "child_runs") and run.child_runs:
        for child in run.child_runs:
            if hasattr(child, "status") and child.status == "success":
                completed_steps.append(child.name)
    elif hasattr(run, "child_run_ids") and run.child_run_ids:
        # If only IDs available, count them as steps
        completed_steps = [f"step_{i}" for i in range(len(run.child_run_ids))]

    # Calculate completion rate
    expected_set = set(expected_steps)
    completed_set = set(completed_steps)
    matched = expected_set & completed_set

    completion_rate = len(matched) / len(expected_set) if expected_set else 1.0

    return EvaluationResult(
        key="workflow_completeness",
        score=completion_rate,
        comment=f"Completed {len(matched)}/{len(expected_set)} steps (IB-Agent step {ib_agent_step})",
    )


def mcp_integration_quality(run: Run, example: Example) -> EvaluationResult:
    """
    Evaluate MCP server integration quality.

    Checks for:
    - Proper error handling (25%)
    - Citation metadata in responses (25%)
    - Successful completion (50%)

    Args:
        run: LangSmith run with MCP tool calls
        example: Dataset example

    Returns:
        EvaluationResult for MCP integration quality
    """
    task = str(example.inputs.get("task", "")).lower()
    mcp_keywords = ["edgar", "fred", "nasdaq", "mcp", "sec", "filing"]

    # Skip for non-MCP tasks
    if not any(kw in task for kw in mcp_keywords):
        return EvaluationResult(
            key="mcp_integration_quality", score=1.0, comment="Non-MCP task (skipped)"
        )

    # Analyze MCP integration
    has_citations = False
    has_error_handling = False
    mcp_success = run.status == "success"

    # Check child runs for MCP tool calls
    if hasattr(run, "child_runs") and run.child_runs:
        for child in run.child_runs:
            child_name = getattr(child, "name", "") or ""
            if any(kw in child_name.lower() for kw in mcp_keywords):
                # Check for citations
                outputs = getattr(child, "outputs", {}) or {}
                if "citations" in str(outputs):
                    has_citations = True

                # Check for error handling
                if child.error or "error" in str(outputs).lower():
                    has_error_handling = True

    # Calculate score
    score = 0.5 if mcp_success else 0.0
    if has_citations:
        score += 0.25
    if has_error_handling or mcp_success:
        score += 0.25

    return EvaluationResult(
        key="mcp_integration_quality",
        score=score,
        comment=f"Success: {mcp_success}, Citations: {has_citations}, Error handling: {has_error_handling}",
    )


def risk_assessment_accuracy(run: Run, example: Example) -> EvaluationResult:
    """
    Evaluate if risk level was correctly assessed.

    High-risk tasks should trigger additional review steps.

    Args:
        run: LangSmith run
        example: Dataset example with risk_level

    Returns:
        EvaluationResult for risk assessment
    """
    expected_risk = example.outputs.get("risk_level", "low")

    # Extract assessed risk from run metadata or outputs
    assessed_risk = "low"
    if hasattr(run, "extra") and run.extra:
        metadata = run.extra.get("metadata", {})
        assessed_risk = metadata.get("risk_level", "low")

    # High-risk tasks should show additional review steps
    high_risk_indicators = []
    if hasattr(run, "child_runs") and run.child_runs:
        for child in run.child_runs:
            name = getattr(child, "name", "") or ""
            if any(kw in name.lower() for kw in ["security", "review", "approval"]):
                high_risk_indicators.append(name)

    # Score based on correct risk handling
    if expected_risk == "high":
        # High-risk should have review steps
        score = 1.0 if high_risk_indicators else 0.5
    elif expected_risk == "low":
        # Low-risk should complete without excessive review
        score = 1.0
    else:  # medium
        score = 0.8

    return EvaluationResult(
        key="risk_assessment_accuracy",
        score=score,
        comment=f"Expected: {expected_risk}, Review steps: {high_risk_indicators}",
    )


def modelops_training_quality(run: Run, example: Example) -> EvaluationResult:
    """
    Evaluate ModelOps training workflow quality.

    Checks for proper training configuration, cost estimation,
    progress tracking, and result handling.

    Args:
        run: LangSmith run
        example: Dataset example

    Returns:
        EvaluationResult for training quality
    """
    score = 0.0
    checks = []

    # Check for training configuration
    has_config = False
    has_cost_estimate = False
    has_job_id = False
    has_status_tracking = False

    if hasattr(run, "outputs") and run.outputs:
        outputs = run.outputs

        # Look for training configuration
        if any(
            key in str(outputs).lower()
            for key in ["training", "config", "lora", "samples"]
        ):
            has_config = True
            checks.append("Training config")
            score += 0.25

        # Look for cost estimation
        if any(
            key in str(outputs).lower() for key in ["cost", "price", "$", "estimate"]
        ):
            has_cost_estimate = True
            checks.append("Cost estimate")
            score += 0.25

        # Look for job tracking
        if any(
            key in str(outputs).lower() for key in ["job_id", "trackio", "training_id"]
        ):
            has_job_id = True
            checks.append("Job tracking")
            score += 0.25

        # Look for status tracking
        if any(
            key in str(outputs).lower()
            for key in ["status", "progress", "completed", "running"]
        ):
            has_status_tracking = True
            checks.append("Status tracking")
            score += 0.25

    return EvaluationResult(
        key="modelops_training_quality",
        score=score,
        comment=f"Checks passed: {', '.join(checks)}",
    )


def modelops_deployment_success(run: Run, example: Example) -> EvaluationResult:
    """
    Evaluate ModelOps deployment workflow success.

    Checks for proper model deployment, config updates,
    version tracking, and rollback capability.

    Args:
        run: LangSmith run
        example: Dataset example

    Returns:
        EvaluationResult for deployment success
    """
    score = 0.0
    checks = []

    # Check for deployment indicators
    has_version = False
    has_config_update = False
    has_rollback_info = False
    has_registry_update = False

    if hasattr(run, "outputs") and run.outputs:
        outputs = run.outputs

        # Look for version tracking
        if any(
            key in str(outputs).lower() for key in ["version", "v1.", "v2.", "deployed"]
        ):
            has_version = True
            checks.append("Version tracking")
            score += 0.25

        # Look for config updates
        if any(
            key in str(outputs).lower() for key in ["config", "models.yaml", "updated"]
        ):
            has_config_update = True
            checks.append("Config update")
            score += 0.25

        # Look for rollback capability
        if any(
            key in str(outputs).lower() for key in ["rollback", "backup", "previous"]
        ):
            has_rollback_info = True
            checks.append("Rollback ready")
            score += 0.25

        # Look for registry updates
        if any(
            key in str(outputs).lower()
            for key in ["registry", "model_id", "deployed_at"]
        ):
            has_registry_update = True
            checks.append("Registry update")
            score += 0.25

    return EvaluationResult(
        key="modelops_deployment_success",
        score=score,
        comment=f"Checks passed: {', '.join(checks)}",
    )


def streaming_response_quality(run: Run, example: Example) -> EvaluationResult:
    """
    Evaluate streaming response quality and SSE compliance.

    Checks for:
    - Streaming events present in trace (40%)
    - Proper SSE format (data: prefix, newlines) (30%)
    - Chunk timing efficiency (<500ms between chunks) (20%)
    - Error handling for stream interruptions (10%)

    Args:
        run: LangSmith run with streaming events
        example: Dataset example

    Returns:
        EvaluationResult for streaming quality
    """
    score = 0.0
    checks = []

    # Check if task involves streaming
    task = str(example.inputs.get("task", "")).lower()
    streaming_keywords = ["stream", "sse", "real-time", "progress", "websocket"]

    # Skip for non-streaming tasks
    if not any(kw in task for kw in streaming_keywords):
        return EvaluationResult(
            key="streaming_response_quality",
            score=1.0,
            comment="Non-streaming task (skipped)",
        )

    has_streaming_events = False
    has_sse_format = False
    has_efficient_timing = True
    has_error_handling = False

    # Analyze streaming events
    if hasattr(run, "outputs") and run.outputs:
        outputs_str = str(run.outputs).lower()

        # Check for streaming events
        if any(kw in outputs_str for kw in ["stream", "chunk", "delta", "event:"]):
            has_streaming_events = True
            checks.append("Streaming events")
            score += 0.4

            # Check SSE format compliance
            if "data:" in outputs_str and (
                "\\n\\n" in outputs_str or "\n\n" in outputs_str
            ):
                has_sse_format = True
                checks.append("SSE format")
                score += 0.3

        # Check for error handling
        if any(kw in outputs_str for kw in ["error", "retry", "fallback", "timeout"]):
            has_error_handling = True
            checks.append("Error handling")
            score += 0.1

    # Check chunk timing from child runs
    if hasattr(run, "child_runs") and run.child_runs:
        chunk_times = []
        for child in run.child_runs:
            if hasattr(child, "start_time") and hasattr(child, "end_time"):
                if child.start_time and child.end_time:
                    duration = (child.end_time - child.start_time).total_seconds()
                    if "stream" in getattr(child, "name", "").lower():
                        chunk_times.append(duration)

        if chunk_times:
            avg_chunk_time = sum(chunk_times) / len(chunk_times)
            if avg_chunk_time < 0.5:  # 500ms threshold
                has_efficient_timing = True
                checks.append("Efficient timing")
                score += 0.2

    # If no streaming detected but task requires it, score 0
    if not has_streaming_events:
        return EvaluationResult(
            key="streaming_response_quality",
            score=0.0,
            comment="Streaming required but not implemented",
        )

    return EvaluationResult(
        key="streaming_response_quality",
        score=score,
        comment=f"Checks passed: {', '.join(checks)}",
    )


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================


def _extract_agents_from_run(run: Run) -> Set[str]:
    """Extract agent names from run metadata and child runs."""
    agents = set()

    # From metadata
    if hasattr(run, "extra") and run.extra:
        metadata = run.extra.get("metadata", {})
        if "agent" in metadata:
            agents.add(metadata["agent"])

    # From run name
    if hasattr(run, "name") and run.name:
        for agent_name in [
            "feature_dev",
            "code_review",
            "infrastructure",
            "cicd",
            "documentation",
            "supervisor",
        ]:
            if agent_name in run.name.lower():
                agents.add(agent_name)

    # From child runs
    if hasattr(run, "child_runs") and run.child_runs:
        for child in run.child_runs:
            child_name = getattr(child, "name", "") or ""
            if "_node" in child_name:
                agent = child_name.replace("_node", "")
                agents.add(agent)

    return agents


def _get_token_threshold(task: str) -> int:
    """Determine token threshold based on task keywords."""
    task_lower = task.lower()

    for category, config in TOKEN_THRESHOLDS.items():
        if category == "default":
            continue
        if any(kw in task_lower for kw in config["keywords"]):
            return config["threshold"]

    return TOKEN_THRESHOLDS["default"]["threshold"]


# =============================================================================
# EVALUATOR COLLECTION
# =============================================================================

# List of all evaluators for use with LangSmith evaluate()
ALL_EVALUATORS = [
    agent_routing_accuracy,
    token_efficiency,
    latency_threshold,
    workflow_completeness,
    mcp_integration_quality,
    risk_assessment_accuracy,
    modelops_training_quality,
    modelops_deployment_success,
    streaming_response_quality,
]

# Phase 1: Data Layer Foundation evaluators (MCP, Docker, infrastructure)
PHASE1_EVALUATORS = [
    mcp_integration_quality,
    latency_threshold,
    workflow_completeness,
]

# Phase 2: Core Agent Development evaluators (LangGraph, RAG, routing)
PHASE2_EVALUATORS = [
    agent_routing_accuracy,
    token_efficiency,
    latency_threshold,
    workflow_completeness,
    streaming_response_quality,
]

# ModelOps: Training and deployment evaluators
MODELOPS_EVALUATORS = [
    modelops_training_quality,
    modelops_deployment_success,
    latency_threshold,
    workflow_completeness,
]

# Quick access mapping
EVALUATOR_MAP = {
    "agent_routing_accuracy": agent_routing_accuracy,
    "token_efficiency": token_efficiency,
    "latency_threshold": latency_threshold,
    "workflow_completeness": workflow_completeness,
    "mcp_integration_quality": mcp_integration_quality,
    "risk_assessment_accuracy": risk_assessment_accuracy,
    "modelops_training_quality": modelops_training_quality,
    "modelops_deployment_success": modelops_deployment_success,
    "streaming_response_quality": streaming_response_quality,
}


def get_evaluators(names: Optional[List[str]] = None) -> List:
    """
    Get evaluator functions by name.

    Args:
        names: List of evaluator names, or None for all

    Returns:
        List of evaluator functions
    """
    if names is None:
        return ALL_EVALUATORS

    return [EVALUATOR_MAP[name] for name in names if name in EVALUATOR_MAP]
