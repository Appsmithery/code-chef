# MCP Gateway (Linear OAuth Service)

**Purpose:** Linear OAuth integration for Dev-Tools agents

Node.js service that provides OAuth 2.0 authentication and API access for Linear.

**Note:** This gateway handles **Linear integration only**. MCP tool routing has been
moved to direct Python MCP SDK access in agents. See `support/docs/ARCHITECTURE.md` for details.

## Features

- **Linear OAuth 2.0** (actor=`app`) installation flow for the `comet-gateway-local` Linear application
- **Token persistence** with automatic refresh and optional developer-token fallback for local runs
- **REST endpoints** for roadmap summaries (`/api/linear-issues`) and project views (`/api/linear-project/:projectId`)
- **Health endpoints** for Docker Compose orchestration

## Architecture

```
Python Agents → linear-sdk (direct) → Linear API ✅
              ↘
                Gateway (OAuth flow) → Linear OAuth → Token Storage
```

**What this gateway does:**

- OAuth authorization flow (`/oauth/linear/install`, `/oauth/linear/callback`)
- Token storage and refresh
- Linear API endpoints for OAuth-based access

**What this gateway does NOT do:**

- ❌ MCP server tool routing (handled by Python agents directly)
- ❌ MCP server discovery (handled by `mcp_discovery.py`)
- ❌ Generic tool invocation (handled by `mcp_tool_client.py`)

## Configuration

Copy `.env.example` to `.env` (or supply environment variables through Docker Compose):

```
PORT=8000
LINEAR_OAUTH_CLIENT_ID=...
LINEAR_OAUTH_CLIENT_SECRET=...
LINEAR_OAUTH_REDIRECT_URI=https://<host>/oauth/linear/callback
LINEAR_OAUTH_SCOPES=read,write,app:mentionable,app:assignable
LINEAR_OAUTH_DEV_TOKEN=lin_oauth_...
LINEAR_WEBHOOK_URI=https://<host>/webhook
LINEAR_WEBHOOK_SIGNING_SECRET=lin_wh_...
LINEAR_TOKEN_STORE_DIR=./config
```

The token store defaults to `./config/linear-token.json`, which is mounted as a
volume in Docker for persistence.

## Local Development

```
npm install
npm run dev
```

Visit `http://localhost:8000/oauth/linear/install` to authorize the agent and
then hit `http://localhost:8000/api/linear-issues` to fetch roadmap data.
