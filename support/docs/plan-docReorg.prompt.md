**Plan: Consolidate `support/docs` Directory**

Objective: Reorganize the `support/docs` directory to create a clear, maintainable taxonomy, eliminate redundant content, and ensure essential architecture, deployment, and operations documentation is easily accessible.

**Action Steps:**

1. **Audit Documentation**

   - Review all files in `support/docs` and subfolders (e.g., `frontend`, `pipelines`).
   - Identify overlapping or redundant documents.
   - Flag candidates for consolidation or archiving.

2. **Redesign Taxonomy**

   - Define categories: `getting-started`, `architecture-and-platform`, `integrations`, `operations`, `reference`, `legacy-archive`.
   - Move and rename files to fit the new structure.
   - Preserve key assets: quickstart guides, architecture, deployment, observability, Linear, LangSmith, Gradient, MCP/RAG guides, and runbooks.

3. **Update Landing Page**

   - Revise `support/docs/README.md` to reflect the new taxonomy.
   - List active documents and provide links to each category.
   - Ensure navigation aligns with the codebase structure.

4. **Standardize Documentation**

   - Add consistent metadata (status, category) to each retained document.
   - Reorganize sections to incorporate recent LangGraph/MCP updates.
   - Clearly distinguish between actionable guides and reference material.

5. **Archive Legacy Content**
   - Create a `legacy-archive` index.
   - Move outdated or trimmed content to the archive, with pointers to current guides.
   - Ensure no critical information is lost and readers can locate legacy material.

**Additional Considerations:**

- Evaluate whether to merge short runbooks (e.g., cleanup, secrets rotation, Docker cleanup) into a unified “operations runbook” or keep them separate for clarity.
- Verify that all referenced tools and links (e.g., config files, scripts) are up-to-date with the latest architecture.
- Consider adding a status badge or table (active/archived) at the top of `support/docs/README.md` to indicate canonical documents.

For reference, see [Microsoft Docs: Organizing Documentation](https://learn.microsoft.com/en-us/contribute/organize-content) and [Markdown Metadata Best Practices](https://learn.microsoft.com/en-us/contribute/metadata).
