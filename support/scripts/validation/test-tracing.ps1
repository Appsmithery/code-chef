#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Test agent tracing by making sample requests
.DESCRIPTION
    Sends test requests to agents to generate LangSmith traces
#>

param(
    [string]$DropletHost = "codechef.appsmithery.co",
    [string]$DropletIp = "45.55.173.72"  # For SSH fallback
)

$ErrorActionPreference = "Continue"

Write-Host "`n=== Testing Agent Tracing ===" -ForegroundColor Cyan
Write-Host "Domain: https://$DropletHost`n" -ForegroundColor Gray

# Test 1: Orchestrator health (via Caddy)
Write-Host "[1/4] Testing orchestrator health..." -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri "https://${DropletHost}/api/health" -TimeoutSec 5 -ErrorAction Stop
    Write-Host "  ✓ Orchestrator: $($response.status)" -ForegroundColor Green
} catch {
    Write-Host "  ✗ Orchestrator unavailable: $($_.Exception.Message)" -ForegroundColor Red
}

# Test 2: RAG Service (via Caddy)
Write-Host "`n[2/4] Testing RAG Service..." -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri "https://${DropletHost}/rag/health" -TimeoutSec 5 -ErrorAction Stop
    Write-Host "  ✓ RAG: $($response.status), Qdrant: $($response.qdrant_status)" -ForegroundColor Green
} catch {
    Write-Host "  ✗ RAG failed: $($_.Exception.Message)" -ForegroundColor Red
}

# Test 3: State Persistence (via Caddy)
Write-Host "`n[3/4] Testing State Persistence..." -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri "https://${DropletHost}/state/health" -TimeoutSec 5 -ErrorAction Stop
    Write-Host "  ✓ State: $($response.status)" -ForegroundColor Green
} catch {
    Write-Host "  ✗ State failed: $($_.Exception.Message)" -ForegroundColor Red
}

# Test 4: LangGraph (via Caddy)
Write-Host "`n[4/4] Testing LangGraph Service..." -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri "https://${DropletHost}/langgraph/health" -TimeoutSec 5 -ErrorAction Stop
    Write-Host "  ✓ LangGraph: $($response.status), Checkpointer: $($response.postgres_checkpointer)" -ForegroundColor Green
} catch {
    Write-Host "  ✗ LangGraph failed: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host "`n=== Next Steps ===" -ForegroundColor Cyan
Write-Host "1. All agents are internal LangGraph nodes (not separate containers)" -ForegroundColor Gray
Write-Host "2. Tracing is via LangSmith (LANGCHAIN_TRACING_V2=true)" -ForegroundColor Gray
Write-Host "3. Check LangSmith: https://smith.langchain.com/o/5029c640-3f73-480c-82f3-58e402ed4207" -ForegroundColor Cyan
Write-Host "4. Traces appear when orchestrator processes tasks`n" -ForegroundColor Gray
