"""
Unified LangChain Configuration for Multi-Provider LLM Support

Supports DigitalOcean Gradient AI (default), Claude, Mistral, OpenAI with easy provider switching.
Single source of truth for all model configurations across agents.
"""

import os
import logging
from typing import Optional, Literal, Union
from langchain_openai import ChatOpenAI, OpenAIEmbeddings

logger = logging.getLogger(__name__)

# Provider selection (defaults to Gradient AI)
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "gradient").lower()
EMBEDDING_PROVIDER = os.getenv("EMBEDDING_PROVIDER", "gradient").lower()

# DigitalOcean Gradient AI (OpenAI-compatible)
GRADIENT_BASE_URL = os.getenv("GRADIENT_BASE_URL", "https://api.digitalocean.com/v2/ai/v1")
GRADIENT_API_KEY = os.getenv("GRADIENT_API_KEY") or os.getenv("GRADIENT_MODEL_ACCESS_KEY")

# Claude (Anthropic)
CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY")

# Mistral
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")

# OpenAI (direct)
OPENAI_API_KEY = os.getenv("OPEN_AI_DEVTOOLS_KEY")

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
        logger.info("Langfuse callback handler initialized")
    except ImportError:
        logger.warning("Langfuse not installed, tracing disabled")
    except Exception as e:
        logger.error(f"Failed to initialize Langfuse handler: {e}")


def get_llm(
    agent_name: str,
    model: Optional[str] = None,
    temperature: float = 0.7,
    max_tokens: int = 2000,
    provider: Optional[Literal["gradient", "claude", "mistral", "openai"]] = None,
    **kwargs
) -> Union[ChatOpenAI, 'ChatAnthropic', 'ChatMistralAI']:
    """
    Get LangChain LLM for specified provider

    Args:
        agent_name: Agent identifier for tracing
        model: Model name (provider-specific)
        temperature: Sampling temperature
        max_tokens: Max tokens to generate
        provider: Override LLM_PROVIDER env var
        **kwargs: Additional provider-specific parameters

    Returns:
        Configured LLM instance

    Examples:
        # Use default (Gradient AI)
        llm = get_llm("orchestrator", model="llama-3.1-70b-instruct")
        
        # Override to Claude
        llm = get_llm("code-review", model="claude-3-5-sonnet-20241022", provider="claude")
        
        # Override to Mistral
        llm = get_llm("feature-dev", model="mistral-large-latest", provider="mistral")
    """
    provider = provider or LLM_PROVIDER
    callbacks = [_langfuse_handler] if _langfuse_handler else []
    tags = [agent_name, provider]

    if provider == "gradient":
        if not GRADIENT_API_KEY:
            logger.warning(f"[{agent_name}] GRADIENT_API_KEY not set, LLM calls will fail")
            return None
        
        return ChatOpenAI(
            base_url=GRADIENT_BASE_URL,
            api_key=GRADIENT_API_KEY,
            model=model or "llama-3.1-8b-instruct",
            temperature=temperature,
            max_tokens=max_tokens,
            callbacks=callbacks,
            tags=tags,
            model_kwargs=kwargs
        )

    elif provider == "claude":
        if not CLAUDE_API_KEY:
            logger.warning(f"[{agent_name}] CLAUDE_API_KEY not set, LLM calls will fail")
            return None
        
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(
            api_key=CLAUDE_API_KEY,
            model=model or "claude-3-5-sonnet-20241022",
            temperature=temperature,
            max_tokens=max_tokens,
            callbacks=callbacks,
            tags=tags,
            **kwargs
        )

    elif provider == "mistral":
        if not MISTRAL_API_KEY:
            logger.warning(f"[{agent_name}] MISTRAL_API_KEY not set, LLM calls will fail")
            return None
        
        from langchain_mistralai import ChatMistralAI
        return ChatMistralAI(
            api_key=MISTRAL_API_KEY,
            model=model or "mistral-large-latest",
            temperature=temperature,
            max_tokens=max_tokens,
            callbacks=callbacks,
            tags=tags,
            **kwargs
        )

    elif provider == "openai":
        if not OPENAI_API_KEY:
            logger.warning(f"[{agent_name}] OPENAI_API_KEY not set, LLM calls will fail")
            return None
        
        return ChatOpenAI(
            api_key=OPENAI_API_KEY,
            model=model or "gpt-4o-mini",
            temperature=temperature,
            max_tokens=max_tokens,
            callbacks=callbacks,
            tags=tags,
            model_kwargs=kwargs
        )

    else:
        raise ValueError(f"Unknown LLM provider: {provider}")


def get_embeddings(
    model: Optional[str] = None,
    chunk_size: int = 1000,
    provider: Optional[Literal["gradient", "openai"]] = None
) -> OpenAIEmbeddings:
    """
    Get LangChain embeddings for specified provider

    Args:
        model: Embedding model name
        chunk_size: Max tokens per embedding request
        provider: Override EMBEDDING_PROVIDER env var

    Returns:
        Configured OpenAIEmbeddings instance

    Note:
        Both Gradient AI and OpenAI use OpenAIEmbeddings (compatible API)
        Claude and Mistral don't offer embedding endpoints via LangChain
    """
    provider = provider or EMBEDDING_PROVIDER

    if provider == "gradient":
        if not GRADIENT_API_KEY:
            logger.warning("GRADIENT_API_KEY not set, embeddings will fail")
            return None
        
        return OpenAIEmbeddings(
            base_url=GRADIENT_BASE_URL,
            api_key=GRADIENT_API_KEY,
            model=model or "text-embedding-3-small",
            chunk_size=chunk_size
        )

    elif provider == "openai":
        if not OPENAI_API_KEY:
            logger.warning("OPENAI_API_KEY not set, embeddings will fail")
            return None
        
        return OpenAIEmbeddings(
            api_key=OPENAI_API_KEY,
            model=model or "text-embedding-3-small",
            chunk_size=chunk_size
        )

    else:
        raise ValueError(f"Unknown embedding provider: {provider}. Supported: gradient, openai")


# Backward compatibility aliases
def get_gradient_llm(agent_name: str, model: str = "llama-3.1-8b-instruct", **kwargs) -> ChatOpenAI:
    """Backward compatibility wrapper for get_llm() with gradient provider"""
    return get_llm(agent_name, model=model, provider="gradient", **kwargs)

def get_gradient_embeddings(model: str = "text-embedding-3-small", chunk_size: int = 1000) -> OpenAIEmbeddings:
    """Backward compatibility wrapper for get_embeddings() with gradient provider"""
    return get_embeddings(model=model, chunk_size=chunk_size, provider="gradient")


# Pre-configured instances using environment-selected provider
orchestrator_llm = get_llm("orchestrator", model="llama-3.1-70b-instruct")
feature_dev_llm = get_llm("feature-dev", model="codellama-13b-instruct")
code_review_llm = get_llm("code-review", model="llama-3.1-70b-instruct")
infrastructure_llm = get_llm("infrastructure", model="llama-3.1-8b-instruct")
cicd_llm = get_llm("cicd", model="llama-3.1-8b-instruct")
documentation_llm = get_llm("documentation", model="mistral-7b-instruct")

# Shared embeddings instance
gradient_embeddings = get_embeddings()

logger.info("Unified LangChain configuration initialized")
logger.info(f"LLM Provider: {LLM_PROVIDER}")
logger.info(f"Embedding Provider: {EMBEDDING_PROVIDER}")
logger.info(f"Langfuse tracing: {'ENABLED' if LANGFUSE_ENABLED else 'DISABLED'}")
