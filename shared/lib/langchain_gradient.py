"""
Unified LangChain Configuration for Multi-Provider LLM Support

Supports DigitalOcean Gradient AI (default), Claude, Mistral, OpenAI with easy provider switching.
Single source of truth for all model configurations across agents.

DigitalOcean Gradient AI Products:
1. Serverless Inference (OpenAI-compatible chat completions)
   - Endpoint: https://api.digitalocean.com/v2/ai
   - Auth: Bearer token from Model Provider Keys (sk-do-...)
   - Models: llama3-8b-instruct, llama3-70b-instruct, etc.

2. Gradient AI Platform (Agentic Cloud)
   - Endpoint: https://api.digitalocean.com/
   - Auth: Personal Access Token (dop_v1_...)
   - Features: Agent workspaces, knowledge bases, guardrails
"""

import logging
import os
from typing import Literal, Optional, Union

from langchain_openai import ChatOpenAI, OpenAIEmbeddings

logger = logging.getLogger(__name__)

# Provider selection (defaults to Gradient AI)
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "gradient").lower()
EMBEDDING_PROVIDER = os.getenv("EMBEDDING_PROVIDER", "gradient").lower()

# DigitalOcean Gradient AI - Serverless Inference (OpenAI-compatible)
# Documentation: https://docs.digitalocean.com/products/gradient-ai-platform/how-to/use-serverless-inference/
GRADIENT_BASE_URL = os.getenv("GRADIENT_BASE_URL", "https://inference.do-ai.run/v1")
GRADIENT_API_KEY = os.getenv("GRADIENT_MODEL_ACCESS_KEY") or os.getenv(
    "DO_SERVERLESS_INFERENCE_KEY"
)

# DigitalOcean Gradient AI Platform (Agentic Cloud API)
# Documentation: https://docs.digitalocean.com/reference/api/digitalocean/#tag/GradientAI-Platform
GRADIENT_GENAI_BASE_URL = os.getenv(
    "GRADIENT_GENAI_BASE_URL", "https://api.digitalocean.com"
)
GRADIENT_GENAI_API_KEY = os.getenv("GRADIENT_API_KEY") or os.getenv("DIGITAL_OCEAN_PAT")

# Claude (Anthropic)
CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY")

# Mistral
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")

# OpenAI (direct)
OPENAI_API_KEY = os.getenv("OPEN_AI_DEVTOOLS_KEY")

# OpenRouter (Multi-Model Gateway)
# Documentation: https://openrouter.ai/docs
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
OPENROUTER_DEFAULT_MODEL = os.getenv(
    "OPENROUTER_DEFAULT_MODEL", "anthropic/claude-3-5-sonnet"
)

# LangSmith tracing is automatic when LANGCHAIN_TRACING_V2=true
# No callback handlers needed - tracing works natively with LangChain
LANGSMITH_ENABLED = os.getenv("LANGCHAIN_TRACING_V2", "false").lower() == "true"
if LANGSMITH_ENABLED:
    logger.info(
        f"LangSmith tracing ENABLED (project: {os.getenv('LANGCHAIN_PROJECT', 'default')})"
    )
else:
    logger.info("LangSmith tracing DISABLED (set LANGCHAIN_TRACING_V2=true to enable)")


def get_llm(
    agent_name: str,
    model: Optional[str] = None,
    temperature: float = 0.7,
    max_tokens: int = 2000,
    provider: Optional[
        Literal["gradient", "claude", "mistral", "openai", "openrouter"]
    ] = None,
    **kwargs,
) -> Union[ChatOpenAI, "ChatAnthropic", "ChatMistralAI"]:
    """
    Get LangChain LLM for specified provider

    Args:
        agent_name: Agent identifier for tracing
        model: Model name (provider-specific)
        temperature: Sampling temperature
        max_tokens: Max tokens to generate (min 256 for Gradient AI)
        provider: Override LLM_PROVIDER env var
        **kwargs: Additional provider-specific parameters

    Returns:
        Configured LLM instance

    DigitalOcean Gradient AI Models (Serverless Inference):
        - llama3-8b-instruct (default, fast, cheap)
        - llama3.3-70b-instruct (best reasoning)
        - mistral-nemo-instruct-2407
        - See full list: https://inference.do-ai.run/v1/models

    OpenRouter Models (Multi-Model Gateway):
        - anthropic/claude-3-5-sonnet (recommended for code)
        - openai/gpt-4o (good all-rounder)
        - meta-llama/llama-3.1-70b-instruct (cost-effective)
        - google/gemini-2.0-flash-exp:free (free tier)
        - See full list: https://openrouter.ai/models

    Examples:
        # Use default (Gradient AI Serverless Inference)
        llm = get_llm("orchestrator", model="llama3.3-70b-instruct")

        # Override to Claude
        llm = get_llm("code-review", model="claude-3-5-sonnet-20241022", provider="claude")

        # Override to Mistral
        llm = get_llm("feature-dev", model="mistral-large-latest", provider="mistral")

        # Override to OpenRouter (access 200+ models)
        llm = get_llm("orchestrator", model="anthropic/claude-3-5-sonnet", provider="openrouter")
    """
    provider = provider or LLM_PROVIDER
    # LangSmith tracing is automatic - no callbacks needed
    tags = [agent_name, provider]

    if provider == "gradient":
        if not GRADIENT_API_KEY:
            logger.warning(
                f"[{agent_name}] GRADIENT_API_KEY/DO_SERVERLESS_INFERENCE_KEY not set, LLM calls will fail"
            )
            logger.warning(
                f"[{agent_name}] Get key at: https://cloud.digitalocean.com/gradient-ai/model-provider-keys"
            )
            return None

        # Use DigitalOcean Serverless Inference (OpenAI-compatible)
        # Note: max_tokens must be >= 256
        effective_max_tokens = max(max_tokens, 256)
        return ChatOpenAI(
            base_url=GRADIENT_BASE_URL,
            api_key=GRADIENT_API_KEY,
            model=model or "llama3-8b-instruct",
            temperature=temperature,
            max_tokens=effective_max_tokens,
            tags=tags,
            model_kwargs=kwargs,
        )

    elif provider == "claude":
        if not CLAUDE_API_KEY:
            logger.warning(
                f"[{agent_name}] CLAUDE_API_KEY not set, LLM calls will fail"
            )
            return None

        from langchain_anthropic import ChatAnthropic

        return ChatAnthropic(
            api_key=CLAUDE_API_KEY,
            model=model or "claude-3-5-haiku-20241022",
            temperature=temperature,
            max_tokens=max_tokens,
            tags=tags,
            **kwargs,
        )

    elif provider == "mistral":
        if not MISTRAL_API_KEY:
            logger.warning(
                f"[{agent_name}] MISTRAL_API_KEY not set, LLM calls will fail"
            )
            return None

        from langchain_mistralai import ChatMistralAI

        return ChatMistralAI(
            api_key=MISTRAL_API_KEY,
            model=model or "mistral-large-latest",
            temperature=temperature,
            max_tokens=max_tokens,
            tags=tags,
            **kwargs,
        )

    elif provider == "openai":
        if not OPENAI_API_KEY:
            logger.warning(
                f"[{agent_name}] OPENAI_API_KEY not set, LLM calls will fail"
            )
            return None

        return ChatOpenAI(
            api_key=OPENAI_API_KEY,
            model=model or "gpt-4o-mini",
            temperature=temperature,
            max_tokens=max_tokens,
            tags=tags,
            model_kwargs=kwargs,
        )

    elif provider == "openrouter":
        if not OPENROUTER_API_KEY:
            logger.warning(
                f"[{agent_name}] OPENROUTER_API_KEY not set, LLM calls will fail"
            )
            logger.warning(f"[{agent_name}] Get API key at: https://openrouter.ai/keys")
            return None

        # Use OpenRouter's OpenAI-compatible API
        # https://openrouter.ai/docs#quick-start
        return ChatOpenAI(
            base_url=OPENROUTER_BASE_URL,
            api_key=OPENROUTER_API_KEY,
            model=model or OPENROUTER_DEFAULT_MODEL,
            temperature=temperature,
            max_tokens=max_tokens,
            streaming=True,  # Enable streaming for astream support
            default_headers={
                "HTTP-Referer": "https://codechef.appsmithery.co",
                "X-Title": "code-chef DevOps Platform",
            },
            tags=tags,
            model_kwargs=kwargs,
        )

    else:
        raise ValueError(f"Unknown LLM provider: {provider}")


def get_embeddings(
    model: Optional[str] = None,
    chunk_size: int = 1000,
    provider: Optional[Literal["gradient", "openai"]] = None,
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
        DigitalOcean Serverless Inference does NOT support embeddings (as of Nov 2025).
        Use OpenAI directly for embedding functionality.
        When provider="gradient", this falls back to OpenAI if available.
    """
    provider = provider or EMBEDDING_PROVIDER

    if provider == "gradient":
        logger.warning(
            "Gradient AI Serverless Inference does not support embeddings. Falling back to OpenAI."
        )
        if not OPENAI_API_KEY:
            logger.error(
                "OPENAI_API_KEY not set, embeddings will fail. Please configure OpenAI or use provider='openai'"
            )
            return None

        return OpenAIEmbeddings(
            api_key=OPENAI_API_KEY,
            model=model or "text-embedding-3-small",
            chunk_size=chunk_size,
        )

    elif provider == "openai":
        if not OPENAI_API_KEY:
            logger.warning("OPENAI_API_KEY not set, embeddings will fail")
            return None

        return OpenAIEmbeddings(
            api_key=OPENAI_API_KEY,
            model=model or "text-embedding-3-small",
            chunk_size=chunk_size,
        )

    else:
        raise ValueError(
            f"Unknown embedding provider: {provider}. Supported: gradient (falls back to openai), openai"
        )


# Backward compatibility aliases
def get_gradient_llm(
    agent_name: str, model: str = "llama3-8b-instruct", **kwargs
) -> ChatOpenAI:
    """Backward compatibility wrapper for get_llm() with gradient provider"""
    return get_llm(agent_name, model=model, provider="gradient", **kwargs)


def get_gradient_embeddings(
    model: str = "text-embedding-ada-002", chunk_size: int = 1000
) -> OpenAIEmbeddings:
    """Backward compatibility wrapper for get_embeddings() with gradient provider"""
    return get_embeddings(model=model, chunk_size=chunk_size, provider="gradient")


# Pre-configured instances loaded from YAML config
# Falls back to hardcoded models if config unavailable
try:
    from lib.config_loader import get_config_loader

    _config_loader = get_config_loader(hot_reload=False)

    # Load all agent configs from YAML
    orchestrator_config = _config_loader.get_agent_config("orchestrator")
    feature_dev_config = _config_loader.get_agent_config("feature-dev")
    code_review_config = _config_loader.get_agent_config("code-review")
    infrastructure_config = _config_loader.get_agent_config("infrastructure")
    cicd_config = _config_loader.get_agent_config("cicd")
    documentation_config = _config_loader.get_agent_config("documentation")

    # Create LLM instances with YAML-loaded configs
    orchestrator_llm = get_llm(
        "orchestrator",
        model=orchestrator_config.model,
        temperature=orchestrator_config.temperature,
        max_tokens=orchestrator_config.max_tokens,
    )
    feature_dev_llm = get_llm(
        "feature-dev",
        model=feature_dev_config.model,
        temperature=feature_dev_config.temperature,
        max_tokens=feature_dev_config.max_tokens,
    )
    code_review_llm = get_llm(
        "code-review",
        model=code_review_config.model,
        temperature=code_review_config.temperature,
        max_tokens=code_review_config.max_tokens,
    )
    infrastructure_llm = get_llm(
        "infrastructure",
        model=infrastructure_config.model,
        temperature=infrastructure_config.temperature,
        max_tokens=infrastructure_config.max_tokens,
    )
    cicd_llm = get_llm(
        "cicd",
        model=cicd_config.model,
        temperature=cicd_config.temperature,
        max_tokens=cicd_config.max_tokens,
    )
    documentation_llm = get_llm(
        "documentation",
        model=documentation_config.model,
        temperature=documentation_config.temperature,
        max_tokens=documentation_config.max_tokens,
    )

    logger.info("Successfully loaded agent configs from config/agents/models.yaml")

except Exception as e:
    # Backward compatibility: Fall back to hardcoded models if YAML unavailable
    logger.warning(f"Failed to load config from YAML, using hardcoded models: {e}")
    orchestrator_llm = get_llm("orchestrator", model="llama3.3-70b-instruct")
    feature_dev_llm = get_llm("feature-dev", model="llama3-8b-instruct")
    code_review_llm = get_llm("code-review", model="llama3.3-70b-instruct")
    infrastructure_llm = get_llm("infrastructure", model="llama3-8b-instruct")
    cicd_llm = get_llm("cicd", model="llama3-8b-instruct")
    documentation_llm = get_llm("documentation", model="mistral-nemo-instruct-2407")

# Shared embeddings instance (falls back to OpenAI since Gradient doesn't support embeddings)
gradient_embeddings = get_embeddings()

logger.info("Unified LangChain configuration initialized")
logger.info(f"LLM Provider: {LLM_PROVIDER}")
logger.info(f"Embedding Provider: {EMBEDDING_PROVIDER}")
logger.info(f"Gradient Base URL: {GRADIENT_BASE_URL}")
logger.info(f"Gradient API Key: {'SET' if GRADIENT_API_KEY else 'NOT SET'}")
logger.info(f"LangSmith tracing: {'ENABLED' if LANGSMITH_ENABLED else 'DISABLED'}")
