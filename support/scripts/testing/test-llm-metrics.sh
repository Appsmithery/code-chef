#!/bin/bash
# Test LLM metrics collection by making a simple orchestrator request
# This will trigger LLM calls and populate the metrics

set -e

ORCHESTRATOR_URL="${1:-http://localhost:8001}"

echo "========================================="
echo "Testing LLM Metrics Collection"
echo "========================================="
echo

echo "[1] Current LLM metrics (before test):"
curl -s "${ORCHESTRATOR_URL}/metrics" | grep -E "^llm_"
echo

echo "[2] Making test request to trigger LLM call..."
# Simple health check won't trigger LLM, need to make actual agent request
# This would require a proper API call to /decompose or /workflow endpoint
echo "⚠️  Note: Need to trigger actual LLM call via orchestrator API"
echo "    Example: POST /api/v1/decompose with task description"
echo

echo "[3] Checking if metrics are incrementing..."
echo "Run this command on droplet to verify:"
echo "  watch -n 5 'curl -s http://localhost:8001/metrics | grep -E \"^llm_\"'"
echo

echo "========================================="
echo "Dashboard URLs"
echo "========================================="
echo "Grafana Cloud: https://appsmithery.grafana.net"
echo "Datasource: grafanacloud-appsmithery-prom"
echo ""

echo "To view metrics in Grafana Cloud:"
echo "1. Navigate to https://appsmithery.grafana.net/explore"
echo "2. Select datasource: grafanacloud-appsmithery-prom"
echo "3. Query: llm_tokens_total"
echo "4. Query: rate(http_requests_total[5m])"
