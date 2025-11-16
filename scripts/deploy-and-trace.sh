#!/bin/bash
# Deploy Frontend & Run Agent Traces
# Run this on the DigitalOcean droplet (45.55.173.72)

set -e

echo "========================================="
echo "🚀 Deploying Frontend & Testing Traces"
echo "========================================="

# Pull latest changes
echo ""
echo "📦 Pulling latest code..."
cd /opt/Dev-Tools
git pull origin main

# Restart gateway (serves frontend)
echo ""
echo "🔄 Restarting gateway..."
docker-compose -f compose/docker-compose.yml restart gateway-mcp

# Wait for gateway to start
echo ""
echo "⏳ Waiting for gateway to start..."
sleep 5

# Check agent health
echo ""
echo "🏥 Checking agent health..."
for port in 8001 8002 8003 8004 8005 8006; do
  echo "  Checking port $port..."
  curl -s http://localhost:$port/health | jq -r '.service + " - " + .status' || echo "  ❌ Failed"
done

# Test orchestration (triggers Langfuse trace)
echo ""
echo "🧪 Testing orchestration (triggers Langfuse trace)..."
curl -X POST http://localhost:8001/orchestrate \
  -H 'Content-Type: application/json' \
  -d '{
    "description": "Build REST API with authentication and user management",
    "priority": "high"
  }' | jq .

echo ""
echo "========================================="
echo "✅ Deployment Complete!"
echo "========================================="
echo ""
echo "📊 Check Langfuse Dashboard:"
echo "   https://us.cloud.langfuse.com"
echo ""
echo "🔍 Look for traces with metadata:"
echo "   - agent_name: orchestrator"
echo "   - task_id: <uuid>"
echo "   - model: llama-3.1-70b-instruct"
echo "   - Execution timing and token usage"
echo ""
echo "🌐 Frontend URLs:"
echo "   http://45.55.173.72/production-landing.html"
echo "   http://45.55.173.72/agents.html"
echo "   http://45.55.173.72/servers.html"
echo ""
echo "========================================="
