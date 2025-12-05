"""
LangSmith Evaluation Package for Code-Chef.

Provides custom evaluators for IB-Agent Platform scenarios and utilities
for running evaluations against traced LangGraph workflows.

Linear Issue: DEV-195
Test Project: https://github.com/Appsmithery/IB-Agent

Usage:
    from support.tests.evaluation import ALL_EVALUATORS, run_evaluation
    from support.tests.evaluation.evaluators import token_efficiency
"""

from support.tests.evaluation.evaluators import (
    # Individual evaluators
    agent_routing_accuracy,
    token_efficiency,
    latency_threshold,
    workflow_completeness,
    mcp_integration_quality,
    risk_assessment_accuracy,
    # Evaluator collections
    ALL_EVALUATORS,
    PHASE1_EVALUATORS,
    PHASE2_EVALUATORS,
    # Helper functions
    get_evaluators,
)

__all__ = [
    # Individual evaluators
    "agent_routing_accuracy",
    "token_efficiency",
    "latency_threshold",
    "workflow_completeness",
    "mcp_integration_quality",
    "risk_assessment_accuracy",
    # Evaluator collections
    "ALL_EVALUATORS",
    "PHASE1_EVALUATORS",
    "PHASE2_EVALUATORS",
    # Helper functions
    "get_evaluators",
]

__version__ = "0.1.0"
