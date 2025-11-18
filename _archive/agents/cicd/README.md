# CI/CD Agent

Automation specialist responsible for designing, provisioning, and operating continuous integration and deployment pipelines across repositories and environments.

## Overview

The CI/CD Agent composes workflow definitions (GitHub Actions, GitLab CI, Azure Pipelines, etc.), manages pipeline executions, and enforces delivery policies. It integrates with artifact stores, testing frameworks, and deployment strategies to deliver consistent build automation. This README is tuned for AI orchestrators requiring precise operational metadata.

### MCP Integration Architecture

CI/CD agent connects to **MCP Gateway** at `http://gateway-mcp:8000` with automation-focused tools:

**Recommended Tool Servers:**

- `gitmcp` (clone, checkout, commit, push, create_pull_request, webhook) - Pipeline trigger and repository operations
- `rust-mcp-filesystem` (read_file, write_file, create_directory) - Workflow YAML generation and artifact management
- `dockerhub` (search_images, inspect_image, push_image, list_tags) - Container registry operations
- `github` (create_workflow, dispatch_workflow, list_runs) - GitHub Actions management
- `memory` (create_entities, create_relations, search_nodes) - Pipeline execution history and metrics
- `fetch` (http_get, http_post) - CI platform API interactions (GitLab, CircleCI, etc.)
- `context7` (search_docs) - Pipeline best practices and security scanning configs
- `playwright` (navigate, screenshot) - Deployment smoke test automation

**Shared Tool Servers:** `time` (build timestamps), additional context/filesystem tools

The agent uses `MCPClient` to generate workflows, trigger builds, and log pipeline events (runs, deployments, promotions) to memory server. All CI/CD operations are traced for compliance and post-mortem analysis.

## Core Responsibilities

- **Pipeline synthesis:** Generate CI/CD definitions tailored to target platforms, build matrices, and compliance requirements.
- **Workflow execution:** Trigger builds, monitor stages, collect logs, and surface failure diagnostics.
- **Policy enforcement:** Apply branch protection rules, quality gates, coverage thresholds, and approval workflows.
- **Artifact management:** Handle build outputs, container images, SBOMs, and promotion between environments.
- **Deployment coordination:** Execute deployment strategies (blue/green, canary, rolling) and manage rollback triggers.

## Input Contract

| Field         | Required | Description                                                       |
| ------------- | -------- | ----------------------------------------------------------------- |
| `pipeline_id` | ✅       | Unique key for pipeline configuration                             |
| `repository`  | ✅       | Git URL + branch/tag to operate on                                |
| `platform`    | ✅       | CI platform (`github`, `gitlab`, `azure`, `circleci`, etc.)       |
| `stages`      | ✅       | Ordered list of build/test/deploy stages with tooling definitions |
| `triggers`    | optional | Events that start the pipeline (push, PR, schedule)               |
| `secrets_ref` | optional | Vault or secret manager handles for credentials                   |
| `policies`    | optional | Quality gates (coverage thresholds, required approvals)           |

### Example: Generate Pipeline

```json
{
  "pipeline_id": "pipeline-billing-service",
  "repository": "git@github.com:appsmithery/billing-service.git",
  "platform": "github",
  "stages": [
    {
      "name": "lint",
      "jobs": [
        { "runner": "ubuntu-latest", "commands": ["npm ci", "npm run lint"] }
      ]
    },
    {
      "name": "test",
      "jobs": [
        { "runner": "ubuntu-latest", "commands": ["npm test -- --coverage"] }
      ]
    },
    {
      "name": "deploy",
      "jobs": [
        {
          "runner": "ubuntu-latest",
          "commands": ["./scripts/deploy.sh staging"]
        }
      ]
    }
  ],
  "triggers": {
    "pull_request": true,
    "push": ["main", "release/*"],
    "schedule": "0 2 * * *"
  },
  "policies": {
    "coverage_threshold": 85,
    "require_approvals": 1
  }
}
```

## API Surface

| Method | Path               | Purpose                                      | Primary Request Fields                              | Success Response Snapshot                                               |
| ------ | ------------------ | -------------------------------------------- | --------------------------------------------------- | ----------------------------------------------------------------------- |
| `POST` | `/pipeline`        | Create or update pipeline definition         | Request body above                                  | `{ "pipeline_id": "pipeline-billing-service", "status": "configured" }` |
| `POST` | `/trigger`         | Manually trigger a pipeline run              | `pipeline_id`, optional `branch`, `parameters`      | `{ "run_id": "run-1204", "status": "queued" }`                          |
| `GET`  | `/status/{run_id}` | Retrieve build/test/deploy progress and logs | n/a                                                 | `{ "run_id": "run-1204", "status": "succeeded", "artifacts": [...] }`   |
| `POST` | `/promote`         | Promote artifacts to next environment        | `run_id`, `target_environment`, optional `strategy` | `{ "promotion_id": "prom-42", "status": "in_progress" }`                |

## Outputs & Artifacts

- Platform-specific workflow files (YAML/JSON) with inline documentation.
- Build logs, test reports (JUnit, Coverage XML), SBOM manifests.
- Deployment manifests and rollback scripts for each environment.
- Promotion manifests capturing artifact provenance and approvals.

## Observability & Metrics

- Structured logs labelled with `pipeline_id`, `run_id`, `stage`, `status`.
- Metrics: `cicd_run_duration_seconds`, `cicd_failure_rate`, `cicd_queue_depth`.
- Supports OpenTelemetry spans `cicd.plan`, `cicd.execute`, `cicd.deploy`, `cicd.promote`.

## Integration Guidelines

- Provide consistent `pipeline_id` values so updates patch in place; otherwise the agent creates new pipelines.
- Attach secret references (not raw secrets) for registry credentials, deploy keys, etc.
- When chaining with the Feature Development Agent, pass the generated branch and build matrix so pipelines compile targeted jobs only.
- Use `/promote` to orchestrate multi-env rollouts; specify `strategy` (`blue_green`, `canary`, `direct`) and approval requirements.

## Failure Modes

- **422 Validation error:** Missing stage definitions or unsupported platform features.
- **409 Conflict:** Pipeline run already active for the same commit; either cancel or await completion.
- **502 Platform error:** Underlying CI provider returned failure; response provides `external_run_url` and `logs_ref` for debugging.
