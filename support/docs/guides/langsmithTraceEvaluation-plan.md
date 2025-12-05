**E2E LangSmith Trace Evaluation Strategy**

Implement a dual-workspace evaluation system for LangSmith traces using the VS Code extension during natural development and CI/CD validation. Follow these steps:

1. **Multi-Project Trace Isolation**

   - Configure separate LangSmith projects for production and testing by setting `LANGCHAIN_PROJECT=code-chef-testing` in your test workspace and updating `.env.template` with environment-specific project names.
   - Ensure production and evaluation traces are isolated.

2. **Evaluation Dataset Creation**

   - Create `support/tests/e2e/langsmith_datasets.py` with `Client().create_dataset()` calls for 10–15 realistic DevOps scenarios (e.g., feature implementation, CI/CD, code review) that reflect your workflow.
   - Reference: [LangSmith Dataset API](https://docs.langchain.com/langsmith/python/api-reference/#clientcreatedataset).

3. **Trace-Generating E2E Tests**

   - Add `support/tests/e2e/test_langsmith_traces.py` containing `@pytest.mark.trace` tests that invoke the orchestrator API, wait for trace upload, and verify trace structure using the LangSmith SDK.
   - Reference: [LangSmith Python SDK](https://docs.langchain.com/langsmith/python/api-reference/).

4. **Custom Evaluator Functions**

   - Implement `support/tests/evaluation/evaluators.py` with evaluators for agent routing accuracy, token efficiency, latency thresholds, and workflow completeness.
   - Reference: [LangSmith Evaluation API](https://docs.langchain.com/langsmith/python/evaluation/).

5. **GitHub Actions Evaluation Workflow**

   - Create `.github/workflows/e2e-langsmith-eval.yml` to run scheduled (daily) or manual evaluations, execute E2E tests, and post results to a Linear issue.
   - Reference: [GitHub Actions Workflow Syntax](https://docs.github.com/en/actions/using-workflows/workflow-syntax-for-github-actions).

6. **VS Code Workspace Configuration**
   - In your development project, set `codechef.orchestratorUrl` to production and `codechef.langsmithProject` to the testing project in `.vscode/settings.json` or a dedicated workspace file to enable natural trace generation.

**Additional Considerations**

- Set a 7-day retention policy for testing traces to reduce costs.
- Schedule daily evaluations and post-deploy validations for regression detection.
- Seed datasets with scenarios extracted from your Linear issue tracker (`DEV-*` issues).

**Scenario Dataset Example**

| #   | Scenario                                             | Expected Agents          | Risk Level |
| --- | ---------------------------------------------------- | ------------------------ | ---------- |
| 1   | Add JWT authentication to Express API                | feature-dev, code-review | medium     |
| 2   | Create GitHub Actions workflow for Docker deployment | cicd                     | high       |
| ... | ...                                                  | ...                      | ...        |

**References**

- [LangSmith Documentation](https://docs.langchain.com/langsmith/)
- [LangSmith Python SDK](https://docs.langchain.com/langsmith/python/api-reference/)
- [GitHub Actions](https://docs.github.com/en/actions)
- [VS Code Workspace Settings](https://code.visualstudio.com/docs/editor/workspaces)

Ensure all steps are implemented as described, with clear separation of production and evaluation traces, automated quality checks, and actionable reporting.
