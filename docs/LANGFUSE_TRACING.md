# Langfuse Tracing Integration

## Overview

All Dev-Tools agents are instrumented with **Langfuse** for automatic LLM observability. Langfuse provides:

- 📊 **Automatic tracing** of all OpenAI SDK calls
- ⏱️ **Latency tracking** for each LLM request
- 💰 **Token usage and cost** monitoring
- 🔍 **Prompt/completion visibility** in the Langfuse UI
- 🏷️ **Metadata tagging** for filtering and analysis

## Architecture

- **Drop-in replacement**: Agents use `from langfuse.openai import openai` instead of `import openai`
- **Zero code changes**: Existing OpenAI calls are automatically traced
- **Environment-based config**: Credentials passed via Docker Compose env vars
- **US Region default**: Points to `https://us.cloud.langfuse.com`

## Configuration

### 1. Environment Variables (Required)

Set these in your `.env` file or export to shell:

```bash
LANGFUSE_SECRET_KEY=sk-lf-51d46621-1aff-4867-be1f-66450c44ef8c
LANGFUSE_PUBLIC_KEY=pk-lf-7029904c-4cc7-44c4-a470-aa73f1e6a745
LANGFUSE_BASE_URL=https://us.cloud.langfuse.com
```

**Get your keys**: https://us.cloud.langfuse.com/

### 2. Docker Compose Integration

All agent services automatically receive Langfuse credentials:

```yaml
orchestrator:
  environment:
    - LANGFUSE_SECRET_KEY=${LANGFUSE_SECRET_KEY}
    - LANGFUSE_PUBLIC_KEY=${LANGFUSE_PUBLIC_KEY}
    - LANGFUSE_BASE_URL=${LANGFUSE_BASE_URL:-https://us.cloud.langfuse.com}
```

### 3. Agent Code Pattern

When agents make LLM calls (future enhancement):

```python
# Instead of: import openai
from langfuse.openai import openai

# Use OpenAI as normal - tracing happens automatically
response = openai.chat.completions.create(
    model="gpt-4",
    messages=[{"role": "user", "content": "Hello"}],
    name="agent-task",  # Optional: name for identification
    metadata={
        "langfuse_session_id": task_id,  # Group related calls
        "langfuse_user_id": "orchestrator",
        "langfuse_tags": ["task-routing"]
    }
)
```

## Features

### Automatic Tracking

Langfuse automatically captures:

- All prompts and completions (with streaming support)
- Model parameters (temperature, max_tokens, etc.)
- Latencies (time to first token, total duration)
- Token usage (prompt tokens, completion tokens, total)
- Cost in USD (based on model pricing)
- Errors and status codes

### Custom Metadata

Add context to traces for filtering and analysis:

```python
# Option 1: Via metadata parameter
response = openai.chat.completions.create(
    model="gpt-4",
    messages=[...],
    metadata={
        "langfuse_session_id": "workflow-123",
        "langfuse_user_id": "feature-dev-agent",
        "langfuse_tags": ["code-generation", "python"],
        "task_type": "feature_implementation",  # Custom metadata
        "priority": "high"
    }
)

# Option 2: Via span context managers
from langfuse import get_client

langfuse = get_client()
with langfuse.start_as_current_span(name="feature-workflow") as span:
    span.update_trace(
        session_id="workflow-123",
        user_id="feature-dev-agent",
        tags=["feature", "python"]
    )
    # All OpenAI calls in this context inherit these attributes
    response = openai.chat.completions.create(...)
```

### Decorator Pattern

Use `@observe()` decorator for automatic function tracing:

```python
from langfuse import observe
from langfuse.openai import openai

@observe()
async def implement_feature(feature_spec: dict):
    # All LLM calls nested under this span
    design = await openai.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": f"Design: {feature_spec}"}],
        name="design-feature"
    )

    code = await openai.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": f"Implement: {design}"}],
        name="generate-code"
    )

    return code
```

## Flushing Events

For short-lived scripts or shutdown handlers:

```python
from langfuse import get_client

# At app shutdown or script end
langfuse = get_client()
langfuse.flush()  # Ensure all events are sent before exit
```

FastAPI agents run continuously, so flushing is typically not needed.

## Debugging

Enable debug mode for troubleshooting:

```python
from langfuse import Langfuse

# Initialize with debug
langfuse = Langfuse(debug=True)
```

Or set environment variable:

```bash
export LANGFUSE_DEBUG=true
```

## Sampling

Control trace volume (useful for high-traffic production):

```bash
export LANGFUSE_SAMPLE_RATE=0.1  # Collect 10% of traces
```

## Disabling Tracing

Temporarily disable without code changes:

```bash
export LANGFUSE_TRACING_ENABLED=false
```

## Langfuse UI

Access your traces at: https://us.cloud.langfuse.com

**Dashboard features:**

- Real-time trace list with filtering
- Detailed trace views with nested spans
- Token usage and cost analytics
- Latency percentiles and distributions
- Prompt/completion comparison
- Custom metadata search
- Export to CSV/JSON

## Integration with MCP Tools

Langfuse tracing is complementary to MCP tool logging:

- **Langfuse**: Tracks LLM calls (prompts, completions, tokens, cost)
- **MCP Memory Server**: Stores task entities, relationships, and workflow state
- **Together**: Full observability from task creation → LLM reasoning → MCP tool usage → task completion

Example workflow trace:

```
Trace: "Implement user authentication"
├─ Span: orchestrator.plan_task (LLM call)
├─ Span: feature-dev.design_solution (LLM call)
├─ Span: feature-dev.generate_code (LLM call)
├─ Span: mcp-tool.filesystem.write_file (logged to memory)
├─ Span: code-review.analyze (LLM call)
└─ Span: mcp-tool.memory.create_entity (task completion)
```

## Roadmap

Future enhancements for Dev-Tools + Langfuse:

1. **Prometheus metrics export** from Langfuse API
2. **Grafana dashboards** for real-time monitoring
3. **Cost alerts** when token usage exceeds thresholds
4. **Prompt version tracking** for A/B testing
5. **Eval integration** with Langfuse's evaluation framework
6. **Custom scores** for code quality, test coverage, etc.

## References

- [Langfuse OpenAI Integration Docs](https://langfuse.com/docs/integrations/openai/python/get-started)
- [Langfuse Tracing Concepts](https://langfuse.com/docs/tracing)
- [Langfuse Python SDK Reference](https://langfuse.com/docs/sdk/python)
- [Dev-Tools Tracing Plan](../config/tracing-plan-v2.md)
