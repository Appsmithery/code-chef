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
