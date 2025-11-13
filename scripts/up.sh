#!/bin/bash
# Bring up the Dev-Tools stack

set -e

echo "Starting Dev-Tools services..."

cd compose
docker-compose up -d

echo "Waiting for services to be healthy..."
sleep 10

echo "Services running:"
docker-compose ps

echo ""
echo "Dev-Tools is ready!"
echo "MCP Gateway: http://localhost:8000"
echo "Orchestrator: http://localhost:8001"