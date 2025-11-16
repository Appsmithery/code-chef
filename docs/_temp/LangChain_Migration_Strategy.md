# **Dev-Tools LangGraph Migration Plan**

**Version:** 2.0  
**Date:** 2025-11-16  
**Status:** Draft - Ready for Review

## Executive Summary

**Problem:** Current Docker/FastAPI architecture creates excessive operational overhead with 11 containers (6 agents + 5 infrastructure services), custom HTTP coordination, and brittle service mesh causing deployment failures and maintenance complexity.

**Solution:** Migrate to LangGraph-based architecture with unified state management, native LangChain tool integration, and simplified deployment model.

**Impact:**

- **Reduce containers:** 11 → 4 (LangGraph API + Qdrant + PostgreSQL + Redis)
- **Eliminate complexity:** Remove custom HTTP routing, manual state persistence, 6 separate agent codebases
- **Preserve capabilities:** Maintain all 150+ MCP tools, Gradient AI integration, Linear SDK, Qdrant RAG
- **Enable future growth:** A2A/AG-UI protocols for IDE integration, standardized agent communication

---

## Current Architecture Assessment

### Existing Stack (Phase 7 Complete)

**Containers (11 total):**

1. `gateway-mcp:8000` - Linear OAuth gateway (Node.js)
2. `orchestrator:8001` - Task routing (FastAPI)
3. `feature-dev:8002` - Code generation (FastAPI)
4. `code-review:8003` - Quality checks (FastAPI)
5. `infrastructure:8004` - IaC generation (FastAPI)
6. `cicd:8005` - Pipeline automation (FastAPI)
7. `documentation:8006` - Doc generation (FastAPI)
8. `rag-context:8007` - Qdrant interface (FastAPI)
9. `state-persistence:8008` - PostgreSQL interface (FastAPI)
10. `qdrant:6333,6334` - Vector database
11. `postgres:5432` - Relational database

**Key Components:**

- **Agent Framework:** FastAPI with custom HTTP routing via `AGENT_ENDPOINTS` dict
- **MCP Integration:** Direct stdio transport via `agents/_shared/mcp_tool_client.py` (subprocess-based Docker MCP Toolkit invocation)
- **LLM Inference:** DigitalOcean Gradient AI via custom `gradient_client.py` (Gradient SDK wrapper)
- **Observability:** Langfuse tracing (automatic via Gradient SDK) + Prometheus metrics
- **State Management:** Manual task registry + PostgreSQL persistence via HTTP POST to state-persistence service
- **Tool Access:** 150+ tools across 17 MCP servers (memory, rust-filesystem, gitmcp, playwright, notion, dockerhub, etc.)

**Pain Points:**

- **Service Mesh Fragility:** HTTP coordination between 9 services causes cascading failures
- **State Synchronization:** Manual task_registry dict + async POST to state-persistence service creates consistency issues
- **Deployment Complexity:** 11 container builds, 6 separate Dockerfiles, volume mounts, network configuration
- **Tool Invocation Overhead:** subprocess Docker calls per tool invocation (50-100ms latency)
- **Manual Routing:** Rule-based `decompose_request()` fallback when LLM unavailable

---

## Target Architecture

### Design Principles

1. **Unified Graph Execution:** Replace 6 FastAPI agents with single LangGraph application
2. **Native Tool Integration:** Use `langchain-mcp-adapters` to maintain MCP tool compatibility
3. **Preserve Infrastructure:** Keep Qdrant, PostgreSQL, Redis for state/vector storage
4. **Gradient AI Compatibility:** Wrap existing `gradient_client.py` as LangChain LLM provider
5. **Incremental Migration:** Agents convert to graph nodes with minimal code changes

### New Stack (Post-Migration)

**Containers (4 total):**

1. `langgraph-api:8123` - Unified agent graph (Python/LangGraph)
2. `qdrant:6333` - Vector database (unchanged)
3. `postgres:5432` - State persistence (unchanged)
4. `redis:6379` - LangGraph checkpoint storage (new)

**Eliminated Services:**

- ❌ gateway-mcp (Linear OAuth handled by Python SDK)
- ❌ orchestrator (becomes graph router node)
- ❌ 5 specialized agents (become graph nodes)
- ❌ rag-context wrapper (direct Qdrant via LangChain)
- ❌ state-persistence wrapper (LangGraph native checkpointing)

**Key Changes:**

- **Agent Coordination:** HTTP POST → LangGraph StateGraph edges
- **State Management:** Manual registry + HTTP → LangGraph PostgresSaver
- **MCP Tools:** subprocess Docker → langchain-mcp-adapters (persistent connections)
- **LLM Integration:** Custom Gradient wrapper → LangChain ChatOpenAI (compatible with DO Gradient)
- **Routing:** Rule-based + optional LLM → LangGraph conditional edges

### Service Migration Matrix

| Legacy Component                                                        | Graph-Era Replacement                                        | Migration Notes                                                                                                                                                                    |
| ----------------------------------------------------------------------- | ------------------------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `orchestrator` FastAPI app                                              | `StateGraph` entry point + `route_task` node                 | Collapse `agents/orchestrator/main.py` into a LangGraph builder that emits deterministic routes per DigitalOcean’s LangGraph playbooks, then delete the HTTP hop entirely.^2       |
| `feature-dev`, `code-review`, `infrastructure`, `cicd`, `documentation` | LangGraph node functions                                     | Lift existing business logic into node modules (e.g., `nodes/feature_dev.py`) that accept `AgentState`, reuse the same Gradient model IDs, and return structured message deltas.^1 |
| `rag-context` wrapper                                                   | `rag_retrieval` node                                         | Replace the REST shim with direct `QdrantVectorStore` calls tied to the shared state payload; continue using DigitalOcean-friendly embeddings + search patterns.^1                 |
| `state-persistence` FastAPI layer                                       | `langgraph.checkpoint.postgres.PostgresSaver` + Redis broker | Wire LangGraph’s checkpoint + replay subsystem into the existing Postgres + Redis pair recommended by LangSmith’s standalone server guide so threads survive restarts.^5           |
| `gateway-mcp` service                                                   | `langchain-mcp` toolkit bindings                             | Load the 17 MCP servers with `langchain_mcp` toolkits so each node can call tools without spawning Docker sidecars.[^22]                                                           |

### State & Persistence Contracts

- **Primary store:** Point `langgraph.checkpoint.postgres.PostgresSaver` at the existing `postgres:5432` DSN so every graph run records checkpoints, artifacts, and resumable threads.^5 Because the LangSmith deployment docs require `DATABASE_URI` + `LANGSMITH_API_KEY`, mirror that `.env` layout for parity between local and droplet targets.
- **Streaming broker:** Reuse the stack’s Redis instance (or add the lightweight `redis:6` service already shown in the compose file) so `langgraph`’s streaming + background runs behave exactly like the LangSmith reference implementation.^5
- **State schema:** Promote the TypedDict shown below into `agents/langgraph/state.py`, keeping `messages` append-only, `rag_context` as a reducer-friendly list, and `mcp_tools_used` as a deduplicated array. This mirrors the DigitalOcean tutorials’ emphasis on explicit state objects for each node transition.^2
- **Step tracking:** Adopt the step-id execution contract from Balaji Kithiganahalli’s LangGraph CoT article so retries, forks, and human-in-the-loop overrides remain traceable across Redis/Postgres checkpoints.^20

### Phase 1: Convert Agents to LangGraph Nodes

**Replace FastAPI orchestration with LangGraph StateGraph**:
Each of your current agents becomes a LangGraph node within a unified graph architecture. The orchestrator agent transforms into the graph execution engine itself.[^2][^5]

```python
from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage, AIMessage
from typing import TypedDict, Annotated
import operator

# Define shared state (replaces your HTTP state passing)
class AgentState(TypedDict):
    messages: Annotated[list, operator.add]
    task_description: str
    current_agent: str
    rag_context: list
    mcp_tools_used: list
    linear_issue_id: str
```

**Transform each specialized agent** from a FastAPI service to a LangGraph node function:

```python
async def feature_dev_node(state: AgentState):
    """Previously: agents/feature-dev/main.py FastAPI service"""
    # Reuse your existing gradient_client.py
    from agents._shared.gradient_client import GradientClient
    from agents._shared.mcp_tool_client import MCPToolClient

    llm = GradientClient(model="codellama-13b-instruct")
    mcp_client = MCPToolClient()  # Keeps your stdio transport

    # Your existing agent logic here
    response = await llm.generate(state["messages"])
    tools_called = await mcp_client.invoke_tools(response.tool_calls)

    return {
        "messages": [response],
        "mcp_tools_used": tools_called,
        "current_agent": "feature-dev"
    }
```

**Build the orchestration graph** (replaces your HTTP router):

```python
workflow = StateGraph(AgentState)

# Add nodes (your 5 specialized agents)
workflow.add_node("feature_dev", feature_dev_node)
workflow.add_node("code_review", code_review_node)
workflow.add_node("infrastructure", infrastructure_node)
workflow.add_node("cicd", cicd_node)
workflow.add_node("documentation", documentation_node)

# Define routing logic (replaces config/routing/task-router.rules.yaml)
def route_task(state: AgentState):
    """Intelligent routing based on task description"""
    if "feature" in state["task_description"].lower():
        return "feature_dev"
    elif "review" in state["task_description"].lower():
        return "code_review"
    # etc.

workflow.add_conditional_edges(
    "feature_dev",
    route_task,
    {
        "code_review": "code_review",
        "documentation": "documentation",
        END: END
    }
)

app = workflow.compile()
```

This eliminates 6 separate Docker containers and consolidates to a single LangGraph application.[^6][^5]

**Action steps (Week 1):**

1. Create `agents/langgraph/state.py` with the TypedDict above and reducers for `messages`, `rag_context`, and `mcp_tools_used`, then add pydantic validators so every node receives consistent payloads.^2
2. Carve each FastAPI agent into `agents/langgraph/nodes/<agent>.py` functions that import the existing `gradient_client` + `mcp_tool_client` helpers; ensure every node returns `{"messages": [...], "current_agent": "feature-dev"}` so downstream routing conditions have deterministic keys.^1
3. Register the nodes inside `agents/langgraph/workflow.py`, mirroring the `workflow.add_node` and `add_conditional_edges` calls above. Keep the routing logic simple (keyword or tag based) until the new LangGraph orchestrator can be driven by LLM-based decompositions.^2
4. Capture trace metadata (task_id, agent_name) in the returned state so the Langfuse hooks already wired into `gradient_client` continue emitting per-step spans once the graph is running.^6

✅ **Scaffolding status:** `agents/langgraph/state.py`, node stubs under `agents/langgraph/nodes/`, and the initial router defined in `agents/langgraph/workflow.py` now exist inside the repo. Use `invoke_workflow()` to smoke-test the routing heuristics while richer node logic is being ported.

### Phase 2: Implement A2A Protocol for Agent Communication

**A2A enables standardized agent-to-agent communication**. Instead of HTTP endpoints between agents, implement A2A message passing:[^3][^4][^7]

**Install dependencies**:

```bash
pip install a2a-python langgraph langchain-mcp-adapters
```

**Wrap your LangGraph agents as A2A-compliant services**:[^4]

```python
from a2a import A2AServer, TaskState, MessageSendParams
from langgraph.graph import StateGraph

class FeatureDevA2AAgent:
    def __init__(self):
        self.graph = self._build_langgraph()

    def _build_langgraph(self):
        # Your LangGraph workflow
        workflow = StateGraph(AgentState)
        # ... node definitions
        return workflow.compile()

    async def handle_message(self, params: MessageSendParams, task: TaskState):
        """A2A message handler"""
        query = self._get_user_query(params)

        # Invoke LangGraph
        result = await self.graph.ainvoke({
            "messages": [HumanMessage(content=query)],
            "task_description": task.description
        })

        return {
            "response": result["messages"][-1].content,
            "state": result
        }

# Expose as A2A server
server = A2AServer(
    agent=FeatureDevA2AAgent(),
    port=8002,
    agent_card={
        "name": "feature-dev",
        "capabilities": ["code_generation", "testing_setup"]
    }
)
```

**Enable inter-agent delegation**:[^8]
With A2A, your orchestrator can delegate to specialized agents without knowing implementation details:

```python
from a2a import A2AClient

# In your orchestrator LangGraph node
async def orchestrator_node(state: AgentState):
    # Discover available agents via A2A
    feature_dev_client = A2AClient("http://feature-dev-agent:8002/a2a")

    # Delegate sub-task using A2A protocol
    response = await feature_dev_client.send_message({
        "content": state["task_description"],
        "context": state["rag_context"]
    })

    return {"messages": [response]}
```

**Action steps (Week 2-3):**

1. Generate an A2A agent card per service using the schema from the Currency Agent tutorial so capabilities, tags, and auth expectations are explicit for IDE clients.^4
2. Wrap the LangGraph workflow with `A2AServer` instances that forward `message/send` and `message/stream` events to `graph.ainvoke` so streaming updates bubble back to the caller; reuse the tutorial’s `TaskStore` helpers until the Redis/Postgres-backed store is ready.^4
3. Teach the orchestrator node to call `A2AClient` for any tasks it decides to delegate externally (e.g., calling an infra agent that still runs as a separate process) so hybrid deployments remain possible during the migration.^7
4. Use the built-in streaming hooks (`process_streaming_agent_response`) from the tutorial to map LangGraph streamed events onto the existing VS Code UX, which keeps feature-dev feedback loops sub-2s even when long-running MCP tools execute.^4

### Phase 3: Integrate AG-UI Protocol for IDE Orchestration

**AG-UI enables real-time interaction between your IDE agent (Cline/Copilot) and backend LangGraph agents**.[^9][^10][^11]

**Architecture pattern**:

```
Cline/Copilot (VS Code)
  ↓ [AG-UI Protocol]
CopilotKit Runtime
  ↓ [A2A Messages]
LangGraph Orchestrator
  ↓ [A2A Messages]
Specialized Sub-Agents (Feature-Dev, Code-Review, etc.)
```

**Install AG-UI dependencies**:

```bash
pip install ag-ui pydantic-ai  # Python SDK
npm install @ag-ui/client @copilotkit/runtime  # For frontend bridge
```

**Create AG-UI bridge service**:[^11][^12]

```typescript
// services/ag-ui-bridge/route.ts (Next.js API route)
import { CopilotRuntime, ExperimentalEmptyAdapter } from "@copilotkit/runtime";
import { HttpAgent } from "@ag-ui/client";

const runtime = new CopilotRuntime({
  agents: [
    new HttpAgent({
      name: "langgraph-orchestrator",
      url: "http://langgraph-api:8123/a2a", // Your LangGraph A2A endpoint
    }),
  ],
});

export async function POST(req: NextRequest) {
  const { handleRequest } = copilotRuntimeNextJSAppRouterEndpoint({
    runtime,
    serviceAdapter: new ExperimentalEmptyAdapter(),
    endpoint: "/api/copilotkit",
  });
  return handleRequest(req);
}
```

**Configure Cline to communicate with AG-UI bridge**:
Create `.vscode/settings.json`:

```json
{
  "cline.apiEndpoint": "http://localhost:3000/api/copilotkit",
  "cline.agentProtocol": "ag-ui"
}
```

Now Cline can coordinate your 5 specialized agents through the AG-UI → A2A → LangGraph pipeline.[^9][^11]

**Action steps (Week 3-4):**

1. Scaffold `services/ag-ui-bridge/` using the CopilotKit runtime snippet shown above so the VS Code extension only needs a single `/api/copilotkit` endpoint to reach every LangGraph node.^11
2. Add the AG-UI FastAPI middleware (`add_adk_fastapi_endpoint`) to the LangGraph container so you can expose both A2A and AG-UI transports without duplicating business logic.^11
3. Wire `useCoAgent` shared state hooks into the existing frontend preview (docs portal) to prove that agent state (e.g., generated docs, Terraform) can stream into arbitrary UIs before the final IDE rollout.^11
4. Document the expected `agent` identifiers (`feature-dev`, `code-review`, etc.) in `docs/AGENT_ENDPOINTS.md` so IDE clients know how to pick the right backend when multiple graphs are running.^9

### Phase 4: Maintain Qdrant RAG Integration

**LangGraph integrates seamlessly with your existing Qdrant setup**:[^2]

```python
from langchain_qdrant import QdrantVectorStore
from langchain_openai import OpenAIEmbeddings  # Use with DigitalOcean Gradient

# Reuse your existing Qdrant configuration
vectorstore = QdrantVectorStore(
    client=qdrant_client,  # Your existing client from rag-context service
    collection_name="the-shop",
    embedding=OpenAIEmbeddings(
        base_url=os.getenv("GRADIENT_BASE_URL"),
        api_key=os.getenv("GRADIENT_API_KEY")
    )
)

# Add RAG retrieval node to LangGraph
def rag_retrieval_node(state: AgentState):
    """Replaces your rag-context service (port 8007)"""
    docs = vectorstore.similarity_search(
        state["task_description"],
        k=5
    )

    return {
        "rag_context": [doc.page_content for doc in docs],
        "messages": [AIMessage(content=f"Retrieved {len(docs)} context docs")]
    }

workflow.add_node("rag_retrieval", rag_retrieval_node)
```

**Action steps (Week 4):**

1. Move the existing Qdrant credentials from `rag-context` into LangGraph settings (`QDRANT_URL`, `QDRANT_API_KEY`) and confirm similarity search latency stays under 150 ms on the DigitalOcean Droplet described in the local-agent tutorial.^1
2. Introduce a `vectorstore` dependency in each node that needs retrieval so future sub-graphs (e.g., doc generation) can opt-in without duplicating connectors.^2
3. Backfill RAG telemetry by logging `docs_retrieved`, `collection_name`, and `query_tokens` into Prometheus before the FastAPI wrappers are retired; this maintains the observability dashboards during the cutover.^6
4. Add regression tests exercising the top 5 MCP tools that depend on retrieved context (git, filesystem, memory) to ensure the new node surfaces data identically to the old microservice.^1

### Phase 5: Docker \& Digital Ocean Deployment

**Simplified Docker Compose** (consolidates 6 agent containers → 1 LangGraph container):[^5]

```yaml
services:
  # Single LangGraph application (replaces orchestrator + 5 agents)
  langgraph-api:
    image: ${DOCR_REGISTRY}/langgraph-app:${IMAGE_TAG}
    build:
      context: .
      dockerfile: Dockerfile
    ports:
      - "8123:8000" # LangGraph API
    environment:
      - REDIS_URI=redis://redis:6379
      - DATABASE_URI=postgres://admin:changeme@postgres:5432/devtools
      - QDRANT_URL=http://qdrant:6333
      - GRADIENT_API_KEY=${GRADIENT_API_KEY}
      - LANGSMITH_API_KEY=${LANGSMITH_API_KEY} # For observability
    depends_on:
      - redis
      - postgres
      - qdrant
    networks:
      - devtools-network

  # Keep existing infrastructure
  qdrant:
    image: qdrant/qdrant:latest
    # ... your existing config

  postgres:
    image: postgres:16-alpine
    # ... your existing config

  redis:
    image: redis:6
    # ... for LangGraph state persistence

  # AG-UI bridge (optional - for IDE integration)
  ag-ui-bridge:
    image: ${DOCR_REGISTRY}/ag-ui-bridge:${IMAGE_TAG}
    build:
      context: ./ag-ui-bridge
    ports:
      - "3000:3000"
    environment:
      - LANGGRAPH_API_URL=http://langgraph-api:8123
    depends_on:
      - langgraph-api
```

**Dockerfile for LangGraph deployment**:[^13][^5]

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install LangGraph CLI
RUN pip install langgraph-cli

# Copy your application
COPY agents/ /app/agents/
COPY config/ /app/config/
COPY requirements.txt /app/

RUN pip install -r requirements.txt

# Build LangGraph application
RUN langgraph build

EXPOSE 8000

CMD ["langgraph", "serve", "--port", "8000"]
```

**Action steps (Week 5):**

1. Mirror the LangSmith standalone server `.env` contract (`REDIS_URI`, `DATABASE_URI`, `LANGSMITH_API_KEY`, `LANGGRAPH_CLOUD_LICENSE_KEY`) so the same container image can run locally, in CI, or on the production Droplet.^5
2. Add a `scripts/deploy_langgraph.ps1` wrapper that builds the LangGraph image with `langgraph build`, pushes to DOCR, and updates the compose stack—matching the workflow from `scripts/deploy.ps1` to minimize operator retraining.^18
3. Validate that `curl :8123/ok` responds with `{ "ok": true }` inside CI (following the LangSmith doc) before tagging a release; this collapses the former nine-container health checks into a single probe.^5
4. Update `compose/docker-compose.yml` to remove the retired FastAPI services once the LangGraph container is healthy for 72h, then archive their Dockerfiles for reference.

### Phase 6: MCP Integration Strategy

**Maintain your existing MCP toolkit** using LangChain adapters:[^8]

```python
from langchain_mcp_adapters import load_mcp_tools

# Load MCP servers (keeps your stdio transport)
mcp_tools = await load_mcp_tools([
    "mcp_server_memory",
    "mcp_server_filesystem",
    "mcp_server_git",
    # ... your 17 MCP servers from config
])

# Bind to LangGraph nodes
llm_with_tools = llm.bind_tools(mcp_tools)

def agent_node(state: AgentState):
    response = llm_with_tools.invoke(state["messages"])
    return {"messages": [response]}
```

**Action steps (Week 6):**

1. Replace the Docker-in-Docker invocation path inside `mcp_tool_client.py` with `langchain_mcp.MCPToolkit` sessions that stay warm across graph runs, as recommended by the PyPI package docs.^22
2. Store MCP connection metadata (server path, allowed directories, auth) in `config/mcp-agent-tool-mapping.yaml` so nodes can lazily load only the tools they need rather than binding all 150+ servers at startup.^8
3. Add smoke tests that stream from the LangGraph API while invoking high-latency MCP tools (e.g., Playwright) to confirm the new streaming stack (Redis + AG-UI) surfaces intermediate ToolMessages, matching the GoPenAI reference pattern.^20
4. Update the AG-UI bridge to surface MCP tool availability in its `agent_card` payload so IDE clients can prompt users before invoking privileged tools (filesystem, git, etc.).^11

### Migration Benefits

**Architectural simplification**:

- **From 6 Docker containers → 1 LangGraph container** (80% infrastructure reduction)[^5]
- **HTTP coordination → Graph-based execution** (eliminates custom routing logic)
- **Manual state management → LangGraph checkpointing** (built-in durability)[^14]

**Enhanced capabilities**:

- **A2A protocol**: Standardized agent communication, enabling future integration with external agents[^7][^3]
- **AG-UI protocol**: Direct IDE agent coordination via Cline/Copilot[^11][^9]
- **LangGraph observability**: Native LangSmith tracing replaces custom Prometheus metrics[^6]
- **Streaming support**: Real-time agent output to IDE[^4]

**Preserved infrastructure**:

- **Qdrant vector store**: Continues functioning with LangChain integration
- **Docker/Digital Ocean**: Same deployment model, simpler compose file
- **MCP tools**: Maintained via `langchain-mcp-adapters`
- **PostgreSQL**: Used by LangGraph for state persistence

### Validation & Rollout Checklist

- **Graph unit tests:** Exercise every node with fixtures that include MCP tool responses, RAG payloads, and Linear issue metadata so state transitions stay deterministic as advised in the DigitalOcean LangGraph tutorials.^2
- **Streaming smoke tests:** Replay the A2A Currency Agent streaming scenario against the new orchestrator to confirm SSE chunks arrive in order and the IDE never blocks while MCP tools run.^4
- **AG-UI UX tests:** Use CopilotKit’s `useCoAgent` hook to verify that shared state mirrors the LangGraph checkpoints, ensuring proverbs/docs/theme data flows bi-directionally before exposing the bridge to all developers.^11
- **Observability probes:** Keep the LangSmith-style `/ok` and Langfuse traces enabled; validate that each MCP run emits task_id + step_id metadata so regressions surface quickly.^5
- **Deployment drills:** Recreate the Droplet from scratch using the new compose file, then restore checkpoints from Postgres snapshots to prove disaster recovery no longer depends on the retired FastAPI services.^18

### Actionable Backlog

| Week | Focus                   | Deliverables                                                                  | Exit Criteria                                                                                 |
| ---- | ----------------------- | ----------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------- |
| 1    | Core LangGraph scaffold | Shared `AgentState`, node modules for feature-dev + code-review, router logic | `app.invoke` reproduces a happy-path feature task locally with MCP mocks.[^1][^2]             |
| 2    | A2A transport           | Agent cards, `A2AServer` wrappers, streaming event handlers                   | `message/send` + `message/stream` requests succeed with LangGraph results in Postman.[^4][^7] |
| 3    | AG-UI bridge            | CopilotKit runtime, FastAPI middleware, shared-state demo                     | VS Code + docs UI both stream intermediate outputs from LangGraph.[^9][^11]                   |
| 4    | RAG + telemetry         | `rag_retrieval` node, Prometheus counters, regression tests                   | Legacy RAG endpoints disabled; LangGraph node surfaces identical context snippets.[^1][^6]    |
| 5    | Containerization        | LangGraph Docker image, compose updates, DOCR push                            | `curl 0.0.0.0:8123/ok` passes in CI and on staging Droplet.[^5][^18]                          |
| 6    | MCP hardening           | `langchain-mcp` integration, tool smoke tests, AG-UI metadata updates         | Streaming MCP runs stay under SLA and IDE displays tool consent prompts.[^11][^20][^22]       |

### Recommended Implementation Order

1. **Week 1**: Convert one agent (Feature-Dev) to LangGraph node, test locally
2. **Week 2**: Build full LangGraph orchestration graph with routing logic
3. **Week 3**: Add A2A protocol wrappers around each specialized agent
4. **Week 4**: Implement AG-UI bridge for Cline/Copilot integration
5. **Week 5**: Docker containerization and Digital Ocean deployment
6. **Week 6**: Performance testing and cutover from FastAPI architecture

This migration maintains your cloud infrastructure while modernizing agent coordination with industry-standard protocols.[^1][^3][^4][^2][^5]
<span style="display:none">[^15][^16][^17][^18][^19][^20][^21]</span>

<div align="center">⁂</div>

[^1]: https://www.digitalocean.com/community/tutorials/local-ai-agents-with-langgraph-and-ollama
[^2]: https://www.digitalocean.com/community/tutorials/getting-started-agentic-ai-langgraph
[^3]: https://wandb.ai/byyoung3/Generative-AI/reports/How-the-Agent2Agent-A2A-protocol-enables-seamless-AI-agent-collaboration--VmlldzoxMjQwMjkwNg
[^4]: https://a2aprotocol.ai/blog/a2a-langraph-tutorial-20250513
[^5]: https://docs.langchain.com/langsmith/deploy-standalone-server
[^6]: https://forum.langchain.com/t/architecture-advice-for-self-hosted-langsmith-langgraph-platform-across-multiple-kubernetes-clusters/142
[^7]: https://a2a-protocol.org
[^8]: https://forum.langchain.com/t/feature-request-native-support-for-a2a-protocol-remote-agents-as-sub-graphs/1521
[^9]: https://docs.agentwire.io
[^10]: https://ai.pydantic.dev/ui/ag-ui/
[^11]: https://www.copilotkit.ai/blog/build-a-frontend-for-your-adk-agents-with-ag-ui
[^12]: https://dev.to/copilotkit/build-a-frontend-for-your-microsoft-agent-framework-agents-with-ag-ui-40ge
[^13]: https://www.youtube.com/watch?v=Gq3CPLOGHPw
[^14]: https://www.linkedin.com/pulse/open-source-vs-cloud-native-comparing-two-camps-ai-agent-raduta-3r08f
[^15]: https://www.youtube.com/shorts/GfhziN6sqms
[^16]: https://www.reddit.com/r/LangChain/comments/1k5mfam/what_are_possible_langgraph_patterns_for/
[^17]: https://www.linkedin.com/posts/ismgonza_s15-serve-an-a2a-server-to-a-langgraph-agent-activity-7391285594645110784-_rRa
[^18]: https://www.digitalocean.com/community/conceptual-articles/build-autonomous-systems-agentic-ai
[^19]: https://docs.ag-ui.com/sdk/js/client/overview
[^20]: https://blog.gopenai.com/from-text-to-action-implementing-computer-control-with-langgraph-and-chain-of-thought-ec368dcb03e5
[^21]: https://docs.langchain.com/langsmith/server-a2a
[^22]: https://pypi.org/project/langchain-mcp/
