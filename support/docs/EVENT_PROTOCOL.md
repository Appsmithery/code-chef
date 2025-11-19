# Inter-Agent Event Protocol

The Event Bus facilitates asynchronous communication between agents. Phase 6 introduces standardized **Inter-Agent Events** backed by Redis Pub/Sub for cross-container messaging.

## Event Schema

All inter-agent events follow the `InterAgentEvent` structure:

```json
{
  "event_id": "uuid-string",
  "event_type": "string",
  "source_agent": "agent-id",
  "target_agent": "agent-id" | null,
  "payload": { ... },
  "timestamp": "iso-8601-string",
  "correlation_id": "task-id" | null,
  "priority": 0
}
```

- **target_agent**: If `null`, the event is a broadcast to all agents. If specified, only the target agent should process it.
- **correlation_id**: Used to trace a workflow across multiple events (usually the `task_id`).

## Event Types

| Event Type            | Description                                | Payload                                 |
| :-------------------- | :----------------------------------------- | :-------------------------------------- |
| `task.delegated`      | Orchestrator assigns a subtask to an agent | `subtask_id`, `description`, `context`  |
| `task.accepted`       | Agent accepts the assignment               | `subtask_id`, `estimated_completion`    |
| `task.rejected`       | Agent rejects the assignment               | `subtask_id`, `reason`                  |
| `task.completed`      | Agent finishes the subtask                 | `subtask_id`, `result`, `artifacts`     |
| `task.failed`         | Agent fails to complete subtask            | `subtask_id`, `error`                   |
| `resource.locked`     | Agent acquires a lock                      | `resource_id`, `agent_id`, `expires_at` |
| `resource.unlocked`   | Agent releases a lock                      | `resource_id`, `agent_id`               |
| `agent.status_change` | Agent status update                        | `status` (active/busy/offline)          |

## Usage

### Emitting an Event

```python
from shared.lib.event_bus import get_event_bus

bus = get_event_bus()

await bus.emit(
    "task.completed",
    {
        "subtask_id": "st-123",
        "result": {"status": "ok"}
    },
    source="agent-feature-dev",
    correlation_id="task-456"
)
```

### Subscribing to Events

```python
async def on_task_delegated(event):
    payload = event.data
    print(f"Received task: {payload['description']}")

bus.subscribe("task.delegated", on_task_delegated)
```

## Redis Integration

- The Event Bus automatically connects to Redis if `REDIS_URL` is set.
- Events emitted with `publish_to_redis=True` (default) are published to the `agent-events` channel.
- Each agent has a background listener that subscribes to `agent-events` and re-emits received messages to its local subscribers.
- **Loop Prevention**: The listener checks if the event originated from itself (logic to be refined in future iterations) or relies on idempotent handlers.
