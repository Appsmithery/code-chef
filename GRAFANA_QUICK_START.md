# Grafana Quick Start - READY TO USE

## ✅ Status: Grafana is LIVE

**URL**: http://45.55.173.72:3000

**Login Credentials:**

- Username: `admin`
- Password: `devtools_grafana_2024`

**Health Check**: ✅ Healthy (commit: 1e84fede543acc892d2a2515187e545eb047f237)

---

## 🚀 Quick Start (3 Steps)

### Step 1: Login to Grafana

1. Open browser: http://45.55.173.72:3000
2. Enter credentials:
   - Username: `admin`
   - Password: `devtools_grafana_2024`
3. Skip "Change Password" prompt (or change it)

### Step 2: Import LLM Token Metrics Dashboard

**Option A: Automated PowerShell Script**

```powershell
# Run from Dev-Tools root
$GRAFANA_URL = "http://45.55.173.72:3000"
$GRAFANA_USER = "admin"
$GRAFANA_PASS = "devtools_grafana_2024"
$DASHBOARD_FILE = "config/grafana/dashboards/llm-token-metrics.json"

# Create auth header
$auth = [Convert]::ToBase64String([Text.Encoding]::ASCII.GetBytes("${GRAFANA_USER}:${GRAFANA_PASS}"))
$headers = @{
    "Authorization" = "Basic $auth"
    "Content-Type" = "application/json"
}

# Load and prepare dashboard
$dashboard = Get-Content $DASHBOARD_FILE | ConvertFrom-Json
$body = @{
    dashboard = $dashboard.dashboard
    overwrite = $true
    folderUid = ""
} | ConvertTo-Json -Depth 20

# Import dashboard
$response = Invoke-RestMethod -Uri "$GRAFANA_URL/api/dashboards/db" -Method POST -Headers $headers -Body $body
Write-Host "Dashboard imported: $($response.url)"
```

**Option B: Manual UI Import**

1. Login to Grafana (http://45.55.173.72:3000)
2. Click menu (☰) → Dashboards
3. Click "New" → "Import"
4. Upload file: `config/grafana/dashboards/llm-token-metrics.json`
5. Select datasource: **Prometheus** (default)
6. Click "Import"

### Step 3: Trigger Test LLM Call (Populate Metrics)

```powershell
# Send test request to orchestrator
Invoke-RestMethod -Uri "http://45.55.173.72:8001/orchestrate" `
  -Method POST `
  -Headers @{"Content-Type"="application/json"} `
  -Body '{"task":"test","description":"Health check to populate metrics"}'

# Wait 30s for Prometheus scrape
Start-Sleep -Seconds 30

# Refresh dashboard - metrics should appear
```

---

## 📊 Dashboard Features (10 Panels)

Once imported, you'll see:

1. **Token Usage Rate by Agent** - Real-time token/hour by agent + type
2. **Cost Breakdown by Agent** - Pie chart of cost attribution
3. **LLM Latency Distribution** - P50/P95/P99 response times
4. **Total Cost (Last 24h)** - Single stat with threshold colors
5. **Total Tokens (Last 24h)** - Aggregate token usage
6. **Avg Tokens per Call** - Bar gauge per agent
7. **Cost Trend Over Time** - Stacked area chart
8. **Token Type Distribution** - Prompt vs completion ratio
9. **Top 5 Most Expensive Agents** - Table view
10. **Avg Latency by Agent** - Timeseries comparison

---

## 🔗 MCP Server Integration

**Grafana MCP Server** provides tools for dashboard management, alerts, and queries.

### Generate Grafana API Key (for MCP)

1. **Login to Grafana** (http://45.55.173.72:3000)
2. **Go to**: Administration (⚙️) → Service Accounts
3. **Create Service Account**:
   - Name: `MCP Server`
   - Role: `Admin`
4. **Add Token**:
   - Click service account → "Add service account token"
   - Name: `mcp-server-token`
   - Copy token (starts with `glsa_`)

### Configure MCP Gateway

Add to `config/env/.env`:

```bash
# Grafana MCP Integration
GRAFANA_URL=http://grafana:3000
GRAFANA_API_KEY=glsa_<your_token_here>
```

Then restart gateway:

```bash
ssh root@45.55.173.72 "cd /opt/Dev-Tools/deploy && docker compose restart gateway-mcp"
```

### Verify MCP Tools Available

```powershell
# Query MCP gateway for Grafana tools
$tools = Invoke-RestMethod -Uri "http://45.55.173.72:8000/tools"
$tools | Where-Object { $_.name -like "*grafana*" } | Select-Object name, description
```

Expected tools:

- `grafana_create_dashboard`
- `grafana_query_prometheus`
- `grafana_list_datasources`
- `grafana_create_alert`
- `grafana_get_dashboard`

---

## ⚙️ Configuration

### Datasources (Pre-Configured)

1. **Prometheus** (default)

   - URL: http://prometheus:9090
   - Access: Server (proxy)
   - Scrape interval: 10s

2. **Loki** (logs)
   - URL: http://loki:3100
   - Access: Server (proxy)
   - Max lines: 1000

### Environment Variables (`.env`)

```bash
# Grafana Configuration
GRAFANA_ADMIN_USER=admin
GRAFANA_ADMIN_PASSWORD=devtools_grafana_2024
GRAFANA_ROOT_URL=http://45.55.173.72:3000
GRAFANA_GITHUB_AUTH_ENABLED=false  # GitHub OAuth disabled (use local login)
GRAFANA_GITHUB_CLIENT_ID=          # Empty (OAuth not configured)
GRAFANA_GITHUB_CLIENT_SECRET=      # Empty (OAuth not configured)
```

---

## 🔧 Troubleshooting

### Issue: Can't Access Grafana

**Solution**: Check firewall rules

```bash
ssh root@45.55.173.72
ufw status | grep 3000
# If not allowed:
ufw allow 3000/tcp
```

### Issue: Dashboard Shows "No Data"

**Cause**: No LLM calls made yet (fresh deployment)

**Solution**: Trigger test call (see Step 3 above)

### Issue: Prometheus Datasource Error

**Solution**: Verify Prometheus is running

```bash
ssh root@45.55.173.72 "docker compose -f /opt/Dev-Tools/deploy/docker-compose.yml ps prometheus"
curl http://45.55.173.72:9090/-/healthy
```

### Issue: GitHub OAuth Loading Forever

**Solution**: GitHub OAuth is NOT configured. Use local admin login instead.

To enable GitHub OAuth (optional):

1. Create GitHub OAuth App: https://github.com/settings/developers
2. Set callback URL: `http://45.55.173.72:3000/login/github`
3. Add Client ID/Secret to `.env`
4. Set `GRAFANA_GITHUB_AUTH_ENABLED=true`
5. Redeploy: `deploy-to-droplet.ps1 -DeployType config`

---

## 📈 Monitoring Best Practices

### First Hour

- [x] Verify Grafana health (DONE)
- [x] Import LLM dashboard (PENDING)
- [ ] Trigger test LLM call
- [ ] Verify metrics populate in dashboard
- [ ] Generate MCP API key

### First Day

- [ ] Monitor token usage patterns
- [ ] Verify Prometheus scraping (check targets at http://45.55.173.72:9090/targets)
- [ ] Test alert rules (trigger threshold)
- [ ] Review cost trends

### First Week

- [ ] Tune alert thresholds based on actual usage
- [ ] Analyze cost per agent
- [ ] Optimize inefficient agents (high tokens/call)
- [ ] Set up email notifications for alerts

---

## 📚 Resources

- **Grafana Docs**: https://grafana.com/docs/grafana/latest/
- **Prometheus Queries**: `support/docs/OBSERVABILITY_GUIDE.md`
- **Dashboard JSON**: `config/grafana/dashboards/llm-token-metrics.json`
- **Alert Rules**: `config/prometheus/alerts/llm-metrics.yml`
- **Setup Guide**: `support/docs/GRAFANA_SETUP_GUIDE.md`

---

## 🎯 Next Steps

1. **Import Dashboard** → Use PowerShell script or UI (Step 2 above)
2. **Trigger Test Call** → Populate metrics with real data (Step 3 above)
3. **Generate API Key** → Enable MCP integration
4. **Monitor First Week** → Tune alerts and analyze usage

---

**Quick Command to Open Browser:**

```powershell
Start-Process "http://45.55.173.72:3000"
```

Login: `admin` / `devtools_grafana_2024`

---

**Production Status**: ✅ OPERATIONAL  
**Deployment**: Commit 7467ddd (November 24, 2025)  
**Health**: http://45.55.173.72:3000/api/health
