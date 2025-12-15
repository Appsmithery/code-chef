#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Debug agent troubleshooting script for Dev-Tools agents.

.DESCRIPTION
    Gathers comprehensive diagnostic information for a specified agent:
    - Container status and resource usage
    - Last 100 log lines
    - Python packages (pip list)
    - /health endpoint response
    - Environment variables (sanitized)

.PARAMETER Agent
    Name of the agent service (orchestrator, feature-dev, code-review, infrastructure, cicd, documentation, gateway-mcp, rag-context, state-persistence)

.PARAMETER Remote
    When present, run diagnostics on the droplet via SSH

.PARAMETER Lines
    Number of log lines to retrieve (default: 100)

.PARAMETER ComposeFile
    Path to docker-compose.yml (default: deploy/docker-compose.yml)

.EXAMPLE
    .\scripts\debug-agent.ps1 -Agent orchestrator
    .\scripts\debug-agent.ps1 -Agent code-review -Remote
    .\scripts\debug-agent.ps1 -Agent gateway-mcp -Lines 200
#>

param(
    [Parameter(Mandatory=$true)]
    [ValidateSet(
        "orchestrator",
        "feature-dev",
        "code-review",
        "infrastructure",
        "cicd",
        "documentation",
        "gateway-mcp",
        "rag-context",
        "state-persistence",
        "langgraph"
    )]
    [string]$Agent,
    
    [switch]$Remote,
    [int]$Lines = 100,
    [string]$ComposeFile = "deploy/docker-compose.yml"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

function Write-Section { param($Title) Write-Host "`n========================================" -ForegroundColor Cyan; Write-Host $Title -ForegroundColor Cyan; Write-Host "========================================" -ForegroundColor Cyan }
function Write-Info { param($Message) Write-Host "  -> $Message" -ForegroundColor Gray }
function Write-Success { param($Message) Write-Host "  [OK] $Message" -ForegroundColor Green }
function Write-Failure { param($Message) Write-Host "  [ERROR] $Message" -ForegroundColor Red }

$DROPLET = "do-codechef-droplet"
$DEPLOY_PATH = "/opt/code-chef"

# Port mapping
$ports = @{
    "gateway-mcp" = 8000
    "orchestrator" = 8001
    "feature-dev" = 8002
    "code-review" = 8003
    "infrastructure" = 8004
    "cicd" = 8005
    "documentation" = 8006
    "rag-context" = 8007
    "state-persistence" = 8008
    "langgraph" = 8009
}

$port = $ports[$Agent]

Write-Section "Agent Diagnostics: $Agent"

if ($Remote) {
    Write-Info "Running diagnostics on droplet ($DROPLET)"
    
    # Container status
    Write-Host "`nContainer Status:" -ForegroundColor Yellow
    ssh $DROPLET "export DOCKER_HOST=unix:///var/run/docker.sock ; cd $DEPLOY_PATH/compose ; docker compose ps $Agent"
    
    # Container stats
    Write-Host "`nResource Usage:" -ForegroundColor Yellow
    ssh $DROPLET "export DOCKER_HOST=unix:///var/run/docker.sock ; docker stats --no-stream $Agent"
    
    # Container logs
    Write-Host "`nLast $Lines Log Lines:" -ForegroundColor Yellow
    ssh $DROPLET "export DOCKER_HOST=unix:///var/run/docker.sock ; cd $DEPLOY_PATH/compose ; docker compose logs --tail=$Lines $Agent"
    
    # Health endpoint
    if ($port) {
        Write-Host "`nHealth Endpoint:" -ForegroundColor Yellow
        $healthCheck = ssh $DROPLET "curl -s -w '\nHTTP_CODE:%{http_code}' http://localhost:$port/health"
        Write-Host $healthCheck
    }
    
    # Python packages (if Python agent)
    if ($Agent -ne "gateway-mcp") {
        Write-Host "`nInstalled Python Packages:" -ForegroundColor Yellow
        ssh $DROPLET "export DOCKER_HOST=unix:///var/run/docker.sock ; docker exec compose-${Agent}-1 pip list 2>/dev/null || echo 'Not a Python container or pip unavailable'"
    }
    
    # Environment variables (sanitized)
    Write-Host "`nEnvironment Variables (sanitized):" -ForegroundColor Yellow
    ssh $DROPLET "export DOCKER_HOST=unix:///var/run/docker.sock ; docker exec compose-${Agent}-1 env | grep -E '^(AGENT_NAME|GRADIENT_MODEL|MCP_GATEWAY_URL|RAG_SERVICE_URL|STATE_SERVICE_URL|SERVICE_NAME|NODE_ENV)=' | sort"
    
} else {
    Write-Info "Running diagnostics locally"
    
    $repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
    Set-Location $repoRoot
    
    # Container status
    Write-Host "`nContainer Status:" -ForegroundColor Yellow
    docker compose -f $ComposeFile ps $Agent
    
    # Container stats
    Write-Host "`nResource Usage:" -ForegroundColor Yellow
    docker stats --no-stream $Agent
    
    # Container logs
    Write-Host "`nLast $Lines Log Lines:" -ForegroundColor Yellow
    docker compose -f $ComposeFile logs --tail=$Lines $Agent
    
    # Health endpoint
    if ($port) {
        Write-Host "`nHealth Endpoint:" -ForegroundColor Yellow
        try {
            $response = Invoke-WebRequest -Uri "http://localhost:$port/health" -Method GET -UseBasicParsing
            Write-Success "HTTP $($response.StatusCode)"
            Write-Host $response.Content
        } catch {
            Write-Failure "Health check failed: $_"
        }
    }
    
    # Python packages (if Python agent)
    if ($Agent -ne "gateway-mcp") {
        Write-Host "`nInstalled Python Packages:" -ForegroundColor Yellow
        docker exec $Agent pip list 2>$null
        if ($LASTEXITCODE -ne 0) {
            Write-Info "Not a Python container or pip unavailable"
        }
    }
    
    # Environment variables (sanitized)
    Write-Host "`nEnvironment Variables (sanitized):" -ForegroundColor Yellow
    docker exec $Agent env | Select-String -Pattern '^(AGENT_NAME|GRADIENT_MODEL|MCP_GATEWAY_URL|RAG_SERVICE_URL|STATE_SERVICE_URL|SERVICE_NAME|NODE_ENV)=' | Sort-Object
}

Write-Host ""
Write-Section "Diagnostics Complete"

Write-Host "`nNext Steps:" -ForegroundColor Yellow
Write-Host "1. Check logs for errors or stack traces" -ForegroundColor White
Write-Host "2. Verify environment variables are set correctly" -ForegroundColor White
Write-Host "3. Confirm health endpoint returns 200 OK" -ForegroundColor White
Write-Host "4. Review resource usage (CPU/Memory)" -ForegroundColor White
Write-Host "5. Test MCP gateway connectivity: curl http://localhost:8000/health" -ForegroundColor White
Write-Host ""
