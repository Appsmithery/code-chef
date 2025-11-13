# Documentation Agent

Autonomous technical writer that synthesizes, curates, and maintains product documentation across codebases, APIs, and architectural assets.

## Overview

The Documentation Agent transforms raw engineering knowledge (code, ADRs, design notes) into audience-specific documentation. It ensures that new features ship with aligned docs, maintains single sources of truth, and keeps diagrams/knowledge bases synchronized. This README presents machine-actionable metadata for orchestrators.

## Core Responsibilities

- **Doc discovery:** Crawl repositories, ADRs, and API definitions to build a knowledge graph of documentation assets.
- **Content generation:** Produce READMEs, API references, runbooks, release notes, and inline docstrings tailored to specified personas.
- **Lifecycle management:** Update existing docs when related code changes or acceptance criteria evolve.
- **Diagram synthesis:** Generate architecture and sequence diagrams (Mermaid, PlantUML) from inferred system relationships.
- **Documentation QA:** Validate accuracy against source-of-truth specs, detect stale references, and flag gaps for review.

## Input Contract

| Field          | Required | Description                                              |
| -------------- | -------- | -------------------------------------------------------- |
| `doc_id`       | ✅       | Unique identifier for the documentation task             |
| `request_type` | ✅       | `generate`, `update`, or `audit`                         |
| `audience`     | ✅       | Target persona (`developer`, `ops`, `executive`, `user`) |
| `sources`      | optional | List of repos, ADRs, API specs, tickets, or URLs         |
| `style_guide`  | optional | Reference to tone/branding guidelines                    |
| `translation`  | optional | Locale codes for localized variants                      |

### Example: Generate API Reference

```json
{
  "doc_id": "docs-593",
  "request_type": "generate",
  "audience": "developer",
  "sources": {
    "openapi": "s3://artifacts/billing-openapi.yaml",
    "repository": "git@github.com:appsmithery/dev-tools.git#services/billing"
  },
  "style_guide": "tech-writer-v2",
  "translation": ["en-US", "de-DE"]
}
```

## API Surface

| Method | Path             | Purpose                                                  | Primary Request Fields            | Success Response Snapshot                                            |
| ------ | ---------------- | -------------------------------------------------------- | --------------------------------- | -------------------------------------------------------------------- |
| `POST` | `/documentation` | Generate new documentation package                       | Request body above                | `{ "doc_id": "docs-593", "status": "in_progress" }`                  |
| `POST` | `/update`        | Patch existing docs with new information                 | `doc_id`, `targets`, `change_log` | `{ "doc_id": "docs-593", "status": "updated", "artifacts": [...] }`  |
| `POST` | `/audit`         | Audit documentation for freshness, gaps, and quality     | `scope`, optional `thresholds`    | `{ "doc_id": "docs-593", "status": "completed", "findings": [...] }` |
| `GET`  | `/docs/{doc_id}` | Retrieve generated assets, metadata, and quality metrics | n/a                               | `{ "doc_id": "docs-593", "status": "ready", "files": [...] }`        |

## Output Artifacts

- Markdown/HTML docs with front matter metadata (version, audience, last_updated).
- Diagram files (Mermaid, SVG, PNG) stored alongside textual docs.
- Quality scorecards summarizing completeness, freshness, and link integrity.
- Localization bundles when requested (`/i18n/{locale}/...`).

## Observability & Metrics

- Logs enriched with `doc_id`, `request_type`, `audience`, `sources`.
- Metrics: `docs_latency_seconds`, `docs_quality_score`, `docs_stale_references_total`.
- Tracing spans: `docs.ingest`, `docs.generate`, `docs.review`, `docs.publish`.

## Integration Guidelines

- Supply explicit audiences and style guides to avoid generic voice output.
- Provide authoritative sources (OpenAPI, GraphQL schema, ADRs) for factual accuracy; missing sources may trigger `422` errors.
- Use `/audit` regularly to keep knowledge bases fresh; integrate findings with orchestrator follow-up tasks.
- For multi-locale docs, the agent returns a manifest referencing each locale variant.

## Failure Modes

- **422 Validation error:** Unsupported `request_type` or missing audience information.
- **409 Conflict:** Documentation update already in progress for `doc_id`; poll `/docs/{doc_id}` before reissuing.
- **404 Not Found:** Requested artifacts purged or never generated; rerun `/documentation`.
