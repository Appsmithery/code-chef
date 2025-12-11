# Changelog Archive (Pre-1.0)

Development history prior to v1.0.0 MVP release (December 11, 2025).

---

## [0.9.0] - 2025-12-10

### Added - Phase 5: Comprehensive Tracing Strategy

Complete observability overhaul with LangSmith integration (CHEF-227 through CHEF-237):

#### Metadata Schema v1.0.0

- **7-Category Schema**: experiment_group, environment, module, agent_name, model_version, operation_type, metadata_version
- **Purpose-Based Projects**: Transitioned from per-agent to production/training/evaluation/experiments
- **Clean Start**: All historical traces deleted December 10, 2025

#### ModelOps Tracing

- **30+ @traceable Decorators**: Complete visibility across training, evaluation, deployment, registry, coordinator
- **Metadata Helpers**: Added `_get_*_trace_metadata()` and `_get_langsmith_project()` to all modules
- **A/B Testing**: Baseline runner script with experiment correlation

#### Documentation

- **LLM Operations Guide**: New canonical 700+ line reference covering model selection, training, evaluation, deployment, A/B testing, cost management, troubleshooting
- **Tracing Schema**: Formal YAML specification with examples
- **Project Restructure Guide**: Migration procedure from old to new project structure

### Files Added

- `config/observability/tracing-schema.yaml` - Metadata schema v1.0.0
- `support/docs/operations/llm-operations.md` - Canonical LLM ops guide
- `support/docs/procedures/langsmith-trace-cleanup.md` - Day 0 cleanup
- `support/docs/procedures/langsmith-project-restructure.md` - Migration guide
- `support/scripts/evaluation/baseline_runner.py` - A/B testing script
- `support/scripts/evaluation/sample_tasks.json` - Evaluation tasks

### Changed

- **agent_orchestrator/agents/infrastructure/modelops/**: All 5 modules updated with enhanced tracing
- **support/docs/integrations/langsmith-tracing.md**: Complete rewrite with new schema
- **support/tests/conftest.py**: LANGSMITH_PROJECT routing based on TRACE_ENVIRONMENT

## [0.8.1] - 2025-12-07

### Added - Cross-Agent Memory & Checkpoint Integration

Backend improvements for workflow continuity (CHEF-197 through CHEF-208):

#### Cross-Agent Memory

- **Shared Types**: New `shared/lib/types.py` with canonical `InsightType`, `WorkflowAction`, `CapturedInsight`
- **Memory Manager**: Refactored `AgentMemoryManager` to use RAG HTTP service (decoupled from Qdrant)
- **Memory MCP Tools**: Added `query_insights`, `store_insight`, `get_agent_history` to agent tool mapping

#### Checkpoint Persistence

- **WorkflowState Extended**: Added `captured_insights` and `memory_context` fields for cross-pause knowledge
- **Resume Injection**: `/resume` endpoints inject last 10 insights as context on workflow resume
- **CAPTURE_INSIGHT Event**: New event type for event-sourced insight tracking

#### Observability

- **@traceable Decorators**: Added 29+ decorators across hitl_manager, progressive_mcp_loader, agent_memory, and 3 workflow files
- **LangSmith Visibility**: All memory operations, HITL approvals, and MCP tool loading now traced

### Changed

- **Documentation**: Updated ARCHITECTURE.md, LANGSMITH_TRACING.md, EVENT_SOURCING.md, MCP_INTEGRATION.md, WORKFLOW_QUICK_REFERENCE.md, HITL_WORKFLOW.md

## [0.8.0] - 2025-12-06

### Added - Workflow Slash Commands & Smart Router

New workflow orchestration features for intelligent task routing:

#### Slash Commands

- **`/workflow`**: Execute a workflow with smart selection: `@chef /workflow Deploy PR #123 to production`
- **`/workflows`**: List available workflow templates with metadata (agents, steps, risk level, duration)

#### Smart Workflow Router

- **Heuristic Matching**: Zero-token keyword/pattern matching for common task types (70-90% confidence)
- **LLM Fallback**: Semantic understanding when heuristics are inconclusive
- **Context Extraction**: Automatic PR/issue ID detection from branch names and task descriptions
- **Confidence-Based Confirmation**: Quick Pick UI for low-confidence selections

#### Workflow Settings

- **Default Workflow** (`codechef.defaultWorkflow`): Auto-select or specify explicit workflow (feature, pr-deployment, hotfix, infrastructure, docs-update)
- **Auto-Execute** (`codechef.workflowAutoExecute`): Start workflows immediately or prompt for confirmation
- **Confirmation Threshold** (`codechef.workflowConfirmThreshold`): Confidence level for requiring confirmation (0.0-1.0)
- **Preview Mode** (`codechef.showWorkflowPreview`): Dry run mode to preview workflow selection

#### Context Extraction Enhancements

- **Branch Type Detection**: Identifies feature/fix/hotfix/release from branch prefixes
- **Issue ID Extraction**: Parses Linear-style IDs (DEV-123, PROJ-456) from branch names
- **PR Number Detection**: Extracts PR numbers from branch patterns (pr-123, feature/123-description)

### Changed

- **Code Organization**: Refactored `chatParticipant.ts` (590→200 lines) into focused modules:
  - `src/handlers/statusHandler.ts`: `/status` and `/approve` logic
  - `src/handlers/workflowHandler.ts`: `/workflow` and `/workflows` logic
  - `src/renderers/responseRenderer.ts`: Markdown rendering utilities
- **Constants Centralized**: New `src/constants.ts` with agent types, emojis, API paths, Linear URL builders
- **Linear URL Utility**: Shared `buildLinearIssueUrl()` used across all modules
- **Activation Events**: Removed redundant `onCommand` events (VS Code auto-generates from `commands` contributions)
- **Chat Participant**: Corrected documentation from `@codechef` to `@chef`

### Technical Details

- Backend: New `/workflow/smart-execute` endpoint with 4-phase selection logic
- Backend: New `/workflow/templates` endpoint with full metadata
- Rules: `workflow-router.rules.yaml` for heuristic configuration
- Integration: `OrchestratorClient` extended with `smartExecuteWorkflow()` and `getWorkflowTemplates()`

## [0.7.0] - 2025-12-05

### Added - Token Optimization Settings

New VS Code settings for controlling LLM token costs:

#### Model Selection

- **Environment Profile** (`codechef.environment`): Switch between `production` (full-power models) and `development` (cheaper 8b models for testing)

#### Tool Loading

- **Tool Loading Strategy** (`codechef.toolLoadingStrategy`): Choose from `minimal`, `progressive`, `agent_profile`, or `full` - up to 95% token savings with minimal strategy
- **Max Tools Per Request** (`codechef.maxToolsPerRequest`): Cap the number of tools exposed to LLM (default: 30)
- **Context7 Cache** (`codechef.enableContext7Cache`): Use cached library IDs for 90% savings on library lookups

#### Context Budget

- **Max Context Tokens** (`codechef.maxContextTokens`): Control total context budget per agent (default: 8000)
- **Max Response Tokens** (`codechef.maxResponseTokens`): Limit response length (default: 2000)

#### RAG Settings

- **RAG Enabled** (`codechef.ragEnabled`): Toggle RAG context in prompts
- **RAG Max Results** (`codechef.ragMaxResults`): Limit semantic search results (default: 5)
- **RAG Collection** (`codechef.ragCollection`): Choose primary collection (code_patterns, issue_tracker, etc.)

#### Cost Controls

- **Daily Token Budget** (`codechef.dailyTokenBudget`): Set daily spending limit (0 = unlimited)
- **Show Token Usage** (`codechef.showTokenUsage`): Display token count after requests
- **Cost Alert Threshold** (`codechef.costAlertThreshold`): Warning when request exceeds threshold

#### New Files

- **`src/settings.ts`**: Settings helper module with `getSettings()`, `buildWorkspaceConfig()`, `formatTokenUsage()`, and cost alert utilities

### Changed

- Settings now organized with `order` property for logical grouping in UI
- Added rich markdown descriptions with tables and formatting
- Added Grafana URL setting (`codechef.grafanaUrl`)
- Updated `ChatResponse` interface to include `token_usage` field
- Updated `ChatMessage` interface to include `workspace_config` field

## [0.6.1] - 2025-12-05

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

## [0.3.0] - 2025-11-29

### Added

- **Health Check Command**: New command palette action "code/chef: Health Check" for testing orchestrator connectivity
- **Graceful Degradation**: Better error handling when orchestrator is unreachable

### Changed

- Improved error messages with actionable suggestions
- Updated documentation with troubleshooting section

## [0.2.0] - 2025-11-25

### Added

- **Streaming Support**: Real-time token streaming from orchestrator
- **Status Command**: `/status` command for checking task progress
- **Workflow Templates**: Pre-built workflows for common tasks

### Changed

- Improved chat participant UI with Markdown rendering
- Better error handling and user feedback

## [0.1.0] - 2025-11-20

### Added

- Initial release with basic chat participant functionality
- Integration with Dev-Tools orchestrator
- Support for 6 specialized agents
- Basic MCP tool integration
