#!/bin/bash
set -e

# Fix Docker socket path
export DOCKER_HOST=unix:///var/run/docker.sock

echo "[REBUILD] Building all 6 agents with --no-cache..."

cd /opt/code-chef

# Build each agent individually using docker build --no-cache
agents=("orchestrator" "feature-dev" "code-review" "infrastructure" "cicd" "documentation")

for agent in "${agents[@]}"; do
    echo "Building $agent..."
    docker build --no-cache \
        -f agent_$agent/Dockerfile \
        -t registry.digitalocean.com/the-shop-infra/$agent:local \
        .
    echo "✓ $agent built successfully"
done

echo "[REBUILD] All agents rebuilt! Restarting services..."
cd deploy
docker compose down
docker compose up -d

echo "[REBUILD] Waiting for services to start..."
sleep 15

echo "[REBUILD] Service status:"
docker compose ps

echo "[REBUILD] Health checks:"
for port in 8000 8001 8002 8003 8004 8005 8006; do
    echo -n "Port $port: "
    curl -s http://localhost:$port/health | grep -q status && echo "✓ Healthy" || echo "✗ Failed"
done
