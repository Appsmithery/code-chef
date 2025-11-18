# Feature Development Agent

LLM-guided implementer that turns product requirements into production-ready application code, tests, and developer documentation.

## Overview

The Feature Development Agent consumes structured or natural-language feature briefs and produces ready-to-merge code artifacts. It scaffolds new modules, writes unit/integration tests, updates docs, and packages deliverables for review pipelines. This README emphasizes the inputs/outputs required for AI orchestration.

### MCP Integration Architecture

Feature-dev connects to the **MCP Gateway** at `http://gateway-mcp:8000` with specialized tooling:

**Recommended Tool Servers:**

- `rust-mcp-filesystem` (read_file, write_file, edit_file, create_directory) - Code generation and workspace management
- `gitmcp` (clone, branch, commit, push, create_pull_request) - Version control workflows
- `context7` (search_docs, retrieve_context) - Framework/API documentation lookup
- `memory` (create_entities, create_relations) - Feature implementation tracking
- `notion` (create_page, add_block) - Design doc and spec management
- `fetch` (http_get, http_post) - API contract validation
- `dockerhub` (search_images, inspect_image) - Base image and dependency queries
- `playwright` (navigate, fill, click, screenshot) - E2E test generation

**Shared Tool Servers:** `time` (timestamps), additional context/filesystem tools

The agent uses `MCPClient` from `agents._shared.mcp_client` to execute file operations, commit code, and log implementation events to the memory server. All tool invocations are traced for debugging and compliance.

## Core Responsibilities

- **Requirement ingestion:** Normalize user stories into explicit acceptance criteria, edge cases, and dependencies.
- **Solution design:** Propose implementation approach, data models, and integration points before code generation.
- **Code synthesis:** Generate typed, lint-compliant code following repository conventions (formatter, directory layout, naming patterns).
- **Test reinforcement:** Produce unit/integration tests, seed data, and CI instructions alongside every feature.
- **Documentation updates:** Draft CHANGELOG entries, README snippets, and API docs when relevant.
- **Feedback loop:** Surface assumptions or missing context back to the orchestrator for clarification.

## Required Inputs

- `feature_id` (string, immutable)
- `summary` (short narrative)
- `acceptance_criteria` (array of bullet strings)
- `target_stack` (language/framework/tooling preferences)
- Optional: `existing_branch`, `style_guides`, `api_contracts`, `design_assets`

## API Surface

| Method | Path                | Purpose                                                  | Primary Request Fields                                                     | Success Response Snapshot                                                            |
| ------ | ------------------- | -------------------------------------------------------- | -------------------------------------------------------------------------- | ------------------------------------------------------------------------------------ |
| `POST` | `/implement`        | Kick off end-to-end feature development                  | `feature_id`, `summary`, `acceptance_criteria`, `target_stack`, `metadata` | `{ "feature_id": "F-1427", "status": "in_progress", "workspace": "feature/F-1427" }` |
| `POST` | `/generate`         | Request scoped code artifact (module/component/function) | `artifact_type`, `spec`, `constraints`                                     | `{ "artifact_id": "component::UserTable", "files": [...] }`                          |
| `GET`  | `/status/{task_id}` | Retrieve progress, artifacts, and code review readiness  | n/a                                                                        | `{ "task_id": "F-1427", "status": "ready_for_review", "artifacts": [...] }`          |

### Sample Feature Request

```json
{
  "feature_id": "F-1427",
  "summary": "Allow exporting invoices to PDF from the billing dashboard",
  "acceptance_criteria": [
    "Users can export the current invoice as a PDF",
    "Generated PDFs include company branding and invoice metadata",
    "Automation tests cover the happy path and missing data edge cases"
  ],
  "target_stack": {
    "language": "TypeScript",
    "framework": "Next.js",
    "testing": ["Playwright", "Jest"]
  },
  "metadata": {
    "repository": "git@github.com:appsmithery/dev-tools.git",
    "branch": "feature/pdf-export",
    "reviewer_slack": "#dev-review"
  }
}
```

### Output Artifacts

- Source code files with deterministic paths (mirroring repo layout).
- Tests wired into existing CI (includes `npm test` instructions or Taskfile targets).
- `docs/` updates or inline JSDoc comments when API surface expands.
- Summary report capturing implementation notes, TODOs, and verification steps.

## Execution Flow

1. Validate inputs and fetch repository metadata.
2. Draft solution design; attach to task timeline for review if manual approval required.
3. Generate implementation + tests in an isolated workspace.
4. Run lint/test commands; attach results to status payload.
5. Publish artifacts (tarball, branch push instructions, PR draft) to object storage and notify orchestrator.

## Observability & Quality Signals

- Structured logs include `feature_id`, `artifact_id`, and `git_ref` for traceability.
- Exposes metrics `feature_dev_cycle_time_seconds`, `feature_dev_regressions_total`, `feature_dev_test_pass_rate`.
- Supports OpenTelemetry spans `feature-dev.plan`, `feature-dev.generate`, `feature-dev.validate` for distributed tracing.

## Integration Notes

- Always supply acceptance criteria; insufficient detail will trigger a `422 Unprocessable Entity` response.
- Provide explicit formatting/ linting commands in metadata to override defaults.
- For incremental updates, reuse the same `feature_id`—the agent will diff and append commit instructions rather than overwriting.

## Failure Modes

- **422 Validation error:** Missing acceptance criteria or unsupported target stack.
- **409 Conflict:** `feature_id` already active in another workspace; either resume via `/status` or choose a new identifier.
- **500 Build failure:** Agent returns captured compiler/test logs for human intervention.
