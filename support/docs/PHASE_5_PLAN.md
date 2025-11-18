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

Workspace-level notification system for multi-project agent operations. Posts approval requests to Linear workspace hub with automatic @mentions for guaranteed notifications. No Slack required - uses Linear's native notification infrastructure (email, mobile, desktop).

### Multi-Project Architecture

```
Workspace: project-roadmaps
├── Team: Project Roadmaps (PR)
│   └── 🤖 Agent Approvals Hub (Workspace-Level Issue)
│       ├── Comment: [dev-tools] Critical approval needed
│       ├── Comment: [twkr] High approval needed
│       └── Labels: hitl:critical, project:dev-tools
│
├── Project: AI DevOps Agent Platform (dev-tools)
│   ├── Orchestrator: Workspace-level client (approval hub access)
│   ├── Subagents: Project-scoped clients (no hub access)
│   └── Issues: PR-53, PR-65, PR-67 (agents comment here)
│
└── Project: TWKR
    ├── Orchestrator: Workspace-level client (approval hub access)
    ├── Subagents: Project-scoped clients (no hub access)
    └── Issues: TWKR-1, TWKR-2 (agents comment here)
```

### Technical Design

```
┌─────────────────────────────────────────────────────────┐
│  Event Bus (FastAPI BackgroundTasks or Redis Pub/Sub)   │
│                                                          │
│  Events:                                                 │
│    - approval_required (workspace hub)                   │
│    - task_completed (project issue)                      │
│    - task_failed (project issue)                         │
│    - agent_error (project issue)                         │
└─────────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│  Notification Router (Multi-Project Aware)               │
│  - Route approvals to workspace hub                      │
│  - Route updates to project issues                       │
│  - Apply scoping rules (orchestrator vs subagent)        │
└─────────────────────────────────────────────────────────┘
          │              │              │
          ▼              ▼              ▼
    ┌─────────┐    ┌─────────┐    ┌─────────┐
    │  Linear │    │  Email  │    │ Webhook │
    │ Workspace│    │(Critical│    │(External│
    │   Hub   │    │  Only)  │    │Systems) │
    └─────────┘    └─────────┘    └─────────┘
```

### Scoping Architecture

**Orchestrator (Workspace-Level)**
- ✅ Post approval requests to workspace hub
- ✅ Create new projects in workspace
- ✅ Read all projects (for routing)
- ❌ Cannot modify project-specific issues

**Subagents (Project-Scoped)**
- ✅ Comment on issues in assigned project
- ✅ Update issue status in assigned project
- ✅ Read issues in assigned project
- ❌ Cannot access workspace approval hub
- ❌ Cannot access other projects

### Implementation Steps

#### Step 1: Linear Client Factory (Day 3)

**File**: `shared/lib/linear_client_factory.py`

```python
def get_linear_client(agent_name: str, project_name: Optional[str] = None):
    """
    Factory enforces scoping:
    - Orchestrator → WorkspaceClient (approval hub access)
    - Subagents → ProjectClient (scoped to project)
    """
    api_key = os.getenv("LINEAR_API_KEY")
    project = project_name or os.getenv("PROJECT_NAME", "dev-tools")
    
    if agent_name == "orchestrator":
        return LinearWorkspaceClient(api_key)
    
    # Subagents get project-scoped access
    project_info = PROJECT_REGISTRY[project]
    return LinearProjectClient(
        api_key=api_key,
        project_id=project_info["id"],
        project_name=project_info["name"]
    )
```

#### Step 2: Event Bus (Day 3-4)

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

#### Step 4: Project Notifier (Day 4)

**File**: `shared/lib/notifiers/linear_project_notifier.py`

```python
class LinearProjectNotifier:
    """
    Project-scoped notifier for subagent updates.
    Can only comment on issues in assigned project.
    """
    
    def __init__(self, project_id: str, project_name: str):
        self.project_id = project_id
        self.project_name = project_name
    
    async def post_progress_update(
        self, 
        issue_id: str,
        message: str,
        agent_name: str
    ):
        """Post update to project issue (security checked)."""
        if not await self._verify_issue_in_project(issue_id):
            logger.error(f"Agent {agent_name} attempted cross-project access")
            return False
        # Post comment...
```

#### Step 5: Wire Events to HITL (Day 5)

**File**: `agent_orchestrator/main.py`

```python
# Initialize event bus
event_bus = EventBus()
workspace_notifier = LinearWorkspaceNotifier()
project_notifier = LinearProjectNotifier(PROJECT_ID, PROJECT_NAME)

# Subscribe to approval events (workspace-level)
event_bus.subscribe("approval_required", workspace_notifier.notify_approval_required)

# Subscribe to task updates (project-level)
event_bus.subscribe("task_completed", project_notifier.post_progress_update)

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

**File**: `config/hitl/notification-config.yaml`

```yaml
workspace:
  id: project-roadmaps
  team_id: f5b610be-ac34-4983-918b-2c9d00aa9b7a
  approval_hub_issue_id: null  # Set after creating workspace hub

projects:
  dev-tools:
    id: b21cbaa1-9f09-40f4-b62a-73e0f86dd501
    name: AI DevOps Agent Platform
    orchestrator_url: http://45.55.173.72:8001
  
  twkr:
    id: null  # Create with orchestrator
    name: TWKR
    orchestrator_url: http://45.55.173.72:8001

channels:
  linear:
    enabled: true
    use_workspace_hub: true  # Post approvals to team-level issue
    mention_on_critical: true  # @mention admin for critical
      
  email:
    enabled: true
    only_critical: true  # Email only for critical/high risk
    smtp_server: smtp.gmail.com
    from: devtools-bot@appsmithery.co
    to: alex@appsmithery.co
    
  vscode:
    enabled: false  # Future: VS Code extension
    poll_interval: 10

routing:
  critical:
    channels: [linear, email]
    mention_admin: true
  high:
    channels: [linear, email]
  medium:
    channels: [linear]
  low:
    channels: [linear]

agent_permissions:
  orchestrator:
    type: workspace
    permissions:
      - post_approval_requests
      - create_projects
      - read_all_projects
  
  feature-dev:
    type: project
    permissions:
      - read_project_issues
      - comment_on_project_issues
      - update_project_issue_status
```

**File**: `config/linear/project-registry.yaml`

```yaml
workspace:
  id: project-roadmaps
  workspace_name: Project Roadmaps
  team_id: f5b610be-ac34-4983-918b-2c9d00aa9b7a
  approval_hub_issue_id: null  # Populate after setup

projects:
  dev-tools:
    id: b21cbaa1-9f09-40f4-b62a-73e0f86dd501
    short_id: 78b3b839d36b
    agents: [orchestrator, feature-dev, code-review, infrastructure, cicd, documentation]
  
  twkr:
    id: null
    short_id: null
    agents: [orchestrator, feature-dev, code-review]
```### Acceptance Criteria

- [x] Event bus with pub/sub pattern
- [x] Linear workspace notifier (posts to approval hub)
- [x] Linear project notifier (posts to project issues)
- [x] Client factory enforces scoping (workspace vs project)
- [x] Email notifier for critical approvals
- [x] Configuration-driven channel routing
- [x] Multi-project support (dev-tools, twkr)
- [x] <5s latency from approval creation to Linear notification
- [x] Security: Subagents cannot access approval hub
- [x] Security: Subagents cannot access other projects
- [x] Prometheus metrics: `notifications_sent_total{channel,event_type,project}`

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
