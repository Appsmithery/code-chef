# Agent Registry Service

Centralized registry for agent discovery, capability matching, and health monitoring. Enables dynamic agent-to-agent communication and multi-agent collaboration workflows.

## Features

- **Agent Registration**: Auto-register agents on startup
- **Capability Discovery**: Search for agents by capability keyword
- **Health Monitoring**: Automatic detection of offline agents (60s timeout)
- **Heartbeat Management**: Keep-alive mechanism for active agents
- **Prometheus Metrics**: Comprehensive observability

## API Endpoints

### Registration & Discovery

- `POST /register` - Register or update an agent
- `GET /agents` - List all registered agents (optional `?status=active` filter)
- `GET /agents/{agent_id}` - Get specific agent details
- `GET /capabilities/search?q={keyword}` - Search for agents by capability

### Health Monitoring

- `POST /agents/{agent_id}/heartbeat` - Update agent heartbeat
- `GET /health/{agent_id}` - Check agent health status
- `GET /health` - Service health check

### Metrics

- `GET /metrics` - Prometheus metrics endpoint

## Configuration

Environment variables:

- `PORT` - Service port (default: 8009)
- `DATABASE_URL` - PostgreSQL connection string
- `HEARTBEAT_TIMEOUT_SECONDS` - Heartbeat timeout (default: 60)

## Agent Registration Schema

```json
{
  "agent_id": "code-review",
  "agent_name": "Code Review Agent",
  "base_url": "http://code-review:8003",
  "status": "active",
  "capabilities": [
    {
      "name": "review_pr",
      "description": "Review pull request for code quality and security",
      "parameters": {
        "repo_url": "str",
        "pr_number": "int"
      },
      "cost_estimate": "~100 tokens",
      "tags": ["git", "security", "code-quality"]
    }
  ],
  "metadata": {}
}
```

## Usage Example

```python
from shared.lib.registry_client import RegistryClient

# Initialize client
registry = RegistryClient(
    registry_url="http://agent-registry:8009",
    agent_id="code-review",
    agent_name="Code Review Agent",
    base_url="http://code-review:8003"
)

# Register capabilities
await registry.register([
    AgentCapability(
        name="review_pr",
        description="Review pull request",
        parameters={"repo_url": "str", "pr_number": "int"},
        cost_estimate="~100 tokens",
        tags=["git", "security"]
    )
])

# Start heartbeat loop
await registry.start_heartbeat()

# Search for agents
matches = await registry.search_capabilities("git")
```

## Database Schema

See `config/state/agent_registry.sql` for full schema.

Key tables:

- `agent_registry` - Agent registrations with capabilities

## Monitoring

Prometheus metrics exported at `/metrics`:

- `agent_registry_size` - Number of registered agents
- `http_requests_total` - Total HTTP requests
- `http_request_duration_seconds` - Request latency

## Deployment

```bash
# Build image
docker build -t agent-registry -f shared/services/agent-registry/Dockerfile .

# Run service
docker run -p 8009:8009 \
  -e DATABASE_URL="postgresql://user:pass@host:5432/db" \
  agent-registry

# Health check
curl http://localhost:8009/health
```

## Integration with Agents

All agents should auto-register on startup using `RegistryClient`:

1. Import registry client
2. Define capabilities
3. Register on startup
4. Start heartbeat loop
5. Update status when busy/idle

See `shared/lib/registry_client.py` for implementation details.
