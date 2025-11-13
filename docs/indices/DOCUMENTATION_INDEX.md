# Documentation Index (Migration Placeholder)

**Last Updated:** 2025-11-12

This index is normally generated automatically by the documentation orchestrator (`operations/environment/update-docs-index.sh`). The automation has not yet been migrated into this repository, so this placeholder records the regeneration steps and interim navigation hints.

## Regeneration Steps

1. Migrate the documentation tooling from the legacy repository:
   - `operations/environment/update-docs-index.sh`
   - any referenced helper scripts or Taskfile targets
2. Ensure the script is executable and referenced from `package.json` (e.g. `npm run validate:docs`).
3. Run the generator from the repository root:
   ```bash
   npm run validate:docs
   ```
4. Commit the updated `docs/indices/DOCUMENTATION_INDEX.md` together with any supporting inventory artefacts.

## Interim Navigation

Until the generator is reinstated, the most relevant documentation can be found at:

- `docs/overview/ARCHITECTURE.md` – repository architecture and structure
- `docs/overview/STANDALONE_STRUCTURE.md` – end-state layout
- `docs/onboarding/SETUP_GUIDE.md` – comprehensive setup instructions
- `docs/governance/REFACTOR_CHECKLIST.md` – migration progress tracker
- `docs/governance/SECRETS_MANAGEMENT.md` – secrets handling policy

Refer to these documents while porting additional tooling. Replace this placeholder with the generated index once the documentation pipeline is restored.
