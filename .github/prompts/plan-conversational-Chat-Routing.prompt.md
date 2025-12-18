# Plan: Add Conversational Chat Support with /execute Gating

## Current Issue

1. When user sends a general query (like "hello"), the **supervisor routes to "end"**
2. The supervisor generates a `reasoning` message but it's filtered out in the streaming response (because it's from the "supervisor" node, not a specialist)
3. **The `conversational_handler_node` exists but is never called** - it's not wired into the graph
4. User receives **no response** because the workflow goes: `supervisor` → `end` (with no visible output)

## Design Goals

- **Conversational by default**: General queries get immediate, helpful responses
- **Task execution gated behind `/execute`**: Only `/execute` commands trigger specialized agents
- **Clear separation**:
  - Regular chat → `conversational_handler_node` (no tools, fast responses)
  - `/execute` → supervisor routing → specialized agents (with tools, structured workflows)

## Solution: Wire Up Conversational Handler

### Step 1: Add "conversational" as a valid routing target

**Location**: `agent_orchestrator/graph.py` - `route_from_supervisor()` function

```python
def route_from_supervisor(state: WorkflowState) -> str:
    """Conditional edge from supervisor to next agent.

    Routes based on supervisor's decision in state["next_agent"].
    """
    next_agent = state.get("next_agent", "end")

    # Check if approval required first
    if state.get("requires_approval", False):
        return "approval"

    # Route to specialized agents
    if next_agent in [
        "feature-dev",
        "code-review",
        "infrastructure",
        "cicd",
        "documentation",
    ]:
        return next_agent

    # NEW: Route general queries to conversational handler
    if next_agent == "conversational":
        return "conversational"

    return "end"
```

### Step 2: Modify supervisor to route general queries to "conversational"

**Location**: `agent_orchestrator/graph.py` - `supervisor_node()` function

Update the routing prompt to include "conversational" as an option:

```python
routing_prompt = """You're having a conversation with a developer. Based on their message, decide:

1. Which specialist should help them:
   - feature-dev: Writing/fixing code, implementing features
   - code-review: Checking security, code quality, best practices
   - infrastructure: Cloud setup, Docker, Kubernetes, IaC
   - cicd: Build pipelines, deployments, automation
   - documentation: README, API docs, code comments
   - conversational: General questions, greetings, status queries, "what can you do?"

2. Is this risky enough to need human approval?
   - Production deployments, infrastructure changes, DB migrations, destructive operations → YES
   - Code generation, reviews, docs, local testing, conversations → NO

Provide:
- agent_name: The specialist name (or 'conversational' for chat, or 'end' if done)
- requires_approval: true/false for HITL approval
- reasoning: Brief explanation in conversational tone

If the request is unclear, set agent_name='supervisor' and ask for clarification in reasoning.
"""
```

### Step 3: Add conversational node to the graph

**Location**: `agent_orchestrator/graph.py` - `create_workflow()` function

```python
def create_workflow(checkpoint_conn_string: str = None) -> StateGraph:
    """Create the LangGraph workflow with all agent nodes."""
    # Create graph
    workflow = StateGraph(WorkflowState)

    # Add all agent nodes
    workflow.add_node("supervisor", supervisor_node)
    workflow.add_node("conversational", conversational_handler_node)  # NEW
    workflow.add_node("feature-dev", feature_dev_node)
    workflow.add_node("code-review", code_review_node)
    workflow.add_node("infrastructure", infrastructure_node)
    workflow.add_node("cicd", cicd_node)
    workflow.add_node("documentation", documentation_node)
    workflow.add_node("approval", approval_node)

    # ... existing template workflow nodes ...

    # Add conditional edges from supervisor to agents
    workflow.add_conditional_edges(
        "supervisor",
        route_from_supervisor,
        {
            "feature-dev": "feature-dev",
            "code-review": "code-review",
            "infrastructure": "infrastructure",
            "cicd": "cicd",
            "documentation": "documentation",
            "conversational": "conversational",  # NEW
            "approval": "approval",
            "end": END,
        },
    )

    # Add edge from conversational back to end (it's terminal)
    workflow.add_edge("conversational", END)

    # ... rest of the graph setup ...
```

### Step 4: Update streaming filter to allow conversational responses

**Location**: `agent_orchestrator/main.py` - `chat_stream_endpoint()`

```python
# Define specialist agents (not supervisor)
SPECIALIST_AGENTS = [
    "feature_dev",
    "feature-dev",
    "code_review",
    "code-review",
    "infrastructure",
    "cicd",
    "documentation",
    "conversational",  # NEW: Allow conversational responses to stream
]
```

### Step 5: Update intent recognizer to distinguish chat vs execute

**Location**: `shared/lib/intent_recognizer.py` (if exists) or `agent_orchestrator/main.py`

Ensure the intent recognizer treats:

- Messages starting with `/execute` → `IntentType.TASK_EXECUTION` → supervisor routing
- All other messages → `IntentType.GENERAL_QUERY` → could route to conversational

This may already be handled correctly, but verify the logic.

## Alternative: Simpler Approach (Less Graph Changes)

If you want to minimize graph changes, modify the supervisor to generate a proper conversational response when routing to "end":

**Location**: `agent_orchestrator/graph.py` - `supervisor_node()` function

```python
# In supervisor_node, after determining routing decision:
if routing_decision.agent_name == "end":
    # This is a general query - generate a proper response
    from lib.llm_client import get_llm_client
    llm_client = get_llm_client()

    conversational_prompt = f"""Answer this question briefly and helpfully: {state['messages'][-1].content}

You are the code-chef AI assistant. You help with development tasks, code review, infrastructure, and more.
If they're just saying hello or asking what you can do, be friendly and explain your capabilities.
"""

    response = await llm_client.complete(prompt=conversational_prompt, temperature=0.7, max_tokens=500)
    conversational_response = AIMessage(content=response.get("content", ""))

    return {
        "messages": [conversational_response],
        "current_agent": "supervisor",
        "next_agent": "end",
        "requires_approval": False,
    }
```

## Recommended Approach

**Recommendation**: Implement the full solution (Steps 1-4) because:

- ✅ Cleaner separation of concerns
- ✅ Conversational handler already exists and works well
- ✅ Better for observability (separate node in LangSmith traces)
- ✅ Easier to optimize conversational responses separately
- ✅ Follows the architecture's intent (supervisor routes, specialists respond)
- ✅ Allows different models/configs for conversational vs task execution

## Testing Scenarios

After implementing, test with:

1. **General greetings**:

   - Input: "hello"
   - Expected: Friendly greeting from conversational handler
   - Route: supervisor → conversational → end

2. **Capability queries**:

   - Input: "what can you do?"
   - Expected: Explanation of capabilities
   - Route: supervisor → conversational → end

3. **Status queries**:

   - Input: "what's the status of my last task?"
   - Expected: Status information (if available)
   - Route: supervisor → conversational → end

4. **Technical questions**:

   - Input: "how does JWT authentication work?"
   - Expected: Helpful technical explanation
   - Route: supervisor → conversational → end

5. **Task execution (gated)**:

   - Input: "/execute implement JWT authentication"
   - Expected: Route to feature-dev agent, actual implementation
   - Route: supervisor → feature-dev → (approval if needed) → end

6. **Code review request**:
   - Input: "/execute review the authentication code"
   - Expected: Route to code-review agent
   - Route: supervisor → code-review → supervisor → end

## Implementation Order

1. **Step 1**: Update `route_from_supervisor()` to handle "conversational" routing
2. **Step 2**: Update `supervisor_node()` prompt to include "conversational" option
3. **Step 3**: Wire up conversational node in `create_workflow()`
4. **Step 4**: Update streaming filter in `main.py`
5. **Test**: Run through all test scenarios above
6. **Deploy**: Push to droplet and verify in production

## Success Criteria

- [ ] User sends "hello" → receives friendly response
- [ ] User sends "what can you do?" → receives capability overview
- [ ] User sends "/execute implement X" → routes to feature-dev agent
- [ ] No errors in logs during conversational routing
- [ ] LangSmith traces show conversational_handler_node invocations
- [ ] Response latency < 2 seconds for conversational queries
- [ ] Streaming works correctly for conversational responses
