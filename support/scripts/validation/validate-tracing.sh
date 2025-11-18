#!/bin/bash
# Comprehensive Validation Script for Dev-Tools Stack
# Validates Langfuse tracing, agent health, MCP gateway, and end-to-end workflows

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

# Function to test endpoint
test_endpoint() {
    local name=$1
    local url=$2
    local data=$3
    local expected_field=$4
    
    echo -e "${YELLOW}Testing: $name${NC}"
    
    response=$(curl -s -w "\n%{http_code}" -X POST "$url" \
        -H 'Content-Type: application/json' \
        -d "$data")
    
    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | sed '$d')
    
    if [ "$http_code" = "200" ]; then
        echo -e "  ${GREEN}✓ HTTP 200 OK${NC}"
        
        # Check if response contains expected field
        if echo "$body" | grep -q "$expected_field"; then
            echo -e "  ${GREEN}✓ Response contains '$expected_field'${NC}"
            PASSED=$((PASSED + 1))
        else
            echo -e "  ${RED}✗ Response missing '$expected_field'${NC}"
            echo "  Response: $body"
            FAILED=$((FAILED + 1))
        fi
    else
        echo -e "  ${RED}✗ HTTP $http_code${NC}"
        echo "  Response: $body"
        FAILED=$((FAILED + 1))
    fi
    echo ""
}

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
        if echo "$body" | grep -q "healthy"; then
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
# PHASE 1: Health Checks
# ============================================================================
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Phase 1: Agent Health Checks${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

test_health "MCP Gateway" 8000
test_health "Orchestrator" 8001
test_health "Feature-Dev" 8002
test_health "Code-Review" 8003
test_health "Infrastructure" 8004
test_health "CI/CD" 8005
test_health "Documentation" 8006
test_health "RAG Context" 8007
test_health "State Persistence" 8008

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
# PHASE 3: Agent Endpoint Tests
# ============================================================================
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Phase 3: Agent Endpoint Tests${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Test 1: Orchestrator (Task Decomposition with Langfuse)
test_endpoint \
    "Orchestrator" \
    "http://localhost:8001/orchestrate" \
    '{"description":"Build a REST API with user authentication and rate limiting","priority":"high"}' \
    "task_id"

# Test 2: Feature-Dev (Code Generation)
test_endpoint \
    "Feature-Dev" \
    "http://localhost:8002/generate" \
    '{"feature":"user login endpoint with JWT tokens","framework":"FastAPI"}' \
    "code"

# Test 3: Code-Review (Static Analysis)
test_endpoint \
    "Code-Review" \
    "http://localhost:8003/review" \
    '{"code":"def authenticate(username, password):\n    if username == \"admin\" and password == \"admin\":\n        return True\n    return False","language":"python"}' \
    "issues"

# Test 4: Infrastructure (IaC Generation)
test_endpoint \
    "Infrastructure" \
    "http://localhost:8004/generate-iac" \
    '{"service":"PostgreSQL database","platform":"docker-compose"}' \
    "iac"

# Test 5: CI/CD Pipeline Generation
test_endpoint \
    "CI/CD" \
    "http://localhost:8005/generate-pipeline" \
    '{"platform":"github-actions","language":"python"}' \
    "pipeline"

# Test 6: Documentation Generation
test_endpoint \
    "Documentation" \
    "http://localhost:8006/generate-docs" \
    '{"code":"def add(a, b):\n    return a + b","format":"markdown"}' \
    "documentation"

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
    echo "1. Check Langfuse Dashboard: https://us.cloud.langfuse.com"
    echo "   - Filter by: metadata.agent_name = \"orchestrator\""
    echo "   - Look for recent traces with LLM calls"
    echo "   - Verify token counts and costs"
    echo ""
    echo "2. Verify Trace Contents:"
    echo "   - Session ID: Should match task_id from response"
    echo "   - User ID: Should be agent name (e.g., 'orchestrator')"
    echo "   - LLM calls: Should show prompts, completions, token counts"
    echo "   - Metadata: Should include model name, temperature, etc."
    echo ""
    echo "3. Check Docker Logs:"
    echo "   docker-compose -f /opt/Dev-Tools/deploy/docker-compose.yml logs -f orchestrator"
    echo ""
    exit 0
else
    echo -e "${RED}❌ Some tests failed. Check logs:${NC}"
    echo "docker-compose -f /opt/Dev-Tools/deploy/docker-compose.yml logs --tail=50"
    echo ""
    exit 1
fi
