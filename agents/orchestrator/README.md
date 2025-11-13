# Orchestrator Agent

Coordinates task routing and agent hand-offs across the development workflow.

## Responsibilities
- Task analysis and decomposition
- Agent selection and routing
- Workflow orchestration
- State management

## Endpoints
- `POST /task` - Submit new task
- `GET /task/{id}` - Get task status
- `POST /route` - Route to appropriate agent