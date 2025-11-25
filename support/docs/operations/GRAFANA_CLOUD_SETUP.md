# Grafana Cloud Setup Guide

## Current Configuration

**Grafana Cloud Instance**: https://appsmithery.grafana.net  
**Organization**: appsmithery  
**Stack**: 1376474-hm

## Step 1: Create Service Account Token

The current API token may need additional permissions. Create a new service account token with dashboard write access:

1. Go to https://appsmithery.grafana.net
2. Navigate to **Administration** → **Service Accounts**
3. Click **Add service account**
   - Name: `MCP DevTools Integration`
   - Role: `Admin` or `Editor`
4. Click **Add service account token**
   - Name: `MCP Server Access`
   - Expiration: No expiration (or long-lived)
5. Copy the token (starts with `glsa_`)
6. Update `.env`:
   ```bash
   GRAFANA_CLOUD_API_TOKEN=glsa_...
   GRAFANA_API_KEY=glsa_...
   ```

## Step 2: Configure Prometheus Datasource

### Option A: Grafana Cloud Agent (Recommended)

Grafana Cloud Agent can scrape your Prometheus metrics and forward to Grafana Cloud:

1. Install Grafana Cloud Agent on droplet:

   ```bash
   ssh root@45.55.173.72
   wget https://github.com/grafana/agent/releases/download/v0.38.0/grafana-agent-linux-amd64.zip
   unzip grafana-agent-linux-amd64.zip
   chmod +x grafana-agent-linux-amd64
   mv grafana-agent-linux-amd64 /usr/local/bin/grafana-agent
   ```

2. Create config at `/etc/grafana-agent/config.yaml`:

   ```yaml
   server:
     log_level: info

   metrics:
     wal_directory: /var/lib/grafana-agent/data
     global:
       scrape_interval: 15s
       remote_write:
         - url: https://prometheus-prod-10-prod-us-east-0.grafana.net/api/prom/push
           basic_auth:
             username: YOUR_PROMETHEUS_USERNAME
             password: YOUR_GRAFANA_CLOUD_API_TOKEN

     configs:
       - name: agent
         scrape_configs:
           - job_name: "orchestrator"
             static_configs:
               - targets: ["localhost:8001"]
                 labels:
                   service: "orchestrator"
                   agent_type: "coordinator"

           - job_name: "gateway-mcp"
             static_configs:
               - targets: ["localhost:8000"]
                 labels:
                   service: "gateway-mcp"

           - job_name: "rag-context"
             static_configs:
               - targets: ["localhost:8007"]
                 labels:
                   service: "rag-context"

           - job_name: "state-persistence"
             static_configs:
               - targets: ["localhost:8008"]
                 labels:
                   service: "state-persistence"

           - job_name: "agent-registry"
             static_configs:
               - targets: ["localhost:8009"]
                 labels:
                   service: "agent-registry"
   ```

3. Get Prometheus credentials from Grafana Cloud:

   - Go to https://appsmithery.grafana.net
   - Navigate to **Connections** → **Add new connection** → **Hosted Prometheus**
   - Copy the remote_write URL and credentials
   - Update config.yaml with these values

4. Start agent:
   ```bash
   grafana-agent -config.file=/etc/grafana-agent/config.yaml &
   ```

### Option B: Direct Datasource (Public Endpoint Required)

If you expose Prometheus publicly (not recommended without authentication):

1. Go to https://appsmithery.grafana.net
2. Navigate to **Connections** → **Data sources** → **Add data source**
3. Select **Prometheus**
4. Configure:
   - Name: `Dev-Tools Prometheus`
   - URL: `http://45.55.173.72:9090` (requires public access)
   - Auth: Basic auth with credentials
5. Click **Save & test**

### Option C: Use Local Grafana as Bridge

Keep the local Grafana instance and use it as a datasource bridge:

1. Configure local Grafana to expose metrics via remote_write
2. Configure Grafana Cloud to scrape from local instance
3. Or use Grafana Cloud Agent to scrape local Prometheus and forward to cloud

## Step 3: Import Dashboard

Once datasource is configured, import the dashboard:

**Method 1: Via Script**

```powershell
# After updating GRAFANA_CLOUD_API_TOKEN with new service account token
.\support\scripts\grafana\import-to-cloud.ps1
```

**Method 2: Via UI**

1. Go to https://appsmithery.grafana.net
2. Navigate to **Dashboards** → **New** → **Import**
3. Upload: `config/grafana/dashboards/llm-token-metrics.json`
4. Select datasource: `Dev-Tools Prometheus` or `grafanacloud-prom`
5. Click **Import**

## Step 4: Configure Loki Datasource (Optional)

For log aggregation in Grafana Cloud:

1. Navigate to **Connections** → **Data sources** → **Add data source**
2. Select **Loki**
3. Configure:
   - Name: `Dev-Tools Loki`
   - URL: `http://45.55.173.72:3100` (requires public access or agent)
4. Or use Grafana Cloud Logs with Promtail/Agent forwarding

## Step 5: Test Metrics

1. Trigger test LLM call:

   ```powershell
   ssh root@45.55.173.72 "curl -X POST http://localhost:8001/orchestrate -H 'Content-Type: application/json' -d '{\"task\":\"test metrics\"}'"
   ```

2. Check metrics in Grafana Cloud:

   - Navigate to **Explore**
   - Select Prometheus datasource
   - Query: `up{service="orchestrator"}`
   - Verify data is flowing

3. Open dashboard:
   - Navigate to **Dashboards** → **LLM Token Metrics & Cost Attribution**
   - Verify all panels are loading

## Summary

**Quick Setup Path** (Recommended):

1. Create service account token in Grafana Cloud (Admin/Editor role)
2. Install Grafana Cloud Agent on droplet
3. Configure agent to scrape local Prometheus endpoints
4. Import dashboard via UI
5. Verify metrics flowing

**Alternative Path** (Simpler but less secure):

1. Keep local Grafana instance
2. View dashboards locally at http://45.55.173.72:3000
3. Use MCP integration with local instance
4. Export dashboards manually to Grafana Cloud when needed

## Environment Variables Updated

```bash
# Grafana Cloud (primary)
GRAFANA_CLOUD_URL=https://appsmithery.grafana.net
GRAFANA_CLOUD_API_TOKEN=glsa_... (needs service account token with write permissions)
GRAFANA_API_KEY=glsa_...

# Local Grafana (fallback)
GRAFANA_ROOT_URL=http://45.55.173.72:3000
GRAFANA_LOCAL_API_KEY=eyJrIjoiYk55THZMVEVHcEx4SFQzWjlOU0JpWFdyazQxVjgxTWsiLCJuIjoiTUNQIFNlcnZlciBBY2Nlc3MiLCJpZCI6MX0=

# GitHub OAuth
GRAFANA_GITHUB_CLIENT_ID=22a84e6bd5a10c0207d255773ce91ec6
GRAFANA_GITHUB_CLIENT_SECRET=b7bc7b0c6f39b36e7455c1e6a0e5f31c
```
