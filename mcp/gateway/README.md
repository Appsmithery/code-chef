# MCP Gateway

Node.js service that fronts Model Context Protocol (MCP) resources and now
includes a Linear roadmap integration for agent access.

## Features

- OAuth 2.0 (actor=`app`) installation flow for the `comet-gateway-local` Linear application.
- Token persistence with automatic refresh and optional developer-token fallback for local runs.
- REST endpoints for roadmap summaries (`/api/linear-issues`) and project-level views (`/api/linear-project/:projectId`).
- Health + metadata endpoints for compose orchestration.

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
