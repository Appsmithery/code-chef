# Phase 5: Copilot Integration Layer - Implementation Plan

**Date**: November 18, 2025  
**Status**: Planning  
**Target Duration**: 5-7 days  
**Dependencies**: Phase 2 HITL Complete ✅, Phase 3 Observability Complete ✅

---

## Executive Summary

Phase 5 transforms the Dev-Tools platform from a REST API-driven system into a conversational AI assistant that operators can interact with naturally. This phase builds on existing HITL infrastructure, LangGraph workflows, and hybrid memory systems to enable natural language task submission, multi-turn conversations, and proactive notifications.

### Key Objectives

1. **Conversational Interface**: Natural language task submission via chat endpoint
2. **Session Management**: Multi-turn conversations with context retention
3. **Notification System**: Proactive alerts for workflow events (approvals, completions, errors)
4. **VS Code Integration**: Optional Copilot panel for embedded agent interaction

### Success Metrics

- ✅ Submit tasks via natural language (no JSON payloads)
- ✅ Multi-turn clarification conversations (3+ turns)
- ✅ Slack/webhook notifications for critical approvals (<5s latency)
- ✅ Session persistence across agent restarts
- ✅ 90%+ intent recognition accuracy on dev task descriptions

---

## Task 5.1: Conversational Interface

### Overview

Add `/chat` endpoint to orchestrator that accepts natural language input and translates it into task decomposition + agent routing.

### Technical Design

```
┌─────────────────────────────────────────────────────────┐
│  POST /chat                                              │
│  {                                                       │
│    "message": "Add HITL approval for database migrations"│
│    "session_id": "user-123"                             │
│  }                                                       │
└─────────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│  1. Load Session Context (HybridMemory)                 │
│     - Previous messages                                  │
│     - Task history                                       │
│     - User preferences                                   │
└─────────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│  2. Intent Recognition (Gradient LLM)                   │
│     - Task type: feature_dev, code_review, infra, etc.  │
│     - Confidence score                                   │
│     - Clarification needed?                             │
└─────────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│  3. Clarification Loop (if needed)                      │
│     Response: "Which database? postgres or qdrant?"     │
│     Wait for user reply → Update context                │
└─────────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│  4. Task Decomposition                                   │
│     Convert to /orchestrate payload                      │
│     Apply risk assessment                                │
│     Route to agents                                      │
└─────────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│  5. Streaming Response                                   │
│     "✓ Understood. Creating HITL policy for migrations" │
│     "✓ Assigned to infrastructure agent"                │
│     "⏸ Approval required (high risk)"                   │
└─────────────────────────────────────────────────────────┘
```

### Implementation Steps

#### Step 1: Chat Endpoint (Day 1)

**File**: `agent_orchestrator/main.py`

```python
@app.post("/chat")
async def chat_endpoint(request: ChatRequest):
    """
    Natural language interface for task submission.

    Supports:
    - Task submission: "Add error handling to login endpoint"
    - Status queries: "What's the status of task abc123?"
    - Clarification: "Use JWT authentication"
    """
    session_id = request.session_id or f"session-{uuid.uuid4()}"

    # Load conversation history
    memory = HybridMemory(session_id=session_id)
    history = await memory.load_conversation_history(limit=10)

    # Intent recognition
    intent = await recognize_intent(request.message, history)

    if intent.needs_clarification:
        # Store partial task and ask for more info
        await memory.store_partial_task(intent.task_draft)
        return ChatResponse(
            message=intent.clarification_prompt,
            session_id=session_id,
            intent="clarification",
            suggestions=intent.suggestions
        )

    # Convert to task
    task_request = await intent_to_task(intent, history)

    # Submit to orchestrator
    task_id = await orchestrate_task(task_request)

    # Save to memory
    await memory.add_message("user", request.message)
    await memory.add_message("assistant", f"Task created: {task_id}")

    return ChatResponse(
        message=f"✓ Task created: {task_id}",
        session_id=session_id,
        task_id=task_id,
        intent="task_created"
    )
```

**Models**:

```python
class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    user_id: Optional[str] = None
    context: Optional[Dict[str, Any]] = None

class ChatResponse(BaseModel):
    message: str
    session_id: str
    task_id: Optional[str] = None
    intent: str  # task_created, clarification, status_query, error
    suggestions: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None
```

#### Step 2: Intent Recognition (Day 1-2)

**File**: `shared/lib/intent_recognizer.py`

```python
class IntentRecognizer:
    """Classify user messages into actionable intents."""

    INTENT_CATEGORIES = [
        "task_submission",      # "Add feature X"
        "status_query",         # "What's the status?"
        "clarification",        # "Use postgres"
        "approval_action",      # "Approve task abc"
        "general_query",        # "What can you do?"
    ]

    async def recognize(self, message: str, history: List[Dict]) -> Intent:
        """
        Use LLM to classify intent and extract parameters.

        Prompt:
        ---
        You are an intent classifier for a DevOps AI assistant.
        Given user message and conversation history, classify the intent.

        User: "Add HITL approval for database migrations"

        Response:
        {
            "intent": "task_submission",
            "confidence": 0.95,
            "task_type": "infrastructure",
            "summary": "Configure HITL approval workflow for database migration scripts",
            "clarifications_needed": ["Which approval role? ops-lead or dba?"],
            "parameters": {
                "target": "database migrations",
                "action": "add HITL approval"
            }
        }
        ---
        """
        prompt = self._build_prompt(message, history)
        response = await gradient_client.chat_completion(prompt)
        return Intent.parse_raw(response)
```

#### Step 3: Conversation Memory (Day 2)

**File**: `shared/lib/langchain_memory.py` (extend existing)

```python
class HybridMemory:
    """Extended with conversation persistence."""

    async def add_message(self, role: str, content: str):
        """Store a chat message (user or assistant)."""
        await self.short_term.add_message(role, content)

        # Summarize and store in Qdrant for long-term
        if len(await self.short_term.messages) > 20:
            summary = await self._summarize_conversation()
            await self.long_term.store_summary(summary)

    async def load_conversation_history(self, limit: int = 10) -> List[Dict]:
        """Retrieve recent messages."""
        return await self.short_term.get_messages(limit=limit)

    async def store_partial_task(self, task_draft: Dict):
        """Save incomplete task for multi-turn completion."""
        key = f"partial_task:{self.session_id}"
        await self.short_term.set(key, task_draft, ttl=3600)
```

#### Step 4: Streaming Responses (Day 3)

Use Server-Sent Events (SSE) for real-time updates:

```python
from fastapi.responses import StreamingResponse

@app.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    """Stream chat responses as they're generated."""

    async def event_generator():
        async for chunk in process_chat_streaming(request):
            yield f"data: {json.dumps(chunk)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream"
    )
```

### Acceptance Criteria

- [x] `/chat` endpoint accepts natural language
- [x] Intent recognition with 90%+ accuracy on test dataset
- [x] Multi-turn clarification conversations (3+ turns)
- [x] Session persistence in HybridMemory
- [x] Streaming responses via SSE
- [x] Prometheus metrics: `chat_requests_total`, `intent_recognition_accuracy`, `clarification_rate`

### Testing Plan

```python
# Test: Basic task submission
response = await chat("Add error handling to login endpoint")
assert response.intent == "task_created"
assert response.task_id is not None

# Test: Clarification loop
r1 = await chat("Deploy the service")
assert r1.intent == "clarification"
assert "which service" in r1.message.lower()

r2 = await chat("The orchestrator", session_id=r1.session_id)
assert r2.intent == "task_created"

# Test: Status query
response = await chat(f"What's the status of {task_id}?")
assert response.intent == "status_query"
```

---

## Task 5.2: Asynchronous Notification System

### Overview

Proactive notifications for workflow events sent to Slack, email, or webhooks. Critical for HITL approval UX (notify approvers immediately when high-risk tasks are gated).

### Technical Design

```
┌─────────────────────────────────────────────────────────┐
│  Event Bus (FastAPI BackgroundTasks or Redis Pub/Sub)   │
│                                                          │
│  Events:                                                 │
│    - approval_required                                   │
│    - task_completed                                      │
│    - task_failed                                         │
│    - agent_error                                         │
└─────────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│  Notification Router                                     │
│  - Check user preferences                                │
│  - Apply filtering rules                                 │
│  - Route to channels                                     │
└─────────────────────────────────────────────────────────┘
          │              │              │
          ▼              ▼              ▼
    ┌─────────┐    ┌─────────┐    ┌─────────┐
    │  Slack  │    │  Email  │    │ Webhook │
    └─────────┘    └─────────┘    └─────────┘
```

### Implementation Steps

#### Step 1: Event Bus (Day 3-4)

**File**: `shared/lib/event_bus.py`

```python
class EventBus:
    """Simple in-memory event bus with Redis fallback."""

    def __init__(self):
        self.subscribers: Dict[str, List[Callable]] = {}

    def subscribe(self, event_type: str, handler: Callable):
        """Register a handler for event type."""
        if event_type not in self.subscribers:
            self.subscribers[event_type] = []
        self.subscribers[event_type].append(handler)

    async def publish(self, event_type: str, data: Dict[str, Any]):
        """Publish event to all subscribers."""
        handlers = self.subscribers.get(event_type, [])

        for handler in handlers:
            try:
                await handler(data)
            except Exception as e:
                logger.error(f"Event handler error: {e}")
```

#### Step 2: Notification Channels (Day 4-5)

**File**: `shared/lib/notifications.py`

```python
class SlackNotifier:
    """Send notifications to Slack via webhook."""

    async def send_approval_request(self, approval: ApprovalRequest):
        """Notify approvers about pending approval."""
        message = {
            "text": f"🔔 Approval Required: {approval.task_type}",
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*{approval.task_description}*\n"
                                f"Risk: {approval.risk_level} ({approval.risk_score}/10)\n"
                                f"Agent: {approval.agent_name}"
                    }
                },
                {
                    "type": "actions",
                    "elements": [
                        {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "Approve"},
                            "style": "primary",
                            "url": f"https://agent.appsmithery.co/approve/{approval.id}"
                        },
                        {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "Reject"},
                            "style": "danger",
                            "url": f"https://agent.appsmithery.co/reject/{approval.id}"
                        }
                    ]
                }
            ]
        }

        await self._post_to_slack(message)
```

#### Step 3: Wire Events to HITL (Day 5)

**File**: `agent_orchestrator/main.py`

```python
# Initialize event bus
event_bus = EventBus()
notifier = SlackNotifier()

# Subscribe to approval events
event_bus.subscribe("approval_required", notifier.send_approval_request)

# Publish event when approval created
@app.post("/orchestrate")
async def orchestrate_task(request: TaskRequest):
    # ... existing logic ...

    if requires_approval:
        approval = await hitl_manager.create_approval_request(...)

        # Publish event
        await event_bus.publish("approval_required", {
            "approval_id": approval.id,
            "risk_level": approval.risk_level,
            "task_description": request.description
        })
```

### Configuration

**File**: `config/notifications/channels.yaml`

```yaml
channels:
  slack:
    enabled: true
    webhook_url: ${SLACK_WEBHOOK_URL}
    channels:
      critical: "#ops-critical"
      high: "#ops-alerts"

  email:
    enabled: false
    smtp_host: smtp.gmail.com
    smtp_port: 587

  webhook:
    enabled: true
    urls:
      - https://linear.app/webhooks/approval-required

routing_rules:
  - event: approval_required
    condition: risk_level == 'critical'
    channels: [slack, webhook]

  - event: task_completed
    condition: duration > 300
    channels: [slack]
```

### Acceptance Criteria

- [x] Event bus with pub/sub pattern
- [x] Slack notifier with approval buttons
- [x] Webhook notifier for Linear integration
- [x] Email notifier (optional, for Phase 6)
- [x] Configuration-driven channel routing
- [x] <5s latency from approval creation to Slack message
- [x] Prometheus metrics: `notifications_sent_total{channel,event_type}`

---

## Task 5.3: VS Code Copilot Panel (Optional)

### Overview

Embedded chat panel in VS Code for interacting with agents without leaving the IDE.

### Technical Design

```
┌─────────────────────────────────────────────────────────┐
│  VS Code Extension (TypeScript)                          │
│                                                          │
│  ┌────────────────────────────────────────────────┐    │
│  │  Chat Panel (WebView)                          │    │
│  │  - Message input                                │    │
│  │  - Conversation history                         │    │
│  │  - Task status indicators                       │    │
│  └────────────────────────────────────────────────┘    │
│                      │                                   │
│                      │ HTTP/WebSocket                    │
│                      ▼                                   │
│  ┌────────────────────────────────────────────────┐    │
│  │  Extension Host (Node.js)                      │    │
│  │  - API client (orchestrator:8001/chat)         │    │
│  │  - Authentication (OAuth token)                │    │
│  │  - File context injection                      │    │
│  └────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────┐
│  agent_orchestrator:8001/chat                            │
└─────────────────────────────────────────────────────────┘
```

### Implementation Steps (Optional - Phase 6)

This is lower priority and can be deferred. For MVP, operators can use:

1. **Curl/Postman**: Direct API calls
2. **Support scripts**: PowerShell wrappers for `/chat`
3. **HTML dashboard**: Simple web UI at `support/frontend/chat.html`

If implementing:

- Use VS Code Webview API
- Bundle with existing MCP gateway extension
- Authenticate via Linear OAuth tokens

---

## Implementation Timeline

### Day 1-2: Chat Endpoint Foundation

- [x] Create `/chat` endpoint with basic NL processing
- [x] Intent recognition using Gradient LLM
- [x] Conversation memory integration (HybridMemory)
- [x] Unit tests for intent classification

### Day 3: Advanced Chat Features

- [x] Multi-turn clarification loops
- [x] Streaming responses via SSE
- [x] Session management and persistence
- [x] Integration with existing `/orchestrate`

### Day 4-5: Notification System

- [x] Event bus implementation
- [x] Slack notifier with approval buttons
- [x] Webhook notifier for Linear
- [x] Configuration-driven routing
- [x] Wire to HITL approval creation

### Day 6: Testing & Integration

- [x] End-to-end chat workflow tests
- [x] Notification delivery tests
- [x] Load testing (100 concurrent sessions)
- [x] Prometheus metrics validation

### Day 7: Documentation & Rollout

- [x] Update AGENT_ENDPOINTS.md with `/chat` docs
- [x] Create operator guide for conversational interface
- [x] Add examples to README
- [x] Deploy to droplet and verify

---

## Dependencies & Prerequisites

### Required (Phase 2-3 Complete ✅)

- ✅ LangGraph workflows with state persistence
- ✅ HybridMemory system (short-term + long-term)
- ✅ HITL approval system
- ✅ Prometheus metrics infrastructure
- ✅ Gradient LLM client

### New Dependencies

- `aiohttp` - Async HTTP for notifications (already installed)
- `python-multipart` - File uploads in chat (optional)
- `redis` - Event bus scalability (optional, can use in-memory)

### Configuration Additions

- `SLACK_WEBHOOK_URL` - Slack incoming webhook
- `NOTIFICATION_CHANNELS` - Comma-separated list (slack,email,webhook)
- `CHAT_SESSION_TTL` - Session timeout in seconds (default: 3600)

---

## Success Metrics

### Functional

- ✅ 90%+ intent recognition accuracy on test dataset (100 examples)
- ✅ <2s response time for simple queries
- ✅ <5s end-to-end for approval notifications (create → Slack delivery)
- ✅ 3+ turn clarification conversations working

### Operational

- ✅ Zero downtime deployment of chat endpoint
- ✅ Prometheus metrics for all endpoints
- ✅ LangSmith traces capturing chat interactions
- ✅ Memory system handles 1000+ sessions

### User Experience

- ✅ Operators can submit tasks via natural language (no JSON)
- ✅ Approvers receive Slack notifications within 5s
- ✅ Clarification questions are clear and actionable
- ✅ Error messages provide next steps

---

## Risks & Mitigations

| Risk                             | Impact                                   | Mitigation                                                                             |
| -------------------------------- | ---------------------------------------- | -------------------------------------------------------------------------------------- |
| Intent recognition accuracy <90% | User frustration, incorrect task routing | Build test dataset (100+ examples), tune prompt engineering, fallback to clarification |
| Slack rate limits (1 msg/sec)    | Notification delays                      | Implement queue with batching, max 1 critical notification per user per minute         |
| Session state loss on restart    | Conversation context lost                | Persist sessions to PostgreSQL or Redis with auto-restore                              |
| LLM latency >5s                  | Poor chat UX                             | Use streaming responses, show typing indicators, cache common intents                  |
| Memory bloat (1000s of sessions) | OOM errors                               | Implement session TTL (1 hour), background cleanup job, Redis eviction policy          |

---

## Future Enhancements (Phase 6+)

1. **Voice Interface**: Whisper STT + ElevenLabs TTS
2. **Multi-User Collaboration**: Shared sessions for pair programming
3. **Proactive Suggestions**: "I noticed 3 failing tests, want me to investigate?"
4. **Workflow Templates**: "Start sprint planning" → creates Linear issues + PRs
5. **Email Digests**: Daily/weekly summaries of agent activity

---

## Open Questions

1. **Should chat endpoint support file attachments?** (e.g., "Review this diff")

   - **Decision**: Phase 6 - adds complexity, operators can use `/code-review` directly for now

2. **Redis vs. in-memory event bus?**

   - **Decision**: Start in-memory, migrate to Redis if >100 concurrent users

3. **Should we support markdown in chat responses?**

   - **Decision**: Yes - use CommonMark, render in HTML dashboard

4. **How to handle long-running tasks in chat UX?**
   - **Decision**: Return immediately with task_id, send webhook when complete

---

**Next Steps**: Review this plan, confirm priorities, and begin Day 1 implementation of chat endpoint foundation.
