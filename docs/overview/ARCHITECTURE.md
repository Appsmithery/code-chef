# Dev-Tools Architecture - Standalone Toolset

**Version:** 1.0.0
**Last Updated:** 2025-11-02
**Status:** Production Ready (Standalone Mode)

---

## 🎯 Overview

Dev-Tools is a **standalone development toolset** providing AI agent orchestration, diagnostics, automation, and testing infrastructure. Originally extracted from ProspectPro, it now operates independently as a reusable toolkit for TypeScript/JavaScript projects.

### Key Principles

1. **Dependency Injection** - All components are injectable for testability
2. **Configuration-Driven** - Behavior controlled via config files, not hardcoded
3. **Modular Design** - Each directory serves a single, clear purpose
4. **Observability First** - Telemetry integrated throughout
5. **Standalone Ready** - No external project dependencies

---

## 📁 Repository Structure

### High-Level Layout

```
Dev-Tools/
├── agents/           # AI agent orchestration
├── automation/       # CI/CD and workflow automation
├── context/          # Legacy context management (being phased out)
├── diagnostics/      # Environment and repo diagnostics
├── docs/             # Documentation
├── observability/    # Telemetry and monitoring
├── reports/          # Generated diagnostic reports
├── scripts/          # Automation scripts
├── testing/          # Test infrastructure
└── workspace/        # Working files and runtime state
```

---

## 🧩 Component Breakdown

### 1. Agents (`/agents/`)

**Purpose:** AI agent profiles, MCP (Model Context Protocol) infrastructure, and context management.

```
agents/
├── _development-workflow/     # Development workflow agent profile
├── _observability/            # Observability agent profile
├── _production-ops/           # Production operations agent profile
├── _system-architect/         # System architect agent profile
├── client-service-layer/      # MCP client package (npm workspace)
├── context/                   # Context manager and schemas
├── mcp-servers/               # MCP server implementations
│   ├── utility/               # Utility MCP server (npm workspace)
│   ├── active-registry.json   # Active server registry
│   └── README.md              # MCP documentation
└── scripts/                   # Agent helper scripts
```

**Key Components:**

- **Agent Profiles:** Persona-based instruction sets for AI agents
- **MCP Client:** Portable MCP client service layer (dependency injection ready)
- **MCP Servers:** Server implementations for tool calling
- **Context Manager:** Shared context storage and retrieval

**Configuration:**

- `.vscode/mcp_config.json` (primary)
- `config/mcp-config.json` (fallback)
- Environment variables via `.env`

**Integration Points:**

- Uses `observability/highlight-node` for telemetry
- Loads config via `ConfigLocator` pattern
- Injectable via `MCPClientManager`

---

### 2. Diagnostics (`/diagnostics/`)

**Purpose:** Cross-platform environment validation and repository analysis.

```
diagnostics/
├── collect-env.ts              # Main CLI entry point
├── helpers/
│   ├── scan-repo-structure.ts  # Repository scanner
│   ├── inventory-packages.ts   # Package analyzer
│   └── detect-languages.ts     # Language detector
├── schemas/                    # JSON validation schemas
└── *.ps1                       # PowerShell wrappers (Windows)
```

**Features:**

- Environment variable validation
- Repository structure scanning
- Package dependency inventory
- Language coverage analysis
- MCP health checks

**Output:** `reports/context/latest/*.json`

**Usage:**

```bash
npm run diagnostics:baseline    # Full scan
npm run diagnostics:env         # Environment only
npm run diagnostics:structure   # Structure only
```

---

### 3. Automation (`/automation/`)

**Purpose:** CI/CD orchestration and automated workflows.

```
automation/
└── ci-cd/
    ├── pipeline.yml            # Pipeline definitions
    ├── stage-taxonomy.sh       # Taxonomy automation
    ├── check-docs-schema.sh    # Documentation validation
    └── render-diagrams.sh      # Diagram generation
```

**Integrations:**

- GitHub Actions (`.github/workflows/`)
- npm scripts (`package.json`)
- Shell scripts (`scripts/automation/`)

---

### 4. Scripts (`/scripts/`)

**Purpose:** Reusable automation and utility scripts.

```
scripts/
├── automation/        # Repository automation
│   ├── repo_scan.sh           # File tree generation
│   ├── audit-docs.sh          # Documentation auditing
│   ├── archive-legacy-files.sh # Legacy file archival
│   ├── init-mcp.sh/.ps1       # MCP initialization
│   └── reset-mcp.sh/.ps1      # MCP cleanup
├── operations/        # Operational scripts
│   └── supabase_cli_helpers.sh
├── setup/             # Bootstrap scripts
│   └── .codespaces-init.sh
├── testing/           # Test utilities
│   └── export-deno-env.sh
├── tooling/           # Development tools
│   └── update-docs-index.sh
└── README.md
```

**Script Categories:**

1. **Automation** - Repository maintenance and CI/CD
2. **Operations** - Runtime operations (Supabase, MCP)
3. **Setup** - Environment bootstrapping
4. **Testing** - Test infrastructure support
5. **Tooling** - Development utilities

**Standards:**

- All scripts support `--help` flag
- Cross-platform where possible (Bash + PowerShell)
- Dry-run mode for safe testing
- Exit code conventions (0 = success, non-zero = error)

---

### 5. Observability (`/observability/`)

**Purpose:** Telemetry and monitoring integration.

```
observability/
└── highlight-node/            # Highlight.io Node.js SDK (npm workspace)
    ├── src/
    │   ├── index.ts           # Main exports
    │   ├── middleware.ts      # MCP middleware
    │   └── edge.ts            # Edge function wrapper
    ├── package.json
    └── README.md
```

**Features:**

- **Highlight.io Integration:** APM and error tracking
- **MCP Middleware:** Automatic tool call tracing
- **Edge Function Support:** Vercel Edge compatibility
- **Custom Instrumentation:** Manual span creation

**Usage:**

```typescript
import { withHighlightEdge } from "@prospectpro/highlight-node";
import { createMCPHighlightMiddleware } from "@prospectpro/highlight-node";
```

**Configuration:**

```bash
HIGHLIGHT_PROJECT_ID=your_project_id
```

---

### 6. Testing (`/testing/`)

**Purpose:** Test infrastructure and utilities.

```
testing/
├── agents/            # Agent-specific tests
├── configs/           # Vitest/Playwright configs
├── fixtures/          # Test data
├── integration/       # Integration tests
│   └── phase5/        # Phase 5 validation tests
├── reports/           # Test reports
├── unit/              # Unit tests
├── utils/             # Test utilities
│   └── setup.ts       # Shared test setup
├── Taskfile.yml       # Task automation
└── README.md
```

**Test Types:**

1. **Unit Tests:** Component-level testing
2. **Integration Tests:** Cross-component testing
3. **E2E Tests:** Full workflow validation
4. **Fixtures:** Reusable test data

**Test Runner:** Vitest (configured in workspace packages)

**Configuration:**

- `testing/integration/phase5/vitest.config.ts`
- Individual workspace `vitest.config.ts` files

---

### 7. Documentation (`/docs/`)

**Purpose:** Comprehensive project documentation.

```
docs/
├── DOCUMENTATION_INDEX.md     # Auto-generated index
├── QUICK_START.md             # Getting started guide
├── SETUP_GUIDE.md             # Detailed setup
├── ARCHITECTURE.md            # This file
├── REFACTOR_CHECKLIST.md      # Migration tracking
├── standalone/                # Standalone usage guides
│   └── GETTING_STARTED.md
├── audit/                     # Audit reports
│   └── audit-report-*.md
├── archive/                   # Archived documentation
│   ├── phase-docs/
│   ├── extraction-docs/
│   └── submodule-docs/
├── inventories/               # Repository inventories
└── provenance/                # Historical context
```

**Documentation Standards:**

- Markdown format
- Auto-generated index via `npm run validate:docs`
- Version dates included
- Examples tested and validated
- Links verified

---

### 8. Reports (`/reports/`)

**Purpose:** Generated diagnostic and validation reports.

```
reports/
├── context/
│   └── latest/                # Latest diagnostic outputs
│       ├── env-diagnostics.json
│       ├── repo-structure.json
│       ├── repo-structure.md
│       ├── package-inventory.json
│       ├── language-report.json
│       ├── filetree.txt
│       └── repo-tree-summary.txt
├── diagnostics/               # Historical diagnostics
├── monitoring/                # Observability snapshots
├── validation/                # Validation reports
└── testing/                   # Test reports
```

**Report Types:**

1. **Diagnostics:** Environment and structure analysis
2. **Validation:** CI/CD validation results
3. **Monitoring:** Observability data
4. **Testing:** Test coverage and results

---

### 9. Workspace (`/workspace/`)

**Purpose:** Working files, runtime state, and archives.

```
workspace/
├── archive/                   # Legacy artifacts
│   └── legacy-scripts-*/
├── context/                   # Context management
│   ├── archive/               # Archived plans
│   └── session_store/         # Session data
└── runtime/                   # Runtime state
    ├── mcp-status.json        # MCP server status
    └── logs/                  # Runtime logs
```

**Usage:**

- **Archive:** Long-term storage of deprecated files
- **Context:** Session-specific working files
- **Runtime:** Active process state

---

## 🔧 Configuration System

### Configuration Hierarchy

1. **Environment Variables** (`.env`)

   - Loaded by all scripts and diagnostics
   - Highest priority

2. **MCP Configuration** (`mcp_config.json`)

   - `.vscode/mcp_config.json` (primary)
   - `config/mcp-config.json` (fallback)
   - Loaded via `ConfigLocator`

3. **TypeScript Configuration** (`tsconfig.json`)

   - Root and workspace-specific

4. **Package Configuration** (`package.json`)
   - Root and workspace-specific
   - npm workspaces enabled

### ConfigLocator Pattern

```typescript
// Example: Loading MCP config
import { ConfigLocator } from "./agents/client-service-layer/src/config";

const locator = new ConfigLocator({
  paths: [".vscode/mcp_config.json", "config/mcp-config.json"],
  required: true,
});

const config = await locator.load();
```

---

## 🔗 Integration Points

### 1. MCP Client ↔ MCP Servers

**Flow:**

```
Agent Profile → MCP Client → MCP Server → Tool Execution
```

**Configuration:** `mcp_config.json`

**Telemetry:** Via Highlight.io middleware

### 2. Diagnostics ↔ Reports

**Flow:**

```
Diagnostic CLI → Analysis → JSON Reports → reports/context/latest/
```

**Output Format:** JSON + Markdown

### 3. Scripts ↔ npm

**Flow:**

```
npm run <script> → package.json → scripts/*.sh → Execution
```

**Standards:**

- Exit codes for CI/CD
- Idempotent operations
- Dry-run support

### 4. Observability ↔ Components

**Flow:**

```
Component → Highlight Node SDK → Highlight.io Backend
```

**Integration:** Middleware and wrappers

---

## 🚀 Deployment Architecture

### Standalone Usage

```
Your Project/
├── dev-tools/                 # Git submodule or npm package
│   ├── agents/
│   ├── diagnostics/
│   └── ...
├── .env                       # Shared or symlinked
└── package.json               # Scripts reference dev-tools
```

**Integration:**

```json
{
  "scripts": {
    "diagnostics": "cd dev-tools && npm run diagnostics:baseline",
    "mcp:init": "cd dev-tools && ./scripts/automation/init-mcp.sh"
  }
}
```

### CI/CD Pipeline

```
GitHub Actions Trigger
  ↓
Install Dependencies
  ↓
Run Diagnostics (npm run diagnostics:baseline)
  ↓
Run Tests (npm test)
  ↓
Run Validation (npm run validate:all)
  ↓
Upload Artifacts (reports/context/latest/)
```

---

## 📊 Data Flow

### Diagnostic Flow

```
User runs: npm run diagnostics:baseline
  ↓
diagnostics/collect-env.ts
  ↓
helpers/scan-repo-structure.ts
helpers/inventory-packages.ts
helpers/detect-languages.ts
  ↓
Generate JSON reports
  ↓
Write to reports/context/latest/
```

### MCP Initialization Flow

```
User runs: npm run diagnostics:mcp
  ↓
scripts/automation/init-mcp.sh
  ↓
Load .env
  ↓
Start MCP servers
  ↓
Run health checks
  ↓
Write mcp-status.json
```

---

## 🔒 Security Considerations

### Environment Variables

- **Never commit** `.env` files
- Use `.env.example` as template
- Validate required variables in diagnostics

### Secrets Management

- No hardcoded credentials
- GitHub tokens via environment only
- Supabase keys loaded at runtime

### CI/CD Security

- GitHub Actions use secrets
- No secrets in logs or artifacts
- CodeQL scanning enabled

---

## 🎯 Extension Points

### Adding New Diagnostics

1. Create script in `diagnostics/helpers/`
2. Add to `diagnostics/collect-env.ts`
3. Update `package.json` scripts
4. Document in `docs/SETUP_GUIDE.md`

### Adding New MCP Servers

1. Create server in `agents/mcp-servers/`
2. Register in `active-registry.json`
3. Add to `config/mcp-config.json`
4. Document in `agents/mcp-servers/README.md`

### Adding New Automation

1. Create script in `scripts/automation/`
2. Add `--help` flag
3. Add to `package.json` scripts
4. Test in dry-run mode
5. Document usage

---

## 📈 Performance Considerations

### Build Time

- **Target:** < 10 minutes for full build
- **Optimization:** Workspace caching
- **Monitoring:** GitHub Actions metrics

### Diagnostic Speed

- **Target:** < 30 seconds for baseline
- **Optimization:** Parallel execution where possible
- **Caching:** Repository structure cache

### MCP Server Startup

- **Target:** < 5 seconds per server
- **Optimization:** Lazy loading
- **Health Checks:** Fast timeout (5s)

---

## 🔄 Update Strategy

### Versioning

- **Semantic Versioning:** MAJOR.MINOR.PATCH
- **Git Tags:** Match package versions
- **CHANGELOG.md:** Document all changes

### Backward Compatibility

- **Deprecated Features:** Moved to `scripts/legacy/`
- **Breaking Changes:** Documented in CHANGELOG
- **Migration Guides:** In `docs/archive/`

---

## 📝 Maintenance

### Regular Tasks

1. **Weekly:** Review audit reports
2. **Monthly:** Update dependencies
3. **Quarterly:** Security audit
4. **Yearly:** Architecture review

### Health Checks

```bash
# Run full validation
npm run validate:all

# Check for vulnerabilities
npm audit

# Update dependencies
npm update --save
```

---

## 🎓 Best Practices

### For Contributors

1. **Read:** `docs/QUICK_START.md` first
2. **Follow:** Dependency injection patterns
3. **Test:** All changes with diagnostics
4. **Document:** New features and changes
5. **Observe:** Use telemetry for debugging

### For Users

1. **Pin Versions:** Use specific tags in production
2. **Review Reports:** Check diagnostic output
3. **Update Regularly:** Monthly dependency updates
4. **Monitor:** Enable Highlight.io in production
5. **Report Issues:** Use GitHub Issues

---

## 📚 Additional Resources

- **[QUICK_START.md](QUICK_START.md)** - Getting started guide
- **[SETUP_GUIDE.md](SETUP_GUIDE.md)** - Detailed setup
- **[REFACTOR_CHECKLIST.md](REFACTOR_CHECKLIST.md)** - Migration status
- **[DOCUMENTATION_INDEX.md](DOCUMENTATION_INDEX.md)** - All docs

---

**Maintained by:** Dev-Tools Team
**Questions:** Open an issue on GitHub
**Contributions:** See CONTRIBUTING.md (coming soon)
