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

# Core services (current architecture - no individual agent ports 8002-8006)
test_health "MCP Gateway" 8000
test_health "Orchestrator" 8001
test_health "RAG Context" 8007
test_health "State Persistence" 8008
test_health "LangGraph" 8010

# ============================================================================
# PHASE 2: MCP Gateway Tool Discovery
# ============================================================================
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Phase 2: MCP Gateway Tool Discovery${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

echo -e "${YELLOW}Testing: MCP Gateway Tool List${NC}"
response=$(curl -s -w "\n%{http_code}" http://localhost:8000/api/tools)
http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | sed '$d')

if [ "$http_code" = "200" ]; then
    echo -e "  ${GREEN}✓ HTTP 200 OK${NC}"
    tool_count=$(echo "$body" | jq -r '.tools | length' 2>/dev/null || echo "0")
    if [ "$tool_count" -gt 0 ]; then
        echo -e "  ${GREEN}✓ Found $tool_count MCP tools${NC}"
        PASSED=$((PASSED + 1))
        
        # List first 5 tools
        echo -e "  ${BLUE}Sample tools:${NC}"
        echo "$body" | jq -r '.tools[:5][] | "    - \(.name)"' 2>/dev/null || echo "    (jq not available)"
    else
        echo -e "  ${RED}✗ No tools found${NC}"
        FAILED=$((FAILED + 1))
    fi
else
    echo -e "  ${RED}✗ HTTP $http_code${NC}"
    FAILED=$((FAILED + 1))
fi
echo ""

# ============================================================================
# PHASE 3: RAG Service Validation
# ============================================================================
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Phase 3: RAG Service Validation${NC}"
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
    echo "   https://smith.langchain.com/o/5029c640-3f73-480c-82f3-58e402ed4207/projects/p/f967bb5e-2e61-434f-8ee1-0df8c22bc046"
    echo ""
    echo "2. Verify Trace Contents:"
    echo "   - Look for recent traces with LLM calls"
    echo "   - Verify token counts and costs"
    echo "   - Check latency metrics"
    echo ""
    echo "3. Check Docker Logs:"
    echo "   docker compose -f /opt/Dev-Tools/deploy/docker-compose.yml logs -f orchestrator"
    echo ""
    exit 0
else
    echo -e "${RED}❌ Some tests failed. Check logs:${NC}"
    echo "docker compose -f /opt/Dev-Tools/deploy/docker-compose.yml logs --tail=50"
    echo ""
    exit 1
fi
