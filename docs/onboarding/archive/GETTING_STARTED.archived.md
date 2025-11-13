## Integration Modes

Dev-Tools can be integrated into your project in three ways:

### 1. Git Submodule (Recommended)

Best for projects that want version control over the Dev-Tools dependency.

```bash
# Add as submodule
git submodule add -b prospect-pro-tools \
  https://github.com/Alextorelli/Dev-Tools.git dev-tools-package

# Initialize and update
git submodule update --init --recursive

# Update to latest
cd dev-tools-package
git pull origin prospect-pro-tools
cd ..
git add dev-tools-package
git commit -m "Update dev-tools-package"
```

**Advantages**:

- Version pinning at commit level
- Can customize for your project
- Tracked in version control

**Disadvantages**:

- Requires submodule management
- Team must run `git submodule update`

### 2. NPM Package (Coming Soon)

Once published to npm registry:

```bash
npm install @prospectpro/dev-tools --save-dev
```

**Advantages**:

- Standard npm workflow
- Semantic versioning
- Easy updates

**Disadvantages**:

- Less flexibility for customization
- Depends on npm registry

### 3. Direct Clone

For evaluation or one-time use:

```bash
git clone https://github.com/Alextorelli/Dev-Tools.git dev-tools
cd dev-tools
npm install
```

## Project Integration

### 1. Add Dev-Tools to Your Project

Using git submodule:

```bash
cd your-project/
git submodule add https://github.com/Alextorelli/Dev-Tools.git dev-tools-package
git submodule update --init --recursive
```

### 2. Install Dependencies

```bash
cd dev-tools-package
npm install
cd ..
```

### 3. Environment Configuration

#### Option A: Shared Environment

Link your project's `.env` to Dev-Tools:

```bash
ln -s ../.env dev-tools-package/.env
```

#### Option B: Separate Environment

Create a dedicated Dev-Tools environment:

```bash
cp dev-tools-package/.env.example dev-tools-package/.env.agent.local
# Edit dev-tools-package/.env.agent.local with your values
```

### 4. Add npm Scripts

Update your project's `package.json`:

```json
{
  "scripts": {
    "diagnostics": "cd dev-tools-package && npm run diagnostics:baseline",
    "diagnostics:env": "cd dev-tools-package && npm run diagnostics:env",
    "mcp:init": "cd dev-tools-package && ./scripts/automation/init-mcp.sh",
    "mcp:stop": "cd dev-tools-package && ./scripts/automation/reset-mcp.sh"
  }
}
```

### 5. Configure Git Ignore

Add to your `.gitignore`:

```gitignore
# Dev-Tools generated reports
dev-tools-package/reports/context/latest/*.json
dev-tools-package/reports/context/latest/*.md

# Dev-Tools runtime state
dev-tools-package/workspace/runtime/*.json
dev-tools-package/workspace/runtime/logs/

# Dev-Tools environment
dev-tools-package/.env
dev-tools-package/.env.local
dev-tools-package/.env.agent.local
```

## Usage Examples

### Running Diagnostics

From your project root:

```bash
# Full diagnostic baseline
npm run diagnostics

# Environment check only
npm run diagnostics:env

# Or run directly
cd dev-tools-package
npm run diagnostics:baseline
```

### Starting MCP Servers

```bash
# Initialize MCP servers
npm run mcp:init

# Stop MCP servers
npm run mcp:stop
```

### Accessing Reports

Diagnostic reports are saved in:

```
dev-tools-package/reports/context/latest/
├── env-diagnostics.json
├── repo-structure.json
├── repo-structure.md
├── package-inventory.json
└── language-report.json
```

Read reports:

```bash
# View environment diagnostics
cat dev-tools-package/reports/context/latest/env-diagnostics.json | jq

# View language report
cat dev-tools-package/reports/context/latest/language-report.json | jq '.languages'
```

## Environment Management

### Environment File Priority

Dev-Tools loads environment variables in this order:

1. `dev-tools-package/agents/.env.agent.local`
2. `dev-tools-package/.env.agent.local`
3. `dev-tools-package/.env`
4. System environment variables

### Required Variables

Minimum configuration:

```bash
NODE_ENV=development
```

### Recommended Variables

For full functionality:

```bash
# Supabase (for MCP database features)
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-anon-key

# GitHub (for repository operations)
GITHUB_TOKEN=ghp_your_token

# Highlight.io (for observability)
HIGHLIGHT_PROJECT_ID=your-project-id
```

### Project-Specific Variables

You can extend Dev-Tools with your own variables. They'll be included in diagnostic reports if present.

## Advanced Integration

### Custom npm Scripts

Create project-specific diagnostic workflows:

```json
{
  "scripts": {
    "validate": "npm run diagnostics && npm test",
    "pre-deploy": "npm run diagnostics && npm run lint && npm test",
    "dev:setup": "npm run diagnostics:env && npm run mcp:init"
  }
}
```

### CI/CD Integration

Add to your GitHub Actions workflow:

```yaml
name: CI

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
        with:
          submodules: recursive

      - uses: actions/setup-node@v3
        with:
          node-version: "20"

      - name: Install dependencies
        run: |
          npm install
          cd dev-tools-package && npm install

      - name: Run diagnostics
        run: npm run diagnostics

      - name: Run tests
        run: npm test

      - name: Upload diagnostic reports
        uses: actions/upload-artifact@v3
        with:
          name: diagnostic-reports
          path: dev-tools-package/reports/context/latest/
```

### Pre-commit Hooks

Add diagnostics to your pre-commit hooks:

```bash
# .git/hooks/pre-commit
#!/bin/bash
echo "Running diagnostics..."
cd dev-tools-package && npm run diagnostics:env
if [ $? -ne 0 ]; then
    echo "Diagnostics failed. Please fix environment configuration."
    exit 1
fi
```

### VS Code Integration

Add to `.vscode/tasks.json`:

```json
{
  "version": "2.0.0",
  "tasks": [
    {
      "label": "Diagnostics: Full Baseline",
      "type": "shell",
      "command": "cd dev-tools-package && npm run diagnostics:baseline",
      "problemMatcher": [],
      "group": {
        "kind": "test",
        "isDefault": false
      }
    },
    {
      "label": "MCP: Initialize",
      "type": "shell",
      "command": "cd dev-tools-package && ./scripts/automation/init-mcp.sh",
      "problemMatcher": []
    }
  ]
}
```

## Upgrading Dev-Tools

### Git Submodule

```bash
cd dev-tools-package
git fetch
git checkout prospect-pro-tools
git pull
cd ..
git add dev-tools-package
git commit -m "Update Dev-Tools to latest"
```

### Direct Clone

```bash
cd dev-tools-package
git pull origin prospect-pro-tools
npm install
```

## Troubleshooting

### Submodule Not Initialized

```bash
git submodule update --init --recursive
```

### Permission Denied on Scripts

```bash
chmod +x dev-tools-package/scripts/automation/*.sh
```

### Environment Variables Not Loading

1. Verify `.env` file exists
2. Check file priority (see [Environment Management](#environment-management))
3. Ensure proper format (no spaces around `=`)

### Diagnostics Fail

1. Check Node.js version: `node --version` (>= 20.0.0)
2. Reinstall dependencies:
   ```bash
   cd dev-tools-package
   rm -rf node_modules package-lock.json
   npm install
   ```
3. Run with verbose logging:
   ```bash
   npm run diagnostics:env 2>&1 | tee diagnostic.log
   ```

## Best Practices

### 1. Version Pinning

Pin Dev-Tools to a specific commit or tag in production:

```bash
cd dev-tools-package
git checkout v1.1.0  # or specific commit SHA
cd ..
git add dev-tools-package
git commit -m "Pin Dev-Tools to v1.1.0"
```

### 2. Regular Updates

Update Dev-Tools monthly to get latest features and fixes.

### 3. Environment Isolation

Use separate `.env.agent.local` for Dev-Tools to avoid conflicts with your project.

### 4. Report Archiving

Archive diagnostic reports before major changes:

```bash
cp -r dev-tools-package/reports/context/latest \
  dev-tools-package/reports/context/archive-$(date +%Y%m%d)
```

### 5. CI Validation

Always run diagnostics in CI to catch environment issues early.

## Next Steps

1. **Run Initial Diagnostics**: `npm run diagnostics`
2. **Review Reports**: Check `dev-tools-package/reports/context/latest/`
3. **Configure MCP**: If using MCP servers, run `npm run mcp:init`
4. **Integrate with CI**: Add diagnostic checks to your pipeline
5. **Customize Scripts**: Add project-specific diagnostic workflows

## Support

- **Documentation**: [docs/DOCUMENTATION_INDEX.md](../DOCUMENTATION_INDEX.md)
- **Setup Guide**: [docs/SETUP_GUIDE.md](../SETUP_GUIDE.md)
- **Issues**: https://github.com/Alextorelli/Dev-Tools/issues

---

**Version**: 1.1.0
**Last Updated**: 2025-11-02
