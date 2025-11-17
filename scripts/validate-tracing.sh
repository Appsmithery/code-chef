#!/bin/bash
# Validation Script for Langfuse Tracing on Production Droplet
# Run this script on the droplet to validate that tracing is working correctly

set -e

echo ""
echo "========================================"
echo "🧪 Langfuse Tracing Validation"
echo "========================================"
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
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

# Test 1: Orchestrator (Task Decomposition with Langfuse)
echo "Test 1: Orchestrator Task Decomposition"
echo "----------------------------------------"
test_endpoint \
    "Orchestrator" \
    "http://localhost:8001/orchestrate" \
    '{"description":"Build a REST API with user authentication and rate limiting","priority":"high"}' \
    "task_id"

# Test 2: Feature-Dev (Code Generation)
echo "Test 2: Feature-Dev Code Generation"
echo "----------------------------------------"
test_endpoint \
    "Feature-Dev" \
    "http://localhost:8002/generate" \
    '{"feature":"user login endpoint with JWT tokens","framework":"FastAPI"}' \
    "code"

# Test 3: Code-Review (Static Analysis)
echo "Test 3: Code-Review Analysis"
echo "----------------------------------------"
test_endpoint \
    "Code-Review" \
    "http://localhost:8003/review" \
    '{"code":"def authenticate(username, password):\n    if username == \"admin\" and password == \"admin\":\n        return True\n    return False","language":"python"}' \
    "issues"

# Test 4: Infrastructure (IaC Generation)
echo "Test 4: Infrastructure IaC Generation"
echo "----------------------------------------"
test_endpoint \
    "Infrastructure" \
    "http://localhost:8004/generate-iac" \
    '{"service":"PostgreSQL database","platform":"docker-compose"}' \
    "iac"

# Test 5: CI/CD Pipeline Generation
echo "Test 5: CI/CD Pipeline Generation"
echo "----------------------------------------"
test_endpoint \
    "CI/CD" \
    "http://localhost:8005/generate-pipeline" \
    '{"platform":"github-actions","language":"python"}' \
    "pipeline"

# Test 6: Documentation Generation
echo "Test 6: Documentation Generation"
echo "----------------------------------------"
test_endpoint \
    "Documentation" \
    "http://localhost:8006/generate-docs" \
    '{"code":"def add(a, b):\n    return a + b","format":"markdown"}' \
    "documentation"

# Test 7: MCP Gateway Tool Discovery
echo "Test 7: MCP Gateway Tool Discovery"
echo "----------------------------------------"
echo -e "${YELLOW}Testing: MCP Gateway${NC}"
response=$(curl -s -w "\n%{http_code}" http://localhost:8000/api/tools)
http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | sed '$d')

if [ "$http_code" = "200" ]; then
    echo -e "  ${GREEN}✓ HTTP 200 OK${NC}"
    tool_count=$(echo "$body" | jq -r '.tools | length' 2>/dev/null || echo "0")
    if [ "$tool_count" -gt 0 ]; then
        echo -e "  ${GREEN}✓ Found $tool_count MCP tools${NC}"
        PASSED=$((PASSED + 1))
    else
        echo -e "  ${RED}✗ No tools found${NC}"
        FAILED=$((FAILED + 1))
    fi
else
    echo -e "  ${RED}✗ HTTP $http_code${NC}"
    FAILED=$((FAILED + 1))
fi
echo ""

# Summary
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
    echo "   docker-compose -f /opt/Dev-Tools/compose/docker-compose.yml logs -f orchestrator"
    echo ""
    exit 0
else
    echo -e "${RED}❌ Some tests failed. Check logs:${NC}"
    echo "docker-compose -f /opt/Dev-Tools/compose/docker-compose.yml logs --tail=50"
    echo ""
    exit 1
fi
