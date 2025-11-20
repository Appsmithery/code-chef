# Agent Icons Reference

This document provides a reference for all agent-specific icons used in the Dev-Tools platform.

## Icon Overview

| Agent | Icon | Color | Description |
|-------|------|-------|-------------|
| **cicd** | ![cicd](../extensions/vscode-devtools-copilot/src/icons/cicd.png) | Orange (#F97316) | Deployment and automation |
| **code-review** | ![code-review](../extensions/vscode-devtools-copilot/src/icons/code-review.png) | Green (#22C55E) | Code quality assurance and review |
| **documentation** | ![documentation](../extensions/vscode-devtools-copilot/src/icons/documentation.png) | Teal (#14B8A6) | Knowledge and documentation |
| **feature-dev** | ![feature-dev](../extensions/vscode-devtools-copilot/src/icons/feature-dev.png) | Blue (#3B82F6) | Feature development and implementation |
| **infrastructure** | ![infrastructure](../extensions/vscode-devtools-copilot/src/icons/infrastructure.png) | Navy (#1E3A8A) | Infrastructure and DevOps |
| **orchestrator** | ![orchestrator](../extensions/vscode-devtools-copilot/src/icons/orchestrator.png) | Purple (#9333EA) | Task coordination and routing |

## Usage

### In Linear

Each agent has a corresponding label in the Linear workspace:

- `agent: cicd` - Deployment and automation
- `agent: code-review` - Code quality assurance and review
- `agent: documentation` - Knowledge and documentation
- `agent: feature-dev` - Feature development and implementation
- `agent: infrastructure` - Infrastructure and DevOps
- `agent: orchestrator` - Task coordination and routing

### In VS Code Extension

Icons are automatically loaded via the extension:

```typescript
import { getAgentIcon, getAgentColor } from './extension';

// Get icon URI for status bar
const icon = getAgentIcon('feature-dev');

// Get color for styling
const color = getAgentColor('feature-dev'); // Returns: #3B82F6
```

### In Documentation

Reference icons in markdown files:

```markdown
![Orchestrator](./extensions/vscode-devtools-copilot/src/icons/orchestrator.png)
```

## Color Palette

The agent icons use a coordinated color scheme:

- **Orange** (#F97316) - cicd
- **Green** (#22C55E) - code-review
- **Teal** (#14B8A6) - documentation
- **Blue** (#3B82F6) - feature-dev
- **Navy** (#1E3A8A) - infrastructure
- **Purple** (#9333EA) - orchestrator

## Icon Files

All icon files are located in:
```
extensions/vscode-devtools-copilot/src/icons/
```

| File | Agent | Source |
|------|-------|--------|
| `cicd.png` | cicd | minions_orange.png |
| `code-review.png` | code-review | minions_green.png |
| `documentation.png` | documentation | minions_teal.png |
| `feature-dev.png` | feature-dev | minions_blue.png |
| `infrastructure.png` | infrastructure | minions_navy.png |
| `orchestrator.png` | orchestrator | minions_purple.png |

