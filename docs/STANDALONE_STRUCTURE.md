# Dev-Tools Standalone Repository Structure

**Purpose:** Define the end-state directory structure and organization for standalone mode
**Status:** Target Architecture
**Last Updated:** 2025-11-02

---

## 🎯 Overview

This document defines the target directory structure for Dev-Tools as a standalone development toolset, independent of any parent project. The structure emphasizes:

- **Clear separation of concerns** - Each directory has a single, well-defined purpose
- **Standalone operation** - No hardcoded paths to external projects
- **Extensibility** - Easy to add new components without restructuring
- **Maintainability** - Deprecated artifacts properly archived

---

## 📂 End-State Directory Structure

### Root Level

```
Dev-Tools/
├── .github/              # GitHub configuration
│   ├── workflows/        # CI/CD workflows
│   ├── copilot-instructions.md
│   └── agents/           # Agent-specific configs (off-limits to main agents)
├── .vscode/              # VS Code workspace settings
│   └── mcp_config.json   # MCP primary configuration
├── agents/               # AI agent infrastructure
├── automation/           # CI/CD automation
├── config/               # Shared configuration files
├── context/              # Legacy context management (deprecated)
├── diagnostics/          # Environment diagnostics
├── docs/                 # Documentation
├── observability/        # Telemetry and monitoring
├── reports/              # Generated reports and artifacts
├── scripts/              # Automation scripts
├── testing/              # Test infrastructure
├── workspace/            # Runtime files and archives
├── .env.example          # Environment template
├── .gitignore            # Git exclusions
├── CHANGELOG.md          # Version history
├── LICENSE               # MIT License
├── package.json          # Root package manifest
├── package-lock.json     # Dependency lockfile
├── README.md             # Main documentation
├── Taskfile.yml          # Task runner configuration
└── tsconfig.json         # TypeScript configuration
```

---

## 📁 Detailed Directory Specifications

### 1. `/agents/` - AI Agent Infrastructure

**Purpose:** AI agent profiles, MCP infrastructure, and context management

```
agents/
├── _development-workflow/       # Development workflow agent
│   └── instructions.md          # Agent persona and instructions
├── _observability/              # Observability agent
│   └── instructions.md
├── _production-ops/             # Production operations agent
│   ├── instructions.md
│   └── deployment-checklist-template.md
├── _system-architect/           # System architect agent
│   └── instructions.md
├── client-service-layer/        # [NPM WORKSPACE] MCP client package
│   ├── src/                     # TypeScript source
│   ├── __tests__/               # Test files
│   ├── package.json
│   ├── tsconfig.json
│   └── README.md
├── context/                     # Context management
│   ├── store/                   # Context templates
│   ├── CONTEXTMANAGER_QUICKREF.md
│   ├── MCP_MODE_TOOL_MATRIX.md
│   ├── README.md
│   └── TEST_RUN_EXPECTATIONS.md
├── mcp-servers/                 # MCP server implementations
│   ├── utility/                 # [NPM WORKSPACE] Utility server
│   │   ├── src/
│   │   ├── dist/
│   │   ├── package.json
│   │   └── tsconfig.json
│   ├── observability-server.js  # Observability server
│   ├── active-registry.json     # Server registry
│   ├── MCP-package.json         # MCP package config
│   ├── package.json
│   ├── tool-reference.md
│   └── README.md
└── scripts/                     # Agent utility scripts
    ├── deploy-client-service-layer.sh
    ├── hydrate-local-env.sh
    ├── start-mcp.sh
    └── stop-mcp.sh
```

**Requirements:**

- All agent profiles must have `instructions.md`
- MCP configuration loaded via `ConfigLocator`
- Client service layer must be dependency-injection ready
- No hardcoded paths to external projects

---

### 2. `/automation/` - CI/CD Automation

**Purpose:** Continuous integration, deployment automation, and pipeline definitions

```
automation/
└── ci-cd/                       # CI/CD pipeline artifacts
    ├── check-docs-schema.sh     # Documentation validation
    ├── patch-diagrams.sh        # Diagram generation
    ├── stage-taxonomy.sh        # Pipeline taxonomy
    └── README.md
```

**Requirements:**

- All scripts must work in CI environment
- No interactive prompts
- Proper error codes (0 = success, >0 = failure)
- Logging to stdout/stderr

---

### 3. `/config/` - Shared Configuration

**Purpose:** Centralized configuration files consumed by all components

```
config/
├── mcp-config.json              # MCP fallback configuration
├── tsconfig.json                # (if needed for shared TS config)
└── README.md                    # Configuration guide
```

**Requirements:**

- Configuration files must be JSON or YAML
- Well-documented with inline comments where possible
- Environment-specific overrides via environment variables
- No secrets committed (use .env instead)

---

### 4. `/diagnostics/` - Environment Diagnostics

**Purpose:** Cross-platform environment validation and analysis

```
diagnostics/
├── helpers/                     # Helper utilities
│   ├── scan-repo-structure.ts   # Repository structure scanner
│   ├── inventory-packages.ts    # Package inventory
│   └── detect-languages.ts      # Language detection
├── schemas/                     # JSON schemas for validation
│   └── environment-schema.json
├── collect-env.ts               # Main diagnostic CLI
├── collect-env.ps1              # PowerShell wrapper (Windows)
└── README.md
```

**Requirements:**

- Cross-platform (Linux, macOS, Windows)
- Output structured JSON reports
- Reports saved to `reports/diagnostics/`
- Non-destructive (read-only operations)

---

### 5. `/docs/` - Documentation

**Purpose:** All project documentation and guides

```
docs/
├── archive/                     # Archived/historical documentation
│   ├── extraction-docs/         # Extraction process docs
│   ├── phase-docs/              # Phase-specific docs
│   ├── submodule-docs/          # Submodule integration docs
│   └── README.md                # Archive index
├── audit/                       # Audit reports
│   └── *.md                     # Generated audit reports
├── inventories/                 # Generated inventories
│   └── file-tree-*.md           # File tree snapshots
├── provenance/                  # Provenance and history
│   └── coverage.md              # Coverage tracking
├── standalone/                  # Standalone-specific docs
│   └── GETTING_STARTED.md       # Standalone quick start
├── ARCHITECTURE.md              # Architecture overview
├── DOCUMENTATION_INDEX.md       # Auto-generated doc index
├── PHASE_B_SUMMARY.md           # Phase B completion summary
├── QUICK_START.md               # Quick start guide
├── REFACTOR_CHECKLIST.md        # Migration checklist
├── SETUP_GUIDE.md               # Detailed setup
└── STANDALONE_STRUCTURE.md      # This file
```

**Requirements:**

- Markdown format for all docs
- DOCUMENTATION_INDEX.md auto-generated
- Archive old/obsolete docs, don't delete
- Clear separation: active docs vs. archived docs

---

### 6. `/observability/` - Telemetry & Monitoring

**Purpose:** Highlight.io integration and observability tooling

```
observability/
└── highlight-node/              # [NPM WORKSPACE] Highlight.io package
    ├── src/                     # TypeScript source
    ├── dist/                    # Compiled output
    ├── package.json
    ├── tsconfig.json
    └── README.md
```

**Requirements:**

- Lightweight, non-blocking telemetry
- Configurable via environment variables
- No telemetry in development by default
- Clear opt-out mechanism

---

### 7. `/reports/` - Generated Reports

**Purpose:** Output directory for generated reports and artifacts

```
reports/
├── audit/                       # Repository audit reports
│   └── standalone-audit-*.md
├── context/                     # Context reports
│   └── latest/                  # Latest diagnostic outputs
│       ├── filetree.txt
│       ├── repo-tree-summary.txt
│       └── *.json
├── diagnostics/                 # Diagnostic outputs
├── monitoring/                  # Monitoring reports
├── observability/               # Observability data
├── source-prospectpro/          # (Future) ProspectPro examples
│   └── examples/
├── validation/                  # Validation reports
└── extraction-manifest.json     # (Legacy) Extraction manifest
```

**Requirements:**

- Timestamped filenames for reports
- JSON format for structured data
- Markdown format for human-readable reports
- `.gitignore` excludes large/temporary reports

---

### 8. `/scripts/` - Automation Scripts

**Purpose:** Reusable automation entry points

```
scripts/
├── automation/                  # Main automation scripts
│   ├── legacy/                  # (Future) Archived legacy scripts
│   ├── audit-repo-standalone.sh # Standalone audit
│   ├── execute-ci-cd-setup.sh   # CI/CD orchestration
│   ├── init-mcp.sh              # MCP initialization
│   ├── migration-dry-run.sh     # Migration validator
│   ├── repo_scan.sh             # Repository scanner
│   ├── reset-mcp.sh             # MCP reset
│   └── *.sh                     # Other automation scripts
├── context/                     # Context management scripts
├── deployment/                  # Deployment scripts
├── diagnostics/                 # Diagnostic helpers
├── docs/                        # Documentation scripts
├── legacy/                      # Legacy/deprecated scripts
│   ├── extraction/              # Extraction scripts
│   ├── phase-scripts/           # Phase-specific scripts
│   └── submodule/               # Submodule integration
├── operations/                  # Operational scripts
├── roadmap/                     # Roadmap management
├── setup/                       # Setup scripts
│   └── .codespaces-init.sh      # Codespaces init
├── testing/                     # Testing scripts
├── tooling/                     # Tooling scripts
│   └── update-docs-index.sh     # Doc index generator
└── README.md
```

**Requirements:**

- All active scripts must have `--help` flag
- Standalone-safe defaults (no hardcoded paths)
- Clear script naming convention
- Deprecated scripts moved to `scripts/legacy/`

---

### 9. `/testing/` - Test Infrastructure

**Purpose:** Test suites, fixtures, and testing utilities

```
testing/
├── agents/                      # Agent-specific tests
│   ├── client-service-layer/
│   ├── context/
│   └── mcp-servers/
├── configs/                     # Test configurations
├── dev-tools/                   # Dev-tools tests
├── fixtures/                    # Test fixtures
├── integration/                 # Integration tests
│   ├── api/
│   └── phase5/
├── reports/                     # Test reports
├── unit/                        # Unit tests
│   ├── app/
│   ├── dev-tools/
│   └── mcp/
├── utils/                       # Test utilities
│   └── setup.ts
├── README.md
└── Taskfile.yml
```

**Requirements:**

- Vitest for unit tests (target)
- Jest compatibility during migration
- Clear separation: unit, integration, e2e
- Test fixtures isolated from production data

---

### 10. `/workspace/` - Runtime & Archives

**Purpose:** Working files, runtime state, and historical archives

```
workspace/
├── archive/                     # Historical archives
│   ├── legacy-context-*/        # Legacy context snapshots
│   └── legacy-scripts-*/        # Legacy script snapshots
├── context/                     # Runtime context
│   ├── archive/                 # Archived context
│   └── session_store/           # Session-specific files
├── runtime/                     # (Future) Runtime state
│   └── mcp-status.json          # MCP runtime status
└── README.md
```

**Requirements:**

- Not for tracked artifacts (use `/reports/` instead)
- `.gitignore` excludes most workspace files
- Keep only essential runtime state
- Archive snapshots timestamped

---

## 🔧 Configuration Files (Root)

### `.env.example`

Template for environment configuration:

```bash
# Core
NODE_ENV=development

# Supabase (optional)
# SUPABASE_URL=https://your-project.supabase.co
# SUPABASE_ANON_KEY=your_key_here

# Highlight.io (optional)
# HIGHLIGHT_PROJECT_ID=your_project_id

# GitHub (optional)
# GITHUB_TOKEN=ghp_your_token_here
```

### `package.json` - npm Scripts

**Required scripts:**

```json
{
  "scripts": {
    "build": "npm run build --workspaces --if-present",
    "test": "npm run test --workspaces --if-present",
    "test:unit": "vitest run",
    "test:integration": "vitest run --config vitest.integration.config.ts",
    "lint": "eslint . --ext .ts,.js,.tsx,.jsx",
    "format": "prettier --write .",
    "diagnostics:baseline": "node --loader ts-node/esm diagnostics/collect-env.ts",
    "diagnostics:mcp": "npm run diagnostics:baseline -- --with-mcp",
    "validate:filetree": "bash scripts/automation/repo_scan.sh",
    "validate:docs": "bash scripts/tooling/update-docs-index.sh .",
    "audit:repo": "bash scripts/automation/audit-repo-standalone.sh . reports/audit false",
    "standalone:validate": "npm run diagnostics:baseline && npm run lint && npm test && npm run validate:docs"
  }
}
```

---

## 🚫 What's Excluded (Archived/Deprecated)

### Moved to `/scripts/legacy/`

- Extraction scripts (`extract-*.sh`, `run-full-extraction.sh`)
- Phase-specific scripts (`phase3-cleanup.sh`, `execute-phase5-*.sh`)
- Submodule integration scripts (`integrate-submodule.sh`, `validate-submodule-*.sh`)
- ProspectPro-specific scripts (`publish-to-github.sh`, `.codespaces-init.sh`)

### Cleaned Up (Completed)

- ✅ Archive folders removed (`docs/archive/`, `docs/onboarding/archive/`)
- ✅ Empty folders removed (`docs/repo/`, `docs/temp/`, `temp/`)
- ✅ Documentation structure flattened (MECE compliance)
- ✅ Config folders consolidated (`configs/` → `config/` with clear subdirectories)
- ✅ Context paths simplified (`context/agents/store/` → `context/_repo-GPS/`)
- ✅ Pipeline structure flattened (`pipelines/.github/workflows/` → `pipelines/`)

### Removed

- Temporary files in `workspace/context/session_store/`
- Build artifacts (`dist/`, `node_modules/`)
- Test coverage reports (not committed)

---

## 📋 Migration Checklist

### Phase A: Archive Legacy Artifacts (✅ Completed)

- [x] Removed archive folders (`docs/archive/`, `docs/onboarding/archive/`)
- [x] Removed empty folders (`docs/repo/`, `docs/temp/`, root `temp/`)
- [x] Flattened documentation structure to MECE compliance
- [x] Consolidated config folders (`configs/` → `config/`)
- [x] Simplified context paths (`context/agents/store/` → `context/_repo-GPS/`)
- [x] Flattened pipeline structure

### Phase B: Update Active Scripts

- [ ] Add `--help` support to all automation scripts
- [ ] Remove hardcoded ProspectPro paths
- [ ] Update script headers with accurate descriptions
- [ ] Test all scripts in standalone mode

### Phase C: Documentation

- [x] Update README.md for standalone usage
- [x] Update ARCHITECTURE.md to reflect end-state
- [x] Update documentation navigation (README.md in docs/)
- [x] Review REFACTOR_CHECKLIST.md

### Phase D: Testing & Linting

- [ ] Add ESLint configuration (`.eslintrc.json`)
- [ ] Add Vitest configuration (`vitest.config.ts`)
- [ ] Wire `npm run lint` command
- [ ] Wire `npm run test:unit` command
- [ ] Update `npm run standalone:validate`

### Phase E: CI/CD

- [ ] Update `.github/workflows/ci.yml`
- [ ] Add lint job
- [ ] Add test job
- [ ] Add validate job
- [ ] Add artifact upload for reports

---

## 🎯 Success Criteria

- ✅ All active scripts have `--help` support
- ✅ No hardcoded paths to external projects
- ✅ ESLint and Vitest configured and working
- ✅ `npm run standalone:validate` passes
- ✅ CI/CD pipeline runs successfully
- ✅ Documentation accurate and complete
- ✅ Legacy artifacts properly archived
- ✅ No ProspectPro references in active code/docs

---

## 📚 Related Documentation

- [ARCHITECTURE.md](ARCHITECTURE.md) - Component architecture
- [REFACTOR_CHECKLIST.md](REFACTOR_CHECKLIST.md) - Migration tracking
- [QUICK_START.md](QUICK_START.md) - Getting started guide
- [SETUP_GUIDE.md](SETUP_GUIDE.md) - Detailed setup instructions

---

**Maintained by:** Dev-Tools Team
**Last Review:** 2025-11-02
**Next Review:** 2025-11-15
