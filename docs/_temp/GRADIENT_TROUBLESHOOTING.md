# Gradient AI Integration Troubleshooting

**Date:** November 15, 2025  
**Status:** Deployment successful, final bug under investigation

## Overview

This document tracks the complete refactoring of our Gradient AI integration from an incorrect OpenAI SDK wrapper to the official Gradient SDK.

## Root Cause Analysis

### Original Issues

1. **Wrong SDK:** Using `langfuse.openai` OpenAI SDK wrapper pointing to non-existent `/v2/ai` endpoint
2. **Wrong Endpoint:** DigitalOcean Gradient has NO `/v2/ai` endpoint - returns 404
3. **Wrong Parameter:** OpenAI's `response_format` parameter not supported by Gradient SDK
4. **Wrong Model IDs:** Used `llama-3.1-8b-instruct` instead of `llama3-8b-instruct`

### API Architecture

DigitalOcean Gradient AI has **three separate client types**:

```python
# 1. Serverless Inference (what we need)
client = Gradient(model_access_key="sk-do-*")
response = client.chat.completions.create(
    model="llama3-8b-instruct",
    messages=[...]
)

# 2. Agentic Cloud API (for management)
client = Gradient(access_token="dop_v1-*")  # Uses DO PAT
agents = client.agents.list()

# 3. Agent Inference (for calling deployed agents)
client = Gradient(agent_access_key="...", agent_endpoint="...")
```

## Solutions Implemented

### 1. SDK Migration (agents/\_shared/gradient_client.py)

**Before:**

```python
from langfuse.openai import openai
client = openai.OpenAI(
    api_key=GRADIENT_API_KEY,
    base_url="https://api.digitalocean.com/v2/ai/v1"
)
```

**After:**

```python
from gradient import Gradient
client = Gradient(model_access_key=GRADIENT_MODEL_ACCESS_KEY)
# SDK handles endpoint internally
```

### 2. Removed Unsupported Parameters

**Issue:** `response_format` parameter not supported by Gradient SDK

**Solution:** Enhanced system prompt with JSON formatting instructions:

```python
json_instruction = "\n\nIMPORTANT: Respond ONLY with valid JSON. Do not include any text before or after the JSON object."
enhanced_system = (system_prompt or "") + json_instruction
```

### 3. Correct Model IDs

Discovered via API: `GET https://api.digitalocean.com/v2/gen-ai/models`

**Available Models:**

- `llama3-8b-instruct` (Llama 3.1 8B) ✅
- `llama3.3-70b-instruct` (Llama 3.3 70B)
- `openai-gpt-4o`, `openai-gpt-5`
- `anthropic-claude-sonnet-4`, `anthropic-claude-opus-4`
- `mistral-nemo-instruct-2407`
- `deepseek-r1-distill-llama-70b`

**Updated `.env`:**

```bash
GRADIENT_MODEL=llama3-8b-instruct  # Was: llama-3.1-8b-instruct
```

### 4. Dependencies Updated

Added to all 6 agent `requirements.txt`:

```
gradient>=1.0.0
```

### 5. Environment Variables Corrected

**docker-compose.yml** (all agent services):

```yaml
environment:
  - LANGFUSE_HOST=${LANGFUSE_HOST:-https://us.cloud.langfuse.com} # Not BASE_URL
  - GRADIENT_MODEL_ACCESS_KEY=${GRADIENT_MODEL_ACCESS_KEY} # Inference auth
  - GRADIENT_MODEL=${GRADIENT_MODEL:-llama3-8b-instruct} # Model name
  # Removed: GRADIENT_API_KEY (management PAT, not needed)
  # Removed: GRADIENT_BASE_URL (SDK handles internally)
```

## Current Status

✅ **Working:**

- Gradient SDK initializes correctly
- Model name validated (`llama3-8b-instruct` exists in catalog)
- Authentication successful (sk-do-\* model access key)
- No 404 routing errors
- Langfuse environment variables correct
- Rule-based fallback working

⚠️ **Outstanding Issue:**

**Error:** `unhashable type: 'dict'` when calling `gradient_client.complete_structured()`

**Location:** `agents/orchestrator/main.py:714`

**Context:**

```python
result = await gradient_client.complete_structured(
    prompt=user_prompt,
    system_prompt=system_prompt,
    temperature=0.3,
    max_tokens=1000,
    metadata={  # <-- Likely culprit
        "task_id": task_id,
        "task_description": request.description,
        "priority": request.priority
    }
)
```

**Hypothesis:**
The `metadata` parameter may be causing issues with Langfuse's automatic tracing or Gradient SDK's parameter validation. The dict might be getting passed somewhere that expects a hashable type.

## Next Steps

1. **Debug metadata parameter:**

   ```python
   # Option A: Remove metadata parameter entirely
   result = await gradient_client.complete_structured(
       prompt=user_prompt,
       system_prompt=system_prompt,
       temperature=0.3,
       max_tokens=1000
   )

   # Option B: Convert metadata to JSON string
   metadata=json.dumps({...})

   # Option C: Add to Langfuse session manually
   langfuse.update_current_trace(metadata={...})
   ```

2. **Add detailed error logging:**

   ```python
   try:
       result = await gradient_client.complete_structured(...)
   except Exception as e:
       logger.error(f"Gradient API error: {e}", exc_info=True)  # Full traceback
       raise
   ```

3. **Test with minimal call:**
   ```bash
   # In orchestrator container
   python3 -c "
   from agents._shared.gradient_client import get_gradient_client
   import asyncio
   gc = get_gradient_client('test', 'llama3-8b-instruct')
   result = asyncio.run(gc.complete('Test', max_tokens=10))
   print(result)
   "
   ```

## Testing Commands

```bash
# 1. Check environment variables in container
ssh root@45.55.173.72 "docker exec compose-orchestrator-1 env | grep GRADIENT"

# 2. Test orchestrator endpoint
curl -X POST http://45.55.173.72:8001/orchestrate \
  -H "Content-Type: application/json" \
  -d '{
    "description": "Create API rate limiter middleware",
    "project_context": {"language": "Python"},
    "priority": "high"
  }'

# 3. Check logs for errors
ssh root@45.55.173.72 "docker logs compose-orchestrator-1 --tail 50"

# 4. Verify Langfuse traces
# Visit: https://us.cloud.langfuse.com/project/cmhy56z2805aaad077jb3i7r0
# Look for traces with model=llama3-8b-instruct
```

## References

- **Gradient SDK Docs:** https://gradient-sdk.digitalocean.com/
- **API Reference:** https://docs.digitalocean.com/reference/api/digitalocean/#tag/GradientAI-Platform
- **Model Catalog:** `GET https://api.digitalocean.com/v2/gen-ai/models` (requires DO PAT)
- **Langfuse Docs:** https://langfuse.com/docs/integrations/openai

## Commits

1. `c9b3dfa` - Initial Gradient SDK migration
2. `40003f0` - Remove response_format parameter
3. _(pending)_ - Fix unhashable dict error

## Key Learnings

1. DigitalOcean Gradient is **not OpenAI-compatible** at HTTP level - requires official SDK
2. Three separate auth mechanisms: model_access_key (inference), access_token (management), agent_access_key (deployed agents)
3. Model IDs use different naming convention than expected (no dots/periods)
4. Langfuse integration is built into Gradient SDK but requires `LANGFUSE_HOST` env var
5. Fast 404 failures indicate routing issues before authentication check
