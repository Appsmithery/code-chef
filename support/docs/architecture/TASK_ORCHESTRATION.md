# Task Orchestration Guide

## Overview

Dev-Tools uses [Taskfile.dev](https://taskfile.dev) for organized, hierarchical automation. This enables modular, MECE-aligned workflows for agent profiles, toolchain, documentation, and reporting.

## Namespace Structure

### agents/

Agent-specific workflows:

- `development-workflow`: Testing, linting, validation
- `observability`: Monitoring and telemetry
- `production-ops`: E2E testing, deployment
- `system-architect`: Security, structure validation

### toolchain/

Development environment setup:

- `init`: Initialize environment
- `dependency:install`: Install dependencies
- `code-quality`: Lint, format, test
- `build`: Build all packages

### docs/

Documentation management:

- `update`: Regenerate documentation index
- `validate`: Check documentation structure
- `chatmodes:sync`: Update agent chatmode symlinks

### reports/

Report management:

- `sync`: Sync agent reports
- `clean`: Clean report directories

## Quick Start

```bash
# Initialize environment
task orchestration:init

# Run full validation
task orchestration:validate

# Agent-specific tasks
task agents:dev-workflow:test
task agents:prod-ops:test:e2e

# Update documentation
task docs:update
```

## VS Code Integration

Tasks appear in VS Code Task Explorer organized by namespace. Use the Task panel to run, validate, or chain workflows for any agent or global operation.

## Customization

- Add new agent profiles by creating a Taskfile in `.taskfiles/agents/` and a matching instructions file in `docs/instructions/`.
- Extend toolchain, docs, or reports as needed for your repo or submodule integration.

## Troubleshooting

- If tasks do not appear, check for YAML syntax errors in Taskfile(s).
- Use `task --list` to see all available tasks and namespaces.
- Validate chatmode symlinks with `task docs:chatmodes:sync`.

---

For more, see the [Taskfile.dev documentation](https://taskfile.dev/usage/).
