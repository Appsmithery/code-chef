# Agent Icons

This directory contains unique icons for each of the 6 Dev-Tools agents. Each icon uses the minion design with distinct color schemes:

## Agent Icon Mapping

| Agent              | Icon File            | Color  | Purpose                                |
| ------------------ | -------------------- | ------ | -------------------------------------- |
| **Orchestrator**   | `orchestrator.png`   | Purple | Task coordination and routing          |
| **Feature-Dev**    | `feature-dev.png`    | Blue   | Feature development and implementation |
| **Code-Review**    | `code-review.png`    | Green  | Code quality assurance                 |
| **Infrastructure** | `infrastructure.png` | Navy   | Infrastructure and DevOps              |
| **CI/CD**          | `cicd.png`           | Orange | Deployment and automation              |
| **Documentation**  | `documentation.png`  | Teal   | Knowledge and documentation            |

## Usage

### In VS Code Extension

Icons are referenced in `extension.ts` for status bar and webview displays:

```typescript
const agentIcon = context.asAbsolutePath(`src/icons/${agentName}.png`);
```

### In Linear

1. Go to Linear → Settings → Teams → Project Roadmaps
2. Click Labels section
3. Upload corresponding icon for each agent label
4. Icons appear in issue cards, filters, and roadmap views

### In Documentation

Reference icons in markdown:

```markdown
![Orchestrator](./src/icons/orchestrator.png)
```

## File Specifications

- **Format**: PNG with transparency
- **Size**: Variable (original minion design dimensions)
- **Source**: Minion design by .minions branding
- **License**: Used with permission for Dev-Tools project

## Color Palette

- **Purple** (#9333EA): Orchestrator - Primary coordination
- **Blue** (#3B82F6): Feature-Dev - Development focus
- **Green** (#22C55E): Code-Review - Quality/validation
- **Navy** (#1E3A8A): Infrastructure - Stability/foundation
- **Orange** (#F97316): CI/CD - Active deployment
- **Teal** (#14B8A6): Documentation - Knowledge/information
