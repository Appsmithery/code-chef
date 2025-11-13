# Dev-Tools Documentation

## Overview

Dev-Tools is a single-root development environment consolidating AI agents, MCP gateway, Docker compose stack, and operational configurations for remote development workflows.

## Quick Start

### Prerequisites

- Docker & Docker Compose
- VS Code with Remote-SSH and Dev Containers extensions
- SSH access to your deployment droplet

### Local Setup

1. Clone the repository:

```bash
git clone https://github.com/Appsmithery/Dev-Tools.git
cd Dev-Tools
```

2. Copy environment template:

```bash
cp configs/env/.env.example configs/env/.env
# Edit .env with your configuration
```

3. Make scripts executable:

```bash
chmod +x scripts/*.sh
```

4. Start services:

```bash
./scripts/up.sh
```

### Remote Development

1. Connect via Remote-SSH to your droplet
2. Open the Dev-Tools folder
3. Click "Reopen in Container" when prompted
4. VS Code will attach to the devcontainer

## Architecture

See [ARCHITECTURE.md](ARCHITECTURE.md) for system design and component relationships.

## Agent Endpoints

See [AGENT_ENDPOINTS.md](AGENT_ENDPOINTS.md) for complete API documentation.

## Handbook

See [HANDBOOK.md](HANDBOOK.md) for operational procedures and troubleshooting.

## Documentation Indices

- [CODEBASE_INDEX.md](CODEBASE_INDEX.md) – generated inventory of scripts, tooling, and automation (currently a migration placeholder with regeneration steps).
- [DOCUMENTATION_INDEX.md](DOCUMENTATION_INDEX.md) – canonical documentation table of contents (migration placeholder pending automation tooling).
