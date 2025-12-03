#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Test agent tracing by making sample requests
.DESCRIPTION
    Sends test requests to agents to generate LangSmith traces
#>

param(
    [string]$DropletIp = "45.55.173.72"
)

$ErrorActionPreference = "Continue"

Write-Host "`n=== Testing Agent Tracing ===" -ForegroundColor Cyan
Write-Host "Droplet: $DropletIp`n" -ForegroundColor Gray

# Test 1: Orchestrator health
Write-Host "[1/5] Testing orchestrator health..." -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri "http://${DropletIp}:8001/health" -TimeoutSec 5 -ErrorAction Stop
    Write-Host "  ✓ Orchestrator: $($response.status)" -ForegroundColor Green
} catch {
    Write-Host "  ✗ Orchestrator unavailable: $($_.Exception.Message)" -ForegroundColor Red
}

# Test 2: Gateway MCP tools
Write-Host "`n[2/5] Testing MCP Gateway..." -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri "http://${DropletIp}:8000/health" -TimeoutSec 5 -ErrorAction Stop
    Write-Host "  ✓ Gateway: $($response.status)" -ForegroundColor Green
} catch {
    Write-Host "  ✗ Gateway failed: $($_.Exception.Message)" -ForegroundColor Red
}

# Test 3: RAG Service
Write-Host "`n[3/5] Testing RAG Service..." -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri "http://${DropletIp}:8007/health" -TimeoutSec 5 -ErrorAction Stop
    Write-Host "  ✓ RAG: $($response.status), Qdrant: $($response.qdrant_status)" -ForegroundColor Green
} catch {
    Write-Host "  ✗ RAG failed: $($_.Exception.Message)" -ForegroundColor Red
}

# Test 4: State Persistence
Write-Host "`n[4/5] Testing State Persistence..." -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri "http://${DropletIp}:8008/health" -TimeoutSec 5 -ErrorAction Stop
    Write-Host "  ✓ State: $($response.status)" -ForegroundColor Green
} catch {
    Write-Host "  ✗ State failed: $($_.Exception.Message)" -ForegroundColor Red
}

# Test 5: LangGraph
Write-Host "`n[5/5] Testing LangGraph Service..." -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri "http://${DropletIp}:8010/health" -TimeoutSec 5 -ErrorAction Stop
    Write-Host "  ✓ LangGraph: $($response.status), Checkpointer: $($response.postgres_checkpointer)" -ForegroundColor Green
} catch {
    Write-Host "  ✗ LangGraph failed: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host "`n=== Next Steps ===" -ForegroundColor Cyan
Write-Host "1. All agents are internal LangGraph nodes (not separate containers)" -ForegroundColor Gray
Write-Host "2. Tracing is via LangSmith (LANGCHAIN_TRACING_V2=true)" -ForegroundColor Gray
Write-Host "3. Check LangSmith: https://smith.langchain.com/o/5029c640-3f73-480c-82f3-58e402ed4207" -ForegroundColor Cyan
Write-Host "4. Traces appear when orchestrator processes tasks`n" -ForegroundColor Gray
