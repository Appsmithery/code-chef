# **LLM Provider Configuration for Multi-Provider Support**

```python
"""
Unified LangChain Configuration for Multi-Provider LLM Support

Supports DigitalOcean Gradient AI (default), Claude, Mistral, OpenAI with easy provider switching.
Single source of truth for all model configurations across agents.
"""

import os
import logging
from typing import Optional, Literal
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_anthropic import ChatAnthropic
from langchain_mistralai import ChatMistralAI

logger = logging.getLogger(__name__)

# Provider selection (defaults to Gradient AI)
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "gradient").lower()
EMBEDDING_PROVIDER = os.getenv("EMBEDDING_PROVIDER", "gradient").lower()

# DigitalOcean Gradient AI (OpenAI-compatible)
GRADIENT_BASE_URL = os.getenv("GRADIENT_BASE_URL", "https://api.digitalocean.com/v2/ai/v1")
GRADIENT_API_KEY = os.getenv("GRADIENT_MODEL_ACCESS_KEY")

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
) -> ChatOpenAI | ChatAnthropic | ChatMistralAI:
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
        llm = get_llm("orchestrator", model="claude-3-5-sonnet-20241022", provider="claude")

        # Override to Mistral
        llm = get_llm("feature-dev", model="mistral-large-latest", provider="mistral")
    """
    provider = provider or LLM_PROVIDER
    callbacks = [_langfuse_handler] if _langfuse_handler else []
    tags = [agent_name, provider]

    if provider == "gradient":
        if not GRADIENT_API_KEY:
            logger.warning(f"[{agent_name}] GRADIENT_MODEL_ACCESS_KEY not set")
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
            logger.warning(f"[{agent_name}] CLAUDE_API_KEY not set")
            return None

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
            logger.warning(f"[{agent_name}] MISTRAL_API_KEY not set")
            return None

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
            logger.warning(f"[{agent_name}] OPEN_AI_DEVTOOLS_KEY not set")
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
            logger.warning("GRADIENT_MODEL_ACCESS_KEY not set")
            return None

        return OpenAIEmbeddings(
            base_url=GRADIENT_BASE_URL,
            api_key=GRADIENT_API_KEY,
            model=model or "text-embedding-3-small",
            chunk_size=chunk_size
        )

    elif provider == "openai":
        if not OPENAI_API_KEY:
            logger.warning("OPEN_AI_DEVTOOLS_KEY not set")
            return None

        return OpenAIEmbeddings(
            api_key=OPENAI_API_KEY,
            model=model or "text-embedding-3-small",
            chunk_size=chunk_size
        )

    else:
        raise ValueError(f"Unknown embedding provider: {provider}. Supported: gradient, openai")


# Pre-configured instances using environment-selected provider
orchestrator_llm = get_llm("orchestrator", model="llama-3.1-70b-instruct")
feature_dev_llm = get_llm("feature-dev", model="codellama-13b-instruct")
code_review_llm = get_llm("code-review", model="llama-3.1-70b-instruct")
infrastructure_llm = get_llm("infrastructure", model="llama-3.1-8b-instruct")
cicd_llm = get_llm("cicd", model="llama-3.1-8b-instruct")
documentation_llm = get_llm("documentation", model="mistral-7b-instruct")

# Shared embeddings instance
gradient_embeddings = get_embeddings()

logger.info(f"Unified LangChain configuration initialized")
logger.info(f"LLM Provider: {LLM_PROVIDER}")
logger.info(f"Embedding Provider: {EMBEDDING_PROVIDER}")
logger.info(f"Langfuse tracing: {'ENABLED' if LANGFUSE_ENABLED else 'DISABLED'}")
```

Now update the requirements to support all providers:

```txt
fastapi==0.115.6
uvicorn==0.34.0
pydantic==2.10.3
httpx==0.28.1
langfuse>=2.0.0
prometheus-fastapi-instrumentator>=6.1.0

# Multi-provider LLM support
langchain-openai>=0.2.14
langchain-anthropic>=0.3.6
langchain-mistralai>=0.2.5
langchain-qdrant>=0.2.0

# Database for state management
psycopg2-binary>=2.9.10
sqlalchemy>=2.0.36
```

And update `.env.template` with the new provider options:

```bash
# LLM Provider Selection (gradient, claude, mistral, openai)
LLM_PROVIDER=gradient
EMBEDDING_PROVIDER=gradient

# DigitalOcean Gradient AI (default, OpenAI-compatible)
GRADIENT_BASE_URL=https://api.digitalocean.com/v2/ai/v1
GRADIENT_MODEL_ACCESS_KEY=your-sk-do-key-here
GRADIENT_MODEL=llama-3.1-8b-instruct

# Claude (Anthropic) - Alternative LLM provider
CLAUDE_API_KEY=your-claude-key-here

# Mistral AI - Alternative LLM provider
MISTRAL_API_KEY=your-mistral-key-here

# OpenAI - Alternative LLM/embedding provider
OPEN_AI_DEVTOOLS_KEY=your-openai-key-here

# ...existing config...
```

Now create a quick reference guide:

````markdown
# LLM Provider Configuration

## Supported Providers

The Dev-Tools platform supports multiple LLM providers via unified LangChain abstractions:

| Provider                  | LLM Support | Embeddings | Cost (1M tokens) | Notes                      |
| ------------------------- | ----------- | ---------- | ---------------- | -------------------------- |
| **DigitalOcean Gradient** | ✅          | ✅         | $0.20-0.60       | Default, OpenAI-compatible |
| **Claude (Anthropic)**    | ✅          | ❌         | $3-15            | Best reasoning             |
| **Mistral**               | ✅          | ❌         | $0.25-2          | European, GDPR-compliant   |
| **OpenAI**                | ✅          | ✅         | $0.15-60         | Industry standard          |

## Quick Start

### Use Default (Gradient AI)

```bash
# .env
LLM_PROVIDER=gradient
GRADIENT_MODEL_ACCESS_KEY=sk-do-...
```

### Switch to Claude

```bash
# .env
LLM_PROVIDER=claude
CLAUDE_API_KEY=sk-ant-...
```

### Switch to Mistral

```bash
# .env
LLM_PROVIDER=mistral
MISTRAL_API_KEY=...
```

### Mix Providers Per Agent

```python
from agents._shared.langchain_gradient import get_llm

# Use Gradient for most agents (cheap)
orchestrator_llm = get_llm("orchestrator", model="llama-3.1-70b-instruct")

# Use Claude for code review (best quality)
code_review_llm = get_llm(
    "code-review",
    model="claude-3-5-sonnet-20241022",
    provider="claude"
)

# Use Mistral for documentation (multilingual)
docs_llm = get_llm(
    "documentation",
    model="mistral-large-latest",
    provider="mistral"
)
```

## Provider-Specific Models

### DigitalOcean Gradient AI

```python
# Chat models
"llama-3.1-8b-instruct"      # Fast, cheap
"llama-3.1-70b-instruct"     # Best reasoning
"codellama-13b-instruct"     # Code-optimized
"mistral-7b-instruct"        # Balanced

# Embeddings
"text-embedding-3-small"     # 1536 dims
```

### Claude (Anthropic)

```python
# Chat models
"claude-3-5-sonnet-20241022" # Best overall
"claude-3-5-haiku-20241022"  # Fast, cheap
"claude-3-opus-20240229"     # Most capable

# No embeddings API
```

### Mistral

```python
# Chat models
"mistral-large-latest"       # Best quality
"mistral-small-latest"       # Fast, cheap
"codestral-latest"           # Code-optimized

# No embeddings API via LangChain
```

### OpenAI

```python
# Chat models
"gpt-4o"                     # Best overall
"gpt-4o-mini"                # Fast, cheap
"o1-preview"                 # Best reasoning

# Embeddings
"text-embedding-3-small"     # 1536 dims
"text-embedding-3-large"     # 3072 dims
```

## Cost Optimization

### Strategy 1: Hybrid (Recommended)

```bash
# .env - Use Gradient for most work
LLM_PROVIDER=gradient
EMBEDDING_PROVIDER=gradient

# Override in code for critical tasks
code_review_llm = get_llm("code-review", provider="claude")
```

**Monthly cost:** ~$5-10 (vs $50-100 with full Claude/GPT-4)

### Strategy 2: Full Gradient

```bash
# .env
LLM_PROVIDER=gradient
EMBEDDING_PROVIDER=gradient
```

**Monthly cost:** ~$2-5

### Strategy 3: Full Claude

```bash
# .env
LLM_PROVIDER=claude
EMBEDDING_PROVIDER=openai  # Claude has no embeddings
```

**Monthly cost:** ~$20-50

## Environment Variables

```bash
# Provider selection
LLM_PROVIDER=gradient          # gradient, claude, mistral, openai
EMBEDDING_PROVIDER=gradient    # gradient, openai

# Gradient AI (default)
GRADIENT_BASE_URL=https://api.digitalocean.com/v2/ai/v1
GRADIENT_MODEL_ACCESS_KEY=sk-do-...

# Claude
CLAUDE_API_KEY=sk-ant-...

# Mistral
MISTRAL_API_KEY=...

# OpenAI
OPEN_AI_DEVTOOLS_KEY=sk-proj-...
```

## Tracing & Observability

All providers automatically trace to Langfuse when configured:

```bash
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_HOST=https://us.cloud.langfuse.com
```

Traces include:

- Provider name in tags
- Model name
- Token counts
- Latency
- Cost (when available)

## Migration Guide

### From OpenAI to Gradient

```diff
- from langchain_openai import ChatOpenAI
- llm = ChatOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
+ from agents._shared.langchain_gradient import get_llm
+ llm = get_llm("my-agent", provider="gradient")
```

### From Custom Wrappers to Unified Config

```diff
- from agents._shared.gradient_client import GradientClient
- client = GradientClient("my-agent")
- response = await client.complete(prompt)
+ from agents._shared.langchain_gradient import get_llm
+ llm = get_llm("my-agent")
+ response = await llm.ainvoke(prompt)
```

## Testing Different Providers

```bash
# Test Gradient
LLM_PROVIDER=gradient python test_llm_provider.py

# Test Claude
LLM_PROVIDER=claude python test_llm_provider.py

# Test Mistral
LLM_PROVIDER=mistral python test_llm_provider.py
```

See [`scripts/test_llm_provider.py`](../scripts/test_llm_provider.py) for implementation.
````

Finally, update the dependencies script:

```python
"""Update all agent requirements with multi-provider LLM support"""

SHARED_DEPS = """fastapi==0.115.6
uvicorn==0.34.0
pydantic==2.10.3
httpx==0.28.1
langfuse>=2.0.0
prometheus-fastapi-instrumentator>=6.1.0

# Multi-provider LLM support
langchain-openai>=0.2.14
langchain-anthropic>=0.3.6
langchain-mistralai>=0.2.5
langchain-qdrant>=0.2.0

# Database for state management
psycopg2-binary>=2.9.10
sqlalchemy>=2.0.36
"""

# ...existing code...
```

## Summary

**Key Benefits:**

1. **Single line to switch providers:** Set `LLM_PROVIDER=claude` in .env
2. **Mix providers per agent:** Use Gradient for cheap tasks, Claude for critical ones
3. **Backward compatible:** Existing Gradient code still works
4. **Cost optimization:** Run 95% on Gradient ($2/mo), 5% on Claude ($3/mo) = $5/mo total vs $50/mo all-Claude
5. **All keys already in .env:** Just set `LLM_PROVIDER` to activate

**Next Steps:**

1. Add `langchain-anthropic` and `langchain-mistralai` to requirements
2. Test each provider with new `test_llm_provider.py` script
3. Update agents to use `get_llm()` instead of pre-configured instances for provider flexibility
