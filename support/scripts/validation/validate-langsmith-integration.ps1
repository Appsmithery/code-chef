<#
.SYNOPSIS
    Validate LangSmith tracing integration across all agents
.DESCRIPTION
    Checks that all agents are properly configured for LangSmith observability
.PARAMETER SkipHealthChecks
    Skip HTTP health endpoint checks (useful if services not running)
#>

param(
    [switch]$SkipHealthChecks
)

$ErrorActionPreference = "Stop"

Write-Host "🔍 LangSmith Integration Validation" -ForegroundColor Cyan
Write-Host "===================================`n" -ForegroundColor Cyan

# Agent list
$agents = @(
    @{Name = "orchestrator"; Port = 8001},
    @{Name = "feature-dev"; Port = 8002},
    @{Name = "code-review"; Port = 8003},
    @{Name = "infrastructure"; Port = 8004},
    @{Name = "cicd"; Port = 8005},
    @{Name = "documentation"; Port = 8006}
)

$errors = @()
$warnings = @()

# Check 1: Verify docker-compose.yml has LangSmith env vars for all agents
Write-Host "✓ Checking docker-compose.yml configuration..." -ForegroundColor Yellow
$composeFile = "deploy/docker-compose.yml"
$composeContent = Get-Content $composeFile -Raw

$requiredEnvVars = @(
    "LANGCHAIN_TRACING_V2",
    "LANGCHAIN_ENDPOINT",
    "LANGCHAIN_PROJECT",
    "LANGCHAIN_API_KEY"
)

foreach ($agent in $agents) {
    $agentName = $agent.Name
    Write-Host "  Checking $agentName..." -NoNewline
    
    $hasAllVars = $true
    foreach ($envVar in $requiredEnvVars) {
        if ($composeContent -notmatch "$agentName[\s\S]*?$envVar") {
            $hasAllVars = $false
            break
        }
    }
    
    if ($hasAllVars) {
        Write-Host " ✅" -ForegroundColor Green
    } else {
        Write-Host " ❌ Missing LangSmith env vars" -ForegroundColor Red
        $errors += "${agentName}: Missing LangSmith environment variables in docker-compose.yml"
    }
}

# Check 2: Verify requirements.txt has necessary packages
Write-Host "`n✓ Checking requirements.txt dependencies..." -ForegroundColor Yellow
$requiredPackages = @(
    "langsmith",
    "langchain",
    "langchain-core",
    "prometheus-fastapi-instrumentator"
)

foreach ($agent in $agents) {
    $agentName = $agent.Name
    $reqFile = "agent_$agentName/requirements.txt"
    
    Write-Host "  Checking $agentName..." -NoNewline
    
    if (Test-Path $reqFile) {
        $reqContent = Get-Content $reqFile -Raw
        $hasMissing = $false
        
        foreach ($pkg in $requiredPackages) {
            if ($reqContent -notmatch "$pkg") {
                $hasMissing = $true
                break
            }
        }
        
        if (-not $hasMissing) {
            Write-Host " ✅" -ForegroundColor Green
        } else {
            Write-Host " ⚠️  Missing packages" -ForegroundColor Yellow
            $warnings += "${agentName}: Some required packages missing in requirements.txt"
        }
    } else {
        Write-Host " ❌ requirements.txt not found" -ForegroundColor Red
        $errors += "${agentName}: requirements.txt file not found"
    }
}

# Check 3: Verify .env file has LangSmith keys
Write-Host "`n✓ Checking .env configuration..." -ForegroundColor Yellow
$envFile = "config/env/.env"

if (Test-Path $envFile) {
    $envContent = Get-Content $envFile -Raw
    
    $envVarsToCheck = @(
        "LANGCHAIN_TRACING_V2",
        "LANGCHAIN_API_KEY",
        "LANGCHAIN_PROJECT"
    )
    
    $allPresent = $true
    foreach ($envVar in $envVarsToCheck) {
        if ($envContent -notmatch "$envVar\s*=") {
            $allPresent = $false
            $errors += "Missing $envVar in .env file"
        }
    }
    
    if ($allPresent) {
        Write-Host "  All LangSmith environment variables present ✅" -ForegroundColor Green
    } else {
        Write-Host "  Missing LangSmith environment variables ❌" -ForegroundColor Red
    }
} else {
    Write-Host "  .env file not found ❌" -ForegroundColor Red
    $errors += ".env file not found at $envFile"
}

# Check 4: Verify gradient_client.py configuration
Write-Host "`n✓ Checking gradient_client.py..." -ForegroundColor Yellow
$gradientClient = "shared/lib/gradient_client.py"

if (Test-Path $gradientClient) {
    $clientContent = Get-Content $gradientClient -Raw
    
    if ($clientContent -match "LangSmith" -and $clientContent -match "LANGCHAIN_TRACING_V2") {
        Write-Host "  gradient_client.py configured for LangSmith ✅" -ForegroundColor Green
    } else {
        Write-Host "  gradient_client.py missing LangSmith references ⚠️" -ForegroundColor Yellow
        $warnings += "gradient_client.py may not be configured for automatic tracing"
    }
} else {
    Write-Host "  gradient_client.py not found ❌" -ForegroundColor Red
    $errors += "gradient_client.py not found at $gradientClient"
}

# Check 5: Health checks (if not skipped)
if (-not $SkipHealthChecks) {
    Write-Host "`n✓ Checking agent health endpoints..." -ForegroundColor Yellow
    
    foreach ($agent in $agents) {
        $agentName = $agent.Name
        $port = $agent.Port
        
        Write-Host "  Checking $agentName (port $port)..." -NoNewline
        
        try {
            $response = Invoke-WebRequest -Uri "http://localhost:$port/health" -Method Get -TimeoutSec 5 -ErrorAction Stop
            if ($response.StatusCode -eq 200) {
                Write-Host " ✅" -ForegroundColor Green
            } else {
                Write-Host " ⚠️  HTTP $($response.StatusCode)" -ForegroundColor Yellow
                $warnings += "${agentName}: Health endpoint returned HTTP $($response.StatusCode)"
            }
        } catch {
            Write-Host " ⚠️  Not accessible" -ForegroundColor Yellow
            $warnings += "${agentName}: Health endpoint not accessible (may not be running)"
        }
    }
} else {
    Write-Host "`n⏭️  Skipping health checks (use without -SkipHealthChecks to test)" -ForegroundColor Gray
}

# Summary
Write-Host "`n" -NoNewline
Write-Host "=================================" -ForegroundColor Cyan
Write-Host "Validation Summary" -ForegroundColor Cyan
Write-Host "=================================`n" -ForegroundColor Cyan

if ($errors.Count -eq 0 -and $warnings.Count -eq 0) {
    Write-Host "✅ All checks passed!" -ForegroundColor Green
    Write-Host "`nAll agents are properly configured for LangSmith tracing." -ForegroundColor Green
    Write-Host "Ready for deployment.`n" -ForegroundColor Green
    exit 0
} else {
    if ($errors.Count -gt 0) {
        Write-Host "❌ Errors ($($errors.Count)):" -ForegroundColor Red
        foreach ($error in $errors) {
            Write-Host "  - $error" -ForegroundColor Red
        }
        Write-Host ""
    }
    
    if ($warnings.Count -gt 0) {
        Write-Host "⚠️  Warnings ($($warnings.Count)):" -ForegroundColor Yellow
        foreach ($warning in $warnings) {
            Write-Host "  - $warning" -ForegroundColor Yellow
        }
        Write-Host ""
    }
    
    if ($errors.Count -gt 0) {
        Write-Host "❌ Validation failed. Please fix errors before deployment." -ForegroundColor Red
        exit 1
    } else {
        Write-Host "⚠️  Validation passed with warnings. Review warnings before deployment." -ForegroundColor Yellow
        exit 0
    }
}
