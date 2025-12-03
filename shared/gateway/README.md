# Gateway (Deprecated)

**Deprecated:** December 3, 2025

The MCP Gateway service has been removed from the architecture.

## What Changed

- **Linear OAuth** is no longer needed - direct GraphQL via `LINEAR_API_KEY` in `.env`
- **MCP Tools** are accessed via Docker MCP Toolkit, not a Docker service
- **Webhooks** are handled directly by the orchestrator at `/webhooks/linear`

## Current Architecture

All Linear integration is now handled by:

- `shared/lib/linear_workspace_client.py` - Direct GraphQL client
- `agent_orchestrator/main.py` - Webhook handler at `/webhooks/linear`

## Archive Location

The original gateway code has been archived to:

```
_archive/gateway-deprecated-2025-12-03/
```

## Migration Notes

If you were using the gateway for Linear OAuth:

1. Set `LINEAR_API_KEY` in `config/env/.env` (OAuth token with full access)
2. Set `LINEAR_TEAM_ID` and `LINEAR_WEBHOOK_SIGNING_SECRET`
3. Update Linear webhook URL to point to `https://your-domain/webhooks/linear`
