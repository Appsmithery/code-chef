# Infrastructure Agent

Self-service infrastructure engineer that converts platform requirements into reproducible infrastructure code, deployment workflows, and environment health checks.

## Overview

The Infrastructure Agent handles the full lifecycle from IaC authoring to rollout execution and verification. By describing desired environments declaratively, orchestration systems can offload provisioning, configuration drift detection, and rollout status reporting to this agent. Documentation emphasizes machine-readable contracts and operational safeguards.

## Core Responsibilities

- **Blueprint authoring:** Generate Terraform, Pulumi, Docker Compose, or Kubernetes manifests aligned with platform standards.
- **Configuration management:** Synthesize parameter files, secrets mappings, and environment-specific overrides.
- **Deployment automation:** Execute apply plans, monitor rollout status, and perform canary/batch strategies when requested.
- **Compliance & policy checks:** Validate templates against guardrails (cost budgets, tagging policies, security baselines).
- **Telemetry propagation:** Emit health and drift metrics to shared observability stacks.

## Input Contract

| Field            | Required | Description                                                             |
| ---------------- | -------- | ----------------------------------------------------------------------- |
| `deployment_id`  | ✅       | Unique identifier for traceability                                      |
| `environment`    | ✅       | Target environment name (`dev`, `staging`, `prod`, etc.)                |
| `template_spec`  | ✅       | High-level infra spec (modules, services, scaling targets)              |
| `runtime`        | ✅       | Desired provisioning tool (`terraform`, `helm`, `docker-compose`, etc.) |
| `parameters`     | optional | Key/value overrides or secret references                                |
| `policy_profile` | optional | Compliance bundle to enforce before apply                               |

### Example Request: `POST /generate`

```json
{
  "deployment_id": "infra-2025-114",
  "environment": "staging",
  "runtime": "terraform",
  "template_spec": {
    "cloud": "aws",
    "modules": [
      { "name": "vpc", "version": "3.21.0", "cidr": "10.16.0.0/16" },
      { "name": "ecs-service", "version": "1.4.5", "desired_count": 3 }
    ],
    "observability": {
      "logging": "cloudwatch",
      "metrics": "prometheus"
    }
  },
  "parameters": {
    "aws_region": "us-east-2",
    "container_image": "ghcr.io/appsmithery/mcp-gateway:latest"
  },
  "policy_profile": "production-guardrails"
}
```

## API Surface

| Method | Path                      | Purpose                                                    | Primary Request Fields                                        | Success Response Snapshot                                                         |
| ------ | ------------------------- | ---------------------------------------------------------- | ------------------------------------------------------------- | --------------------------------------------------------------------------------- |
| `POST` | `/generate`               | Produce IaC templates, parameter files, and documentation  | Request body above                                            | `{ "deployment_id": "infra-2025-114", "artifacts": {"iac": "s3://.../main.tf"} }` |
| `POST` | `/deploy`                 | Execute apply/rollout using previously generated artifacts | `deployment_id`, optional overrides (`plan_only`, `strategy`) | `{ "deployment_id": "infra-2025-114", "status": "applying" }`                     |
| `GET`  | `/status/{deployment_id}` | Fetch rollout state, drift checks, and audit logs          | n/a                                                           | `{ "deployment_id": "infra-2025-114", "status": "healthy", "checks": [...] }`     |
| `POST` | `/drift-scan`             | Trigger on-demand drift detection                          | `deployment_id`, optional `scope`                             | `{ "deployment_id": "infra-2025-114", "status": "scanning" }`                     |

## Outputs & Artifacts

- IaC bundles (Terraform modules, Helm charts, Compose files) with templated variables.
- Secrets manifest referencing vault paths (never plain secrets inline).
- Deployment playbooks outlining command execution order and rollback instructions.
- Drift & compliance reports (SARIF/JSON) stored in artifact buckets.

## Execution Flow

1. Validate template spec + policy profile compatibility.
2. Generate IaC + configuration assets in a temporary workspace.
3. Run static analysis (terraform validate, tflint, kubeval, etc.).
4. Optionally run `plan_only` or full apply.
5. Stream progress events; persist audit log entries.
6. Publish artifacts and status summary to orchestrator.

## Observability & Metrics

- Structured logs attach `deployment_id`, `environment`, and `stage` fields.
- Prometheus metrics: `infra_apply_duration_seconds`, `infra_policy_violations_total`, `infra_drift_events_total`.
- Exposes OpenTelemetry spans `infra.generate`, `infra.plan`, `infra.apply`, `infra.drift-scan`.

## Integration Guidelines

- Use deterministic `deployment_id` values so retries remain idempotent.
- Attach policy profiles to enforce org-specific guardrails; unsupported policies return `422` with rule IDs.
- Provide runtime credentials via secret mounts (Azure Key Vault, AWS IAM roles, etc.); do not inline sensitive keys.
- For blue/green or canary rollouts, pass `strategy` (`blue_green`, `canary`, `rolling`) and `traffic_shift` parameters to `/deploy`.

## Failure Modes & Recovery

- **422 Validation error:** Template spec missing required fields or violates policy profile.
- **409 Conflict:** Another deployment with same `deployment_id` in progress; wait for completion or cancel before retrying.
- **502 Runtime failure:** Underlying provisioning tool returned non-zero exit; response includes `logs_ref` for troubleshooting.
- **Drift detected:** `/status` payload includes `drift` section with remediation steps; orchestrator should schedule follow-up.
