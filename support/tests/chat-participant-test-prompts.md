# Code-Chef Chat Participant Test Prompts

Test these prompts in the VS Code chat to generate rich LangSmith traces with system prompts, embeddings, and waterfalls.

## 1. Task Submission Tests

### Simple Feature Request

```
@code-chef implement JWT authentication middleware for our API
```

**Expected Trace:**

- Intent recognition (general_query → task_submission)
- Workflow routing (feature_development)
- Agent selection (feature_dev)
- Tool loading (progressive disclosure)
- RAG context retrieval (if relevant files exist)

### Feature with Context

```
@code-chef #file:agent_orchestrator/main.py add rate limiting to the /chat endpoint
```

**Expected Trace:**

- File reference extraction
- RAG query with file context
- Context7 library lookup (if enabled)
- Semantic embedding search
- Intent classification with high confidence

### Infrastructure Task

```
@code-chef deploy the orchestrator service to Kubernetes with autoscaling
```

**Expected Trace:**

- Infrastructure workflow selection
- IaC tool loading (terraform, kubectl)
- Risk assessment (should be HIGH)
- HITL approval trigger (if configured)

## 2. Status Query Tests

### Simple Status Check

```
@code-chef what's the status of my last task?
```

**Expected Trace:**

- Intent: status_query
- Session management
- Task lookup via last_task_id
- Minimal LLM usage (efficient)

### Specific Task Status

```
@code-chef check the status of task-abc123
```

**Expected Trace:**

- Intent: status_query with explicit ID
- Database query (no LLM needed)
- Sub-task status aggregation

## 3. Clarification Tests

### Ambiguous Request

```
@code-chef fix the bug
```

**Expected Trace:**

- Intent: clarification_needed
- LLM reasoning about missing context
- Suggested clarification questions
- No task creation

### Follow-up Question

```
@code-chef use OAuth2 instead
```

**Expected Trace:**

- Session history loading
- Context from previous message
- Intent refinement
- Task update or new task creation

## 4. Approval Tests

### High-Risk Operation

```
@code-chef delete all staging databases
```

**Expected Trace:**

- Risk assessment: CRITICAL
- Approval request creation
- Linear issue generation (if configured)
- Workflow interruption
- No execution without approval

### Production Deployment

```
@code-chef deploy to production
```

**Expected Trace:**

- Risk assessment: HIGH
- HITL trigger
- Guardrail checks
- Approval required response

## 5. Multi-Agent Workflow Tests

### End-to-End Feature

```
@code-chef implement a user profile page with tests and documentation
```

**Expected Trace:**

- Workflow: feature_development + testing + documentation
- Multiple agent invocations (feature_dev → cicd → documentation)
- Parallel task execution (if configured)
- State checkpointing between agents

### Code Review Request

```
@code-chef review the security of our authentication implementation
```

**Expected Trace:**

- Workflow: code_review
- Agent: code_review
- Security-focused tool loading
- Static analysis tool invocation

## 6. Context-Heavy Tests

### With File References

```
@code-chef #file:shared/lib/progressive_mcp_loader.py #file:agent_orchestrator/graph.py optimize the tool loading strategy
```

**Expected Trace:**

- Multiple file embeddings
- RAG retrieval with high relevance
- Context window management
- Token optimization via progressive disclosure

### With Symbol References

```
@code-chef @function:recognize_intent improve the confidence scoring
```

**Expected Trace:**

- Symbol resolution
- Function-level context extraction
- Precise RAG query
- Targeted code modification

## 7. Streaming Tests

### Long-Running Task

```
@code-chef refactor the entire agent_orchestrator module to use async/await consistently
```

**Expected Trace:**

- Streaming response chunks
- Agent progress updates
- Tool call events
- Partial completion markers

### Multi-Step Workflow

```
@code-chef create a new microservice for user authentication, write tests, and set up CI/CD
```

**Expected Trace:**

- Workflow status events
- Agent handoffs
- Subtask creation
- Parallel execution groups

## 8. Error Handling Tests

### Invalid Request

```
@code-chef pqwoeirpqoweirupqoweiur
```

**Expected Trace:**

- Intent recognition failure
- Fallback to general_query
- Clarification response
- Error handling gracefully

### Tool Failure

```
@code-chef use a tool that doesn't exist
```

**Expected Trace:**

- Tool resolution failure
- Error propagation
- Graceful degradation
- Alternative suggestion

## 9. RAG Context Tests

### Library-Specific Query

```
@code-chef implement a LangGraph workflow with checkpointing to PostgreSQL
```

**Expected Trace:**

- Context7 library lookup: langgraph, langchain
- RAG retrieval from documentation
- High-relevance context injection
- Token savings from context pruning

### Domain Knowledge Query

```
@code-chef how do I configure LangSmith tracing with a service key?
```

**Expected Trace:**

- Documentation search
- Internal knowledge retrieval
- Minimal LLM usage (RAG-powered)

## 10. Optimization Tests

### Progressive Disclosure Validation

```
@code-chef create a simple hello world endpoint
```

**Expected Trace:**

- MINIMAL tool loading (10-30 tools)
- Efficient intent recognition
- No unnecessary RAG queries
- <500 tokens total

### Maximum Context Test

```
@code-chef analyze the entire codebase and suggest architectural improvements
```

**Expected Trace:**

- FULL tool loading (150+ tools)
- Extensive RAG retrieval
- Multiple context sources
- Token optimization still applied

---

## Testing Methodology

1. **Open VS Code** with the code-chef extension installed
2. **Open the chat panel** (Ctrl+Alt+I or Cmd+Opt+I)
3. **Type prompts** using `@code-chef` prefix
4. **Monitor LangSmith** at https://smith.langchain.com/projects/code-chef-production
5. **Review traces** for:
   - System prompts
   - Token counts
   - Latency metrics
   - Tool invocations
   - RAG context quality
   - Waterfall visualization

## Expected Metadata in Traces

Each trace should contain:

```json
{
  "environment": "production",
  "extension_version": "2.0.0",
  "experiment_group": "code-chef",
  "model_version": "<model-name>",
  "session_id": "<session-uuid>",
  "user_id": "<vscode-machine-id>"
}
```

## Validation Checklist

- [ ] All traces appear in LangSmith without 403 errors
- [ ] System prompts are visible and complete
- [ ] Token counts are accurate
- [ ] Waterfall shows nested LLM calls
- [ ] RAG context is included in traces
- [ ] Intent recognition is logged
- [ ] Tool invocations are traced
- [ ] Error handling is captured
- [ ] Streaming events are visible
- [ ] Session continuity is maintained
