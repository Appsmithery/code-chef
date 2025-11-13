# Infrastructure Agent

Manages infrastructure as code, deployments, and system configuration.

## Responsibilities
- IaC generation (Terraform, Docker Compose)
- Deployment automation
- Environment configuration
- Resource provisioning

## Endpoints
- `POST /infrastructure` - Generate infrastructure code
- `POST /deploy` - Deploy infrastructure
- `GET /status/{id}` - Check deployment status