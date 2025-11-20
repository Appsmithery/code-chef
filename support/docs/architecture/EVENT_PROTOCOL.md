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

## Complete Usage Examples

### Example 1: PR Deployment Workflow (Sequential)

```python
from shared.lib.event_bus import get_event_bus
from shared.lib.agent_events import AgentRequestEvent, AgentRequestType, AgentRequestPriority

bus = get_event_bus()

# Step 1: Request code review
review_request = AgentRequestEvent(
    source_agent="orchestrator",
    target_agent="code-review",
    request_type=AgentRequestType.REVIEW_CODE,
    payload={"repo_url": "https://github.com/myorg/myapp", "pr_number": 42},
    priority=AgentRequestPriority.HIGH
)

try:
    review_response = await bus.request_agent(review_request, timeout=300.0)

    if review_response.status == "success":
        print(f"Review completed: {review_response.result['comments']} comments")

        # Step 2: Run tests if review passed
        test_request = AgentRequestEvent(
            source_agent="orchestrator",
            target_agent="cicd",
            request_type=AgentRequestType.RUN_PIPELINE,
            payload={"repo_url": "https://github.com/myorg/myapp", "pr_number": 42, "pipeline_type": "test"},
            priority=AgentRequestPriority.HIGH
        )

        test_response = await bus.request_agent(test_request, timeout=600.0)

        if test_response.status == "success" and test_response.result["status"] == "passed":
            print(f"Tests passed: {test_response.result['tests_passed']}/{test_response.result['tests_run']}")

except asyncio.TimeoutError:
    print("Request timed out")
except Exception as e:
    print(f"Error: {e}")
```

### Example 2: Parallel Documentation Generation

```python
import asyncio
from shared.lib.event_bus import get_event_bus
from shared.lib.agent_events import AgentRequestEvent, AgentRequestType

bus = get_event_bus()

async def generate_all_docs(repo_url: str):
    tasks = [
        bus.request_agent(
            AgentRequestEvent(
                source_agent="orchestrator",
                target_agent="documentation",
                request_type=AgentRequestType.GENERATE_DOCS,
                payload={"repo_url": repo_url, "doc_type": "api_reference"}
            ),
            timeout=300.0
        ),
        bus.request_agent(
            AgentRequestEvent(
                source_agent="orchestrator",
                target_agent="documentation",
                request_type=AgentRequestType.GENERATE_DOCS,
                payload={"repo_url": repo_url, "doc_type": "user_guide"}
            ),
            timeout=300.0
        )
    ]

    responses = await asyncio.gather(*tasks, return_exceptions=True)

    results = {}
    for i, resp in enumerate(responses):
        doc_type = ["api_reference", "user_guide"][i]
        if isinstance(resp, Exception):
            results[doc_type] = {"error": str(resp)}
        elif resp.status == "success":
            results[doc_type] = resp.result
        else:
            results[doc_type] = {"error": resp.error}

    return results

docs = await generate_all_docs("https://github.com/myorg/myapp")
```

## Error Handling Patterns

### Pattern 1: Retry with Exponential Backoff

```python
async def request_with_retry(request, max_retries=3, base_delay=1.0):
    bus = get_event_bus()

    for attempt in range(max_retries):
        try:
            response = await bus.request_agent(request, timeout=60.0)
            if response.status == "success":
                return response

            if attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt)
                await asyncio.sleep(delay)

        except asyncio.TimeoutError:
            if attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt)
                await asyncio.sleep(delay)

    raise Exception(f"Failed after {max_retries} attempts")
```

### Pattern 2: Graceful Degradation

```python
async def safe_emit_with_fallback(event_type, data, source):
    bus = get_event_bus()

    try:
        await bus.emit(event_type, data, source=source, publish_to_redis=True)
    except Exception as e:
        await bus.emit(event_type, data, source=source, publish_to_redis=False)
```

## Best Practices

1. **Always Set Correlation IDs**: Use task IDs as `correlation_id` to trace related events
2. **Use Appropriate Timeouts**: Short (10-30s) for quick ops, long (300-600s) for builds/deployments
3. **Handle Subscriber Failures**: Don't re-raise exceptions in subscribers (they don't affect others)
4. **Idempotent Event Handlers**: Design handlers to be safe to execute multiple times
5. **Monitor Statistics**: Use `bus.get_stats()` to monitor system health

## Prometheus Metrics

- `event_bus_events_emitted_total{event_type, source}` - Total events emitted
- `event_bus_events_delivered_total{event_type}` - Total events delivered
- `event_bus_subscriber_errors_total{event_type, callback_name}` - Subscriber failures
- `agent_request_latency_seconds{source_agent, target_agent, request_type}` - Request latency
- `agent_requests_active{source_agent, target_agent}` - Active requests
- `agent_request_timeouts_total{source_agent, target_agent}` - Request timeouts
