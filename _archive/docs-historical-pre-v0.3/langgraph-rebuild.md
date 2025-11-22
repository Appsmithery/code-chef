# **Recommended Architecture: Single Container, Multi-Agent Workflows**

## Core Insight from LangGraph

LangGraph supports **multi-agent systems** where each agent is a **node in a graph**, not a separate microservice. This preserves:

- ✅ Distinct agent configurations (LLM, tools, prompts)
- ✅ Independent agent evolution (swap models per agent)
- ✅ Multiple workflow routes (conditional edges)
- ✅ Agent-to-agent delegation (supervisor pattern)

### Architecture: Orchestrator with Embedded Agent Graph

**Container Structure (3 services):**

```
orchestrator/
├── main.py                    # FastAPI entry point
├── agents/                    # Agent node definitions
│   ├── supervisor.py          # Orchestrator LLM (routes tasks)
│   ├── feature_dev.py         # CodeLlama-13b + GitHub tools
│   ├── code_review.py         # Llama-3.1-70b + Sonar tools
│   ├── infrastructure.py      # Llama-3.1-8b + Terraform tools
│   ├── cicd.py               # Llama-3.1-8b + Jenkins tools
│   └── documentation.py       # Mistral-7b + Confluence tools
├── graph.py                   # LangGraph workflow definition
├── tools/                     # Tool configurations per agent
│   ├── feature_dev_tools.yaml
│   ├── code_review_tools.yaml
│   └── ...
└── models.py                  # Agent configuration models
```

### LangGraph Multi-Agent Pattern

```python
# graph.py
from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage

# Define workflow state
class WorkflowState(TypedDict):
    messages: list[HumanMessage]
    current_agent: str
    task_result: dict
    approvals: list[str]

# Create agent nodes
def feature_dev_node(state: WorkflowState):
    """Feature dev agent node with CodeLlama-13b"""
    agent = get_agent("feature-dev")  # Loads config from tools/feature_dev_tools.yaml
    result = agent.invoke(state["messages"])
    return {"messages": result, "task_result": result}

def code_review_node(state: WorkflowState):
    """Code review agent with Llama-70b"""
    agent = get_agent("code-review")
    result = agent.invoke(state["messages"])
    return {"messages": result, "task_result": result}

# Build graph
workflow = StateGraph(WorkflowState)

# Add agent nodes
workflow.add_node("supervisor", supervisor_node)
workflow.add_node("feature_dev", feature_dev_node)
workflow.add_node("code_review", code_review_node)
workflow.add_node("infrastructure", infrastructure_node)
workflow.add_node("cicd", cicd_node)
workflow.add_node("documentation", documentation_node)

# Conditional routing (supervisor decides next agent)
def route_to_agent(state: WorkflowState) -> str:
    """Supervisor LLM decides which agent to invoke next"""
    supervisor = get_agent("supervisor")
    routing_decision = supervisor.invoke([
        SystemMessage(content="Analyze task and route to appropriate agent"),
        HumanMessage(content=state["messages"][-1])
    ])
    return routing_decision.next_agent  # "feature_dev" | "code_review" | END

workflow.add_conditional_edges(
    "supervisor",
    route_to_agent,
    {
        "feature_dev": "feature_dev",
        "code_review": "code_review",
        "infrastructure": "infrastructure",
        "cicd": "cicd",
        "documentation": "documentation",
        "end": END
    }
)

# Agents report back to supervisor
workflow.add_edge("feature_dev", "supervisor")
workflow.add_edge("code_review", "supervisor")
workflow.add_edge("infrastructure", "supervisor")
workflow.add_edge("cicd", "supervisor")
workflow.add_edge("documentation", "supervisor")

workflow.set_entry_point("supervisor")
app = workflow.compile()
```

### Agent Configuration (Per-Agent Settings)

```yaml
# tools/feature_dev_tools.yaml
agent:
  name: feature-dev
  model: codellama-13b
  temperature: 0.7
  max_tokens: 2000
  system_prompt: |
    You are a senior Python developer specializing in feature development.
    Break down features into implementable tasks with clear acceptance criteria.

tools:
  progressive_strategy: MINIMAL
  allowed_servers:
    - github
    - filesystem
    - git
    - docker

langsmith:
  project: agents-feature-dev
  tags: [feature-development, code-generation]
```

```yaml
# tools/code_review_tools.yaml
agent:
  name: code-review
  model: llama-3.1-70b
  temperature: 0.3
  max_tokens: 4000
  system_prompt: |
    You are a code quality expert. Review code for security, performance, and maintainability.
    Provide actionable feedback with specific line references.

tools:
  progressive_strategy: AGENT_PROFILE
  allowed_servers:
    - github
    - sonarqube
    - git

langsmith:
  project: agents-code-review
  tags: [code-review, quality-assurance]
```

### Benefits of This Architecture

**1. Resource Efficiency (Single Container):**

- Before: 6 containers × 150MB = 900MB baseline
- After: 1 container = 150MB baseline
- **Memory savings: ~750MB (83% reduction)**

**2. Preserved Multi-Agent Capabilities:**

- ✅ **Distinct agent configs**: Each agent node loads own YAML (model, tools, prompt)
- ✅ **Independent LLM swapping**: Change CodeLlama → GPT-4 for feature-dev without affecting others
- ✅ **Tool isolation**: Progressive disclosure per agent (feature-dev gets GitHub, code-review gets SonarQube)
- ✅ **Multiple workflow routes**: Supervisor can route feature-dev → code-review → cicd (conditional edges)
- ✅ **Agent-to-agent delegation**: Supervisor pattern with LLM-powered routing decisions

**3. LangGraph Advantages:**

- **State management**: Workflow state persisted across agent transitions
- **Checkpointing**: Resume workflows after HITL approvals
- **Conditional routing**: LLM decides next agent based on task context
- **Human-in-the-loop**: Built-in approval nodes (interrupt graph, wait for Linear approval)
- **Observability**: LangSmith traces entire graph execution (all agents + routing decisions)

**4. Performance Improvements:**

- No HTTP serialization between agents (in-memory function calls)
- No network latency (agents communicate via graph state)
- Faster workflow execution (~50% reduction in total latency)
- Single Docker build (~5min vs 6× builds = 30min)

### Migration Path

**Phase 1: Create Agent Nodes (Week 1)**

```python
# agent_orchestrator/agents/feature_dev.py
from shared.lib.mcp_client import MCPClient
from shared.lib.gradient_client import get_gradient_client
from langchain_core.runnables import RunnableConfig

class FeatureDevAgent:
    def __init__(self, config_path: str):
        self.config = load_yaml(config_path)
        self.mcp = MCPClient(agent_name="feature-dev")
        self.llm = get_gradient_client(
            model_name=self.config["agent"]["model"],
            temperature=self.config["agent"]["temperature"]
        )
        self.tools = self.mcp.to_langchain_tools(
            self.config["tools"]["allowed_servers"]
        )
        self.agent = self.llm.bind_tools(self.tools)

    async def invoke(self, messages: list, config: RunnableConfig):
        """Execute agent with bound tools"""
        return await self.agent.ainvoke(messages, config=config)
```

**Phase 2: Build LangGraph Workflow (Week 1)**

- Create `graph.py` with supervisor + 5 agent nodes
- Add conditional routing based on task type
- Add HITL approval nodes (interrupt graph, wait for Linear notification)
- Add checkpointing for workflow resume

**Phase 3: Update Docker Compose (Week 1)**

```yaml
# deploy/docker-compose.yml
services:
  orchestrator:
    build: ./agent_orchestrator
    environment:
      - GRADIENT_MODEL=llama-3.1-70b # Supervisor model
      - MCP_GATEWAY_URL=http://gateway-mcp:8000
      - LANGSMITH_TRACING=true
    volumes:
      - ./agent_orchestrator/tools:/app/tools:ro
      - ./shared:/app/shared:ro

  # Remove 5 agent services (feature-dev, code-review, etc.)
```

**Phase 4: Test & Deploy (Week 2)**

- Test multi-agent workflows locally
- Verify tool isolation per agent
- Validate HITL approval flow with Linear notifications
- Deploy to droplet with single orchestrator container

### Example Multi-Agent Workflow

```python
# User: "Implement user authentication with OAuth2"

# 1. Supervisor receives task
supervisor_input = {
    "messages": [HumanMessage(content="Implement user authentication with OAuth2")],
    "current_agent": "supervisor"
}

# 2. Supervisor routes to feature-dev
routing_decision = supervisor.invoke(supervisor_input)
# → next_agent = "feature_dev"

# 3. Feature-dev creates implementation plan
feature_dev_result = feature_dev_agent.invoke({
    "messages": [HumanMessage(content="Create OAuth2 implementation plan")],
    "tools": ["github", "filesystem", "git"]
})
# → Returns: Implementation plan with 5 subtasks

# 4. Supervisor requests HITL approval (interrupt graph)
approval_required = supervisor.invoke(feature_dev_result)
# → Creates Linear sub-issue in DEV-68, waits for approval

# 5. After approval, supervisor routes to code-review
code_review_result = code_review_agent.invoke({
    "messages": [HumanMessage(content="Review OAuth2 implementation")],
    "tools": ["github", "sonarqube", "git"]
})
# → Returns: Review feedback with security recommendations

# 6. Supervisor routes to cicd for deployment
cicd_result = cicd_agent.invoke({
    "messages": [HumanMessage(content="Deploy OAuth2 to staging")],
    "tools": ["jenkins", "kubernetes", "terraform"]
})
# → Returns: Deployment status

# 7. Workflow complete
workflow_result = {"status": "complete", "agents_invoked": 3, "approvals": 1}
```

---

## Updated Recommendation: **Option D (LangGraph Multi-Agent in Single Container)**

**What We're Building:**

- ✅ **Single orchestrator container** (150MB baseline, down from 900MB)
- ✅ **6 distinct LangGraph agent nodes** (supervisor + 5 specialists)
- ✅ **Per-agent configuration** (YAML files for model, tools, prompts)
- ✅ **Conditional workflow routing** (supervisor decides next agent via LLM)
- ✅ **HITL approval nodes** (interrupt graph, Linear notifications, resume after approval)
- ✅ **Preserved multi-agent capabilities** (independent LLM swapping, tool isolation, multiple routes)

**What Gets Removed:**

- ❌ 5 FastAPI microservices (HTTP overhead eliminated)
- ❌ Qdrant vector DB (use PostgreSQL for state)
- ❌ Prometheus (use LangSmith + Docker stats)

**Expected Resource Usage:**

- Memory: ~300MB (orchestrator + gateway + postgres)
- CPU: ~0.3 avg (spikes to 1.5 during LLM calls)
- Disk: ~2GB (down from 22GB)

**Timeline:**

- Week 1: Implement agent nodes + LangGraph workflow
- Week 2: Test, deploy, validate on droplet
