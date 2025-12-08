#!/usr/bin/env pwsh
<#
.SYNOPSIS
Pre-Deployment Checklist for Dev-Tools Multi-Agent System

.DESCRIPTION
Validates all critical configurations before production deployment:
- LangSmith tracing configuration
- Gradient AI credentials
- Orchestrator workflows
- Agent configurations
- Docker images
- Environment variables
#>

param(
    [switch]$Verbose,
    [switch]$SkipDockerCheck
)

$ErrorActionPreference = "Continue"
$Script:FailCount = 0
$Script:PassCount = 0
$Script:WarnCount = 0

function Test-CheckItem {
    param(
        [string]$Name,
        [scriptblock]$Test,
        [string]$SuccessMessage = "✅ PASS",
        [string]$FailMessage = "❌ FAIL",
        [string]$WarnMessage = "⚠️  WARN",
        [switch]$Critical
    )
    
    Write-Host "`n🔍 Checking: $Name" -ForegroundColor Cyan
    
    try {
        $result = & $Test
        
        if ($result -eq $true) {
            Write-Host "  $SuccessMessage" -ForegroundColor Green
            $Script:PassCount++
            return $true
        }
        elseif ($result -eq "WARN") {
            Write-Host "  $WarnMessage" -ForegroundColor Yellow
            $Script:WarnCount++
            return "WARN"
        }
        else {
            Write-Host "  $FailMessage" -ForegroundColor Red
            $Script:FailCount++
            if ($Critical) {
                Write-Host "  ⛔ CRITICAL: Deployment blocked" -ForegroundColor Red
            }
            return $false
        }
    }
    catch {
        Write-Host "  ❌ ERROR: $($_.Exception.Message)" -ForegroundColor Red
        $Script:FailCount++
        return $false
    }
}

Write-Host @"
╔══════════════════════════════════════════════════════════════════╗
║           Dev-Tools Pre-Deployment Checklist                     ║
║                 $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")                    ║
╚══════════════════════════════════════════════════════════════════╝
"@ -ForegroundColor Magenta

# ============================================================================
# 1. Environment Configuration
# ============================================================================
Write-Host "`n━━━ 1. ENVIRONMENT CONFIGURATION ━━━" -ForegroundColor Yellow

Test-CheckItem -Name "Config directory exists" -Critical -Test {
    Test-Path "config/env/.env"
}

Test-CheckItem -Name "LangSmith tracing enabled" -Critical -Test {
    $env_content = Get-Content "config/env/.env" -Raw
    if ($env_content -match "LANGCHAIN_TRACING_V2=true") {
        Write-Host "    Tracing: ENABLED" -ForegroundColor Gray
        return $true
    }
    return $false
}

Test-CheckItem -Name "LangSmith API key configured" -Critical -Test {
    $env_content = Get-Content "config/env/.env" -Raw
    if ($env_content -match "LANGCHAIN_API_KEY=lsv2_pt_[a-zA-Z0-9_]+") {
        $key = ($env_content | Select-String "LANGCHAIN_API_KEY=(.+)" | ForEach-Object { $_.Matches.Groups[1].Value })
        Write-Host "    Key: $($key.Substring(0, 20))..." -ForegroundColor Gray
        return $true
    }
    return $false
}

Test-CheckItem -Name "LangSmith project configured" -Test {
    $env_content = Get-Content "config/env/.env" -Raw
    if ($env_content -match "LANGCHAIN_PROJECT=(.+)") {
        $project = ($env_content | Select-String "LANGCHAIN_PROJECT=(.+)" | ForEach-Object { $_.Matches.Groups[1].Value })
        Write-Host "    Project: $project" -ForegroundColor Gray
        return $true
    }
    return "WARN"
}

Test-CheckItem -Name "Gradient AI credentials configured" -Critical -Test {
    $env_content = Get-Content "config/env/.env" -Raw
    if ($env_content -match "GRADIENT_MODEL_ACCESS_KEY=sk-do-") {
        Write-Host "    Gradient: CONFIGURED" -ForegroundColor Gray
        return $true
    }
    return $false
}

Test-CheckItem -Name "Linear Personal API Key configured" -Test {
    $env_content = Get-Content "config/env/.env" -Raw
    $has_api_key = $env_content -match "LINEAR_API_KEY=lin_api_"  # Personal API Key format
    if ($has_api_key) {
        Write-Host "    Linear: CONFIGURED" -ForegroundColor Gray
        return $true
    }
    return "WARN"
}

# ============================================================================
# 2. Orchestrator Workflows
# ============================================================================
Write-Host "`n━━━ 2. ORCHESTRATOR WORKFLOWS ━━━" -ForegroundColor Yellow

Test-CheckItem -Name "Workflows directory exists" -Critical -Test {
    Test-Path "agent_orchestrator/workflows"
}

Test-CheckItem -Name "PR Deployment workflow" -Critical -Test {
    $file = "agent_orchestrator/workflows/pr_deployment.py"
    if (Test-Path $file) {
        $content = Get-Content $file -Raw
        $has_app = $content -match "pr_deployment_app = workflow\.compile\(\)"
        $has_nodes = $content -match "workflow\.add_node"
        if ($has_app -and $has_nodes) {
            Write-Host "    Nodes: code_review, test, approval, deploy" -ForegroundColor Gray
            return $true
        }
    }
    return $false
}

Test-CheckItem -Name "Parallel Docs workflow" -Critical -Test {
    $file = "agent_orchestrator/workflows/parallel_docs.py"
    if (Test-Path $file) {
        $content = Get-Content $file -Raw
        $has_app = $content -match "parallel_docs_app = workflow\.compile\(\)"
        $has_parallel = $content -match "add_edge\(START"
        if ($has_app -and $has_parallel) {
            Write-Host "    Parallel nodes: api_docs, user_guide, deployment_guide" -ForegroundColor Gray
            return $true
        }
    }
    return $false
}

Test-CheckItem -Name "Self-Healing workflow" -Critical -Test {
    $file = "agent_orchestrator/workflows/self_healing.py"
    if (Test-Path $file) {
        $content = Get-Content $file -Raw
        $has_app = $content -match "self_healing_app = workflow\.compile\(\)"
        $has_loop = $content -match "check_resolution"
        if ($has_app -and $has_loop) {
            Write-Host "    Loop nodes: detect, diagnose, apply_fix, verify" -ForegroundColor Gray
            return $true
        }
    }
    return $false
}

Test-CheckItem -Name "Workflows module exports" -Critical -Test {
    $file = "agent_orchestrator/workflows.py"
    if (Test-Path $file) {
        $content = Get-Content $file -Raw
        $imports = @("pr_deployment_app", "parallel_docs_app", "self_healing_app")
        $all_imported = $true
        foreach ($import in $imports) {
            if ($content -notmatch $import) {
                $all_imported = $false
                break
            }
        }
        if ($all_imported) {
            Write-Host "    All 3 workflows imported in WorkflowManager" -ForegroundColor Gray
            return $true
        }
    }
    return $false
}

# ============================================================================
# 3. Agent Configurations
# ============================================================================
Write-Host "`n━━━ 3. AGENT CONFIGURATIONS ━━━" -ForegroundColor Yellow

$agents = @("orchestrator", "feature-dev", "code-review", "infrastructure", "cicd", "documentation")

foreach ($agent in $agents) {
    Test-CheckItem -Name "Agent: $agent" -Test {
        $agentName = $agent
        $dir = "agent_$($agentName.Replace('-', '_'))"
        $has_main = Test-Path "$dir/main.py"
        $has_dockerfile = Test-Path "$dir/Dockerfile"
        $has_reqs = Test-Path "$dir/requirements.txt"
        
        if ($has_main -and $has_dockerfile -and $has_reqs) {
            $main_content = Get-Content "$dir/main.py" -Raw
            $has_gradient = $main_content -match "gradient_client|GradientClient"
            $has_prometheus = $main_content -match "Instrumentator|prometheus"
            
            if ($has_gradient -and $has_prometheus) {
                Write-Host "    Success: Gradient client and Prometheus metrics" -ForegroundColor Gray
                return $true
            }
            elseif ($has_gradient) {
                Write-Host "    Warning: Gradient client but missing Prometheus" -ForegroundColor Gray
                return "WARN"
            }
        }
        return $false
    }
}

# ============================================================================
# 4. Docker Configuration
# ============================================================================
Write-Host "`n━━━ 4. DOCKER CONFIGURATION ━━━" -ForegroundColor Yellow

Test-CheckItem -Name "docker-compose.yml exists" -Critical -Test {
    Test-Path "deploy/docker-compose.yml"
}

Test-CheckItem -Name "All agents in docker-compose" -Critical -Test {
    $compose = Get-Content "deploy/docker-compose.yml" -Raw
    $missing = @()
    foreach ($agent in $agents) {
        $pattern = "$agent" + ":"
        if ($compose -notmatch $pattern) {
            $missing += $agent
        }
    }
    if ($missing.Count -eq 0) {
        Write-Host "    All 6 agents configured" -ForegroundColor Gray
        return $true
    }
    else {
        Write-Host "    Missing: $($missing -join ', ')" -ForegroundColor Gray
        return $false
    }
}

Test-CheckItem -Name "env_file configured for all agents" -Critical -Test {
    $compose = Get-Content "deploy/docker-compose.yml" -Raw
    $env_file_count = ([regex]::Matches($compose, "env_file:")).Count
    if ($env_file_count -ge 6) {
        Write-Host "    $env_file_count services with env_file mount" -ForegroundColor Gray
        return $true
    }
    return $false
}

if (-not $SkipDockerCheck) {
    Test-CheckItem -Name "Docker daemon running" -Test {
        try {
            docker info 2>&1 | Out-Null
            if ($LASTEXITCODE -eq 0) {
                return $true
            }
        }
        catch { }
        return "WARN"
    }
}

# ============================================================================
# 5. RAG Integration
# ============================================================================
Write-Host "`n━━━ 5. RAG INTEGRATION ━━━" -ForegroundColor Yellow

Test-CheckItem -Name "RAG service configuration" -Test {
    $compose = Get-Content "deploy/docker-compose.yml" -Raw
    if ($compose -match "rag-context:" -and $compose -match "RAG_SERVICE_URL") {
        Write-Host "    RAG service: rag-context:8007" -ForegroundColor Gray
        return $true
    }
    return "WARN"
}

Test-CheckItem -Name "Orchestrator RAG metrics" -Test {
    $main = Get-Content "agent_orchestrator/main.py" -Raw
    $has_metrics = $main -match "rag_context_injected_total" -and $main -match "rag_vendor_keywords_detected"
    if ($has_metrics) {
        Write-Host "    Prometheus RAG metrics configured" -ForegroundColor Gray
        return $true
    }
    return "WARN"
}

# ============================================================================
# 6. Monitoring & Observability
# ============================================================================
Write-Host "`n━━━ 6. MONITORING & OBSERVABILITY ━━━" -ForegroundColor Yellow

Test-CheckItem -Name "Prometheus configuration" -Test {
    Test-Path "config/prometheus/prometheus.yml"
}

Test-CheckItem -Name "LangSmith endpoint configured" -Test {
    $env_content = Get-Content "config/env/.env" -Raw
    if ($env_content -match "LANGCHAIN_ENDPOINT=https://api.smith.langchain.com") {
        return $true
    }
    return "WARN"
}

# ============================================================================
# SUMMARY
# ============================================================================
Write-Host "`n╔══════════════════════════════════════════════════════════════════╗" -ForegroundColor Magenta
Write-Host "║                      CHECKLIST SUMMARY                            ║" -ForegroundColor Magenta
Write-Host "╚══════════════════════════════════════════════════════════════════╝" -ForegroundColor Magenta

Write-Host "`n  [+] PASSED: $Script:PassCount" -ForegroundColor Green
Write-Host "  [!] WARNINGS: $Script:WarnCount" -ForegroundColor Yellow
Write-Host "  [-] FAILED: $Script:FailCount" -ForegroundColor Red

if ($Script:FailCount -gt 0) {
    Write-Host "`n[BLOCKED] DEPLOYMENT BLOCKED - Fix critical issues before deploying" -ForegroundColor Red
    exit 1
}
elseif ($Script:WarnCount -gt 0) {
    Write-Host "`n[WARN] WARNINGS DETECTED - Review before deploying" -ForegroundColor Yellow
    exit 0
}
else {
    Write-Host "`n[OK] ALL CHECKS PASSED - Ready for deployment!" -ForegroundColor Green
    exit 0
}
