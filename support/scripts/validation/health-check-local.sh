#!/usr/bin/env bash
set -euo pipefail

echo "[HEALTH] Checking local service health..."

services=(
  "8000:gateway-mcp"
  "8001:orchestrator"
  "8007:rag-context"
  "8008:state-persistence"
  "8009:agent-registry"
  "8010:langgraph"
)

for svc in "${services[@]}"; do
  port="${svc%%:*}"
  name="${svc##*:}"
  status=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:${port}/health" || echo "000")
  if [[ "$status" == "200" ]]; then
    echo "  [OK] ${name} (port ${port})"
  else
    echo "  [ERROR] ${name} (port ${port}) - HTTP ${status}"
  fi
done
