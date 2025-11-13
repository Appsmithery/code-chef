# Orchestrator Agent

Central command layer that interprets incoming work, breaks it into autonomous subtasks, and supervises execution across every downstream agent.

## Overview

The Orchestrator Agent is the first touchpoint for any automation request. It performs natural-language intent parsing, plans a multi-step workflow, assigns each unit of work to the most capable specialist agent, and aggregates progress back into a single timeline. This README is optimized for both human operators and AI-driven orchestrators consuming metadata about the agent.

## Core Responsibilities

- **Task understanding:** Use LLM-powered parsing to convert free-form requests into structured objectives, constraints, and acceptance criteria.
- **Plan synthesis:** Derive a MECE (mutually exclusive, collectively exhaustive) subtask plan, sequencing steps with dependencies and approval gates.
- **Agent brokerage:** Match each subtask to the appropriate specialist agent using capability tags, SLAs, and current load.
- **Context propagation:** Maintain a shared execution context (task graph, artifacts, audit trail) and forward the minimal necessary data to each agent.
- **Runtime governance:** Track status, handle retries or escalations, and emit heartbeat updates for observability and SLA monitoring.

## Decision Model & State

- **Planning heuristic:** Hybrid rule-based + LLM planner with guardrails for scope, prerequisites, and termination conditions.
- **State store:** Task graph persisted in Postgres via the shared workflow schema; ephemeral execution notes cached in Redis.
- **Idempotency:** All orchestration commands are keyed by `task_id`; duplicate submissions return the existing plan and status.

## API Surface

| Method | Path                 | Purpose                                                        | Primary Request Fields                                            | Success Response Snapshot                                                        |
| ------ | -------------------- | -------------------------------------------------------------- | ----------------------------------------------------------------- | -------------------------------------------------------------------------------- |
| `POST` | `/orchestrate`       | Submit a new high-level task and trigger decomposition         | `task_id`, `title`, `description`, `priority`, `metadata.context` | `{ "task_id": "...", "status": "planned", "subtasks": [...] }`                   |
| `POST` | `/execute/{task_id}` | Begin or resume execution of a planned workflow                | `execution_mode` (`auto`/`manual`), optional checkpoints          | `{ "task_id": "...", "status": "running" }`                                      |
| `GET`  | `/tasks/{task_id}`   | Fetch real-time status, agent assignments, and artifacts       | n/a                                                               | `{ "task_id": "...", "status": "running", "subtasks": [...], "metrics": {...} }` |
| `GET`  | `/agents`            | Discover available specialist agents and their declared skills | query filters: `domain`, `capability`, `health`                   | `{ "agents": [{"name": "code-review", "skills": [...]}] }`                       |

### Sample: `POST /orchestrate`

```json
{
  "task_id": "feature-1087",
  "title": "Implement invoice PDF export",
  "description": "Add PDF export support to the billing dashboard including automated regression tests.",
  "priority": "high",
  "metadata": {
    "repository": "git@github.com:appsmithery/dev-tools.git",
    "requester": "product-management",
    "due_date": "2025-11-22"
  }
}
```

### Sample Status Response

```json
{
  "task_id": "feature-1087",
  "status": "running",
  "subtasks": [
    {
      "subtask_id": "feature-dev::feature-1087::1",
      "agent": "feature-dev",
      "state": "completed",
      "outputs": {
        "branch": "feature/invoice-pdf",
        "pull_request": "https://github.com/.../pull/412"
      }
    },
    {
      "subtask_id": "code-review::feature-1087::1",
      "agent": "code-review",
      "state": "running"
    }
  ],
  "metrics": {
    "elapsed_seconds": 1482,
    "on_time": true
  }
}
```

## Context Contracts

- **Inbound context:** Free-form natural language, project metadata, optional repo pointers, SLA hints.
- **Shared context schema:** JSON task graph persisted with fields `task_id`, `subtasks`, `dependencies`, `artifacts`, `status_history`.
- **Outbound payloads:** Minimal subtask brief + references to shared context and artifact storage locations.

## Observability

- Emits structured logs to `logs/orchestrator.log` with correlation IDs per `task_id` and `subtask_id`.
- Publishes Prometheus metrics: `orchestrator_tasks_active`, `orchestrator_subtask_failures_total`, `orchestrator_latency_seconds`.
- Integrates with OpenTelemetry tracing; span names follow `orchestrator.plan`, `orchestrator.dispatch`, `orchestrator.aggregate`.

## Integration Notes

- Use exponential backoff when polling `GET /tasks/{task_id}`; prefer webhook callbacks where available.
- Always provide deterministic `task_id` inputs to ensure idempotent reruns.
- Provide capability tags when registering downstream agents so the orchestrator can maintain accurate routing tables.

## Failure Modes & Recovery

- **Validation error (400):** Input missing required fields; the orchestrator returns structured diagnostics with `fields[].issue`.
- **Agent unavailable (503):** The orchestrator marks the subtask as `blocked` and emits an alert for manual routing.
- **Timeout escalation:** If a subtask exceeds SLA, the orchestrator auto-retries (up to 3 attempts) then flags the workflow for human review.
