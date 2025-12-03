# LangSmith Tracing Integration

## Overview

All Dev-Tools agents are instrumented with **LangSmith** for automatic LLM observability via LangChain's native tracing integration. LangSmith provides:

- 📊 **Automatic tracing** of all LangChain/LangGraph operations
- ⏱️ **Latency tracking** for each LLM request
- 💰 **Token usage and cost** monitoring
- 🔍 **Prompt/completion visibility** in the LangSmith UI
- 🏷️ **Metadata tagging** for filtering and analysis
- 🔄 **Workflow visualization** for LangGraph executions

## Dashboard Access

**Production Dashboard**: https://smith.langchain.com/o/5029c640-3f73-480c-82f3-58e402ed4207/projects/p/f967bb5e-2e61-434f-8ee1-0df8c22bc046

## Configuration

### Required Environment Variables

Set these in `config/env/.env`:

```bash
# Enable LangSmith tracing
LANGSMITH_TRACING=true
LANGCHAIN_TRACING_V2=true

# LangSmith connection
LANGCHAIN_ENDPOINT=https://api.smith.langchain.com
LANGCHAIN_PROJECT=agents

# API Keys (use service key for production)
LANGCHAIN_API_KEY=lsv2_sk_***
LANGSMITH_API_KEY=lsv2_sk_***

# Required for org-scoped service keys
LANGSMITH_WORKSPACE_ID=5029c640-3f73-480c-82f3-58e402ed4207
```

### Key Types

| Key Type       | Format      | Use Case                        |
| -------------- | ----------- | ------------------------------- |
| Service Key    | `lsv2_sk_*` | Production (org-level access)   |
| Personal Token | `lsv2_pt_*` | Development (user-level access) |

**Note**: Service keys require `LANGSMITH_WORKSPACE_ID` to be set.

## Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Orchestrator   │────▶│  LangChain       │────▶│  LangSmith      │
│  (LangGraph)    │     │  Callbacks       │     │  (Cloud)        │
└─────────────────┘     └──────────────────┘     └─────────────────┘
         │
         ▼
┌─────────────────┐
│  Agent Nodes    │
│  (feature_dev,  │
│  code_review,   │
│  etc.)          │
└─────────────────┘
```

- **Zero code changes**: LangChain automatically sends traces when `LANGCHAIN_TRACING_V2=true`
- **Environment-based config**: All credentials via environment variables
- **LangGraph integration**: Workflow graphs are visualized as nested traces

## Automatic Tracking

LangSmith automatically captures:

| Metric                | Description                         |
| --------------------- | ----------------------------------- |
| Prompts & completions | Full input/output text              |
| Model parameters      | Temperature, max_tokens, etc.       |
| Latencies             | Time to first token, total duration |
| Token usage           | Prompt tokens, completion tokens    |
| Cost                  | USD based on model pricing          |
| Errors                | Exception traces and status codes   |
| Workflow structure    | LangGraph node execution order      |

## LangGraph Workflow Visualization

LangGraph workflows appear as nested trace hierarchies:

```
Trace: "Process feature request"
├─ Span: router_node
├─ Span: supervisor_node (routing decision)
├─ Span: feature_dev_node
│   ├─ LLM Call: design solution
│   └─ LLM Call: generate code
├─ Span: code_review_node
│   └─ LLM Call: analyze code
└─ END
```

## Debugging

### Check if tracing is enabled

```bash
# On droplet
docker exec deploy-orchestrator-1 printenv | grep -E "LANG(CHAIN|SMITH)"
```

### View traces

1. Open https://smith.langchain.com
2. Select project "agents"
3. Filter by timeframe or metadata

### Enable debug mode

```bash
export LANGCHAIN_VERBOSE=true
```

## Disabling Tracing

Temporarily disable without code changes:

```bash
export LANGCHAIN_TRACING_V2=false
```

## Deployment Notes

After changing tracing configuration:

```bash
# Must recreate containers (restart won't reload .env)
docker compose down && docker compose up -d
```

## Related Documentation

- [LangSmith Official Docs](https://docs.smith.langchain.com/)
- [LangGraph Tracing](https://docs.smith.langchain.com/old/tracing/faq/logging_and_viewing#logging-traces-from-langgraph)
- [Copilot Instructions - LangSmith Section](../../.github/copilot-instructions.md#langsmith-llm-tracing)
