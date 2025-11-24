# Grafana Cloud Agent - Authentication Fix

## Problem

Grafana Agent is getting `401 Unauthorized` when trying to push metrics to Grafana Cloud Prometheus:

```
server returned HTTP status 401 Unauthorized: authentication error: invalid authentication credentials
```

## Root Cause

The `basic_auth` credentials in the agent config are incorrect. The service account token (`glsa_...`) is for Grafana API, not for Prometheus remote_write.

Prometheus remote_write requires:

- **Username**: Instance ID (not Org ID)
- **Password**: Generated API token with `metrics:write` scope

## Solution Steps

### Step 1: Get Prometheus Remote Write Credentials

1. **Open Grafana Cloud Console**:

   - Go to https://grafana.com/orgs/appsmithery
   - Navigate to **Home** → **Connections** → **Add new connection**
   - Search for "Prometheus" and select **Hosted Prometheus metrics**

2. **Find Remote Write Details**:

   - URL: `https://prometheus-prod-56-prod-us-east-2.grafana.net/api/prom/push`
   - **Instance ID** (username): Should be a number like `123456` or `1376474` (your stack ID)
   - **Generate API Token** with `metrics:write` scope

3. **Alternative - Check Existing Token**:
   - Go to https://grafana.com/orgs/appsmithery/access-policies
   - Look for existing token with `metrics:write` permission
   - Or create new token: **Create access policy** → Name: "Prometheus Write" → Scopes: `metrics:write`, `metrics:read`

### Step 2: Update Agent Config

**File**: `/etc/grafana-agent/config.yaml` on droplet

**Current (WRONG)**:

```yaml
remote_write:
  - url: https://prometheus-prod-56-prod-us-east-2.grafana.net/api/prom/push
    basic_auth:
      username: "1534681" # ❌ This is Org ID, not Instance ID
      password: "glc_eyJv..." # ❌ This is read-only migration token
```

**Correct**:

```yaml
remote_write:
  - url: https://prometheus-prod-56-prod-us-east-2.grafana.net/api/prom/push
    basic_auth:
      username: "1376474" # ✅ Stack ID (Instance ID)
      password: "glc_CORRECT_TOKEN_HERE" # ✅ Token with metrics:write scope
```

**OR use Bearer token** (if provided by Grafana Cloud):

```yaml
remote_write:
  - url: https://prometheus-prod-56-prod-us-east-2.grafana.net/api/prom/push
    headers:
      Authorization: "Bearer glc_TOKEN_HERE"
```

### Step 3: Quick Fix Commands

**Option A: Manual Fix** (if you have credentials):

```powershell
# SSH to droplet
ssh root@45.55.173.72

# Edit config (replace INSTANCE_ID and TOKEN)
nano /etc/grafana-agent/config.yaml

# Find remote_write section, update:
#   username: "INSTANCE_ID"  # From Grafana Cloud console
#   password: "TOKEN_HERE"    # From generated API token

# Restart agent
systemctl restart grafana-agent

# Verify logs (should see no more 401 errors)
journalctl -u grafana-agent -f
```

**Option B: Use Grafana Cloud Agent Generator** (Recommended):

1. Go to https://grafana.com/orgs/appsmithery
2. Navigate to **Connections** → **Install Grafana Agent**
3. Select **Linux** → Copy generated config snippet
4. Config will have correct credentials pre-filled
5. Replace `/etc/grafana-agent/config.yaml` with generated config
6. Add your scrape_configs from `config/grafana/agent-config.yaml`

### Step 4: Verification

After fixing credentials:

```bash
# Check logs (no more 401 errors)
ssh root@45.55.173.72 "journalctl -u grafana-agent --since '1 minute ago' | grep -i error"

# Should see success messages like:
# "successfully sent batch"
# "remote_write samples sent"
```

Then verify metrics in Grafana Cloud:

```powershell
# Run verification script
$env:GRAFANA_CLOUD_API_TOKEN="glsa_gYG6QyRKAKYInZSNQ8inn5SMdFh47fmV_375df6c0"
.\support\scripts\grafana\verify-cloud-metrics.ps1
```

Or manually in Grafana Cloud:

1. Go to https://appsmithery.grafana.net/explore
2. Select datasource: `grafanacloud-appsmithery-prom`
3. Query: `up{cluster="dev-tools"}`
4. Should see services with value `1` (UP)

---

## Quick Reference

**Grafana Cloud Console**: https://grafana.com/orgs/appsmithery  
**Grafana Cloud Dashboard**: https://appsmithery.grafana.net  
**Stack ID**: 1376474-hm  
**Org ID**: 1534681  
**Prometheus URL**: https://prometheus-prod-56-prod-us-east-2.grafana.net/api/prom/push

**Agent Config Path**: `/etc/grafana-agent/config.yaml`  
**Agent Service**: `systemctl status grafana-agent`  
**Agent Logs**: `journalctl -u grafana-agent -f`

---

## Next Steps

Once authentication is fixed:

1. ✅ Verify metrics flowing (should see `up{cluster="dev-tools"}=1`)
2. ✅ Open dashboard: https://appsmithery.grafana.net/d/ed621f5b-cc44-43e6-be73-ab9922cb36fc
3. ✅ Trigger test LLM call to populate token/cost metrics
4. ✅ Set up alerting rules in Grafana Cloud
5. ✅ Configure Loki datasource for logs
