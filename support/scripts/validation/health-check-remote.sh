#!/usr/bin/env bash
set -euo pipefail

# Domain and IP configuration
DROPLET_HOST="codechef.appsmithery.co"
DROPLET_IP="45.55.173.72"  # For SSH fallback

echo "[HEALTH] Checking droplet service health at ${DROPLET_HOST}..."
echo ""

# Services accessible via Caddy reverse proxy (HTTPS)
echo "[HTTPS via Caddy]"
https_services=(
  "/api/health:orchestrator"
  "/rag/health:rag-context"
  "/state/health:state-persistence"
  "/langgraph/health:langgraph"
)

for svc in "${https_services[@]}"; do
  path="${svc%%:*}"
  name="${svc##*:}"
  status=$(curl -s -o /dev/null -w "%{http_code}" "https://${DROPLET_HOST}${path}" || echo "000")
  if [[ "$status" == "200" ]]; then
    echo "  [OK] ${name} (${path})"
  else
    echo "  [ERROR] ${name} - HTTP ${status}"
  fi
done

echo ""
echo "[Direct Port Access via SSH]"
direct_services=(
  "8001:orchestrator"
  "8007:rag-context"
  "8008:state-persistence"
  "8010:langgraph"
)

for svc in "${direct_services[@]}"; do
  port="${svc%%:*}"
  name="${svc##*:}"
  result=$(ssh "root@${DROPLET_IP}" "curl -s http://localhost:${port}/health 2>/dev/null" || echo "error")
  if echo "$result" | grep -q '"status"'; then
    echo "  [OK] ${name} (port ${port})"
  else
    echo "  [ERROR] ${name} (port ${port}) - Unhealthy"
  fi
done
