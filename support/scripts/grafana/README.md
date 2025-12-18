# Grafana Dashboard Management

Scripts for managing Grafana Cloud dashboards for code-chef monitoring.

## 📁 Files

| File                    | Purpose                                        |
| ----------------------- | ---------------------------------------------- |
| `upload_dashboards.ps1` | Upload all dashboards to Grafana Cloud via API |
| `README.md`             | This file                                      |

## 🚀 Quick Start

### 1. Get Your Grafana API Key

1. Go to https://appsmithery.grafana.net
2. Click **Settings** (gear icon) → **API Keys**
3. Click **Add API Key**
4. Configure:
   - **Name**: `Dashboard Upload`
   - **Role**: **Editor**
   - **Time to live**: Never expire (or 30 days)
5. Click **Add**
6. **Copy the API key** (starts with `glsa_...`)

### 2. Set Environment Variable

```powershell
# In PowerShell (persistent for session)
$env:GRAFANA_CLOUD_API_TOKEN = "glsa_your_key_here"

# Or add to your .env file
echo "GRAFANA_CLOUD_API_TOKEN=glsa_your_key_here" >> config/env/.env
```

### 3. Upload Dashboards

```powershell
# Dry run (preview what will be uploaded)
.\support\scripts\grafana\upload_dashboards.ps1 -DryRun

# Upload all dashboards
.\support\scripts\grafana\upload_dashboards.ps1

# Or with explicit API key
.\support\scripts\grafana\upload_dashboards.ps1 -ApiKey "glsa_your_key_here"
```

## 📊 Available Dashboards

Located in `config/grafana/dashboards/`:

1. **llm-token-metrics.json** - Token usage, cost tracking, latency
2. **agent-performance.json** - HTTP metrics, response times, error rates
3. **hitl-approval-workflow.json** - Human-in-the-loop monitoring
4. **intent-recognition-mode-analysis.json** - Task routing analytics

## 🔧 Advanced Usage

### Custom Grafana Instance

```powershell
.\support\scripts\grafana\upload_dashboards.ps1 `
    -GrafanaUrl "https://your-instance.grafana.net" `
    -ApiKey "glsa_..."
```

### Custom Dashboard Directory

```powershell
.\support\scripts\grafana\upload_dashboards.ps1 `
    -DashboardDir "path/to/dashboards"
```

## 🐛 Troubleshooting

### Error: GRAFANA_CLOUD_API_TOKEN not set

Set the environment variable:

```powershell
$env:GRAFANA_CLOUD_API_TOKEN = "glsa_..."
```

### Error: 401 Unauthorized

- API key is invalid or expired
- Create a new key with **Editor** role
- Ensure key starts with `glsa_`

### Error: 403 Forbidden

- API key doesn't have sufficient permissions
- Recreate key with **Editor** role (not Viewer)

### Error: 404 Not Found

- Grafana URL is incorrect
- Check: https://appsmithery.grafana.net

### Dashboard Not Showing Data

After upload:

1. **Select datasource**: Edit dashboard → Settings → Variables → Datasource = `grafanacloud-appsmithery-prom`
2. **Wait for metrics**: LLM metrics populate after orchestrator makes LLM calls
3. **Test endpoint**: `curl http://localhost:8001/metrics | grep llm_`

## 📈 Verify Upload

After running the script:

1. Go to https://appsmithery.grafana.net/dashboards
2. You should see 4 new dashboards
3. Open "LLM Token Metrics & Cost Attribution"
4. If empty, make a test LLM call:
   ```bash
   curl -X POST https://codechef.appsmithery.co/execute \
     -H "Content-Type: application/json" \
     -d '{"message": "Create hello world", "user_id": "test"}'
   ```

## 🔄 Update Dashboards

To update existing dashboards, just run the upload script again. The `-overwrite true` flag ensures dashboards are replaced.

## 🎯 Next Steps

After upload:

1. ✅ Dashboards imported
2. ⏭️ Configure alerts (optional)
3. ⏭️ Create custom views
4. ⏭️ Share with team

## 📚 Related Documentation

- [Grafana Agent Config](../../../config/grafana/agent-config.yaml)
- [Observability Guide](../../docs/integrations/observability-guide.md)
- [LLM Operations](../../docs/operations/LLM_OPERATIONS.md)
