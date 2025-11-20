# GitHub Packages Installation Guide

This guide explains how to install MCP Bridge Client packages from GitHub Packages.

## Prerequisites

You need a GitHub Personal Access Token (PAT) with `read:packages` permission.

**Create a PAT:**

1. Go to https://github.com/settings/tokens
2. Click "Generate new token (classic)"
3. Select scope: `read:packages`
4. Generate and copy the token

## NPM Package Installation

### 1. Configure NPM to use GitHub Packages

Create or edit `~/.npmrc` (global) or `.npmrc` (project-level):

```
@appsmithery:registry=https://npm.pkg.github.com
//npm.pkg.github.com/:_authToken=YOUR_GITHUB_TOKEN
```

**Windows:** `C:\Users\<USERNAME>\.npmrc`  
**Linux/Mac:** `~/.npmrc`

### 2. Install the package

```bash
npm install @appsmithery/mcp-bridge-client
```

### 3. Usage

```typescript
import { MCPBridgeClient } from "@appsmithery/mcp-bridge-client";

const client = new MCPBridgeClient({
  gatewayUrl: "http://45.55.173.72:8000",
});

const tools = await client.listTools();
```

## Python Package Installation

### 1. Configure pip to use GitHub Packages

Create or edit `~/.pypirc`:

```ini
[distutils]
index-servers =
    github

[github]
repository = https://pypi.pkg.github.com/Appsmithery
username = YOUR_GITHUB_USERNAME
password = YOUR_GITHUB_TOKEN
```

**Alternative: Environment Variable**

```bash
export PIP_INDEX_URL=https://${GITHUB_USERNAME}:${GITHUB_TOKEN}@pypi.pkg.github.com/Appsmithery/simple/
```

### 2. Install the package

```bash
pip install mcp-bridge-client
```

### 3. Usage

```python
import asyncio
from mcp_bridge_client import MCPBridgeClient

async def main():
    async with MCPBridgeClient(gateway_url='http://45.55.173.72:8000') as client:
        tools = await client.list_tools()
        print(f"Found {len(tools)} tools")

asyncio.run(main())
```

## Local Testing (Before Publishing)

### NPM Package

```bash
cd packages/mcp-bridge-client

# Test build
npm run build

# Test local installation
npm link

# In another project
npm link @appsmithery/mcp-bridge-client
```

### Python Package

```bash
cd packages/mcp-bridge-client-py

# Test build
python -m build

# Test local installation
pip install -e .

# Verify import
python -c "from mcp_bridge_client import MCPBridgeClient; print('✅ Success')"
```

## Publishing Packages

### Manual Publishing

**NPM:**

```bash
cd packages/mcp-bridge-client
npm run build
echo "//npm.pkg.github.com/:_authToken=${GITHUB_TOKEN}" >> .npmrc
npm publish
```

**Python:**

```bash
cd packages/mcp-bridge-client-py
python -m build
twine upload --repository-url https://upload.pypi.org/legacy/ dist/* -u __token__ -p ${GITHUB_TOKEN}
```

### Automated Publishing (GitHub Actions)

**Trigger NPM publish:**

```bash
git tag npm-v0.1.0
git push origin npm-v0.1.0
```

**Trigger Python publish:**

```bash
git tag py-v0.1.0
git push origin py-v0.1.0
```

GitHub Actions workflows will automatically build and publish packages when tags are pushed.

## Troubleshooting

### NPM: 401 Unauthorized

- Verify your GitHub token has `read:packages` scope
- Check `.npmrc` file exists and has correct token
- Try regenerating your GitHub PAT

### Python: Authentication Failed

- Verify token in `~/.pypirc` or environment variable
- Use `__token__` as username, not your GitHub username
- Check repository URL is correct

### NPM: Package not found

- Ensure package is published: https://github.com/Appsmithery/Dev-Tools/packages
- Verify `@appsmithery` scope is configured in `.npmrc`
- Check package name matches exactly: `@appsmithery/mcp-bridge-client`

### Python: No matching distribution

- Ensure package is published to GitHub Packages
- Verify repository URL in pip config
- Try: `pip install --index-url https://pypi.pkg.github.com/Appsmithery/simple/ mcp-bridge-client`

## CI/CD Integration

### GitHub Actions

```yaml
- name: Setup npm for GitHub Packages
  run: |
    echo "@appsmithery:registry=https://npm.pkg.github.com" >> .npmrc
    echo "//npm.pkg.github.com/:_authToken=${{ secrets.GITHUB_TOKEN }}" >> .npmrc

- name: Install dependencies
  run: npm install @appsmithery/mcp-bridge-client
```

### Docker

```dockerfile
# NPM in Dockerfile
ARG GITHUB_TOKEN
RUN echo "@appsmithery:registry=https://npm.pkg.github.com" > .npmrc && \
    echo "//npm.pkg.github.com/:_authToken=${GITHUB_TOKEN}" >> .npmrc && \
    npm install @appsmithery/mcp-bridge-client

# Python in Dockerfile
ARG GITHUB_TOKEN
RUN pip install --index-url https://__token__:${GITHUB_TOKEN}@pypi.pkg.github.com/Appsmithery/simple/ mcp-bridge-client
```

## Security Notes

- **Never commit tokens** to version control
- Use environment variables or secret management
- Rotate tokens regularly
- Use fine-grained PATs with minimal permissions
- Store tokens in GitHub Secrets for CI/CD

## Support

- **Issues:** https://github.com/Appsmithery/Dev-Tools/issues
- **Packages:** https://github.com/Appsmithery?tab=packages
- **Documentation:** See package README files
