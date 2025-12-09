# Legacy Documentation Archive

This folder contains deprecated, superseded, or historical documentation that has been archived but preserved for reference purposes.

## Archived Documents

| Document                                                                               | Original Location                                          | Reason                                | Current Alternative                                                                                                |
| -------------------------------------------------------------------------------------- | ---------------------------------------------------------- | ------------------------------------- | ------------------------------------------------------------------------------------------------------------------ |
| [event-sourcing.md](event-sourcing.md)                                                 | guides/EVENT_SOURCING.md                                   | Superseded by workflow engine updates | See [architecture-and-platform/task-orchestration.md](../architecture-and-platform/task-orchestration.md)          |
| [hitl-workflow.md](hitl-workflow.md)                                                   | guides/HITL_WORKFLOW.md                                    | Consolidated into Linear integration  | See [integrations/linear-hitl-workflow.md](../integrations/linear-hitl-workflow.md)                                |
| [workflow-cli.md](workflow-cli.md)                                                     | guides/WORKFLOW_CLI.md                                     | CLI interface deprecated              | See [reference/langgraph-quick-ref.md](../reference/langgraph-quick-ref.md)                                        |
| [workflow-testing.md](workflow-testing.md)                                             | WORKFLOW_TESTING.md                                        | Test patterns evolved                 | See [architecture-and-platform/multi-agent-workflows.md](../architecture-and-platform/multi-agent-workflows.md)    |
| [e2e-test-checklist.md](e2e-test-checklist.md)                                         | E2E_TEST_CHECKLIST.md                                      | Replaced by automated testing         | Contact engineering team for current test strategy                                                                 |
| [langsmith-trace-evaluation-plan.md](langsmith-trace-evaluation-plan.md)               | guides/langsmithTraceEvaluation-plan.md                    | Implementation plan (completed)       | See [integrations/langsmith-tracing.md](../integrations/langsmith-tracing.md)                                      |
| [linear-integration-deprecated-20251125.md](linear-integration-deprecated-20251125.md) | guides/\_archive/LINEAR_INTEGRATION.md.deprecated-20251125 | Old Linear integration docs           | See [integrations/linear-integration-guide.md](../integrations/linear-integration-guide.md)                        |
| [flowchart.mmd](flowchart.mmd)                                                         | architecture/flowchart.mmd                                 | Legacy Mermaid diagram                | See [architecture-and-platform/architecture.md](../architecture-and-platform/architecture.md) for current diagrams |

## When to Reference Archived Docs

Use archived documentation when:

- Investigating historical context for architecture decisions
- Understanding deprecated features for migration purposes
- Researching evolution of system patterns
- Troubleshooting legacy integrations

⚠️ **Warning**: Archived documents may contain outdated information, broken links, or deprecated patterns. Always verify against current documentation before implementing any guidance from archived sources.

## Archival Policy

Documents are archived when they:

1. Are superseded by newer, consolidated documentation
2. Reference deprecated features or APIs
3. Contain outdated architecture patterns
4. Are implementation plans that have been completed
5. Duplicate information available in active documentation

---

**Questions?** Check the [main documentation index](../README.md) or open an issue on GitHub.
