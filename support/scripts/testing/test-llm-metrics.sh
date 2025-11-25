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
echo "Grafana: https://appsmithery.grafana.net"
echo "Prometheus: http://45.55.173.72:9090"
echo

echo "To view metrics in Prometheus:"
echo "1. Navigate to http://45.55.173.72:9090/graph"
echo "2. Query: llm_tokens_total"
echo "3. Query: rate(http_requests_total[5m])"
