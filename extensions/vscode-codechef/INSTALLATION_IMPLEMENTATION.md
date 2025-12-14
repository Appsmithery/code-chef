# Extension Installation Streamlining - Implementation Summary

**Date**: December 14, 2025  
**Status**: ✅ Complete

## Changes Implemented

### 1. ✅ Updated package.json for dual publishing

**File**: `extensions/vscode-codechef/package.json`

**Changes**:

- Changed `name` from `"vscode-codechef"` → `"@appsmithery/vscode-codechef"` (scoped for GitHub Packages)
- Added `bin` field: `{"vscode-codechef": "./install-cli.js"}` for CLI installer
- Updated `publishConfig.registry` to GitHub Packages: `https://npm.pkg.github.com`
- Added `postinstall` script: `"node install-cli.js"` for automatic installation
- Added `ovsx` package (v0.8.0) to devDependencies for Open VSX publishing

### 2. ✅ Created install-cli.js helper script

**File**: `extensions/vscode-codechef/install-cli.js` (new)

**Features**:

- ✅ Detects VS Code CLI (`code` command) availability
- ✅ Checks for bundled VSIX in npm package first
- ✅ Downloads VSIX from GitHub releases if not bundled
- ✅ Executes `code --install-extension` with VSIX
- ✅ Graceful error handling with helpful user messages
- ✅ Skips installation in CI environments (checks `CI` and `SKIP_INSTALL` env vars)
- ✅ Provides troubleshooting guidance for missing `code` CLI

**Usage**: `npx @appsmithery/vscode-codechef`

### 3. ✅ Updated publish-extension.yml workflow

**File**: `.github/workflows/publish-extension.yml`

**Changes**:

- ✅ Removed package.json name rewrite (line 201-212) - now uses scoped name directly
- ✅ Changed `NODE_AUTH_TOKEN` from `${{ secrets.GITHUB_TOKEN }}` → `${{ secrets.NPM_TOKEN }}`
- ✅ Added `--access public` to npm publish command
- ✅ Added Open VSX publishing step after VSIX packaging:
  ```yaml
  - name: Publish to Open VSX Registry
    run: npx ovsx publish *.vsix -p ${{ secrets.OPENVSX_TOKEN }}
    continue-on-error: true
  ```

**Required GitHub Secrets** (need to be added):

- `NPM_TOKEN` - GitHub Personal Access Token with `read:packages` and `write:packages` scopes
- `OPENVSX_TOKEN` - Open VSX Registry Personal Access Token

### 4. ✅ Updated README.md installation instructions

**File**: `extensions/vscode-codechef/README.md`

**Changes**:

- ✅ Added **Option 1: npx (Recommended)** with one-command installation
- ✅ Included `.npmrc` setup instructions for GitHub Packages authentication
- ✅ Added **Option 2: Open VSX Registry** (no authentication required)
- ✅ Kept **Option 3: GitHub Releases** as fallback
- ✅ Added **Troubleshooting** section for common issues:
  - Missing `code` CLI
  - Authentication errors
  - Alternative installation methods

### 5. ✅ Created .npmrc configuration files

**Files**:

- `extensions/vscode-codechef/.npmrc.example` (template for contributors)
- Updated `extensions/vscode-codechef/.gitignore` to exclude `.npmrc` (prevent token leakage)

**Content**:

```ini
@appsmithery:registry=https://npm.pkg.github.com
//npm.pkg.github.com/:_authToken=YOUR_GITHUB_TOKEN_HERE
```

---

## Post-Implementation Tasks

### Required Setup

#### 1. Create GitHub Secrets

Navigate to: https://github.com/Appsmithery/code-chef/settings/secrets/actions

**Add the following secrets**:

1. **NPM_TOKEN**

   - Go to: https://github.com/settings/tokens/new?scopes=read:packages,write:packages
   - Description: "code-chef npm publishing"
   - Scopes: `read:packages`, `write:packages`
   - Generate token and add to GitHub Secrets

2. **OPENVSX_TOKEN**
   - Create Open VSX namespace: https://open-vsx.org/user-settings/namespaces
   - Generate Personal Access Token: https://open-vsx.org/user-settings/tokens
   - Add token to GitHub Secrets

#### 2. Open VSX Namespace Setup

1. **Register namespace** (if not exists):

   - Visit: https://open-vsx.org/user-settings/namespaces
   - Request namespace: `appsmithery`
   - If taken, file ownership claim at: https://github.com/eclipse/openvsx/wiki/Namespace-Access

2. **Generate Personal Access Token**:
   - Visit: https://open-vsx.org/user-settings/tokens
   - Create token with "Publish Extensions" permission
   - Add to GitHub Secrets as `OPENVSX_TOKEN`

#### 3. Test Publishing Workflow

Run the workflow manually to test all changes:

```bash
# Trigger workflow
gh workflow run publish-extension.yml \
  --field version=1.0.0-beta.5 \
  --field version_bump=none

# Monitor progress
gh run watch
```

**Expected outcomes**:

- ✅ VSIX packaged successfully
- ✅ Published to GitHub Packages as `@appsmithery/vscode-codechef`
- ✅ Published to Open VSX Registry as `appsmithery.vscode-codechef`
- ✅ GitHub Release created with VSIX asset

---

## Installation Methods Summary

After implementation, users can install via:

### Method 1: npx (One Command)

```bash
# Setup once (create ~/.npmrc)
echo "@appsmithery:registry=https://npm.pkg.github.com" >> ~/.npmrc
echo "//npm.pkg.github.com/:_authToken=YOUR_TOKEN" >> ~/.npmrc

# Install
npx @appsmithery/vscode-codechef
```

**Pros**: Fastest, automated installation  
**Cons**: Requires GitHub token setup (future monetization support)

### Method 2: Open VSX (No Auth)

```bash
code --install-extension appsmithery.vscode-codechef
```

**Pros**: No authentication, public discoverability  
**Cons**: Requires `code` CLI in PATH

### Method 3: GitHub Releases (Manual)

```bash
curl -L https://github.com/Appsmithery/code-chef/releases/latest/download/vscode-codechef-1.0.0.vsix -o codechef.vsix
code --install-extension codechef.vsix
```

**Pros**: Always available, no dependencies  
**Cons**: Manual download step

---

## Further Considerations

### 1. Package Size Optimization

**Issue**: VSIX bundled in npm package may exceed npm's 250MB limit.

**Current approach**: `install-cli.js` checks for bundled VSIX first, falls back to downloading from GitHub releases.

**Test before publishing**:

```bash
cd extensions/vscode-codechef
npm pack --dry-run
```

If package size > 250MB, the download fallback will handle it automatically.

### 2. VS Code Marketplace Publishing

**Status**: Not implemented (requires Azure DevOps setup)

**Recommendation**: Add after validating Open VSX workflow:

- Open VSX: 10K+ users (VSCodium, Gitpod, Code-OSS)
- VS Code Marketplace: 100K+ users (official VS Code)

**Setup**:

1. Create Azure DevOps Personal Access Token (VSCE_PAT)
2. Add to GitHub Secrets
3. Add step to workflow:
   ```yaml
   - name: Publish to VS Code Marketplace
     run: npx vsce publish -p ${{ secrets.VSCE_PAT }}
   ```

### 3. Monitoring & Metrics

Track installation success rates:

- **npx installs**: GitHub Packages download metrics
- **Open VSX installs**: https://open-vsx.org/extension/appsmithery/vscode-codechef
- **GitHub Releases**: Release asset download counts

---

## Testing Checklist

Before releasing to users:

### Pre-Publishing Tests

- [ ] Verify `package.json` has scoped name: `@appsmithery/vscode-codechef`
- [ ] Test `install-cli.js` locally: `node install-cli.js`
- [ ] Confirm `.npmrc` is in `.gitignore`
- [ ] Run `npm pack` and check size < 250MB
- [ ] Test VSIX packaging: `npm run package`

### GitHub Secrets

- [ ] `NPM_TOKEN` added with `read:packages` + `write:packages` scopes
- [ ] `OPENVSX_TOKEN` added from Open VSX Registry
- [ ] Test token permissions: `curl -H "Authorization: token $NPM_TOKEN" https://npm.pkg.github.com/@appsmithery/vscode-codechef`

### Publishing Tests

- [ ] Trigger workflow: `gh workflow run publish-extension.yml`
- [ ] Verify GitHub Packages publication: https://github.com/orgs/Appsmithery/packages
- [ ] Verify Open VSX publication: https://open-vsx.org/extension/appsmithery/vscode-codechef
- [ ] Verify GitHub Release created with VSIX asset

### Installation Tests

- [ ] Test npx install: `npx @appsmithery/vscode-codechef`
- [ ] Test Open VSX install: `code --install-extension appsmithery.vscode-codechef`
- [ ] Test GitHub Releases install: Download VSIX and install manually
- [ ] Test without `code` CLI (expect helpful error message)
- [ ] Test in CI environment (expect skip message)

---

## Documentation Updates Needed

### User-Facing Docs

- [x] README.md installation instructions (updated)
- [ ] Main repository README.md (add npx method)
- [ ] DEVELOPMENT.md (add contributor instructions for `.npmrc`)

### Internal Docs

- [ ] Deployment guide (add Open VSX and npm publishing steps)
- [ ] Troubleshooting guide (add npx installation issues)

---

## Success Metrics

Track these after release:

1. **Installation Success Rate**

   - Target: >95% successful npx installs
   - Measure: GitHub Packages download metrics vs VS Code activation events

2. **Installation Method Adoption**

   - Track downloads by source (npx, Open VSX, GitHub Releases)
   - Optimize most popular method

3. **Support Tickets**
   - Monitor for authentication issues (npx)
   - Track "code command not found" errors
   - Measure before/after comparison

---

## Rollback Plan

If issues arise after publishing:

1. **Revert package.json changes**:

   ```bash
   git revert <commit-hash>
   git push origin main
   ```

2. **Unpublish from registries**:

   ```bash
   # GitHub Packages (cannot unpublish, deprecate instead)
   npm deprecate @appsmithery/vscode-codechef@1.0.0-beta.5 "Use GitHub Releases instead"

   # Open VSX (contact support)
   # Email: admin@open-vsx.org with version to remove
   ```

3. **Update README** to remove npx instructions

4. **GitHub Release** remains unaffected (fallback always available)

---

## Contact & Support

**Questions?** File an issue in [Linear](https://linear.app/dev-ops/project/codechef-78b3b839d36b) with label `extension-installation`.

**Implementation**: All changes completed by GitHub Copilot (Sous Chef) on December 14, 2025.
