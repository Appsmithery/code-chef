#!/usr/bin/env pwsh
# Pre-Deployment Validation for Dev-Tools
# Checks LangSmith tracing, workflows, and agent configurations

$ErrorActionPreference = "Continue"
$passed = 0
$failed = 0
$warnings = 0

function Check {
    param([string]$name, [scriptblock]$test)
    Write-Host "`nChecking: $name" -ForegroundColor Cyan
    try {
        $result = & $test
        if ($result -eq $true) {
            Write-Host "  PASS" -ForegroundColor Green
            $script:passed++
        }
        elseif ($result -eq "WARN") {
            Write-Host "  WARN" -ForegroundColor Yellow
            $script:warnings++
        }
        else {
            Write-Host "  FAIL" -ForegroundColor Red
            $script:failed++
        }
    }
    catch {
        Write-Host "  ERROR: $($_.Exception.Message)" -ForegroundColor Red
        $script:failed++
    }
}

Write-Host "========================================" -ForegroundColor Magenta
Write-Host "  Dev-Tools Pre-Deployment Checklist" -ForegroundColor Magenta
Write-Host "========================================" -ForegroundColor Magenta

Write-Host "`n--- ENVIRONMENT CONFIGURATION ---" -ForegroundColor Yellow

Check ".env file exists" {
    Test-Path "config/env/.env"
}

Check "LangSmith tracing enabled" {
    $env_content = Get-Content "config/env/.env" -Raw
    $env_content -match "LANGCHAIN_TRACING_V2=true"
}

Check "LangSmith API key" {
    $env_content = Get-Content "config/env/.env" -Raw
    if ($env_content -match "LANGCHAIN_API_KEY=lsv2_pt_") {
        Write-Host "    Configured" -ForegroundColor Gray
        return $true
    }
    return $false
}

Check "LangSmith project" {
    $env_content = Get-Content "config/env/.env" -Raw
    if ($env_content -match "LANGCHAIN_PROJECT=") {
        $project = ($env_content | Select-String "LANGCHAIN_PROJECT=(.+)" | ForEach-Object { $_.Matches.Groups[1].Value })
        Write-Host "    Project: $project" -ForegroundColor Gray
        return $true
    }
    return "WARN"
}

Check "Gradient AI credentials" {
    $env_content = Get-Content "config/env/.env" -Raw
    $env_content -match "GRADIENT_MODEL_ACCESS_KEY=sk-do-"
}

Write-Host "`n--- ORCHESTRATOR WORKFLOWS ---" -ForegroundColor Yellow

Check "Workflows directory" {
    Test-Path "agent_orchestrator/workflows"
}

Check "PR Deployment workflow" {
    $file = "agent_orchestrator/workflows/pr_deployment.py"
    if (Test-Path $file) {
        $content = Get-Content $file -Raw
        $has_app = $content -match "pr_deployment_app = workflow\.compile\(\)"
        if ($has_app) {
            Write-Host "    PR workflow compiled" -ForegroundColor Gray
            return $true
        }
    }
    return $false
}

Check "Parallel Docs workflow" {
    $file = "agent_orchestrator/workflows/parallel_docs.py"
    if (Test-Path $file) {
        $content = Get-Content $file -Raw
        $has_app = $content -match "parallel_docs_app = workflow\.compile\(\)"
        if ($has_app) {
            Write-Host "    Parallel docs workflow compiled" -ForegroundColor Gray
            return $true
        }
    }
    return $false
}

Check "Self-Healing workflow" {
    $file = "agent_orchestrator/workflows/self_healing.py"
    if (Test-Path $file) {
        $content = Get-Content $file -Raw
        $has_app = $content -match "self_healing_app = workflow\.compile\(\)"
        if ($has_app) {
            Write-Host "    Self-healing workflow compiled" -ForegroundColor Gray
            return $true
        }
    }
    return $false
}

Check "Workflow imports in main" {
    $file = "agent_orchestrator/workflows.py"
    if (Test-Path $file) {
        $content = Get-Content $file -Raw
        $pr = $content -match "pr_deployment_app"
        $parallel = $content -match "parallel_docs_app"
        $healing = $content -match "self_healing_app"
        if ($pr -and $parallel -and $healing) {
            Write-Host "    All 3 workflows imported" -ForegroundColor Gray
            return $true
        }
    }
    return $false
}

Write-Host "`n--- AGENT CONFIGURATIONS ---" -ForegroundColor Yellow

$agents = @("orchestrator", "feature-dev", "code-review", "infrastructure", "cicd", "documentation")

foreach ($agent in $agents) {
    Check "Agent: $agent" {
        $agentName = $agent
        $dir = "agent_$agentName"
        $has_main = Test-Path "$dir/main.py"
        $has_dockerfile = Test-Path "$dir/Dockerfile"
        
        if ($has_main -and $has_dockerfile) {
            return $true
        }
        return $false
    }
}

Write-Host "`n--- DOCKER CONFIGURATION ---" -ForegroundColor Yellow

Check "docker-compose.yml" {
    Test-Path "deploy/docker-compose.yml"
}

Check "All agents in compose" {
    $compose = Get-Content "deploy/docker-compose.yml" -Raw
    $count = 0
    foreach ($agent in $agents) {
        if ($compose -match $agent) {
            $count++
        }
    }
    if ($count -eq 6) {
        Write-Host "    All 6 agents configured" -ForegroundColor Gray
        return $true
    }
    return $false
}

Check "env_file mounts" {
    $compose = Get-Content "deploy/docker-compose.yml" -Raw
    $env_file_count = ([regex]::Matches($compose, "env_file:")).Count
    if ($env_file_count -ge 6) {
        Write-Host "    $env_file_count services with env_file" -ForegroundColor Gray
        return $true
    }
    return $false
}

Write-Host "`n--- RAG INTEGRATION ---" -ForegroundColor Yellow

Check "RAG service config" {
    $compose = Get-Content "deploy/docker-compose.yml" -Raw
    ($compose -match "rag-context") -and ($compose -match "RAG_SERVICE_URL")
}

Check "Orchestrator RAG metrics" {
    $main = Get-Content "agent_orchestrator/main.py" -Raw
    ($main -match "rag_context_injected_total") -and ($main -match "rag_vendor_keywords_detected")
}

Write-Host "`n--- MONITORING ---" -ForegroundColor Yellow

Check "Prometheus config" {
    Test-Path "config/prometheus/prometheus.yml"
}

Check "LangSmith endpoint" {
    $env_content = Get-Content "config/env/.env" -Raw
    $env_content -match "LANGCHAIN_ENDPOINT=https://api.smith.langchain.com"
}

Write-Host "`n========================================"  -ForegroundColor Magenta
Write-Host "SUMMARY" -ForegroundColor Magenta
Write-Host "========================================" -ForegroundColor Magenta
Write-Host "  PASSED: $passed" -ForegroundColor Green
Write-Host "  WARNINGS: $warnings" -ForegroundColor Yellow
Write-Host "  FAILED: $failed" -ForegroundColor Red

if ($failed -gt 0) {
    Write-Host "`nDEPLOYMENT BLOCKED - Fix critical issues" -ForegroundColor Red
    exit 1
}
elseif ($warnings -gt 0) {
    Write-Host "`nWARNINGS DETECTED - Review before deploying" -ForegroundColor Yellow
    exit 0
}
else {
    Write-Host "`nALL CHECKS PASSED - Ready for deployment!" -ForegroundColor Green
    exit 0
}
