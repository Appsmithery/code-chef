"""
Unified LangChain Configuration for DigitalOcean Gradient AI

Manages both LLM inference and embeddings via standard LangChain abstractions.
Single source of truth for all model configurations across agents.
"""

import os
import logging
from typing import Optional, List
from langchain_openai import ChatOpenAI
from langchain_community.embeddings import OpenAIEmbeddings

logger = logging.getLogger(__name__)

# DigitalOcean Gradient AI configuration
GRADIENT_BASE_URL = os.getenv(
    "GRADIENT_BASE_URL", 
    "https://api.digitalocean.com/v2/ai/v1"
)
GRADIENT_API_KEY = os.getenv("GRADIENT_API_KEY") or os.getenv("GRADIENT_MODEL_ACCESS_KEY")

# Langfuse tracing (automatic when configured)
LANGFUSE_ENABLED = all([
    os.getenv("LANGFUSE_SECRET_KEY"),
    os.getenv("LANGFUSE_PUBLIC_KEY"),
    os.getenv("LANGFUSE_HOST")
])

_langfuse_handler = None
if LANGFUSE_ENABLED:
    try:
        from langfuse.callback import CallbackHandler
        _langfuse_handler = CallbackHandler(
            secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
            public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
            host=os.getenv("LANGFUSE_HOST")
        )
        logger.info("Langfuse callback handler initialized for unified config")
    except ImportError:
        logger.warning("Langfuse not installed, tracing disabled")
    except Exception as e:
        logger.error(f"Failed to initialize Langfuse handler: {e}")


def get_gradient_llm(
    agent_name: str,
    model: str = "llama-3.1-8b-instruct",
    temperature: float = 0.7,
    max_tokens: int = 2000,
    **kwargs
) -> ChatOpenAI:
    """
    Get LangChain LLM configured for DO Gradient AI
    
    Args:
        agent_name: Agent identifier for tracing
        model: Gradient model name
        temperature: Sampling temperature
        max_tokens: Max tokens to generate
        **kwargs: Additional ChatOpenAI parameters
        
    Returns:
        Configured ChatOpenAI instance
    """
    if not GRADIENT_API_KEY:
        logger.warning(f"[{agent_name}] GRADIENT_API_KEY not set, LLM calls will fail")
        # Return a dummy client that will error gracefully
        return None
    
    callbacks = []
    if _langfuse_handler:
        callbacks.append(_langfuse_handler)
    
    return ChatOpenAI(
        base_url=GRADIENT_BASE_URL,
        api_key=GRADIENT_API_KEY,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        callbacks=callbacks,
        tags=[agent_name, "gradient-ai"],
        model_kwargs=kwargs
    )


def get_gradient_embeddings(
    model: str = "text-embedding-3-small",
    chunk_size: int = 1000
) -> OpenAIEmbeddings:
    """
    Get LangChain embeddings configured for DO Gradient AI
    
    Args:
        model: Embedding model name
        chunk_size: Max tokens per embedding request
        
    Returns:
        Configured OpenAIEmbeddings instance
    """
    if not GRADIENT_API_KEY:
        logger.warning("GRADIENT_API_KEY not set, embeddings will fail")
        return None
    
    return OpenAIEmbeddings(
        base_url=GRADIENT_BASE_URL,
        api_key=GRADIENT_API_KEY,
        model=model,
        chunk_size=chunk_size
    )


# Pre-configured instances for each agent
orchestrator_llm = get_gradient_llm(
    agent_name="orchestrator",
    model="llama-3.1-70b-instruct"
)

feature_dev_llm = get_gradient_llm(
    agent_name="feature-dev",
    model="codellama-13b-instruct"
)

code_review_llm = get_gradient_llm(
    agent_name="code-review",
    model="llama-3.1-70b-instruct"
)

infrastructure_llm = get_gradient_llm(
    agent_name="infrastructure",
    model="llama-3.1-8b-instruct"
)

cicd_llm = get_gradient_llm(
    agent_name="cicd",
    model="llama-3.1-8b-instruct"
)

documentation_llm = get_gradient_llm(
    agent_name="documentation",
    model="mistral-7b-instruct"
)

# Shared embeddings instance
gradient_embeddings = get_gradient_embeddings("text-embedding-3-small")

logger.info("Unified LangChain configuration initialized")
logger.info(f"Gradient API: {GRADIENT_BASE_URL}")
logger.info(f"Langfuse tracing: {'ENABLED' if LANGFUSE_ENABLED else 'DISABLED'}")
