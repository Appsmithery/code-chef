"""
Unified LangGraph Configuration
Single source of truth for all LLM, embedding, and infrastructure config across agents
"""

import os
from typing import Dict, Any, Optional
import logging

from shared.lib.langchain_gradient import (
    orchestrator_llm,
    feature_dev_llm,
    code_review_llm,
    infrastructure_llm,
    cicd_llm,
    documentation_llm,
    shared_embeddings,
    get_gradient_llm,
    get_embeddings,
)
from shared.lib.qdrant_client import get_qdrant_client
from shared.lib.langgraph_base import get_postgres_checkpointer

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

# Model metadata loaded from YAML config (single source of truth)
# Lazy-loaded on first access to avoid circular imports
_CONFIG_LOADER = None


def _get_config_loader():
    """Lazy-load ConfigLoader to avoid circular imports."""
    global _CONFIG_LOADER
    if _CONFIG_LOADER is None:
        try:
            from lib.config_loader import get_config_loader

            _CONFIG_LOADER = get_config_loader()
            logger.info("Loaded agent configs from config/agents/models.yaml")
        except Exception as e:
            logger.warning(f"Failed to load ConfigLoader: {e}")
            _CONFIG_LOADER = None
    return _CONFIG_LOADER


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
    Get metadata about the model used by an agent (loaded from YAML config)

    Args:
        agent_name: Name of the agent

    Returns:
        Dict with model metadata or None if not found
    """
    config_loader = _get_config_loader()
    if config_loader is None:
        logger.warning("ConfigLoader unavailable, returning None for model metadata")
        return None

    try:
        agent_config = config_loader.get_agent_config(agent_name)
        return {
            "model": agent_config.model,
            "provider": agent_config.provider,
            "use_case": agent_config.use_case,
            "cost_per_1m_tokens": agent_config.cost_per_1m_tokens,
            "context_window": agent_config.context_window,
            "temperature": agent_config.temperature,
            "max_tokens": agent_config.max_tokens,
            "tags": agent_config.tags,
        }
    except KeyError:
        logger.warning(f"No config found for agent: {agent_name}")
        return None


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
