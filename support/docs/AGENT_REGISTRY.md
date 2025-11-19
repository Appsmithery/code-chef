# Agent Registry Service

The Agent Registry is a centralized service that enables dynamic discovery, capability matching, and health monitoring for all agents in the Dev-Tools ecosystem.

## Architecture

- **Service**: `agent-registry` (FastAPI)
- **Port**: 8009
- **Storage**: PostgreSQL (`agent_registry` table)
- **Client**: `shared.lib.registry_client.RegistryClient`

## Features

1.  **Auto-Registration**: Agents register themselves on startup with their capabilities and metadata.
2.  **Heartbeat Monitoring**: Agents send periodic heartbeats. If a heartbeat is missed (default 60s), the agent is marked `offline`.
3.  **Capability Discovery**: Clients can search for agents based on capability keywords (e.g., "python", "security", "deployment").
4.  **Health Checks**: Provides real-time health status of agents.

## API Endpoints

| Method | Endpoint                 | Description                              |
| :----- | :----------------------- | :--------------------------------------- |
| `POST` | `/register`              | Register or update an agent              |
| `POST` | `/agents/{id}/heartbeat` | Send a heartbeat                         |
| `GET`  | `/agents`                | List all agents (optional status filter) |
| `GET`  | `/agents/{id}`           | Get agent details                        |
| `GET`  | `/capabilities/search`   | Search agents by capability              |
| `GET`  | `/health/{id}`           | Check specific agent health              |

## Integration Guide

### Registering an Agent

Agents use the `RegistryClient` to register on startup:

```python
from shared.lib.registry_client import RegistryClient, AgentCapability

client = RegistryClient(
    registry_url="http://agent-registry:8009",
    agent_id="my-agent",
    agent_name="My Custom Agent",
    base_url="http://my-agent:8000"
)

capabilities = [
    AgentCapability(
        name="code_generation",
        description="Generates Python code",
        cost_estimate="~100 tokens",
        tags=["coding", "python"]
    )
]

await client.register(capabilities)
await client.start_heartbeat()
```

### Discovering Agents

The Orchestrator (or other agents) can discover peers:

```python
# Find an agent that can do "security scanning"
matches = await client.search_capabilities("security")

if matches:
    target_agent = matches[0].agent_id
    # Delegate task to target_agent...
```

## Database Schema

See `config/state/agent_registry.sql` for the full schema definition.

```sql
CREATE TABLE agent_registry (
    agent_id VARCHAR(64) PRIMARY KEY,
    agent_name VARCHAR(128) NOT NULL,
    base_url VARCHAR(256) NOT NULL,
    status VARCHAR(32) NOT NULL,
    capabilities JSONB NOT NULL,
    last_heartbeat TIMESTAMP NOT NULL
);
```
