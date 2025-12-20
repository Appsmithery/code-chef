### Troubleshooting Analysis

1.  **Intent Hallucination**: The `intent_recognizer` incorrectly classified `@chef hello?` as a `TASK_SUBMISSION` with high confidence, bypassing the conversational override and triggering a redirect to `/execute/stream`.
2.  **Streaming Hang**: The system is stuck at `Switching to Agent mode...`. This is likely due to:
    *   **Caddy Buffering**: `config/caddy/Caddyfile` is missing the `request_buffering off` directive (noted as a critical fix in `STREAMING_DIAGNOSIS.md`), causing it to buffer the request context.
    *   **Initialization Latency**: The `/execute/stream` endpoint performs several slow operations (MCP tool calls to read files, workflow routing) before yielding its first chunk.
    *   **Database Import Hang**: `agent_orchestrator/graph.py` initializes a global `app` that connects to Postgres at import time, which can hang the entire process if the database is slow.

### Recommended Fix Plan

#### 1. Fix Caddy Buffering
Add `request_buffering off` to ensure large request contexts don't cause hangs.

```plaintext
// ...existing code...
	# Chat stream endpoint (SSE streaming) - BEFORE root handler!
	# CRITICAL: flush_interval -1 disables response buffering for real-time SSE
	handle /chat/stream {
		reverse_proxy orchestrator:8001 {
			flush_interval -1      # Disable buffering - send SSE chunks immediately
			request_buffering off  # Disable request buffering for large contexts
			transport http {
// ...existing code...
	# Execute stream endpoint (Agent mode SSE streaming)
	handle /execute/stream {
		reverse_proxy orchestrator:8001 {
			flush_interval -1      # Disable buffering for SSE
			request_buffering off  # Disable request buffering
			transport http {
// ...existing code...
```

#### 2. Tune Intent Recognition
Adjust the prompt to be more conservative in `ask` mode and fix the `WorkflowRouter` method call.

```python
// ...existing code...
        if mode_hint == "ask":
            mode_guidance = """
**Mode Context: ASK MODE** (Conversational)
- User is in Ask/Chat mode, typically asking questions or seeking information
- Bias heavily toward "general_query" for greetings (hi, hello) and informational questions
- Only classify as "task_submission" if there is a CLEAR ACTIONABLE REQUEST (e.g., "implement X", "fix Y")
- If the message is just a greeting or a short question, it is ALWAYS "general_query"
- Confidence threshold for task_submission should be VERY HIGH (>0.9)
"""
// ...existing code...
```

#### 3. Fix Workflow Router Method
The `WorkflowRouter` is calling a non-existent `chat_async` method.

```python
// ...existing code...
        try:
            # Use complete() instead of non-existent chat_async()
            response = await self.llm_client.complete(
                prompt=prompt,
                max_tokens=200,
                temperature=0.1,
            )

            # Parse JSON response
            import json

            content = response.get("content", "")
// ...existing code...
```

#### 4. Add Initialization Heartbeat
Add an immediate "initializing" chunk to `agent_orchestrator/main.py` to prevent the UI from appearing stuck.

```python
// ...existing code...
@app.post("/execute/stream", tags=["execution"])
@traceable(name="execute_stream", tags=["api", "streaming", "sse", "agent-mode"])
async def execute_stream_endpoint(request: ChatStreamRequest):
    # ...existing code...
    async def event_generator():
        """Generate SSE events from workflow execution."""
        # Yield immediate heartbeat to prevent UI hang
        yield f"data: {json.dumps({'type': 'content', 'content': '⚙️ *Initializing agent workflow...*\\n\\n'})}\n\n"
        
        try:
            from graph import WorkflowState, get_graph
// ...existing code...
```

### Next Steps
1. Apply the **Caddyfile** fix first and restart Caddy (`caddy reload`).
2. Apply the **Intent Recognition** and **Workflow Router** fixes.
3. Restart the **Orchestrator** service.
4. Verify by typing `hello?` again; it should now stay in conversational mode.
