# Shared Library Documentation: Notification Components

**Module**: `shared/lib/`  
**Purpose**: Reusable notification infrastructure for all agents  
**Status**: ✅ Production (Phase 5.2)

---

## Module Index

| Module                                   | Purpose                             | Status        | Dependencies                       |
| ---------------------------------------- | ----------------------------------- | ------------- | ---------------------------------- |
| `event_bus.py`                           | Async pub/sub event routing         | ✅ Production | asyncio, logging                   |
| `linear_workspace_client.py`             | GraphQL API client for Linear       | ✅ Production | gql[requests], httpx               |
| `linear_client_factory.py`               | Factory for Linear client instances | ✅ Production | linear_workspace_client            |
| `notifiers/linear_workspace_notifier.py` | Event subscriber for Linear         | ✅ Production | event_bus, linear_workspace_client |
| `notifiers/email_notifier.py`            | SMTP-based email notifications      | ⚠️ Disabled   | smtplib, email.mime                |

---

## event_bus.py

### Overview

Singleton event bus implementing async pub/sub pattern for inter-component communication.

### Usage

```python
from shared.lib.event_bus import get_event_bus

# Get singleton instance
event_bus = get_event_bus()

# Subscribe to events
async def my_handler(event_data: dict):
    print(f"Received: {event_data}")

await event_bus.subscribe("my_event_type", my_handler)

# Emit events
await event_bus.emit(
    event_type="my_event_type",
    event_data={"key": "value"},
    source="my_agent",
    correlation_id="task-123"
)
```

### API Reference

#### `get_event_bus() -> EventBus`

Returns the singleton EventBus instance. Creates one if it doesn't exist.

**Returns**: EventBus instance

#### `EventBus.subscribe(event_type: str, handler: Callable) -> None`

Subscribe a handler function to an event type.

**Parameters**:

- `event_type` (str): Event type identifier (e.g., "approval_required")
- `handler` (Callable): Async function accepting event_data dict

**Example**:

```python
async def on_approval(data: dict):
    approval_id = data.get("approval_id")
    # Handle event...

await event_bus.subscribe("approval_required", on_approval)
```

#### `EventBus.emit(event_type: str, event_data: dict, source: str, correlation_id: str) -> None`

Emit an event to all subscribers asynchronously.

**Parameters**:

- `event_type` (str): Event type identifier
- `event_data` (dict): Event payload
- `source` (str): Source component name
- `correlation_id` (str): Correlation ID for tracing

**Example**:

```python
await event_bus.emit(
    "approval_required",
    {
        "approval_id": "uuid-123",
        "risk_level": "high",
        "task_description": "Deploy to production"
    },
    source="orchestrator",
    correlation_id="task-456"
)
```

**Logging**:

- Emits log: `INFO:lib.event_bus:Emitting '<event_type>' to N subscribers`
- Warning if no subscribers: `WARNING:lib.event_bus:No subscribers for event '<event_type>'`

### Implementation Notes

- **Thread-safe**: Uses singleton pattern with lock
- **Async**: All handlers run concurrently via `asyncio.gather`
- **Error handling**: Subscriber exceptions logged but don't block other subscribers
- **Subscribers**: Dict mapping event_type → list of handler functions

---

## linear_workspace_client.py

### Overview

GraphQL API client for Linear workspace operations using OAuth authentication.

### Configuration

**Environment Variables**:

```bash
LINEAR_API_KEY=lin_oauth_...              # OAuth token (required)
LINEAR_APPROVAL_HUB_ISSUE_ID=PR-68        # Approval hub issue ID (required)
```

### Usage

```python
from shared.lib.linear_client_factory import create_linear_workspace_client

# Create client
client = create_linear_workspace_client("orchestrator")

# Post to approval hub
comment_id = await client.post_to_approval_hub(
    approval_id="uuid-123",
    task_description="Deploy to production",
    risk_level="high",
    project_name="my-project",
    metadata={"task_id": "task-456", "priority": "critical"}
)
```

### API Reference

#### `LinearWorkspaceClient(agent_name: str)`

Constructor for Linear workspace client.

**Parameters**:

- `agent_name` (str): Name of calling agent (for logging)

**Raises**:

- `ValueError`: If LINEAR_API_KEY or LINEAR_APPROVAL_HUB_ISSUE_ID not set

#### `post_to_approval_hub(...) -> str`

Post formatted approval request comment to Linear workspace hub.

**Parameters**:

- `approval_id` (str): UUID of approval request
- `task_description` (str): Human-readable task description
- `risk_level` (str): "low", "medium", "high", or "critical"
- `project_name` (str): Project identifier
- `metadata` (dict): Additional context (task_id, priority, agent, timestamp)

**Returns**: Comment ID (UUID string)

**Example**:

```python
comment_id = await client.post_to_approval_hub(
    approval_id="e69e47dd-a8a8-4e18-8e1b-ab5bd58deb2e",
    task_description="Execute database migration",
    risk_level="critical",
    project_name="phase-5-chat",
    metadata={
        "task_id": "7caa3e83-4ae9-4f9c-83f6-e944f38387ae",
        "priority": "critical",
        "agent": "orchestrator",
        "timestamp": "2025-11-19T02:20:28.761732"
    }
)
# Returns: "6e087c73-f763-4482-86ea-f6012e401a02"
```

**Comment Format**:

````markdown
🟠 **HIGH Approval Required**

**Project**: `phase-5-chat`
**Approval ID**: `e69e47dd-a8a8-4e18-8e1b-ab5bd58deb2e`

@ops-lead - Your approval is needed:

Execute database migration

**Actions**:

- ✅ Approve: `task workflow:approve REQUEST_ID=e69e47dd-a8a8-4e18-8e1b-ab5bd58deb2e`
- ❌ Reject: `task workflow:reject REQUEST_ID=e69e47dd-a8a8-4e18-8e1b-ab5bd58deb2e REASON="<reason>"`

**Details**: [View in dashboard](http://45.55.173.72:8001/approvals/e69e47dd-a8a8-4e18-8e1b-ab5bd58deb2e)

**Metadata**: ```json
{'task_id': '7caa3e83-4ae9-4f9c-83f6-e944f38387ae', 'priority': 'critical', ...}
````

````

**Risk Emoji Mapping**:
- `low`: 🟢
- `medium`: 🟡
- `high`: 🟠
- `critical`: 🔴

**Logging**:
- Success: `INFO:lib.linear_workspace_client:Posted approval <id> to workspace hub: <comment_id>`
- Error: `ERROR:lib.linear_workspace_client:Failed to post approval: <error>`

### GraphQL Mutations

The client uses the following Linear GraphQL mutation:

```graphql
mutation CreateComment($issueId: String!, $body: String!) {
  commentCreate(input: {issueId: $issueId, body: $body}) {
    success
    comment {
      id
      body
      createdAt
    }
  }
}
````

---

## linear_client_factory.py

### Overview

Factory function for creating configured Linear client instances.

### Usage

```python
from shared.lib.linear_client_factory import create_linear_workspace_client

# Create workspace-level client
client = create_linear_workspace_client("orchestrator")

# Use client...
comment_id = await client.post_to_approval_hub(...)
```

### API Reference

#### `create_linear_workspace_client(agent_name: str) -> LinearWorkspaceClient`

Create and configure a Linear workspace client.

**Parameters**:

- `agent_name` (str): Name of calling agent (for logging/telemetry)

**Returns**: Configured LinearWorkspaceClient instance

**Logging**:

- `INFO:lib.linear_client_factory:Creating workspace-level Linear client for <agent_name>`

**Example**:

```python
# In orchestrator startup
from shared.lib.linear_client_factory import create_linear_workspace_client

client = create_linear_workspace_client("orchestrator")
logger.info("Linear workspace client initialized")
```

---

## notifiers/linear_workspace_notifier.py

### Overview

Event subscriber that posts approval notifications to Linear workspace hub.

### Usage

```python
from shared.lib.notifiers.linear_workspace_notifier import LinearWorkspaceNotifier
from shared.lib.event_bus import get_event_bus

# Initialize notifier (auto-subscribes to events)
notifier = LinearWorkspaceNotifier()

# Event bus will route events to notifier automatically
# No additional setup needed
```

### API Reference

#### `LinearWorkspaceNotifier()`

Constructor that creates Linear client and subscribes to events.

**Side Effects**:

- Creates LinearWorkspaceClient via factory
- Subscribes to "approval_required" event
- Logs initialization: `INFO:lib.notifiers.linear_workspace_notifier:Linear workspace notifier initialized`

#### `on_approval_required(event_data: dict) -> None` (async)

Event handler for approval_required events.

**Parameters**:

- `event_data` (dict): Event payload containing:
  - `approval_id` (str): Approval UUID
  - `task_description` (str): Task description
  - `risk_level` (str): Risk level
  - `project_name` (str): Project identifier
  - `metadata` (dict): Additional context

**Example Event Data**:

```python
{
    "approval_id": "e69e47dd-a8a8-4e18-8e1b-ab5bd58deb2e",
    "task_description": "Deploy to production",
    "risk_level": "high",
    "project_name": "phase-5-chat",
    "metadata": {
        "task_id": "task-456",
        "priority": "critical",
        "agent": "orchestrator"
    }
}
```

**Logging**:

- Start: `INFO:lib.notifiers.linear_workspace_notifier:Posting approval <id> to workspace hub (risk: <level>, project: <name>)`
- Success: `INFO:lib.notifiers.linear_workspace_notifier:✅ Posted approval <id> to workspace hub: <comment_id>`
- Error: `ERROR:lib.notifiers.linear_workspace_notifier:Failed to post approval <id>: <error>`

### Integration Example

```python
# agent_orchestrator/main.py

from shared.lib.event_bus import get_event_bus
from shared.lib.notifiers.linear_workspace_notifier import LinearWorkspaceNotifier

# Startup: Initialize notification system
event_bus = get_event_bus()
linear_notifier = LinearWorkspaceNotifier()
logger.info("Notification system initialized (Linear)")

# Later: Emit approval events
await event_bus.emit(
    "approval_required",
    {
        "approval_id": approval_id,
        "task_description": request.description,
        "risk_level": risk_level,
        "project_name": project_name,
        "metadata": {...}
    },
    source="orchestrator",
    correlation_id=task_id
)

# Linear notifier automatically receives and processes event
```

---

## notifiers/email_notifier.py

### Overview

SMTP-based email notifications for approval requests (optional fallback).

### Configuration

**Environment Variables**:

```bash
SMTP_HOST=smtp.gmail.com                  # SMTP server hostname
SMTP_PORT=587                             # SMTP port (587 for TLS)
SMTP_USER=your-email@gmail.com            # SMTP username
SMTP_PASS=app-specific-password           # SMTP password (app-specific for Gmail)
NOTIFICATION_EMAIL_TO=ops@company.com     # Recipient email
```

### Usage

```python
from shared.lib.notifiers.email_notifier import EmailNotifier

# Initialize notifier (auto-subscribes if SMTP configured)
notifier = EmailNotifier()

# Event bus will route events to notifier automatically
# Disabled if SMTP env vars not set
```

### API Reference

#### `EmailNotifier()`

Constructor that checks SMTP configuration and subscribes to events.

**Side Effects**:

- Checks for SMTP environment variables
- If all present: subscribes to "approval_required" event
- If missing: logs warning and disables notifier

**Logging** (if disabled):

```
WARNING:lib.notifiers.email_notifier:SMTP_HOST not configured, email notifier disabled
WARNING:lib.notifiers.email_notifier:NOTIFICATION_EMAIL_TO not configured, email notifier disabled
WARNING:lib.notifiers.email_notifier:Email notifier disabled (missing configuration)
```

#### `on_approval_required(event_data: dict) -> None` (async)

Event handler for approval_required events. Sends HTML email with approval details.

**Parameters**: Same as LinearWorkspaceNotifier

**Email Format**:

- **Subject**: "🚨 Approval Required: <task_description>"
- **Body**: HTML with approval details, action buttons, CLI commands
- **To**: NOTIFICATION_EMAIL_TO environment variable

**Logging**:

- Success: `INFO:lib.notifiers.email_notifier:Email sent for approval <id> to <email>`
- Error: `ERROR:lib.notifiers.email_notifier:Failed to send email for approval <id>: <error>`

### Enabling Email Notifications

1. Configure SMTP in `.env`:

```bash
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASS=your-app-password
NOTIFICATION_EMAIL_TO=ops-team@company.com
```

2. Force-recreate orchestrator:

```bash
cd deploy
docker compose up -d orchestrator --force-recreate
```

3. Verify initialization:

```bash
docker logs deploy-orchestrator-1 --tail 20 | grep -i email
```

Expected: `INFO:lib.notifiers.email_notifier:Email notifier initialized`

---

## Adding New Notifiers

### Step 1: Create Notifier Class

**File**: `shared/lib/notifiers/slack_notifier.py`

```python
from shared.lib.event_bus import get_event_bus
import httpx
import logging
import os

logger = logging.getLogger(__name__)

class SlackNotifier:
    """Post approval notifications to Slack via webhook."""

    def __init__(self):
        self.webhook_url = os.getenv("SLACK_WEBHOOK_URL")

        if not self.webhook_url:
            logger.warning("SLACK_WEBHOOK_URL not configured, Slack notifier disabled")
            return

        self.event_bus = get_event_bus()
        self.event_bus.subscribe("approval_required", self.on_approval_required)
        logger.info("Slack notifier initialized")

    async def on_approval_required(self, event_data: dict):
        """Handle approval_required events."""
        if not self.webhook_url:
            return

        approval_id = event_data.get("approval_id")
        risk_level = event_data.get("risk_level")
        task_description = event_data.get("task_description")

        # Format Slack message
        message = {
            "text": f"🚨 Approval Required ({risk_level.upper()})",
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Approval ID*: `{approval_id}`\n*Task*: {task_description}"
                    }
                },
                {
                    "type": "actions",
                    "elements": [
                        {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "Approve"},
                            "style": "primary",
                            "url": f"http://45.55.173.72:8001/approvals/{approval_id}"
                        }
                    ]
                }
            ]
        }

        # Send to Slack
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(self.webhook_url, json=message)
                response.raise_for_status()
                logger.info(f"Posted approval {approval_id} to Slack")
            except Exception as e:
                logger.error(f"Failed to post approval {approval_id} to Slack: {e}")
```

### Step 2: Register in Agent

**File**: `agent_orchestrator/main.py`

```python
from shared.lib.notifiers.slack_notifier import SlackNotifier

# Startup
linear_notifier = LinearWorkspaceNotifier()
email_notifier = EmailNotifier()
slack_notifier = SlackNotifier()  # NEW

logger.info("Notification system initialized (Linear + Email + Slack)")
```

### Step 3: Configure Environment

**File**: `config/env/.env`

```bash
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL
```

### Step 4: Test

```bash
# Rebuild and restart
cd deploy
docker compose build orchestrator
docker compose up -d orchestrator --force-recreate

# Create test approval
curl -X POST http://45.55.173.72:8001/orchestrate \
  -H "Content-Type: application/json" \
  -d '{"description": "Test Slack notification", "priority": "high"}'

# Check logs
docker logs deploy-orchestrator-1 --tail 20 | grep Slack
```

---

## Common Patterns

### Pattern 1: Multi-Channel Notifications

```python
# Initialize all notifiers
linear_notifier = LinearWorkspaceNotifier()
email_notifier = EmailNotifier()
slack_notifier = SlackNotifier()

# Event automatically routes to all subscribers
await event_bus.emit("approval_required", {...})
# → Linear comment posted
# → Email sent (if configured)
# → Slack message posted (if configured)
```

### Pattern 2: Conditional Notifications

```python
class ConditionalNotifier:
    async def on_approval_required(self, event_data: dict):
        risk_level = event_data.get("risk_level")

        # Only notify for high/critical risk
        if risk_level in ["high", "critical"]:
            await self.send_notification(event_data)
```

### Pattern 3: Notification Aggregation

```python
class AggregatingNotifier:
    def __init__(self):
        self.pending = []
        self.event_bus = get_event_bus()
        self.event_bus.subscribe("approval_required", self.on_approval)

        # Send batch every 5 minutes
        asyncio.create_task(self.send_batch_periodically())

    async def on_approval(self, event_data: dict):
        self.pending.append(event_data)

    async def send_batch_periodically(self):
        while True:
            await asyncio.sleep(300)  # 5 minutes
            if self.pending:
                await self.send_batch(self.pending)
                self.pending = []
```

---

## Testing

### Unit Tests

```python
# tests/test_event_bus.py

import pytest
from shared.lib.event_bus import get_event_bus

@pytest.mark.asyncio
async def test_event_emission():
    bus = get_event_bus()
    received = []

    async def handler(data):
        received.append(data)

    await bus.subscribe("test_event", handler)
    await bus.emit("test_event", {"key": "value"}, "test", "corr-123")

    assert len(received) == 1
    assert received[0]["key"] == "value"
```

### Integration Tests

```bash
# Test Linear notification
curl -X POST http://localhost:8001/orchestrate \
  -H "Content-Type: application/json" \
  -d '{
    "description": "Test notification integration",
    "priority": "critical",
    "project_context": {"environment": "production"}
  }'

# Verify in Linear PR-68
# Check comment posted within 1 second
```

---

## Troubleshooting

### Issue: Event Emitted But No Subscribers

**Symptom**: `WARNING:lib.event_bus:No subscribers for event 'approval_approved'`

**Solution**: Create and register subscriber:

```python
class ApprovalDecisionNotifier:
    def __init__(self):
        event_bus = get_event_bus()
        event_bus.subscribe("approval_approved", self.on_approved)
```

### Issue: Linear Client Fails to Initialize

**Symptom**: `ValueError: LINEAR_API_KEY or LINEAR_APPROVAL_HUB_ISSUE_ID not set`

**Solution**:

1. Check `.env` file has both variables (no quotes)
2. Force-recreate container: `docker compose up -d orchestrator --force-recreate`
3. Verify: `docker exec deploy-orchestrator-1 printenv | grep LINEAR`

### Issue: Email Not Sending

**Symptom**: `WARNING:lib.notifiers.email_notifier:Email notifier is disabled`

**Solution**: Configure all SMTP variables:

```bash
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASS=app-password
NOTIFICATION_EMAIL_TO=recipient@company.com
```

---

## Related Documentation

- **Notification System Architecture**: `support/docs/NOTIFICATION_SYSTEM.md`
- **Agent Endpoints**: `support/docs/AGENT_ENDPOINTS.md`
- **HITL Implementation**: `support/docs/HITL_IMPLEMENTATION_PHASE2.md`
- **Linear Setup**: `support/docs/LINEAR_SETUP.md`

---

**Last Updated**: November 18, 2025  
**Status**: ✅ Production  
**Phase**: 5.2 Complete
