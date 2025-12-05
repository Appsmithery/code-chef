# Changelog

All notable changes to the "code/chef - AI Agent Orchestrator" extension will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.6.1-alpha.1] - 2025-12-05

### Added

- **Context7 Library Cache (DEV-194)**: RAG-based caching for library ID lookups
  - 56 libraries pre-seeded across 6 categories (ai-ml, web-frameworks, devops, data, testing, utilities)
  - New `library_registry` collection in Qdrant Cloud
  - 93-97% token savings on repeat library lookups
  - New `/library-cache/stats` endpoint for cache monitoring

### Changed

- **Default RAG Collection**: Changed from `the-shop` to `code_patterns`
- **RAG Collections**: Now 6 active collections (814 total vectors)
  - `code_patterns` (505) - Python AST extraction [DEFAULT]
  - `issue_tracker` (155) - Linear issues
  - `library_registry` (56) - Context7 cache (NEW)
  - `vendor-docs` (94) - API documentation
  - `feature_specs` (4) - Linear projects

### Removed

- **`the-shop` collection**: Deleted stale DigitalOcean KB collection (460 vectors of outdated data)

## [0.5.0] - 2025-12-03

### Added

- **API Key Authentication**: Secure orchestrator access with API key
  - New `codechef.apiKey` setting for configuring the API key
  - Supports both `X-API-Key` header and `Authorization: Bearer` token
  - Health/metrics endpoints remain public for monitoring
  - Configuration hot-reload: changing API key applies immediately
- **Improved OrchestratorClient**: New config-based constructor pattern with type-safe options

### Security

- Orchestrator API now requires authentication when `ORCHESTRATOR_API_KEY` is set
- Constant-time comparison prevents timing attacks on API key validation
- Unauthorized requests are logged with client IP for audit

### Changed

- `OrchestratorClient` constructor now accepts config object with `baseUrl`, `timeout`, and `apiKey`
- Backward-compatible: old `(baseUrl, timeout)` signature still works

## [0.4.0] - 2025-12-03

### Added

- **Chef Hat Icon**: New branded icon for the extension
- **Production Domain**: All endpoints now use `https://codechef.appsmithery.co` with HTTPS via Caddy reverse proxy

### Changed

- **Complete Rebranding**: Extension renamed from "Dev-Tools" to "code/chef"
- **Extension Name**: `vscode-devtools-copilot` → `vscode-codechef`
- **Chat Participant**: `@devtools` → `@codechef`
- **Command Prefix**: `devtools.*` → `codechef.*`
- **Configuration Prefix**: `devtools.*` → `codechef.*`
- **Default Orchestrator URL**: `http://45.55.173.72:8001` → `https://codechef.appsmithery.co/api`
- **Homepage**: Updated to `https://codechef.appsmithery.co`

### Removed

- **MCP Gateway URL Setting**: Removed deprecated `mcpGatewayUrl` configuration (gateway deprecated)
- **Direct IP Access**: All direct IP references replaced with domain URLs

### Migration Notes

If upgrading from v0.3.x:

1. Settings will need to be reconfigured (new `codechef.*` prefix)
2. Update any scripts using `@devtools` to use `@codechef`
3. Bookmarks to old IP-based URLs should be updated to domain

## [0.3.0] - 2025-11-22

### Added

- **LangGraph Single-Orchestrator Architecture**: Migrated from 6 microservices to single orchestrator with internal agent nodes
- **PostgreSQL Workflow Checkpointing**: LangGraph StateGraph with persistent workflow state for resumable execution
- **Simplified Health Checks**: Single endpoint health validation (port 8001) instead of 6 separate service checks
- **Updated Documentation Links**: Links to consolidated guides (LINEAR_INTEGRATION_GUIDE.md, LINEAR_HITL_WORKFLOW.md, DEPLOYMENT_GUIDE.md)
- **Enhanced Architecture Diagram**: Updated ASCII diagram showing LangGraph StateGraph with supervisor node, 5 agent nodes, approval gate node

### Changed

- **Architecture**: 6 separate FastAPI microservices (ports 8001-8006) → 1 LangGraph orchestrator (port 8001) with internal agent nodes
- **Agent Nodes**: feature-dev, code-review, infrastructure, cicd, documentation are now internal workflow nodes, not separate services
- **Health Checks**: Removed multi-service health validation loop, now single orchestrator health check
- **Deployment Complexity**: Simplified from 6-service stack to single-orchestrator deployment
- **Linear Hub Issue**: Updated default from PR-68 to DEV-68 (public identifier)
- **Extension Description**: Updated to mention "LangGraph single-orchestrator architecture"
- **Badge**: Changed from "6 agents" to "LangGraph Orchestrator (6 Agent Nodes)"

### Deprecated

- **Individual Agent Endpoints**: Ports 8002-8006 no longer exist (agents are internal nodes)
- **Multi-Service Health Validation**: Extension no longer checks 6 separate service endpoints
- **Agent-Specific URLs**: All requests now route through single orchestrator at port 8001

### Technical Details

- LangGraph StateGraph manages workflow execution with conditional routing
- Supervisor node handles task decomposition and agent selection
- Agent nodes execute as internal workflow steps with shared MCP tool access
- Approval gate node integrates HITL workflow with Linear sub-issue creation
- PostgreSQL stores workflow checkpoints for resumable execution after approvals
- All agent nodes share same MCP gateway connection (port 8000)

## [0.2.0] - 2025-01-XX

### Added

- **LangChain Function Calling**: Agents can now INVOKE 150+ MCP tools via LangChain's native tool binding (not just read documentation)
- **Progressive Tool Disclosure**: 80-90% token reduction through intelligent tool filtering with 4 strategies (minimal/agent_profile/progressive/full)
- **3-Layer Tool Architecture**: Discovery (progressive_mcp_loader) → Conversion (to_langchain_tools) → Binding (llm.bind_tools)
- Enhanced README with architecture diagrams showing LangChain integration
- Comprehensive marketplace metadata (badges, expanded keywords, enhanced descriptions)
- Documentation links to PROGRESSIVE_TOOL_DISCLOSURE.md and SETUP_GUIDE.md

### Changed

- Extension display name: "code/chef - AI Agent Orchestrator" → "code/chef - AI Agent Orchestrator"
- Extension description now highlights LangChain function calling and progressive disclosure
- Keywords expanded from 6 to 16 (added: langchain, multi-agent, function-calling, progressive-disclosure, automation, code-generation, hitl, observability, digitalocean, gradient-ai)
- Architecture diagram updated to show 3-layer tool binding flow
- MCP tools section now lists all 17 servers by category

### Fixed

- Tool invocation capability: LLM can now execute tools via LangChain protocol instead of only reading tool documentation
- Token efficiency: Progressive disclosure maintained while adding function calling capability

## [0.1.0] - 2024-XX-XX

### Added

- Initial release
- `@codechef` chat participant for natural language task submission
- Multi-agent orchestration (6 specialized agents)
- Workspace context extraction (git branch, open files, project type)
- Linear integration for HITL approval workflow
- LangSmith traces and Prometheus metrics
- PostgreSQL-backed session management
- Command palette commands (Submit Task, Check Status, Configure, Show Approvals, Clear Cache)
- Chat participant commands (/status, /approve, /tools)
- Real-time approval notifications (<1s latency)

### Infrastructure

- DigitalOcean droplet deployment (codechef.appsmithery.co)
- 6 specialized agents on ports 8001-8006
- MCP gateway with 17 servers, 150+ tools
- DigitalOcean Gradient AI models (llama-3.1-70b, codellama-13b, llama-3.1-8b, mistral-7b)
- LangSmith workspace integration for LLM tracing
- Prometheus metrics collection across all services

[0.2.0]: https://github.com/Appsmithery/code/chef/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/Appsmithery/code/chef/releases/tag/v0.1.0
