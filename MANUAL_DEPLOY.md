# Manual Deployment Instructions

**Issue:** SSH connection to droplet is timing out (port 22 blocked or droplet not responding)

## 🔧 Troubleshooting Steps

### Option 1: Use DigitalOcean Console

1. **Access Droplet Console**

   - Go to: https://cloud.digitalocean.com/droplets
   - Find droplet: `mcp-gateway` (45.55.173.72)
   - Click "Console" button (top right)

2. **Login as root** (or your configured user)

3. **Run Deployment Commands**

```bash
cd /opt/Dev-Tools
git pull origin main
chmod +x scripts/deploy-and-trace.sh
./scripts/deploy-and-trace.sh
```

### Option 2: Check SSH Access

If you have direct access to the droplet through another terminal:

```bash
# Check if SSH is running
sudo systemctl status ssh

# Check firewall rules
sudo ufw status

# Ensure port 22 is allowed
sudo ufw allow 22/tcp

# Check if droplet is online
ping 45.55.173.72
```

### Option 3: Alternative SSH Command

Try connecting with verbose output to see where it's failing:

```powershell
ssh -vvv root@45.55.173.72
```

Or try with the user from your config:

```powershell
ssh -vvv -p 22 root@45.55.173.72
```

## 📦 What Needs to Be Deployed

The following files have been pushed to GitHub and need to be deployed:

1. **frontend/agents.html** - New agent cards page
2. **frontend/production-landing.html** - Updated landing page with compact tiles
3. **scripts/deploy-and-trace.sh** - Automated deployment script

## 🚀 Manual Deployment (If SSH Works)

Once you can connect, run these commands:

```bash
# Navigate to project
cd /opt/Dev-Tools

# Pull latest code
git pull origin main

# Restart gateway (serves frontend)
cd compose
docker-compose restart gateway-mcp

# Wait for startup
sleep 10

# Test agent health
for port in 8001 8002 8003 8004 8005 8006; do
  echo "Testing port $port..."
  curl -s http://localhost:$port/health | jq -r '.service + " - " + .status'
done

# Trigger orchestration (creates Langfuse trace)
curl -X POST http://localhost:8001/orchestrate \
  -H 'Content-Type: application/json' \
  -d '{"description":"Build REST API with authentication","priority":"high"}' | jq .
```

## 🌐 Verify Deployment

### Frontend URLs (test from browser):

- http://45.55.173.72/production-landing.html
- http://45.55.173.72/agents.html
- http://45.55.173.72/servers.html

### Langfuse Dashboard:

- https://us.cloud.langfuse.com
- Filter: `metadata.agent_name = "orchestrator"`
- Look for traces with task_id, thread_id, model metadata

### Agent Health (test from browser or curl):

- http://45.55.173.72:8001/health (Orchestrator)
- http://45.55.173.72:8002/health (Feature-Dev)
- http://45.55.173.72:8003/health (Code-Review)

## 🔍 Common Issues

**"Connection timed out"**

- Droplet may be offline - check DigitalOcean dashboard
- Firewall blocking SSH - use DigitalOcean console instead
- Network issue - try from different network

**"Permission denied"**

- SSH key not configured correctly
- Try: `ssh -i ~/.ssh/your_key root@45.55.173.72`

**"git pull fails"**

- Check git credentials: `git config --list`
- Try: `git fetch origin && git reset --hard origin/main`

## 📞 Need Help?

If you're still stuck:

1. Check droplet status in DigitalOcean dashboard
2. Use the web console to access droplet directly
3. Verify SSH key is added to droplet
4. Check if firewall rules allow SSH from your IP

## ✅ Once Deployed

After successful deployment, you should see:

- ✅ New agent cards page at /agents.html
- ✅ Updated landing page with compact tiles
- ✅ Langfuse traces appearing from orchestrator
- ✅ All 6 agents reporting healthy status
- ✅ Metadata tracking (agent_name, task_id, thread_id, model)
