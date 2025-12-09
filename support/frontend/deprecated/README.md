# Deprecated Static Files

This directory contains the previous static HTML/CSS frontend implementations that have been replaced by the React/TypeScript v3 implementation.

## Migration Date

December 9, 2025

## Deprecated Files

- `index.html` - Original homepage (static HTML)
- `agents.html` - Agents listing page (static HTML)
- `servers.html` - Servers listing page (static HTML)
- `docs-overview-new.html` - Documentation page (static HTML)
- `production-landing.html` - Production landing variant (static HTML)
- `styles.css` - Legacy CSS styles

## Active Frontend

The production frontend is now served from:

- **Source**: `support/frontend/v3/`
- **Build Output**: `support/frontend/v3/dist/`
- **Technology Stack**: React 18 + TypeScript + Vite + Tailwind CSS 4
- **Routing**: Wouter (client-side SPA routing)

## Caddy Configuration

Production deployment via `config/caddy/Caddyfile`:

- Serves from: `/srv/frontend` (mounted to `v3/dist` in docker-compose.yml)
- SPA routing with fallback to `index.html`

## Rollback Instructions

If rollback is necessary:

1. Update `deploy/docker-compose.yml` caddy volume:

   ```yaml
   - ../support/frontend/deprecated:/srv/frontend:ro
   ```

2. Update `config/caddy/Caddyfile` to remove SPA encoding if needed

3. Rebuild and restart: `docker compose up -d --build caddy`

## Deletion Schedule

These files can be safely deleted after **January 9, 2026** (30 days post-migration).
