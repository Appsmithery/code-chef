# Import Grafana Dashboards to Grafana Cloud

## Quick Import Steps

### Option 1: Via Grafana Cloud UI (Recommended)

1. **Navigate to**: https://appsmithery.grafana.net
2. **Click**: Dashboards → New → Import
3. **Upload** one of these files:
   - `config/grafana/dashboards/agent-performance.json`
   - `config/grafana/dashboards/llm-token-metrics.json`
4. **Select datasource**: "grafanacloud-appsmithery-prom" (or "Prometheus")
5. **Click**: Import

### Option 2: Via API (Automated)

```powershell
# Set your Grafana Cloud API key
$GRAFANA_API_KEY = "your-api-key-here"
$GRAFANA_URL = "https://appsmithery.grafana.net"

# Import Agent Performance Dashboard
$dashboard = Get-Content "config/grafana/dashboards/agent-performance.json" -Raw | ConvertFrom-Json
$body = @{
    dashboard = $dashboard.dashboard
    overwrite = $true
} | ConvertTo-Json -Depth 100

Invoke-RestMethod -Uri "$GRAFANA_URL/api/dashboards/db" `
    -Method Post `
    -Headers @{"Authorization" = "Bearer $GRAFANA_API_KEY"} `
    -ContentType "application/json" `
    -Body $body
```

## Why Manual Import is Needed

**Local Grafana** (port 3000):

- ✅ Auto-provisions from `config/grafana/dashboards/` via Docker volumes
- ✅ Works automatically with docker-compose

**Grafana Cloud** (appsmithery.grafana.net):

- ❌ Cannot access local files
- ✅ Must manually import via UI or API
- ✅ Stores dashboards in cloud

## Dashboard Status

### Available for Import:

1. ✅ **agent-performance.json** - HTTP metrics, response times, errors
2. ✅ **llm-token-metrics.json** - Token usage, cost tracking

### After Import:

- Configure datasource: "grafanacloud-appsmithery-prom"
- Dashboards will auto-refresh every 30s
- Data will populate from droplet Prometheus (via Grafana Alloy)

## Alternative: Use Local Grafana

If you want auto-provisioned dashboards:

```powershell
# Access local Grafana on droplet
ssh -L 3000:localhost:3000 root@45.55.173.72

# Open in browser
http://localhost:3000

# Login
Username: admin
Password: admin (or check .env GRAFANA_ADMIN_PASSWORD)
```

Local Grafana will automatically have both dashboards loaded from the volumes.

---

**Recommended**: Import both dashboards to Grafana Cloud via the UI (takes 2 minutes).
