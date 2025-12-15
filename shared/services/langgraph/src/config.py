"""
Unified LangGraph Configuration
Single source of truth for all LLM, embedding, and infrastructure config across agents
"""

import logging
import os
from typing import Any, Dict, Optional

from shared.lib.langgraph_base import get_postgres_checkpointer
from shared.lib.llm_providers import (
    cicd_llm,
    code_review_llm,
    documentation_llm,
    feature_dev_llm,
    get_embeddings,
    get_llm,
    infrastructure_llm,
    orchestrator_llm,
    shared_embeddings,
)
from shared.lib.qdrant_client import get_qdrant_client

logger = logging.getLogger(__name__)

# Agent LLM configuration (pre-configured instances)
AGENT_LLMS = {
    "orchestrator": orchestrator_llm,
    "feature-dev": feature_dev_llm,
    "code-review": code_review_llm,
    "infrastructure": infrastructure_llm,
    "cicd": cicd_llm,
    "documentation": documentation_llm,
}

# Shared components
EMBEDDINGS = shared_embeddings
QDRANT_CLIENT = get_qdrant_client()
CHECKPOINTER = get_postgres_checkpointer()

# Model metadata (for logging/tracing)
MODEL_METADATA: Dict[str, Dict[str, Any]] = {
    "orchestrator": {
        "model": "llama-3.1-70b-instruct",
        "provider": "digitalocean-gradient",
        "use_case": "complex_reasoning",
        "cost_per_1m_tokens": 0.60,
        "context_window": 128000,
    },
    "feature-dev": {
        "model": "codellama-13b-instruct",
        "provider": "digitalocean-gradient",
        "use_case": "code_generation",
        "cost_per_1m_tokens": 0.30,
        "context_window": 16000,
    },
    "code-review": {
        "model": "llama-3.1-70b-instruct",
        "provider": "digitalocean-gradient",
        "use_case": "code_analysis",
        "cost_per_1m_tokens": 0.60,
        "context_window": 128000,
    },
    "infrastructure": {
        "model": "llama-3.1-8b-instruct",
        "provider": "digitalocean-gradient",
        "use_case": "infrastructure_config",
        "cost_per_1m_tokens": 0.20,
        "context_window": 128000,
    },
    "cicd": {
        "model": "llama-3.1-8b-instruct",
        "provider": "digitalocean-gradient",
        "use_case": "pipeline_generation",
        "cost_per_1m_tokens": 0.20,
        "context_window": 128000,
    },
    "documentation": {
        "model": "mistral-7b-instruct",
        "provider": "digitalocean-gradient",
        "use_case": "documentation_generation",
        "cost_per_1m_tokens": 0.20,
        "context_window": 8192,
    },
}


def get_agent_llm(agent_name: str):
    """
    Get configured LLM for specific agent

    Args:
        agent_name: Name of the agent (orchestrator, feature-dev, etc.)

    Returns:
        Configured ChatOpenAI instance or None if not found
    """
    llm = AGENT_LLMS.get(agent_name)
    if not llm:
        logger.warning(f"No LLM configured for agent: {agent_name}")
    return llm


def get_embeddings():
    """Get shared embeddings instance"""
    if not EMBEDDINGS:
        logger.warning("Gradient embeddings not available (missing API key)")
    return EMBEDDINGS


def get_qdrant():
    """Get Qdrant client instance"""
    if not QDRANT_CLIENT.is_enabled():
        logger.warning("Qdrant client not available (missing credentials)")
    return QDRANT_CLIENT


def get_checkpointer():
    """Get PostgreSQL checkpointer for workflow persistence"""
    return CHECKPOINTER


def get_model_metadata(agent_name: str) -> Optional[Dict[str, Any]]:
    """
    Get metadata about the model used by an agent

    Args:
        agent_name: Name of the agent

    Returns:
        Dict with model metadata or None if not found
    """
    return MODEL_METADATA.get(agent_name)


def is_fully_configured() -> Dict[str, bool]:
    """
    Check configuration status of all components

    Returns:
        Dict mapping component name to availability status
    """
    status = {
        "llms": all(llm is not None for llm in AGENT_LLMS.values()),
        "embeddings": EMBEDDINGS is not None,
        "qdrant": QDRANT_CLIENT.is_enabled(),
        "checkpointer": CHECKPOINTER is not None,
    }

    return status


# Log configuration status on import
_status = is_fully_configured()
logger.info(f"LangGraph configuration loaded:")
logger.info(f"  LLMs: {'✓' if _status['llms'] else '✗'}")
logger.info(f"  Embeddings: {'✓' if _status['embeddings'] else '✗'}")
logger.info(f"  Qdrant: {'✓' if _status['qdrant'] else '✗'}")
logger.info(f"  Checkpointer: {'✓' if _status['checkpointer'] else '✗'}")
