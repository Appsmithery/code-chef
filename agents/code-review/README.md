# Code Review Agent

Autonomous reviewer that inspects proposed changesets for quality, security, style adherence, and maintainability risks.

## Overview

This agent ingests diffs or repository references, performs multilayer analysis (static analysis, dependency checks, secret scanning), and produces structured review feedback suitable for CI gating or human triage. Documentation is optimized for AI orchestration pipelines.

## Core Responsibilities

- **Diff analysis:** Parse git patches or file bundles, compute semantic impact, and map findings to source locations.
- **Standards enforcement:** Apply project coding standards, lint rules, and architectural guidelines.
- **Security posture:** Run SAST patterns, dependency vulnerability checks (OSV, npm audit, pip-audit), and leak detection.
- **Test validation:** Ensure tests exist/updated for modified modules and verify last CI run status when available.
- **Actionable feedback:** Emit prioritized comments with remediation instructions, severity scoring, and confidence levels.

## Input Contract

| Field           | Required      | Description                                                                 |
| --------------- | ------------- | --------------------------------------------------------------------------- |
| `review_id`     | ✅            | Stable identifier for tracking feedback cycles                              |
| `source`        | ✅            | Either `git` (with repo URL + ref) or `inline` (list of files with content) |
| `target_branch` | ✅ (git mode) | Baseline branch for diff comparison                                         |
| `ruleset`       | optional      | Overrides for lint, security, or style rule packs                           |
| `ci_context`    | optional      | Last pipeline results, coverage metrics, or Jira issue keys                 |

### Example: Submit Review

```json
{
  "review_id": "PR-872",
  "source": {
    "mode": "git",
    "repository": "git@github.com:appsmithery/dev-tools.git",
    "pull_request": 872
  },
  "target_branch": "main",
  "ruleset": {
    "lint": ["eslint-strict"],
    "security": ["npm-audit", "gitleaks"],
    "quality": ["cyclomatic-threshold"],
    "severity_threshold": "medium"
  },
  "ci_context": {
    "coverage_delta": -2.1,
    "failed_tests": ["tests/api/invoices.test.ts"]
  }
}
```

## API Surface

| Method | Path                   | Purpose                                                  | Primary Request Fields             | Success Response Snapshot                                             |
| ------ | ---------------------- | -------------------------------------------------------- | ---------------------------------- | --------------------------------------------------------------------- |
| `POST` | `/review`              | Start analysis for a new code submission                 | Request body above                 | `{ "review_id": "PR-872", "status": "running" }`                      |
| `GET`  | `/results/{review_id}` | Retrieve findings, severity summary, and suggested fixes | n/a                                | `{ "review_id": "PR-872", "status": "completed", "findings": [...] }` |
| `POST` | `/recheck/{review_id}` | Re-run analysis after fixes                              | optional: `changed_files`, `notes` | `{ "review_id": "PR-872", "status": "running", "iteration": 2 }`      |

## Output Schema (Completed Review)

```json
{
  "review_id": "PR-872",
  "status": "completed",
  "summary": {
    "severity_counts": { "critical": 0, "high": 1, "medium": 2, "low": 4 },
    "risk_score": 0.42,
    "coverage_delta": -1.3,
    "recommendation": "changes_requested"
  },
  "findings": [
    {
      "id": "lint/unused-import",
      "severity": "low",
      "confidence": 0.86,
      "location": {
        "file": "src/modules/billing/export.ts",
        "line": 42
      },
      "message": "Remove unused import `LegacyExporter`.",
      "suggested_fix": "Delete the import or use the symbol in the module."
    },
    {
      "id": "security/sql-injection",
      "severity": "high",
      "confidence": 0.71,
      "location": {
        "file": "src/modules/billing/export.ts",
        "line": 118
      },
      "message": "Unsanitized user input concatenated into SQL query.",
      "suggested_fix": "Use parameterized query via `db.query(sql, params)`.",
      "references": ["https://owasp.org/www-project-top-ten/2017/A1-Injection"]
    }
  ],
  "artifacts": {
    "sarif_report": "s3://agent-output/PR-872/report.sarif",
    "html_summary": "s3://agent-output/PR-872/summary.html"
  }
}
```

## Observability & Metrics

- Logs each finding with structured fields (`severity`, `confidence`, `rule_id`, `file`).
- Emits metrics: `code_review_findings_total`, `code_review_blocking_rate`, `code_review_runtime_seconds`.
- OpenTelemetry spans: `code-review.fetch-source`, `code-review.analyze`, `code-review.publish`.

## Integration Guidelines

- Provide repository credentials via secure context (never inline secrets in payloads).
- If supplying inline files, include full relative paths to allow proper comment anchoring.
- Poll `/results/{review_id}` with exponential backoff (recommended: start at 2s, cap at 30s) or subscribe to the webhook callback channel.
- When integrating with the Orchestrator Agent, forward the `summary.recommendation` to determine approval vs. rework routing.

## Failure Modes

- **400 Bad Request:** Payload missing `source` information or unsupported mode.
- **403 Forbidden:** Credential issue accessing the repository; reconfigure secret binding.
- **500 Analyzer error:** Internal tooling failure—response includes diagnostic ID for reprocessing.
