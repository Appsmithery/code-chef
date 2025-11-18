#!/usr/bin/env bash
set -euo pipefail

DROPLET_IP=${1:-45.55.173.72}

echo "[HEALTH] Checking droplet service health (${DROPLET_IP})..."

services=(
  "8000:gateway-mcp"
  "8001:orchestrator"
  "8002:feature-dev"
  "8003:code-review"
  "8004:infrastructure"
  "8005:cicd"
  "8006:documentation"
  "8007:rag-context"
  "8008:state-persistence"
)

for svc in "${services[@]}"; do
  port="${svc%%:*}"
  name="${svc##*:}"
  status=$(curl -s -o /dev/null -w "%{http_code}" "http://${DROPLET_IP}:${port}/health" || echo "000")
  if [[ "$status" == "200" ]]; then
    echo "  [OK] ${name} (port ${port})"
  else
    echo "  [ERROR] ${name} (port ${port}) - HTTP ${status}"
  fi
done
