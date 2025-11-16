# LLM Multi-Provider Configuration

## Overview

The Dev-Tools platform supports multiple LLM providers via unified LangChain abstractions, allowing you to easily switch between providers or mix them based on your needs.

## Supported Providers

| Provider                  | LLM Support | Embeddings | Cost (1M tokens) | Notes                      |
| ------------------------- | ----------- | ---------- | ---------------- | -------------------------- |
| **DigitalOcean Gradient** | ✅          | ✅         | $0.20-0.60       | Default, OpenAI-compatible |
| **Claude (Anthropic)**    | ✅          | ❌         | $3-15            | Best reasoning             |
| **Mistral**               | ✅          | ❌         | $0.25-2          | European, GDPR-compliant   |
| **OpenAI**                | ✅          | ✅         | $0.15-60         | Industry standard          |

## Quick Start

### Use Default (Gradient AI)

```bash
# config/env/.env
LLM_PROVIDER=gradient
GRADIENT_MODEL_ACCESS_KEY=sk-do-...
```

### Switch to Claude

```bash
# config/env/.env
LLM_PROVIDER=claude
CLAUDE_API_KEY=sk-ant-...
```

### Switch to Mistral

```bash
# config/env/.env
LLM_PROVIDER=mistral
MISTRAL_API_KEY=...
```

### Switch to OpenAI

```bash
# config/env/.env
LLM_PROVIDER=openai
OPEN_AI_DEVTOOLS_KEY=sk-proj-...
```

## Code Examples

### Basic Usage (Use Environment-Selected Provider)

```python
from agents._shared.langchain_gradient import get_llm, get_embeddings

# LLM will use provider from LLM_PROVIDER env var
llm = get_llm("my-agent", model="llama-3.1-70b-instruct")
response = await llm.ainvoke("What is the capital of France?")

# Embeddings will use provider from EMBEDDING_PROVIDER env var
embeddings = get_embeddings()
vector = await embeddings.aembed_query("Hello world")
```

### Override Provider Per Agent (Hybrid Strategy)

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

# Use OpenAI for specific tasks
openai_llm = get_llm(
    "special-task",
    model="gpt-4o",
    provider="openai"
)
```

### Backward Compatibility

```python
# Old code still works
from agents._shared.langchain_gradient import get_gradient_llm, get_gradient_embeddings

llm = get_gradient_llm("my-agent", model="llama-3.1-8b-instruct")
embeddings = get_gradient_embeddings()
```

## Provider-Specific Models

### DigitalOcean Gradient AI

```python
# Chat models
"llama-3.1-8b-instruct"      # Fast, cheap ($0.20/1M tokens)
"llama-3.1-70b-instruct"     # Best reasoning ($0.60/1M tokens)
"codellama-13b-instruct"     # Code-optimized
"mistral-7b-instruct"        # Balanced

# Embeddings
"text-embedding-3-small"     # 1536 dims
```

### Claude (Anthropic)

```python
# Chat models
"claude-3-5-sonnet-20241022" # Best overall ($3/1M in, $15/1M out)
"claude-3-5-haiku-20241022"  # Fast, cheap ($0.80/1M in, $4/1M out)
"claude-3-opus-20240229"     # Most capable ($15/1M in, $75/1M out)

# No embeddings API
```

### Mistral

```python
# Chat models
"mistral-large-latest"       # Best quality ($2/1M tokens)
"mistral-small-latest"       # Fast, cheap ($0.25/1M tokens)
"codestral-latest"           # Code-optimized

# No embeddings API via LangChain
```

### OpenAI

```python
# Chat models
"gpt-4o"                     # Best overall ($2.50/1M in, $10/1M out)
"gpt-4o-mini"                # Fast, cheap ($0.15/1M in, $0.60/1M out)
"o1-preview"                 # Best reasoning ($15/1M in, $60/1M out)

# Embeddings
"text-embedding-3-small"     # 1536 dims ($0.02/1M tokens)
"text-embedding-3-large"     # 3072 dims ($0.13/1M tokens)
```

## Cost Optimization Strategies

### Strategy 1: Hybrid (Recommended)

Use Gradient AI for most work, upgrade to Claude/OpenAI for critical tasks.

```bash
# config/env/.env - Use Gradient by default
LLM_PROVIDER=gradient
EMBEDDING_PROVIDER=gradient

# All API keys configured for selective override
GRADIENT_MODEL_ACCESS_KEY=sk-do-...
CLAUDE_API_KEY=sk-ant-...
MISTRAL_API_KEY=...
OPEN_AI_DEVTOOLS_KEY=sk-proj-...
```

```python
# agents/code_review/main.py
from agents._shared.langchain_gradient import get_llm

# Override to Claude for best code review quality
llm = get_llm("code-review", model="claude-3-5-sonnet-20241022", provider="claude")
```

**Monthly cost:** ~$5-10 (vs $50-100 with full Claude/GPT-4)

### Strategy 2: Full Gradient (Ultra Low Cost)

```bash
# config/env/.env
LLM_PROVIDER=gradient
EMBEDDING_PROVIDER=gradient
GRADIENT_MODEL_ACCESS_KEY=sk-do-...
```

**Monthly cost:** ~$2-5

### Strategy 3: Full Claude (Best Quality)

```bash
# config/env/.env
LLM_PROVIDER=claude
EMBEDDING_PROVIDER=openai  # Claude has no embeddings
CLAUDE_API_KEY=sk-ant-...
OPEN_AI_DEVTOOLS_KEY=sk-proj-...  # For embeddings only
```

**Monthly cost:** ~$20-50

### Strategy 4: Mix and Match

```bash
# config/env/.env
LLM_PROVIDER=gradient        # Default for most agents
EMBEDDING_PROVIDER=gradient  # Cheap embeddings

# Configure all keys for flexibility
GRADIENT_MODEL_ACCESS_KEY=sk-do-...
CLAUDE_API_KEY=sk-ant-...
MISTRAL_API_KEY=...
OPEN_AI_DEVTOOLS_KEY=sk-proj-...
```

Then override per agent in code as needed.

## Environment Variables

```bash
# Provider selection
LLM_PROVIDER=gradient          # gradient, claude, mistral, openai
EMBEDDING_PROVIDER=gradient    # gradient, openai

# DigitalOcean Gradient AI (default)
GRADIENT_BASE_URL=https://api.digitalocean.com/v2/ai/v1
GRADIENT_MODEL_ACCESS_KEY=sk-do-...

# Claude (Anthropic)
CLAUDE_API_KEY=sk-ant-...

# Mistral AI
MISTRAL_API_KEY=...

# OpenAI
OPEN_AI_DEVTOOLS_KEY=sk-proj-...

# Langfuse tracing (works with all providers)
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_HOST=https://us.cloud.langfuse.com
```

## Tracing & Observability

All providers automatically trace to Langfuse when configured. Traces include:

- Provider name in tags
- Model name
- Token counts
- Latency
- Cost (when available)

View traces at: https://us.cloud.langfuse.com

## Testing

Test all providers:

```bash
# Test default provider
python scripts/test_llm_provider.py

# Test specific provider
LLM_PROVIDER=claude python scripts/test_llm_provider.py
LLM_PROVIDER=mistral python scripts/test_llm_provider.py
LLM_PROVIDER=openai python scripts/test_llm_provider.py

# Test all providers at once
python scripts/test_llm_provider.py --all

# Test only LLM (skip embeddings)
python scripts/test_llm_provider.py --llm-only

# Test only embeddings
python scripts/test_llm_provider.py --embeddings-only
```

## Migration Guide

### From OpenAI to Unified Config

```diff
- from langchain_openai import ChatOpenAI
- llm = ChatOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
+ from agents._shared.langchain_gradient import get_llm
+ llm = get_llm("my-agent", provider="openai")  # or use LLM_PROVIDER env
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

### From get_gradient_llm to get_llm (Optional)

```diff
- from agents._shared.langchain_gradient import get_gradient_llm
- llm = get_gradient_llm("my-agent", model="llama-3.1-8b-instruct")
+ from agents._shared.langchain_gradient import get_llm
+ llm = get_llm("my-agent", model="llama-3.1-8b-instruct", provider="gradient")
```

Note: `get_gradient_llm()` still works for backward compatibility.

## Deployment

### Update Stack with New Dependencies

```bash
# Rebuild all agents with new langchain packages
cd compose
docker-compose build

# Restart services
docker-compose down
docker-compose up -d

# Verify health
docker-compose ps
curl http://localhost:8001/health  # orchestrator
curl http://localhost:8002/health  # feature-dev
# etc.
```

### Remote Deployment (DigitalOcean)

```bash
# From local machine
./scripts/deploy.ps1 -Target remote

# Or manually on droplet
ssh do-mcp-gateway
cd /opt/Dev-Tools
git pull
docker-compose build
docker-compose down
docker-compose up -d
```

## Troubleshooting

### Provider Not Working

1. Check API key is set in `.env`:
   ```bash
   grep -E "CLAUDE_API_KEY|MISTRAL_API_KEY|OPEN_AI_DEVTOOLS_KEY" config/env/.env
   ```

2. Test provider connectivity:
   ```bash
   LLM_PROVIDER=claude python scripts/test_llm_provider.py
   ```

3. Check agent logs:
   ```bash
   docker-compose logs orchestrator | grep -i "provider\|langchain"
   ```

### Langfuse Tracing Not Working

1. Verify Langfuse keys in `.env`:
   ```bash
   grep LANGFUSE config/env/.env
   ```

2. Check callback handler initialization:
   ```bash
   docker-compose logs orchestrator | grep -i langfuse
   ```

3. Verify traces at: https://us.cloud.langfuse.com

### Import Errors

If you see `ModuleNotFoundError: No module named 'langchain_anthropic'`:

1. Ensure dependencies are in `requirements.txt`:
   ```bash
   cat agents/orchestrator/requirements.txt | grep -E "anthropic|mistral"
   ```

2. Rebuild container:
   ```bash
   docker-compose build orchestrator
   docker-compose up -d orchestrator
   ```

## Best Practices

1. **Start with Gradient**: Use Gradient AI by default for cost efficiency
2. **Upgrade selectively**: Override to Claude/GPT-4 only for critical tasks
3. **Configure all keys**: Keep all API keys in `.env` for flexibility
4. **Test before deploy**: Run `test_llm_provider.py --all` before production deployment
5. **Monitor costs**: Use Langfuse traces to track token usage per provider
6. **Use embeddings wisely**: Stick with Gradient/OpenAI for embeddings (Claude/Mistral don't support them)

## FAQs

**Q: Can I use different providers for different agents?**  
A: Yes! Override the provider parameter in `get_llm()` calls.

**Q: Do I need all API keys configured?**  
A: No, only configure keys for providers you want to use. Others will gracefully fail with warnings.

**Q: Will traces work with all providers?**  
A: Yes, Langfuse automatically traces all LangChain LLM calls regardless of provider.

**Q: Can I change providers without rebuilding containers?**  
A: Yes, just update `LLM_PROVIDER` in `.env` and restart: `docker-compose restart`

**Q: What happens if API key is missing?**  
A: The agent logs a warning and returns `None` for the LLM instance. Your code should check for `None` before using.

## See Also

- [Architecture Snapshot](ARCHITECTURE.md)
- [Langfuse Tracing Guide](LANGFUSE_TRACING.md)
- [Gradient Quick Start](GRADIENT_QUICK_START.md)
- [Agent Endpoints](AGENT_ENDPOINTS.md)
