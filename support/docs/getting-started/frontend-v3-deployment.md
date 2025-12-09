# React/TypeScript v3 Frontend Deployment Guide

**Status**: ✅ Ready for Production Deployment  
**Date**: December 9, 2025  
**Commit**: [`4aa26a6`](https://github.com/Appsmithery/Dev-Tools/commit/4aa26a62135b7acb1ea3777eb4fff6cac8336ac8)

---

## Overview

Migrated code-chef frontend from static HTML/CSS to React 18 + TypeScript production application with modern build tooling.

## Technology Stack

- **React 18.2** with TypeScript 5.3
- **Vite 5.0** for lightning-fast builds and HMR
- **Tailwind CSS 4.0** with Code/Chef brand colors (oklch color space)
- **Wouter 3.0** for client-side SPA routing
- **Lucide React** for professional iconography (replaces emojis)
- **Radix UI** for accessible component primitives

## Architecture Changes

### Source Code Structure

```
support/frontend/v3/
├── src/
│   ├── components/
│   │   ├── ui/          # Radix UI + shadcn components
│   │   │   ├── button.tsx
│   │   │   ├── card.tsx
│   │   │   ├── badge.tsx
│   │   │   ├── tooltip.tsx
│   │   │   └── sonner.tsx
│   │   └── ErrorBoundary.tsx
│   ├── contexts/
│   │   └── ThemeContext.tsx  # Light/dark theme support
│   ├── pages/
│   │   ├── Home.tsx      # Main landing page
│   │   └── NotFound.tsx  # 404 page
│   ├── lib/
│   │   └── utils.ts      # Tailwind class merging
│   ├── App.tsx           # Root component with routing
│   ├── main.tsx          # React entry point
│   └── index.css         # Tailwind + brand colors
├── public/
│   └── logos/            # SVG/PNG assets
├── dist/                 # Production build output
├── package.json
├── vite.config.ts
├── tsconfig.json
└── tailwind.config.ts
```

### Key Files & Permalinks

| File                        | Purpose             | GitHub Link                                                                                                                           |
| --------------------------- | ------------------- | ------------------------------------------------------------------------------------------------------------------------------------- |
| `vite.config.ts`            | Build configuration | [View](https://github.com/Appsmithery/Dev-Tools/blob/4aa26a62135b7acb1ea3777eb4fff6cac8336ac8/support/frontend/v3/vite.config.ts)     |
| `deploy/docker-compose.yml` | Caddy volume mount  | [View](https://github.com/Appsmithery/Dev-Tools/blob/4aa26a62135b7acb1ea3777eb4fff6cac8336ac8/deploy/docker-compose.yml#L320-L325)    |
| `config/caddy/Caddyfile`    | SPA routing config  | [View](https://github.com/Appsmithery/Dev-Tools/blob/4aa26a62135b7acb1ea3777eb4fff6cac8336ac8/config/caddy/Caddyfile#L64-L69)         |
| `src/pages/Home.tsx`        | Main landing page   | [View](https://github.com/Appsmithery/Dev-Tools/blob/4aa26a62135b7acb1ea3777eb4fff6cac8336ac8/support/frontend/v3/src/pages/Home.tsx) |

### Docker Compose Changes

**File**: `deploy/docker-compose.yml`

```diff
   caddy:
     volumes:
-      - ../support/frontend:/srv/frontend:ro
+      - ../support/frontend/v3/dist:/srv/frontend:ro
```

**Impact**: Caddy now serves the optimized React production bundle instead of raw HTML files.

### Caddyfile Changes

**File**: `config/caddy/Caddyfile`

```diff
-  # Serve frontend files from mounted volume (MUST come after API handlers)
+  # Serve React SPA from mounted volume (MUST come after API handlers)
+  # SPA routing: try file, then fallback to index.html for client-side routing
   handle {
     root * /srv/frontend
+    encode gzip
     try_files {path} /index.html
     file_server
   }
```

**Impact**: Enables SPA routing—page refreshes on `/agents` or `/servers` will serve `index.html` instead of 404.

### Deprecated Files

Old static HTML files moved to: [`support/frontend/deprecated/`](https://github.com/Appsmithery/Dev-Tools/tree/4aa26a62135b7acb1ea3777eb4fff6cac8336ac8/support/frontend/deprecated)

- `index.html` (old homepage)
- `agents.html`, `servers.html`, `docs-overview-new.html`
- `production-landing.html`
- `styles.css` (legacy CSS)

**Deletion Schedule**: Safe to delete after **January 9, 2026** (30 days post-migration).

---

## Build Performance

| Metric                      | Size (Raw) | Size (Gzipped) |
| --------------------------- | ---------- | -------------- |
| **Total Bundle**            | 343 KB     | 89 KB          |
| Vendor chunk (React + deps) | 146 KB     | 48 KB          |
| App chunk (code-chef code)  | 90 KB      | 29 KB          |
| UI chunk (Lucide + Sonner)  | 38 KB      | 11 KB          |
| CSS (Tailwind purged)       | 69 KB      | 11 KB          |
| HTML                        | 7 KB       | 2 KB           |

**Vite Build Output**:

```
✓ 1487 modules transformed.
dist/index.html                   7.14 kB │ gzip:  2.24 kB
dist/assets/index-BWr_m9E-.css   68.99 kB │ gzip: 10.63 kB
dist/assets/ui-Dnd0nIQY.js       38.19 kB │ gzip: 10.81 kB
dist/assets/index-CciHdlO5.js    89.56 kB │ gzip: 28.79 kB
dist/assets/vendor-DLHwVcFw.js  146.38 kB │ gzip: 47.80 kB
✓ built in 4.97s
```

---

## Deployment Steps

### Prerequisites

- Access to DigitalOcean droplet (`45.55.173.72`)
- SSH key configured
- Git repository access

### 1. Build Production Bundle Locally (Optional Verification)

```bash
cd support/frontend/v3
npm install
npm run build
# Verify dist/ directory created with assets
```

### 2. Deploy to Production

```bash
# SSH into production droplet
ssh root@45.55.173.72

# Navigate to application directory
cd /opt/code-chef

# Pull latest changes (includes commit 4aa26a6)
git pull origin main

# Install dependencies and build frontend
cd support/frontend/v3
npm install
npm run build

# Return to root and restart Caddy to pick up new files
cd /opt/code-chef
docker compose restart caddy

# Verify Caddy is healthy
docker compose ps caddy
```

### 3. Verify Deployment

Open in browser:

- **Homepage**: https://codechef.appsmithery.co
- **Health Check**: https://codechef.appsmithery.co/api/health
- **Test SPA routing**: Navigate around, then refresh page—should not 404

Check browser console for errors:

```javascript
// Should see React mount logs, no errors
```

### 4. Monitor for 24 Hours

- Check Grafana for Caddy metrics: https://appsmithery.grafana.net
- Monitor Loki logs for 404s or errors
- Verify Let's Encrypt SSL certificate renewal

---

## Testing Checklist

- [ ] Homepage loads with React app (not static HTML)
- [ ] Code/Chef logo and branding visible
- [ ] Theme toggle works (light/dark mode persists in localStorage)
- [ ] Navigation between sections smooth (no page reloads)
- [ ] API health check link functional
- [ ] GitHub link in header opens in new tab
- [ ] No console errors in browser DevTools
- [ ] Mobile responsive layout verified (test on phone)
- [ ] SPA routing handles page refreshes correctly (no 404s)
- [ ] Assets load over HTTPS (padlock icon in browser)
- [ ] Font loading: Google Sans Code renders correctly

---

## Rollback Plan

If critical issues occur, revert to static HTML:

### Option 1: Docker Compose Rollback

```bash
cd /opt/code-chef

# Edit deploy/docker-compose.yml
nano deploy/docker-compose.yml

# Change line 324:
- ../support/frontend/v3/dist:/srv/frontend:ro
# to:
- ../support/frontend/deprecated:/srv/frontend:ro

# Restart Caddy
docker compose restart caddy
```

### Option 2: Git Rollback

```bash
cd /opt/code-chef
git revert 4aa26a62135b7acb1ea3777eb4fff6cac8336ac8
docker compose restart caddy
```

---

## Known Issues & Limitations

### Current Limitations

1. **No Agents/Servers pages yet**: Only Homepage implemented in v3
   - Old pages still in `deprecated/` if needed
2. **No Cookbook/Docs page**: Future enhancement
3. **Theme preference**: Stored in localStorage (not synced across devices)

### Future Enhancements

- [ ] Migrate Agents page to React
- [ ] Migrate Servers page to React
- [ ] Add Cookbook/Documentation section
- [ ] Implement real-time status indicators via WebSocket
- [ ] Add analytics (Plausible or PostHog)
- [ ] Progressive Web App (PWA) manifest

---

## Monitoring & Observability

### Metrics to Watch

**Grafana Dashboard**: https://appsmithery.grafana.net

- Caddy request rate (`caddy_http_requests_total`)
- Response times (P50, P95, P99)
- Error rate (4xx, 5xx)
- Static asset cache hit rate

**Loki Logs**: https://appsmithery.grafana.net/a/grafana-lokiexplore-app/explore

```logql
{job="caddy"} |= "GET /" | json
```

### Alerts to Configure

1. **High 404 rate**: Indicates SPA routing misconfiguration
2. **Slow response times**: Check Caddy gzip encoding overhead
3. **SSL cert expiry**: Let's Encrypt auto-renewal failure

---

## Success Criteria

✅ **Deployment Successful** if:

1. Homepage loads in < 2 seconds (LCP)
2. Zero 404 errors on valid routes
3. Theme toggle persists across sessions
4. Mobile responsive (no horizontal scroll)
5. No console errors or warnings
6. HTTPS certificate valid
7. API proxying still works (`/api/*` routes)

---

## Contact & Support

- **Primary**: Alex Torelli (@alextorelli28)
- **GitHub**: https://github.com/Appsmithery/Dev-Tools/issues
- **Linear**: code-chef project board

## Related Documentation

- [Architecture Overview](https://github.com/Appsmithery/Dev-Tools/blob/main/support/docs/ARCHITECTURE.md)
- [Deployment Guide](https://github.com/Appsmithery/Dev-Tools/blob/main/support/docs/DEPLOYMENT.md)
- [Caddy Configuration](https://github.com/Appsmithery/Dev-Tools/blob/main/config/caddy/Caddyfile)

---

**Last Updated**: December 9, 2025  
**Next Review**: January 9, 2026 (30-day post-deployment check)
