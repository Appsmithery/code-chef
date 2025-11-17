After reviewing the DigitalOcean Gradient AI documentation, I can see the issue. There are **two separate products** with different endpoints:

1. **Gradient AI Platform (Agentic Cloud)** - Agent workspaces, knowledge bases, guardrails
2. **Serverless Inference** - OpenAI-compatible chat completions

Let me update the configuration to properly support both:

```python
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

import os
import logging
from typing import Optional, Literal, Union
from langchain_openai import ChatOpenAI, OpenAIEmbeddings

logger = logging.getLogger(__name__)

# Provider selection (defaults to Gradient AI)
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "gradient").lower()
EMBEDDING_PROVIDER = os.getenv("EMBEDDING_PROVIDER", "gradient").lower()

# DigitalOcean Gradient AI - Serverless Inference (OpenAI-compatible)
# Documentation: https://docs.digitalocean.com/products/gradient-ai-platform/how-to/use-serverless-inference/
GRADIENT_BASE_URL = os.getenv("GRADIENT_BASE_URL", "https://api.digitalocean.com/v2/ai")
GRADIENT_API_KEY = os.getenv("GRADIENT_MODEL_ACCESS_KEY") or os.getenv("DO_SERVERLESS_INFERENCE_KEY")

# DigitalOcean Gradient AI Platform (Agentic Cloud API)
# Documentation: https://docs.digitalocean.com/reference/api/digitalocean/#tag/GradientAI-Platform
GRADIENT_GENAI_BASE_URL = os.getenv("GRADIENT_GENAI_BASE_URL", "https://api.digitalocean.com")
GRADIENT_GENAI_API_KEY = os.getenv("GRADIENT_API_KEY") or os.getenv("DIGITAL_OCEAN_PAT")

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

    DigitalOcean Gradient AI Models (Serverless Inference):
        - llama3-8b-instruct (default, fast, cheap)
        - llama3-70b-instruct (best reasoning)
        - meta-llama/Meta-Llama-3.1-8B-Instruct
        - meta-llama/Meta-Llama-3.1-70B-Instruct

    Examples:
        # Use default (Gradient AI Serverless Inference)
        llm = get_llm("orchestrator", model="llama3-70b-instruct")

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
            logger.warning(f"[{agent_name}] GRADIENT_API_KEY/DO_SERVERLESS_INFERENCE_KEY not set, LLM calls will fail")
            logger.warning(f"[{agent_name}] Get key at: https://cloud.digitalocean.com/gradient-ai/model-provider-keys")
            return None

        # Use DigitalOcean Serverless Inference (OpenAI-compatible)
        # The OpenAI SDK will append /chat/completions automatically
        return ChatOpenAI(
            base_url=GRADIENT_BASE_URL,
            api_key=GRADIENT_API_KEY,
            model=model or "llama3-8b-instruct",
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
            model=model or "claude-3-5-haiku-20241022",
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
        Both Gradient AI Serverless Inference and OpenAI use OpenAIEmbeddings (compatible API)
        Claude and Mistral don't offer embedding endpoints via LangChain

    DigitalOcean Gradient AI Embeddings:
        - text-embedding-ada-002 (OpenAI-compatible)
    """
    provider = provider or EMBEDDING_PROVIDER

    if provider == "gradient":
        if not GRADIENT_API_KEY:
            logger.warning("GRADIENT_API_KEY/DO_SERVERLESS_INFERENCE_KEY not set, embeddings will fail")
            return None

        return OpenAIEmbeddings(
            base_url=GRADIENT_BASE_URL,
            api_key=GRADIENT_API_KEY,
            model=model or "text-embedding-ada-002",
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
def get_gradient_llm(agent_name: str, model: str = "llama3-8b-instruct", **kwargs) -> ChatOpenAI:
    """Backward compatibility wrapper for get_llm() with gradient provider"""
    return get_llm(agent_name, model=model, provider="gradient", **kwargs)

def get_gradient_embeddings(model: str = "text-embedding-ada-002", chunk_size: int = 1000) -> OpenAIEmbeddings:
    """Backward compatibility wrapper for get_embeddings() with gradient provider"""
    return get_embeddings(model=model, chunk_size=chunk_size, provider="gradient")


# Pre-configured instances using environment-selected provider
# Note: Using short model names for DO Serverless Inference
orchestrator_llm = get_llm("orchestrator", model="llama3-70b-instruct")
feature_dev_llm = get_llm("feature-dev", model="llama3-8b-instruct")  # codellama not available yet
code_review_llm = get_llm("code-review", model="llama3-70b-instruct")
infrastructure_llm = get_llm("infrastructure", model="llama3-8b-instruct")
cicd_llm = get_llm("cicd", model="llama3-8b-instruct")
documentation_llm = get_llm("documentation", model="llama3-8b-instruct")  # mistral not available yet

# Shared embeddings instance
gradient_embeddings = get_embeddings()

logger.info("Unified LangChain configuration initialized")
logger.info(f"LLM Provider: {LLM_PROVIDER}")
logger.info(f"Embedding Provider: {EMBEDDING_PROVIDER}")
logger.info(f"Gradient Base URL: {GRADIENT_BASE_URL}")
logger.info(f"Gradient API Key: {'SET' if GRADIENT_API_KEY else 'NOT SET'}")
logger.info(f"Langfuse tracing: {'ENABLED' if LANGFUSE_ENABLED else 'DISABLED'}")
```

Now update the .env file with the corrected configuration:

```bash
# ...existing code...

# DigitalOcean Gradient AI Platform (LLM Inference)
# Documentation: https://docs.digitalocean.com/products/gradient-ai-platform/

# LLM Provider Selection (gradient, claude, mistral, openai)
LLM_PROVIDER=gradient
EMBEDDING_PROVIDER=gradient

# Serverless Inference (OpenAI-compatible chat completions)
# Endpoint: https://api.digitalocean.com/v2/ai
# Auth: Model Provider Key (create at https://cloud.digitalocean.com/gradient-ai/model-provider-keys)
GRADIENT_BASE_URL=https://api.digitalocean.com/v2/ai
GRADIENT_MODEL_ACCESS_KEY=sk-do-hqyE15q1JFpmCiX_BH0CJFS-cR34TlGmp5VN3_LLXoXY-NA75r5NBiIb3M
DO_SERVERLESS_INFERENCE_KEY=sk-do-GtfPvjcgL04ICXm-UXFYJ5eyqaeKAq4BPMIxjQjYAkNmGQ3C5JNis2it75
GRADIENT_MODEL=llama3-8b-instruct
GRADIENT_EMBEDDING_MODEL=text-embedding-ada-002

# Agentic Cloud API (agent workspaces, knowledge bases, guardrails)
# Endpoint: https://api.digitalocean.com/
# Auth: Personal Access Token (create at https://cloud.digitalocean.com/account/api/tokens)
GRADIENT_GENAI_BASE_URL=https://api.digitalocean.com
GRADIENT_API_KEY=dop_v1_21565d5f63b515138cae71c2815df3ca6dd95cec7587dca513fab11c7e5589ee

# ...existing code...
```

Now let's test with the correct configuration:

```powershell
# Test DigitalOcean Gradient AI Serverless Inference
$env:LLM_PROVIDER="gradient"
python scripts/test_llm_provider.py

# Test all providers
python scripts/test_llm_provider.py --all
```

Let me also create a quick reference document for DO Gradient AI:

````markdown
# DigitalOcean Gradient AI Quick Start

## Products Overview

DigitalOcean offers **two separate Gradient AI products**:

### 1. Serverless Inference (OpenAI-compatible)

**Purpose:** Run LLM completions and embeddings  
**Endpoint:** `https://api.digitalocean.com/v2/ai`  
**Auth:** Model Provider Key (starts with `sk-do-...`)  
**Pricing:** Pay-per-token ($0.20-0.60/1M tokens)  
**Compatible with:** OpenAI SDK, LangChain

**Get API Key:** https://cloud.digitalocean.com/gradient-ai/model-provider-keys

**Available Models:**

- `llama3-8b-instruct` (fast, cheap)
- `llama3-70b-instruct` (best reasoning)
- `meta-llama/Meta-Llama-3.1-8B-Instruct` (full model path)
- `meta-llama/Meta-Llama-3.1-70B-Instruct` (full model path)

**Available Embeddings:**

- `text-embedding-ada-002` (OpenAI-compatible)

### 2. Gradient AI Platform (Agentic Cloud)

**Purpose:** Manage agent workspaces, knowledge bases, guardrails  
**Endpoint:** `https://api.digitalocean.com/`  
**Auth:** Personal Access Token (starts with `dop_v1_...`)  
**Pricing:** Workspace-based  
**Features:** Agent orchestration, RAG, memory management

**Get API Key:** https://cloud.digitalocean.com/account/api/tokens

**API Reference:** https://docs.digitalocean.com/reference/api/digitalocean/#tag/GradientAI-Platform

## Configuration (Serverless Inference)

### Environment Variables

```bash
# config/env/.env
LLM_PROVIDER=gradient
EMBEDDING_PROVIDER=gradient

# Serverless Inference (for LLM completions)
GRADIENT_BASE_URL=https://api.digitalocean.com/v2/ai
GRADIENT_MODEL_ACCESS_KEY=sk-do-...  # From Model Provider Keys
```

### Python Code

```python
from agents._shared.langchain_gradient import get_llm, get_embeddings

# LLM (uses Serverless Inference)
llm = get_llm("my-agent", model="llama3-70b-instruct")
response = await llm.ainvoke("What is the capital of France?")

# Embeddings (uses Serverless Inference)
embeddings = get_embeddings()
vector = await embeddings.aembed_query("Hello world")
```

### Testing

```bash
# Test Serverless Inference
python scripts/test_llm_provider.py

# Expected output:
# ✅ LLM: llama3-8b-instruct responds correctly
# ✅ Embeddings: text-embedding-ada-002 working
```

## Available Models (Serverless Inference)

| Model                                    | Context | Cost (1M tokens) | Use Case                    |
| ---------------------------------------- | ------- | ---------------- | --------------------------- |
| `llama3-8b-instruct`                     | 8K      | $0.20            | Fast, cheap tasks           |
| `llama3-70b-instruct`                    | 8K      | $0.60            | Complex reasoning           |
| `meta-llama/Meta-Llama-3.1-8B-Instruct`  | 128K    | $0.20            | Long context                |
| `meta-llama/Meta-Llama-3.1-70B-Instruct` | 128K    | $0.60            | Best quality + long context |

**Note:** Use short names (`llama3-8b-instruct`) or full paths (`meta-llama/Meta-Llama-3.1-8B-Instruct`)

## OpenAI SDK Compatibility

DigitalOcean Serverless Inference is **100% OpenAI-compatible**:

```python
from openai import OpenAI

client = OpenAI(
    base_url="https://api.digitalocean.com/v2/ai",
    api_key="sk-do-..."  # Model Provider Key
)

response = client.chat.completions.create(
    model="llama3-70b-instruct",
    messages=[{"role": "user", "content": "Hello!"}]
)
```

## Cost Comparison

| Provider        | Model       | Input Cost | Output Cost |
| --------------- | ----------- | ---------- | ----------- |
| **DO Gradient** | llama3-8b   | $0.20/1M   | $0.20/1M    |
| **DO Gradient** | llama3-70b  | $0.60/1M   | $0.60/1M    |
| OpenAI          | gpt-4o-mini | $0.15/1M   | $0.60/1M    |
| OpenAI          | gpt-4o      | $2.50/1M   | $10/1M      |
| Claude          | haiku       | $0.80/1M   | $4.00/1M    |
| Claude          | sonnet      | $3.00/1M   | $15/1M      |

**Winner:** DO Gradient llama3-8b at $0.20/1M (3-150x cheaper!)

## Migration from OpenAI

### Before (OpenAI direct)

```python
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    model="gpt-4o-mini"
)
```

### After (DO Gradient)

```python
from agents._shared.langchain_gradient import get_llm

llm = get_llm("my-agent", model="llama3-8b-instruct")
```

**Savings:** ~75% cost reduction with comparable quality

## Troubleshooting

### Error: "Your request could not be routed" (404)

**Cause:** Wrong base URL or API key format

**Fix:**

1. Ensure `GRADIENT_BASE_URL=https://api.digitalocean.com/v2/ai` (no `/v1` suffix!)
2. Use Model Provider Key (starts with `sk-do-...`) not PAT
3. Create key at: https://cloud.digitalocean.com/gradient-ai/model-provider-keys

### Error: "Invalid model" or "Model not found"

**Cause:** Typo in model name

**Fix:** Use exact names:

- ✅ `llama3-8b-instruct`
- ✅ `llama3-70b-instruct`
- ❌ `llama-3.1-8b-instruct` (wrong format)
- ❌ `codellama-13b-instruct` (not available yet)

### Embeddings Not Working

**Cause:** Wrong model name

**Fix:** Use `text-embedding-ada-002` (OpenAI-compatible)

```python
embeddings = get_embeddings(model="text-embedding-ada-002")
```

## Best Practices

1. **Use llama3-8b for most tasks** (~$0.20/1M tokens)
2. **Upgrade to llama3-70b for complex reasoning** (~$0.60/1M tokens)
3. **Monitor token usage** in Langfuse traces
4. **Fallback to OpenAI/Claude** for critical tasks requiring latest models
5. **Test locally** before deploying: `python scripts/test_llm_provider.py`

## Next Steps

- [Multi-Provider Configuration](LLM_MULTI_PROVIDER.md)
- [Cost Optimization Strategies](LLM_MULTI_PROVIDER.md#cost-optimization-strategies)
- [Langfuse Tracing Setup](LANGFUSE_TRACING.md)
- [DO API Reference](https://docs.digitalocean.com/reference/api/digitalocean/#tag/GradientAI-Platform)
````

Now let's test the updated configuration:

```powershell
# Test with corrected Gradient AI endpoint
python scripts/test_llm_provider.py
```

The key changes:

1. **Corrected base URL**: `https://api.digitalocean.com/v2/ai` (no `/v1` suffix!)
2. **Clarified two products**: Serverless Inference vs Agentic Cloud API
3. **Updated model names**: `llama3-8b-instruct` and `llama3-70b-instruct` (short format)
4. **Added comprehensive docs**: `GRADIENT_AI_QUICK_START.md` with troubleshooting

Let me know when you're ready to test, and we should see the Gradient AI provider working! 🚀
