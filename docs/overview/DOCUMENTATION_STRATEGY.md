# Documentation Strategy for Dev-Tools

**Last Updated:** 2025-11-02
**Status:** Active

---

## Overview

Dev-Tools uses a **dual-track documentation strategy** optimizing for both AI agents (technical reference) and human developers (usage guides). This document defines the standards, locations, and workflows for maintaining high-quality, minimal documentation across the repository.

---

## Documentation Types

### 1. Agent-Optimized (Technical Reference)

**Purpose:** Enable AI agents to understand architecture, APIs, and implementation details without human intervention.
**Location:** `README.md` files co-located with components

**Format:**

- Markdown with code blocks
- Inline JSDoc/TSDoc comments
- Type definitions and interfaces
- Architecture diagrams (Mermaid)
- API reference tables

**Content:**

```markdown
# Component Name

## Architecture

[Technical diagram or description]

## API Reference

### Class: ComponentName

- `method(param: Type): ReturnType` - Description

## Integration Points

- Dependencies: X, Y, Z
- Exports: A, B, C
- Configuration: `config.json`

## Testing

- Unit tests: `__tests__/component.test.ts`
- Coverage target: 80%

## Examples

[Code examples with full context]
```

**Examples:**

- `agents/client-service-layer/README.md` - MCP client architecture
- `observability/highlight-node/README.md` - Observability integration
- `testing/README.md` - Test infrastructure

---

### 2. Human-Optimized (Usage Guides)

**Purpose:** Help developers get started, troubleshoot issues, and understand workflows.
**Location:** `docs/` directory

**Format:**

- Narrative documentation
- Step-by-step tutorials
- Troubleshooting guides
- Decision trees
- Visual aids (screenshots, diagrams)

**Content:**

```markdown
# Feature Name Guide

## Quick Start

1. Install dependencies: `npm install`
2. Configure: Edit `config/file.json`
3. Run: `npm run command`

## Common Workflows

### Workflow A

[Step-by-step with explanations]

### Workflow B

[Step-by-step with explanations]

## Troubleshooting

**Problem:** Error message
**Solution:** Fix instructions

## FAQ

**Q:** Common question?
**A:** Answer with context
```

**Examples:**

- `docs/SETUP_GUIDE.md` - Complete setup instructions
- `docs/SECRETS_MANAGEMENT.md` - Secrets configuration guide
- `docs/PHASE5_QUICK_REFERENCE.md` - Workflow reference

---

## Documentation Standards

### Required Documentation

| Component Type  | Required Files                              | Update Frequency |
| --------------- | ------------------------------------------- | ---------------- |
| Agent Profile   | `README.md`, `config.json`, `toolset.jsonc` | Per feature      |
| MCP Server      | `README.md`, `index.ts` (JSDoc)             | Per API change   |
| Script/Tool     | Inline `--help` flag, usage comments        | On creation      |
| Feature/Module  | `README.md` in module directory             | Per change       |
| Repository Root | `README.md`, `docs/SETUP_GUIDE.md`          | Quarterly        |

### Forbidden Documentation

**Do NOT create:**

- One-off summary files outside designated locations
- Duplicate documentation (check existing docs first)
- Version-specific docs (use version control instead)
- Implementation notes in root (use component README)

**Designated Summary Locations:**

- Execution reports: `reports/context/latest/`
- Session context: `workspace/context/session_store/`
- Archived plans: `workspace/archive/plans-YYYYMMDD/`

---

## Maintenance Workflows

### Automated Maintenance

Run regular audits to prevent documentation drift:

```bash
# Preview audit (recommended weekly)
npm run maintenance:audit

# Archive obsolete files
npm run maintenance:archive

# Full cleanup (archive + remove temp files)
npm run maintenance:cleanup

# Regenerate documentation index
npm run validate:docs

# Regenerate file tree
npm run validate:filetree
```

### Manual Review Triggers

Trigger documentation review when:

1. **Major Feature Added:** Update component README + user guide
2. **API Change:** Update type definitions + examples
3. **Configuration Change:** Update setup guide + config docs
4. **Deprecation:** Archive old docs, add migration guide
5. **Quarterly Review:** Audit all docs for accuracy

### Documentation Checklist

Before committing changes:

- [ ] Component README updated (if applicable)
- [ ] User guide updated (if needed)
- [ ] Code examples tested
- [ ] Inline comments added for complex logic
- [ ] `npm run validate:docs` passes
- [ ] No obsolete files remain

---

## Dev-Tools Specific Patterns

### Agent Profiles

**Technical (README.md):**

```markdown
# Agent: Profile Name

## Purpose

One-sentence description

## Configuration

- `config.json`: Core settings
- `toolset.jsonc`: Available tools
- `taskfile.yaml`: Task definitions

## Integration

- MCP Servers: X, Y, Z
- Dependencies: A, B, C

## Testing

- Test suite: `testing/agents/profile-name/`
```

**Usage (docs/):**

```markdown
# Using the Profile Name Agent

## When to Use

[Decision criteria]

## Getting Started

1. Configure profile: `cp agents/_profile-name/config.json.example config.json`
2. Install dependencies: `npm install`
3. Run: `task profile-name:start`

## Common Tasks

[Workflow examples]
```

### MCP Servers

**Technical (server/README.md):**

```typescript
/**
 * Server Name MCP Server
 *
 * @description Brief purpose
 * @protocol MCP version
 * @transport stdio | SSE
 */

/**
 * Tool: toolName
 * @param {string} param - Description
 * @returns {Promise<Result>} Description
 */
```

**Usage (docs/):**

```markdown
# Server Name MCP Server

## Installation

[Setup steps]

## Available Tools

### Tool Name

**Purpose:** What it does
**Usage:** Code example
**Options:** Parameters
```

### Scripts & Automation

**Inline Help (required):**

```bash
#!/usr/bin/env bash
#
# script-name.sh - Brief description
#
# Usage: ./script-name.sh [OPTIONS]
#
# Description:
#   Detailed description
#
# Options:
#   --option    Description
#   --help      Show this help

if [[ "${1:-}" == "--help" ]]; then
  awk '/^#/{if(NR>1 && !/#!/)print substr($0,3)}; /^[^#]/{exit}' "$0"
  exit 0
fi
```

**External Docs (optional, only if complex):**

- Add to `docs/scripts/` if script has multiple workflows
- Reference from component README if integrated

---

## Quality Metrics

### Documentation Coverage

**Minimum Requirements:**

- All exported functions: JSDoc comments
- All public classes: Class-level documentation
- All agent profiles: Complete README + config docs
- All MCP servers: Tool documentation + examples
- All scripts: Inline `--help` flag

### Maintenance Health

Track documentation health via automated audit:

```bash
npm run maintenance:audit
```

**Healthy Repository:**

- Zero obsolete plan files
- Zero undocumented scripts
- Zero duplicate documentation
- DOCUMENTATION_INDEX.md auto-generated daily
- File tree regenerated on structure changes

**Warning Signs:**

- Multiple phase/plan files outside archive
- Scripts without `--help` flags
- README files > 6 months old without updates
- Broken links in documentation index

---

## Migration & Archival

### When to Archive

Archive documentation when:

1. Feature deprecated or removed
2. Plan/phase completed
3. Replaced by newer documentation
4. No longer referenced by code

### Archival Process

```bash
# Preview what will be archived
npm run maintenance:audit

# Execute archival
npm run maintenance:archive

# Verify archived files
ls -la workspace/archive/maintenance-YYYYMMDD_HHMMSS/
```

**Archive Structure:**

```
workspace/archive/
  maintenance-20250102_143022/
    docs/
      OLD_PHASE_PLAN.md
    scripts/
      obsolete-script.sh
  plans-20241201/
    INTEGRATION_PLAN.md
  schemas/
    legacy-secrets.schema.json
```

---

## Integration with Development Workflows

### On Feature Development

```bash
# 1. Read existing docs
cat agents/client-service-layer/README.md

# 2. Implement feature
# ... code changes ...

# 3. Update documentation
vim agents/client-service-layer/README.md
vim docs/CLIENT_SERVICE_GUIDE.md

# 4. Validate
npm run validate:docs
npm run maintenance:audit

# 5. Commit
git add -A
git commit -m "feat: add feature X with documentation"
```

### On Repository Cleanup

```bash
# 1. Run audit
npm run maintenance:audit

# 2. Review report
cat reports/maintenance/maintenance-audit-*.md

# 3. Execute cleanup
npm run maintenance:cleanup

# 4. Regenerate indices
npm run validate:docs
npm run validate:filetree

# 5. Commit
git add -A
git commit -m "chore: automated maintenance cleanup"
```

### On Release

```bash
# 1. Update version
npm version patch

# 2. Update CHANGELOG
vim CHANGELOG.md

# 3. Validate all docs
npm run validate:docs
npm run maintenance:audit

# 4. Archive completed plans
npm run maintenance:archive

# 5. Tag release
git tag -a v1.0.1 -m "Release v1.0.1"
git push --tags
```

---

## Examples & Templates

### Component README Template

```markdown
# Component Name

**Purpose:** One-sentence description
**Status:** Active | Experimental | Deprecated
**Maintainer:** Team/Person

## Architecture

[Diagram or description]

## Installation

[Setup steps if standalone]

## API Reference

### Class/Function Name

[Type signatures and descriptions]

## Configuration

[Config file examples]

## Testing

- Unit tests: `path/to/tests`
- Coverage: X%
- Run: `npm test`

## Integration

- Used by: [List components]
- Depends on: [List dependencies]
- Exports: [List public APIs]

## Troubleshooting

**Problem:** Common issue
**Solution:** Fix steps

## Examples

[Code examples]

## References

- [Link to related docs]
```

### User Guide Template

```markdown
# Feature Name Guide

**Audience:** Developers | Operators | Contributors
**Prerequisites:** [List requirements]

## Overview

[What this feature does and why it's useful]

## Quick Start

[Minimal steps to get started]

## Detailed Usage

### Workflow A

[Step-by-step instructions]

### Workflow B

[Step-by-step instructions]

## Configuration

[Config options with examples]

## Troubleshooting

[Common problems and solutions]

## Advanced Topics

[Optional advanced usage]

## FAQ

[Common questions]

## Next Steps

[Links to related guides]
```

---

## Continuous Improvement

### Documentation Review Cycle

**Weekly:**

- Run `npm run maintenance:audit`
- Fix broken links
- Update outdated examples

**Monthly:**

- Review component READMEs for accuracy
- Update setup guides with new workflows
- Archive completed plans

**Quarterly:**

- Full documentation audit
- User guide updates based on feedback
- Documentation strategy refinement

### Metrics to Track

1. **Coverage:** % of components with README
2. **Freshness:** Days since last doc update
3. **Accuracy:** User-reported issues
4. **Maintenance:** Obsolete files remaining
5. **Automation:** Scripts with `--help` flags

---

## References

- [Copilot Instructions](../.github/copilot-instructions.md) - Agent guidelines
- [Setup Guide](./SETUP_GUIDE.md) - Initial repository setup
- [Secrets Management](./SECRETS_MANAGEMENT.md) - Secrets configuration
- [Documentation Index](./DOCUMENTATION_INDEX.md) - Auto-generated index

---

**Note:** This strategy evolves with the project. Suggest improvements via pull request or issue.
