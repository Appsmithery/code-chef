# Changelog

All notable changes to the "Dev-Tools Multi-Agent Orchestrator" extension will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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

- Extension display name: "Dev-Tools Copilot Extension" → "Dev-Tools Multi-Agent Orchestrator"
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
- `@devtools` chat participant for natural language task submission
- Multi-agent orchestration (6 specialized agents)
- Workspace context extraction (git branch, open files, project type)
- Linear integration for HITL approval workflow
- LangSmith traces and Prometheus metrics
- PostgreSQL-backed session management
- Command palette commands (Submit Task, Check Status, Configure, Show Approvals, Clear Cache)
- Chat participant commands (/status, /approve, /tools)
- Real-time approval notifications (<1s latency)

### Infrastructure

- DigitalOcean droplet deployment (45.55.173.72)
- 6 specialized agents on ports 8001-8006
- MCP gateway with 17 servers, 150+ tools
- DigitalOcean Gradient AI models (llama-3.1-70b, codellama-13b, llama-3.1-8b, mistral-7b)
- LangSmith workspace integration for LLM tracing
- Prometheus metrics collection across all services

[0.2.0]: https://github.com/Appsmithery/Dev-Tools/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/Appsmithery/Dev-Tools/releases/tag/v0.1.0
