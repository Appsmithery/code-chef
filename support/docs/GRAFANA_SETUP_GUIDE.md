# Grafana Setup Guide

## Current Issue
Grafana GitHub OAuth authentication is stuck on "Grafana is loading..." screen.

## Root Cause
Missing GitHub OAuth application configuration for Grafana authentication.

---

## Quick Fix: Use Local Admin Login (Recommended)

**Skip GitHub OAuth and use local credentials:**

1. **Access Grafana directly** at: `http://45.55.173.72:3000`
2. **Login with admin credentials:**
   - Username: `admin`
   - Password: `devtools_grafana_2024` (from `.env`)
3. **Import LLM Token Metrics dashboard:**
   - Go to: Dashboards → Import
   - Upload: `config/grafana/dashboards/llm-token-metrics.json`
   - Select datasource: `Prometheus`
   - Click "Import"

**This bypasses GitHub OAuth entirely and gets you operational immediately.**

---

## Optional: Enable GitHub OAuth (If Needed)

If you want GitHub authentication, follow these steps:

### Step 1: Create GitHub OAuth App

1. **Go to GitHub Settings:**
   - https://github.com/settings/developers
   - Click "OAuth Apps" → "New OAuth App"

2. **Configure OAuth App:**
   ```
   Application name: Dev-Tools Grafana
   Homepage URL: http://45.55.173.72:3000
   Authorization callback URL: http://45.55.173.72:3000/login/github
   ```

3. **Save Client ID and Secret:**
   - After creating, copy the **Client ID**
   - Generate a new **Client Secret** and copy it

### Step 2: Update Environment Variables

Edit `config/env/.env`:

```bash
GRAFANA_GITHUB_AUTH_ENABLED=true
GRAFANA_GITHUB_CLIENT_ID=<your_github_client_id>
GRAFANA_GITHUB_CLIENT_SECRET=<your_github_client_secret>
```

### Step 3: Restart Grafana

```powershell
# On droplet (SSH)
cd /opt/Dev-Tools/deploy
docker compose restart grafana

# Check logs
docker compose logs -f grafana
```

### Step 4: Test GitHub Login

1. Go to: `http://45.55.173.72:3000`
2. Click "Sign in with GitHub"
3. Authorize the OAuth app
4. You should be redirected to Grafana dashboard

---

## MCP Server Connection for Grafana

**Grafana MCP Server** provides tools for dashboard creation, data source management, and query building.

### Prerequisites

The Grafana MCP server requires:
- **Grafana URL**: `http://grafana:3000` (internal) or `http://45.55.173.72:3000` (external)
- **Grafana API Key**: Generate from Grafana UI (Service Account token)

### Generate Grafana API Key

1. **Login to Grafana** (http://45.55.173.72:3000)
2. **Go to:** Configuration (⚙️) → Service Accounts
3. **Create Service Account:**
   - Name: `MCP Server`
   - Role: `Admin` (for full access)
4. **Add Service Account Token:**
   - Click on the service account
   - Click "Add service account token"
   - Name: `mcp-server-token`
   - Copy the generated token (starts with `glsa_`)

### Configure MCP Gateway

Add to `config/env/.env`:

```bash
# Grafana MCP Integration
GRAFANA_URL=http://grafana:3000
GRAFANA_API_KEY=glsa_<your_generated_token>
```

### Verify MCP Connection

```powershell
# Check MCP gateway tools
curl http://45.55.173.72:8000/tools | jq '.[] | select(.name | contains("grafana"))'
```

You should see Grafana tools like:
- `grafana_create_dashboard`
- `grafana_query_prometheus`
- `grafana_list_datasources`
- `grafana_create_alert`

---

## Dashboard Import (Automated)

Once Grafana is running, import the pre-built LLM Token Metrics dashboard:

### Option 1: Manual Import (UI)

1. **Login to Grafana** (http://45.55.173.72:3000)
2. **Navigate to:** Dashboards → Import
3. **Upload file:** `config/grafana/dashboards/llm-token-metrics.json`
4. **Select datasource:** Prometheus (should be pre-configured)
5. **Click:** Import

### Option 2: Automated Import (API)

```powershell
# Set variables
$GRAFANA_URL = "http://45.55.173.72:3000"
$GRAFANA_USER = "admin"
$GRAFANA_PASS = "devtools_grafana_2024"
$DASHBOARD_FILE = "config/grafana/dashboards/llm-token-metrics.json"

# Create API key via basic auth
$auth = [Convert]::ToBase64String([Text.Encoding]::ASCII.GetBytes("${GRAFANA_USER}:${GRAFANA_PASS}"))
$headers = @{
    "Authorization" = "Basic $auth"
    "Content-Type" = "application/json"
}

# Import dashboard
$dashboard = Get-Content $DASHBOARD_FILE | ConvertFrom-Json
$body = @{
    dashboard = $dashboard.dashboard
    overwrite = $true
} | ConvertTo-Json -Depth 20

Invoke-RestMethod -Uri "$GRAFANA_URL/api/dashboards/db" -Method POST -Headers $headers -Body $body
```

---

## Verification Checklist

### ✅ Grafana Service Health
```bash
docker compose ps grafana
curl http://45.55.173.72:3000/api/health
```

### ✅ Prometheus Data Source
```bash
# Login to Grafana UI
# Go to: Configuration → Data Sources
# Verify "Prometheus" datasource is connected
```

### ✅ Dashboard Imported
```bash
# Login to Grafana UI
# Go to: Dashboards → LLM Token Metrics & Cost Attribution
# Verify 10 panels are visible
```

### ✅ Live Metrics Flowing
```bash
# Trigger test LLM call to populate metrics
curl -X POST http://45.55.173.72:8001/orchestrate \
  -H "Content-Type: application/json" \
  -d '{"task": "test", "description": "Health check"}'

# Wait 30s for metrics scrape
# Refresh Grafana dashboard
# Verify token counters update
```

---

## Troubleshooting

### Issue: GitHub OAuth Stuck Loading

**Solution:** Use local admin login instead (see Quick Fix above).

**Root Cause:** Missing OAuth app configuration or misconfigured callback URL.

### Issue: Dashboard Shows "No Data"

**Possible Causes:**
1. Prometheus not scraping orchestrator metrics
2. No LLM calls made yet (fresh deployment)
3. Datasource misconfigured

**Solutions:**
```bash
# 1. Check Prometheus targets
curl http://45.55.173.72:9090/api/v1/targets | jq '.data.activeTargets[] | select(.labels.job=="orchestrator")'

# 2. Trigger test LLM call
curl -X POST http://45.55.173.72:8001/orchestrate -H "Content-Type: application/json" -d '{"task":"test"}'

# 3. Verify datasource
curl http://45.55.173.72:3000/api/datasources -u admin:devtools_grafana_2024
```

### Issue: MCP Server Can't Connect to Grafana

**Solution:**
1. Generate Grafana API key (Service Account token)
2. Add to `.env`: `GRAFANA_API_KEY=glsa_...`
3. Restart gateway: `docker compose restart gateway-mcp`

---

## Next Steps

1. ✅ **Deploy Grafana** → `docker compose up -d grafana`
2. ✅ **Login with admin credentials** → http://45.55.173.72:3000
3. ✅ **Import LLM dashboard** → Upload `llm-token-metrics.json`
4. ⏳ **Trigger test LLM call** → Populate metrics with real data
5. ⏳ **Generate API key** → Enable MCP server integration
6. ⏳ **Monitor first week** → Tune alert thresholds based on usage

---

**Quick Start Command:**

```powershell
# Deploy Grafana
cd d:\INFRA\Dev-Tools\Dev-Tools\deploy
docker compose up -d grafana

# Wait 30s for startup
Start-Sleep -Seconds 30

# Check health
Invoke-RestMethod -Uri "http://45.55.173.72:3000/api/health"

# Open browser
Start-Process "http://45.55.173.72:3000"
```

Login: `admin` / `devtools_grafana_2024`
