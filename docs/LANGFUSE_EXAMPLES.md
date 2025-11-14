# Example: Adding LLM Calls with Langfuse Tracing

This file demonstrates how to add LLM capabilities to agents with automatic Langfuse tracing.

## Simple OpenAI Call

```python
# agents/feature-dev/main.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from langfuse.openai import openai  # Drop-in replacement for OpenAI
from agents._shared.mcp_client import MCPClient

app = FastAPI()
mcp_client = MCPClient(agent_name="feature-dev")

class FeatureRequest(BaseModel):
    description: str
    requirements: list[str]

@app.post("/implement")
async def implement_feature(request: FeatureRequest):
    """Generate feature implementation using LLM with automatic Langfuse tracing."""

    # Build prompt
    prompt = f"""Design a solution for: {request.description}

Requirements:
{chr(10).join(f"- {req}" for req in request.requirements)}

Provide:
1. High-level design
2. Key files to create/modify
3. Test strategy
"""

    # LLM call - automatically traced by Langfuse
    response = openai.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are an expert software engineer."},
            {"role": "user", "content": prompt}
        ],
        name="feature-design",  # Identifies this call type in Langfuse
        metadata={
            "langfuse_session_id": f"feature-{request.description[:20]}",
            "langfuse_user_id": "feature-dev-agent",
            "langfuse_tags": ["feature-planning", "design"],
            "feature_type": "implementation"  # Custom metadata
        }
    )

    design = response.choices[0].message.content

    # Log to MCP memory server
    await mcp_client.log_event(
        event_type="feature_designed",
        metadata={
            "description": request.description,
            "design_length": len(design),
            "model": "gpt-4",
            "tokens": response.usage.total_tokens
        }
    )

    return {
        "design": design,
        "tokens_used": response.usage.total_tokens,
        "model": "gpt-4"
    }
```

## Multi-Step Workflow with Nested Traces

```python
from langfuse import observe
from langfuse.openai import openai

@observe()  # Creates parent span for entire workflow
async def full_feature_workflow(feature_spec: dict):
    """Complete feature implementation with nested LLM calls."""

    # Step 1: Design (traced as child span)
    design = await openai.chat.completions.create(
        model="gpt-4",
        messages=[...],
        name="design-architecture"
    )

    # Step 2: Generate code (traced as child span)
    code = await openai.chat.completions.create(
        model="gpt-4",
        messages=[...],
        name="generate-implementation"
    )

    # Step 3: Generate tests (traced as child span)
    tests = await openai.chat.completions.create(
        model="gpt-4",
        messages=[...],
        name="generate-tests"
    )

    return {"design": design, "code": code, "tests": tests}
```

Langfuse trace structure:

```
full_feature_workflow (parent)
├─ design-architecture (LLM call)
├─ generate-implementation (LLM call)
└─ generate-tests (LLM call)
```

## Advanced: Context Manager for Grouped Operations

```python
from langfuse import get_client, propagate_attributes
from langfuse.openai import openai

langfuse = get_client()

@app.post("/orchestrate")
async def orchestrate_task(request: TaskRequest):
    """Orchestrate workflow with shared trace attributes."""

    task_id = str(uuid.uuid4())

    # Create parent span for entire orchestration
    with langfuse.start_as_current_span(name="orchestrate-workflow") as span:
        # Set attributes that propagate to all child operations
        with propagate_attributes(
            user_id="orchestrator",
            session_id=task_id,
            tags=["orchestration", "workflow"]
        ):
            # Analyze task requirements
            analysis = await openai.chat.completions.create(
                model="gpt-4",
                messages=[...],
                name="analyze-requirements"
            )

            # Generate subtask plan
            plan = await openai.chat.completions.create(
                model="gpt-4",
                messages=[...],
                name="create-task-plan"
            )

            # All calls inherit session_id and tags automatically

        # Update trace with results
        span.update_trace(
            metadata={
                "task_id": task_id,
                "subtask_count": len(plan["subtasks"]),
                "estimated_duration": plan["estimated_minutes"]
            }
        )

    return {"task_id": task_id, "plan": plan}
```

## Streaming Responses with Token Tracking

```python
from langfuse.openai import openai

@app.post("/generate-code")
async def generate_code_streaming(request: CodeRequest):
    """Stream code generation with token usage tracking."""

    stream = openai.chat.completions.create(
        model="gpt-4",
        messages=[...],
        stream=True,
        stream_options={"include_usage": True},  # Get token usage from OpenAI
        name="code-generation-stream"
    )

    result = ""
    for chunk in stream:
        # Check for empty choices (token usage chunk)
        if chunk.choices:
            delta = chunk.choices[0].delta.content or ""
            result += delta
            # Stream to client here if needed

    # Langfuse automatically captures full conversation + token usage
    return {"code": result}
```

## Error Tracking

```python
from langfuse.openai import openai

@app.post("/review")
async def review_code(request: ReviewRequest):
    """Code review with automatic error capture."""

    try:
        response = openai.chat.completions.create(
            model="gpt-4",
            messages=[...],
            name="code-review-analysis"
        )
        return {"review": response.choices[0].message.content}

    except Exception as e:
        # Langfuse automatically captures:
        # - Exception type and message
        # - Stack trace
        # - Level = "error"
        # - Status message

        # Still re-raise for FastAPI error handling
        raise HTTPException(status_code=500, detail=str(e))
```

## Integration with MCP Tools

```python
from langfuse import observe
from langfuse.openai import openai
from agents._shared.mcp_client import MCPClient

mcp_client = MCPClient(agent_name="feature-dev")

@observe()  # Trace entire function
async def implement_with_mcp_tools(feature_spec: dict):
    """Combine LLM reasoning with MCP tool execution."""

    # LLM designs the implementation
    design = await openai.chat.completions.create(
        model="gpt-4",
        messages=[...],
        name="design-solution",
        metadata={"langfuse_tags": ["design", "planning"]}
    )

    # MCP tool creates files (logged to memory server)
    file_result = await mcp_client.invoke_tool(
        server="rust-mcp-filesystem",
        tool="write_file",
        params={
            "path": "src/feature.py",
            "content": design.choices[0].message.content
        }
    )

    # LLM generates tests
    tests = await openai.chat.completions.create(
        model="gpt-4",
        messages=[...],
        name="generate-tests",
        metadata={"langfuse_tags": ["testing", "generation"]}
    )

    # MCP tool writes test file
    test_result = await mcp_client.invoke_tool(
        server="rust-mcp-filesystem",
        tool="write_file",
        params={
            "path": "tests/test_feature.py",
            "content": tests.choices[0].message.content
        }
    )

    return {
        "design": design.choices[0].message.content,
        "files_created": ["src/feature.py", "tests/test_feature.py"],
        "tokens_used": design.usage.total_tokens + tests.usage.total_tokens
    }
```

Resulting trace in Langfuse:

```
implement_with_mcp_tools
├─ design-solution (LLM call - tracked by Langfuse)
│  ├─ Prompt: "Design a solution for..."
│  ├─ Completion: "Here's the implementation..."
│  ├─ Tokens: 1,234
│  └─ Cost: $0.0247
├─ mcp-tool.filesystem.write_file (logged to memory server)
├─ generate-tests (LLM call - tracked by Langfuse)
│  ├─ Prompt: "Generate tests for..."
│  ├─ Completion: "import pytest..."
│  ├─ Tokens: 856
│  └─ Cost: $0.0171
└─ mcp-tool.filesystem.write_file (logged to memory server)
```

## Shutdown Handler

```python
from contextlib import asynccontextmanager
from langfuse import get_client

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    yield
    # Shutdown - flush pending traces
    langfuse = get_client()
    langfuse.flush()

app = FastAPI(lifespan=lifespan)
```

## Environment-based Configuration

```python
import os
from langfuse import Langfuse

# Check if Langfuse is configured
LANGFUSE_ENABLED = bool(
    os.getenv("LANGFUSE_SECRET_KEY") and
    os.getenv("LANGFUSE_PUBLIC_KEY")
)

if LANGFUSE_ENABLED:
    # Use Langfuse-wrapped OpenAI
    from langfuse.openai import openai
else:
    # Fall back to standard OpenAI
    import openai
    print("Warning: Langfuse tracing disabled - no credentials found")

# Rest of agent code works the same way
```

## Next Steps

1. **Add LLM calls to agents**: Replace TODO placeholders with actual OpenAI API calls
2. **Deploy Langfuse server**: Use `docker-compose.yml` from `config/tracing-plan-v2.md`
3. **Configure credentials**: Set LANGFUSE\_\* env vars in `.env`
4. **Test tracing**: Make agent requests and verify traces in Langfuse UI
5. **Add Prometheus**: Export metrics from Langfuse for Grafana dashboards

## References

- [docs/LANGFUSE_TRACING.md](LANGFUSE_TRACING.md) - Full integration guide
- [config/tracing-plan-v2.md](../config/tracing-plan-v2.md) - Observability architecture
- [Langfuse OpenAI Docs](https://langfuse.com/docs/integrations/openai/python/get-started)
