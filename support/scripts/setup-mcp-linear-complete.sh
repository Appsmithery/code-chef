#!/bin/bash
# Complete MCP + Linear Setup Script

echo "=== MCP & Linear Integration Setup ==="
cd /opt/Dev-Tools

echo -e "\n1. Checking current .env file..."
grep -E "(LINEAR_API_KEY|MCP)" config/env/.env || echo "Not found"

echo -e "\n2. Adding LINEAR_API_KEY if missing..."
if ! grep -q "LINEAR_API_KEY=" config/env/.env; then
    echo "LINEAR_API_KEY=lin_oauth_8f8990917b7e520efcd51f8ebe84055a251f53f8738bb526c8f2fac8ff0a1571" >> config/env/.env
    echo "Added LINEAR_API_KEY"
else
    echo "LINEAR_API_KEY already exists"
fi

echo -e "\n3. Checking Docker MCP plugin..."
if docker mcp --version 2>/dev/null; then
    echo "Docker MCP already installed"
else
    echo "Docker MCP not found - installing..."
    # Docker Desktop should have MCP built-in
    systemctl --user restart docker-desktop
    sleep 15
    docker mcp --version || echo "MCP plugin not available in this Docker version"
fi

echo -e "\n4. Listing MCP servers..."
docker mcp list 2>/dev/null || echo "No MCP servers or command not available"

echo -e "\n5. Rebuilding orchestrator with new environment..."
docker compose -f deploy/docker-compose.yml stop orchestrator
docker compose -f deploy/docker-compose.yml rm -f orchestrator
docker compose -f deploy/docker-compose.yml up -d orchestrator

echo -e "\n6. Waiting for orchestrator to start..."
sleep 10

echo -e "\n7. Checking health..."
curl -s http://localhost:8001/health | jq '.' || echo "Health check failed"

echo -e "\n=== Setup Complete ==="
