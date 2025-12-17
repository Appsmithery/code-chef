## Plan: Separate Ask Mode from Agent Mode Execution

Backend separation of conversational chat from task execution by creating distinct streaming endpoints with independent routing logic while reusing existing session management and LangGraph infrastructure.

### Steps

1. **Create `/execute/stream` endpoint** in [agent_orchestrator/main.py](agent_orchestrator/main.py)

   - Copy SSE event generator pattern from existing `/chat/stream`
   - Remove supervisor filtering (stream all agent activity)
   - Add workflow router integration for template selection
   - Include risk assessment and HITL approval flow
   - Enable automatic Linear issue creation

2. **Refactor `/chat/stream` for Ask mode** in [agent_orchestrator/main.py](agent_orchestrator/main.py)

   - Add `intent_recognizer.recognize()` at endpoint entry
   - Route `TASK_SUBMISSION` intents → redirect to `/execute/stream`
   - Handle `GENERAL_QUERY`, `STATUS_QUERY`, `CLARIFICATION` with conversational LLM responses
   - Keep existing supervisor filtering logic
   - Add new `conversational_handler_node` to LangGraph for Ask mode queries

3. **Add `executeStream()` method** to [extensions/vscode-codechef/src/orchestratorClient.ts](extensions/vscode-codechef/src/orchestratorClient.ts)

   - Mirror `chatStream()` signature but target `/execute/stream` endpoint
   - Reuse SSE parser and chunk handling
   - Add support for workflow progress events (`workflow_status` chunk type)

4. **Update chat participant routing** in [extensions/vscode-codechef/src/chatParticipant.ts](extensions/vscode-codechef/src/chatParticipant.ts)

   - Modify `handleStreamingChat()` to call `client.chatStream()` (Ask mode)
   - Modify `handleExecuteCommand()` to call `client.executeStream()` (Agent mode)
   - Add session mode tracking (`mode: "ask" | "agent"` in metadata)

5. **Add conversational handler node** to [agent_orchestrator/graph.py](agent_orchestrator/graph.py)
   - Create `@traceable` decorated `conversational_handler_node()` function
   - Use simple LLM completion without tool loading
   - Set as alternative entry point for Ask mode (vs. `supervisor` for Agent mode)
   - Return structured response with session continuity

### Further Considerations

1. **Intent recognition accuracy** - Should we add confidence threshold with user confirmation? Current LLM-based classifier may misroute edge cases like "Can you add a feature?" (question vs. task).

2. **Session mode persistence** - Allow mid-conversation mode switches or enforce consistency? Example: User asks question (Ask mode) then says "actually, do that" (should trigger Agent mode).

3. **Workflow router testing** - [workflow_router.py](agent_orchestrator/workflows/workflow_router.py) exists but isn't used in current streaming. Need integration tests with template YAML files.

4. **Token usage monitoring** - Agent mode will stream supervisor reasoning + all specialist output. Set up LangSmith filters to track token usage delta vs. current implementation.

5. **HITL checkpoint handling** - SSE streams with `interrupt()` may timeout on long approvals. Consider adding `approval_pending` chunk type with reconnection logic.
