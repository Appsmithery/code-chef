# Refactor Checklist - Standalone Dev-Tools Migration

This checklist tracks the migration of Dev-Tools from a ProspectPro-extraction repository to a standalone, production-ready development toolset.
**Status:** In Progress
**Target Completion:** 2025-11-15
**Current Phase:** Documentation & Cleanup

---

## ✅ Phase 1: Repository Audit (COMPLETE)

- [x] Create automated audit script (`scripts/automation/audit-docs.sh`)
- [x] Scan for ProspectPro references (469 found)
- [x] Identify Phase-specific files (10 files)
- [x] Identify extraction-related files (10 files)
- [x] Identify submodule integration files (4 files)
- [x] Generate audit report (`reports/audit/audit-report-*.md`)

**Completion Date:** 2025-11-02

---

## 🔄 Phase 2: Documentation Reorganization (IN PROGRESS)

### 2.1 Archive Structure

- [x] Create `docs/archive/` directory structure
- [ ] Move Phase-specific documentation to archive
  - [ ] `PHASE5_COMPLETION_SUMMARY.md` → `docs/archive/phase-docs/`
  - [ ] `docs/PHASE5_QUICK_REFERENCE.md` → `docs/archive/phase-docs/`
  - [ ] `reports/README-phase-2-reports.md` → `docs/archive/phase-docs/`
  - [ ] `reports/phase-2-validation-summary.md` → `docs/archive/phase-docs/`
  - [ ] `reports/phase-3-readiness-summary.md` → `docs/archive/phase-docs/`

### 2.2 New Documentation

- [x] Create `docs/QUICK_START.md`
- [ ] Create `docs/ARCHITECTURE.md`
- [ ] Create `docs/REFACTOR_CHECKLIST.md` (this file)
- [ ] Create `docs/archive/README.md` explaining archived content

### 2.3 Update Existing Docs

- [ ] Update `README.md` - remove ProspectPro references, focus on standalone usage
- [ ] Update `DOCUMENTATION_INDEX.md` - reflect new structure
- [ ] Update `docs/SETUP_GUIDE.md` - clarify standalone setup
- [ ] Update `docs/standalone/GETTING_STARTED.md` - ensure accuracy

---

## 🧹 Phase 3: Script Cleanup (NOT STARTED)

### 3.1 Archive Scripts

- [ ] Create `scripts/legacy/` directory structure
  - [ ] `scripts/legacy/extraction/`
  - [ ] `scripts/legacy/phase-scripts/`
  - [ ] `scripts/legacy/submodule/`
- [ ] Move extraction scripts to `scripts/legacy/extraction/`
  - [ ] `extract-agents.sh`
  - [ ] `extract-automation.sh`
  - [ ] `extract-scripts.sh`
  - [ ] `extract-testing.sh`
  - [ ] `extract-workspace.sh`
  - [ ] `generate-extraction-manifest.sh`
  - [ ] `init-devtools-repo.sh`
  - [ ] `run-full-extraction.sh`
- [ ] Move phase scripts to `scripts/legacy/phase-scripts/`
  - [ ] `phase3-cleanup.sh`
  - [ ] `execute-phase5-cleanup.sh`
  - [ ] `execute-phase5-refactor.sh`
  - [ ] `README-PHASE5.md`
- [ ] Move submodule scripts to `scripts/legacy/submodule/`
  - [ ] `integrate-submodule.sh`
  - [ ] `validate-submodule-filetree.sh`
  - [ ] `validate-submodule-integration.sh`
  - [ ] `validate-prospectpro-integration.sh`

### 3.2 Update Active Scripts

- [ ] Add `--help` flag to all automation scripts
- [ ] Ensure standalone-safe defaults in all scripts
- [ ] Remove ProspectPro-specific logic from active scripts
- [ ] Update script headers with accurate descriptions

### 3.3 Create Script Documentation

- [ ] Create `scripts/README.md` with standalone usage guide
- [ ] Document all npm script commands
- [ ] Add examples for common workflows

---

## 🏗️ Phase 4: Repository Structure (NOT STARTED)

### 4.1 Define End-State Structure

- [ ] Create `docs/ARCHITECTURE.md` documenting:
  - [ ] Directory structure and purpose
  - [ ] Component boundaries
  - [ ] Integration points
  - [ ] Configuration patterns

### 4.2 Update package.json

- [ ] Remove placeholder test command
- [ ] Remove placeholder lint command
- [ ] Add proper test infrastructure
- [ ] Add ESLint configuration
- [ ] Update scripts for standalone usage
- [ ] Remove Phase-specific scripts

### 4.3 Clean Up Root Directory

- [ ] Archive or remove `REPO_RESTRUCTURE_PLAN.md`
- [ ] Update `CHANGELOG.md` - focus on standalone releases
- [ ] Ensure `.gitignore` covers all temporary files
- [ ] Verify `.env.example` has accurate defaults

---

## 🧪 Phase 5: Testing Infrastructure (NOT STARTED)

### 5.1 Test Configuration

- [ ] Add Vitest configuration for unit tests
- [ ] Configure test coverage reporting
- [ ] Set up test fixtures for standalone usage
- [ ] Remove ProspectPro-specific test dependencies

### 5.2 Linting Configuration

- [ ] Add ESLint configuration
- [ ] Add Prettier configuration (optional)
- [ ] Configure TypeScript strict mode
- [ ] Add lint-staged for pre-commit hooks

### 5.3 New npm Scripts

- [ ] `npm run standalone:validate` - Standalone validation suite
- [ ] `npm run test:unit` - Unit tests
- [ ] `npm run test:integration` - Integration tests
- [ ] `npm run lint` - Code linting
- [ ] `npm run format` - Code formatting (optional)

---

## 🔐 Phase 6: CI/CD Updates (NOT STARTED)

### 6.1 GitHub Actions Workflow

- [ ] Remove Phase-specific CI jobs
- [ ] Add standalone validation job
- [ ] Add test coverage reporting
- [ ] Add security scanning
- [ ] Optimize caching strategy

### 6.2 Automation Scripts

- [ ] Update `scripts/automation/execute-ci-cd-setup.sh` for standalone
- [ ] Remove submodule-specific validations
- [ ] Add standalone CI/CD documentation

---

## 📝 Phase 7: Final Cleanup (NOT STARTED)

### 7.1 ProspectPro References

- [ ] Update all ProspectPro references to be generic or remove
- [ ] Search and replace in documentation
- [ ] Update code comments
- [ ] Update error messages

**Helper Commands:**

```bash
# Find all ProspectPro references
grep -r "ProspectPro" . --exclude-dir=node_modules --exclude-dir=.git --exclude-dir=docs/archive --exclude-dir=scripts/legacy
# Count references by file type
grep -r "ProspectPro" . --exclude-dir=node_modules --exclude-dir=.git --exclude-dir=docs/archive --exclude-dir=scripts/legacy --include="*.md" -c | grep -v ":0$"
# Generate replacement script (dry-run first!)
find . -type f \( -name "*.md" -o -name "*.ts" -o -name "*.js" \) \
  -not -path "*/node_modules/*" \
  -not -path "*/.git/*" \
  -not -path "*/docs/archive/*" \
  -not -path "*/scripts/legacy/*" \
  -exec grep -l "ProspectPro" {} \;
```

### 7.2 Workspace Cleanup

- [ ] Review `workspace/context/archive/` - archive or remove old plans
- [ ] Clean `workspace/context/session_store/` temporary files
- [ ] Update `.gitignore` for workspace files
- [ ] Add README to workspace directories

### 7.3 Reports Cleanup

- [ ] Archive phase-2 and phase-3 reports
- [ ] Remove extraction manifest from reports
- [ ] Ensure report directory structure is clear
- [ ] Add README to reports directory

---

## 🎯 Phase 8: Validation & Testing (NOT STARTED)

### 8.1 Functional Testing

- [ ] Run `npm run diagnostics:baseline` - verify success
- [ ] Run `npm run validate:all` - verify all checks pass
- [ ] Test all npm scripts individually
- [ ] Verify file tree generation works
- [ ] Verify documentation index updates

### 8.2 Integration Testing

- [ ] Test as submodule in sample project
- [ ] Test standalone usage
- [ ] Verify environment variable loading
- [ ] Test on different platforms (Linux, macOS, Windows)

### 8.3 Security Audit

- [ ] Run `npm audit` and address vulnerabilities
- [ ] Run CodeQL security scanning
- [ ] Review exposed secrets or credentials
- [ ] Verify `.gitignore` prevents committing sensitive files

### 8.4 Documentation Validation

- [ ] Review all documentation for accuracy
- [ ] Test all code examples in documentation
- [ ] Verify all links work
- [ ] Ensure consistent formatting

---

## 📊 Progress Tracking

### Overall Progress

- **Phases Complete:** 1 / 8
- **Tasks Complete:** 6 / 100+
- **Estimated Completion:** ~12% complete

### Current Sprint Focus

1. Complete Phase 2: Documentation Reorganization
2. Begin Phase 3: Script Cleanup
3. Draft Phase 4: Repository Structure

---

## 🚀 Required Environment Variables

### Minimum (Core Functionality)

```bash
NODE_ENV=development
```

### Recommended (Full Features)

```bash
# Core
NODE_ENV=development

# Supabase (for MCP database features)
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your_anon_key_here

# Highlight.io (for observability)
HIGHLIGHT_PROJECT_ID=your_project_id_here

# GitHub (for repository operations)
GITHUB_TOKEN=ghp_your_token_here
```

---

## 📋 CI/CD Expectations

### Build Requirements

- Node.js 20.0.0+
- npm 9.0.0+
- Bash 4+ (for shell scripts)

### Test Requirements

- All npm scripts must succeed
- Diagnostics must pass
- No security vulnerabilities
- Documentation must be up-to-date

### Deployment Requirements

- All tests passing
- Security scan clean
- Documentation validated
- Version tagged

---

## 🔍 Removal Targets

### Files to Archive

1. All Phase-specific documentation
2. All extraction scripts
3. All submodule integration scripts
4. ProspectPro-specific validation scripts

### Files to Update

1. `README.md` - focus on standalone usage
2. `package.json` - remove placeholders
3. `.github/workflows/ci.yml` - standalone CI
4. All npm scripts

### Files to Remove (After Archiving)

1. `EXTRACTION_MANIFEST.md`
2. `REPO_RESTRUCTURE_PLAN.md` (maybe archive)
3. Temporary files in `workspace/context/session_store/`
4. Old phase validation reports

---

## 💡 Migration Notes

### Breaking Changes

- ProspectPro-specific scripts moved to `scripts/legacy/`
- Phase-specific documentation archived
- Submodule integration scripts deprecated
- npm script names may change

### Backward Compatibility

- Archived scripts remain accessible in `scripts/legacy/`
- Archived docs remain in `docs/archive/`
- Old npm scripts will show deprecation warnings

### Migration Path for Users

1. Update to latest Dev-Tools version
2. Review `docs/QUICK_START.md` for new setup
3. Update npm script references in CI/CD
4. Remove submodule-specific configurations
5. Update environment variables per new requirements

---

## 🎓 Success Criteria

### Documentation

- [ ] All links work
- [ ] All examples tested
- [ ] No ProspectPro-specific references (except in archive)
- [ ] Clear standalone setup guide

### Scripts

- [ ] All npm scripts work standalone
- [ ] All shell scripts have `--help`
- [ ] No broken references
- [ ] Clear deprecation notices for legacy scripts

### Repository

- [ ] Clean git status
- [ ] Proper `.gitignore` coverage
- [ ] No secrets committed
- [ ] All workspace packages build successfully

### CI/CD

- [ ] All CI jobs pass
- [ ] Security scan clean
- [ ] Test coverage > 70%
- [ ] Build time < 10 minutes

---

**Last Updated:** 2025-11-02
**Next Review:** 2025-11-09
**Owner:** Dev-Tools Maintainers
