#!/bin/bash
# Nuclear Option: Complete Droplet Cleanup
# WARNING: This stops all services, removes containers, images, and volumes
# Use this when you need a completely fresh start

set -e  # Exit on error

DROPLET_HOST="root@45.55.173.72"
DEPLOY_PATH="/opt/code-chef"

echo "🚨 NUCLEAR CLEANUP: Complete droplet scrub"
echo "Target: ${DROPLET_HOST}:${DEPLOY_PATH}"
echo ""
read -p "Are you SURE? This will delete ALL containers, volumes, and images. Type 'NUCLEAR' to proceed: " confirm

if [ "$confirm" != "NUCLEAR" ]; then
    echo "❌ Aborted. (You typed: '$confirm')"
    exit 1
fi

echo ""
echo "⏳ Step 1/7: Stopping all Docker Compose services..."
ssh ${DROPLET_HOST} "cd ${DEPLOY_PATH}/deploy && docker compose down --remove-orphans --volumes || true"

echo ""
echo "⏳ Step 2/7: Removing ALL containers (including non-compose)..."
ssh ${DROPLET_HOST} "docker container stop \$(docker container ls -aq) 2>/dev/null || true"
ssh ${DROPLET_HOST} "docker container rm \$(docker container ls -aq) 2>/dev/null || true"

echo ""
echo "⏳ Step 3/7: Removing ALL Docker images..."
ssh ${DROPLET_HOST} "docker image rm -f \$(docker image ls -aq) 2>/dev/null || true"

echo ""
echo "⏳ Step 4/7: Removing ALL Docker volumes..."
ssh ${DROPLET_HOST} "docker volume rm \$(docker volume ls -q) 2>/dev/null || true"

echo ""
echo "⏳ Step 5/7: Removing ALL Docker networks (except defaults)..."
ssh ${DROPLET_HOST} "docker network rm \$(docker network ls -q --filter type=custom) 2>/dev/null || true"

echo ""
echo "⏳ Step 6/7: Pruning Docker build cache..."
ssh ${DROPLET_HOST} "docker builder prune -af"

echo ""
echo "⏳ Step 7/7: Full system prune..."
ssh ${DROPLET_HOST} "docker system prune -af --volumes"

echo ""
echo "✅ Droplet scrubbed clean!"
echo ""
echo "📋 Docker status:"
ssh ${DROPLET_HOST} "df -h /var/lib/docker"
ssh ${DROPLET_HOST} "docker system df"

echo ""
echo "Next steps:"
echo "1. Run: ssh ${DROPLET_HOST} 'cd ${DEPLOY_PATH} && git pull origin main'"
echo "2. Update config/env/.env on droplet (ensure LLM_PROVIDER=openrouter)"
echo "3. Run: ssh ${DROPLET_HOST} 'cd ${DEPLOY_PATH}/deploy && docker compose up -d --build'"
echo "4. Wait 60-90s, then verify: curl https://codechef.appsmithery.co/health"
