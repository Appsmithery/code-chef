# Manual Deployment Guide - Dev-Tools

## Current Issue

SSH commands are hanging when trying to run Docker build/compose commands. This typically indicates:

- Docker daemon is busy with a running build
- Droplet is under heavy load
- Network/SSH connection instability

## Manual Deployment Steps

### Option 1: Via DigitalOcean Console

1. **Access Droplet Console**

   - Go to: https://cloud.digitalocean.com/droplets
   - Click on droplet `mcp-gateway` (45.55.173.72)
   - Click **"Access"** → **"Launch Droplet Console"**

2. **Check Docker Status**

   ```bash
   docker ps
   docker compose -f /opt/Dev-Tools/compose/docker-compose.yml ps
   ```

3. **Stop Any Running Builds**

   ```bash
   cd /opt/Dev-Tools/compose
   docker compose down
   pkill -f "docker compose build"
   ```

4. **Build Images (One at a Time)**

   ```bash
   cd /opt/Dev-Tools/compose

   # Build infrastructure first
   docker compose build gateway-mcp
   docker compose build rag-context
   docker compose build state-persistence

   # Then build agents
   docker compose build orchestrator
   docker compose build feature-dev
   docker compose build code-review
   docker compose build infrastructure
   docker compose build cicd
   docker compose build documentation
   ```

5. **Start Services**

   ```bash
   cd /opt/Dev-Tools/compose
   docker compose up -d
   ```

6. **Verify Health**
   ```bash
   curl http://localhost:8000/health  # MCP Gateway
   curl http://localhost:8001/health  # Orchestrator
   curl http://localhost:8002/health  # Feature Dev
   curl http://localhost:8003/health  # Code Review
   curl http://localhost:8004/health  # Infrastructure
   curl http://localhost:8005/health  # CI/CD
   curl http://localhost:8006/health  # Documentation
   ```

### Option 2: Via PowerShell (After SSH Fixes)

```powershell
# Test basic connectivity
Test-NetConnection -ComputerName 45.55.173.72 -Port 22

# Check what's running
Invoke-RestMethod http://45.55.173.72:8000/health
Invoke-RestMethod http://45.55.173.72:8001/health

# If services are already running, skip build and just verify
$ports = 8000..8008
foreach ($port in $ports) {
    try {
        $response = Invoke-RestMethod "http://45.55.173.72:$port/health" -TimeoutSec 5
        Write-Host "Port $port : ✅ $($response.status)" -ForegroundColor Green
    } catch {
        Write-Host "Port $port : ❌ Offline" -ForegroundColor Red
    }
}
```

### Option 3: Check if Services Are Already Running

It's possible the earlier builds succeeded and services are already running. Let me check:

```powershell
# Test each endpoint
$endpoints = @(
    @{Name="MCP Gateway"; URL="http://45.55.173.72:8000/health"},
    @{Name="Orchestrator"; URL="http://45.55.173.72:8001/health"},
    @{Name="Feature Dev"; URL="http://45.55.173.72:8002/health"},
    @{Name="Code Review"; URL="http://45.55.173.72:8003/health"},
    @{Name="Infrastructure"; URL="http://45.55.173.72:8004/health"},
    @{Name="CI/CD"; URL="http://45.55.173.72:8005/health"},
    @{Name="Documentation"; URL="http://45.55.173.72:8006/health"}
)

foreach ($ep in $endpoints) {
    try {
        $r = Invoke-RestMethod $ep.URL -TimeoutSec 5
        Write-Host "✅ $($ep.Name): $($r.status)" -ForegroundColor Green
    } catch {
        Write-Host "❌ $($ep.Name): Offline" -ForegroundColor Red
    }
}
```

## Troubleshooting SSH Hangs

If SSH commands continue to hang:

1. **Check droplet load via API:**

   ```powershell
   $headers = @{"Authorization" = "Bearer dop_v1_21565d5f63b515138cae71c2815df3ca6dd95cec7587dca513fab11c7e5589ee"}
   Invoke-RestMethod -Uri "https://api.digitalocean.com/v2/droplets/529438997" -Headers $headers | Select-Object -ExpandProperty droplet | Select-Object name, status, memory, vcpus
   ```

2. **Reboot droplet if needed:**

   ```powershell
   $headers = @{
       "Authorization" = "Bearer dop_v1_21565d5f63b515138cae71c2815df3ca6dd95cec7587dca513fab11c7e5589ee"
       "Content-Type" = "application/json"
   }
   $body = @{"type" = "reboot"} | ConvertTo-Json
   Invoke-RestMethod -Uri "https://api.digitalocean.com/v2/droplets/529438997/actions" -Method POST -Headers $headers -Body $body
   ```

3. **Wait 2-3 minutes, then check health endpoints again**

## Alternative: Skip Docker Build

If images exist from previous builds:

```bash
cd /opt/Dev-Tools/compose
docker compose up -d  # Start with existing images
```

## Next Steps After Deployment

Once services are confirmed running:

1. **Test Orchestrator:**

   ```powershell
   $task = @{description="List available MCP tools"} | ConvertTo-Json
   Invoke-RestMethod http://45.55.173.72:8001/tasks -Method POST -Body $task -ContentType "application/json"
   ```

2. **Check Langfuse Traces:**

   - https://us.cloud.langfuse.com

3. **Verify Linear Integration:**

   ```powershell
   Invoke-RestMethod http://45.55.173.72:8000/api/linear-issues
   ```

4. **Monitor Prometheus:**
   - http://45.55.173.72:9090
