# LangSmith Trace Cleanup Procedure

## Purpose

Establish "Day 0" for clean longitudinal tracking by removing all historical traces that may contain contaminated data.

## Date

December 10, 2025

## Manual Steps Required

### 1. Access LangSmith Projects

Navigate to: https://smith.langchain.com

### 2. Delete Traces from Each Project

For each project listed below, perform these actions:

1. Open the project
2. Go to the "Traces" tab
3. Select all traces (or use bulk delete if available)
4. Click "Delete"
5. Confirm deletion

**Projects to clean:**

- `code-chef-feature-dev`
- `code-chef-code-review`
- `code-chef-infrastructure`
- `code-chef-cicd`
- `code-chef-documentation`
- `code-chef-supervisor`
- Any other code-chef related projects

### 3. Update Project Descriptions

After deletion, update each project description to include:

```
Clean traces established: December 10, 2025
Tracking: Longitudinal performance improvement and A/B testing
```

## New Project Structure (to be created)

After cleanup, create these new purpose-driven projects:

- `code-chef-production` - All live extension usage
- `code-chef-experiments` - A/B test comparisons
- `code-chef-training` - Model training runs
- `code-chef-evaluation` - Model evaluation runs

## Verification

After cleanup:

- [ ] All old projects show 0 traces
- [ ] New projects created with updated descriptions
- [ ] Date recorded in project metadata

## Next Steps

Once cleanup is complete, proceed with implementation of the new tracing schema in code.
