"""
Unified LangChain LLM Provider Configuration

Multi-provider LLM abstraction layer with OpenRouter as the primary gateway.
Single source of truth for all model configurations across agents.

Architecture:
- Primary LLM Gateway: OpenRouter (200+ models, unified API)
- Embedding Provider: OpenAI (text-embedding-3-small)
- Additional Providers: Claude, Mistral, OpenAI (direct access)

OpenRouter Benefits:
- Access to 200+ models from 50+ providers via single API key
- Per-agent model selection for cost/performance optimization
- Automatic failover between providers
- Unified billing and rate limiting
- Free tier models available for development

Supported Providers:
1. openrouter (default) - Multi-model gateway
   - Endpoint: https://openrouter.ai/api/v1
   - Auth: API key from https://openrouter.ai/keys
   - Models: anthropic/claude-3-5-sonnet, qwen/qwen-2.5-coder-32b-instruct, etc.
   - See: https://openrouter.ai/models

2. openai - Direct OpenAI API access
   - Endpoint: https://api.openai.com/v1
   - Models: gpt-4o, gpt-4o-mini, etc.
   - Also used for embeddings (text-embedding-3-small)

3. claude - Direct Anthropic API access
   - Endpoint: https://api.anthropic.com/v1
   - Models: claude-3-5-sonnet, claude-3-5-haiku

4. mistral - Direct Mistral API access
   - Endpoint: https://api.mistral.ai/v1
   - Models: mistral-large-latest, mistral-small-latest

Configuration:
- Per-agent models: config/agents/models.yaml
- Provider selection: LLM_PROVIDER environment variable (default: openrouter)
- API keys: OPENROUTER_API_KEY, OPENAI_API_KEY, etc.
"""

import logging
import os
from typing import Literal, Optional, Union

from langchain_openai import ChatOpenAI, OpenAIEmbeddings

logger = logging.getLogger(__name__)

# Provider selection (defaults to OpenRouter for multi-model access)
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openrouter").lower()
EMBEDDING_PROVIDER = os.getenv("EMBEDDING_PROVIDER", "openai").lower()

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
    provider: Optional[Literal["claude", "mistral", "openai", "openrouter"]] = None,
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

    if provider == "claude":
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


# Backward compatibility aliases (deprecated - use get_llm/get_embeddings directly)
def get_gradient_llm(
    agent_name: str, model: str = "llama3-8b-instruct", **kwargs
) -> ChatOpenAI:
    """Deprecated: Use get_llm() with provider='openrouter' instead"""
    logger.warning(
        "get_gradient_llm() is deprecated. Use get_llm() with provider='openrouter'"
    )
    return get_llm(agent_name, model=model, provider="openrouter", **kwargs)


def get_gradient_embeddings(
    model: str = "text-embedding-3-small", chunk_size: int = 1000
) -> OpenAIEmbeddings:
    """Deprecated: Use get_embeddings() with provider='openai' instead"""
    logger.warning("get_gradient_embeddings() is deprecated. Use get_embeddings()")
    return get_embeddings(model=model, chunk_size=chunk_size, provider="openai")


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

# Shared embeddings instance (OpenAI text-embedding-3-small)
shared_embeddings = get_embeddings()

logger.info("🚀 Unified LangChain configuration initialized")
logger.info(f"  LLM Provider: {LLM_PROVIDER} (OpenRouter multi-model gateway)")
logger.info(f"  Embedding Provider: {EMBEDDING_PROVIDER} (text-embedding-3-small)")
logger.info(f"  OpenRouter API Key: {'✓ SET' if OPENROUTER_API_KEY else '✗ NOT SET'}")
logger.info(f"  OpenAI API Key: {'✓ SET' if OPENAI_API_KEY else '✗ NOT SET'}")
logger.info(
    f"  LangSmith tracing: {'✓ ENABLED' if LANGSMITH_ENABLED else '✗ DISABLED'}"
)
