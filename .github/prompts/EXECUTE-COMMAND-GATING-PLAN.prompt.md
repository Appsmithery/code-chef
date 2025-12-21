# Execute Command Gating - Implementation Plan

**Created**: December 20, 2025  
**Status**: Planning  
**Priority**: High  
**Ticket**: CHEF-[TBD]

---

## Executive Summary

**Current State**: The `/chat/stream` endpoint uses LLM-based intent recognition to automatically detect task submissions and redirect to agent mode. This creates:

- Unpredictable behavior (LLM hallucinations)
- No explicit user control
- Confusion about when agents are invoked

**Desired State**: Clear separation:

- `/chat/stream` → **Always conversational** (Ask mode only)
- `/execute` or `/execute/stream` → **Explicit task submission** with Linear issue creation and subagent orchestration

---

## Current Architecture Audit

### ✅ What Exists

1. **Endpoints**:

   - `/chat/stream` - Conversational chat with automatic intent detection (PROBLEMATIC)
   - `/execute/stream` - Task execution endpoint (CORRECT, but not enforced)
   - `/execute/{task_id}` - Legacy task execution by ID

2. **Intent Recognition**:

   - `shared/lib/intent_recognizer.py` - LLM-based classification
   - Classifies messages as `GENERAL_QUERY` or `TASK_SUBMISSION`
   - Uses confidence threshold (0.85+)

3. **Linear Integration**:
   - `lib/linear_client.py` - GraphQL API client
   - `lib/linear_project_manager.py` - Project/issue management
   - Linear issue creation exists but is NOT triggered by `/execute`

### ❌ What's Missing

1. **No `/execute` command check** in `/chat/stream` endpoint
2. **Automatic intent detection** in chat (unreliable)
3. **Linear issue orchestration** not wired to `/execute/stream`
4. **No subagent task decomposition** from execute endpoint
5. **No parent/child issue hierarchy** creation

---

## Implementation Strategy

### Phase 1: Enforce `/execute` Command Gating (1-2 hours)

**Goal**: `/chat/stream` becomes pure conversational, no automatic task routing.

**Changes**:

1. **Remove intent recognition from `/chat/stream`**:

   ```python
   # agent_orchestrator/main.py

   @app.post("/chat/stream")
   async def chat_stream_endpoint(request: ChatStreamRequest):
       """
       Pure conversational chat (Ask mode only).

       - No task execution
       - No agent routing
       - No intent detection
       - Users must use /execute for tasks
       """
       # Remove: intent = await intent_recognizer.recognize(...)
       # Remove: if intent.type == IntentType.TASK_SUBMISSION: redirect...

       # Always use conversational_handler_node
   ```

2. **Add command parser** to detect `/execute` in messages:

   ```python
   # shared/lib/command_parser.py (NEW)

   class CommandType(str, Enum):
       EXECUTE = "execute"
       HELP = "help"
       STATUS = "status"
       CANCEL = "cancel"

   def parse_command(message: str) -> Optional[Dict]:
       """
       Parse slash commands from user messages.

       Supported:
       - /execute <task description>
       - /help
       - /status <workflow_id>
       - /cancel <workflow_id>

       Returns:
           Dict with command, args, raw_message
       """
       if not message.strip().startswith("/"):
           return None

       parts = message.strip().split(maxsplit=1)
       command = parts[0][1:]  # Remove /
       args = parts[1] if len(parts) > 1 else ""

       if command not in [cmd.value for cmd in CommandType]:
           return None

       return {
           "command": command,
           "args": args,
           "raw_message": message
       }
   ```

3. **Update `/chat/stream` to detect and redirect**:

   ```python
   @app.post("/chat/stream")
   async def chat_stream_endpoint(request: ChatStreamRequest):
       # Check for /execute command
       command = parse_command(request.message)

       if command and command["command"] == "execute":
           # Redirect to /execute/stream with task description
           yield f"data: {json.dumps({
               'type': 'redirect',
               'endpoint': '/execute/stream',
               'reason': 'explicit_command',
               'task': command['args']
           })}\n\n"
           return

       # Otherwise, always conversational
       # ... conversational_handler_node logic
   ```

**Testing**:

- ✅ Chat messages without `/execute` stay conversational
- ✅ `/execute create auth system` redirects to agent mode
- ✅ "implement login" (no slash) stays conversational

---

### Phase 2: Linear Issue Orchestration (2-3 hours)

**Goal**: `/execute/stream` creates parent Linear issue + subissues for agents.

**Changes**:

1. **Add Linear orchestration to `/execute/stream`**:

   ```python
   @app.post("/execute/stream")
   async def execute_stream_endpoint(request: ChatStreamRequest):
       """
       Execute task with full orchestration:
       1. Create parent Linear issue
       2. Decompose into subissues (one per agent)
       3. Route to supervisor for agent assignment
       4. Track execution via Linear state updates
       """

       # STEP 1: Create parent issue
       linear_client = get_linear_client()
       project_manager = get_project_manager()

       # Determine Linear project from context
       project_id = None
       if request.project_context:
           project_id = request.project_context.get("linear_project_id")

       if not project_id:
           # Fallback to default project
           project_id = "CHEF"  # Or from config

       parent_issue = await linear_client.create_issue(
           project_id=project_id,
           title=f"Task: {request.message[:60]}...",
           description=f"**User Request**: {request.message}\n\n"
                      f"**Status**: Analyzing and decomposing...\n"
                      f"**Session**: {session_id}",
           labels=["orchestrator", "in-progress"]
       )

       parent_issue_id = parent_issue["id"]
       logger.info(f"[Execute] Created parent issue: {parent_issue_id}")

       # Yield event to UI
       yield f"data: {json.dumps({
           'type': 'workflow_status',
           'status': 'issue_created',
           'issue_id': parent_issue_id,
           'issue_url': parent_issue['url']
       })}\n\n"
   ```

2. **Implement task decomposition**:

   ```python
   # STEP 2: Use supervisor to decompose into subtasks
   from graph import supervisor_node, WorkflowState
   from langchain_core.messages import HumanMessage

   # Create initial state for supervisor
   state = WorkflowState(
       messages=[HumanMessage(content=request.message)],
       current_agent="supervisor",
       next_agent="",
       task_result={},
       approvals=[],
       requires_approval=False,
       workflow_id=session_id,
       thread_id=session_id,
       pending_operation="",
       captured_insights=[],
       memory_context=None,
       workflow_template=None,
       workflow_context=None,
       use_template_engine=False,
       project_context=project_context,
       routing_decision=None
   )

   # Invoke supervisor to get routing decision
   updated_state = await supervisor_node(state)
   next_agent = updated_state.get("next_agent", "")

   logger.info(f"[Execute] Supervisor routed to: {next_agent}")
   ```

3. **Create subissues for each agent**:

   ```python
   # STEP 3: Create Linear subissue for assigned agent
   if next_agent not in ["end", "conversational"]:
       subissue = await linear_client.create_issue(
           project_id=project_id,
           title=f"[{next_agent.upper()}] {request.message[:40]}...",
           description=f"**Agent**: {next_agent}\n"
                      f"**Parent Task**: {parent_issue_id}\n\n"
                      f"{updated_state['routing_decision']['reasoning']}",
           labels=[next_agent, "subtask"],
           parent_id=parent_issue_id
       )

       logger.info(f"[Execute] Created subissue: {subissue['id']} for {next_agent}")

       yield f"data: {json.dumps({
           'type': 'workflow_status',
           'status': 'subissue_created',
           'agent': next_agent,
           'issue_id': subissue['id'],
           'issue_url': subissue['url']
       })}\n\n"
   ```

4. **Stream agent execution with Linear updates**:

   ```python
   # STEP 4: Execute agent and update Linear
   from graph import get_agent

   agent = get_agent(next_agent, project_context=project_context)

   # Update Linear: Mark as in-progress
   await linear_client.update_issue(
       subissue['id'],
       state="In Progress"
   )

   # Stream agent output
   async for chunk in agent.astream(state["messages"]):
       # Yield to SSE
       yield f"data: {json.dumps({
           'type': 'content',
           'content': chunk,
           'agent': next_agent
       })}\n\n"

   # Update Linear: Mark as complete
   await linear_client.update_issue(
       subissue['id'],
       state="Done",
       description=f"... [previous content]\n\n**Result**:\n{result}"
   )

   # Update parent issue
   await linear_client.update_issue(
       parent_issue_id,
       description=f"... [previous content]\n\n"
                  f"**Completed**: {next_agent} ✅"
   )
   ```

**Testing**:

- ✅ `/execute` creates parent Linear issue
- ✅ Supervisor assigns agent and creates subissue
- ✅ Agent execution updates subissue state
- ✅ Parent issue tracks overall progress

---

### Phase 3: Multi-Agent Workflows (3-4 hours)

**Goal**: Handle tasks requiring multiple agents (feature-dev → code-review → cicd).

**Changes**:

1. **Implement agent chaining**:

   ```python
   # Continue routing after first agent completes
   while next_agent not in ["end", ""]:
       # Create subissue for this agent
       # Execute agent
       # Update subissue
       # Get next routing decision from supervisor
       updated_state = await supervisor_node(updated_state)
       next_agent = updated_state.get("next_agent", "end")
   ```

2. **Add workflow summary to parent issue**:

   ```python
   # After all agents complete
   summary = generate_workflow_summary(execution_log)

   await linear_client.update_issue(
       parent_issue_id,
       state="Done",
       description=f"{original_description}\n\n"
                  f"## Execution Summary\n\n"
                  f"{summary}"
   )
   ```

---

### Phase 4: UI/UX Refinements (1-2 hours)

**Goal**: Clarify user experience and provide command help.

**Changes**:

1. **Add help command**:

   ```python
   # /help shows available commands
   HELP_TEXT = """
   **Available Commands:**

   - `/execute <task>` - Submit task for agent execution
   - `/status <workflow_id>` - Check workflow status
   - `/cancel <workflow_id>` - Cancel running workflow
   - `/help` - Show this message

   **Examples:**
   - /execute Implement JWT authentication with refresh tokens
   - /execute Review security of auth/login.py
   - /execute Deploy to staging environment
   """
   ```

2. **Add conversational prompt hint**:

   ```python
   # When user asks task-like question without /execute
   if looks_like_task_request(message):
       yield "💡 *Tip: Use `/execute <task>` to submit tasks for execution*\n\n"
   ```

3. **Frontend changes** (extensions/vscode-codechef/):

   ```typescript
   // Add command palette integration
   vscode.commands.registerCommand("codechef.executeTask", async () => {
     const task = await vscode.window.showInputBox({
       prompt: "Describe the task to execute",
       placeHolder: "e.g., Implement login feature with OAuth",
     });

     if (task) {
       // Send to /execute/stream
       chatPanel.sendMessage(`/execute ${task}`);
     }
   });
   ```

---

## Migration Strategy

### Option A: Hard Cutover (Recommended)

**Pros**:

- Clean, simple change
- No dual behavior
- Clear expectations

**Cons**:

- Breaking change for existing users
- Requires documentation update

**Timeline**: 1 day

### Option B: Gradual Rollout

**Pros**:

- Less disruptive
- Can A/B test

**Cons**:

- Complex dual-mode logic
- Confusing for users

**Timeline**: 2-3 days

**Recommendation**: Use Option A with clear changelog and migration guide.

---

## Testing Plan

### Unit Tests

```python
# support/tests/unit/test_command_parser.py
def test_execute_command_parsing():
    cmd = parse_command("/execute create login system")
    assert cmd["command"] == "execute"
    assert cmd["args"] == "create login system"

def test_no_command():
    cmd = parse_command("hello world")
    assert cmd is None

def test_invalid_command():
    cmd = parse_command("/invalid test")
    assert cmd is None
```

### Integration Tests

```python
# support/tests/integration/test_execute_endpoint.py
async def test_execute_creates_linear_issue():
    response = await client.post("/execute/stream", json={
        "message": "/execute implement auth",
        "user_id": "test"
    })

    # Should create parent issue
    assert "issue_created" in response.events

    # Should create subissue for agent
    assert "subissue_created" in response.events

async def test_chat_stays_conversational():
    response = await client.post("/chat/stream", json={
        "message": "implement login system",  # No /execute
        "user_id": "test"
    })

    # Should NOT redirect to execute
    assert "redirect" not in response.events
    assert response.agent == "conversational"
```

### E2E Tests

```python
# support/tests/e2e/test_execute_workflow.py
async def test_full_execute_workflow():
    """Test complete execute workflow with Linear integration."""

    # 1. Submit task via /execute
    task = "/execute Implement JWT authentication"
    response = await execute_stream(task)

    # 2. Verify parent issue created
    assert response.parent_issue_id is not None

    # 3. Verify supervisor routing
    assert response.routed_to == "feature-dev"

    # 4. Verify subissue created
    assert response.subissue_id is not None

    # 5. Verify agent execution
    assert response.execution_status == "completed"

    # 6. Verify Linear updates
    parent_issue = await linear.get_issue(response.parent_issue_id)
    assert parent_issue.state == "Done"
```

---

## Rollout Checklist

### Code Changes

- [ ] Create `shared/lib/command_parser.py`
- [ ] Update `agent_orchestrator/main.py`:
  - [ ] Remove intent recognition from `/chat/stream`
  - [ ] Add command parsing to `/chat/stream`
  - [ ] Add Linear orchestration to `/execute/stream`
  - [ ] Add task decomposition logic
  - [ ] Add multi-agent workflow support
- [ ] Update frontend (VS Code extension):
  - [ ] Add `/execute` command palette item
  - [ ] Update chat UI to show command help
  - [ ] Add command autocomplete

### Documentation

- [ ] Update `README.md` with new command structure
- [ ] Create migration guide for existing users
- [ ] Update API documentation
- [ ] Add examples to Copilot instructions
- [ ] Create video tutorial (optional)

### Configuration

- [ ] Add Linear project defaults to config
- [ ] Update `config/linear/agent-project-mapping.yaml`
- [ ] Configure command prefix (default: `/`)

### Testing

- [ ] Unit tests for command parser
- [ ] Integration tests for execute endpoint
- [ ] E2E tests for full workflow
- [ ] Manual QA on droplet

### Deployment

- [ ] Deploy to droplet (production)
- [ ] Monitor logs for errors
- [ ] Check Linear issue creation
- [ ] Verify agent execution
- [ ] Update VS Code extension

### Communication

- [ ] Post changelog in Linear
- [ ] Update Copilot instructions
- [ ] Create user announcement
- [ ] Document breaking changes

---

## Timeline Estimate

| Phase                          | Duration        | Dependencies     |
| ------------------------------ | --------------- | ---------------- |
| Phase 1: Command Gating        | 1-2 hours       | None             |
| Phase 2: Linear Orchestration  | 2-3 hours       | Phase 1          |
| Phase 3: Multi-Agent Workflows | 3-4 hours       | Phase 2          |
| Phase 4: UI/UX Refinements     | 1-2 hours       | Phase 3          |
| Testing                        | 2-3 hours       | All phases       |
| Documentation                  | 1-2 hours       | All phases       |
| **Total**                      | **10-16 hours** | **~2 work days** |

---

## Risks & Mitigations

| Risk                               | Impact | Mitigation                           |
| ---------------------------------- | ------ | ------------------------------------ |
| Breaking change for existing users | High   | Provide migration guide, update docs |
| Linear API rate limits             | Medium | Implement backoff, batch operations  |
| Complex multi-agent workflows      | Medium | Start simple, iterate                |
| UI confusion around commands       | Low    | Add help command, autocomplete       |

---

## Success Metrics

- **User Clarity**: 100% of task submissions via explicit `/execute`
- **Linear Integration**: 100% of execute calls create Linear issues
- **Agent Routing**: 95%+ accurate supervisor routing
- **Workflow Completion**: 90%+ workflows complete successfully
- **Response Time**: <2s for execute initialization
- **Error Rate**: <5% failures

---

## Future Enhancements

1. **Batch Commands**: `/execute batch task1, task2, task3`
2. **Scheduled Execution**: `/execute at 2pm deploy to staging`
3. **Workflow Templates**: `/execute workflow:pr-deployment`
4. **Agent Selection**: `/execute with:feature-dev implement auth`
5. **Approval Override**: `/execute --skip-approval update config`

---

## Questions for Discussion

1. Should we support both `/execute` and natural language detection? (Recommendation: No, cleaner UX)
2. What should be the default behavior if Linear API is unavailable? (Recommendation: Log locally, continue execution)
3. Should we allow mid-workflow cancellation? (Recommendation: Yes, via `/cancel` command)
4. How should we handle very long task descriptions? (Recommendation: Truncate in Linear title, full text in description)

---

## Approval

**Reviewed by**: [Name]  
**Approved by**: [Name]  
**Date**: [Date]

---

## Implementation Tracking

Create Linear issue: `CHEF-[TBD]` with subtasks:

- [ ] CHEF-[TBD]-1: Implement command parser
- [ ] CHEF-[TBD]-2: Remove intent detection from /chat/stream
- [ ] CHEF-[TBD]-3: Add Linear orchestration to /execute/stream
- [ ] CHEF-[TBD]-4: Implement multi-agent workflows
- [ ] CHEF-[TBD]-5: Add UI/UX refinements
- [ ] CHEF-[TBD]-6: Write tests
- [ ] CHEF-[TBD]-7: Update documentation
- [ ] CHEF-[TBD]-8: Deploy to production
