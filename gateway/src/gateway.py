"""Legacy placeholder.

The MCP gateway is now implemented as a Node.js service. See `app.js`
and accompanying modules in this directory for the active entrypoint.
This file remains only so existing import paths fail loudly if used.
"""

raise RuntimeError(
    "The MCP gateway now runs via Node.js. Use npm scripts in mcp/gateway."
)