Refactor the orchestrator to fully integrate LangGraph agent execution, replacing all stubs and consolidating execution paths. Follow these steps:

1. **Replace `DummyAgent` with real agents in `graph.py` node functions (lines 63-215):**

   - Update `feature_dev_node`, `code_review_node`, `infrastructure_node`, `cicd_node`, and `documentation_node` to use `agents.get_agent()` and invoke the agent with `BaseAgent.invoke()`.
   - Example:
     ```python
     agent = get_agent("feature-dev")
     response = await agent.invoke(state["messages"])
     ```

2. **Wire `supervisor_node` to `SupervisorAgent` in `graph.py` (lines 95-130):**

   - Import and use `SupervisorAgent` for task decomposition and routing, utilizing the actual LLM.

3. **Refactor `/execute/{task_id}` endpoint in `main.py` (lines 2017-2175):**

   - Remove HTTP microservice calls to `AGENT_ENDPOINTS`.
   - Invoke `compiled_workflow.ainvoke()` from `graph.py` with proper `WorkflowState` initialization.

4. **Consolidate execution endpoints in `main.py`:**

   - Migrate the `/orchestrate/langgraph` pattern (lines 2954-3028) into the main `/orchestrate` endpoint.
   - Deprecate `task_registry` in favor of LangGraph `thread_id` checkpointing.

5. **Integrate `WorkflowRouter` from `workflow_router.py`:**

   - Use `router.route_to_workflow()` to select between sequential, parallel, and HITL-gated execution patterns based on task complexity.

6. **Update the VS Code extension (`extensions/vscode-codechef/`):**
   - Call the unified LangGraph endpoint.
   - Handle `thread_id`-based status polling instead of `task_id`.

---

## Architecture Decisions

### 1. Checkpoint Storage: PostgreSQL Only (No Redis)

**Decision:** Use `PostgresSaver` exclusively for checkpoint persistence.

**Rationale:**

- Current scale (<50 concurrent workflows) doesn't warrant Redis complexity
- LangGraph's `PostgresSaver` has built-in connection pooling via `get_postgres_checkpointer()`
- ACID compliance ensures durability across orchestrator restarts
- Single database reduces operational overhead

**Future scaling path:** If latency becomes an issue at higher scale, add `cachetools` in-memory LRU cache for hot checkpoints before introducing Redis:

```python
from cachetools import TTLCache

class CachedCheckpointer:
    def __init__(self, postgres_saver: PostgresSaver, ttl_seconds: int = 300):
        self._postgres = postgres_saver
        self._cache = TTLCache(maxsize=500, ttl=ttl_seconds)

    async def get(self, thread_id: str):
        if thread_id in self._cache:
            return self._cache[thread_id]
        checkpoint = await self._postgres.aget(thread_id)
        self._cache[thread_id] = checkpoint
        return checkpoint
```

---

### 2. HITL Approval Node: Webhook + Polling Hybrid

**Decision:** Use Linear webhook as primary trigger with polling fallback for reliability.

**Rationale:**

- Linear webhooks are already configured (`config/linear/webhook-handlers.yaml`)
- Webhook provides <1 second latency after approval
- Polling catches missed webhooks (Linear outage, network blip)
- Existing `expires_at` logic in `approval_requests` table supports timeout handling

**Implementation:**

```python
# Primary path: Linear webhook handler in main.py
@app.post("/webhooks/linear/approval")
async def handle_linear_approval(request: Request):
    """Primary path: Linear calls this when approval emoji added"""
    payload = await verify_linear_webhook(request)
    if payload["action"] == "approved":
        request_id = extract_approval_request_id(payload)
        await resume_workflow_from_approval(request_id)

# Secondary path: Polling fallback in workflow_engine.py
async def poll_pending_approvals():
    """Fallback: runs every 30s to catch missed webhooks"""
    async with get_async_connection() as conn:
        pending = await conn.fetch("""
            SELECT id, thread_id, checkpoint_id
            FROM approval_requests
            WHERE status = 'approved' AND resumed_at IS NULL
            AND updated_at > NOW() - INTERVAL '5 minutes'
        """)
        for req in pending:
            await resume_workflow_from_checkpoint(req["thread_id"], req["checkpoint_id"])
```

**Graph node pattern using LangGraph interrupt:**

```python
from langgraph.prebuilt import interrupt

async def approval_node(state: MultiAgentWorkflowState) -> MultiAgentWorkflowState:
    """HITL gate - interrupts workflow for high-risk operations"""
    hitl = get_hitl_manager()
    risk = hitl.risk_assessor.assess_task(state["pending_operation"])

    if hitl.risk_assessor.requires_approval(risk):
        request_id = await hitl.create_approval_request(
            workflow_id=state["workflow_id"],
            thread_id=state["thread_id"],
            checkpoint_id=state.get("checkpoint_id", ""),
            task=state["pending_operation"],
            agent_name=state["current_agent"]
        )
        # LangGraph interrupt - saves state and exits
        interrupt({"approval_request_id": request_id, "risk_level": risk})

    return {**state, "approval_status": "approved"}
```

---

### 3. MCP Tool Binding: Invoke-Time with Caching

**Decision:** Bind tools dynamically during `BaseAgent.invoke()` based on task context, with LLM caching per tool configuration.

**Rationale:**

- Progressive tool loading reduces tokens from 150+ to 10-30 tools per request
- Task description enables intelligent filtering via `ProgressiveMCPLoader`
- Cache bound LLM per `(agent, strategy, tool_hash)` tuple to avoid repeated binding overhead

**Implementation in `base_agent.py`:**

```python
from functools import lru_cache
import hashlib

class BaseAgent:
    def __init__(self, ...):
        # ... existing init ...
        self._bound_llm_cache: Dict[str, BaseChatModel] = {}

    def _get_cache_key(self, tools: List[str]) -> str:
        """Create stable cache key from tool list"""
        tool_str = ",".join(sorted(tools))
        return hashlib.md5(tool_str.encode()).hexdigest()[:16]

    async def _bind_tools_for_task(self, task_description: str) -> BaseChatModel:
        """Bind tools dynamically based on task context"""
        if not self.tool_loader:
            return self.llm

        # Get relevant tools via progressive disclosure
        strategy = ToolLoadingStrategy[
            self.config["tools"].get("progressive_strategy", "MINIMAL")
        ]
        tools = await self.tool_loader.load_tools_for_task(
            task_description=task_description,
            strategy=strategy,
            allowed_servers=self.config["tools"].get("allowed_servers", [])
        )

        # Check cache
        cache_key = self._get_cache_key([t.name for t in tools])
        if cache_key in self._bound_llm_cache:
            return self._bound_llm_cache[cache_key]

        # Bind and cache
        bound_llm = self._gradient_client.get_llm_with_tools(
            tools=tools,
            temperature=self.config["agent"].get("temperature", 0.7),
            max_tokens=self.config["agent"].get("max_tokens", 2000)
        )
        self._bound_llm_cache[cache_key] = bound_llm
        return bound_llm

    @traceable(name="agent_invoke", tags=["agent", "subagent"])
    async def invoke(
        self,
        messages: List[BaseMessage],
        config: Optional[RunnableConfig] = None
    ) -> BaseMessage:
        # Extract task from messages for tool selection
        task_description = self._extract_task_description(messages)

        # Bind tools dynamically
        executor = await self._bind_tools_for_task(task_description)

        # Prepend system prompt
        if not messages or not isinstance(messages[0], SystemMessage):
            messages = [SystemMessage(content=self.get_system_prompt())] + messages

        return await executor.ainvoke(messages, config=config)

    def _extract_task_description(self, messages: List[BaseMessage]) -> str:
        """Extract task description from most recent HumanMessage"""
        for msg in reversed(messages):
            if isinstance(msg, HumanMessage):
                return msg.content[:500]  # Limit for tool matching
        return ""
```

---

## Decision Summary

| Decision           | Choice              | Key Benefit                     |
| ------------------ | ------------------- | ------------------------------- |
| Checkpoint storage | PostgreSQL only     | Simplicity, ACID durability     |
| HITL blocking      | Webhook + polling   | Fast resume, reliable fallback  |
| Tool binding       | Invoke-time + cache | Token efficiency, context-aware |

---

**Reference Documentation:**

- [LangGraph Documentation](https://langgraph.readthedocs.io/)
- [VS Code Extension API](https://code.visualstudio.com/api)
- Refer to `graph.py`, `main.py`, `workflow_router.py`, and agent implementations for code examples and architecture details.

Ensure all changes are self-contained, maintain the core intent, and follow the outlined architecture and workflow patterns.
