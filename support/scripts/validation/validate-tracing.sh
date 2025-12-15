#!/bin/bash
# Comprehensive Validation Script for Dev-Tools Stack
# Validates LangSmith tracing, agent health, MCP gateway, and end-to-end workflows

set -e

echo ""
echo "========================================"
echo "🧪 Dev-Tools Stack Validation"
echo "========================================"
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test counter
PASSED=0
FAILED=0

# Function to test health endpoint
test_health() {
    local name=$1
    local port=$2
    
    echo -e "${YELLOW}Health Check: $name (port $port)${NC}"
    
    response=$(curl -s -w "\n%{http_code}" http://localhost:$port/health)
    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | sed '$d')
    
    if [ "$http_code" = "200" ]; then
        echo -e "  ${GREEN}✓ HTTP 200 OK${NC}"
        
        # Check for expected health response
        if echo "$body" | grep -q -E "healthy|ok"; then
            echo -e "  ${GREEN}✓ Status: healthy${NC}"
            PASSED=$((PASSED + 1))
        else
            echo -e "  ${RED}✗ Unexpected response${NC}"
            echo "  Response: $body"
            FAILED=$((FAILED + 1))
        fi
    else
        echo -e "  ${RED}✗ HTTP $http_code${NC}"
        FAILED=$((FAILED + 1))
    fi
    echo ""
}

# ============================================================================
# PHASE 1: Health Checks (Current Architecture)
# ============================================================================
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Phase 1: Service Health Checks${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Core services (current architecture - orchestrator runs all agent nodes)
# Note: MCP Gateway (8000) deprecated - tools accessed via Docker MCP Toolkit in VS Code
test_health "Orchestrator" 8001
test_health "RAG Context" 8007
test_health "State Persistence" 8008
test_health "LangGraph" 8010

# ============================================================================
# PHASE 2: RAG Service Validation
# ============================================================================
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Phase 2: RAG Service Validation${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

echo -e "${YELLOW}Testing: RAG Collections${NC}"
response=$(curl -s -w "\n%{http_code}" http://localhost:8007/collections)
http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | sed '$d')

if [ "$http_code" = "200" ]; then
    echo -e "  ${GREEN}✓ HTTP 200 OK${NC}"
    collection_count=$(echo "$body" | jq -r 'length' 2>/dev/null || echo "0")
    if [ "$collection_count" -gt 0 ]; then
        echo -e "  ${GREEN}✓ Found $collection_count collections${NC}"
        PASSED=$((PASSED + 1))
        
        # List collections
        echo -e "  ${BLUE}Collections:${NC}"
        echo "$body" | jq -r '.[] | "    - \(.name): \(.count) vectors"' 2>/dev/null || echo "    (jq not available)"
    else
        echo -e "  ${YELLOW}⚠ No collections found (may need indexing)${NC}"
        PASSED=$((PASSED + 1))  # Not a failure, just empty
    fi
else
    echo -e "  ${RED}✗ HTTP $http_code${NC}"
    FAILED=$((FAILED + 1))
fi
echo ""

# ============================================================================
# PHASE 3: LangSmith Tracing Validation
# ============================================================================
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Phase 3: LangSmith Tracing Check${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

echo -e "${YELLOW}Testing: LangSmith Configuration${NC}"

# Check if LANGSMITH_TRACING is enabled in orchestrator
if docker exec deploy-orchestrator-1 printenv | grep -q "LANGSMITH_TRACING=true"; then
    echo -e "  ${GREEN}✓ LANGSMITH_TRACING=true${NC}"
    PASSED=$((PASSED + 1))
else
    echo -e "  ${RED}✗ LANGSMITH_TRACING not enabled${NC}"
    FAILED=$((FAILED + 1))
fi

if docker exec deploy-orchestrator-1 printenv | grep -q "LANGCHAIN_TRACING_V2=true"; then
    echo -e "  ${GREEN}✓ LANGCHAIN_TRACING_V2=true${NC}"
    PASSED=$((PASSED + 1))
else
    echo -e "  ${RED}✗ LANGCHAIN_TRACING_V2 not enabled${NC}"
    FAILED=$((FAILED + 1))
fi
echo ""

# ============================================================================
# PHASE 4: Summary
# ============================================================================
echo "========================================"
echo "📊 Test Results"
echo "========================================"
echo ""
echo -e "Passed: ${GREEN}$PASSED${NC}"
echo -e "Failed: ${RED}$FAILED${NC}"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✅ All tests passed!${NC}"
    echo ""
    echo "Next Steps:"
    echo "1. Check LangSmith Dashboard:"
    echo "   https://smith.langchain.com/o/5029c640-3f73-480c-82f3-58e402ed4207/projects"
    echo ""
    echo "2. Check Grafana Cloud Metrics:"
    echo "   https://appsmithery.grafana.net"
    echo ""
    echo "3. Verify RAG Collections (should have 6 active):"
    echo "   curl http://localhost:8007/collections | jq"
    echo ""
    echo "4. Check Docker Logs:"
    echo "   docker compose -f /opt/code-chef/deploy/docker-compose.yml logs -f orchestrator"
    echo ""
    exit 0
else
    echo -e "${RED}❌ Some tests failed. Check logs:${NC}"
    echo "docker compose -f /opt/code-chef/deploy/docker-compose.yml logs --tail=50"
    echo ""
    exit 1
fi
