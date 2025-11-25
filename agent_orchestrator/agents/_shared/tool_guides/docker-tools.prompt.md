# Docker Tools Usage Guide

## When to Use

- Building and managing Docker images
- Running containers
- Docker Compose orchestration
- Container inspection and logs

## Available Tools (docker MCP server)

### `build_image`

```json
{
  "context": ".",
  "dockerfile": "Dockerfile",
  "tags": ["myapp:latest", "myapp:v1.0.0"],
  "build_args": {
    "PYTHON_VERSION": "3.11"
  }
}
```

**Use when**: Building Docker images from Dockerfile.

### `run_container`

```json
{
  "image": "myapp:latest",
  "name": "myapp-dev",
  "ports": { "8000": "8000" },
  "env": {
    "DEBUG": "true"
  },
  "detach": true
}
```

**Use when**: Starting new containers for testing or deployment.

### `compose_up`

```json
{
  "file": "deploy/docker-compose.yml",
  "services": ["orchestrator", "gateway"],
  "detach": true,
  "build": false
}
```

**Use when**: Starting multi-service stacks.

### `compose_down`

```json
{
  "file": "deploy/docker-compose.yml",
  "remove_orphans": true,
  "volumes": false
}
```

**Use when**: Stopping services and cleaning up containers.

### `container_logs`

```json
{
  "container": "orchestrator",
  "tail": 100,
  "follow": false
}
```

**Use when**: Debugging container issues or checking output.

### `inspect_container`

```json
{
  "container": "orchestrator"
}
```

**Use when**: Getting detailed container state and configuration.

## Common Patterns

**Pattern 1: Build and Test**

1. `build_image` → build from Dockerfile
2. `run_container` → start with test config
3. `container_logs` → check for errors
4. `stop_container` → cleanup

**Pattern 2: Stack Management**

1. `compose_down` → stop existing services
2. `compose_up` → start with latest images
3. Wait 10-15s for initialization
4. Health check all services

**Pattern 3: Debugging**

1. `container_logs` → check recent logs
2. `inspect_container` → verify configuration
3. `exec_command` → run diagnostic commands
4. Fix issue and restart

## Safety Rules

- Always use `compose_down` before `compose_up` for clean state
- Check container health after starting
- Use `remove_orphans: true` to clean up old containers
- Don't delete volumes unless explicitly instructed
- Use resource limits (memory, CPU) in production
