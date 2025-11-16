# Configuring Gradient AI Agents - UI Guide

## Current Agent Status

| Agent                 | Status     | URL                                                |
| --------------------- | ---------- | -------------------------------------------------- |
| DevTools Orchestrator | ✅ Running | https://zqavbvjov22wijsmbqtkqy4r.agents.do-ai.run  |
| Feature Development   | ✅ Running | https://mdu2tzvveslhs6spm36znwul.agents.do-ai.run  |
| Code Review           | ✅ Running | https://miml4tgrdvjufzudn5udh2sp.agents.do-ai.run  |
| Infrastructure        | ❌ Offline | https://r2eqzfrjao62mdzdbtolmq3sa.agents.do-ai.run |
| CI/CD                 | ✅ Running | https://dxoc7qrjjgbvj7ybct7nogbp.agents.do-ai.run  |
| Documentation         | ❌ Offline | https://tzyvehgqf3pgl4z46rrzbbs.agents.do-ai.run   |

## Step-by-Step: Add Environment Variables to Each Agent

### 1. Navigate to Agent Platform

- Go to: https://cloud.digitalocean.com/ai
- Click on **"the shop"** workspace
- Click the **"Agents"** tab

### 2. For EACH Agent, Add Environment Variables

Click on the agent name (e.g., "DevTools Orchestrator"), then:

#### A. Add MCP Gateway URL

1. Scroll to **"Resources"** section
2. Look for **"Environment Variables"** or **"Settings"**
3. Click **"Edit"** or **"Add Environment Variable"**
4. Add:
   ```
   Name:  MCP_GATEWAY_URL
   Value: http://45.55.173.72:8000
   ```

#### B. Add Linear API Key

5. Add another environment variable:
   ```
   Name:  LINEAR_API_KEY
   Value: lin_oauth_8f8990917b7e520efcd51f8ebe84055a251f53f8738bb526c8f2fac8ff0a1571
   ```

#### C. Add Langfuse Tracing Keys

6. Add these for observability:
   ```
   Name:  LANGFUSE_SECRET_KEY
   Value: sk-lf-51d46621-1aff-4867-be1f-66450c44ef8c
   ```
   ```
   Name:  LANGFUSE_PUBLIC_KEY
   Value: pk-lf-7029904c-4cc7-44c4-a470-aa73f1e6a745
   ```
   ```
   Name:  LANGFUSE_HOST
   Value: https://us.cloud.langfuse.com
   ```

#### D. Save and Deploy

7. Click **"Save"** or **"Update Agent"**
8. The agent will restart with new environment variables

### 3. Repeat for All Agents

Complete steps 2A-2D for each of these agents:

- [ ] DevTools Orchestrator
- [ ] Feature Development Agent
- [ ] Code Review Agent
- [ ] Infrastructure Agent (currently offline - may need to restart)
- [ ] CI/CD Agent
- [ ] Documentation Agent (currently offline - may need to restart)
- [ ] Kubernetes Genius

### 4. Restart Offline Agents

For **Infrastructure** and **Documentation** agents (currently offline):

1. Click on the agent name
2. Look for **"Actions"** dropdown in top-right
3. Click **"Restart"** or **"Redeploy"**
4. Wait 30-60 seconds
5. Verify agent shows "Running" status

### 5. Verify Configuration

After updating all agents, run this PowerShell command to verify:

```powershell
$agents = @(
    @{Name="Orchestrator"; URL="https://zqavbvjov22wijsmbqtkqy4r.agents.do-ai.run"},
    @{Name="Feature Dev"; URL="https://mdu2tzvveslhs6spm36znwul.agents.do-ai.run"},
    @{Name="Code Review"; URL="https://miml4tgrdvjufzudn5udh2sp.agents.do-ai.run"},
    @{Name="Infrastructure"; URL="https://r2eqzfrjao62mdzdbtolmq3sa.agents.do-ai.run"},
    @{Name="CI/CD"; URL="https://dxoc7qrjjgbvj7ybct7nogbp.agents.do-ai.run"},
    @{Name="Documentation"; URL="https://tzyvehgqf3pgl4z46rrzbbs.agents.do-ai.run"},
    @{Name="Kubernetes"; URL="https://uwu4yx7stpwcahkg56m4zn7k.agents.do-ai.run"}
)

foreach ($agent in $agents) {
    try {
        $health = Invoke-RestMethod -Uri "$($agent.URL)/health" -TimeoutSec 10
        Write-Host "$($agent.Name): ✅ $($health.status)" -ForegroundColor Green
        if ($health.mcp.gateway_url) {
            Write-Host "  MCP: $($health.mcp.gateway_url)" -ForegroundColor Gray
        }
        if ($health.integrations.linear) {
            Write-Host "  Linear: $($health.integrations.linear)" -ForegroundColor Gray
        }
    } catch {
        Write-Host "$($agent.Name): ❌ Offline" -ForegroundColor Red
    }
}
```

## Expected Results

After configuration, each agent's health check should show:

```json
{
  "status": "ok",
  "agent": "agent-name",
  "mcp": {
    "gateway_url": "http://45.55.173.72:8000",
    "gateway_connected": true,
    "available_tools": 150
  },
  "integrations": {
    "linear": true,
    "langfuse": true
  }
}
```

## Troubleshooting

### Agent Not Showing Environment Variables Option

If you don't see an "Environment Variables" section:

1. Check if the agent was created with a custom Dockerfile/code
2. You may need to redeploy the agent with the environment variables set during creation
3. Contact DigitalOcean support if the UI doesn't expose env var configuration

### Agent Keeps Restarting

If an agent keeps restarting after adding env vars:

1. Check the agent logs in DigitalOcean dashboard
2. Verify the MCP gateway is accessible: `curl http://45.55.173.72:8000/health`
3. Remove the env vars and add them one at a time to isolate the issue

### Gateway Connection Errors

If agents can't connect to MCP gateway:

1. Verify gateway is running: `docker ps | grep gateway-mcp` (on droplet)
2. Check firewall allows port 8000: `ufw status | grep 8000` (on droplet)
3. Test from outside: `curl http://45.55.173.72:8000/health`

## Alternative: Deploy with Environment Variables

If the UI doesn't allow editing env vars on existing agents, you may need to:

1. **Export agent configuration** (if possible in UI)
2. **Delete the agent**
3. **Recreate with environment variables** set during creation
4. Use the agent code from `agents/*/main.py` in this repo

Or use the DigitalOcean API to update agent environment variables programmatically.
